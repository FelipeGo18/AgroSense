"""Heladas, temperatura máxima y aguaceros por mes (HU-045, HU-046; specs/02-contratos.md, tablas `climate_risk_month` y
`climate_frost_month`).

Sale de `climate_day`: la mínima y la máxima diarias de cada municipio, ya corregidas por altitud (HU-044).

- Un día de helada es uno con la mínima **menor o igual** al umbral de `pipeline/region.yaml` (`frost`: 2 °C, el
  criterio del ZARC de Brasil, `mapa_zarc_2025`; decidido por Felipe el 10 de noviembre de 2026).
- `climate_frost_month`: los días de helada de cada mes de cada año (`frost_days`) y los días con mínima (`valid_days`).
  Un mes con todos sus días es `ok`; si le falta alguno, `partial`; sin ningún día con mínima, no se publica (R1). Con
  ella el motor cuenta los años con helada de una ventana (HU-077).
- `climate_risk_month`, por municipio y mes, en los años del periodo normal (`climate_normal`: 1991-2020):
  - `frost_freq_pct`: el porcentaje de años en los que ese mes tuvo al menos un día de helada.
  - `frost_days_mean`: los días de helada de ese mes, en promedio por año.
  - `tmax_p90_c`: la temperatura máxima que se supera uno de cada diez días de ese mes (el percentil 90 de las máximas
    diarias de todos sus años), para la señal de calor.
  - Un año cuenta en un mes si tiene al menos el 90 % de sus días con dato: los días sin dato no se rellenan (R1).
  - `heavy_rain_days_mean` (HU-046): los días de aguacero de ese mes, en promedio por año. Aguacero es un día con lluvia
    de NASA POWER (la de la celda del municipio, sin corregir por altitud) mayor o igual al umbral de `region.yaml`
    (`heavy_rain`: 20 mm, el índice R20mm de ETCCDI, `etccdi_indices`). Un año cuenta si tiene el 90 % de los días del
    mes con lluvia.
  - `dry_window_freq_pct` y `blight_days_mean` (HU-046) van nulas hasta tener una regla con fuente (R8).
  - `years`: los años que cuentan (con aguaceros, el menor entre heladas, máxima y lluvia). Con menos de los que pide el
    periodo normal (24), `quality = partial`. Sin ninguno, la fila no se publica.

Es historia del clima de la zona, nunca un pronóstico. La mínima de NASA POWER en los valles sale más caliente que la de
las estaciones del IDEAM (HU-044): con ella se cuentan menos heladas de las que hay, y se dice (`docs/riesgos.md`).
"""

from typing import Any

import polars as pl

from pipeline.climate_normals import Normal
from pipeline.sources.nasa_power import SOURCE_ID

TMAX_QUANTILE = 0.9

RISK_SCHEMA = {
    "municipality_id": pl.String,
    "month": pl.Int8,
    "frost_freq_pct": pl.Float64,
    "frost_days_mean": pl.Float64,
    "tmax_p90_c": pl.Float64,
    "heavy_rain_days_mean": pl.Float64,
    "dry_window_freq_pct": pl.Float64,
    "blight_days_mean": pl.Float64,
    "years": pl.Int16,
    "quality": pl.String,
    "source_id": pl.String,
}

FROST_SCHEMA = {
    "municipality_id": pl.String,
    "year": pl.Int16,
    "month": pl.Int8,
    "frost_days": pl.Int16,
    "valid_days": pl.Int16,
    "quality": pl.String,
    "source_id": pl.String,
}


def frost_threshold(region: dict[str, Any]) -> float | None:
    """El umbral de helada de `region.yaml` (`frost.threshold_c`). Sin él no se publican heladas: no se inventa (R8)."""
    config = region.get("frost")
    return None if config is None else float(config["threshold_c"])


def frost_source(region: dict[str, Any]) -> str | None:
    """La fuente del umbral de helada (`frost.source_id` de `region.yaml`). El pipeline comprueba que esté en `sources`
    (R8)."""
    config = region.get("frost") or {}
    return config.get("source_id")


def heavy_rain_threshold(region: dict[str, Any]) -> float | None:
    """El umbral de aguacero de `region.yaml` (`heavy_rain.threshold_mm`, HU-046). Sin él, `heavy_rain_days_mean` queda
    nula: no se inventa (R8)."""
    config = region.get("heavy_rain")
    return None if config is None else float(config["threshold_mm"])


def heavy_rain_source(region: dict[str, Any]) -> dict[str, Any] | None:
    """La fila de `sources` del umbral de aguacero (`heavy_rain.source` de `region.yaml`), o None sin el bloque."""
    config = region.get("heavy_rain") or {}
    return config.get("source")


def heavy_rain_month(rain_day: pl.DataFrame, threshold_mm: float, normal: Normal) -> pl.DataFrame:
    """Por municipio y mes, en los años del periodo normal: los días de aguacero (lluvia ≥ `threshold_mm`) en promedio
    por año (`heavy_rain_days_mean`) y cuántos años cuentan (`rain_years`).

    Un año cuenta en un mes si tiene al menos el 90 % de sus días con lluvia (`climate_normal.min_day_share`): los días
    sin dato no se rellenan ni cuentan como secos (R1)."""
    if rain_day.is_empty():
        return pl.DataFrame(
            schema={"municipality_id": pl.String, "month": pl.Int8, "heavy_rain_days_mean": pl.Float64, "rain_years": pl.UInt32}
        )
    days = rain_day.filter(pl.col("date").dt.year().is_between(normal.first_year, normal.last_year)).with_columns(
        pl.col("date").dt.year().cast(pl.Int16).alias("year"),
        pl.col("date").dt.month().cast(pl.Int8).alias("month"),
        pl.col("date").dt.month_end().dt.day().alias("month_days"),
    )
    by_year = days.group_by("municipality_id", "year", "month").agg(
        pl.col("precip_mm").is_not_null().sum().alias("rain_days"),
        (pl.col("precip_mm") >= threshold_mm).sum().alias("heavy_days"),
        pl.col("month_days").first(),
    )
    return (
        by_year.filter(pl.col("rain_days") >= normal.min_day_share * pl.col("month_days"))
        .group_by("municipality_id", "month")
        .agg(pl.col("heavy_days").mean().round(2).alias("heavy_rain_days_mean"), pl.len().alias("rain_years"))
        .sort("municipality_id", "month")
    )


