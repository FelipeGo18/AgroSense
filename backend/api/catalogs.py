"""Catálogos del dataset publicado: `/api/v1/catalogs/*` (HU-078; specs/02-contratos.md, «Endpoints»).

Por ahora, los municipios de la región. Los cultivos, el límite y el suelo de cada municipio llegan con sus tablas.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.api.errors import ApiError, explain
from backend.config.logging import get_logger
from backend.dataset import Dataset, DatasetUnavailable, get_dataset

log = get_logger("agrosense.api")

DATASET_UNAVAILABLE = "Los datos de AgroSense no están disponibles en este momento. Intente de nuevo más tarde."


def require_dataset() -> Dataset:
    """El dataset publicado, o 503 `dataset_unavailable` con el motivo en el log. Nunca se inventa un catálogo (R5)."""
    try:
        return get_dataset()
    except DatasetUnavailable as error:
        detail = f"Datos no disponibles (503) porque {error}"
        log.warning("dataset_unavailable", detail=detail)
        raise ApiError(503, "dataset_unavailable", DATASET_UNAVAILABLE, log=detail) from error


router = APIRouter(prefix="/api/v1/catalogs", tags=["catálogos"])


class MunicipalityItem(BaseModel):
    municipality_id: str
    name: str
    department: str
    lat: float | None
    lon: float | None


@router.get("/municipalities")
def municipalities(request: Request, dataset: Dataset = Depends(require_dataset)) -> list[MunicipalityItem]:
    """Los municipios de la región, por departamento y nombre. No usa la base de datos ni guarda nada (R9)."""
    items = sorted(dataset.municipalities.values(), key=lambda m: (m.department, m.name, m.municipality_id))
    explain(request, f"Municipios consultados: {len(items)} del dataset {dataset.version}")
    return [MunicipalityItem(**{field: getattr(m, field) for field in MunicipalityItem.model_fields}) for m in items]
