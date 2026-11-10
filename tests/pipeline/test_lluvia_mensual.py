"""Lluvia mensual de NASA POWER y su normal (HU-042): `climate_month` (R1, R4, R7, R8).

Sin red: las series son de ejemplo (R5), con la forma que deja `nasa_power.read_cache`.
"""

from datetime import date, timedelta

import polars as pl

from pipeline import build, schema
from pipeline.sources import dane, nasa_power
from tests.conftest import SAMPLE_MUNICIPALITIES

# Samacá y Villa de Leyva caen en la misma celda; Zipaquirá, en la de al lado.
NORTH, SOUTH = "5.500_-73.750", "5.000_-73.750"


def daily(cell: str, first: date, last: date, rain=lambda day: 1.0, wetness=lambda day: (0.4, 0.6)) -> pl.DataFrame:
    """Una serie diaria de ejemplo (R5): `rain(día)` mm y `wetness(día)` (superficial, de raíces) cada día; `None` es un
    día sin dato. La radiación, el viento y la humedad relativa van con un valor cualquiera: aquí no se usan."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    wet = [wetness(day) for day in days]
    return pl.DataFrame(
        {
            "cell": cell,
            "date": days,
            "temp_min_c": 8.0,
            "temp_max_c": 19.0,
            "precip_mm": [rain(day) for day in days],
            "soil_wetness_top": [w[0] if w else None for w in wet],
            "soil_wetness_root": [w[1] if w else None for w in wet],
            "radiation_mj_m2": 15.0,
            "wind_2m_m_s": 2.0,
            "rh_2m_pct": 80.0,
        },
        schema=nasa_power.SERIES_SCHEMA,
    )


def municipalities() -> pl.DataFrame:
    # Sin altitud: la lluvia no se corrige por altitud y sale igual (HU-042).
    return dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])


def month_of(table: pl.DataFrame, municipality_id: str, year: int, month: int) -> dict:
    rows = table.filter((pl.col("municipality_id") == municipality_id) & (pl.col("year") == year) & (pl.col("month") == month))
    return rows.to_dicts()[0] if rows.height else {}


def test_la_lluvia_del_mes_es_la_suma_de_sus_dias_y_cumple_el_contrato():
    series = daily(NORTH, date(2024, 1, 1), date(2024, 3, 31))
    table = nasa_power.climate_month(series, municipalities(), date(2024, 3, 31))
    schema.check("climate_month", schema.typed("climate_month", table))
    january = month_of(table, "15646", 2024, 1)
    assert january["precip_mm"] == 31.0 and january["source_id"] == "nasa_power"
    assert month_of(table, "15646", 2024, 2)["precip_mm"] == 29.0  # 2024 es bisiesto
    # Samacá y Villa de Leyva comparten celda; Zipaquirá está en otra que la serie no trae: no tiene filas.
    assert set(table["municipality_id"].to_list()) == {"15407", "15646"}


def test_el_mes_en_curso_no_se_publica():
    series = daily(NORTH, date(2024, 1, 1), date(2024, 2, 10))
    table = nasa_power.climate_month(series, municipalities(), date(2024, 2, 10))
    assert table["month"].unique().to_list() == [1]


def test_un_mes_con_pocos_dias_sin_dato_es_parcial_y_uno_con_muchos_no_se_publica():
    # Enero: 2 días sin dato (29 de 31, más del 90 %). Febrero: 10 días sin dato (19 de 29).
    def rain(day):
        if day.month == 1 and day.day <= 2 or day.month == 2 and day.day <= 10:
            return None
        return 2.0

    table = nasa_power.climate_month(daily(NORTH, date(2024, 1, 1), date(2024, 2, 29), rain), municipalities(), date(2024, 2, 29))
    january = month_of(table, "15646", 2024, 1)
    assert (january["precip_mm"], january["quality"]) == (58.0, "partial")
    # Sin el 90 % de sus días, el mes no tiene total de lluvia: queda nulo, no se rellena (R1). La fila sale por la
    # humedad del suelo, que sí está completa.
    february = month_of(table, "15646", 2024, 2)
    assert (february["precip_mm"], february["soil_wetness_root"], february["quality"]) == (None, 0.6, "partial")
    # Sin la lluvia ni la humedad, el mes no tiene ningún dato y no se publica.
    dry = nasa_power.climate_month(
        daily(NORTH, date(2024, 1, 1), date(2024, 2, 29), rain, lambda day: None if day.month == 2 else (0.4, 0.6)),
        municipalities(),
        date(2024, 2, 29),
    )
    assert month_of(dry, "15646", 2024, 2) == {}


def test_la_normal_es_el_promedio_de_1991_a_2020_con_24_anos_completos():
    # Cada enero llueve 1 mm por día más que el anterior; los demás meses, 1 mm por día.
    series = daily(NORTH, date(1985, 1, 1), date(2022, 12, 31), lambda day: float(day.year - 1990) if day.month == 1 else 1.0)
    table = nasa_power.climate_month(series, municipalities(), date(2022, 12, 31))
    # De 1991 a 2020 el enero llueve de 1 a 30 mm por día: en promedio 15,5 mm por día, 480,5 mm.
    january = month_of(table, "15646", 2005, 1)
    assert january["precip_normal_mm"] == 480.5 and january["quality"] == "ok"
    # La normal es la misma para todos los años del mes, también fuera del periodo.
    assert month_of(table, "15646", 2022, 1)["precip_normal_mm"] == 480.5
    assert month_of(table, "15646", 1986, 3)["precip_normal_mm"] == 31.0


def test_sin_24_anos_completos_no_hay_normal_y_el_mes_es_parcial():
    series = daily(NORTH, date(2000, 1, 1), date(2020, 12, 31))  # 21 años del periodo
    table = nasa_power.climate_month(series, municipalities(), date(2020, 12, 31))
    month = month_of(table, "15646", 2010, 5)
    assert month["precip_mm"] == 31.0 and month["precip_normal_mm"] is None and month["quality"] == "partial"


def test_la_lluvia_se_publica_aunque_falte_la_altitud(tmp_path, monkeypatch):
    """La temperatura necesita la altitud (HU-206); la lluvia no: `climate_month` sale con la caché de POWER sola."""
    import json

    from tests.pipeline.test_clima_diario import REGION, dane_cache, response

    days = {f"{day:%Y%m%d}": (8.0, 19.0, 1.0) for day in (date(2024, 1, 1) + timedelta(days=i) for i in range(31))}
    power = tmp_path / "power"
    power.mkdir()
    for cell, elevation in ((NORTH, 2476.01), (SOUTH, 2600.0)):
        (power / f"{cell}.json").write_text(json.dumps(response(cell, elevation, days)), encoding="utf-8")
    meta = {"downloaded_at": "2026-11-10T14:00:00+00:00", "requested_end": "2024-01-31", "cells": [NORTH, SOUTH]}
    (power / nasa_power.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setattr(build, "load_region", lambda: {**REGION})
    folder = tmp_path / "published"
    manifest = build.build(folder=folder, cache=dane_cache(tmp_path / "raw"), power_cache=power)
    assert "climate_month" in manifest["tables"] and "climate_day" not in manifest["tables"]
    month = pl.read_parquet(folder / "climate_month.parquet")
    assert month.height == 3 and set(month["precip_mm"].to_list()) == {31.0}
    # Un solo año: sin normal, y por eso `partial` (R1).
    assert month["precip_normal_mm"].null_count() == 3 and set(month["quality"].to_list()) == {"partial"}
    build.verify(folder, REGION["dataset_version"])


# ---------- Humedad del suelo (HU-205) ----------


def test_la_humedad_del_suelo_es_el_promedio_del_mes_de_0_a_1():
    series = daily(NORTH, date(2024, 1, 1), date(2024, 1, 31), wetness=lambda day: (0.3, 0.5) if day.day <= 15 else (0.5, 0.7))
    january = month_of(nasa_power.climate_month(series, municipalities(), date(2024, 1, 31)), "15646", 2024, 1)
    assert (january["soil_wetness_top"], january["soil_wetness_root"]) == (
        round((15 * 0.3 + 16 * 0.5) / 31, 3),
        round((15 * 0.5 + 16 * 0.7) / 31, 3),
    )


def test_a_la_humedad_le_falta_un_dia_y_el_mes_es_parcial():
    series = daily(
        NORTH,
        date(1991, 1, 1),
        date(2020, 12, 31),
        wetness=lambda day: None if (day.year, day.month, day.day) == (2010, 5, 3) else (0.4, 0.6),
    )
    table = nasa_power.climate_month(series, municipalities(), date(2020, 12, 31))
    may = month_of(table, "15646", 2010, 5)
    assert (may["soil_wetness_top"], may["quality"]) == (0.4, "partial")
    assert month_of(table, "15646", 2010, 6)["quality"] == "ok"


def test_una_cache_de_antes_de_hu_205_pide_bajarla_otra_vez(tmp_path):
    """Sin la humedad, la radiación y el viento en la caché, no se publican nulos como si POWER no los tuviera (R1)."""
    import json

    import pytest

    from tests.pipeline.test_clima_diario import DAYS, response

    body = response(NORTH, 2476.01, DAYS)
    for name in ("GWETTOP", "GWETROOT", "ALLSKY_SFC_SW_DWN", "WS2M", "RH2M"):
        del body["properties"]["parameter"][name]
    (tmp_path / f"{NORTH}.json").write_text(json.dumps(body), encoding="utf-8")
    (tmp_path / nasa_power.META_FILE).write_text(json.dumps({"cells": [NORTH]}), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="--descargar"):
        nasa_power.read_cache([NORTH], tmp_path)
