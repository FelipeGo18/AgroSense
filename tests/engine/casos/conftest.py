"""Lo común de los casos de referencia del motor (HU-121). Cada caso llama al contrato (`POST /api/v1/rotations`), no a
funciones internas: el motor todavía no existe y su resultado esperado se escribe antes (R4, R5).

Todo dato armado aquí es de EJEMPLO (R5): el clima y los municipios son los de `tests/conftest.py`; el catálogo de cultivos
es el real. Los casos reales sobre `data/published` no van en este PR (se eligen con el dataset 2026.11.11, del PR #62).
"""

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from common.region import region_today

# Municipios de ejemplo de `SAMPLE_CLIMATE` (tests/conftest.py): Samacá es frío (papa apta); Girardot, cálido (papa no apta).
EJEMPLO_FRIO = "15646"
EJEMPLO_CALIDO = "25307"
EJEMPLO_PRIORIDADES = {"water": 3, "soil": 3, "income": 3, "risk": 3}
SOIL_CRITERIA = ["nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion"]

# TODO(HU-062): cuando entre el PR #62, el dataset de ejemplo tiene que publicar también `rotation_rules`.


@pytest.fixture
def datos(dataset_con_clima):
    """El dataset de ejemplo con clima (aptitud posible). Corre hoy: no depende de las reglas de rotación."""
    return dataset_con_clima


@pytest.fixture
def api(datos) -> TestClient:
    return TestClient(app)


@pytest.fixture
def fuentes(datos) -> set[str]:
    """Los `source_id` publicados en `sources` (R8)."""
    return set(pl.read_parquet(datos / "sources.parquet")["source_id"].to_list())


@pytest.fixture
def familias(datos) -> dict[str, tuple[str | None, bool | None]]:
    """De cada cultivo del catálogo: su familia y si fija nitrógeno, tal como la ficha publicada."""
    crops = pl.read_parquet(datos / "crops.parquet")
    return {row["crop_id"]: (row["family"], row["fixes_nitrogen"]) for row in crops.iter_rows(named=True)}


def rotacion(api: TestClient, **campos) -> dict:
    """Consulta `/rotations` con una entrada de ejemplo válida y responde el JSON. Siembra hoy (hora de la región)."""
    cuerpo = {
        "municipality_id": EJEMPLO_FRIO,
        "sowing_date": region_today().isoformat(),
        "previous_crop_ids": [],
        "priorities": EJEMPLO_PRIORIDADES,
        **campos,
    }
    respuesta = api.post("/api/v1/rotations", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()
