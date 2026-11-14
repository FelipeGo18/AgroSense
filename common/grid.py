"""La rejilla común de 250 m (HU-191; contrato, «La rejilla de 250 m»).

Fórmulas de celda (`cell_id`), centro de celda (`cell_center`) y llave entera (`cell_key`)
para indexar la rejilla sin importar el pipeline ni el backend.
"""

GRID_STEP_DEG = 0.0025
GRID_COLUMNS = 144_000


def cell_id(lat: float, lon: float) -> str:
    """La celda de la rejilla común que contiene un punto: fila y columna desde (90° N, 180° O)."""
    row = int((90 - lat) // GRID_STEP_DEG)
    col = int((lon + 180) // GRID_STEP_DEG)
    return f"{row}_{col}"


def cell_center(cell: str) -> tuple[float, float]:
    """El centro (lat, lon) de una celda de la rejilla común."""
    row, col = (int(p) for p in cell.split("_"))
    return 90 - (row + 0.5) * GRID_STEP_DEG, -180 + (col + 0.5) * GRID_STEP_DEG


def cell_key(cell: str) -> int:
    """Llave entera de una celda: fila * GRID_COLUMNS + columna."""
    row, col = (int(p) for p in cell.split("_"))
    return row * GRID_COLUMNS + col
