"""Los datos de la señal de mercado (HU-073): qué central le toca a un municipio y el índice estacional de un cultivo en
el mes de cosecha. Son lecturas del dataset publicado, sin errores HTTP, sin base de datos y sin guardar nada (R9). El
motor recibe solo el número (`backend.engine.market_signal`, R6).
"""

import polars as pl

from backend.dataset import Dataset, Municipality


def market_for(dataset: Dataset, municipality: Municipality) -> str | None:
    """El `market_id` de SIPSA que da el precio en el departamento del municipio (`department_markets` de la región).

    Un departamento que no está en el mapa, o una región sin mapa, no tiene central: None. Nunca se usa otra central
    por defecto (R1).
    """
    # El pipeline ya validó que llaves y centrales son texto y existen (`pipeline.build.validate_department_markets`).
    return (dataset.region.get("department_markets") or {}).get(municipality.department_id)


def seasonal_index(dataset: Dataset, crop_id: str, market_id: str | None, month: int) -> tuple[float | None, int | None]:
    """El `seasonal_index` y sus `years` de `market_month` para el cultivo, la central y el mes de cosecha (1 a 12).

    Sin `market_month`, sin central o sin fila (un cultivo sin producto en SIPSA, o sin 3 años completos en esa
    central, no tiene filas): `(None, None)` (R1).
    """
    table = dataset.market_month
    if table is None or market_id is None:
        return None, None
    rows = table.filter((pl.col("crop_id") == crop_id) & (pl.col("market_id") == market_id) & (pl.col("month") == month)).select(
        "seasonal_index", "years"
    )
    if rows.is_empty():
        return None, None
    index, years = rows.row(0)
    if index is None:
        return None, None
    return float(index), int(years) if years is not None else None
