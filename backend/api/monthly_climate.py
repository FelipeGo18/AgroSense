"""La lluvia y la ET0 mensuales de un municipio, de la fuente que define `catalog/sources.yaml` para la región.

Son lecturas del dataset publicado, sin errores HTTP, sin base de datos y sin guardar nada (R9). El motor recibe solo
los números (`backend.engine.water_need`, R6). Las usan las tendencias (HU-078) y las usará la señal `water` (HU-071,
HU-144).

- **La lluvia** sale de la fuente `water.rain` de la región. La tabla la decide la fuente, no la consulta: GPM IMERG y
  cualquier otra fuente de lluvia por satélite se publican en `precip_month` (HU-207, con `source_id` en la llave);
  NASA POWER, en `climate_month.precip_mm` (HU-042). Si la fuente elegida no tiene dato para el municipio, no hay
  lluvia: nunca se cambia a la de contraste ni a la otra tabla (R1; `catalog/sources.yaml`).
- **La ET0** sale de la fuente `water.et0` de la región, en `climate_month.et0_mm` (Penman-Monteith, FAO-56).
"""

import math
from dataclasses import dataclass

import polars as pl

from backend.dataset import Dataset
from common import signal_sources

MonthKey = tuple[int, int]


@dataclass(frozen=True)
class MonthlySeries:
    """Los totales mensuales de un municipio de una fuente, por `(año, mes)`. Un mes con fila y valor nulo (o NaN) es `None`;
    un mes sin fila no está. `years` son los años que la fuente publica para el municipio, en orden."""

    source_id: str
    values: dict[MonthKey, float | None]

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted({year for year, _ in self.values}))


def water_sources(dataset: Dataset) -> signal_sources.SignalSource:
    """Las fuentes de la señal `water` de la región del dataset (lluvia en `used`, ET0 en `et0`).

    Si la región no está en `catalog/sources.yaml`, es un error de despliegue (el pipeline no publica sin ella): falla
    con `SignalSourcesError` y la API responde 500 con el motivo en el log, en vez de inventar una fuente.
    """
    return signal_sources.get_signal_sources().for_region(dataset.region["id"])["water"]


def _value(value: float | None) -> float | None:
    """Un total mensual como `float`, o `None` si es nulo o NaN: un NaN es un dato que falta, nunca un número que
    llegue a la suma ni al JSON (R1)."""
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) else number


def _series(table: pl.DataFrame, municipality_id: str, source_id: str, column: str) -> MonthlySeries:
    rows = table.filter((pl.col("municipality_id") == municipality_id) & (pl.col("source_id") == source_id))
    return MonthlySeries(
        source_id,
        {(int(year), int(month)): _value(value) for year, month, value in rows.select("year", "month", column).iter_rows()},
    )


def _publishes(table: pl.DataFrame | None, source_id: str) -> bool:
    return table is not None and not table.filter(pl.col("source_id") == source_id).is_empty()


def monthly_rain(dataset: Dataset, municipality_id: str, source_id: str) -> MonthlySeries:
    """La lluvia mensual del municipio de `source_id`: de `precip_month` si esa tabla publica la fuente; si no, de
    `climate_month` si es su fuente. Vacía si ninguna la publica o no hay filas del municipio (R1)."""
    if _publishes(dataset.precip_month, source_id):
        return _series(dataset.precip_month, municipality_id, source_id, "precip_mm")
    if _publishes(dataset.climate_month, source_id):
        return _series(dataset.climate_month, municipality_id, source_id, "precip_mm")
    return MonthlySeries(source_id, {})


def monthly_et0(dataset: Dataset, municipality_id: str, source_id: str) -> MonthlySeries:
    """La ET0 mensual del municipio de `source_id` (`climate_month.et0_mm`). Vacía sin la tabla o sin filas (R1)."""
    if dataset.climate_month is None:
        return MonthlySeries(source_id, {})
    return _series(dataset.climate_month, municipality_id, source_id, "et0_mm")
