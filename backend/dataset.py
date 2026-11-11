"""El dataset publicado (`data/published/`): lo lee la API, nunca el motor (R6). Solo se lee: la API no lo cambia.

Se carga una vez y queda en memoria. Si falta o no se puede leer, los endpoints que lo necesitan responden 503
`dataset_unavailable` y el log dice por qué; los demás siguen (como las cuentas con la base de datos apagada).
"""
import json
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl
import shapely
from shapely.geometry.base import BaseGeometry

from backend.config.settings import get_settings
from backend.engine.stages import StageSpan


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
    # Mediana de la pendiente de sus celdas de `grid_cells` (decisión 14); nula hasta HU-206.
    slope_pct: float | None = None


@dataclass(frozen=True)
class Dataset:
    version: str
    rules_version: str | None
    created_at: datetime
    region: dict[str, Any]
    # Por `municipality_id`, en el orden de la tabla (por código).
    municipalities: dict[str, Municipality]
    sources: list[dict[str, Any]]
    # El límite de cada municipio (WGS84), preparado para preguntar rápido si un lote cae dentro. Vacío si el dataset
    # no trae `municipality_boundaries`: entonces no se puede dibujar ni validar un lote (R1).
    boundaries: dict[str, BaseGeometry]
    # Las fichas del catálogo agronómico (`crops`), por `crop_id`, en orden. Vacío si el dataset no las trae (R1).
    crops: dict[str, dict[str, Any]]
    # Las etapas de cada cultivo en orden (`crop_stages`), para la etapa por calendario (HU-220). Vacío sin catálogo.
    stages: dict[str, list[StageSpan]]
    # El suelo estimado de cada municipio (`soil_municipality`, HU-181), por `municipality_id`. Vacío si el dataset no
    # lo trae: entonces el suelo es `insufficient_data` (R1).
    soil: dict[str, dict[str, Any]]
    # Precios mayoristas de SIPSA (HU-221). Nulos si el dataset publicado no los trae: no se inventan.
    market_prices: pl.DataFrame | None = None
    market_season: pl.DataFrame | None = None
    # El último precio de cada producto en cada central (`market_price_latest`), ya calculado por el pipeline.
    market_latest: pl.DataFrame | None = None
    # El último día con precios, para compararlo con las versiones de las actualizaciones (HU-222). Nulo sin precios.
    market_last_date: date | None = None
    # Las centrales de la región: (código de SIPSA, nombre), de `region.yaml` o, si no las dice, de los precios.
    markets: tuple[tuple[str, str], ...] = ()


def load(folder: Path) -> Dataset:
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise DatasetUnavailable(f"no existe {manifest_path} (se publica con: uv run python -m pipeline.build)")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        municipalities = pl.read_parquet(folder / "municipalities.parquet")
        sources = pl.read_parquet(folder / "sources.parquet")
        boundaries_path = folder / "municipality_boundaries.parquet"
        boundaries = pl.read_parquet(boundaries_path) if boundaries_path.exists() else None
        crops_path = folder / "crops.parquet"
        crops = pl.read_parquet(crops_path).to_dicts() if crops_path.exists() else []
        stages_path = folder / "crop_stages.parquet"
        stage_rows = pl.read_parquet(stages_path).to_dicts() if stages_path.exists() else []
        soil_path = folder / "soil_municipality.parquet"
        soil = pl.read_parquet(soil_path).to_dicts() if soil_path.exists() else []
        prices_path, season_path = folder / "market_price_day.parquet", folder / "market_price_season.parquet"
        market_prices = pl.read_parquet(prices_path) if prices_path.exists() else None
        market_season = pl.read_parquet(season_path) if season_path.exists() else None
        latest_path = folder / "market_price_latest.parquet"
        market_latest = pl.read_parquet(latest_path) if latest_path.exists() else None
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
                slope_pct=row.get("slope_pct"),
            )
            for row in municipalities.iter_rows(named=True)
        },
        sources=sources.to_dicts(),
        boundaries={} if boundaries is None else _geometries(boundaries),
        crops={crop["crop_id"]: crop for crop in crops},
        stages=_stages(stage_rows),
        soil={row["municipality_id"]: row for row in soil},
        market_prices=market_prices,
        market_season=market_season,
        market_latest=market_latest,
        market_last_date=market_latest["market_date"].max() if market_latest is not None and market_latest.height else None,
        markets=_markets(manifest["region"], market_latest),
    )


def _markets(region: dict[str, Any], latest: pl.DataFrame | None) -> tuple[tuple[str, str], ...]:
    """Las centrales de la región en orden de código: las de `region.yaml` o, si no las dice, las que tienen precios."""
    if region.get("markets"):
        return tuple(sorted(region["markets"].items()))
    if latest is None:
        return ()
    return tuple(latest.select("market_id", "market").unique().sort("market_id").iter_rows())


def _stages(rows: list[dict[str, Any]]) -> dict[str, list[StageSpan]]:
    """Las filas ya vienen en el orden de las etapas (el pipeline las ordena)."""
    stages: dict[str, list[StageSpan]] = {}
    for row in rows:
        stages.setdefault(row["crop_id"], []).append(StageSpan(row["stage"], row["days"]))
    return stages


def _geometries(table: pl.DataFrame) -> dict[str, BaseGeometry]:
    geometries = {}
    for municipality_id, wkb in table.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        shapely.prepare(geometry)
        geometries[municipality_id] = geometry
    return geometries


@lru_cache
def _cached(folder: Path) -> Dataset:
    return load(folder)


def get_dataset() -> Dataset:
    """El dataset de `AGROSENSE_DATA_DIR`. Un fallo no se recuerda: en cuanto se publique, se lee."""
    return _cached(get_settings().data_dir.resolve())
