"""Lo común de los casos de referencia del motor (HU-121). Cada caso llama al contrato (`POST /api/v1/rotations`), no a
funciones internas: el motor todavía no existe y su resultado esperado se escribe antes (R4, R5).

Todo dato armado aquí es de EJEMPLO (R5): el clima y los municipios son los de `tests/conftest.py`; el catálogo de cultivos
es el real. Los casos REALES leen `data/published` del repositorio sin modificarlo (`datos_reales`) y comparan con la versión
de su `manifest.json`, sea cual sea (R4); en los de estrategias todavía no van (se eligen con el dataset 2026.11.11, del PR #62).
"""

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.settings import get_settings
from common.region import region_today

PUBLICADO = Path(__file__).resolve().parents[3] / "data" / "published"

# Municipios de ejemplo de `SAMPLE_CLIMATE` (tests/conftest.py): Samacá es frío (papa apta); Girardot, cálido (papa no apta).
EJEMPLO_FRIO = "15646"
EJEMPLO_CALIDO = "25307"
# Un municipio de ejemplo que sí tiene lluvia de IMERG en `ejemplo_dos_lluvias`, y otro (Samacá) que no.
EJEMPLO_CON_IMERG = "15407"
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


def reglas_del_catalogo():
    """Las `rotation_rules` reales del catálogo (HU-062) y sus fuentes, armadas con el código del pipeline como en
    `pipeline/build.py`."""
    from pipeline import catalog as crops_catalog
    from pipeline import rotation_rules

    catalog = crops_catalog.load()
    crops, _, _ = crops_catalog.build(catalog)
    return rotation_rules.build(
        rotation_rules.load(),
        crop_sources=catalog.get("sources") or [],
        known_families=set(crops["family"].drop_nulls().to_list()),
        expected_version=catalog["version"],
    )


@pytest.fixture
def datos(dataset_con_clima):
    """El dataset de ejemplo con clima (aptitud posible) y con las `rotation_rules` reales del catálogo (HU-062)."""
    reglas, fuentes_reglas = reglas_del_catalogo()
    _republicar(dataset_con_clima, rules=reglas, extra_sources=fuentes_reglas)
    return dataset_con_clima


def _publicar_heladas(datos, *, con_helada, frecuencia: float):
    """Publica en `datos` el clima diario de Samacá con tres noches de 1 °C los primeros días de cada mes de los años para los
    que `con_helada(año)` es verdadero, y comprueba que la frecuencia de heladas sea `frecuencia` (%). Ejemplo (R5)."""
    from datetime import date, timedelta

    from pipeline import climate_normals, climate_risk
    from pipeline.sources import nasa_power

    dias = [date(1991, 1, 1) + timedelta(days=i) for i in range((date(2020, 12, 31) - date(1991, 1, 1)).days + 1)]
    helada = [d.day <= 3 and con_helada(d.year) for d in dias]
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
    assert riesgo["frost_freq_pct"].min() == riesgo["frost_freq_pct"].max() == frecuencia  # el cálculo de arriba
    fuente = pl.DataFrame([nasa_power.source(clima, {"downloaded_at": "2026-11-14T00:00:00+00:00", "elevations": {}})])
    _republicar(datos, extra_sources=fuente, region=region, climate=clima, frost=(riesgo, por_año))
    return datos


@pytest.fixture
def datos_con_heladas_moderadas(datos):
    """`datos` con heladas de ejemplo (R5) en 9 de los 30 años en cada mes (30 %): `frost` es moderada, no crítica
    (curva de `thresholds.yaml`: 70 en 20 % y 40 en 40 %). Ningún ciclo es de alto riesgo, pero los cultivos sensibles bajan el
    `risk` de su estrategia frente al descanso. El número depende de la siembra: dentro de un año (desde enero) son 9 de 30 años,
    30 %, y `frost` 55. Con la arveja sembrada el 16 de nov de 2026 su etapa media y la final caen de enero a marzo del año
    siguiente, la serie por año de siembra pierde el último año y quedan 8 de 29 (28 %): `frost` 59, y ese es su `risk`."""
    return _publicar_heladas(datos, con_helada=lambda año: año % 10 in (1, 2, 3), frecuencia=30.0)


