"""Suelo y terreno del lote calculados al vuelo (HU-182). Nunca escriben en la BD.

Las medianas incluyen solo datos finitos. Un polígono sin datos no se sustituye
por su municipio (R1). La textura conserva la moda y el desempate del pipeline.
"""

from typing import Any

import numpy as np
import polars as pl

from backend.accounts.farm_models import Lot
from backend.api.lot_terrain import _lot_cells, _positions, lot_texture
from backend.dataset import SOIL_COLUMNS, Dataset, Grid, Municipality


def _median(grid: Grid, positions: np.ndarray, name: str) -> float | None:
    if name == "altitude_m":
        values = grid.altitude_m[positions]
    elif grid.properties is not None and name in grid.properties.columns:
        values = grid.properties[name].gather(positions).cast(pl.Float64).to_numpy()
    else:
        return None
    values = values[np.isfinite(values)]
    return float(np.median(values)) if len(values) else None


def zone_soil(dataset: Dataset, municipality: Municipality, lot: Lot | None = None) -> dict[str, Any] | None:
    """Propiedades de suelo del contrato, con `basis`, `cells` y sus fuentes."""
    if lot is None or lot.geometry is None:
        row = dataset.soil.get(municipality.municipality_id)
        return None if row is None else dict(row, basis="municipality")
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
        if "source_ids" in rows.columns:
            sources = {source for row in rows["source_ids"].to_list() for source in (row or [])}
        if "quality" in rows.columns:
            partial |= any(value != "ok" for value in rows["quality"].to_list())
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
        properties = dataset.grid.properties
        cells = 0
        if properties is not None and "municipality_id" in properties.columns:
            cells = properties.filter(pl.col("municipality_id") == municipality.municipality_id).height
        return {"altitude_m": municipality.altitude_m, "slope_pct": municipality.slope_pct, "basis": "municipality", "cells": cells}
    keys, _ = _lot_cells(lot.geometry)
    positions = _positions(keys, dataset.grid)
    return {
        "altitude_m": _median(dataset.grid, positions, "altitude_m"),
        "slope_pct": _median(dataset.grid, positions, "slope_pct"),
        "basis": "lot",
        "cells": len(keys),
    }
