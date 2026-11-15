"""La rejilla común de 250 m en `common/grid.py` (HU-191, pieza A): `cell_id`, `cell_center` y la llave entera de una celda.

Salieron de `pipeline/schema.py` para que la API los use sin importar el pipeline. Aquí se fija que dan lo mismo que la
fórmula del contrato («La rejilla de 250 m»): `cell_id` = «{fila}_{columna}» desde (90° N, 180° O), con paso de 0,0025°.
"""

import pytest

from common import grid
from pipeline import schema

STEP = 0.0025


def contract_cell_id(lat: float, lon: float) -> str:
    """Copia de la fórmula del contrato tal como estaba en `pipeline/schema.py` antes de moverse."""
    return f"{int((90 - lat) // STEP)}_{int((lon + 180) // STEP)}"


def contract_cell_center(cell: str) -> tuple[float, float]:
    row, col = (int(part) for part in cell.split("_"))
    return 90 - (row + 0.5) * STEP, -180 + (col + 0.5) * STEP


# Puntos de la región piloto (Boyacá y Cundinamarca), incluidos algunos justo en el borde de una celda.
SAMPLE_POINTS = [
    (5.8244, -73.0341),  # Duitama
    (5.5353, -73.3678),  # Tunja
    (4.3049, -74.8016),  # Girardot
    (5.0, -73.125),
    (6.0, -72.0),
    (4.0, -75.0),
    (90 - 2320 * STEP, -180 + 58000 * STEP),  # esquina exacta de una celda
    (90 - 2320 * STEP - 1e-9, -180 + 58000 * STEP + 1e-9),  # un pelo dentro de la celda de al lado
    (90 - 2320.5 * STEP, -180 + 58000.5 * STEP),  # el centro de una celda
]


@pytest.mark.parametrize(("lat", "lon"), SAMPLE_POINTS)
def test_cell_id_da_lo_mismo_que_la_formula_del_contrato(lat, lon):
    assert grid.cell_id(lat, lon) == contract_cell_id(lat, lon)


@pytest.mark.parametrize(("lat", "lon"), SAMPLE_POINTS)
def test_cell_center_da_lo_mismo_que_la_formula_del_contrato(lat, lon):
    cell = grid.cell_id(lat, lon)
    assert grid.cell_center(cell) == contract_cell_center(cell)


def test_cell_id_conserva_la_forma_fila_guion_bajo_columna():
    assert isinstance(grid.cell_id(5.8244, -73.0341), str)
    row, col = grid.cell_id(5.8244, -73.0341).split("_")
    assert (int(row), int(col)) == (int((90 - 5.8244) // STEP), int((-73.0341 + 180) // STEP))


def test_el_centro_de_una_celda_cae_en_esa_celda():
    for lat, lon in SAMPLE_POINTS:
        cell = grid.cell_id(lat, lon)
        assert grid.cell_id(*grid.cell_center(cell)) == cell


def test_el_paso_es_de_0_0025_grados_y_las_columnas_son_144000():
    assert grid.GRID_STEP_DEG == STEP
    assert grid.GRID_COLUMNS == 144_000


def test_cell_key_es_fila_por_144000_mas_columna():
    assert grid.cell_key("0_0") == 0
    assert grid.cell_key("2_7") == 2 * 144_000 + 7
    row, col = (int(part) for part in grid.cell_id(5.8244, -73.0341).split("_"))
    assert grid.cell_key(grid.cell_id(5.8244, -73.0341)) == row * 144_000 + col


def test_cell_key_no_repite_llaves_entre_celdas_vecinas():
    cells = {f"{row}_{col}" for row in range(5) for col in range(5)}
    assert len({grid.cell_key(cell) for cell in cells}) == 25


def test_pipeline_schema_sigue_exponiendo_las_mismas_funciones():
    """`pipeline/schema.py` ahora las importa de `common/grid.py`: son las mismas, no una segunda copia."""
    assert schema.cell_id is grid.cell_id and schema.cell_center is grid.cell_center
    assert schema.GRID_STEP_DEG == grid.GRID_STEP_DEG
