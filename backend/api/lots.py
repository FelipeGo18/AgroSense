"""Lotes del agricultor: `/api/v1/lots*` (HU-164, HU-169; specs/02-contratos.md, «Cuerpos de cuenta»).

Un lote se dibuja en el mapa (`geometry`, un polígono que cae dentro de su municipio; su área la calcula la API) o se
guarda sin dibujar, con el área escrita a mano (`geometry` nulo). Un lote sin dibujar se puede dibujar después.

Un usuario solo ve y modifica sus propios lotes: uno ajeno, o borrado, responde 404 (igual que uno que no existe).
"""

import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.farm_models import Lot, Season
from backend.accounts.models import User
from backend.api import calc_examples
from backend.api.auth import current_user, require_accounts
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain, request_id_of
from backend.api.lot_geometry import as_geojson, drawn_lot
from backend.dataset import Dataset, DatasetUnavailable, get_dataset
from backend.db.session import get_db
from backend.engine.stages import stage_today

router = APIRouter(prefix="/api/v1", tags=["finca"], dependencies=[Depends(require_accounts)], responses=calc_examples.responses(401, 422))

LotName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
# Mayor que cero y con tope: nadie tiene un lote de más de 100 000 ha, y la columna guarda 4 decimales.
Area = Annotated[float, Field(gt=0, le=100_000)]
NOT_FOUND = "Ese lote no existe o no es suyo."


class LotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: LotName
    municipality_id: str = Field(max_length=12)
    # Obligatoria sin `geometry`; con `geometry`, la calcula la API y se ignora la enviada.
    area_ha: Area | None = None
    # Sí, no, o nulo si todavía no lo sabe.
    irrigated: bool | None = None
    geometry: dict[str, Any] | None = None


class LotPatch(BaseModel):
    """Lo que no viene no cambia. `irrigated` acepta nulo: «Todavía no sé»."""

    model_config = ConfigDict(extra="forbid")

    name: LotName | None = None
    municipality_id: str | None = Field(None, max_length=12)
    area_ha: Area | None = None
    irrigated: bool | None = None
    geometry: dict[str, Any] | None = None


class LotOut(BaseModel):
    lot_id: uuid.UUID
    municipality_id: str
    name: str
    geometry: dict[str, Any] | None
    area_ha: float
    irrigated: bool | None
    created_at: datetime
    updated_at: datetime


class LotListItem(LotOut):
    # Los cultivos en curso, de mayor a menor área, para la fila de Mi finca. Vacía si no hay siembra en curso.
    current_crop_ids: list[str]


class CurrentSeason(BaseModel):
    season_id: uuid.UUID
    crop_id: str
    area_ha: float
    follows_season_ids: list[uuid.UUID]
    sowing_date: date
    days_since_sowing: int
    # La etapa por calendario (HU-220): sale de las etapas del cultivo (`crop_stages`). Sin ellas, nulas (R1).
    stage: str | None = None
    stage_progress_pct: float | None = None
    stage_method: str | None = None
    thermal_data_until: date | None = None
    harvest_estimate: date | None = None
    harvest_basis: str | None = None
    # Ya pasó la cosecha estimada y no se ha registrado la cosecha.
    harvest_due: bool | None = None


class LotDetail(LotOut):
    # Nulo mientras no esté publicado el suelo (HU-181): no se inventa (R1).
    soil: dict[str, Any] | None
    current_seasons: list[CurrentSeason]


