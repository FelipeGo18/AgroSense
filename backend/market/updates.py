"""Las dos actualizaciones de los precios de SIPSA (HU-222). Las corre el servicio `market` de Docker Compose con
supercronic, en los horarios del `.env`; la API nunca baja nada.

    python -m backend.market.updates diario    # el precio del día del boletín del DANE (unos 340 KB)
    python -m backend.market.updates semanal   # la serie completa del servicio web de SIPSA (unos 300 MB)

- **Diario** (de lunes a viernes, después de las 2:00 p. m., cuando el DANE publica): baja el anexo del boletín de cada
  día hábil que falte, hasta `BACKFILL_DAYS` atrás, y le suma esos días a la última versión. Un día sin boletín (festivo)
  no es un error. Sin días nuevos no escribe nada.
- **Semanal** (los domingos): baja la respuesta completa del servicio y la deja como versión nueva. Esos precios sí
  traen el mínimo y el máximo y reemplazan los días del boletín; solo se conservan los días del boletín posteriores al
  último día del servicio en cada central.

La temporada (`market_price_season`) y el precio por cultivo (`market_month`) no se recalculan aquí: solo cambian una vez
al año, cuando cierra un año completo, y salen del dataset publicado (`uv run python -m pipeline.build`).

Si algo falla, no se toca la versión que se sirve (R1), el log dice por qué y el comando termina con error.
"""

import argparse
import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import polars as pl

from backend.config.settings import get_settings
from backend.market.store import MarketData, load_latest, write_version
from common import logging
from pipeline.sources import sipsa, sipsa_boletin

log = logging.get_logger("agrosense.market")

# Colombia no cambia de hora en el año: UTC−5 fijo, sin depender de la base de zonas horarias del sistema.
BOGOTA = timezone(timedelta(hours=-5), "Bogotá")
# Cuántos días atrás busca el boletín diario los días hábiles que falten (por ejemplo, si el equipo estuvo apagado).
BACKFILL_DAYS = 10
# Una descarga cortada del servicio (el DANE a veces cierra la conexión a mitad de los 300 MB) se reintenta.
ATTEMPTS = 3
PAUSE_S = 60
# Una actualización que lleva más de esto con el candado puesto se da por muerta.
LOCK_STALE_S = 6 * 3600


class UpdateError(RuntimeError):
    """La actualización no se pudo hacer. El mensaje dice por qué."""


