"""Las versiones de los precios de SIPSA (HU-222): las escriben las actualizaciones y la API solo las lee.

    data/market/                                  # AGROSENSE_MARKET_DIR (volumen `market_data` en Docker Compose)
      current.json                                # qué versión se sirve
      sipsa-20261109T150012-boletin/              # market_price_day.parquet y sources.json
      sipsa-20261108T150020-servicio/

Cada versión es inmutable, se escribe completa en una carpeta aparte y se publica al final cambiando `current.json`:
nadie lee una versión a medias (R1) y cada respuesta dice cuál usó (R4). La temporada (`market_price_season`) no va
aquí: solo cambia una vez al año y sale del dataset publicado.
"""

import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from common.logging import get_logger

log = get_logger("agrosense.market")

CURRENT = "current.json"
PRICES = "market_price_day.parquet"
SOURCES = "sources.json"
# Versiones que se guardan, contando la que se sirve: la anterior queda por si hay que volver atrás a mano.
KEEP = 2
# Cada cuánto vuelve a mirar la API si hay una versión nueva. Solo lee `current.json`, que es chico.
CHECK_EVERY = 60


@dataclass(frozen=True)
class MarketData:
    version: str
    updated_at: datetime
    prices: pl.DataFrame
    # Las filas de `sources` que citan estos precios (R8).
    sources: list[dict[str, Any]]


def load_latest(folder: Path) -> MarketData | None:
    """La versión que dice `current.json`. Sin ella, o si no se puede leer, nada: no se inventa (R1)."""
    pointer = folder / CURRENT
    if not pointer.exists():
        return None
    try:
        info = json.loads(pointer.read_text(encoding="utf-8"))
        version_dir = folder / info["version"]
        return MarketData(
            version=info["version"],
            updated_at=datetime.fromisoformat(info["updated_at"]),
            prices=pl.read_parquet(version_dir / PRICES),
            sources=json.loads((version_dir / SOURCES).read_text(encoding="utf-8")),
        )
    except (OSError, ValueError, KeyError, pl.exceptions.PolarsError) as error:
        log.warning("market_version_unreadable", detail=f"No se pudo leer la versión de precios de {folder}: {type(error).__name__}")
        return None


def write_version(folder: Path, kind: str, prices: pl.DataFrame, sources: list[dict[str, Any]], now: datetime) -> MarketData:
    """Escribe una versión nueva y la deja como la que se sirve. `kind` dice de dónde salió: `boletin` o `servicio`."""
    folder.mkdir(parents=True, exist_ok=True)
    version = f"sipsa-{now:%Y%m%dT%H%M%S}-{kind}"
    staging = folder / f"{version}.tmp"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    prices.write_parquet(staging / PRICES)
    (staging / SOURCES).write_text(json.dumps(sources, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    target = folder / version
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
    pointer = folder / f"{CURRENT}.tmp"
    pointer.write_text(json.dumps({"version": version, "updated_at": now.isoformat()}), encoding="utf-8")
    pointer.replace(folder / CURRENT)
    _prune(folder, version)
    return MarketData(version=version, updated_at=now, prices=prices, sources=sources)


def _prune(folder: Path, keep_version: str) -> None:
    versions = sorted(p for p in folder.glob("sipsa-*") if p.is_dir() and not p.name.endswith(".tmp"))
    for old in versions[: max(0, len(versions) - KEEP)]:
        if old.name != keep_version:
            shutil.rmtree(old, ignore_errors=True)


class Served:
    """Lo que sirve la API: la última versión, que vuelve a mirar como mucho cada `CHECK_EVERY` segundos.

    Así una versión que deja el servicio `market` se sirve en un minuto, sin reiniciar la API y sin que la API baje nada.
    """

    def __init__(self) -> None:
        self._data: MarketData | None = None
        self._version: str | None = None
        self._checked_at = float("-inf")

    def get(self, folder: Path, now: float | None = None) -> MarketData | None:
        now = time.monotonic() if now is None else now
        if now - self._checked_at < CHECK_EVERY:
            return self._data
        self._checked_at = now
        try:
            version = json.loads((folder / CURRENT).read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError):
            return self._data
        if version != self._version:
            data = load_latest(folder)
            if data is not None:
                self._data, self._version = data, data.version
                log.info("market_version_loaded", detail=f"Se sirve la versión de precios {data.version}")
        return self._data


served = Served()
