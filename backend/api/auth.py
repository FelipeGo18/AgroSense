"""Cuenta y sesión: `/api/v1/auth/*` y `/api/v1/me*` (HU-160, HU-162, HU-163 y HU-178; specs/02-contratos.md)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.limits import FAILED_PER_IP_AND_USER, LIMITER, LOGIN_PER_IP, REGISTER_PER_IP, Hit, Rule, retry_after
from backend.accounts.models import LoginAttempt, Session, User
from backend.accounts.security import (
    ATTEMPT_WINDOW,
    clear_attempts,
    hash_password,
    hash_token,
    new_session_token,
    release_attempt,
    take_attempt,
    verify_password,
)
from backend.api.errors import ACCOUNTS_UNAVAILABLE, ApiError, explain, request_id_of
from backend.config.logging import get_logger
from backend.config.settings import Settings, get_settings
from backend.db.session import get_db
from backend.db.state import accounts_state

log = get_logger("agrosense.api")


def require_accounts(db: Db = Depends(get_db)) -> None:
    """Todo lo de las cuentas pasa primero por aquí. Si la base de datos no responde o su esquema no está en la
    última migración, se responde 503 y el log dice por qué; no se intenta atender contra tablas que no son las esperadas."""
    state = accounts_state(db)
    if state.available:
        return
    log.warning(
        "accounts_unavailable",
        reason=state.reason,
        current_migration=state.current,
        expected_migration=state.expected,
        detail=f"Cuentas no disponibles (503) porque {state.explanation}",
    )
    raise ApiError(503, f"accounts_{state.reason}", ACCOUNTS_UNAVAILABLE, log=f"Cuentas no disponibles (503) porque {state.explanation}")


router = APIRouter(prefix="/api/v1", tags=["cuenta"], dependencies=[Depends(require_accounts)])

SESSION_COOKIE = "agrosense_session"
SESSION_DAYS = 30
# Versión vigente del consentimiento (HU-163). Supuesto por confirmar: otra versión responde 422.
CONSENT_VERSION = 3
# Las señales que el agricultor puede ponderar (specs/01-reglas.md): las seis del P0 y las tres del P1.
SIGNALS = frozenset({"water", "frost", "heat", "soil", "supply", "market", "excess_rain", "disease", "harvest_weather"})
TOO_MANY_ATTEMPTS = "Demasiados intentos. Espere 15 minutos y vuelva a intentar."
TOO_MANY_REQUESTS = "Demasiadas peticiones desde su conexión. Espere unos minutos y vuelva a intentar."

# 3 a 30 caracteres: letras minúsculas sin tilde, números, punto y guion bajo.
Username = Annotated[str, StringConstraints(pattern=r"^[a-z0-9._]{3,30}$")]
# Al menos 8 caracteres. El tope evita gastar el servidor calculando el hash de un texto enorme.
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class RegisterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    password: Password
    display_name: DisplayName
    consent_version: int
    consent_accepted: bool


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Sin patrón: un usuario mal escrito es «usuario o contraseña incorrectos» (401), no un 422.
    username: str = Field(max_length=128)
    password: str = Field(max_length=128)


class ProfilePatch(BaseModel):
    """Lo que se puede editar del perfil. Un campo que no viene no cambia; `priorities` nulo vuelve a las de AgroSense."""

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    username: Username | None = None
    priorities: dict[str, int] | None = None

    @field_validator("priorities")
    @classmethod
    def valid_priorities(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        if value is None:
            return None
        if not value or set(value) - SIGNALS or any(not 0 <= weight <= 5 for weight in value.values()):
            raise ValueError("Cada prioridad es un entero de 0 a 5 para una señal conocida.")
        if all(weight == 0 for weight in value.values()):
            raise ValueError("No pueden estar todas las prioridades en 0.")
        return value


class DeleteBody(BaseModel):
    """Borrar la cuenta pide la contraseña: una sesión abierta en un equipo prestado no basta para borrarlo todo."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(max_length=128)


class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(max_length=128)
    new_password: Password