@contextmanager
def _lock(folder: Path) -> Iterator[None]:
    """Una sola actualización a la vez sobre la misma carpeta, aunque se corra una a mano mientras corre el cron."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ".lock"
    try:
        if path.exists() and time.time() - path.stat().st_mtime > LOCK_STALE_S:
            path.unlink(missing_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise UpdateError(f"ya hay otra actualización de precios corriendo en {folder}") from error
    os.close(fd)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _published(published: Path) -> tuple[pl.DataFrame, list[dict[str, Any]]]:
    """Los precios y la fuente de SIPSA del dataset publicado: el punto de partida si no hay ninguna versión bajada."""
    path = published / "market_price_day.parquet"
    if not path.exists():
        raise UpdateError(f"no hay precios publicados en {published} ni una versión bajada en la que basarse")
    sources = pl.read_parquet(published / "sources.parquet")
    return pl.read_parquet(path), sources.filter(pl.col("source_id") == sipsa.SOURCE_ID).to_dicts()


def base(folder: Path, published: Path) -> tuple[pl.DataFrame, list[dict[str, Any]]]:
    """Los precios de los que se parte: la última versión bajada si es al menos tan nueva como la publicada."""
    latest = load_latest(folder)
    published_prices, published_sources = _published(published) if (published / "market_price_day.parquet").exists() else (None, [])
    if latest is not None and (published_prices is None or latest.prices["date"].max() >= published_prices["date"].max()):
        return latest.prices, latest.sources
    if published_prices is None:
        raise UpdateError(f"no hay precios publicados en {published} ni una versión bajada en la que basarse")
    return published_prices, published_sources


def markets(published: Path) -> dict[str, str]:
    """Las centrales de la región (`region.yaml`, copiado en el manifiesto del dataset publicado)."""
    try:
        found = json.loads((published / "manifest.json").read_text(encoding="utf-8"))["region"].get("markets")
    except (OSError, ValueError, KeyError) as error:
        raise UpdateError(f"no se pudo leer el manifiesto de {published}: {type(error).__name__}") from error
    if not found:
        raise UpdateError("la región no dice qué centrales de abastos publicar (`markets` en region.yaml)")
    return found


def _keep_names(new: pl.DataFrame, previous: pl.DataFrame) -> pl.DataFrame:
    """El boletín escribe algunos nombres distinto que el servicio («Lechuga Batavia» y «Lechuga batavia»): para un
    producto que ya se conoce se usan el nombre, el grupo y el asterisco de antes, y la web no cambia."""
    known = previous.sort("date").group_by("product_id").agg(pl.col("product", "group", "several_varieties").last())
    return (
        new.join(known, on="product_id", how="left", suffix="_known")
        .with_columns(pl.coalesce(f"{col}_known", col).alias(col) for col in ("product", "group", "several_varieties"))
        .select(list(sipsa.SCHEMA))
    )


def _validate(prices: pl.DataFrame) -> None:
    try:
        sipsa.validate(prices, {sipsa.SOURCE_ID, sipsa_boletin.SOURCE_ID})
    except sipsa.PricesError as error:
        raise UpdateError(str(error)) from error


def _bulletin_source(prices: pl.DataFrame, downloaded_at: str, previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Las fuentes de una versión: las de antes sin el boletín, y el boletín si quedan días suyos."""
    rows = [row for row in previous if row["source_id"] != sipsa_boletin.SOURCE_ID]
    days = prices.filter(pl.col("source_id") == sipsa_boletin.SOURCE_ID)
    if days.height:
        rows.append(sipsa_boletin.source(days, downloaded_at))
    return rows


def daily(
    folder: Path,
    published: Path,
    now: datetime | None = None,
    download: Callable[[date, Path], Path | None] = sipsa_boletin.download,
) -> MarketData | None:
    """Suma los días hábiles que falten desde el boletín diario. Sin días nuevos, no escribe nada y devuelve nada."""
    now = (now or datetime.now(UTC)).astimezone(BOGOTA)
    with _lock(folder):
        regional = markets(published)
        prices, sources = base(folder, published)
        last = prices["date"].max()
        today = now.date()
        days = [today - timedelta(days=n) for n in range(BACKFILL_DAYS, -1, -1)]
        days = [day for day in days if day > last and day.weekday() < 5]
        raw = folder / "raw"
        found = []
        try:
            for day in days:
                path = download(day, raw)
                if path is None:
                    log.info("market_bulletin_missing", day=str(day), detail=f"El DANE no publicó boletín el {day} (festivo o todavía no)")
                    continue
                try:
                    rows = sipsa_boletin.prices(path, day, regional)
                except sipsa_boletin.BulletinError as error:
                    raise UpdateError(str(error)) from error
                without = sorted(set(regional) - set(rows["market_id"].unique().to_list()))
                if len(without) == len(regional):
                    # Corabastos sale casi todos los días: si ninguna central de la región sale, puede que el DANE haya
                    # cambiado los nombres de las columnas (`sipsa_boletin.COLUMNS`).
                    log.warning(
                        "market_bulletin_empty",
                        day=str(day),
                        detail=f"El boletín del {day} no trae precios de ninguna central de la región",
                    )
                elif without:
                    names = ", ".join(regional[market_id] for market_id in without)
                    log.info("market_bulletin_partial", day=str(day), detail=f"El boletín del {day} no trae precios de {names}")
                found.append(rows)
        finally:
            shutil.rmtree(raw, ignore_errors=True)
        new = pl.concat(found) if found else pl.DataFrame(schema=sipsa.SCHEMA)
        new = new.join(prices.select("product_id", "market_id", "date"), on=["product_id", "market_id", "date"], how="anti")
        if new.is_empty():
            log.info("market_no_news", detail=f"No hay precios nuevos del boletín: lo servido llega hasta el {last}")
            return None
        combined = pl.concat([prices, _keep_names(new, prices)]).sort("product_id", "market_id", "date")
        _validate(combined)
        downloaded_at = now.astimezone(UTC).isoformat(timespec="seconds")
        data = write_version(folder, "boletin", combined, _bulletin_source(combined, downloaded_at, sources), now)
    log.info(
        "market_refreshed",
        version=data.version,
        rows_added=new.height,
        detail=f"Precios del boletín diario: {new.height} precios nuevos, hasta el {new['date'].max()}; versión {data.version}",
    )
    return data


