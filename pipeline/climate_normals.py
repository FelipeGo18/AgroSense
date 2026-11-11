"""El periodo normal del clima y la temperatura media anual de cada municipio (HU-044; specs/01-reglas.md, «Aptitud del
cultivo en la zona»).

El periodo normal vive en `pipeline/region.yaml` (`climate_normal`), uno solo para todo lo que se compara con una normal:
1991-2020 con al menos 24 de sus 30 años, el periodo de referencia de la OMM y el de las normales del IDEAM (decidido por
Felipe el 10 de noviembre de 2026). Un año cuenta si tiene al menos el 90 % de sus días con dato: no se rellena (R1).

`tmean_annual_c` es el promedio de `(temp_min_c + temp_max_c) / 2` en los días de los años que cuentan, desde
`climate_day`, ya corregida por la altitud de la cabecera (HU-044, HU-206). Es la que usa el filtro de aptitud. Sin años
suficientes, queda nula y la aptitud es `insufficient_data` (R1).
"""

from dataclasses import dataclass
from typing import Any

import polars as pl


@dataclass(frozen=True)
class Normal:
    first_year: int
    last_year: int
    min_years: int
    min_day_share: float
    # El año seco (HU-143): el percentil de la lluvia de cada mes que se supera en 4 de cada 5 años.
    dry_quantile: float

    @classmethod
    def from_region(cls, region: dict[str, Any]) -> "Normal | None":
        config = region.get("climate_normal")
        if config is None:
            return None
        return cls(
            first_year=int(config["first_year"]),
            last_year=int(config["last_year"]),
            min_years=int(config["min_years"]),
            min_day_share=float(config["min_day_share"]),
            dry_quantile=float(config["dry_quantile"]),
        )


def tmean_annual(climate_day: pl.DataFrame, normal: Normal) -> pl.DataFrame:
    """La temperatura media anual de cada municipio en el periodo normal: `municipality_id`, `tmean_annual_c`, `years`."""
    schema = {"municipality_id": pl.String, "tmean_annual_c": pl.Float64, "years": pl.Int16}
    if climate_day.is_empty():
        return pl.DataFrame(schema=schema)
    days = climate_day.filter(pl.col("date").dt.year().is_between(normal.first_year, normal.last_year)).with_columns(
        pl.col("date").dt.year().alias("year"), ((pl.col("temp_min_c") + pl.col("temp_max_c")) / 2).alias("tmean")
    )
    year_days = pl.when(pl.date("year", 12, 31).dt.ordinal_day() == 366).then(366).otherwise(365)
    years = (
        days.group_by("municipality_id", "year")
        .agg(pl.col("tmean").count().alias("valid"))
        .filter(pl.col("valid") >= normal.min_day_share * year_days)
        .select("municipality_id", "year")
    )
    return (
        days.join(years, on=["municipality_id", "year"])
        .group_by("municipality_id")
        .agg(pl.col("tmean").mean().round(1).alias("tmean_annual_c"), pl.col("year").n_unique().alias("years"))
        .with_columns(pl.when(pl.col("years") >= normal.min_years).then(pl.col("tmean_annual_c")).alias("tmean_annual_c"))
        .cast(schema)
        .sort("municipality_id")
    )


def with_tmean(municipalities: pl.DataFrame, tmean: pl.DataFrame) -> pl.DataFrame:
    """`municipalities` con su `tmean_annual_c`. Un municipio sin ella queda nulo (R1)."""
    return (
        municipalities.drop("tmean_annual_c")
        .join(tmean.select("municipality_id", "tmean_annual_c"), on="municipality_id", how="left")
        .select(municipalities.columns)
    )
