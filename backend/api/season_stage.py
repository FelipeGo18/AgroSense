"""La etapa de hoy de una temporada en curso (HU-220): una sola función para el detalle del lote y para el historial.

Es una lectura: sale de la fecha de siembra y de las etapas publicadas del cultivo (`crop_stages`); no se guarda ni
escribe nada. Sin dataset, o sin etapas del cultivo (el descanso), la etapa va nula y los días desde la siembra
siguen (R1). Una temporada cosechada no tiene etapa de hoy.
"""

from datetime import UTC, date, datetime
from typing import Any

from backend.accounts.farm_models import Season
from backend.dataset import Dataset, DatasetUnavailable, get_dataset
from backend.engine.stages import stage_today

EMPTY = {
    "stage": None,
    "stage_progress_pct": None,
    "stage_method": None,
    "days_since_sowing": None,
    "harvest_estimate": None,
    "harvest_basis": None,
    "harvest_due": None,
}


def today() -> date:
    return datetime.now(UTC).date()


def dataset_or_none() -> Dataset | None:
    """Para leer lo guardado sin depender de los datos: sin dataset el lote y su historial se ven igual, sin etapa."""
    try:
        return get_dataset()
    except DatasetUnavailable:
        return None


def stage_fields(season: Season, dataset: Dataset | None, on: date) -> dict[str, Any]:
    """Los campos de la etapa de hoy, con los mismos nombres del contrato en `current_seasons` y en el historial."""
    if season.harvest_date is not None:
        return dict(EMPTY)
    stages = dataset.stages.get(season.crop_id) if dataset is not None else None
    if not stages:
        return EMPTY | {"days_since_sowing": max((on - season.sowing_date).days, 0)}
    state = stage_today(stages, season.sowing_date, on)
    return {
        "stage": state.stage,
        "stage_progress_pct": state.stage_progress_pct,
        "stage_method": state.stage_method,
        "days_since_sowing": state.days_since_sowing,
        "harvest_estimate": state.harvest_estimate,
        "harvest_basis": "calendar",
        "harvest_due": state.harvest_due,
    }
