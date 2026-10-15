"""`GET /api/v1/version`: qué versiones y qué criterio está usando AgroSense (HU-122, HU-198).

El dataset, la región y las fuentes salen del `manifest.json` publicado; las reglas agronómicas todavía no existen y
vienen nulas. Sin dataset publicado, sus campos vienen nulos o vacíos, nunca inventados (R5): el criterio sí está.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.api import errors
from backend.config.weights import get_default_weights
from backend.dataset import DatasetUnavailable, get_dataset

router = APIRouter(prefix="/api/v1", tags=["estado"])


class Version(BaseModel):
    """Lo que muestra «¿Cómo funciona y de dónde sale esto?» y lo que necesita la web antes de consultar."""

    dataset_version: str | None
    rules_version: str | None
    created_at: datetime | None
    region: str | None
    # El peso por defecto de 0 a 5 de cada señal: el criterio de AgroSense.
    default_weights: dict[str, int]
    # Versión de `weights.yaml` y por qué pesa lo que pesa cada señal (criterio del equipo, no dato agronómico).
    weights_version: str
    weights_reasons: dict[str, str]
    sources: list[dict[str, Any]]


@router.get("/version")
def version(request: Request) -> Version:
    """No usa la base de datos ni guarda nada: responde aunque las cuentas o el dataset no estén."""
    defaults = get_default_weights()
    try:
        dataset = get_dataset()
    except DatasetUnavailable as error:
        errors.explain(request, f"Versiones consultadas: pesos por defecto {defaults.version}; sin dataset porque {error}")
        dataset = None
    else:
        errors.explain(request, f"Versiones consultadas: dataset {dataset.version}, pesos por defecto {defaults.version}")
    return Version(
        dataset_version=dataset.version if dataset else None,
        rules_version=dataset.rules_version if dataset else None,
        created_at=dataset.created_at if dataset else None,
        region=dataset.region.get("name") if dataset else None,
        default_weights=defaults.weights,
        weights_version=defaults.version,
        weights_reasons=defaults.reasons,
        sources=dataset.sources if dataset else [],
    )
