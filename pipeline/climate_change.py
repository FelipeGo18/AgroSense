"""El clima de dos periodos para «Qué cambió» (HU-216; specs/02-contratos.md, `climate_change_month`; specs/01-reglas.md,
«Qué cambió en la zona»).

Para cada municipio, periodo y mes, los indicadores del periodo, siempre de **una sola fuente** (decisión 11):

- **NASA POWER** (`source_id = nasa_power`): la frecuencia de heladas (`frost_freq_pct`) y la máxima p90 (`tmax_p90_c`),
  con el mismo cálculo, el mismo umbral (≤ 2 °C) y la misma temperatura corregida por altitud que `climate_risk_month`
  (HU-045), y la lluvia normal del mes (`precip_normal_mm`) de `climate_month`.
- **GPM IMERG** (`source_id = imerg`): solo la lluvia normal, de `precip_month`; las heladas y el calor van nulos.

Los periodos viven en `pipeline/region.yaml` (`change_periods`), cada uno con su fuente, y el manifiesto los lista (R4).
Un año cuenta en un mes con el 90 % de sus días (o de su área, en IMERG). Un indicador con menos años que el mínimo del
periodo (`min_year_share` de sus años) queda nulo; una fila sin ningún indicador no se publica (R1). `quality` es `ok`
con todos los indicadores de su fuente y `partial` si falta alguno.

Es historia comparada, nunca un pronóstico: dice cómo fue un periodo frente a otro, no cómo será el clima.
"""

import math
from dataclasses import dataclass
from typing import Any

import polars as pl

from pipeline import climate_risk
from pipeline.climate_normals import Normal

POWER, IMERG = "nasa_power", "imerg"

CHANGE_SCHEMA = {
    "municipality_id": pl.String,
    "period_id": pl.String,
    "month": pl.Int8,
    "source_id": pl.String,
    "frost_freq_pct": pl.Float64,
    "tmax_p90_c": pl.Float64,
    "precip_normal_mm": pl.Float64,
    "years": pl.Int16,
    "quality": pl.String,
}


@dataclass(frozen=True)
class Period:
    period_id: str
    start_year: int
    end_year: int
    source_id: str
    min_years: int

    def manifest(self) -> dict[str, Any]:
        return {"period_id": self.period_id, "start_year": self.start_year, "end_year": self.end_year, "source_id": self.source_id}


def periods_from_region(region: dict[str, Any]) -> list[Period]:
    """Los periodos de `region.yaml` (`change_periods`), en orden. Sin la configuración, ninguno (no se inventan)."""
    config = region.get("change_periods")
    if not config:
        return []
    share = float(config["min_year_share"])
    periods = []
    for source_id in (POWER, IMERG):
        for entry in config.get(source_id) or []:
            start, end = int(entry["start_year"]), int(entry["end_year"])
            periods.append(Period(str(entry["period_id"]), start, end, source_id, math.ceil(share * (end - start + 1))))
    return periods


def _rain(table: pl.DataFrame, period: Period) -> pl.DataFrame:
    """La lluvia normal de cada municipio y mes en el periodo: el promedio de los años con dato, y cuántos son."""
    return (
        table.filter(pl.col("year").is_between(period.start_year, period.end_year) & pl.col("precip_mm").is_not_null())
        .group_by("municipality_id", "month")
        .agg(pl.col("precip_mm").sort().mean().round(1).alias("precip_normal_mm"), pl.len().alias("rain_years"))
        .with_columns(pl.when(pl.col("rain_years") >= period.min_years).then(pl.col("precip_normal_mm")).alias("precip_normal_mm"))
    )


def _power(
    climate_day: pl.DataFrame | None, climate_month: pl.DataFrame | None, threshold: float | None, normal: Normal, period: Period
) -> pl.DataFrame:
    parts = []
    if climate_day is not None and not climate_day.is_empty() and threshold is not None:
        window = Normal(period.start_year, period.end_year, period.min_years, normal.min_day_share, normal.dry_quantile)
        risk = climate_risk.climate_risk_month(climate_day, threshold, window).select(
            "municipality_id",
            pl.col("month").cast(pl.Int8),
            *(pl.when(pl.col("years") >= period.min_years).then(pl.col(c)).alias(c) for c in ("frost_freq_pct", "tmax_p90_c")),
            pl.col("years").alias("risk_years"),
        )
        parts.append(risk)
    if climate_month is not None and not climate_month.is_empty():
        parts.append(_rain(climate_month, period).with_columns(pl.col("month").cast(pl.Int8)))
    if not parts:
        return pl.DataFrame(schema=CHANGE_SCHEMA)
    table = parts[0]
    for part in parts[1:]:
        table = table.join(part, on=["municipality_id", "month"], how="full", coalesce=True)
    for column in ("frost_freq_pct", "tmax_p90_c", "precip_normal_mm"):
        if column not in table.columns:
            table = table.with_columns(pl.lit(None, dtype=pl.Float64).alias(column))
    indicators = ("frost_freq_pct", "tmax_p90_c", "precip_normal_mm")
    # Los años de la fila son los del indicador con menos años, entre los que se publican.
    counted = [
        pl.when(pl.col(i).is_not_null()).then(pl.col(y))
        for i, y in (("frost_freq_pct", "risk_years"), ("tmax_p90_c", "risk_years"), ("precip_normal_mm", "rain_years"))
        if y in table.columns
    ]
    return _finish(table.with_columns(pl.min_horizontal(counted).alias("years")), indicators, period)


def _imerg(precip_month: pl.DataFrame | None, period: Period) -> pl.DataFrame:
    if precip_month is None or precip_month.is_empty():
        return pl.DataFrame(schema=CHANGE_SCHEMA)
    rain = _rain(precip_month, period).with_columns(
        pl.col("month").cast(pl.Int8),
        pl.lit(None, dtype=pl.Float64).alias("frost_freq_pct"),
        pl.lit(None, dtype=pl.Float64).alias("tmax_p90_c"),
        pl.when(pl.col("precip_normal_mm").is_not_null()).then(pl.col("rain_years")).alias("years"),
    )
    return _finish(rain, ("precip_normal_mm",), period)


def _finish(table: pl.DataFrame, indicators: tuple[str, ...], period: Period) -> pl.DataFrame:
    present = [pl.col(i).is_not_null() for i in indicators]
    return (
        table.filter(pl.any_horizontal(present))
        .select(
            "municipality_id",
            pl.lit(period.period_id).alias("period_id"),
            "month",
            pl.lit(period.source_id).alias("source_id"),
            "frost_freq_pct",
            "tmax_p90_c",
            "precip_normal_mm",
            "years",
            pl.when(pl.all_horizontal(present)).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
        )
        .cast(CHANGE_SCHEMA)
    )


def climate_change_month(
    region: dict[str, Any],
    climate_day: pl.DataFrame | None,
    climate_month: pl.DataFrame | None,
    precip_month: pl.DataFrame | None,
) -> pl.DataFrame:
    """La tabla `climate_change_month` con todos los periodos de `region.yaml`, cada uno con su fuente."""
    normal = Normal.from_region(region)
    threshold = climate_risk.frost_threshold(region)
    tables = []
    for period in periods_from_region(region):
        if period.source_id == POWER and normal is not None:
            tables.append(_power(climate_day, climate_month, threshold, normal, period))
        elif period.source_id == IMERG:
            tables.append(_imerg(precip_month, period))
    if not tables:
        return pl.DataFrame(schema=CHANGE_SCHEMA)
    return pl.concat(tables).sort("municipality_id", "source_id", "period_id", "month")
