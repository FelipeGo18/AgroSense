"""Contraseñas, tokens de sesión y tope de intentos (specs/02-contratos.md, «Cómo viaja la credencial»)."""

import hashlib
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as Db

from backend.accounts.models import LoginAttempt

_hasher = PasswordHasher()  # Argon2id con los parámetros recomendados por la librería

# Hash de una contraseña que nadie tiene: se verifica contra él cuando el usuario no existe,
# para que la respuesta tarde lo mismo y no revele qué usuarios están registrados.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))

# Tope **general** por usuario, desde cualquier conexión: para un ataque repartido entre muchas IP. El tope de cada
# conexión (5 en 15 minutos) vive en `limits.py`; este vive en la base de datos y sobrevive a un reinicio.
MAX_ATTEMPTS = 20
ATTEMPT_WINDOW = timedelta(minutes=15)

# Cada cálculo de Argon2 usa unos 64 MiB de memoria. Como mucho 4 a la vez: los demás esperan su turno hasta 10
# segundos y, si no les llega, la API responde 503 en vez de quedarse sin memoria.
ARGON2_SLOTS = 4
ARGON2_WAIT_S = 10.0
_slots = threading.BoundedSemaphore(ARGON2_SLOTS)


class ServerBusy(RuntimeError):
    """Todos los cálculos de contraseña están en uso y no se liberó ninguno a tiempo."""


def _argon2[T](work: Callable[[], T]) -> T:
    if not _slots.acquire(timeout=ARGON2_WAIT_S):
        raise ServerBusy("Todos los cálculos de contraseña están en uso")
    try:
        return work()
    finally:
        _slots.release()


def hash_password(password: str) -> str:
    return _argon2(lambda: _hasher.hash(password))


def verify_password(password_hash: str | None, password: str) -> bool:
    def work() -> bool:
        try:
            return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
        except (VerificationError, InvalidHashError):
            return False

    return _argon2(work)


def new_session_token() -> str:
    """Token aleatorio de 256 bits. Es lo único que viaja en la cookie."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """En la base de datos se guarda este hash, nunca el token: quien lea la tabla no puede abrir una sesión."""
    return hashlib.sha256(token.encode()).hexdigest()


def _attempt_key(username: str) -> str:
    """El tope se lleva por usuario, pero sin guardar lo que se escribió: podría ser una contraseña en el campo equivocado."""
    return hashlib.sha256(f"intento:{username}".encode()).hexdigest()


def take_attempt(db: Db, username: str) -> LoginAttempt | None:
    """Anota el intento **antes** de verificar la contraseña, y devuelve su fila si cabe en el tope general de 20 en
    15 minutos.

    Se confirma de una vez y después se cuenta, así que varias peticiones a la vez no se saltan el tope: cada una ve,
    por lo menos, las que se anotaron antes que ella. Si ya no cabe, se quita y devuelve nulo: un intento rechazado
    no alarga el bloqueo. Si la contraseña resulta mala la fila se queda; si es buena, se suelta (`release_attempt`) o
    se limpian todas (`clear_attempts`). De paso borra los que ya no cuentan (de cualquier usuario).
    """
    key = _attempt_key(username)
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at <= datetime.now(UTC) - ATTEMPT_WINDOW))
    attempt = LoginAttempt(username_hash=key)
    db.add(attempt)
    db.commit()
    recent = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.username_hash == key, LoginAttempt.attempted_at > datetime.now(UTC) - ATTEMPT_WINDOW)
    )
    if (recent or 0) > MAX_ATTEMPTS:
        release_attempt(db, attempt)
        return None
    return attempt


def release_attempt(db: Db, attempt: LoginAttempt) -> None:
    """La contraseña era la buena: ese intento no cuenta como fallido."""
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempt_id == attempt.attempt_id))
    db.commit()


def clear_attempts(db: Db, username: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.username_hash == _attempt_key(username)))
