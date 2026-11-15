"""`Dataset.grid` (HU-191, pieza A): la altitud de cada celda de `grid_cells`, compacta y opcional (R1).

Solo se leen `cell_id` y `altitude_m`; sin `grid_cells.parquet`, `grid` es `None` y el resto del dataset carga igual.
"""

import numpy as np
import polars as pl

from backend import dataset as dataset_module
from backend.dataset import Grid
from common.grid import cell_key


def test_sin_grid_cells_la_rejilla_es_nula_y_el_resto_carga_igual(dataset):
    assert not (dataset / "grid_cells.parquet").exists()
    loaded = dataset_module.load(dataset)
    assert loaded.grid is None
    assert loaded.municipalities and loaded.sources and loaded.version


def test_con_grid_cells_carga_las_llaves_ordenadas_y_la_altitud_con_nan_donde_falta(dataset):
    # Fuera de orden a propósito: la llave entera (fila * 144000 + columna) debe quedar ordenada, con su altitud al lado.
    # Datos de ejemplo (R5). Solo dos columnas: es lo que `load()` lee.
    table = pl.DataFrame(
        {"cell_id": ["3000_59001", "2999_59000", "3000_59000", "3001_58999"], "altitude_m": [2501.0, 2400.0, None, 2600.0]},
        schema={"cell_id": pl.String, "altitude_m": pl.Float64},
    )
    table.write_parquet(dataset / "grid_cells.parquet")
    loaded = dataset_module.load(dataset)
    assert isinstance(loaded.grid, Grid)
    assert loaded.grid.keys.dtype == np.int64 and loaded.grid.altitude_m.dtype == np.float64
    assert loaded.grid.keys.tolist() == [cell_key("2999_59000"), cell_key("3000_59000"), cell_key("3000_59001"), cell_key("3001_58999")]
    assert np.all(np.diff(loaded.grid.keys) > 0)
    altitudes = loaded.grid.altitude_m
    assert altitudes[0] == 2400.0 and np.isnan(altitudes[1]) and altitudes[2] == 2501.0 and altitudes[3] == 2600.0
    # El resto del dataset carga igual que sin la rejilla.
    assert loaded.municipalities.keys() == dataset_module.load(dataset).municipalities.keys()


def test_el_dataset_por_defecto_no_trae_rejilla():
    assert dataset_module.Dataset.__dataclass_fields__["grid"].default is None
