"""Aguaceros por mes (HU-046): `heavy_rain_days_mean` de `climate_risk_month` (R1, R4, R8).

Sin red: la lluvia diaria es de ejemplo (R5), con la forma de la que sale de NASA POWER por municipio.
"""

from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
import yaml

from pipeline import build, climate_normals, climate_risk, schema
from pipeline.sources import nasa_power
from tests.pipeline.test_heladas import climate_day, month_of

THRESHOLD = 2.0
HEAVY_MM = 20.0
NORMAL = climate_normals.Normal(first_year=1991, last_year=2020, min_years=24, min_day_share=0.9, dry_quantile=0.2)
FIRST, LAST = date(1991, 1, 1), date(2020, 12, 31)


def rain_day(first: date, last: date, rain, municipality_id: str = "15001") -> pl.DataFrame:
    """Lluvia diaria de ejemplo (R5): `rain(día)` en mm; `None` es un día sin dato."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return pl.DataFrame(
        {"municipality_id": municipality_id, "date": days, "precip_mm": [rain(day) for day in days]},
        schema={"municipality_id": pl.String, "date": pl.Date, "precip_mm": pl.Float64},
    )


def risk(rain, heavy_mm=HEAVY_MM, temps=None):
    temps = temps if temps is not None else climate_day(FIRST, LAST, lambda day: 6.0)
    return climate_risk.climate_risk_month(temps, THRESHOLD, NORMAL, rain, heavy_mm)


def test_un_aguacero_es_un_dia_con_20_mm_o_mas_y_se_promedia_por_ano():
    """Octubre de los años pares tiene 3 días de 25 mm (15 de 30 años): 1,5 días por año. Un día de 19,9 mm no cuenta."""

    def rain(day):
        if day.month == 10 and day.year % 2 == 0 and day.day <= 3:
            return 25.0
        return 19.9 if day.month == 10 and day.day == 20 else 2.0

    table = risk(rain_day(FIRST, LAST, rain))
    schema.check("climate_risk_month", schema.typed("climate_risk_month", table))
    october = month_of(table, 10)
    assert (october["heavy_rain_days_mean"], october["years"], october["quality"]) == (1.5, 30, "ok")
    assert month_of(table, 1)["heavy_rain_days_mean"] == 0.0


def test_20_mm_justos_es_aguacero():
    """R20mm de ETCCDI: «PRCP ≥ 20mm»."""
    table = risk(rain_day(FIRST, LAST, lambda day: 20.0 if day.month == 3 and day.day == 1 else 0.0))
    assert month_of(table, 3)["heavy_rain_days_mean"] == 1.0


def test_un_dia_sin_lluvia_no_cuenta_ni_como_seco_ni_como_aguacero():
    """Un mes con más del 10 % de sus días sin dato no cuenta ese año (R1): no se rellena con 0."""

    def rain(day):
        if day.year == 2000 and day.month == 5:
            return None if day.day <= 4 else 30.0  # 4 de 31 días sin dato: no llega al 90 %
        return 30.0 if day.month == 5 and day.day == 1 else 0.0

    may = month_of(risk(rain_day(FIRST, LAST, rain)), 5)
    # Cuentan los otros 29 años, cada uno con un aguacero; el 2000 (27 aguaceros con dato) no entra.
    assert (may["heavy_rain_days_mean"], may["years"], may["quality"]) == (1.0, 29, "ok")


def test_con_menos_anos_de_lluvia_que_los_que_pide_la_normal_la_fila_es_partial():
    """`years` es el menor entre heladas, máxima y lluvia: con lluvia solo de 2001 a 2020 (20 años), `partial`."""
    table = risk(rain_day(date(2001, 1, 1), LAST, lambda day: 0.0))
    january = month_of(table, 1)
    assert (january["heavy_rain_days_mean"], january["years"], january["quality"]) == (0.0, 20, "partial")
    assert january["frost_freq_pct"] == 0.0


def test_fuera_del_periodo_normal_no_cuenta():
    rain = rain_day(date(1981, 1, 1), LAST, lambda day: 50.0 if day.year < 1991 else 0.0)
    assert month_of(risk(rain), 6)["heavy_rain_days_mean"] == 0.0


@pytest.mark.parametrize(("rain", "heavy_mm"), [(None, HEAVY_MM), ("lluvia", None)])
def test_sin_lluvia_o_sin_umbral_los_aguaceros_quedan_nulos(rain, heavy_mm):
    """Sin la lluvia de POWER o sin el umbral con fuente de `region.yaml`, no se inventa el número (R1, R8)."""
    frame = rain_day(FIRST, LAST, lambda day: 30.0) if rain else None
    january = month_of(risk(frame, heavy_mm), 1)
    assert january["heavy_rain_days_mean"] is None and january["years"] == 30


def test_la_lluvia_no_agrega_filas_de_municipios_sin_temperatura():
    """Un municipio con lluvia pero sin `climate_day` (sin altitud) no gana filas solo por la lluvia."""
    rain = pl.concat([rain_day(FIRST, LAST, lambda day: 0.0), rain_day(FIRST, LAST, lambda day: 0.0, "15002")])
    assert set(risk(rain)["municipality_id"].to_list()) == {"15001"}


def test_las_ventanas_secas_y_la_gota_siguen_nulas():
    """Sin una regla con fuente no se publican (R8): las ventanas secas y la gota quedan para cuando la haya."""
    january = month_of(risk(rain_day(FIRST, LAST, lambda day: 0.0)), 1)
    assert january["dry_window_freq_pct"] is None and january["blight_days_mean"] is None


def test_la_lluvia_de_cada_municipio_es_la_de_su_celda_y_un_hueco_queda_nulo():
    series = pl.DataFrame(
        {"cell": ["6.000_-73.125"] * 2, "date": [date(2020, 1, 1), date(2020, 1, 2)], "precip_mm": [12.5, None]},
        schema={"cell": pl.String, "date": pl.Date, "precip_mm": pl.Float64},
    )
    municipalities = pl.DataFrame(
        {"municipality_id": ["15238", "15999"], "lat": [5.8, None], "lon": [-73.0, None]},
        schema={"municipality_id": pl.String, "lat": pl.Float64, "lon": pl.Float64},
    )
    assert nasa_power.cell_of(5.8, -73.0) == "6.000_-73.125"
    table = nasa_power.rain_day(series, municipalities)
    assert table.rows() == [("15238", date(2020, 1, 1), 12.5), ("15238", date(2020, 1, 2), None)]


def test_el_umbral_y_su_fuente_salen_de_region_yaml():
    region = yaml.safe_load(Path("pipeline/region.yaml").read_text(encoding="utf-8"))
    assert climate_risk.heavy_rain_threshold(region) == 20.0
    source = climate_risk.heavy_rain_source(region)
    assert source["source_id"] == "etccdi_indices" and source["license"] and source["citation"]
    assert "R20mm" in source["name"]
    assert climate_risk.heavy_rain_threshold({}) is None and climate_risk.heavy_rain_source({}) is None


def sources(*ids):
    return pl.DataFrame({"source_id": list(ids)})


def test_aguaceros_con_un_umbral_sin_fuente_no_pasan():
    table = risk(rain_day(FIRST, LAST, lambda day: 0.0))
    build.validate_heavy_rain(table, sources("nasa_power", "etccdi_indices"), "etccdi_indices")
    with pytest.raises(build.ValidationError, match="no está en `sources`"):
        build.validate_heavy_rain(table, sources("nasa_power"), "etccdi_indices")
    with pytest.raises(build.ValidationError, match="no está en `sources`"):
        build.validate_heavy_rain(table, sources("nasa_power"), None)


def test_dias_de_aguacero_imposibles_no_pasan():
    table = risk(rain_day(FIRST, LAST, lambda day: 0.0)).with_columns(heavy_rain_days_mean=pl.lit(40.0))
    with pytest.raises(build.ValidationError, match="imposibles"):
        build.validate_heavy_rain(table, sources("etccdi_indices"), "etccdi_indices")


def test_sin_aguaceros_no_se_exige_la_fuente():
    table = risk(None)
    build.validate_heavy_rain(table, sources("nasa_power"), None)


def test_comprobacion_a_mano_en_duitama_contra_lo_publicado():
    """Duitama (15238), celda de POWER 6.000_-73.125, octubre de 1991 a 2020: 42 días con `PRECTOTCORR` ≥ 20 mm en los
    930 días (todos con dato), contados a mano en `data/raw/nasa_power/6.000_-73.125.json`: 42 / 30 años = 1,4."""
    table = pl.read_parquet("data/published/climate_risk_month.parquet")
    october = table.filter((pl.col("municipality_id") == "15238") & (pl.col("month") == 10)).row(0, named=True)
    assert (october["heavy_rain_days_mean"], october["years"]) == (1.4, 30)
    published = pl.read_parquet("data/published/sources.parquet")
    assert "etccdi_indices" in published["source_id"].to_list()