def _download_service(raw: Path, download: Callable[[Path], Path], pause: float) -> None:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            download(raw)
            return
        except OSError as error:  # cortes de red, `IncompleteRead`, tiempo o tamaño de más
            if attempt == ATTEMPTS:
                raise UpdateError(f"la descarga de SIPSA falló {ATTEMPTS} veces: {type(error).__name__}: {error}") from error
            log.warning("market_download_retry", attempt=attempt, reason=f"{type(error).__name__}: {error}")
            time.sleep(pause * attempt)


def weekly(
    folder: Path,
    published: Path,
    now: datetime | None = None,
    download: Callable[[Path], Path] = sipsa.download,
    pause: float = PAUSE_S,
) -> MarketData:
    """Baja la serie completa del servicio web y la deja como versión nueva, con el mínimo y el máximo de cada día."""
    now = (now or datetime.now(UTC)).astimezone(BOGOTA)
    with _lock(folder):
        regional = markets(published)
        raw = folder / "raw"
        log.info("market_download_started", detail="Bajando la serie completa de SIPSA del DANE (unos 300 MB)")
        try:
            _download_service(raw, download, pause)
            service, downloaded_at = sipsa.read_cache(regional, raw)
        finally:
            # La descarga pesa unos 300 MB: no se guarda, ya quedó leída (o falló).
            shutil.rmtree(raw, ignore_errors=True)
        previous = load_latest(folder)
        bulletin = pl.DataFrame(schema=sipsa.SCHEMA)
        if previous is not None:
            # Los días del boletín posteriores al último día del servicio en su central siguen sirviendo.
            last = service.group_by("market_id").agg(pl.col("date").max().alias("last"))
            bulletin = (
                previous.prices.filter(pl.col("source_id") == sipsa_boletin.SOURCE_ID)
                .join(last, on="market_id", how="left")
                .filter(pl.col("last").is_null() | (pl.col("date") > pl.col("last")))
                .select(list(sipsa.SCHEMA))
            )
        combined = pl.concat([service, bulletin]).sort("product_id", "market_id", "date")
        _validate(combined)
        sources = [sipsa.source(service, downloaded_at)]
        if bulletin.height:
            sources.append(next(row for row in previous.sources if row["source_id"] == sipsa_boletin.SOURCE_ID))
        data = write_version(folder, "servicio", combined, sources, now)
    log.info(
        "market_refreshed",
        version=data.version,
        rows=combined.height,
        detail=f"Precios de SIPSA del servicio web: {service.height} filas hasta el {service['date'].max()}, más "
        f"{bulletin.height} del boletín; versión {data.version}",
    )
    return data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Actualiza los precios de SIPSA (HU-222).")
    parser.add_argument("cual", choices=["diario", "semanal"], help="diario: boletín del DANE; semanal: serie completa del servicio")
    args = parser.parse_args(argv)
    settings = get_settings()
    logging.configure(settings.log_level, settings.log_format)
    job = daily if args.cual == "diario" else weekly
    try:
        job(settings.market_dir, settings.data_dir)
    except (UpdateError, OSError, ValueError, pl.exceptions.PolarsError) as error:
        log.error(
            "market_refresh_failed",
            job=args.cual,
            detail=f"No se actualizaron los precios ({args.cual}): {type(error).__name__}: {error}. Se sigue sirviendo lo de antes",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
