"""Clima diario: NASA POWER (HU-041; specs/02-contratos.md, tabla `climate_day`).

Fuente: la API diaria por punto del proyecto POWER del Langley Research Center de la NASA (comunidad AG, sin cuenta).
Es un **reanálisis** (MERRA-2 y, en los días recientes, GEOS-IT): un modelo con observaciones asimiladas, no una
observación directa de satélite ni de estación.

Su celda mide 0,5° de latitud por 0,625° de longitud (unos 55 × 70 km en la región), y todos los puntos de una celda
reciben la misma serie. Por eso se baja una vez por celda y no por municipio: los 239 municipios de Boyacá y
Cundinamarca caen en 20 celdas. Comprobado el 9 de noviembre de 2026: Úmbita y Chía, a 70 km, dan la misma serie y la
misma altura de celda; La Capilla y Tenza, a 3 km pero a lado y lado de un borde, dan otra.

La respuesta trae la altura de la celda (`climate_cell_elevation_m`). Con ella y la altitud del municipio (NASADEM,
HU-206) se corrige la temperatura con el gradiente de `pipeline/region.yaml` (HU-044). Un municipio sin altitud no tiene
filas en `climate_day`: no se publica una temperatura sin corregir como si lo estuviera (R1).

La lluvia diaria (`PRECTOTCORR`) se baja en la misma consulta y queda en la caché para la lluvia mensual (HU-042).
"""

import json
import math
import time
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl

from common.logging import get_logger
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.nasa_power")

SOURCE_ID = "nasa_power"
API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PAGE_URL = "https://power.larc.nasa.gov/"
COMMUNITY = "AG"
# Mínima y máxima a 2 m (°C) y lluvia corregida (mm/día). Sus series empiezan en 1981.
PARAMETERS = ("T2M_MIN", "T2M_MAX", "PRECTOTCORR")
FIRST_DAY = date(1981, 1, 1)
# La rejilla de MERRA-2, la de POWER para estas variables: celdas centradas en múltiplos de estos pasos.
LAT_STEP, LON_STEP = 0.5, 0.625

CACHE = Path("data/raw/nasa_power")
META_FILE = "nasa_power.meta.json"
# Una descarga cortada se reintenta; la pausa crece con cada intento.
ATTEMPTS = 3
PAUSE_S = 10

SERIES_SCHEMA = {"cell": pl.String, "date": pl.Date, "temp_min_c": pl.Float64, "temp_max_c": pl.Float64, "precip_mm": pl.Float64}
DAY_SCHEMA = {
    "municipality_id": pl.String,
    "date": pl.Date,
    "temp_min_c": pl.Float64,
    "temp_max_c": pl.Float64,
    "quality": pl.String,
    "source_id": pl.String,
}


def cell_of(lat: float, lon: float) -> str:
    """La celda de POWER que contiene un punto, nombrada por su centro: «5.000_-73.125»."""
    row = math.floor((lat + 90) / LAT_STEP + 0.5)
    col = math.floor((lon + 180) / LON_STEP + 0.5)
    return f"{-90 + row * LAT_STEP:.3f}_{-180 + col * LON_STEP:.3f}"


def cell_center(cell: str) -> tuple[float, float]:
    lat, lon = cell.split("_")
    return float(lat), float(lon)


def cells(municipalities: pl.DataFrame) -> list[str]:
    """Las celdas que cubren los municipios con coordenadas, ordenadas (R4)."""
    points = municipalities.drop_nulls(["lat", "lon"]).select("lat", "lon").iter_rows()
    return sorted({cell_of(lat, lon) for lat, lon in points})


def _url(cell: str, end: date) -> str:
    lat, lon = cell_center(cell)
    query = {
        "parameters": ",".join(PARAMETERS),
        "community": COMMUNITY,
        "latitude": f"{lat:.3f}",
        "longitude": f"{lon:.3f}",
        "start": f"{FIRST_DAY:%Y%m%d}",
        "end": f"{end:%Y%m%d}",
        "format": "JSON",
    }
    return f"{API_URL}?{urllib.parse.urlencode(query)}"


def _fetch(url: str, dest: Path, timeout_s: float, max_bytes: int) -> None:
    """Baja una respuesta a `dest` con los límites de `fetch` (tiempo total y tamaño). Solo deja el archivo si es una
    respuesta completa de POWER con las variables pedidas: una a medias o sin ellas no entra a la caché (R1)."""
    partial = dest.with_name(dest.name + ".download")
    request = urllib.request.Request(url, headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310 - dirección fija de POWER
    try:
        fetch(request, partial, timeout_s, max_bytes)
        body = json.loads(partial.read_text(encoding="utf-8"))
        missing = [name for name in PARAMETERS if name not in body.get("properties", {}).get("parameter", {})]
        if missing or "geometry" not in body:
            raise DownloadError(f"la respuesta no trae {missing or 'la geometría'}")
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)


