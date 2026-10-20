"""Precios de SIPSA al día (HU-222): la API los baja del DANE una vez al día y los sirve sin reiniciarse.

El DANE publica los precios diarios a las 2:00 p. m. (hora de Colombia). A las 3:00 p. m. la API baja la respuesta
completa del servicio, la lee con el mismo adaptador del pipeline (`pipeline/sources/sipsa.py`), la valida con las
mismas reglas (`pipeline.build.validate_market`) y la guarda como una versión nueva en `AGROSENSE_MARKET_DIR`:

    data/market/
      current.json                 # qué versión se sirve
      sipsa-20261021T1500/         # market_price_day.parquet y market_price_season.parquet
      raw/                         # la descarga del día; se borra al terminar

Cada versión es inmutable y tiene nombre propio: la respuesta dice cuál usó (R4). Si la descarga o la validación
fallan, se sigue sirviendo la última versión buena y el log dice por qué: nunca se mezclan datos de dos versiones ni
se sirve una tabla a medias (R1). Sin ninguna versión bajada, la API sirve los precios de `data/published`.

    python -m backend.market_updates     # baja los precios ahora, una vez, sin esperar a las 3:00 p. m.
"""

import asyncio
import json
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path

import polars as pl

from backend.config.logging import get_logger
from backend.config.settings import get_settings
from pipeline.build import validate_market
from pipeline.sources import sipsa

log = get_logger("agrosense.market")

# Colombia no cambia de hora en el año: UTC−5 fijo, sin depender de la base de zonas horarias del sistema.
BOGOTA = timezone(timedelta(hours=-5), "Bogotá")
# El DANE publica a las 2:00 p. m.; se baja a las 3:00 p. m. para darle margen.
DAILY_AT = time(15, 0)
CURRENT = "current.json"
# Versiones que se guardan, contando la que se sirve: la anterior queda por si hay que volver atrás a mano.
KEEP = 2


@dataclass(frozen=True)
class MarketData:
    version: str
    updated_at: datetime
    prices: pl.DataFrame
    season: pl.DataFrame


_lock = threading.Lock()
_current: MarketData | None = None


def current() -> MarketData | None:
    """La última versión bajada que se está sirviendo, o nada si no se ha bajado ninguna."""
    return _current


def _serve(data: MarketData | None) -> None:
    global _current
    _current = data


def load_latest(folder: Path) -> MarketData | None:
    """Lee la versión que dice `current.json`. Sin ella, o si no se puede leer, nada: no se inventa."""
    pointer = folder / CURRENT
    if not pointer.exists():
        return None
    try:
        info = json.loads(pointer.read_text(encoding="utf-8"))
        version_dir = folder / info["version"]
        data = MarketData(
            version=info["version"],
            updated_at=datetime.fromisoformat(info["updated_at"]),
            prices=pl.read_parquet(version_dir / "market_price_day.parquet"),
            season=pl.read_parquet(version_dir / "market_price_season.parquet"),
        )
    except (OSError, ValueError, KeyError, pl.exceptions.PolarsError) as error:
        log.warning("market_version_unreadable", detail=f"No se pudo leer la versión de precios de {folder}: {type(error).__name__}")
        return None
    _serve(data)
    return data


def refresh(
    folder: Path, markets: dict[str, str], download: Callable[[Path], Path] = sipsa.download, now: datetime | None = None
) -> MarketData:
    """Baja los precios, los valida y, solo si todo sale bien, los deja como la versión que se sirve.

    Lanza el error si algo falla: quien llama decide qué hacer (el bucle diario lo escribe en el log y sigue).
    """
    with _lock:
        updated_at = (now or datetime.now(UTC)).astimezone(BOGOTA)
        version = f"sipsa-{updated_at:%Y%m%dT%H%M}"
        raw = folder / "raw"
        try:
            download(raw)
            prices, _ = sipsa.read_cache(markets, raw)
            validate_market(prices, pl.DataFrame({"source_id": [sipsa.SOURCE_ID]}))
            season = sipsa.seasonal(prices)
            # Se escribe en una carpeta aparte y se renombra al final: nadie lee una versión a medio escribir.
            staging = folder / f"{version}.tmp"
            shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True)
            prices.write_parquet(staging / "market_price_day.parquet")
            season.write_parquet(staging / "market_price_season.parquet")
            target = folder / version
            shutil.rmtree(target, ignore_errors=True)
            staging.rename(target)
            pointer = folder / f"{CURRENT}.tmp"
            pointer.write_text(json.dumps({"version": version, "updated_at": updated_at.isoformat()}), encoding="utf-8")
            pointer.replace(folder / CURRENT)
        finally:
            # La descarga pesa unos 300 MB: no se guarda, ya quedó leída en las tablas (o falló).
            shutil.rmtree(raw, ignore_errors=True)
        _prune(folder, version)
        data = MarketData(version=version, updated_at=updated_at, prices=prices, season=season)
        _serve(data)
    last = prices["date"].max()
    log.info("market_refreshed", detail=f"Precios de SIPSA actualizados: versión {version}, {prices.height} filas, hasta el {last}")
    return data


def _prune(folder: Path, keep_version: str) -> None:
    versions = sorted(p for p in folder.glob("sipsa-*") if p.is_dir() and not p.name.endswith(".tmp"))
    for old in versions[: max(0, len(versions) - KEEP)]:
        if old.name != keep_version:
            shutil.rmtree(old, ignore_errors=True)


def next_run(now: datetime) -> datetime:
    """La próxima vez que toca bajar los precios: hoy a las 3:00 p. m. de Bogotá, o mañana si ya pasó."""
    local = now.astimezone(BOGOTA)
    run = datetime.combine(local.date(), DAILY_AT, tzinfo=BOGOTA)
    return run if local < run else run + timedelta(days=1)


def is_stale(data: MarketData | None, now: datetime) -> bool:
    """Hace falta bajar ya si no hay versión o si la que hay es anterior a la última publicación del DANE."""
    if data is None:
        return True
    return data.updated_at < next_run(now) - timedelta(days=1)


async def run_daily(folder: Path, markets: dict[str, str]) -> None:
    """El bucle de la API: al arrancar, baja si lo que hay es viejo; después, cada día a las 3:00 p. m."""
    load_latest(folder)
    while True:
        now = datetime.now(UTC)
        if is_stale(current(), now):
            try:
                # En otro hilo: la API sigue atendiendo mientras baja y lee los 300 MB.
                await asyncio.to_thread(refresh, folder, markets)
            # Cualquier fallo (red, XML roto, validación): el bucle no se cae y la API sigue con lo que tenía.
            except Exception as error:
                served = current()
                log.warning(
                    "market_refresh_failed",
                    detail=f"No se pudieron actualizar los precios de SIPSA ({type(error).__name__}: {error}); "
                    f"se sigue sirviendo {served.version if served else 'el dataset publicado'}",
                )
                # Se reintenta en una hora, no al día siguiente: el DANE a veces publica tarde.
                await asyncio.sleep(3600)
                continue
        wait = (next_run(datetime.now(UTC)) - datetime.now(UTC)).total_seconds()
        await asyncio.sleep(max(wait, 1))


def main() -> None:
    from backend.dataset import get_dataset

    settings = get_settings()
    markets = get_dataset().region["markets"]
    data = refresh(settings.market_dir, markets)
    print(f"Precios de SIPSA actualizados: versión {data.version}, {data.prices.height} filas, hasta el {data.prices['date'].max()}.")


if __name__ == "__main__":
    main()
