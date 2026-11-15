"""Los datos de las señales de heladas (HU-077) y calor (HU-190): lee del dataset publicado lo de un municipio, el periodo
normal del manifiesto y el aviso de `catalog/sources.yaml`, y llama al motor con todo ya leído (R6). Solo lee: qué fila
sirve (un mes `partial`, un nulo, un NaN) lo decide cada señal en el motor. Sin errores HTTP, sin base de datos y sin
guardar nada (R9). Las dos señales van juntas porque comparten el periodo normal y la forma de leer las tablas del
clima del municipio; el ensamblado en `/diagnostics` es de HU-076.

Las filas del municipio se leen una sola vez (`zone_climate`) y se pasan a cada ventana (`frost_in`, `heat_in`): el
diagnóstico evalúa la ventana consultada y, si busca otra, las doce del año (HU-076); `/rotations`, una por ciclo.
`frost_for` y `heat_for` son el atajo para una sola ventana.

`crop_name` es el nombre del cultivo con su artículo («la papa»), como lo arma quien llama con la ficha
(`article` y `name_es`).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import polars as pl

from backend.config.thresholds import Thresholds
from backend.dataset import Dataset
from backend.engine.frost_signal import FrostMonth, frost_signal
from backend.engine.heat_signal import HeatMonth, heat_signal
from backend.engine.sensitive_signal import ClimateNormal, ClimateSignalResult
from backend.engine.stages import FROST, CropWindow
from common.signal_sources import get_signal_sources

NORMAL_FIELDS = ("first_year", "last_year", "min_years")


def climate_normal(dataset: Dataset) -> ClimateNormal | None:
    """El periodo normal que publicó el pipeline en el manifiesto (`climate_normal`, de `pipeline/region.yaml`).

    Un dataset publicado sin él, o con una forma que no sirve (años que no son enteros, `first_year` después de
    `last_year`, `min_years` menor que 1), da None y las señales son `insufficient_data`: nunca se usa un periodo por
    defecto ni se adivina (R1, R4).
    """
    config = dataset.region.get("climate_normal")
    if not isinstance(config, Mapping):
        return None
    values = [config.get(field) for field in NORMAL_FIELDS]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return None
    first_year, last_year, min_years = values
    if first_year > last_year or min_years < 1:
        return None
    return ClimateNormal(first_year, last_year, min_years)


def frost_caveat(dataset: Dataset) -> str | None:
    """El `frost_caveat` de la región del dataset en `catalog/sources.yaml` (ya leído y validado al arrancar la API)."""
    return get_signal_sources().for_region(dataset.region["id"])[FROST].caveat


def frost_months(dataset: Dataset, municipality_id: str) -> dict[tuple[int, int], FrostMonth]:
    """Las filas de `climate_frost_month` del municipio por `(año, mes)`. Sin la tabla o sin filas: vacío (R1)."""
    table = dataset.climate_frost_month
    if table is None:
        return {}
    rows = table.filter(pl.col("municipality_id") == municipality_id).select("year", "month", "frost_days", "quality")
    return {(year, month): FrostMonth(frost_days, quality) for year, month, frost_days, quality in rows.iter_rows()}


def heat_months(dataset: Dataset, municipality_id: str) -> dict[int, HeatMonth]:
    """Las filas de `climate_risk_month` del municipio por mes, tal como están (`tmax_p90_c` y `quality`). Sin la tabla
    o sin filas: vacío (R1)."""
    table = dataset.climate_risk_month
    if table is None:
        return {}
    rows = table.filter(pl.col("municipality_id") == municipality_id).select("month", "tmax_p90_c", "quality")
    return {month: HeatMonth(tmax_p90_c, quality) for month, tmax_p90_c, quality in rows.iter_rows()}


@dataclass(frozen=True)
class ZoneClimate:
    """Lo que las señales de heladas y calor leen del dataset para un municipio, leído una vez: las filas de cada tabla,
    el periodo normal y el aviso de heladas de la región."""

    frost_months: Mapping[tuple[int, int], FrostMonth]
    heat_months: Mapping[int, HeatMonth]
    normal: ClimateNormal | None
    frost_caveat: str | None


def zone_climate(dataset: Dataset, municipality_id: str) -> ZoneClimate:
    """El clima del municipio para todas las ventanas de una consulta."""
    return ZoneClimate(
        frost_months(dataset, municipality_id), heat_months(dataset, municipality_id), climate_normal(dataset), frost_caveat(dataset)
    )


def frost_in(climate: ZoneClimate, window: CropWindow | None, thresholds: Thresholds, crop_name: str) -> ClimateSignalResult:
    """La señal `frost` de la ventana con el clima ya leído (`window` nula: cultivo sin etapas)."""
    return frost_signal(window, climate.frost_months, climate.normal, thresholds, crop_name, climate.frost_caveat)


def heat_in(
    climate: ZoneClimate, window: CropWindow | None, crop: dict[str, Any], thresholds: Thresholds, crop_name: str
) -> ClimateSignalResult:
    """La señal `heat` de la ventana con el clima ya leído; `crop` es la ficha (`dataset.crops[crop_id]`)."""
    return heat_signal(window, climate.heat_months, crop, climate.normal, thresholds, crop_name)


def frost_for(
    dataset: Dataset, municipality_id: str, window: CropWindow | None, thresholds: Thresholds, crop_name: str
) -> ClimateSignalResult:
    """La señal `frost` de una sola ventana en el municipio (`window` nula: cultivo sin etapas)."""
    return frost_in(zone_climate(dataset, municipality_id), window, thresholds, crop_name)


def heat_for(
    dataset: Dataset, municipality_id: str, window: CropWindow | None, crop: dict[str, Any], thresholds: Thresholds, crop_name: str
) -> ClimateSignalResult:
    """La señal `heat` de una sola ventana en el municipio; `crop` es la ficha (`dataset.crops[crop_id]`)."""
    return heat_in(zone_climate(dataset, municipality_id), window, crop, thresholds, crop_name)