def _area(value: Decimal | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _out(lot: Lot) -> dict[str, Any]:
    return {field: getattr(lot, field) for field in LotOut.model_fields} | {"area_ha": _area(lot.area_ha)}


def _current(db: Db, lot: Lot) -> list[Season]:
    """Temporadas en curso del lote: sin cosecha y sin borrar, de mayor a menor área."""
    query = select(Season).where(Season.lot_id == lot.lot_id, Season.harvest_date.is_(None), Season.deleted_at.is_(None))
    return list(db.scalars(query.order_by(Season.area_ha.desc(), Season.sowing_date, Season.season_id)))


def _own_lot(db: Db, user: User, lot_id: uuid.UUID) -> Lot:
    lot = db.scalar(select(Lot).where(Lot.lot_id == lot_id, Lot.user_id == user.user_id, Lot.deleted_at.is_(None)))
    if lot is None:
        raise ApiError(404, "not_found", NOT_FOUND, log="Lote no encontrado: no existe, es de otro usuario o está borrado")
    return lot


def _check_municipality(dataset: Dataset, municipality_id: str) -> None:
    if municipality_id not in dataset.municipalities:
        raise ApiError(
            422,
            "invalid_input",
            "Ese municipio no está entre los de la región de AgroSense.",
            log=f"Lote rechazado: el municipio no está en el catálogo del dataset {dataset.version}",
        )


def _drawn(dataset: Dataset, municipality_id: str, geometry: dict[str, Any]):
    """El contorno validado contra el límite publicado de su municipio. Sin ese límite no se puede validar: 503 (R1)."""
    boundary = dataset.boundaries.get(municipality_id)
    if boundary is None:
        raise ApiError(
            503,
            "dataset_unavailable",
            "Los datos de AgroSense no están disponibles en este momento. Intente de nuevo más tarde.",
            log=f"Contorno sin validar (503) porque el dataset {dataset.version} no trae el límite del municipio",
        )
    return drawn_lot(geometry, boundary, dataset.municipalities[municipality_id].name)


@router.get("/lots")
def list_lots(request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> list[LotListItem]:
    """Los lotes del usuario, del más antiguo al más nuevo. Los borrados no salen (restaurarlos es HU-204, P1)."""
    lots = list(db.scalars(select(Lot).where(Lot.user_id == user.user_id, Lot.deleted_at.is_(None)).order_by(Lot.created_at, Lot.name)))
    explain(request, f"Lotes consultados: {len(lots)}")
    return [LotListItem(**_out(lot), current_crop_ids=[season.crop_id for season in _current(db, lot)]) for lot in lots]


@router.post("/lots", status_code=201)
def create_lot(
    body: LotCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    dataset: Dataset = Depends(require_dataset),
) -> LotOut:
    """Crea un lote, dibujado o con el área escrita a mano. Guarda solo lo mínimo: nombre, municipio, contorno o área y
    riego (R9). La ubicación del lote es un dato personal que nombra el consentimiento (HU-163)."""
    _check_municipality(dataset, body.municipality_id)
    if body.geometry is not None:
        drawn = _drawn(dataset, body.municipality_id, body.geometry)
        geometry, area_ha = as_geojson(drawn.geometry), drawn.area_ha
    elif body.area_ha is not None:
        geometry, area_ha = None, body.area_ha
    else:
        raise ApiError(422, "invalid_input", "Dibuje el lote en el mapa o escriba su área.", log="Lote rechazado: sin contorno ni área")
    lot = Lot(
        user_id=user.user_id,
        municipality_id=body.municipality_id,
        name=body.name,
        geometry=geometry,
        area_ha=Decimal(str(area_ha)),
        irrigated=body.irrigated,
    )
    db.add(lot)
    db.flush()
    activity.record(db, "lot.created", request_id=request_id_of(request), actor=user, object_type="lot", object_id=lot.lot_id)
    db.commit()
    db.refresh(lot)
    explain(request, "Lote creado con su dibujo" if geometry else "Lote creado sin dibujar")
    return LotOut(**_out(lot))


@router.get("/lots/{lot_id}", responses=calc_examples.responses(404))
def get_lot(lot_id: uuid.UUID, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> LotDetail:
    lot = _own_lot(db, user, lot_id)
    today = datetime.now(UTC).date()
    try:
        dataset = get_dataset()
    except DatasetUnavailable:
        # Sin catálogo no hay etapas: el lote se ve igual, con la etapa nula (R1).
        dataset = None
    seasons = []
    for season in _current(db, lot):
        stages = dataset.stages.get(season.crop_id) if dataset else None
        state = stage_today(stages, season.sowing_date, today) if stages else None
        seasons.append(
            CurrentSeason(
                season_id=season.season_id,
                crop_id=season.crop_id,
                area_ha=_area(season.area_ha),
                follows_season_ids=list(season.follows_season_ids or []),
                sowing_date=season.sowing_date,
                days_since_sowing=max((today - season.sowing_date).days, 0),
                stage=state.stage if state else None,
                stage_progress_pct=state.stage_progress_pct if state else None,
                stage_method=state.stage_method if state else None,
                harvest_estimate=state.harvest_estimate if state else None,
                harvest_basis="calendar" if state else None,
                harvest_due=state.harvest_due if state else None,
            )
        )
    explain(request, f"Lote consultado: {len(seasons)} temporadas en curso")
    return LotDetail(**_out(lot), soil=None, current_seasons=seasons)


@router.patch("/lots/{lot_id}", responses=calc_examples.responses(404))
def update_lot(
    lot_id: uuid.UUID,
    body: LotPatch,
    request: Request,
    user: User = Depends(current_user),
    db: Db = Depends(get_db),
    dataset: Dataset = Depends(require_dataset),
) -> LotOut:
    """Cambia el nombre, el municipio, el contorno, el área o el riego. Con contorno, el área sale del dibujo y la enviada
    se ignora; el dibujo no se quita, se corrige. El área no puede quedar por debajo de lo sembrado (422)."""
    lot = _own_lot(db, user, lot_id)
    changes = {field: getattr(body, field) for field in body.model_fields_set}
    if any(changes.get(field, "") is None for field in ("name", "municipality_id", "area_ha", "geometry")):
        raise ApiError(
            422,
            "invalid_input",
            "El nombre, el municipio, el área y el dibujo no pueden quedar vacíos.",
            log="Lote no editado: campo vacío",
        )
    if "municipality_id" in changes:
        _check_municipality(dataset, changes["municipality_id"])
    municipality_id = changes.get("municipality_id", lot.municipality_id)
    # El contorno nuevo, o el que ya tenía si cambió de municipio: siempre tiene que caer dentro del suyo.
    geometry = changes.pop("geometry", None) or (lot.geometry if "municipality_id" in changes else None)
    if geometry is not None:
        drawn = _drawn(dataset, municipality_id, geometry)
        changes["geometry"], changes["area_ha"] = as_geojson(drawn.geometry), drawn.area_ha
    elif lot.geometry is not None:
        # Un lote dibujado tiene el área de su dibujo.
        changes.pop("area_ha", None)
    if "area_ha" in changes:
        sown = db.scalar(
            select(func.coalesce(func.sum(Season.area_ha), 0)).where(
                Season.lot_id == lot.lot_id, Season.harvest_date.is_(None), Season.deleted_at.is_(None)
            )
        )
        if Decimal(str(changes["area_ha"])) < Decimal(sown):
            raise ApiError(
                422,
                "area_below_seasons",
                f"El lote no puede quedar más chico que lo que tiene sembrado: {_area(sown):.2f} ha.".replace(".", ",", 1),
                log="Lote no editado: el área nueva es menor que la de sus temporadas en curso",
            )
        changes["area_ha"] = Decimal(str(changes["area_ha"]))
    changed = [field for field, value in changes.items() if getattr(lot, field) != value]
    for field in changed:
        setattr(lot, field, changes[field])
    if changed:
        activity.record(
            db, "lot.updated", request_id=request_id_of(request), actor=user, object_type="lot", object_id=lot.lot_id, fields=changed
        )
    db.commit()
    db.refresh(lot)
    explain(request, f"Lote actualizado: {', '.join(sorted(changed))}" if changed else "Lote sin cambios: llegó lo mismo que ya tenía")
    return LotOut(**_out(lot))


@router.delete("/lots/{lot_id}", status_code=204, responses=calc_examples.responses(404))
def delete_lot(lot_id: uuid.UUID, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> Response:
    """Borra el lote y sus temporadas: se marcan con la misma hora, para restaurarlos juntos durante 30 días (HU-204)."""
    lot = _own_lot(db, user, lot_id)
    now = datetime.now(UTC)
    lot.deleted_at = now
    for season in db.scalars(select(Season).where(Season.lot_id == lot.lot_id, Season.deleted_at.is_(None))):
        season.deleted_at = now
    activity.record(db, "lot.deleted", request_id=request_id_of(request), actor=user, object_type="lot", object_id=lot.lot_id)
    db.commit()
    explain(request, "Lote borrado con sus temporadas (se puede restaurar durante 30 días)")
    return Response(status_code=204)
