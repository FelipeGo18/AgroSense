"""Temperatura media anual de cada municipio (HU-044): `municipalities.tmean_annual_c`, la que usa el filtro de aptitud.

Sin red: las series diarias son de ejemplo (R5), con la forma de `climate_day`.
"""

from datetime import date, timedelta

import polars as pl
import pytest

from pipeline import build, climate_normals

NORMAL = climate_normals.Normal(first_year=1991, last_year=2020, min_years=24, min_day_share=0.9)


def climate_day(first: date, last: date, tmin=lambda day: 8.0, tmax=lambda day: 18.0) -> pl.DataFrame:
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return pl.DataFrame(
        {"municipality_id": "15001", "date": days, "temp_min_c": [tmin(d) for d in days], "temp_max_c": [tmax(d) for d in days]},
        schema={"municipality_id": pl.String, "date": pl.Date, "temp_min_c": pl.Float64, "temp_max_c": pl.Float64},
    )


def tmean_of(table: pl.DataFrame) -> dict:
    return table.to_dicts()[0] if table.height else {}


def test_es_el_promedio_de_la_minima_y_la_maxima_en_el_periodo_normal():
    # Fuera de 1991-2020 hace mucho más calor: no cuenta.
    series = climate_day(date(1985, 1, 1), date(2024, 12, 31), tmax=lambda day: 40.0 if day.year > 2020 or day.year < 1991 else 18.0)
    row = tmean_of(climate_normals.tmean_annual(series, NORMAL))
    assert (row["tmean_annual_c"], row["years"]) == (13.0, 30)


def test_un_ano_sin_el_90_por_ciento_de_sus_dias_no_cuenta():
    # En 2000 faltan 60 días y los demás son de 30 °C de máxima: si contara, subiría el promedio.
    def tmax(day):
        if day.year == 2000:
            return None if day.timetuple().tm_yday <= 60 else 30.0
        return 18.0

    row = tmean_of(climate_normals.tmean_annual(climate_day(date(1991, 1, 1), date(2020, 12, 31), tmax=tmax), NORMAL))
    assert (row["tmean_annual_c"], row["years"]) == (13.0, 29)


def test_sin_24_anos_queda_nula():
    row = tmean_of(climate_normals.tmean_annual(climate_day(date(2001, 1, 1), date(2020, 12, 31)), NORMAL))
    assert row["tmean_annual_c"] is None and row["years"] == 20


def test_el_periodo_normal_vive_en_la_region():
    """Decidido por Felipe el 10 de noviembre de 2026: 1991-2020 con 24 años y el 90 % de los días, en `region.yaml`."""
    normal = climate_normals.Normal.from_region(build.load_region())
    assert normal == NORMAL


def test_lo_publicado_en_el_repositorio_tiene_la_temperatura_media_de_todos_los_municipios():
    folder = build.PUBLISHED
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    if municipalities["altitude_m"].null_count() == municipalities.height:
        pytest.skip("data/published no trae la altitud en esta imagen")
    assert municipalities["tmean_annual_c"].null_count() == 0
    by_name = dict(municipalities.select("name", "tmean_annual_c").iter_rows())
    # Tierra caliente frente a tierra fría.
    assert by_name["Girardot"] > 25 > 15 > by_name["Tunja"]
