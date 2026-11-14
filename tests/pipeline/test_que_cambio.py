"""El clima de dos periodos para «Qué cambió» (HU-216): `climate_change_month` (R1, R4, R7, R8; decisión 11).

Sin red: las series son de ejemplo (R5), con la forma de `climate_day`, `climate_month` y `precip_month`.
"""

from datetime import date, timedelta

import polars as pl
import pytest

from pipeline import build, climate_change, schema

REGION = {
    "climate_normal": {"first_year": 1991, "last_year": 2020, "min_years": 24, "min_day_share": 0.9, "dry_quantile": 0.2},
    "frost": {"threshold_c": 2.0, "source_id": "mapa_zarc_2025"},
    "change_periods": {
        "min_year_share": 0.8,
        "nasa_power": [
            {"period_id": "p1981_2000", "start_year": 1981, "end_year": 2000},
            {"period_id": "p2005_2024", "start_year": 2005, "end_year": 2024},
        ],
        "imerg": [
            {"period_id": "p2001_2012", "start_year": 2001, "end_year": 2012},
            {"period_id": "p2013_2024", "start_year": 2013, "end_year": 2024},
        ],
    },
}


def climate_day(first: date, last: date, tmin, tmax=lambda day: 18.0) -> pl.DataFrame:
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return pl.DataFrame(
        {"municipality_id": "15001", "date": days, "temp_min_c": [tmin(d) for d in days], "temp_max_c": [tmax(d) for d in days]},
        schema={"municipality_id": pl.String, "date": pl.Date, "temp_min_c": pl.Float64, "temp_max_c": pl.Float64},
    )


def monthly(years, rain, municipality_id: str = "15001") -> pl.DataFrame:
    """Una tabla mensual de lluvia de ejemplo (R5): `rain(año, mes)` mm; `None` es un mes sin dato."""
    rows = [(municipality_id, y, m, rain(y, m)) for y in years for m in range(1, 13)]
    return pl.DataFrame(
        rows, schema={"municipality_id": pl.String, "year": pl.Int16, "month": pl.Int8, "precip_mm": pl.Float64}, orient="row"
    )


def row(table: pl.DataFrame, period_id: str, month: int) -> dict:
    found = table.filter((pl.col("period_id") == period_id) & (pl.col("month") == month))
    return found.to_dicts()[0] if found.height else {}


def test_los_periodos_viven_en_la_region_con_su_fuente_y_su_minimo_de_anos():
    """El 80 % de los años: 16 de 20 con POWER y 10 de 12 con IMERG (`pipeline/region.yaml`)."""
    periods = climate_change.periods_from_region(build.load_region())
    assert [(p.period_id, p.source_id, p.min_years) for p in periods] == [
        ("p1981_2000", "nasa_power", 16),
        ("p2005_2024", "nasa_power", 16),
        ("p2001_2012", "imerg", 10),
        ("p2013_2024", "imerg", 10),
    ]


def test_cada_periodo_de_power_tiene_sus_heladas_su_calor_y_su_lluvia():
    # En enero heló (1 °C el día 3) solo en los años antes de 2001; la máxima y la lluvia suben en el segundo periodo.
    def tmin(day):
        return 1.0 if day.month == 1 and day.day == 3 and day.year <= 2000 else 6.0

    def tmax(day):
        return 20.0 if day.year >= 2005 else 18.0

    series = climate_day(date(1981, 1, 1), date(2024, 12, 31), tmin, tmax)
    rain = monthly(range(1981, 2025), lambda y, m: 120.0 if y >= 2005 else 80.0)
    table = climate_change.climate_change_month(REGION, series, rain, None)
    schema.check("climate_change_month", schema.typed("climate_change_month", table))
    before, after = row(table, "p1981_2000", 1), row(table, "p2005_2024", 1)
    assert (before["frost_freq_pct"], before["tmax_p90_c"], before["precip_normal_mm"]) == (100.0, 18.0, 80.0)
    assert (after["frost_freq_pct"], after["tmax_p90_c"], after["precip_normal_mm"]) == (0.0, 20.0, 120.0)
    assert (before["years"], before["quality"], before["source_id"]) == (20, "ok", "nasa_power")


