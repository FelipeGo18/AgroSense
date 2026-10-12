"""Contraseñas, tokens de sesión y tope de intentos (specs/02-contratos.md, «Cómo viaja la credencial»)."""

import hashlib
import secrets
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

MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = timedelta(minutes=15)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    """Token aleatorio de 256 bits. Es lo único que viaja en la cookie."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """En la base de datos se guarda este hash, nunca el token: quien lea la tabla no puede abrir una sesión."""
    return hashlib.sha256(token.encode()).hexdigest()


def _attempt_key(username: str) -> str:
    """El tope se lleva por usuario, pero sin guardar lo que se escribió: podría ser una contraseña en el campo equivocado."""
    return hashlib.sha256(f"intento:{username}".encode()).hexdigest()


def too_many_attempts(db: Db, username: str) -> bool:
    """Verdadero tras 5 intentos fallidos de ese usuario en los últimos 15 minutos."""
    since = datetime.now(UTC) - ATTEMPT_WINDOW
    recent = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.username_hash == _attempt_key(username), LoginAttempt.attempted_at > since)
    )
    return (recent or 0) >= MAX_ATTEMPTS


def record_failed_attempt(db: Db, username: str) -> None:
    """Anota un intento fallido y, de paso, borra los que ya no cuentan (de cualquier usuario)."""
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at <= datetime.now(UTC) - ATTEMPT_WINDOW))
    db.add(LoginAttempt(username_hash=_attempt_key(username)))


def clear_attempts(db: Db, username: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.username_hash == _attempt_key(username)))
