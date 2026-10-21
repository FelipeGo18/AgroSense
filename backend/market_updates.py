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
import time as time_module
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


def reload_if_newer(folder: Path) -> None:
    """Si otro proceso dejó una versión nueva (por ejemplo, `python -m backend.market_updates` a mano), se sirve esa.

    Solo lee `current.json`, que es chico; las tablas se leen si la versión cambió.
    """
    try:
        version = json.loads((folder / CURRENT).read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return
    served = current()
    if served is None or served.version != version:
        data = load_latest(folder)
        if data is not None:
            log.info("market_version_loaded", detail=f"Se sirve la versión de precios {data.version}, que dejó otro proceso")


# Una descarga cortada (el DANE a veces cierra la conexión a mitad de los 300 MB) se reintenta enseguida, unas veces.
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_PAUSE = 30


def _download_with_retries(download: Callable[[Path], Path], raw: Path, pause: float) -> None:
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            download(raw)
            return
        except OSError as error:  # incluye los cortes de red (`IncompleteRead`, `URLError`, tiempo agotado)
            if attempt == DOWNLOAD_ATTEMPTS:
                raise
            log.warning(
                "market_download_retry",
                detail=f"La descarga de SIPSA se cortó ({type(error).__name__}); intento {attempt + 1} de {DOWNLOAD_ATTEMPTS}",
            )
            time_module.sleep(pause)


def refresh(
    folder: Path,
    markets: dict[str, str],
    download: Callable[[Path], Path] = sipsa.download,
    now: datetime | None = None,
    pause: float | None = None,
) -> MarketData:
    """Baja los precios, los valida y, solo si todo sale bien, los deja como la versión que se sirve.

    Lanza el error si algo falla: quien llama decide qué hacer (el bucle diario lo escribe en el log y sigue).
    """
    with _lock:
        updated_at = (now or datetime.now(UTC)).astimezone(BOGOTA)
        version = f"sipsa-{updated_at:%Y%m%dT%H%M}"
        raw = folder / "raw"
        try:
            _download_with_retries(download, raw, DOWNLOAD_PAUSE if pause is None else pause)
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
    """El bucle de la API: al arrancar, baja si lo que hay es viejo; después, cada día a las 3:00 p. m.

    Mira el reloj de pared cada `CHECK_EVERY` segundos en vez de dormir hasta las 3:00 p. m. de una vez: una espera
    larga se mide con el reloj interno, que se detiene si el equipo (o la máquina virtual de Docker) se suspende, y la
    actualización se atrasaba horas. Así, al despertar, se pone al día en minutos.
    """
    load_latest(folder)
    retry_at: datetime | None = None
    while True:
        retry_at = await check_once(folder, markets, retry_at)
        await asyncio.sleep(CHECK_EVERY)


# Cada cuánto se mira el reloj, y cuánto se espera para reintentar después de un fallo (el DANE a veces publica tarde).
CHECK_EVERY = 300
RETRY_AFTER = timedelta(hours=1)


async def check_once(
    folder: Path,
    markets: dict[str, str],
    retry_at: datetime | None = None,
    now: datetime | None = None,
    download: Callable[[Path], Path] = sipsa.download,
) -> datetime | None:
    """Una vuelta del bucle: si lo servido es viejo (y no toca esperar un reintento), baja los precios.

    Devuelve cuándo reintentar si falló, o nada.
    """
    now = now or datetime.now(UTC)
    reload_if_newer(folder)
    if not is_stale(current(), now) or (retry_at is not None and now < retry_at):
        return retry_at
    served = current()
    showing = served.version if served else "el dataset publicado"
    log.info("market_refresh_started", detail=f"Bajando los precios de SIPSA del DANE; mientras tanto se sirve {showing}")
    try:
        # En otro hilo: la API sigue atendiendo mientras baja y lee los 300 MB.
        await asyncio.to_thread(refresh, folder, markets, download, now)
    # Cualquier fallo (red, XML roto, validación): el bucle no se cae y la API sigue con lo que tenía.
    except Exception as error:
        retry = now + RETRY_AFTER
        log.warning(
            "market_refresh_failed",
            detail=f"No se pudieron actualizar los precios de SIPSA ({type(error).__name__}: {error}); se sigue sirviendo "
            f"{showing} y se reintenta a las {retry.astimezone(BOGOTA):%H:%M} de Bogotá",
        )
        return retry
    return None


def main() -> None:
    from backend.dataset import get_dataset

    settings = get_settings()
    markets = get_dataset().region["markets"]
    data = refresh(settings.market_dir, markets)
    print(f"Precios de SIPSA actualizados: versión {data.version}, {data.prices.height} filas, hasta el {data.prices['date'].max()}.")


if __name__ == "__main__":
    main()
