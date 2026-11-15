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

# El frío de ejemplo de `datos_con_heladas` (R5): en cada mes de 1991 a 2020, tres noches de 1 °C (≤ 2 °C, el umbral de
# helada de `region.yaml`) en 24 de los 30 años (todos menos los múltiplos de 5), y 6 °C el resto.
# Frecuencia de heladas = 24 / 30 = 80 %. Con la curva de `frost` en `backend/config/thresholds.yaml`
# ([[0,100],[20,70],[40,40],[100,0]]) vale 40 - 40 * (80 - 40) / (100 - 40) = 13,3, bajo `critical_below: 40`: crítica.
AÑOS_SIN_HELADA = 5


def _republicar(folder, *, rules=None, extra_sources=None, **tablas) -> None:
    """Vuelve a publicar `folder` con el código del pipeline (`publish`): lo que ya tenía más lo que se pida. `publish()`
    solo escribe tablas completas, así que se leen las publicadas y se pasan de nuevo."""
    from pipeline import catalog as crops_catalog
    from pipeline.build import publish
    from tests.conftest import SAMPLE_REGION

    nombres = ("municipalities", "sources", "municipality_boundaries", "crops", "crop_stages")
    leer = {nombre: pl.read_parquet(folder / f"{nombre}.parquet") for nombre in nombres}
    previas = folder / "rotation_rules.parquet"
    if rules is None and previas.exists():
        rules = pl.read_parquet(previas)
    fuentes = leer["sources"] if extra_sources is None else pl.concat([leer["sources"], extra_sources], how="diagonal_relaxed")
    region = {**SAMPLE_REGION, **tablas.pop("region", {})}
    version = crops_catalog.load()["version"]
    publish(
        region,
        leer["municipalities"],
        fuentes,
        folder,
        leer["municipality_boundaries"],
        (version, leer["crops"], leer["crop_stages"]),
        rules=rules,
        **tablas,
    )


@pytest.fixture
def datos(dataset_con_clima):
    """El dataset de ejemplo con clima (aptitud posible) y con las `rotation_rules` reales del catálogo (HU-062), armadas
    con el código del pipeline como en `pipeline/build.py`."""
    from pipeline import catalog as crops_catalog
    from pipeline import rotation_rules

    catalog = crops_catalog.load()
    crops, _, _ = crops_catalog.build(catalog)
    reglas, fuentes_reglas = rotation_rules.build(
        rotation_rules.load(),
        crop_sources=catalog.get("sources") or [],
        known_families=set(crops["family"].drop_nulls().to_list()),
        expected_version=catalog["version"],
    )
    _republicar(dataset_con_clima, rules=reglas, extra_sources=fuentes_reglas)
    return dataset_con_clima


@pytest.fixture
def datos_con_heladas(datos):
    """`datos` con clima diario y heladas de ejemplo (R5) para Samacá (`EJEMPLO_FRIO`), publicadas con `publish()`:
    `climate_day`, `climate_risk_month` y `climate_frost_month`, calculadas con el código de `pipeline.climate_risk` como
    en `frost_tables`. Los demás municipios quedan sin heladas (R1). `tmean_annual_c` sigue siendo la de ejemplo (12,8 °C):
    no se rederiva de este clima. Falta: la oferta (`supply_semester`), que `publish()` todavía no escribe."""
    from datetime import date, timedelta

    from pipeline import climate_normals, climate_risk
    from pipeline.sources import nasa_power

    dias = [date(1991, 1, 1) + timedelta(days=i) for i in range((date(2020, 12, 31) - date(1991, 1, 1)).days + 1)]
    helada = [d.day <= 3 and d.year % AÑOS_SIN_HELADA != 0 for d in dias]
    clima = pl.DataFrame(
        {
            "municipality_id": EJEMPLO_FRIO,
            "date": dias,
            "temp_min_c": [1.0 if h else 6.0 for h in helada],
            "temp_max_c": 18.0,
            "quality": "ok",
            "source_id": nasa_power.SOURCE_ID,
        },
        schema={
            "municipality_id": pl.String,
            "date": pl.Date,
            "temp_min_c": pl.Float64,
            "temp_max_c": pl.Float64,
            "quality": pl.String,
            "source_id": pl.String,
        },
    )
    region = {
        "frost": {"threshold_c": 2.0, "source_id": "mapa_zarc_2025"},
        "climate_normal": {"first_year": 1991, "last_year": 2020, "min_years": 24, "min_day_share": 0.9, "dry_quantile": 0.2},
    }
    normal = climate_normals.Normal.from_region(region)
    riesgo = climate_risk.climate_risk_month(clima, 2.0, normal)
    por_año = climate_risk.climate_frost_month(clima, 2.0)
    assert riesgo["frost_freq_pct"].min() == riesgo["frost_freq_pct"].max() == 80.0  # el cálculo de arriba
    fuente = pl.DataFrame([nasa_power.source(clima, {"downloaded_at": "2026-11-14T00:00:00+00:00", "elevations": {}})])
    _republicar(datos, extra_sources=fuente, region=region, climate=clima, frost=(riesgo, por_año))
    return datos


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
