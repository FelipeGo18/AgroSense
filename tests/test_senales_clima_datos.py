"""Los datos de las señales de heladas y calor (HU-077, HU-190): las tablas del clima en el dataset, el periodo normal
del manifiesto y el aviso de `catalog/sources.yaml`, leídos por la API y pasados al motor ya resueltos (R6). Usa el
dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5) y el de las pruebas sin clima."""

import math
from dataclasses import replace
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from backend.api.climate_signals import climate_normal, frost_for, heat_for, heat_months
from backend.config.thresholds import load_thresholds
from backend.dataset import load
from backend.engine.heat_signal import HeatMonth
from backend.engine.sensitive_signal import ClimateNormal
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from backend.engine.stages import crop_window
from common.signal_sources import get_signal_sources
from pipeline.build import climate_normal_entry, load_region

EXAMPLES = Path("data/examples")
TUNJA = "15001"


@pytest.fixture(scope="module")
def examples():
    return load(EXAMPLES)


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


def papa_window(examples, sowing=date(2026, 8, 3)):
    return crop_window(examples.stages["papa"], sowing)


def test_las_tablas_del_clima_se_cargan_del_dataset(examples):
    assert {"municipality_id", "year", "month", "frost_days", "quality"} <= set(examples.climate_frost_month.columns)
    assert {"municipality_id", "month", "tmax_p90_c", "quality"} <= set(examples.climate_risk_month.columns)


def test_sin_tablas_del_clima_quedan_nulas_y_lo_demas_carga(dataset):
    loaded = load(dataset)
    assert loaded.climate_frost_month is None and loaded.climate_risk_month is None
    assert loaded.municipalities


def test_el_manifiesto_publica_el_periodo_normal_de_la_region():
    """Como el gradiente, el periodo normal lo fija la versión del dataset (R4)."""
    assert climate_normal_entry(load_region()) == {"climate_normal": {"first_year": 1991, "last_year": 2020, "min_years": 24}}
    assert climate_normal_entry({}) == {}


def with_normal(examples, normal):
    """Los ejemplos con otro `climate_normal` en el manifiesto (sin él si es None)."""
    region = {key: value for key, value in examples.region.items() if key != "climate_normal"}
    return replace(examples, region=region if normal is None else {**region, "climate_normal": normal})


def test_la_api_lee_el_periodo_normal_del_manifiesto(examples):
    """El manifiesto de ejemplo dice el periodo que cubren los datos de ejemplo (2015-2024), no el de la región (R5)."""
    assert climate_normal(examples) == ClimateNormal(2015, 2024, 8)
    assert climate_normal(with_normal(examples, None)) is None


@pytest.mark.parametrize(
    "normal",
    [
        "1991-2020",
        {"first_year": 1991, "last_year": 2020},
        {"first_year": "1991", "last_year": 2020, "min_years": 24},
        {"first_year": 1991.0, "last_year": 2020, "min_years": 24},
        {"first_year": True, "last_year": 2020, "min_years": 24},
        {"first_year": 2020, "last_year": 1991, "min_years": 24},
        {"first_year": 1991, "last_year": 2020, "min_years": 0},
    ],
)
def test_un_periodo_normal_mal_formado_es_sin_datos(examples, thresholds, normal):
    """Nunca se adivina el periodo ni se divide por cero: la señal es sin datos y lo dice (R1)."""
    broken = with_normal(examples, normal)
    assert climate_normal(broken) is None
    result = frost_for(broken, TUNJA, papa_window(broken), thresholds, "la papa")
    assert (result.status, result.reasons) == (
        INSUFFICIENT_DATA,
        ("Sin el periodo de referencia del clima de la zona: la señal no se evalúa",),
    )


def test_la_helada_se_califica_con_los_datos_de_ejemplo_y_lleva_el_aviso(examples, thresholds):
    """Con el periodo de los ejemplos alcanzan los años y la señal se califica, con el `frost_caveat` de
    `catalog/sources.yaml` en las limitaciones (aprobado por Felipe, PR #61). La razón cita los años de ejemplo."""
    caveat = get_signal_sources().for_region(examples.region["id"])["frost"].caveat
    assert caveat
    result = frost_for(examples, TUNJA, papa_window(examples), thresholds, "la papa")
    assert result.status == AVAILABLE and result.indicators == ("frost_freq_pct",)
    assert result.reasons[0].endswith("sembrando de 2015 a 2024")
    assert caveat in result.limitations
    assert result == frost_for(examples, TUNJA, papa_window(examples), thresholds, "la papa")  # R4


def test_con_un_periodo_que_los_ejemplos_no_cubren_la_helada_es_sin_datos(examples, thresholds):
    """Con la normal 1991-2020 los ejemplos (2015-2024) no tienen los años: sin datos y con el aviso (R1)."""
    long = with_normal(examples, {"first_year": 1991, "last_year": 2020, "min_years": 24})
    result = frost_for(long, TUNJA, papa_window(long), thresholds, "la papa")
    assert result.status == INSUFFICIENT_DATA
    assert get_signal_sources().for_region(examples.region["id"])["frost"].caveat in result.limitations


def test_sin_ventana_las_dos_senales_son_sin_datos(examples, thresholds):
    """El descanso no tiene etapas: `crop_window` da None y ninguna señal revienta (R1)."""
    assert frost_for(examples, TUNJA, None, thresholds, "el descanso").status == INSUFFICIENT_DATA
    assert heat_for(examples, TUNJA, None, examples.crops["papa"], thresholds, "el descanso").status == INSUFFICIENT_DATA


def test_un_municipio_sin_filas_es_sin_datos(examples, thresholds):
    window = papa_window(examples)
    assert frost_for(examples, "99999", window, thresholds, "la papa").status == INSUFFICIENT_DATA
    assert heat_for(examples, "99999", window, examples.crops["papa"], thresholds, "la papa").status == INSUFFICIENT_DATA


def test_el_calor_se_califica_con_la_maxima_del_municipio(examples, thresholds):
    result = heat_for(examples, TUNJA, papa_window(examples), examples.crops["papa"], thresholds, "la papa")
    assert result.status == AVAILABLE and result.indicators == ("tmax_p90_c",)
    assert result.reasons[0].startswith("De 2015 a 2024, ")
    assert "la papa aguanta hasta 30 °C" in result.reasons[0]


def test_la_api_pasa_las_filas_de_calor_como_estan(examples):
    """La API solo lee: los meses `partial`, nulos o NaN llegan al motor, que decide que no sirven."""
    risk = examples.climate_risk_month.with_columns(
        pl.when((pl.col("municipality_id") == TUNJA) & (pl.col("month") == 1))
        .then(pl.lit("partial"))
        .otherwise(pl.col("quality"))
        .alias("quality"),
        pl.when((pl.col("municipality_id") == TUNJA) & (pl.col("month") == 2))
        .then(None)
        .when((pl.col("municipality_id") == TUNJA) & (pl.col("month") == 3))
        .then(float("nan"))
        .otherwise(pl.col("tmax_p90_c"))
        .alias("tmax_p90_c"),
    )
    rows = heat_months(replace(examples, climate_risk_month=risk), TUNJA)
    assert set(rows) == set(range(1, 13))
    assert rows[1].quality == "partial" and rows[2] == HeatMonth(None, "ok") and math.isnan(rows[3].tmax_p90_c)