def download(cell_ids: list[str], cache: Path = CACHE, end: date | None = None) -> Path:
    """Baja la serie diaria de cada celda a la caché, una por una y con reintentos. Es lo único que usa la red.

    El manifiesto de la caché (`META_FILE`) se escribe al final, solo si bajaron todas: una caché a medias no se usa.
    """
    settings = get_settings()
    end = end or datetime.now(UTC).date()
    cache.mkdir(parents=True, exist_ok=True)
    (cache / META_FILE).unlink(missing_ok=True)
    max_bytes = int(settings.power_max_mb * 2**20)
    log.info("source_downloading", source=SOURCE_ID, cells=len(cell_ids), detail=f"Bajando NASA POWER: {len(cell_ids)} celdas a {cache}")
    for number, cell in enumerate(cell_ids, start=1):
        for attempt in range(1, ATTEMPTS + 1):
            try:
                _fetch(_url(cell, end), cache / f"{cell}.json", settings.power_timeout_s, max_bytes)
                break
            except (OSError, ValueError) as error:
                reason = f"{type(error).__name__}: {error}"
                if attempt == ATTEMPTS:
                    log.error("source_download_failed", source=SOURCE_ID, cell=cell, reason=reason, detail=f"No bajó la celda {cell}")
                    raise DownloadError(f"NASA POWER: la celda {cell} no bajó después de {ATTEMPTS} intentos ({reason})") from error
                log.warning("source_download_retry", source=SOURCE_ID, cell=cell, attempt=attempt, reason=reason)
                time.sleep(PAUSE_S * attempt)
        log.debug("cell_downloaded", source=SOURCE_ID, cell=cell, number=number, total=len(cell_ids))
    meta = {
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "requested_end": f"{end:%Y-%m-%d}",
        "parameters": list(PARAMETERS),
        "cells": cell_ids,
    }
    (cache / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("source_downloaded", source=SOURCE_ID, cells=len(cell_ids), detail=f"NASA POWER: {len(cell_ids)} celdas en {cache}")
    return cache


def _values(series: dict[str, float], days: list[str], fill: float) -> list[float | None]:
    """El valor de cada día; el de relleno de POWER (-999) es un día sin dato: nulo, nunca un número (R1)."""
    return [None if (value := series.get(day)) is None or value == fill else float(value) for day in days]


def read_cache(cell_ids: list[str], cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Las series diarias de las celdas, sin corregir, y el manifiesto de la caché con la altura de cada celda.

    Falta la caché, o le falta alguna celda (por ejemplo, si cambió la región): `FileNotFoundError` con cómo bajarla.
    """
    hint = "Bájela con: uv run python -m pipeline.build --descargar"
    meta_path = cache / META_FILE
    if not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de NASA POWER en {cache}. {hint}")
    missing = [cell for cell in cell_ids if not (cache / f"{cell}.json").exists()]
    if missing:
        raise FileNotFoundError(f"A la caché de NASA POWER le faltan {len(missing)} celdas ({missing[:3]}). {hint}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    frames, elevations, versions = [], {}, set()
    for cell in cell_ids:
        body = json.loads((cache / f"{cell}.json").read_text(encoding="utf-8"))
        header = body.get("header", {})
        fill = header.get("fill_value", -999.0)
        parameter = body["properties"]["parameter"]
        days = sorted(parameter["T2M_MIN"])
        elevations[cell] = float(body["geometry"]["coordinates"][2])
        versions.add((header.get("api") or {}).get("version"))
        frames.append(
            pl.DataFrame(
                {
                    "cell": [cell] * len(days),
                    "date": [datetime.strptime(day, "%Y%m%d").date() for day in days],
                    "temp_min_c": _values(parameter["T2M_MIN"], days, fill),
                    "temp_max_c": _values(parameter["T2M_MAX"], days, fill),
                    "precip_mm": _values(parameter["PRECTOTCORR"], days, fill),
                },
                schema=SERIES_SCHEMA,
            )
        )
    meta["elevations"] = elevations
    meta["api_version"] = ", ".join(sorted(v for v in versions if v)) or None
    series = pl.concat(frames) if frames else pl.DataFrame(schema=SERIES_SCHEMA)
    return series.sort("cell", "date"), meta


def with_cell_elevation(municipalities: pl.DataFrame, elevations: dict[str, float]) -> pl.DataFrame:
    """`climate_cell_elevation_m` de cada municipio: la altura de su celda de POWER (HU-044). La fila suma la fuente."""
    points = municipalities.select("lat", "lon").iter_rows()
    elevation = [elevations.get(cell_of(lat, lon)) if lat is not None and lon is not None else None for lat, lon in points]
    return municipalities.with_columns(pl.Series("climate_cell_elevation_m", elevation, dtype=pl.Float64)).with_columns(
        pl.when(pl.col("climate_cell_elevation_m").is_not_null() & ~pl.col("source_ids").list.contains(SOURCE_ID))
        .then(pl.concat_list("source_ids", pl.lit(SOURCE_ID)).list.sort())
        .otherwise(pl.col("source_ids"))
        .alias("source_ids")
    )


def climate_day(series: pl.DataFrame, municipalities: pl.DataFrame, lapse_rate: dict[str, Any] | None) -> pl.DataFrame:
    """La tabla `climate_day`: mínima y máxima diarias de cada municipio, corregidas por altitud.

    - Corrección (HU-044): temperatura del municipio = temperatura de la celda + gradiente × (altura de la celda −
      altitud del municipio). El gradiente (°C por metro) es distinto para la mínima y la máxima.
    - Sin altitud del municipio, sin altura de la celda o sin gradiente no se corrige, y el municipio no tiene filas (R1).
    - Un día sin la mínima o sin la máxima queda con ese valor nulo y `quality = partial`. Un día sin ninguna de las dos
      no se publica: no se rellena (R1). Así tampoco salen los últimos días, que POWER todavía no tiene.
    """
    if lapse_rate is None or series.is_empty():
        return pl.DataFrame(schema=DAY_SCHEMA)
    places = municipalities.drop_nulls(["lat", "lon", "altitude_m", "climate_cell_elevation_m"])
    places = places.select(
        "municipality_id",
        pl.Series("cell", [cell_of(lat, lon) for lat, lon in places.select("lat", "lon").iter_rows()], dtype=pl.String),
        (pl.col("climate_cell_elevation_m") - pl.col("altitude_m")).alias("drop_m"),
    )
    rate_min, rate_max = float(lapse_rate["temp_min_c_per_m"]), float(lapse_rate["temp_max_c_per_m"])
    return (
        places.join(series.select("cell", "date", "temp_min_c", "temp_max_c"), on="cell")
        .filter(pl.col("temp_min_c").is_not_null() | pl.col("temp_max_c").is_not_null())
        .select(
            "municipality_id",
            "date",
            (pl.col("temp_min_c") + rate_min * pl.col("drop_m")).round(2).alias("temp_min_c"),
            (pl.col("temp_max_c") + rate_max * pl.col("drop_m")).round(2).alias("temp_max_c"),
            pl.when(pl.col("temp_min_c").is_null() | pl.col("temp_max_c").is_null())
            .then(pl.lit("partial"))
            .otherwise(pl.lit("ok"))
            .alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .cast(DAY_SCHEMA)
        .sort("municipality_id", "date")
    )


def source(series: pl.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8). Dice siempre que es un reanálisis y de qué tamaño es su celda."""
    with_data = series.filter(pl.col("temp_min_c").is_not_null() | pl.col("temp_max_c").is_not_null())
    period = f"Del {with_data['date'].min()} al {with_data['date'].max()}" if with_data.height else None
    downloaded = (meta.get("downloaded_at") or "")[:10]
    # La versión de la API sale de la respuesta. Si no la trae, la cita no nombra ninguna: no se inventa (R5).
    version = (meta.get("api_version") or "").removeprefix("v")
    citation = (
        "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's "
        "Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division."
    )
    if version:
        citation += f" The data was obtained from the POWER Project's Daily {version} version on {downloaded.replace('-', '/')}."
    return {
        "source_id": SOURCE_ID,
        "name": "NASA POWER · Datos diarios por punto (comunidad AG)",
        "institution": "NASA Langley Research Center, proyecto POWER (Prediction Of Worldwide Energy Resources)",
        "url": PAGE_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": f"{len(meta.get('elevations', {}))} celdas de 0,5° × 0,625° que cubren la región",
        "license": "La página de POWER no da una licencia; pide citar la fuente (https://power.larc.nasa.gov/docs/referencing/)",
        # La cita que pide POWER (R8): la de la entrega.
        "citation": citation,
        "notes": (
            "Es un reanálisis (MERRA-2 y GEOS-IT): un modelo con observaciones asimiladas, no una observación directa. "
            "Celda de 0,5° de latitud por 0,625° de longitud (unos 55 × 70 km): es un dato de la zona, no del lote. "
            "Temperatura mínima y máxima a 2 m (T2M_MIN, T2M_MAX) y lluvia corregida (PRECTOTCORR). Las temperaturas se "
            "corrigen por altitud con la altura de la celda que da POWER, la altitud del municipio y el gradiente térmico de "
            "pipeline/region.yaml. Los días sin dato (-999) quedan nulos, nunca rellenos."
        ),
    }
