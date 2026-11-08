"""Catálogos del dataset publicado: `/api/v1/catalogs/*` (HU-078; specs/02-contratos.md, «Endpoints»).

Los municipios de la región, su límite y los cultivos del catálogo agronómico. El suelo llega con su tabla (HU-181).
"""

from typing import Any

import shapely.geometry
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.api.errors import ApiError, explain
from backend.config.logging import get_logger
from backend.dataset import Dataset, DatasetUnavailable, get_dataset

log = get_logger("agrosense.api")

# La fuente de los límites municipales (pipeline/sources/dane_mgn.py).
BOUNDARY_SOURCE = "dane_mgn_2025"
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


@router.get("/municipalities/{municipality_id}/boundary")
def boundary(municipality_id: str, request: Request, dataset: Dataset = Depends(require_dataset)) -> dict[str, Any]:
    """El límite del municipio en GeoJSON (WGS84), para centrar el mapa y validar el dibujo del lote en la web."""
    municipality = dataset.municipalities.get(municipality_id)
    if municipality is None:
        raise ApiError(
            404,
            "not_found",
            "Ese municipio no está entre los de la región de AgroSense.",
            log="Límite pedido de un municipio fuera del catálogo",
        )
    geometry = dataset.boundaries.get(municipality_id)
    if geometry is None:
        detail = f"Datos no disponibles (503) porque el dataset {dataset.version} no trae el límite de ese municipio"
        log.warning("dataset_unavailable", detail=detail)
        raise ApiError(503, "dataset_unavailable", DATASET_UNAVAILABLE, log=detail)
    explain(request, f"Límite del municipio consultado (dataset {dataset.version})")
    return {
        "type": "Feature",
        "properties": {"municipality_id": municipality_id, "name": municipality.name, "source_id": BOUNDARY_SOURCE},
        "geometry": shapely.geometry.mapping(geometry),
    }


class CropItem(BaseModel):
    crop_id: str
    name_es: str
    kind: str
    archetype: str | None
    family: str | None
    cycle_months: float | None


@router.get("/crops")
def crops(request: Request, dataset: Dataset = Depends(require_dataset)) -> list[CropItem]:
    """Los cultivos del catálogo, con lo que la web necesita para elegir y dibujar. La ficha completa la usa el motor."""
    if not dataset.crops:
        detail = f"Datos no disponibles (503) porque el dataset {dataset.version} no trae el catálogo de cultivos"
        log.warning("dataset_unavailable", detail=detail)
        raise ApiError(503, "dataset_unavailable", DATASET_UNAVAILABLE, log=detail)
    explain(request, f"Cultivos consultados: {len(dataset.crops)} del catálogo {dataset.rules_version}")
    return [CropItem(**{field: crop.get(field) for field in CropItem.model_fields}) for crop in dataset.crops.values()]