class Profile(BaseModel):
    """El perfil del usuario. Nunca incluye el hash de la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    display_name: str
    role: str
    consent_version: int
    consent_at: datetime
    priorities: dict[str, Any] | None
    created_at: datetime


class ActivityItem(BaseModel):
    """Un evento de «Mi actividad». Al agricultor nunca se le dice quién es el administrador: solo su rol."""

    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    occurred_at: datetime
    action: str
    actor_role: str | None
    object_type: str | None
    object_id: uuid.UUID | None
    outcome: str
    ticket_id: uuid.UUID | None
    details: dict[str, Any] | None


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    # Nulo cuando no hay más páginas.
    next_before: datetime | None


def _now() -> datetime:
    return datetime.now(UTC)


def _open_session(db: Db, user: User, response: Response, settings: Settings) -> Session:
    token = new_session_token()
    session = Session(user_id=user.user_id, token_hash=hash_token(token), expires_at=_now() + timedelta(days=SESSION_DAYS))
    db.add(session)
    db.flush()
    # httpOnly: el JavaScript de la página no puede leer el token. SameSite=Lax y Secure: ver el contrato.
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return session


def _close_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=settings.session_cookie_secure, samesite="lax")


def _client_ip(request: Request) -> str:
    """La IP de quien llama. Solo se usa en memoria, como llave de los límites, y nunca se guarda ni se escribe (R9).
    Detrás de un proxy, Uvicorn la toma de `X-Forwarded-For` solo si el proxy está en `FORWARDED_ALLOW_IPS`."""
    return request.client.host if request.client else "sin-ip"


def _limit_connection(request: Request, rule: Rule, what: str) -> None:
    """Límite de peticiones por conexión (IP), salgan bien o mal."""
    taken = LIMITER.take(rule, _client_ip(request))
    if isinstance(taken, float):
        raise ApiError(
            429,
            "too_many_requests",
            TOO_MANY_REQUESTS,
            log=f"Rechazado: demasiadas peticiones de {what} desde la misma conexión",
            headers={"Retry-After": retry_after(taken)},
        )


@dataclass
class PasswordCheck:
    """Un intento de verificar una contraseña, anotado antes de verificarla en los dos topes: el de esta conexión con
    este usuario (en memoria) y el general del usuario (en la base de datos). Si la contraseña es mala, queda anotado."""

    db: Db
    ip: str
    username: str
    hit: Hit
    attempt: LoginAttempt

    def release(self) -> None:
        """La contraseña era la buena, pero no se siguió (cuenta bloqueada, contraseña nueva igual): no cuenta."""
        LIMITER.release(self.hit)
        release_attempt(self.db, self.attempt)

    def succeeded(self) -> None:
        """La contraseña era la buena y se siguió: se borran los intentos de este usuario. Se confirma con el cambio."""
        LIMITER.clear(FAILED_PER_IP_AND_USER, self.ip, self.username)
        clear_attempts(self.db, self.username)


def _check_password(db: Db, request: Request, username: str, actor: User | None, action: str) -> PasswordCheck:
    """Antes de verificar una contraseña: 429 si esta conexión ya se equivocó 5 veces con este usuario en 15 minutos,
    o si el usuario lleva 20 fallidos desde cualquier conexión. Un bloqueo deja un solo evento por ventana."""
    ip = _client_ip(request)
    hit = LIMITER.take(FAILED_PER_IP_AND_USER, ip, username)
    if isinstance(hit, float):
        activity.record_lockout(db, action, request_id=request_id_of(request), actor=actor, window=ATTEMPT_WINDOW)
        raise ApiError(
            429,
            "too_many_attempts",
            TOO_MANY_ATTEMPTS,
            log="Rechazado: 5 contraseñas que no coinciden para ese usuario desde la misma conexión en 15 minutos",
            headers={"Retry-After": retry_after(hit)},
        )
    attempt = take_attempt(db, username)
    if attempt is None:
        LIMITER.release(hit)
        activity.record_lockout(db, action, request_id=request_id_of(request), actor=actor, window=ATTEMPT_WINDOW)
        raise ApiError(
            429,
            "too_many_attempts",
            TOO_MANY_ATTEMPTS,
            log="Rechazado: 20 intentos fallidos de ese usuario desde cualquier conexión en 15 minutos",
            headers={"Retry-After": retry_after(ATTEMPT_WINDOW.total_seconds())},
        )
    return PasswordCheck(db, ip, username, hit, attempt)


def current_session(request: Request, db: Db = Depends(get_db)) -> Session:
    """La sesión de quien llama. Sin cookie, con un token desconocido, con la sesión vencida o con la cuenta bloqueada, 401."""
    token = request.cookies.get(SESSION_COOKIE)
    session = db.scalar(select(Session).where(Session.token_hash == hash_token(token))) if token else None
    why = "no trae cookie de sesión" if not token else "la sesión no existe o ya fue cerrada"
    if session is not None and session.expires_at <= _now():
        db.delete(session)
        db.commit()
        session, why = None, "la sesión venció (duran 30 días)"
    if session is not None and session.user.blocked_at is not None:
        session, why = None, "la cuenta está bloqueada"
    if session is None:
        raise ApiError(401, "unauthorized", "Inicie sesión para continuar.", log=f"Petición rechazada: {why}")
    # Para la línea de log de la petición: quién fue, sin su usuario ni su nombre.
    request.state.user_id = str(session.user_id)
    request.state.role = session.user.role
    return session


def current_user(session: Session = Depends(current_session)) -> User:
    return session.user


@router.post("/auth/register", status_code=201, response_model=Profile)
def register(
    body: RegisterBody,
    request: Request,
    response: Response,
    db: Db = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Crea la cuenta y deja la sesión abierta. Sin aceptar el consentimiento vigente no se crea nada (R9).
    Cada conexión intenta hasta 10 registros por hora: así tampoco se puede probar en masa qué usuarios existen (409)."""
    _limit_connection(request, REGISTER_PER_IP, "registro")
    if not body.consent_accepted or body.consent_version != CONSENT_VERSION:
        raise ApiError(
            422,
            "consent_required",
            "Para crear la cuenta hay que aceptar el tratamiento de datos.",
            log="Registro rechazado: no aceptó el consentimiento vigente (versión 3)",
        )
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        consent_version=body.consent_version,
        consent_at=_now(),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "username_taken",
            "Ese nombre de usuario ya está en uso. Pruebe con otro.",
            log="Rechazado: ese nombre de usuario ya existe",
        ) from exc
    session = _open_session(db, user, response, settings)
    request_id = request_id_of(request)
    activity.record(db, "auth.registered", request_id=request_id, actor=user, object_type="user", object_id=user.user_id)
    activity.record(db, "consent.accepted", request_id=request_id, actor=user, object_type="user", object_id=user.user_id)
    activity.record(db, "auth.login", request_id=request_id, actor=user, object_type="session", object_id=session.session_id)
    db.commit()
    return user


