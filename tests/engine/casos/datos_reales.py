"""Lo común de los casos de aptitud y diagnóstico (HU-121, PR 2): el dataset publicado y los datos de
EJEMPLO que se arman aquí (R5). Se importa de forma explícita en cada módulo de casos.

Casos REALES: leen `data/published` del repositorio sin modificarlo (`AGROSENSE_DATA_DIR` apunta a esa carpeta con
`monkeypatch`; nada se copia ni se escribe). No fijan una versión del dataset: comparan con la del `manifest.json` (R4).
Casos de EJEMPLO: tablas mínimas armadas con `publish()`, con cifras rotuladas `EJEMPLO_*`.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.settings import get_settings
from common.region import region_today

PUBLICADO = Path(__file__).resolve().parents[3] / "data" / "published"

# Municipios de ejemplo de `tests/conftest.py` (`dataset_con_clima`): Samacá es frío (papa apta); Girardot, cálido (no apta).
EJEMPLO_FRIO = "15646"
EJEMPLO_CALIDO = "25307"
# Un municipio de ejemplo que sí tiene lluvia de IMERG en `ejemplo_dos_lluvias`, y otro (Samacá) que no.
EJEMPLO_CON_IMERG = "15407"


def pendiente(*hus: str, extra: str = ""):
    """`xfail` estricto: cuando la HU entre y el caso pase, la prueba falla hasta quitar la marca (nunca `skip`)."""
    return pytest.mark.xfail(strict=True, reason=f"espera {', '.join(hus)}" if not extra else f"espera {', '.join(hus)} ({extra})")


@pytest.fixture
def datos_reales(monkeypatch) -> Path:
    """`data/published` del repositorio, solo para leer. Gana al aislamiento autouse `no_dataset` de `tests/conftest.py`."""
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(PUBLICADO))
    get_settings.cache_clear()
    return PUBLICADO


def version_publicada() -> str:
    """La `dataset_version` del `manifest.json` publicado: lo que `versions.dataset` debe repetir (R4), sea cual sea."""
    return json.loads((PUBLICADO / "manifest.json").read_text(encoding="utf-8"))["dataset_version"]


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


def publicar_ejemplo(
    carpeta: Path,
    *,
    imerg_en: tuple[str, ...] = (),
    lluvia_mm: float = 60.0,
    helada_anios: int | dict[int, int] | None = None,
    ph: float | None = None,
) -> None:
    """Publica con `publish()` un dataset de EJEMPLO (R5) para el diagnóstico de papa en Samacá y Villa de Leyva.

    - Lluvia (EJEMPLO, igual en todos los meses de 2015 a 2024): NASA POWER (`climate_month`) en los dos municipios, y GPM
      IMERG (`precip_month`) solo en `imerg_en`. Las filas de `sources` de IMERG son las reales del dataset publicado.
    - `helada_anios`: de los 30 años de 1991 a 2020, en cuántos hay tres noches de 1 C (helada: mínima <= 2 C) los primeros
      días de cada mes; en Samacá. Con un `dict` es `{mes: años}` y los meses que no están no tienen heladas. Sin él no hay
      `climate_risk_month` ni `climate_frost_month` (R1). La frecuencia es
      `helada_anios / 30`: 3 años es 10 % (favorable), 9 es 30 % (moderada) y 24 es 80 % (crítica). La máxima es de 18 C.
    - `ph`: el pH de `soil_municipality` en Samacá (franco, la lluvia y el agua no cambian). Sin él no hay suelo (R1).
    Villa de Leyva tiene 12,8 C como Samacá (en `tests/conftest.py` queda a 6 C, sin cultivo apto).
    """
    from pipeline import catalog as crops_catalog
    from pipeline import climate_normals, climate_risk
    from pipeline.build import publish
    from pipeline.sources import dane, dane_mgn, nasa_power
    from tests.conftest import (
        SAMPLE_CLIMATE,
        SAMPLE_META,
        SAMPLE_MUNICIPALITIES,
        SAMPLE_REGION,
        SAMPLE_WARM_MUNICIPALITY,
        sample_boundaries,
    )

    clima_mpio = {**SAMPLE_CLIMATE, EJEMPLO_CON_IMERG: {**SAMPLE_CLIMATE[EJEMPLO_CON_IMERG], "tmean_annual_c": 12.8}}
    municipios = dane.municipalities([*SAMPLE_MUNICIPALITIES, SAMPLE_WARM_MUNICIPALITY], ["15", "25"]).with_columns(
        *(
            pl.col("municipality_id")
            .replace_strict({k: v[c] for k, v in clima_mpio.items()}, default=None, return_dtype=pl.Float64)
            .alias(c)
            for c in ("tmean_annual_c", "altitude_m")
        ),
    )
    catalogo = crops_catalog.load()
    cultivos, etapas, fuentes_catalogo = crops_catalog.build(catalogo)
    reales = tabla(PUBLICADO, "sources").filter(pl.col("source_id").is_in(["imerg", "soilgrids"]))

    dias = [date(1991, 1, 1) + timedelta(days=i) for i in range((date(2020, 12, 31) - date(1991, 1, 1)).days + 1)]

    def anios_con_helada(mes: int) -> int:
        if isinstance(helada_anios, dict):
            return helada_anios.get(mes, 0)
        return helada_anios or 0

    helada = [d.day <= 3 and d.year < 1991 + anios_con_helada(d.month) for d in dias]
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
        **SAMPLE_REGION,
        "frost": {"threshold_c": 2.0, "source_id": "mapa_zarc_2025"},
        "climate_normal": {"first_year": 1991, "last_year": 2020, "min_years": 24, "min_day_share": 0.9, "dry_quantile": 0.2},
    }
    normal = climate_normals.Normal.from_region(region)
    fuente_power = pl.DataFrame([nasa_power.source(clima, {"downloaded_at": "2026-11-14T00:00:00+00:00", "elevations": {}})])
    fuentes = pl.concat(
        [pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)]), fuentes_catalogo, reales, fuente_power],
        how="diagonal_relaxed",
    )

    meses = [(a, m) for a in range(2015, 2025) for m in range(1, 13)]
    power = pl.DataFrame(
        [
            {
                "municipality_id": mpio,
                "year": a,
                "month": m,
                "precip_mm": lluvia_mm,
                "precip_normal_mm": lluvia_mm,
                "precip_dry_mm": lluvia_mm,
                "et0_mm": 80.0,
                "et0_normal_mm": 80.0,
                "soil_wetness_top": None,
                "soil_wetness_root": None,
                "quality": "ok",
                "source_id": "nasa_power",
            }
            for mpio in (EJEMPLO_FRIO, EJEMPLO_CON_IMERG)
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
                "municipality_id": mpio,
                "year": a,
                "month": m,
                "source_id": "imerg",
                "precip_mm": lluvia_mm,
                "precip_normal_mm": lluvia_mm,
                "precip_dry_mm": lluvia_mm,
                "normal_period": "2001-2024",
                "quality": "ok",
            }
            for mpio in imerg_en
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
    suelo = None
    if ph is not None:
        suelo = pl.DataFrame(
            [
                {
                    "municipality_id": EJEMPLO_FRIO,
                    "ph": ph,
                    "ph_p05": ph - 0.3,
                    "ph_p95": ph + 0.3,
                    "soc_g_kg": 30.0,
                    "soc_p05": 25.0,
                    "soc_p95": 35.0,
                    "nitrogen_g_kg": 2.0,
                    "clay_pct": 25.0,
                    "sand_pct": 40.0,
                    "silt_pct": 35.0,
                    "texture_class": "franco",
                    "cells": 100,
                    "quality": "ok",
                    "source_id": "soilgrids",
                }
            ],
            schema={
                "municipality_id": pl.String,
                "ph": pl.Float64,
                "ph_p05": pl.Float64,
                "ph_p95": pl.Float64,
                "soc_g_kg": pl.Float64,
                "soc_p05": pl.Float64,
                "soc_p95": pl.Float64,
                "nitrogen_g_kg": pl.Float64,
                "clay_pct": pl.Float64,
                "sand_pct": pl.Float64,
                "silt_pct": pl.Float64,
                "texture_class": pl.String,
                "cells": pl.Int32,
                "quality": pl.String,
                "source_id": pl.String,
            },
        )
    frost = None
    if helada_anios is not None:
        frost = (climate_risk.climate_risk_month(clima, 2.0, normal), climate_risk.climate_frost_month(clima, 2.0))
    publish(
        region,
        municipios,
        fuentes,
        carpeta,
        sample_boundaries(municipios),
        (catalogo["version"], cultivos, etapas),
        climate=clima if helada_anios is not None else None,
        climate_month=power,
        precip_month=imerg if imerg_en else None,
        frost=frost,
        soil=suelo,
    )


@pytest.fixture
def armar_ejemplo(tmp_path, monkeypatch):
    """Una función que publica un dataset de EJEMPLO con lo que se pida (`publicar_ejemplo`) y devuelve la API sobre él.
    Se puede llamar una vez por prueba."""

    def armar(**datos) -> TestClient:
        carpeta = tmp_path / "published"
        publicar_ejemplo(carpeta, **datos)
        monkeypatch.setenv("AGROSENSE_DATA_DIR", str(carpeta))
        get_settings.cache_clear()
        return TestClient(app)

    return armar


@pytest.fixture
def ejemplo_dos_lluvias(armar_ejemplo) -> TestClient:
    """Dataset de EJEMPLO con las dos lluvias: NASA POWER (`climate_month`) en Samacá y Villa de Leyva, y GPM IMERG
    (`precip_month`) solo en Villa de Leyva. La lluvia es de ejemplo, igual en todos los meses."""
    return armar_ejemplo(imerg_en=(EJEMPLO_CON_IMERG,))
