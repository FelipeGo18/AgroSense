"""Tablas de soporte, trazabilidad y uso (specs/02-contratos.md: «Trazabilidad» y `usage_daily`). M8.

Todo cambio en este archivo necesita su migración: `uv run python -m backend.db.revision "..."` (backend/README.md).
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

TICKET_STATUSES = ("open", "in_progress", "closed")
OUTCOMES = ("ok", "denied", "failed")
OBJECT_TYPES = ("user", "session", "lot", "season", "ticket")
USAGE_ENDPOINTS = ("diagnostics", "rotations", "changes", "calendar", "water_plans", "scenarios")


def _in(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


class SupportTicket(Base):
    """Un problema que reporta el agricultor, opcionalmente sobre un lote (HU-170)."""

    __tablename__ = "support_tickets"
    __table_args__ = (CheckConstraint(f"status in {_in(TICKET_STATUSES)}", name="status_valid"),)

    ticket_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    # Si el lote se borra para siempre, el ticket queda sin lote.
    lot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lots.lot_id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActivityEvent(Base):
    """Quién hizo qué, cuándo y sobre qué (HU-178). Solo se agrega; se conserva 180 días.

    Nunca guarda contraseñas, tokens, el polígono, valores de campos, el usuario que se intentó en un inicio de
    sesión fallido ni la IP. `details` lleva solo los nombres de los campos que cambiaron.
    """

    __tablename__ = "activity_log"
    __table_args__ = (
        CheckConstraint(f"outcome in {_in(OUTCOMES)}", name="outcome_valid"),
        CheckConstraint(f"object_type is null or object_type in {_in(OBJECT_TYPES)}", name="object_type_valid"),
        # «Mi actividad» y la bitácora se leen del evento más reciente al más antiguo.
        Index("ix_activity_log_subject_user_id_occurred_at", "subject_user_id", "occurred_at"),
        Index("ix_activity_log_occurred_at", "occurred_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # El mismo identificador de la cabecera `X-Request-ID` y de los logs de la terminal.
    request_id: Mapped[uuid.UUID | None] = mapped_column()
    # Nulo solo en un inicio de sesión fallido con un usuario que no existe. Al borrar una cuenta, sus eventos se
    # borran; en los de un administrador sobre esa cuenta queda nulo de quién eran los datos.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(16))
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40))
    object_type: Mapped[str | None] = mapped_column(String(16))
    object_id: Mapped[uuid.UUID | None] = mapped_column()
    outcome: Mapped[str] = mapped_column(String(8), default="ok", server_default="ok")
    # Obligatorios en las acciones de un administrador sobre datos ajenos.
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support_tickets.ticket_id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class UsageDaily(Base):
    """Contador anónimo de uso para las métricas (HU-170): cuántas consultas hubo por día, tipo, municipio y cultivo.

    No tiene usuario, sesión, IP, hora, fecha de siembra, prioridades, área ni riego, y no se puede unir con
    `activity_log` (R9).
    """

    __tablename__ = "usage_daily"
    __table_args__ = (
        CheckConstraint(f"endpoint in {_in(USAGE_ENDPOINTS)}", name="endpoint_valid"),
        CheckConstraint("count >= 0", name="count_not_negative"),
    )

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(16), primary_key=True)
    municipality_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    crop_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
