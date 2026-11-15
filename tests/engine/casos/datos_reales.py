"""Lo común de los casos de aptitud y diagnóstico (HU-121, PR 2): el dataset publicado, su versión fijada y los datos de
EJEMPLO que se arman aquí (R5). Se importa de forma explícita en cada módulo de casos.

Casos REALES: leen `data/published` del repositorio sin modificarlo (`AGROSENSE_DATA_DIR` apunta a esa carpeta con
`monkeypatch`; nada se copia ni se escribe) y fijan la versión con la que se calculó su resultado esperado (R4).
Casos de EJEMPLO: tablas mínimas armadas con `publish()`, con cifras rotuladas `EJEMPLO_*`.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.settings import get_settings
from common.region import region_today

PUBLICADO = Path(__file__).resolve().parents[3] / "data" / "published"
# La `dataset_version` con la que se calcularon a mano los valores esperados de los casos reales.
VERSION_CASOS_REALES = "2026.11.18"

# Municipios de ejemplo de `tests/conftest.py` (`dataset_con_clima`): Samacá es frío (papa apta); Girardot, cálido (no apta).
EJEMPLO_FRIO = "15646"
EJEMPLO_CALIDO = "25307"
# Un municipio de ejemplo que sí tiene lluvia de IMERG en `ejemplo_dos_lluvias`, y otro (Samacá) que no.
EJEMPLO_CON_IMERG = "15407"

# HU de las que dependen los casos pendientes (`reason` de cada `xfail`). Son todas las que faltan, no solo la primera.
SENALES = ("HU-071", "HU-072", "HU-073", "HU-074", "HU-077", "HU-190")


def pendiente(*hus: str, extra: str = ""):
    """`xfail` estricto: cuando la HU entre y el caso pase, la prueba falla hasta quitar la marca (nunca `skip`)."""
    return pytest.mark.xfail(strict=True, reason=f"espera {', '.join(hus)}" if not extra else f"espera {', '.join(hus)} ({extra})")


@pytest.fixture
def version_fijada() -> str:
    """Falla, no se salta, si el dataset publicado no es el de `VERSION_CASOS_REALES`."""
    version = json.loads((PUBLICADO / "manifest.json").read_text(encoding="utf-8"))["dataset_version"]
    if version != VERSION_CASOS_REALES:
        pytest.fail(
            f"El dataset publicado cambió a {version}; los casos reales se calcularon con {VERSION_CASOS_REALES}: "
            "recalcule los valores esperados (HU-121)",
            pytrace=False,
        )
    return version


@pytest.fixture
def datos_reales(version_fijada, monkeypatch) -> Path:
    """`data/published` del repositorio, solo para leer. Gana al aislamiento autouse `no_dataset` de `tests/conftest.py`."""
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(PUBLICADO))
    get_settings.cache_clear()
    return PUBLICADO


def tabla(datos: Path, nombre: str) -> pl.DataFrame:
    return pl.read_parquet(datos / f"{nombre}.parquet")


def valor(datos: Path, nombre: str, llave: str, id_: str, columna: str):
    """La columna de la fila de `nombre` cuya llave es `id_`; falla si la fila no está (un caso real no inventa)."""
    filas = tabla(datos, nombre).filter(pl.col(llave) == id_)
    assert filas.height == 1, f"{nombre}.{llave}={id_} no tiene exactamente una fila"
    return filas[columna][0]


def consulta(cliente: TestClient, **campos):
    """`POST /diagnostics` con una entrada válida: papa en Samacá, sembrando hoy (hora de la región)."""
    cuerpo = {"municipality_id": EJEMPLO_FRIO, "crop_id": "papa", "sowing_date": region_today().isoformat(), **campos}
    return cliente.post("/api/v1/diagnostics", json=cuerpo)


def diagnostico(cliente: TestClient, **campos) -> dict:
    """El JSON del diagnóstico; si el motor aún no existe, falla aquí con el 501 (la razón del `xfail`)."""
    respuesta = consulta(cliente, **campos)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture
def cliente(dataset_con_clima) -> TestClient:
    """La API sobre el dataset de EJEMPLO con clima (`tests/conftest.py`): Samacá apta para papa, Girardot no."""
    return TestClient(app)


@pytest.fixture
def ejemplo_dos_lluvias(tmp_path, monkeypatch) -> TestClient:
    """Dataset de EJEMPLO con las dos lluvias: NASA POWER (`climate_month`) en Samacá y GPM IMERG (`precip_month`) solo en
    el otro municipio (Villa de Leyva). La lluvia es de ejemplo, igual en todos los meses; las filas de `sources` de IMERG y de
    NASA POWER son las reales del dataset publicado."""
    from pipeline import catalog as crops_catalog
    from pipeline.build import publish
    from pipeline.sources import dane, dane_mgn
    from tests.conftest import (
        SAMPLE_CLIMATE,
        SAMPLE_META,
        SAMPLE_MUNICIPALITIES,
        SAMPLE_REGION,
        SAMPLE_WARM_MUNICIPALITY,
        sample_boundaries,
    )

    municipios = dane.municipalities([*SAMPLE_MUNICIPALITIES, SAMPLE_WARM_MUNICIPALITY], ["15", "25"]).with_columns(
        *(
            pl.col("municipality_id")
            .replace_strict({k: v[c] for k, v in SAMPLE_CLIMATE.items()}, default=None, return_dtype=pl.Float64)
            .alias(c)
            for c in ("tmean_annual_c", "altitude_m")
        ),
    )
    catalogo = crops_catalog.load()
    cultivos, etapas, fuentes_catalogo = crops_catalog.build(catalogo)
    reales = tabla(PUBLICADO, "sources").filter(pl.col("source_id").is_in(["imerg", "nasa_power"]))
    fuentes = pl.concat(
        [pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)]), fuentes_catalogo, reales], how="diagonal_relaxed"
    )

    meses = [(a, m) for a in range(2015, 2025) for m in range(1, 13)]
    EJEMPLO_LLUVIA_MM = 60.0
    power = pl.DataFrame(
        [
            {
                "municipality_id": EJEMPLO_FRIO,
                "year": a,
                "month": m,
                "precip_mm": EJEMPLO_LLUVIA_MM,
                "precip_normal_mm": EJEMPLO_LLUVIA_MM,
                "precip_dry_mm": EJEMPLO_LLUVIA_MM,
                "et0_mm": 80.0,
                "et0_normal_mm": 80.0,
                "soil_wetness_top": None,
                "soil_wetness_root": None,
                "quality": "ok",
                "source_id": "nasa_power",
            }
            for a, m in meses
        ],
        schema={
            "municipality_id": pl.String,
            "year": pl.Int16,
            "month": pl.Int8,
            "precip_mm": pl.Float64,
            "precip_normal_mm": pl.Float64,
            "precip_dry_mm": pl.Float64,
            "et0_mm": pl.Float64,
            "et0_normal_mm": pl.Float64,
            "soil_wetness_top": pl.Float64,
            "soil_wetness_root": pl.Float64,
            "quality": pl.String,
            "source_id": pl.String,
        },
    )
    imerg = pl.DataFrame(
        [
            {
                "municipality_id": EJEMPLO_CON_IMERG,
                "year": a,
                "month": m,
                "source_id": "imerg",
                "precip_mm": EJEMPLO_LLUVIA_MM,
                "precip_normal_mm": EJEMPLO_LLUVIA_MM,
                "precip_dry_mm": EJEMPLO_LLUVIA_MM,
                "normal_period": "2001-2024",
                "quality": "ok",
            }
            for a, m in meses
        ],
        schema={
            "municipality_id": pl.String,
            "year": pl.Int16,
            "month": pl.Int8,
            "source_id": pl.String,
            "precip_mm": pl.Float64,
            "precip_normal_mm": pl.Float64,
            "precip_dry_mm": pl.Float64,
            "normal_period": pl.String,
            "quality": pl.String,
        },
    )
    folder = tmp_path / "published"
    publish(
        SAMPLE_REGION,
        municipios,
        fuentes,
        folder,
        sample_boundaries(municipios),
        (catalogo["version"], cultivos, etapas),
        climate_month=power,
        precip_month=imerg,
    )
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()
    return TestClient(app)