@router.post("/auth/login", response_model=Profile)
def login(
    body: LoginBody,
    request: Request,
    response: Response,
    db: Db = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    _limit_connection(request, LOGIN_PER_IP, "inicio de sesión")
    username = body.username.strip().lower()
    request_id = request_id_of(request)
    user = db.scalar(select(User).where(User.username == username))
    # El intento se anota antes de verificar: así varias peticiones a la vez no se saltan el tope.
    check = _check_password(db, request, username, user, "auth.login_failed")
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        # El intento ya quedó anotado. El evento no guarda el usuario que se intentó: si no existe, queda sin actor.
        activity.record(db, "auth.login_failed", request_id=request_id, actor=user, outcome="failed")
        db.commit()
        # A la persona se le dice lo mismo en los dos casos; en la terminal del servidor sí se sabe cuál fue.
        why = "usuario no registrado" if user is None else "contraseña incorrecta"
        raise ApiError(401, "invalid_credentials", "El usuario o la contraseña no coinciden.", log=f"Inicio de sesión rechazado: {why}")
    if user.blocked_at is not None:
        check.release()
        activity.record_rejected(db, "auth.login_failed", request_id=request_id, actor=user, outcome="denied")
        raise ApiError(403, "account_blocked", "Esta cuenta está bloqueada.", log="Inicio de sesión rechazado: la cuenta está bloqueada")
    check.succeeded()
    # De paso se limpia lo vencido: sesiones de este usuario y eventos de más de 180 días.
    db.execute(delete(Session).where(Session.user_id == user.user_id, Session.expires_at <= _now()))
    activity.purge_old(db)
    session = _open_session(db, user, response, settings)
    activity.record(db, "auth.login", request_id=request_id, actor=user, object_type="session", object_id=session.session_id)
    db.commit()
    return user


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(current_session),
    db: Db = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Cierra la sesión actual: la fila se borra, así que el token deja de servir aunque alguien lo haya copiado."""
    activity.record(
        db, "auth.logout", request_id=request_id_of(request), actor=session.user, object_type="session", object_id=session.session_id
    )
    db.delete(session)
    db.commit()
    _close_cookie(response, settings)


@router.get("/me", response_model=Profile)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.patch("/me", response_model=Profile)
def update_me(body: ProfilePatch, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> User:
    """Edita el nombre, el usuario o las prioridades. Cambiar el usuario no cierra la sesión."""
    changes = {field: getattr(body, field) for field in body.model_fields_set}
    # Solo `priorities` acepta nulo (vuelve a las de AgroSense); el nombre y el usuario no se pueden vaciar.
    if any(changes[field] is None for field in ("display_name", "username") if field in changes):
        raise ApiError(
            422,
            "invalid_input",
            "El nombre y el usuario no pueden quedar vacíos.",
            log="Edición del perfil rechazada: nombre o usuario vacío",
        )
    changed = [field for field, value in changes.items() if getattr(user, field) != value]
    for field in changed:
        setattr(user, field, changes[field])
    explain(request, f"Perfil actualizado: {', '.join(sorted(changed))}" if changed else "Perfil sin cambios: llegó lo mismo que ya tenía")
    if changed:
        activity.record(
            db, "profile.updated", request_id=request_id_of(request), actor=user, object_type="user", object_id=user.user_id, fields=changed
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "username_taken",
            "Ese nombre de usuario ya está en uso. Pruebe con otro.",
            log="Rechazado: ese nombre de usuario ya existe",
        ) from exc
    return user


@router.post("/me/password", status_code=204)
def change_password(
    body: PasswordBody,
    request: Request,
    session: Session = Depends(current_session),
    db: Db = Depends(get_db),
) -> None:
    """Cambia la contraseña. Cierra las demás sesiones del usuario; la actual sigue abierta."""
    user = session.user
    request_id = request_id_of(request)
    check = _check_password(db, request, user.username, user, "auth.password_changed")
    if not verify_password(user.password_hash, body.current_password):
        # Cuenta igual que un intento fallido de entrar (ya quedó anotado). La sesión sigue abierta.
        activity.record(
            db, "auth.password_changed", request_id=request_id, actor=user, outcome="failed", object_type="user", object_id=user.user_id
        )
        db.commit()
        raise ApiError(
            403,
            "wrong_password",
            "La contraseña actual no coincide.",
            log="Cambio de contraseña rechazado: la contraseña actual es incorrecta",
        )
    if body.new_password == body.current_password:
        check.release()
        raise ApiError(
            422,
            "same_password",
            "La contraseña nueva debe ser distinta de la actual.",
            log="Cambio de contraseña rechazado: la nueva es igual a la actual",
        )
    user.password_hash = hash_password(body.new_password)
    db.execute(delete(Session).where(Session.user_id == user.user_id, Session.session_id != session.session_id))
    check.succeeded()
    activity.record(db, "auth.password_changed", request_id=request_id, actor=user, object_type="user", object_id=user.user_id)
    db.commit()


@router.get("/me/activity", response_model=ActivityPage)
def my_activity(
    before: datetime | None = None,
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
) -> ActivityPage:
    """Mi actividad: lo que hice con mi cuenta y lo que soporte hizo sobre mis datos, de lo más reciente a lo más antiguo."""
    events, next_before = activity.page(db, user, before, limit)
    return ActivityPage(items=[ActivityItem.model_validate(event) for event in events], next_before=next_before)


@router.delete("/me", status_code=204)
def delete_me(
    body: DeleteBody,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Borra la cuenta para siempre, con todo lo que cuelga de ella: sesiones, lotes, temporadas, tickets y su actividad (R9).
    Pide la contraseña; una que no coincide cuenta como un intento fallido y la sesión sigue abierta."""
    check = _check_password(db, request, user.username, user, "account.deleted")
    if not verify_password(user.password_hash, body.password):
        activity.record(
            db,
            "account.deleted",
            request_id=request_id_of(request),
            actor=user,
            outcome="failed",
            object_type="user",
            object_id=user.user_id,
        )
        db.commit()
        raise ApiError(
            403, "wrong_password", "La contraseña no coincide.", log="Borrado de la cuenta rechazado: la contraseña es incorrecta"
        )
    check.succeeded()
    activity.forget_user(db, user)
    db.execute(delete(User).where(User.user_id == user.user_id))
    db.commit()
    _close_cookie(response, settings)
