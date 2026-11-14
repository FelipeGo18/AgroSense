"""El terreno de un lote: su altitud y la temperatura de la zona corregida a ella (HU-191; contrato, «La rejilla de 250 m»).

Son cálculos de lectura sobre la rejilla del dataset, sin errores HTTP, sin base de datos y sin guardar nada (R9). El
motor sigue recibiendo `tmean_annual_c` como un número (R6): la geometría, la mediana y el gradiente viven aquí.
"""

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import shapely
from shapely.geometry import shape

from backend.accounts.farm_models import Lot
from backend.dataset import Dataset, Grid, Municipality
from common.grid import GRID_COLUMNS, GRID_STEP_DEG, cell_id, cell_key


@dataclass(frozen=True)
class LotAltitude:
    """La altitud de un lote en metros enteros (nula si ninguna celda tiene dato), con cuántas celdas la dan y si salió
    de la celda que contiene su centro porque ningún centro de celda cae dentro del polígono."""

    altitude_m: float | None
    cells: int
    by_center: bool


def _altitudes(keys: np.ndarray, grid: Grid) -> np.ndarray:
    """La altitud de las celdas pedidas que están en la rejilla y tienen dato. Las que faltan o son nulas no cuentan:
    nunca se rellenan (R1)."""
    if len(grid.keys) == 0 or len(keys) == 0:
        return np.empty(0)
    positions = np.searchsorted(grid.keys, keys)
    in_range = positions < len(grid.keys)
    found = np.zeros(len(keys), dtype=bool)
    found[in_range] = grid.keys[positions[in_range]] == keys[in_range]
    values = grid.altitude_m[positions[found]]
    return values[~np.isnan(values)]


def lot_altitude(geometry: dict[str, Any], grid: Grid) -> LotAltitude:
    """La mediana de la altitud de las celdas de 250 m cuyo centro cae dentro del polígono (un centro justo en el borde
    cuenta). Con un número par de celdas, el promedio de las dos del medio.

    Un lote más chico que una celda usa la celda que contiene su centro (`by_center`). Sin ninguna celda con dato, la
    altitud es nula. El contorno ya viene validado y normalizado al guardarse el lote (`lot_geometry.drawn_lot`).
    """
    polygon = shape(geometry)
    shapely.prepare(polygon)
    min_x, min_y, max_x, max_y = polygon.bounds
    rows = np.arange(int((90.0 - max_y) // GRID_STEP_DEG), int((90.0 - min_y) // GRID_STEP_DEG) + 1)
    columns = np.arange(int((min_x + 180.0) // GRID_STEP_DEG), int((max_x + 180.0) // GRID_STEP_DEG) + 1)
    row_grid, column_grid = np.meshgrid(rows, columns, indexing="ij")
    row_flat, column_flat = row_grid.ravel(), column_grid.ravel()
    inside = shapely.intersects_xy(polygon, -180.0 + (column_flat + 0.5) * GRID_STEP_DEG, 90.0 - (row_flat + 0.5) * GRID_STEP_DEG)

    if not inside.any():
        center = polygon.centroid
        values = _altitudes(np.array([cell_key(cell_id(center.y, center.x))], dtype=np.int64), grid)
        return LotAltitude(float(round(values[0])) if len(values) else None, cells=1, by_center=True)

    values = _altitudes(row_flat[inside] * GRID_COLUMNS + column_flat[inside], grid)
    if not len(values):
        return LotAltitude(None, cells=0, by_center=False)
    return LotAltitude(float(round(np.median(values))), cells=len(values), by_center=False)


def tmean_at_altitude(tmean_annual_c: float, reference_altitude_m: float, altitude_m: float, lapse_rate: dict[str, Any]) -> float:
    """Corrige la temperatura media anual de la altitud de referencia a otra con el gradiente de la región.

    Las temperaturas diarias del pipeline se corrigen con una tasa para la mínima y otra para la máxima, y la media es
    lineal: corregir la media con el promedio de las dos tasas da lo mismo que recalcular a la otra altitud (0,1 °C como
    mucho, por el redondeo). Se redondea a 1 decimal, como `tmean_annual_c`, para que el límite exacto del rango se
    compare igual en un municipio y en un lote.
    """
    lapse = (lapse_rate["temp_min_c_per_m"] + lapse_rate["temp_max_c_per_m"]) / 2
    return round(tmean_annual_c + lapse * (reference_altitude_m - altitude_m), 1)


@dataclass(frozen=True)
class ZoneTemperature:
    """La temperatura media anual con la que se decide la aptitud y de dónde salió. Con `tmean_annual_c` nulo, la
    aptitud es `insufficient_data` y `limitation` dice por qué si lo causó el lote."""

    basis: Literal["lot", "municipality"]
    tmean_annual_c: float | None
    altitude_m: float | None
    cells: int = 0
    by_center: bool = False
    limitation: str | None = None


def _at(altitude_m: float | None) -> str:
    return f", a {altitude_m:.0f} m" if altitude_m is not None else ""


def _unusable(limitation: str | None) -> ZoneTemperature:
    return ZoneTemperature("lot", None, None, limitation=limitation)


def zone_temperature(dataset: Dataset, municipality: Municipality, lot: Lot | None) -> ZoneTemperature:
    """La única que decide qué temperatura entra a la aptitud (HU-191).

    Sin lote, o con un lote sin contorno, la del municipio (a la altitud de su cabecera). Con contorno, la del municipio
    corregida a la altitud del lote. Si no se puede saber la altitud del lote, `insufficient_data` y no la del
    municipio: sería poner el lote en otro lugar (R1). R9: ni el contorno ni la altitud del lote se registran.
    """
    if lot is None:
        return ZoneTemperature("municipality", municipality.tmean_annual_c, municipality.altitude_m)
    if lot.geometry is None:
        return ZoneTemperature(
            "municipality",
            municipality.tmean_annual_c,
            municipality.altitude_m,
            limitation=(
                "Su lote no tiene contorno dibujado: la aptitud usa la temperatura media del municipio"
                f"{_at(municipality.altitude_m)}. Dibuje el lote para corregirla a su altitud."
            ),
        )
    if municipality.tmean_annual_c is None:
        return _unusable(None)
    if dataset.grid is None:
        return _unusable("La altitud de los lotes no está publicada en esta versión del dataset.")
    lapse_rate = dataset.region.get("temperature_lapse_rate")
    if lapse_rate is None or municipality.altitude_m is None:
        return _unusable(
            "No se pudo corregir la temperatura a la altitud de su lote: falta el gradiente de temperatura "
            "o la altitud del municipio en esta versión del dataset."
        )
    found = lot_altitude(lot.geometry, dataset.grid)
    if found.altitude_m is None:
        return _unusable("No hay altitud de NASADEM para su lote: no se pudo saber si el cultivo se da a esa altura.")
    tmean = tmean_at_altitude(municipality.tmean_annual_c, municipality.altitude_m, found.altitude_m, lapse_rate)
    return ZoneTemperature("lot", tmean, found.altitude_m, found.cells, found.by_center)
