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


def daily(cell: str, first: date, last: date, rain=lambda day: 1.0) -> pl.DataFrame:
    """Una serie diaria de ejemplo (R5): `rain(día)` mm cada día; `None` es un día sin dato."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return pl.DataFrame(
        {"cell": cell, "date": days, "temp_min_c": 8.0, "temp_max_c": 19.0, "precip_mm": [rain(day) for day in days]},
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
    # Sin el 90 % de sus días, el mes no tiene total, y sin ningún otro dato no se publica: no se rellena (R1).
    assert month_of(table, "15646", 2024, 2) == {}


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
