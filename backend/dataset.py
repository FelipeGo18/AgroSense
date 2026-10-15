"""El dataset publicado (`data/published/`): lo lee la API, nunca el motor (R6). Solo se lee: la API no lo cambia.

Se carga una vez y queda en memoria. Si falta o no se puede leer, los endpoints que lo necesitan responden 503
`dataset_unavailable` y el log dice por qué; los demás siguen (como las cuentas con la base de datos apagada).
"""

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl

from backend.config.settings import get_settings


class DatasetUnavailable(RuntimeError):
    """No hay dataset publicado que leer. El mensaje dice por qué, para el log."""


@dataclass(frozen=True)
class Municipality:
    municipality_id: str
    name: str
    department_id: str
    department: str
    lat: float | None
    lon: float | None


@dataclass(frozen=True)
class Dataset:
    version: str
    rules_version: str | None
    created_at: datetime
    region: dict[str, Any]
    # Por `municipality_id`, en el orden de la tabla (por código).
    municipalities: dict[str, Municipality]
    sources: list[dict[str, Any]]


def load(folder: Path) -> Dataset:
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise DatasetUnavailable(f"no existe {manifest_path} (se publica con: uv run python -m pipeline.build)")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        municipalities = pl.read_parquet(folder / "municipalities.parquet")
        sources = pl.read_parquet(folder / "sources.parquet")
    except (OSError, ValueError, pl.exceptions.PolarsError) as error:
        raise DatasetUnavailable(f"no se pudo leer el dataset de {folder}: {type(error).__name__}") from error
    return Dataset(
        version=manifest["dataset_version"],
        rules_version=manifest.get("rules_version"),
        created_at=datetime.fromisoformat(manifest["created_at"]),
        region=manifest["region"],
        municipalities={
            row["municipality_id"]: Municipality(
                municipality_id=row["municipality_id"],
                name=row["name"],
                department_id=row["department_id"],
                department=row["department"],
                lat=row["lat"],
                lon=row["lon"],
            )
            for row in municipalities.iter_rows(named=True)
        },
        sources=sources.to_dicts(),
    )


@lru_cache
def _cached(folder: Path) -> Dataset:
    return load(folder)


def get_dataset() -> Dataset:
    """El dataset de `AGROSENSE_DATA_DIR`. Un fallo no se recuerda: en cuanto se publique, se lee."""
    return _cached(get_settings().data_dir.resolve())
