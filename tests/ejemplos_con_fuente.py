"""El dataset de ejemplo con la lluvia rotulada con la fuente de su tabla, para las pruebas de la señal de agua (HU-071).

`data/examples/` rotula todas sus filas con `source_id = ejemplo` (R5). La señal de agua y `/trends` solo leen las filas
rotuladas con la fuente que dice `catalog/sources.yaml` (`backend/api/monthly_climate.py`): con las del ejemplo, ninguna
fuente tiene lluvia. Esta copia les pone la fuente que cada tabla publica según el contrato (`precip_month`: GPM IMERG;
`climate_month`: NASA POWER), como hace `tests/test_tendencias.py`. Las cifras siguen siendo de ejemplo: la copia vive en
una carpeta temporal y su versión sigue siendo `ejemplo` (R5).
"""

import shutil
from pathlib import Path

import polars as pl

EXAMPLES = Path("data/examples")
# La fuente que publica cada tabla de lluvia y clima mensual (contrato; `catalog/sources.yaml` de la región piloto).
TABLE_SOURCES = {"precip_month": "imerg", "climate_month": "nasa_power"}


def label_sources(folder: Path) -> None:
    """Cambia `source_id` de `precip_month` y `climate_month` de la carpeta por la fuente de su tabla."""
    for table, source_id in TABLE_SOURCES.items():
        path = folder / f"{table}.parquet"
        pl.read_parquet(path).with_columns(pl.lit(source_id).alias("source_id")).write_parquet(path)


def examples_with_sources(folder: Path) -> Path:
    """Una copia de `data/examples/` en `folder`, con la lluvia rotulada con su fuente."""
    shutil.copytree(EXAMPLES.resolve(), folder)
    label_sources(folder)
    return folder
