"""Heladas y temperatura máxima por mes (HU-045): `climate_risk_month` y `climate_frost_month` (R1, R4, R7, R8).

Sin red: las series diarias son de ejemplo (R5), con la forma de `climate_day`.
"""

from datetime import date, timedelta

import polars as pl
import pytest

from pipeline import build, climate_normals, climate_risk, schema

THRESHOLD = 2.0
NORMAL = climate_normals.Normal(first_year=1991, last_year=2020, min_years=24, min_day_share=0.9, dry_quantile=0.2)


def climate_day(first: date, last: date, tmin, tmax=lambda day: 18.0, municipality_id: str = "15001") -> pl.DataFrame:
    """Una `climate_day` de ejemplo (R5): `tmin(día)` y `tmax(día)` en °C; `None` es un día sin dato."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return pl.DataFrame(
        {
            "municipality_id": municipality_id,
            "date": days,
            "temp_min_c": [tmin(day) for day in days],
            "temp_max_c": [tmax(day) for day in days],
            "quality": "ok",
            "source_id": "nasa_power",
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


def month_of(table: pl.DataFrame, month: int, municipality_id: str = "15001") -> dict:
    rows = table.filter((pl.col("municipality_id") == municipality_id) & (pl.col("month") == month))
    return rows.to_dicts()[0] if rows.height else {}


def test_la_frecuencia_es_el_porcentaje_de_anos_con_al_menos_una_helada():
    # Enero de los años pares de 1991 a 2020 tiene dos noches de 1 °C (15 de 30 años); los demás días, 6 °C.
    def tmin(day):
        return 1.0 if day.month == 1 and day.year % 2 == 0 and day.day <= 2 else 6.0

    table = climate_risk.climate_risk_month(climate_day(date(1991, 1, 1), date(2020, 12, 31), tmin), THRESHOLD, NORMAL)
    schema.check("climate_risk_month", schema.typed("climate_risk_month", table))
    january = month_of(table, 1)
    assert (january["frost_freq_pct"], january["frost_days_mean"], january["years"], january["quality"]) == (50.0, 1.0, 30, "ok")
    assert month_of(table, 2)["frost_freq_pct"] == 0.0
    # Las columnas del P1 no se inventan (R1).
    assert january["heavy_rain_days_mean"] is None and january["blight_days_mean"] is None


def test_una_minima_de_2_grados_justos_es_helada():
    """El criterio del ZARC es «temperaturas mínimas menores ou igual a 2°C» (decidido por Felipe el 10 de noviembre de
    2026); una de 2,1 °C ya no es helada."""
    at_threshold = climate_risk.climate_risk_month(climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 2.0), THRESHOLD, NORMAL)
    assert month_of(at_threshold, 1)["frost_freq_pct"] == 100.0
    above = climate_risk.climate_risk_month(climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 2.1), THRESHOLD, NORMAL)
    assert month_of(above, 1)["frost_freq_pct"] == 0.0


def test_la_maxima_p90_es_la_que_se_supera_uno_de_cada_diez_dias():
    # Cada día de marzo, la máxima es el día del mes: de 1 a 31 °C.
    series = climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 6.0, lambda day: float(day.day))
    march = month_of(climate_risk.climate_risk_month(series, THRESHOLD, NORMAL), 3)
    assert march["tmax_p90_c"] == pytest.approx(pl.Series([float(d) for d in range(1, 32)]).quantile(0.9, interpolation="linear"), abs=0.05)


def test_solo_cuentan_los_anos_de_la_normal_y_los_meses_casi_completos():
    def tmin(day):
        if day.year == 2021:
            return -5.0  # fuera de 1991-2020: no cuenta
        if day.year == 2000 and day.month == 1 and day.day <= 5:
            return None  # a enero de 2000 le faltan 5 de 31 días: no cuenta
        return 6.0

    table = climate_risk.climate_risk_month(climate_day(date(1991, 1, 1), date(2021, 12, 31), tmin), THRESHOLD, NORMAL)
    assert month_of(table, 1)["years"] == 29 and month_of(table, 1)["frost_freq_pct"] == 0.0
    assert month_of(table, 2)["years"] == 30


def test_con_pocos_anos_el_mes_es_parcial_y_sin_datos_no_se_publica():
    table = climate_risk.climate_risk_month(climate_day(date(2001, 1, 1), date(2020, 12, 31), lambda day: 6.0), THRESHOLD, NORMAL)
    assert (month_of(table, 5)["years"], month_of(table, 5)["quality"]) == (20, "partial")
    assert climate_risk.climate_risk_month(climate_day(date(1985, 1, 1), date(1989, 12, 31), lambda day: 6.0), THRESHOLD, NORMAL).is_empty()


def test_una_frecuencia_fuera_de_0_a_100_no_se_publica():
    table = climate_risk.climate_risk_month(climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 6.0), THRESHOLD, NORMAL)
    by_year = climate_risk.climate_frost_month(climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 6.0), THRESHOLD)
    bad = table.with_columns(pl.lit(120.0).alias("frost_freq_pct"))
    municipalities = pl.DataFrame({"municipality_id": ["15001"]})
    sources = pl.DataFrame({"source_id": ["nasa_power", "mapa_zarc_2025"]})
    zarc = "mapa_zarc_2025"
    with pytest.raises(build.ValidationError, match="frecuencia"):
        build.validate_frost(bad, by_year, municipalities, sources, zarc)
    with pytest.raises(build.ValidationError, match="días"):
        build.validate_frost(table, by_year.with_columns(pl.lit(40).cast(pl.Int16).alias("frost_days")), municipalities, sources, zarc)
    build.validate_frost(table, by_year, municipalities, sources, zarc)


def test_un_umbral_cuya_fuente_no_esta_en_sources_no_se_publica():
    """R8 (revisión de Felipe del PR #61): `frost.source_id` de `region.yaml` tiene que estar en `sources`."""
    series = climate_day(date(1991, 1, 1), date(2020, 12, 31), lambda day: 6.0)
    table = climate_risk.climate_risk_month(series, THRESHOLD, NORMAL)
    by_year = climate_risk.climate_frost_month(series, THRESHOLD)
    municipalities = pl.DataFrame({"municipality_id": ["15001"]})
    sources = pl.DataFrame({"source_id": ["nasa_power"]})
    with pytest.raises(build.ValidationError, match="mapa_zarc_2025"):
        build.validate_frost(table, by_year, municipalities, sources, "mapa_zarc_2025")
    with pytest.raises(build.ValidationError, match="frost.source_id"):
        build.validate_frost(table, by_year, municipalities, sources, None)


def test_el_umbral_de_la_region_es_el_del_zarc_y_su_fuente_se_publica():
    """El umbral real de `pipeline/region.yaml`: 2 °C, el criterio del ZARC (`mapa_zarc_2025`), cuya fila de `sources`
    sale del catálogo (R8)."""
    region = build.load_region()
    assert climate_risk.frost_threshold(region) == 2.0 and region["frost"]["source_id"] == "mapa_zarc_2025"
    from pipeline import catalog

    _, _, catalog_sources = catalog.build(catalog.load())
    assert "mapa_zarc_2025" in catalog_sources["source_id"].to_list()


# ---------- Los días de helada de cada mes de cada año (`climate_frost_month`, HU-077) ----------


def test_cada_mes_de_cada_ano_trae_sus_dias_de_helada_y_sus_dias_con_minima():
    # 1995: tres noches de 2 °C o menos en enero; 1996: ninguna.
    def tmin(day):
        return 2.0 if (day.year, day.month) == (1995, 1) and day.day <= 3 else 6.0

    table = climate_risk.climate_frost_month(climate_day(date(1995, 1, 1), date(1996, 12, 31), tmin), THRESHOLD)
    schema.check("climate_frost_month", schema.typed("climate_frost_month", table))
    rows = {(r["year"], r["month"]): r for r in table.to_dicts()}
    assert (rows[(1995, 1)]["frost_days"], rows[(1995, 1)]["valid_days"], rows[(1995, 1)]["quality"]) == (3, 31, "ok")
    assert rows[(1996, 1)]["frost_days"] == 0 and rows[(1996, 2)]["valid_days"] == 29
    assert table.height == 24 and set(table["source_id"]) == {"nasa_power"}


def test_un_mes_sin_todos_sus_dias_es_parcial_y_sin_ninguno_no_se_publica():
    def tmin(day):
        if day.month == 3:
            return None  # marzo sin ningún dato: no se publica (R1)
        if day.month == 2 and day.day == 10:
            return None  # a febrero le falta un día: partial
        return 6.0

    table = climate_risk.climate_frost_month(climate_day(date(2010, 1, 1), date(2010, 4, 30), tmin), THRESHOLD)
    rows = {r["month"]: r for r in table.to_dicts()}
    assert set(rows) == {1, 2, 4}
    assert (rows[2]["valid_days"], rows[2]["quality"]) == (27, "partial") and rows[1]["quality"] == "ok"


def test_los_dias_de_helada_de_cada_ano_cuadran_con_la_frecuencia_del_mes():
    """`climate_risk_month` y `climate_frost_month` cuentan igual: los años con helada en enero de la normal."""

    def tmin(day):
        return 1.0 if day.month == 1 and day.year % 3 == 0 and day.day == 5 else 6.0

    series = climate_day(date(1991, 1, 1), date(2020, 12, 31), tmin)
    by_year = climate_risk.climate_frost_month(series, THRESHOLD).filter(pl.col("month") == 1)
    january = month_of(climate_risk.climate_risk_month(series, THRESHOLD, NORMAL), 1)
    assert january["frost_freq_pct"] == round(100 * (by_year["frost_days"] > 0).mean(), 1)


def test_lo_publicado_en_el_repositorio_tiene_heladas_de_diciembre_a_marzo():
    """La comprobación de HU-045: en el altiplano, el mes con más heladas cae entre diciembre y marzo, como dicen la
    Gobernación de Boyacá y el IDEAM."""
    folder = build.PUBLISHED
    if not (folder / "climate_risk_month.parquet").exists():
        pytest.skip("data/published no trae climate_risk_month en esta imagen")
    risk = pl.read_parquet(folder / "climate_risk_month.parquet")
    high = pl.read_parquet(folder / "municipalities.parquet").filter(pl.col("altitude_m") >= 2500)["municipality_id"].implode()
    by_month = (
        risk.filter(pl.col("municipality_id").is_in(high)).group_by("month").agg(pl.col("frost_freq_pct").mean()).sort("frost_freq_pct")
    )
    assert by_month["month"][-1] in (12, 1, 2, 3)
