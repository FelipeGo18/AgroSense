"""Tablas de las cuentas (specs/02-contratos.md, «Base de datos de cuentas»). M8.

Todo cambio en este archivo necesita su migración: `uv run python -m backend.db.revision "..."` (backend/README.md).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class User(Base):
    """Un agricultor (o quien da soporte). Sin correo, celular, documento ni dirección (R9)."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('farmer', 'admin', 'developer')", name="role_valid"),)

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    # Solo el hash Argon2 de la contraseña; la contraseña nunca se guarda.
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(16), default="farmer", server_default="farmer")
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[int] = mapped_column(SmallInteger)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Pesos de 0 a 5 por señal que eligió el agricultor; nulo = los de AgroSense.
    priorities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class Session(Base):
    """Una sesión abierta. Se guarda el hash del token, nunca el token. Vence a los 30 días."""

    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Borrar al usuario borra sus sesiones (R9).
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class LoginAttempt(Base):
    """Un intento fallido (o en curso) de entrar, de cambiar la contraseña o de borrar la cuenta. Sirve solo para el
    tope general de 20 intentos en 15 minutos por usuario, desde cualquier conexión: se anota antes de verificar la
    contraseña y se quita si era la buena. El tope de 5 por conexión vive en memoria (`backend/accounts/limits.py`).

    No guarda el usuario que se intentó (podría ser una contraseña escrita en el campo equivocado) sino su hash,
    ni la IP. Las filas viejas se borran solas: pasados los 15 minutos ya no cuentan.
    """

    __tablename__ = "login_attempts"

    attempt_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username_hash: Mapped[str] = mapped_column(String(64), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
