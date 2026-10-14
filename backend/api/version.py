"""`GET /api/v1/version`: qué versiones y qué criterio está usando AgroSense (HU-122, HU-198).

Por ahora solo existe el criterio: los pesos por defecto de las señales. El dataset, las reglas, la región y las
fuentes llegan con el pipeline y el catálogo; mientras tanto esos campos vienen nulos o vacíos, nunca inventados (R5).
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.api import errors
from backend.config.weights import get_default_weights

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
    """No usa la base de datos ni guarda nada: responde aunque las cuentas estén apagadas."""
    defaults = get_default_weights()
    errors.explain(request, f"Versiones consultadas: pesos por defecto {defaults.version}; todavía no hay dataset ni reglas publicados")
    return Version(
        dataset_version=None,
        rules_version=None,
        created_at=None,
        region=None,
        default_weights=defaults.weights,
        weights_version=defaults.version,
        weights_reasons=defaults.reasons,
        sources=[],
    )
