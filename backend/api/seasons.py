"""Temporadas: qué se sembró en qué parte de un lote y cuándo se cosechó (HU-165; specs/02-contratos.md).

- `GET` y `POST /api/v1/lots/{lot_id}/seasons`: el historial del lote y una siembra nueva.
- `PATCH` y `DELETE /api/v1/seasons/{season_id}`: registrar la cosecha, corregir o borrar (borrar marca `deleted_at`).

Reglas de área (una sola): la suma de las temporadas en curso nunca pasa del área del lote. Lo cosechado deja su
terreno libre, así que una siembra nueva cabe si su área no pasa del área libre. «Qué había antes» (`follows_season_ids`)
son temporadas cosechadas del mismo lote, con la cosecha igual o anterior a la siembra nueva; una temporada puede venir
de varias (juntar) y tener varias sucesoras (dividir).
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.farm_models import Lot, Season
from backend.accounts.models import User
from backend.api import calc_examples
from backend.api.auth import current_user, require_accounts
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain, request_id_of
from backend.api.lots import _area, _own_lot
from backend.api.season_stage import dataset_or_none, stage_fields, today
from backend.dataset import Dataset
from backend.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["finca"], dependencies=[Depends(require_accounts)], responses=calc_examples.responses(401, 422))

Area = Annotated[float, Field(gt=0, le=100_000)]
LIGHTS = {"green", "yellow", "red", "not_evaluable"}
ACTIONS = {"sow", "other_window", "rotate", "review_data"}
NOT_FOUND = "Esa siembra no existe o no es suya."


class Diagnosis(BaseModel):
    """El diagnóstico que vio el agricultor al sembrar (R4). Todo nulo si no lo consultó."""

    diagnosis_light: str | None = None
    diagnosis_light_default: str | None = None
    diagnosis_action: str | None = None
    diagnosis_weights: dict[str, int] | None = None
    diagnosis_irrigated: bool | None = None
    dataset_version: str | None = Field(None, max_length=40)
    rules_version: str | None = Field(None, max_length=40)


class SeasonCreate(Diagnosis):
    model_config = ConfigDict(extra="forbid")

    crop_id: str = Field(max_length=40)
    sowing_date: date
    # Sin ella, ocupa lo que queda libre del lote.
    area_ha: Area | None = None
    follows_season_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)


class SeasonPatch(BaseModel):
    """Registrar la cosecha o corregir. Lo que no viene no cambia; `harvest_date` nulo deshace la cosecha."""

    model_config = ConfigDict(extra="forbid")

    harvest_date: date | None = None
    crop_id: str | None = Field(None, max_length=40)
    sowing_date: date | None = None
    area_ha: Area | None = None
    follows_season_ids: list[uuid.UUID] | None = Field(None, max_length=20)


class SeasonOut(BaseModel):
    season_id: uuid.UUID
    lot_id: uuid.UUID
    crop_id: str
    area_ha: float
    follows_season_ids: list[uuid.UUID]
    sowing_date: date
    harvest_date: date | None
    diagnosis_light: str | None
    diagnosis_light_default: str | None
    diagnosis_action: str | None
    diagnosis_weights: dict[str, Any] | None
    diagnosis_irrigated: bool | None
    dataset_version: str | None
    rules_version: str | None
    created_at: datetime
    # Solo en curso: la etapa por calendario y la cosecha estimada (HU-220). Nulas si está cosechada o sin etapas.
    stage: str | None = None
    stage_progress_pct: float | None = None
    stage_method: str | None = None
    days_since_sowing: int | None = None
    harvest_estimate: date | None = None
    harvest_basis: str | None = None
    harvest_due: bool | None = None


def season_out(season: Season, dataset: Dataset | None, on: date | None = None) -> SeasonOut:
    data = {field: getattr(season, field) for field in SeasonOut.model_fields if hasattr(season, field)}
    data |= {"area_ha": _area(season.area_ha), "follows_season_ids": list(season.follows_season_ids or [])}
    return SeasonOut(**data | stage_fields(season, dataset, on or today()))


def _invalid(message: str, why: str, code: str = "invalid_input") -> ApiError:
    return ApiError(422, code, message, log=f"Siembra rechazada: {why}")


def _own_season(db: Db, user: User, season_id: uuid.UUID) -> tuple[Season, Lot]:
    row = db.execute(
        select(Season, Lot)
        .join(Lot, Lot.lot_id == Season.lot_id)
        .where(Season.season_id == season_id, Season.deleted_at.is_(None), Lot.user_id == user.user_id, Lot.deleted_at.is_(None))
    ).first()
    if row is None:
        raise ApiError(404, "not_found", NOT_FOUND, log="Siembra no encontrada: no existe, es de otro usuario o está borrada")
    return row[0], row[1]


def _sown(db: Db, lot: Lot, without: Season | None = None) -> Decimal:
    """Lo que ocupan las temporadas en curso del lote (sin contar `without`, si se está corrigiendo)."""
    query = select(func.coalesce(func.sum(Season.area_ha), 0)).where(
        Season.lot_id == lot.lot_id, Season.harvest_date.is_(None), Season.deleted_at.is_(None)
    )
    if without is not None:
        query = query.where(Season.season_id != without.season_id)
    return Decimal(db.scalar(query))


def _check_crop(dataset: Dataset, crop_id: str) -> None:
    if crop_id not in dataset.crops:
        raise _invalid("Ese cultivo no está en el catálogo de AgroSense.", f"el cultivo no está en el catálogo {dataset.rules_version}")


def _check_dates(sowing: date, harvest: date | None) -> None:
    now = today()
    if sowing > now:
        raise _invalid("La fecha de siembra no puede ser posterior a hoy: registre lo que ya sembró.", "siembra en el futuro")
    if harvest is not None and harvest < sowing:
        raise _invalid("La cosecha no puede ser antes de la siembra.", "cosecha antes de la siembra")
    if harvest is not None and harvest > now:
        raise _invalid("La fecha de cosecha no puede ser posterior a hoy.", "cosecha en el futuro")


def _check_follows(db: Db, lot: Lot, ids: list[uuid.UUID], sowing: date, itself: uuid.UUID | None = None) -> None:
    """Cada anterior es una temporada cosechada del mismo lote, cosechada el día de la siembra o antes."""
    if len(set(ids)) != len(ids) or (itself is not None and itself in ids):
        raise _invalid("Lo que había antes no puede repetirse ni ser la misma siembra.", "anteriores repetidas o ella misma")
    if not ids:
        return
    found = {s.season_id: s for s in db.scalars(select(Season).where(Season.season_id.in_(ids), Season.deleted_at.is_(None)))}
    for season_id in ids:
        season = found.get(season_id)
        if season is None or season.lot_id != lot.lot_id:
            raise _invalid("Lo que había antes tiene que ser una siembra de este mismo lote.", "una anterior no es del lote")
        if season.harvest_date is None:
            raise _invalid("Lo que había antes tiene que estar cosechado.", "una anterior sigue en curso")
        if season.harvest_date > sowing:
            raise _invalid("Lo que había antes se cosechó después de esta siembra.", "una anterior se cosechó después")


def _check_area(area: Decimal, free: Decimal) -> None:
    if area > free:
        shown = f"{float(free):.2f}".replace(".", ",")
        raise _invalid(f"No cabe: en el lote quedan {shown} ha libres.", "el área pasa del área libre del lote", "area_exceeds_free")


def _check_diagnosis(body: Diagnosis) -> None:
    for light in (body.diagnosis_light, body.diagnosis_light_default):
        if light is not None and light not in LIGHTS:
            raise _invalid("El diagnóstico guardado no es válido.", "luz desconocida")
    if body.diagnosis_action is not None and body.diagnosis_action not in ACTIONS:
        raise _invalid("El diagnóstico guardado no es válido.", "acción desconocida")


@router.get("/lots/{lot_id}/seasons", responses=calc_examples.responses(404))
def list_seasons(
    lot_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    dataset: Dataset | None = Depends(dataset_or_none),
) -> list[SeasonOut]:
    """El historial del lote: las temporadas sin borrar, de la siembra más reciente a la más antigua. Solo lee: sin
    dataset se ve igual, con la etapa nula (R1), como en el detalle del lote."""
    lot = _own_lot(db, user, lot_id)
    seasons = db.scalars(
        select(Season)
        .where(Season.lot_id == lot.lot_id, Season.deleted_at.is_(None))
        .order_by(Season.sowing_date.desc(), Season.created_at.desc())
    )
    result = [season_out(season, dataset) for season in seasons]
    explain(request, f"Historial del lote consultado: {len(result)} siembras")
    return result


@router.post("/lots/{lot_id}/seasons", status_code=201, responses=calc_examples.responses(404))
def create_season(
    lot_id: uuid.UUID,
    body: SeasonCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    dataset: Dataset = Depends(require_dataset),
) -> SeasonOut:
    """Registra una siembra en una parte del lote, con lo que había antes en ese terreno."""
    lot = _own_lot(db, user, lot_id)
    _check_crop(dataset, body.crop_id)
    _check_dates(body.sowing_date, None)
    _check_diagnosis(body)
    _check_follows(db, lot, body.follows_season_ids, body.sowing_date)
    free = Decimal(lot.area_ha) - _sown(db, lot)
    if free <= 0:
        raise _invalid(
            "El lote no tiene área libre: registre primero la cosecha de lo que tiene sembrado.", "lote sin área libre", "area_exceeds_free"
        )
    area = Decimal(str(body.area_ha)) if body.area_ha is not None else free
    _check_area(area, free)
    season = Season(
        lot_id=lot.lot_id,
        crop_id=body.crop_id,
        area_ha=area,
        follows_season_ids=body.follows_season_ids,
        sowing_date=body.sowing_date,
        **body.model_dump(include=set(Diagnosis.model_fields)),
    )
    db.add(season)
    db.flush()
    activity.record(db, "season.created", request_id=request_id_of(request), actor=user, object_type="season", object_id=season.season_id)
    db.commit()
    db.refresh(season)
    explain(request, f"Siembra registrada: {body.crop_id}")
    return season_out(season, dataset)


@router.patch("/seasons/{season_id}", responses=calc_examples.responses(404))
def update_season(
    season_id: uuid.UUID,
    body: SeasonPatch,
    request: Request,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    dataset: Dataset = Depends(require_dataset),
) -> SeasonOut:
    """Registra la cosecha o corrige la siembra, con las mismas validaciones de registrar. El diagnóstico guardado no
    se recalcula: es el que se vio ese día (R4)."""
    season, lot = _own_season(db, user, season_id)
    changes = {field: getattr(body, field) for field in body.model_fields_set}
    if any(changes.get(field, "") is None for field in ("crop_id", "sowing_date", "area_ha", "follows_season_ids")):
        raise _invalid("El cultivo, la fecha de siembra, el área y lo de antes no pueden quedar vacíos.", "campo vacío")
    crop_id = changes.get("crop_id", season.crop_id)
    sowing = changes.get("sowing_date", season.sowing_date)
    harvest = changes.get("harvest_date", season.harvest_date)
    follows = changes.get("follows_season_ids", list(season.follows_season_ids or []))
    if "crop_id" in changes:
        _check_crop(dataset, crop_id)
    _check_dates(sowing, harvest)
    _check_follows(db, lot, follows, sowing, itself=season.season_id)
    # Las que vienen de esta siembra se sembraron después de su cosecha.
    if harvest is not None:
        later = [
            s
            for s in db.scalars(select(Season).where(Season.lot_id == lot.lot_id, Season.deleted_at.is_(None)))
            if season.season_id in (s.follows_season_ids or [])
        ]
        if any(s.sowing_date < harvest for s in later):
            raise _invalid(
                "Ya hay una siembra registrada en ese terreno antes de esa fecha de cosecha.", "una sucesora es anterior a la cosecha"
            )
    elif "harvest_date" in changes and any(
        season.season_id in (s.follows_season_ids or [])
        for s in db.scalars(select(Season).where(Season.lot_id == lot.lot_id, Season.deleted_at.is_(None)))
    ):
        raise _invalid("No se puede deshacer la cosecha: ya hay una siembra después de ella en ese terreno.", "tiene sucesoras")
    area = Decimal(str(changes["area_ha"])) if "area_ha" in changes else Decimal(season.area_ha)
    # Si sigue (o vuelve a estar) en curso, tiene que caber en lo libre sin contarse a sí misma.
    if harvest is None:
        _check_area(area, Decimal(lot.area_ha) - _sown(db, lot, without=season))
    values = {"crop_id": crop_id, "sowing_date": sowing, "harvest_date": harvest, "follows_season_ids": follows, "area_ha": area}
    changed = [field for field, value in values.items() if field in changes and getattr(season, field) != value]
    for field in changed:
        setattr(season, field, values[field])
    if changed:
        # Registrar la cosecha es una edición más: `details` dice que cambió `harvest_date`.
        activity.record(
            db,
            "season.updated",
            request_id=request_id_of(request),
            actor=user,
            object_type="season",
            object_id=season.season_id,
            fields=changed,
        )
    db.commit()
    db.refresh(season)
    explain(request, f"Siembra actualizada: {', '.join(sorted(changed))}" if changed else "Siembra sin cambios")
    return season_out(season, dataset)


@router.delete("/seasons/{season_id}", status_code=204, responses=calc_examples.responses(404))
def delete_season(season_id: uuid.UUID, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> Response:
    """Borra la siembra: se marca y deja de verse; restaurarla durante 30 días es HU-204 (P1)."""
    season, _ = _own_season(db, user, season_id)
    season.deleted_at = datetime.now(UTC)
    activity.record(db, "season.deleted", request_id=request_id_of(request), actor=user, object_type="season", object_id=season.season_id)
    db.commit()
    explain(request, "Siembra borrada (se puede restaurar durante 30 días)")
    return Response(status_code=204)