def test_la_helada_es_la_de_hu_045_con_2_grados_justos():
    table = climate_change.climate_change_month(REGION, climate_day(date(2005, 1, 1), date(2024, 12, 31), lambda d: 2.0), None, None)
    assert row(table, "p2005_2024", 1)["frost_freq_pct"] == 100.0


def test_con_menos_anos_que_el_minimo_el_indicador_queda_nulo_y_sin_ninguno_no_hay_fila():
    # Lluvia de 2005 a 2019: 15 años, uno menos de los 16 que pide el periodo 2005-2024 (R1).
    rain = monthly(range(2005, 2020), lambda y, m: 90.0)
    table = climate_change.climate_change_month(REGION, None, rain, None)
    assert table.filter(pl.col("period_id") == "p2005_2024").is_empty()
    # Con heladas pero sin lluvia suficiente: la fila sale, sin lluvia y `partial`.
    series = climate_day(date(2005, 1, 1), date(2024, 12, 31), lambda d: 6.0)
    table = climate_change.climate_change_month(REGION, series, rain, None)
    may = row(table, "p2005_2024", 5)
    assert may["precip_normal_mm"] is None and may["frost_freq_pct"] == 0.0 and may["quality"] == "partial"


def test_imerg_trae_solo_la_lluvia_con_sus_propios_periodos():
    precip = monthly(range(2001, 2025), lambda y, m: 150.0 if y >= 2013 else 100.0)
    table = climate_change.climate_change_month(REGION, None, None, precip)
    assert set(table["source_id"]) == {"imerg"} and set(table["period_id"]) == {"p2001_2012", "p2013_2024"}
    first, second = row(table, "p2001_2012", 7), row(table, "p2013_2024", 7)
    assert (first["precip_normal_mm"], second["precip_normal_mm"], first["years"]) == (100.0, 150.0, 12)
    assert first["frost_freq_pct"] is None and first["tmax_p90_c"] is None and first["quality"] == "ok"


def test_las_dos_fuentes_salen_en_filas_aparte_y_nunca_se_mezclan():
    rain = monthly(range(1981, 2025), lambda y, m: 80.0)
    precip = monthly(range(2001, 2025), lambda y, m: 140.0)
    table = climate_change.climate_change_month(REGION, None, rain, precip)
    pairs = set(table.select("period_id", "source_id").unique().iter_rows())
    assert pairs == {("p1981_2000", "nasa_power"), ("p2005_2024", "nasa_power"), ("p2001_2012", "imerg"), ("p2013_2024", "imerg")}


def test_un_periodo_con_la_fuente_equivocada_no_se_publica():
    precip = monthly(range(2001, 2025), lambda y, m: 140.0)
    table = climate_change.climate_change_month(REGION, None, None, precip)
    municipalities = pl.DataFrame({"municipality_id": ["15001"]})
    sources = pl.DataFrame({"source_id": ["nasa_power", "imerg"]})
    periods = climate_change.periods_from_region(REGION)
    build.validate_change(table, municipalities, sources, periods)
    with pytest.raises(build.ValidationError, match="periodo"):
        build.validate_change(table.with_columns(pl.lit("nasa_power").alias("source_id")), municipalities, sources, periods)


def test_sin_periodos_en_la_region_no_hay_tabla():
    assert climate_change.climate_change_month({}, None, monthly(range(1981, 2025), lambda y, m: 80.0), None).is_empty()


def test_lo_publicado_en_el_repositorio_trae_los_cuatro_periodos_y_el_manifiesto_los_lista():
    folder = build.PUBLISHED
    if not (folder / "climate_change_month.parquet").exists():
        pytest.skip("data/published no trae climate_change_month en esta imagen")
    import json

    table = pl.read_parquet(folder / "climate_change_month.parquet")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert {p["period_id"] for p in manifest["periods"]} == set(table["period_id"])
    assert table["municipality_id"].n_unique() == 239