@pytest.fixture
def datos_con_heladas(datos):
    """`datos` con clima diario y heladas de ejemplo (R5) para Samacá (`EJEMPLO_FRIO`), publicadas con `publish()`:
    `climate_day`, `climate_risk_month` y `climate_frost_month`, calculadas con el código de `pipeline.climate_risk` como
    en `frost_tables`. Los demás municipios quedan sin heladas (R1). `tmean_annual_c` sigue siendo la de ejemplo (12,8 °C):
    no se rederiva de este clima. Falta: la oferta (`supply_semester`), que `publish()` todavía no escribe."""
    return _publicar_heladas(datos, con_helada=lambda año: año % AÑOS_SIN_HELADA != 0, frecuencia=80.0)


# Contorno del lote de ejemplo (dos celdas de la rejilla de `datos_con_suelo`).
CONTORNO_LOTE = {
    "type": "Polygon",
    "coordinates": [[[-73.487, 5.4905], [-73.483, 5.4905], [-73.483, 5.492], [-73.487, 5.492], [-73.487, 5.4905]]],
}


@pytest.fixture
def datos_con_suelo(datos):
    """`datos` con suelo de EJEMPLO (R5): el del municipio de Samacá (pH 6,0, carbono orgánico bajo: 20 g/kg, bajo los 29 de
    `materia_organica_ciclos`) y el de las dos celdas de la rejilla bajo `CONTORNO_LOTE`, con otro pH (6,3 de mediana) para que se
    note de cuál de los dos sale. La pendiente es de 2 % (sin erosión). Cifras inventadas, como en `tests/test_endpoint_rotaciones.py`."""
    from backend.dataset import SOIL_COLUMNS
    from common.grid import cell_id

    filas = [
        {
            "cell_id": cell_id(5.49125, lon),
            "altitude_m": 2700.0,
            "slope_pct": 2.0,
            **dict.fromkeys(SOIL_COLUMNS, 10.0),
            "ph": ph,
            "ph_p05": ph - 0.2,
            "ph_p95": ph + 0.2,
            "soc_g_kg": 20.0,
            "soc_p05": 15.0,
            "soc_p95": 25.0,
            "texture_class": "franco",
            "quality": "ok",
            "source_ids": ["soilgrids"],
        }
        for lon, ph in [(-73.48375, 6.2), (-73.48625, 6.4)]
    ]
    pl.DataFrame(filas).write_parquet(datos / "grid_cells.parquet")
    municipio = {
        "municipality_id": EJEMPLO_FRIO,
        **dict.fromkeys(SOIL_COLUMNS, 10.0),
        "ph": 6.0,
        "ph_p05": 5.7,
        "ph_p95": 6.3,
        "soc_g_kg": 20.0,
        "soc_p05": 15.0,
        "soc_p95": 25.0,
        "texture_class": "franco",
        "cells": 30,
        "quality": "ok",
        "source_id": "soilgrids",
    }
    pl.DataFrame([municipio]).write_parquet(datos / "soil_municipality.parquet")
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
    """El JSON del diagnóstico; falla si la respuesta no es 200."""
    respuesta = consulta(cliente, **campos)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture
def cliente(dataset_con_clima) -> TestClient:
    """La API sobre el dataset de EJEMPLO con clima (`tests/conftest.py`): Samacá apta para papa, Girardot no."""
    return TestClient(app)


def _oferta_de_ejemplo(cultivos: pl.DataFrame, cambio_pct: float) -> pl.DataFrame:
    """`supply_semester` de EJEMPLO (R5): 2025 A y B, 50 ha sembradas y el cambio de área dado, para Samacá y cada cultivo."""
    filas = [
        {
            "municipality_id": EJEMPLO_FRIO,
            "crop_id": cultivo,
            "year": 2025,
            "semester": semestre,
            "source_id": "eva",
            "planted_ha": 50.0,
            "harvested_ha": None,
            "production_t": None,
            "yield_t_ha": None,
            "planted_change_pct": cambio_pct,
            "dept_share_pct": None,
            "preliminary": False,
            "quality": "ok",
        }
        for cultivo in cultivos.filter(pl.col("kind") == "crop")["crop_id"].to_list()
        for semestre in ("A", "B")
    ]
    from pipeline import schema

    return pl.DataFrame(filas, schema={col: spec.dtype for col, spec in schema.TABLES["supply_semester"].columns.items()})


