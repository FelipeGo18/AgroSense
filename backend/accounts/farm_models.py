"""Tablas de la finca: lotes y temporadas (specs/02-contratos.md, «Base de datos de cuentas»). M8.

Todo cambio en este archivo necesita su migración: `uv run python -m backend.db.revision "..."` (backend/README.md).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

LIGHTS = "('green', 'yellow', 'red', 'not_evaluable')"
ACTIONS = "('sow', 'other_window', 'rotate', 'review_data')"


class Lot(Base):
    """Un lote del agricultor. La «zona» es su municipio (R7). Borrarlo es reversible durante 30 días (`deleted_at`)."""

    __tablename__ = "lots"
    __table_args__ = (CheckConstraint("area_ha > 0", name="area_positive"),)

    lot_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Borrar al usuario borra sus lotes para siempre (R9).
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    # Código oficial de la unidad territorial (en Colombia, el DIVIPOLA). Se valida contra el catálogo publicado, no aquí.
    municipality_id: Mapped[str] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(60))
    # Polígono GeoJSON en WGS84, dibujado en el mapa; nulo si el usuario aún no lo dibuja.
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    area_ha: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    # Si el lote tiene riego; nulo si no lo ha dicho.
    irrigated: Mapped[bool | None] = mapped_column(Boolean)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    seasons: Mapped[list["Season"]] = relationship(back_populates="lot", cascade="all, delete-orphan", passive_deletes=True)


class Season(Base):
    """Un cultivo en una parte del lote, de la siembra a la cosecha. Guarda el diagnóstico que se vio al sembrar (R4)."""

    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("area_ha > 0", name="area_positive"),
        CheckConstraint("harvest_date is null or harvest_date >= sowing_date", name="harvest_after_sowing"),
        CheckConstraint(f"diagnosis_light is null or diagnosis_light in {LIGHTS}", name="diagnosis_light_valid"),
        CheckConstraint(f"diagnosis_light_default is null or diagnosis_light_default in {LIGHTS}", name="diagnosis_light_default_valid"),
        CheckConstraint(f"diagnosis_action is null or diagnosis_action in {ACTIONS}", name="diagnosis_action_valid"),
    )

    season_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.lot_id", ondelete="CASCADE"), index=True)
    # Se valida contra el catálogo publicado, no aquí.
    crop_id: Mapped[str] = mapped_column(String(40))
    # La parte del lote que ocupa. Las partes son de área, no de forma.
    area_ha: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    # Las temporadas que había antes en ese terreno; vacía si es la primera. Es el historial para las rotaciones.
    follows_season_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid()), server_default=text("'{}'"), default=list)
    sowing_date: Mapped[date] = mapped_column(Date)
    # Nula mientras el cultivo sigue en curso.
    harvest_date: Mapped[date | None] = mapped_column(Date)
    # El diagnóstico que vio el agricultor al sembrar; todo nulo si no lo consultó.
    diagnosis_light: Mapped[str | None] = mapped_column(String(16))
    diagnosis_light_default: Mapped[str | None] = mapped_column(String(16))
    diagnosis_action: Mapped[str | None] = mapped_column(String(16))
    diagnosis_weights: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    diagnosis_irrigated: Mapped[bool | None] = mapped_column(Boolean)
    dataset_version: Mapped[str | None] = mapped_column(String(40))
    rules_version: Mapped[str | None] = mapped_column(String(40))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped[Lot] = relationship(back_populates="seasons")
