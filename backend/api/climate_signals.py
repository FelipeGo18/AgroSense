"""Los datos de las señales de heladas (HU-077) y calor (HU-190): lee del dataset publicado lo de un municipio, el periodo
normal del manifiesto y el aviso de `catalog/sources.yaml`, y llama al motor con todo ya leído (R6). Solo lee: qué fila
sirve (un mes `partial`, un nulo, un NaN) lo decide cada señal en el motor. Sin errores HTTP, sin base de datos y sin
guardar nada (R9). Las dos señales van juntas porque comparten el periodo normal y la forma de leer las tablas del
clima del municipio; el ensamblado en `/diagnostics` es de HU-076.

Cada llamada filtra la tabla del clima por municipio. Para una ventana basta; HU-076 (con las doce ventanas del año) y
`/rotations` (con una por ciclo) deben leer las filas del municipio una sola vez y pasarlas a cada ventana.

`crop_name` es el nombre del cultivo con su artículo («la papa»), como lo arma quien llama con la ficha
(`article` y `name_es`).
"""

from collections.abc import Mapping
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


def frost_for(
    dataset: Dataset, municipality_id: str, window: CropWindow | None, thresholds: Thresholds, crop_name: str
) -> ClimateSignalResult:
    """La señal `frost` de la ventana en el municipio (`window` nula: cultivo sin etapas)."""
    return frost_signal(
        window, frost_months(dataset, municipality_id), climate_normal(dataset), thresholds, crop_name, frost_caveat(dataset)
    )


def heat_for(
    dataset: Dataset, municipality_id: str, window: CropWindow | None, crop: dict[str, Any], thresholds: Thresholds, crop_name: str
) -> ClimateSignalResult:
    """La señal `heat` de la ventana en el municipio; `crop` es la ficha (`dataset.crops[crop_id]`)."""
    return heat_signal(window, heat_months(dataset, municipality_id), crop, climate_normal(dataset), thresholds, crop_name)