def _month_years(climate_day: pl.DataFrame, frost_threshold_c: float) -> pl.DataFrame:
    """Por municipio, año y mes: los días con mínima, con máxima, los días de helada y los días que tiene el mes."""
    return (
        climate_day.with_columns(
            pl.col("date").dt.year().cast(pl.Int16).alias("year"), pl.col("date").dt.month().cast(pl.Int8).alias("month")
        )
        .group_by("municipality_id", "year", "month")
        .agg(
            pl.col("temp_min_c").count().alias("min_days"),
            pl.col("temp_max_c").count().alias("max_days"),
            (pl.col("temp_min_c") <= frost_threshold_c).sum().alias("frost_days"),
        )
        .with_columns(pl.date("year", "month", 1).dt.month_end().dt.day().alias("month_days"))
    )


def climate_frost_month(climate_day: pl.DataFrame, frost_threshold_c: float) -> pl.DataFrame:
    """La tabla `climate_frost_month`: los días de helada de cada mes de cada año, con los días que tuvieron mínima."""
    if climate_day.is_empty():
        return pl.DataFrame(schema=FROST_SCHEMA)
    return (
        _month_years(climate_day, frost_threshold_c)
        .filter(pl.col("min_days") > 0)
        .select(
            "municipality_id",
            "year",
            "month",
            "frost_days",
            pl.col("min_days").alias("valid_days"),
            pl.when(pl.col("min_days") == pl.col("month_days")).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .cast(FROST_SCHEMA)
        .sort("municipality_id", "year", "month")
    )


def climate_risk_month(
    climate_day: pl.DataFrame,
    frost_threshold_c: float,
    normal: Normal,
    rain_day: pl.DataFrame | None = None,
    heavy_rain_mm: float | None = None,
) -> pl.DataFrame:
    """La tabla `climate_risk_month` desde `climate_day` y, para los aguaceros (HU-046), la lluvia diaria de cada
    municipio (`rain_day`: `municipality_id`, `date`, `precip_mm`) con el umbral de `region.yaml`.

    Sin la lluvia o sin el umbral, `heavy_rain_days_mean` queda nula. Las ventanas secas y la gota van nulas hasta tener
    una regla con fuente: no se inventan (R1, R8). Con aguaceros, `years` también cuenta los años con lluvia."""
    if climate_day.is_empty():
        return pl.DataFrame(schema=RISK_SCHEMA)
    in_normal = pl.col("date").dt.year().is_between(normal.first_year, normal.last_year)
    month_years = _month_years(climate_day.filter(in_normal), frost_threshold_c)
    enough = normal.min_day_share * pl.col("month_days")
    frost = (
        month_years.filter(pl.col("min_days") >= enough)
        .group_by("municipality_id", "month")
        .agg(
            (100 * (pl.col("frost_days") > 0).mean()).round(1).alias("frost_freq_pct"),
            pl.col("frost_days").mean().round(2).alias("frost_days_mean"),
            pl.len().alias("frost_years"),
        )
    )
    # El percentil 90 de las máximas: solo con los días de los años que tienen el 90 % del mes con máxima.
    with_max = month_years.filter(pl.col("max_days") >= enough).select("municipality_id", "year", "month")
    days = climate_day.filter(in_normal).with_columns(
        pl.col("date").dt.year().cast(pl.Int16).alias("year"), pl.col("date").dt.month().cast(pl.Int8).alias("month")
    )
    heat = (
        days.join(with_max, on=["municipality_id", "year", "month"])
        .group_by("municipality_id", "month")
        .agg(
            pl.col("temp_max_c").quantile(TMAX_QUANTILE, interpolation="linear").round(1).alias("tmax_p90_c"),
            pl.col("year").n_unique().alias("heat_years"),
        )
    )
    table = frost.join(heat, on=["municipality_id", "month"], how="full", coalesce=True)
    counted = [pl.col("frost_years").fill_null(0), pl.col("heat_years").fill_null(0)]
    if rain_day is not None and heavy_rain_mm is not None:
        # Solo los municipios y meses que ya tienen heladas o calor: la tabla no gana filas por la lluvia.
        heavy = heavy_rain_month(rain_day, heavy_rain_mm, normal)
        table = table.join(heavy, on=["municipality_id", "month"], how="left")
        counted.append(pl.col("rain_years").fill_null(0))
    else:
        table = table.with_columns(pl.lit(None, dtype=pl.Float64).alias("heavy_rain_days_mean"))
    years = pl.min_horizontal(*counted)
    return (
        table.select(
            "municipality_id",
            "month",
            "frost_freq_pct",
            "frost_days_mean",
            "tmax_p90_c",
            "heavy_rain_days_mean",
            *(pl.lit(None, dtype=pl.Float64).alias(c) for c in ("dry_window_freq_pct", "blight_days_mean")),
            years.alias("years"),
            pl.when(years >= normal.min_years).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .cast(RISK_SCHEMA)
        .sort("municipality_id", "month")
    )