def publicar_ejemplo(
    carpeta: Path,
    *,
    imerg_en: tuple[str, ...] = (),
    lluvia_mm: float | dict[int, float] = 60.0,
    helada_anios: int | dict[int, int | range] | None = None,
    ph: float | None = None,
    reglas: bool = False,
    precios: dict[str, int] | None = None,
    oferta_cambio_pct: float | None = None,
) -> None:
    """Publica con `publish()` un dataset de EJEMPLO (R5) para el diagnóstico de papa en Samacá y Villa de Leyva.
    - Lluvia (EJEMPLO, de 2015 a 2024; igual en todos los meses, o con un `dict` `{mes: mm}` donde los meses que faltan valen 60):
      NASA POWER (`climate_month`) en los dos municipios, y GPM IMERG (`precip_month`) solo en `imerg_en`. Las filas de
      `sources` de IMERG son las reales del dataset publicado.
    - `helada_anios`: de los 30 años de 1991 a 2020, en cuántos hay tres noches de 1 C (helada: mínima <= 2 C) los primeros
      días de cada mes; en Samacá. Con un `dict` es `{mes: años}` y los meses que no están no tienen heladas; los `años` son un
      número (los primeros N años desde 1991) o un `range` de años (por ejemplo `range(1996, 2001)`, para que cada mes
      tenga heladas en años distintos). Sin él no hay
      `climate_risk_month` ni `climate_frost_month` (R1). La frecuencia es
      `helada_anios / 30`: 3 años es 10 % (favorable), 9 es 30 % (moderada) y 24 es 80 % (crítica). La máxima es de 18 C.
    - `ph`: el pH de `soil_municipality` en Samacá (franco, la lluvia y el agua no cambian). Sin él no hay suelo (R1).
    - `reglas`: publica también las `rotation_rules` del catálogo (hacen falta para `/rotations`).
    - `precios`: `{cultivo: años por encima}` de EJEMPLO (R5). Publica `market_month` de la central `9` (la de Boyacá en
      `department_markets`) con 5 años (2021 a 2025), `years_above` = el valor y `years_below` = 5 - el valor, igual en los doce
      meses, para que el valor esperado no dependa del mes de la cosecha. Un cultivo que no está no tiene historia (R1).
    - `oferta_cambio_pct`: publica `supply_semester` de EJEMPLO (2025, A y B, 50 ha, ese cambio de área) para Samacá y todos los
      cultivos. Sin él no hay oferta (R1).
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
    ids = ["imerg", "soilgrids", *(["dane_sipsa"] if precios is not None else []), *(["eva"] if oferta_cambio_pct is not None else [])]
    reales = tabla(PUBLICADO, "sources").filter(pl.col("source_id").is_in(ids))
    reglas_tabla = fuentes_reglas = None
    if reglas:
        reglas_tabla, fuentes_reglas = reglas_del_catalogo()
        reales = pl.concat([reales, fuentes_reglas], how="diagonal_relaxed")

    dias = [date(1991, 1, 1) + timedelta(days=i) for i in range((date(2020, 12, 31) - date(1991, 1, 1)).days + 1)]

    def anios_con_helada(mes: int) -> range:
        años = helada_anios.get(mes, 0) if isinstance(helada_anios, dict) else (helada_anios or 0)
        return años if isinstance(años, range) else range(1991, 1991 + años)

    helada = [d.day <= 3 and d.year in anios_con_helada(d.month) for d in dias]
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
        "region": {**SAMPLE_REGION["region"], "department_markets": {"15": "9"}, "markets": {"9": "Tunja (ejemplo)"}},
    }
    normal = climate_normals.Normal.from_region(region)
    fuente_power = pl.DataFrame([nasa_power.source(clima, {"downloaded_at": "2026-11-14T00:00:00+00:00", "elevations": {}})])
    fuentes = pl.concat(
        [pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)]), fuentes_catalogo, reales, fuente_power],
        how="diagonal_relaxed",
    )

    meses = [(a, m) for a in range(2015, 2025) for m in range(1, 13)]

    def lluvia_en(mes: int) -> float:
        return lluvia_mm.get(mes, 60.0) if isinstance(lluvia_mm, dict) else lluvia_mm

    power = pl.DataFrame(
        [
            {
                "municipality_id": mpio,
                "year": a,
                "month": m,
                "precip_mm": lluvia_en(m),
                "precip_normal_mm": lluvia_en(m),
                "precip_dry_mm": lluvia_en(m),
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
                "precip_mm": lluvia_en(m),
                "precip_normal_mm": lluvia_en(m),
                "precip_dry_mm": lluvia_en(m),
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
        rules=reglas_tabla,
        supply=_oferta_de_ejemplo(cultivos, oferta_cambio_pct) if oferta_cambio_pct is not None else None,
    )
    if precios is not None:
        # `publish()` solo escribe `market_month` desde los precios diarios de SIPSA: aquí se arma la tabla de EJEMPLO ya hecha.
        from pipeline import schema

        filas = [
            {
                "crop_id": cultivo,
                "market_id": "9",
                "month": mes,
                "product_id": f"{cultivo}-ejemplo",
                "price_cop_kg": 1000,
                "price_year": 2025,
                "volume_t": None,
                "seasonal_index": 1.0,
                "years": 5,
                "years_above": arriba,
                "years_below": 5 - arriba,
                "first_year": 2021,
                "last_year": 2025,
                "quality": "ok",
                "source_id": "dane_sipsa",
            }
            for cultivo, arriba in sorted(precios.items())
            for mes in range(1, 13)
        ]
        columnas = {col: spec.dtype for col, spec in schema.TABLES["market_month"].columns.items()}
        pl.DataFrame(filas, schema=columnas).write_parquet(carpeta / "market_month.parquet")


@pytest.fixture
def armar_ejemplo(tmp_path, monkeypatch):
    """Una función que publica un dataset de EJEMPLO con lo que se pida (`publicar_ejemplo`) y devuelve la API sobre él.
    Se puede llamar una vez por prueba."""

    def armar(**datos) -> TestClient:
        carpeta = tmp_path / "published"
        publicar_ejemplo(carpeta, **datos)
        if datos.get("oferta_cambio_pct") is not None:
            # `tests/conftest.py` parchea la región de ejemplo en `climate_signals`, pero la oferta lee `get_signal_sources`
            # de su propio módulo: se parcha igual para que `pruebas` tenga sus fuentes por señal (HU-072).
            from backend.api import supply_signal
            from common import signal_sources

            monkeypatch.setattr(supply_signal, "get_signal_sources", signal_sources.get_signal_sources)
        monkeypatch.setenv("AGROSENSE_DATA_DIR", str(carpeta))
        get_settings.cache_clear()
        return TestClient(app)

    return armar


@pytest.fixture
def armar_ejemplos(tmp_path, monkeypatch):
    """Como `armar_ejemplo`, pero con varios datasets de EJEMPLO a la vez, cada uno en su carpeta: `armar_ejemplos(sin={...},
    con={...})` publica uno por nombre (los argumentos son los de `publicar_ejemplo`) y devuelve `usar(nombre)`, que apunta la API
    a ese y devuelve el cliente. Para comparar la misma consulta sobre datos distintos (R4)."""
    from backend.api import supply_signal
    from common import signal_sources

    # `tests/conftest.py` parchea la región de ejemplo en `climate_signals`, pero la oferta lee `get_signal_sources` de su propio
    # módulo: se parcha igual para que `pruebas` tenga sus fuentes por señal (HU-072).
    monkeypatch.setattr(supply_signal, "get_signal_sources", signal_sources.get_signal_sources)
    carpetas = {}

    def armar(**datasets: dict) -> Callable[[str], TestClient]:
        for nombre, datos in datasets.items():
            carpetas[nombre] = tmp_path / nombre
            publicar_ejemplo(carpetas[nombre], **datos)

        def usar(nombre: str) -> TestClient:
            monkeypatch.setenv("AGROSENSE_DATA_DIR", str(carpetas[nombre]))
            get_settings.cache_clear()
            return TestClient(app)

        return usar

    return armar


@pytest.fixture
def ejemplo_dos_lluvias(armar_ejemplo) -> TestClient:
    """Dataset de EJEMPLO con las dos lluvias: NASA POWER (`climate_month`) en Samacá y Villa de Leyva, y GPM IMERG
    (`precip_month`) solo en Villa de Leyva. La lluvia es de ejemplo, igual en todos los meses."""
    return armar_ejemplo(imerg_en=(EJEMPLO_CON_IMERG,))


@pytest.fixture
def hoy_fijo(monkeypatch) -> date:
    """Fija el «hoy» de la región en el 16 de noviembre de 2026 (`common.region.region_today`). Solo para un caso cuyo orden de
    ventanas parte del mes en curso: las mejores ventanas son las de los próximos doce meses, así que cuáles quedan entre las tres
    primeras depende del día. Los demás casos no lo usan y dan lo mismo cualquier día (R4)."""
    ahora = datetime(2026, 11, 16, 17, 0, tzinfo=UTC)

    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return ahora if tz is None else ahora.astimezone(tz)

    monkeypatch.setattr("common.region.datetime", Reloj)
    return ahora.date()
