"""Suelo y terreno del lote calculados al vuelo (HU-182). Nunca escriben en la BD.

Las medianas incluyen solo datos finitos. Un polígono sin datos no se sustituye
por su municipio (R1). La textura conserva la moda y el desempate del pipeline.
"""

from typing import Any

import numpy as np
import polars as pl

from backend.accounts.farm_models import Lot
from backend.api.lot_terrain import _lot_cells, _positions, lot_altitude, lot_texture
from backend.dataset import SOIL_COLUMNS, Dataset, Grid, Municipality

# Las fuentes del suelo en la rejilla son SoilGrids y el triángulo de texturas del USDA (`Grid.properties.soil_sources`, sin `nasadem`).
# `grid_cells.source_ids` trae además `nasadem` (la altitud y la pendiente), que no es una fuente del suelo (R8).


def _median(grid: Grid, positions: np.ndarray, name: str) -> float | None:
    if name == "altitude_m":
        values = grid.altitude_m[positions]
    elif grid.properties is not None and name in grid.properties.columns:
        values = grid.properties[name].gather(positions).cast(pl.Float64).to_numpy()
    else:
        return None
    values = values[np.isfinite(values)]
    if not len(values):
        return None
    median = float(np.median(values))
    # Las propiedades van en float32 (unos 7 dígitos): sin redondear, 3,8 saldría 3,7999999523 en la respuesta.
    return median if name == "altitude_m" else float(f"{median:.6g}")


def zone_soil(dataset: Dataset, municipality: Municipality, lot: Lot | None = None) -> dict[str, Any] | None:
    """Propiedades de suelo del contrato, con `basis`, `cells` y sus fuentes."""
    if lot is None or lot.geometry is None:
        row = dataset.soil.get(municipality.municipality_id)
        if row is None:
            return None
        # La misma forma que el del lote: `source_ids` como lista (revisión del PR #143).
        municipal = {key: value for key, value in row.items() if key != "source_id"}
        return dict(municipal, basis="municipality", source_ids=[row["source_id"]] if row.get("source_id") else [])
    grid = dataset.grid
    if grid is None:
        return None
    keys, _ = _lot_cells(lot.geometry)
    positions = _positions(keys, grid)
    values = {name: _median(grid, positions, name) for name in SOIL_COLUMNS}
    texture = lot_texture(lot.geometry, grid)
    if all(value is None for value in values.values()) and texture is None:
        return None
    sources: set[str] = set()
    partial = len(positions) != len(keys) or any(value is None for value in values.values())
    if grid.properties is not None:
        rows = grid.properties[positions.tolist()]
        if "soil_sources" in rows.columns:
            sources = {source for joined in rows["soil_sources"].to_list() if joined for source in joined.split(",")}
        # La `quality` de la celda también es `partial` por un hueco de NASADEM: el del suelo se decide con sus columnas.
        for name in SOIL_COLUMNS:
            if name in rows.columns:
                partial |= any(value is None or not np.isfinite(value) for value in rows[name].to_list())
    return dict(
        values,
        texture_class=texture,
        basis="lot",
        cells=len(keys),
        quality="partial" if partial or texture is None else "ok",
        source_ids=sorted(sources),
    )


def zone_terrain(dataset: Dataset, municipality: Municipality, lot: Lot) -> dict[str, Any] | None:
    """Altitud y pendiente según el mismo polígono, sin persistirlas (R9)."""
    if dataset.grid is None:
        return None
    if lot.geometry is None:
        cells = dataset.grid.cells_by_municipality.get(municipality.municipality_id, 0)
        return {"altitude_m": municipality.altitude_m, "slope_pct": municipality.slope_pct, "basis": "municipality", "cells": cells}
    keys, _ = _lot_cells(lot.geometry)
    positions = _positions(keys, dataset.grid)
    # La altitud es la de `lot_altitude`, la misma que usa la aptitud: una sola definición para el lote.
    altitude = lot_altitude(lot.geometry, dataset.grid)
    return {
        "altitude_m": altitude.altitude_m,
        "slope_pct": _median(dataset.grid, positions, "slope_pct"),
        "basis": "lot",
        "cells": altitude.cells,
    }
