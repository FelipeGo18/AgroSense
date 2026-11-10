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

La lluvia diaria (`PRECTOTCORR`) se baja en la misma consulta. Con ella sale `climate_month` (HU-042): la lluvia de
cada mes completo y su normal de 1991 a 2020. La lluvia no se corrige por altitud: no hay un gradiente con fuente.
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
from pipeline import et0
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.nasa_power")

SOURCE_ID = "nasa_power"
API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PAGE_URL = "https://power.larc.nasa.gov/"
COMMUNITY = "AG"
# Mínima y máxima a 2 m (°C) y lluvia corregida (mm/día). Sus series empiezan en 1981.
# Cada variable de POWER y su columna en la caché leída (HU-041, HU-205). Nombres verificados en la API de parámetros de
# POWER (comunidad AG, diaria) el 10 de noviembre de 2026. Todas empiezan el 1 de enero de 1981, menos la radiación, que
# empieza el 1 de enero de 1984 y llega unos días después que las demás.
COLUMNS = {
    "T2M_MIN": "temp_min_c",  # temperatura mínima a 2 m, °C
    "T2M_MAX": "temp_max_c",  # temperatura máxima a 2 m, °C
    "PRECTOTCORR": "precip_mm",  # lluvia corregida, mm/día
    "GWETTOP": "soil_wetness_top",  # humedad del suelo de los primeros 5 cm, de 0 (seco) a 1 (saturado)
    "GWETROOT": "soil_wetness_root",  # humedad del suelo de la zona de raíces (hasta 1 m), de 0 a 1
    "ALLSKY_SFC_SW_DWN": "radiation_mj_m2",  # radiación solar que llega al suelo, MJ/m²/día
    "WS2M": "wind_2m_m_s",  # viento a 2 m, m/s
    "RH2M": "rh_2m_pct",  # humedad relativa a 2 m, %
}
PARAMETERS = tuple(COLUMNS)
FIRST_DAY = date(1981, 1, 1)
# La rejilla de MERRA-2, la de POWER para estas variables: celdas centradas en múltiplos de estos pasos.
LAT_STEP, LON_STEP = 0.5, 0.625

CACHE = Path("data/raw/nasa_power")
META_FILE = "nasa_power.meta.json"
# Una descarga cortada se reintenta; la pausa crece con cada intento.
ATTEMPTS = 3
PAUSE_S = 10

# La normal de la lluvia (HU-042): el periodo de referencia de la OMM, el mismo de las normales del IDEAM. Un mes tiene
# normal si al menos 24 de sus 30 años están completos (`ok`); si no, queda nula (R1).
NORMAL_PERIOD = (1991, 2020)
NORMAL_MIN_YEARS = 24
# Un mes es `ok` con todos sus días con dato, y `partial` con al menos este porcentaje: su total es la suma de los
# días con dato y la fila lo dice. Con menos, el mes no tiene total (R1).
PARTIAL_MIN_SHARE = 0.9
# El año seco (HU-143): la lluvia de ese mes que se supera en 4 de cada 5 años de 1991 a 2020 (el percentil 20), la
# «lluvia confiable al 80 %» con la que se planea el riego. Supuesto por confirmar: la HU solo pide un percentil bajo.
DRY_QUANTILE = 0.2
# Las columnas de humedad del suelo de `climate_month` (HU-205), que salen tal cual de la serie diaria.
WETNESS = ("soil_wetness_top", "soil_wetness_root")

SERIES_SCHEMA = {"cell": pl.String, "date": pl.Date, **dict.fromkeys(COLUMNS.values(), pl.Float64)}
DAY_SCHEMA = {
    "municipality_id": pl.String,
    "date": pl.Date,
    "temp_min_c": pl.Float64,
    "temp_max_c": pl.Float64,
    "quality": pl.String,
    "source_id": pl.String,
}


MONTH_SCHEMA = {
    "municipality_id": pl.String,
    "year": pl.Int16,
    "month": pl.Int8,
    "precip_mm": pl.Float64,
    "precip_normal_mm": pl.Float64,
    "precip_dry_mm": pl.Float64,
    "et0_mm": pl.Float64,
    "et0_normal_mm": pl.Float64,
    "soil_wetness_top": pl.Float64,
    "soil_wetness_root": pl.Float64,
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
        absent = [name for name in PARAMETERS if name not in parameter]
        if absent:
            # Una caché bajada antes de HU-205 no trae la humedad, la radiación ni el viento: no se publican nulos como si
            # POWER no los tuviera (R1).
            raise FileNotFoundError(f"La celda {cell} de la caché de NASA POWER no trae {absent}. {hint}")
        days = sorted(parameter["T2M_MIN"])
        elevations[cell] = float(body["geometry"]["coordinates"][2])
        versions.add((header.get("api") or {}).get("version"))
        frames.append(
            pl.DataFrame(
                {
                    "cell": [cell] * len(days),
                    "date": [datetime.strptime(day, "%Y%m%d").date() for day in days],
                    **{column: _values(parameter[name], days, fill) for name, column in COLUMNS.items()},
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


def cell_months(series: pl.DataFrame, end: date) -> pl.DataFrame:
    """La lluvia de cada celda en cada mes completo hasta `end`, con su calidad y su normal (HU-042).

    El mes en curso, o uno que termina después de `end`, no se publica: todavía no tiene todos sus días.
    """
    days = pl.date("year", "month", 1).dt.month_end().dt.day()
    months = (
        series.with_columns(pl.col("date").dt.year().cast(pl.Int16).alias("year"), pl.col("date").dt.month().cast(pl.Int8).alias("month"))
        .group_by("cell", "year", "month")
        .agg(
            pl.col("precip_mm").sum().alias("total"),
            pl.col("precip_mm").count().alias("valid"),
            *(pl.col(c).mean().alias(f"{c}_mean") for c in WETNESS),
            *(pl.col(c).count().alias(f"{c}_valid") for c in WETNESS),
        )
        .filter(pl.date("year", "month", 1).dt.month_end() <= end)
        .with_columns(days.alias("days"))
        .with_columns(
            pl.when(pl.col("valid") == pl.col("days"))
            .then(pl.lit("ok"))
            .when(pl.col("valid") >= PARTIAL_MIN_SHARE * pl.col("days"))
            .then(pl.lit("partial"))
            .otherwise(pl.lit(None, dtype=pl.String))
            .alias("days_quality")
        )
        .with_columns(pl.when(pl.col("days_quality").is_not_null()).then(pl.col("total").round(1)).alias("precip_mm"))
        # La humedad del suelo (HU-205): el promedio de los días con dato, si son al menos el 90 % del mes.
        .with_columns(
            *(
                pl.when(pl.col(f"{c}_valid") >= PARTIAL_MIN_SHARE * pl.col("days")).then(pl.col(f"{c}_mean").round(3)).alias(c)
                for c in WETNESS
            ),
            pl.all_horizontal(pl.col(f"{c}_valid") == pl.col("days") for c in WETNESS).alias("wetness_complete"),
        )
    )
    first, last = NORMAL_PERIOD
    normal = (
        months.filter((pl.col("days_quality") == "ok") & pl.col("year").is_between(first, last))
        .group_by("cell", "month")
        .agg(
            pl.col("precip_mm").mean().round(1).alias("precip_normal_mm"),
            pl.col("precip_mm").quantile(DRY_QUANTILE, interpolation="linear").round(1).alias("precip_dry_mm"),
            pl.len().alias("years"),
        )
        .with_columns(pl.when(pl.col("years") >= NORMAL_MIN_YEARS).then(pl.col(c)).alias(c) for c in ("precip_normal_mm", "precip_dry_mm"))
        .select("cell", "month", "precip_normal_mm", "precip_dry_mm")
    )
    return months.join(normal, on=["cell", "month"], how="left").select(
        "cell", "year", "month", "precip_mm", "precip_normal_mm", "precip_dry_mm", *WETNESS, "days_quality", "wetness_complete"
    )


def municipality_et0(series: pl.DataFrame, municipalities: pl.DataFrame, lapse_rate: dict[str, Any] | None, end: date) -> pl.DataFrame:
    """La ET0 de cada mes completo de cada municipio (HU-143) y su normal: Penman-Monteith de FAO-56 (`pipeline/et0.py`).

    - Cada día usa la mínima y la máxima corregidas por altitud, como `climate_day`, y la altitud y la latitud del
      municipio. Sin altitud no se corrige la temperatura ni se sabe la presión: el municipio no tiene ET0 (R1).
    - Un mes tiene ET0 solo si todos sus días la tienen: a uno que le falta una variable (la radiación empieza en 1984)
      no se le suma una parte, ni se cambia de método (R1). La normal es el promedio de 1991 a 2020 con 24 años.
    """
    schema = {"municipality_id": pl.String, "year": pl.Int16, "month": pl.Int8, "et0_mm": pl.Float64, "et0_normal_mm": pl.Float64}
    if lapse_rate is None or series.is_empty():
        return pl.DataFrame(schema=schema)
    places = municipalities.drop_nulls(["lat", "lon", "altitude_m", "climate_cell_elevation_m"])
    places = places.select(
        "municipality_id",
        "lat",
        "altitude_m",
        pl.Series("cell", [cell_of(lat, lon) for lat, lon in places.select("lat", "lon").iter_rows()], dtype=pl.String),
        (pl.col("climate_cell_elevation_m") - pl.col("altitude_m")).alias("drop_m"),
    )
    rate_min, rate_max = float(lapse_rate["temp_min_c_per_m"]), float(lapse_rate["temp_max_c_per_m"])
    days = places.join(series, on="cell").with_columns(
        et0.penman_monteith(
            pl.col("temp_min_c") + rate_min * pl.col("drop_m"),
            pl.col("temp_max_c") + rate_max * pl.col("drop_m"),
            pl.col("rh_2m_pct"),
            pl.col("wind_2m_m_s"),
            pl.col("radiation_mj_m2"),
            pl.col("lat"),
            pl.col("altitude_m"),
            pl.col("date").dt.ordinal_day(),
        ).alias("et0_day"),
        pl.col("date").dt.year().cast(pl.Int16).alias("year"),
        pl.col("date").dt.month().cast(pl.Int8).alias("month"),
    )
    months = (
        days.group_by("municipality_id", "year", "month")
        .agg(pl.col("et0_day").sum().alias("total"), pl.col("et0_day").count().alias("valid"))
        .filter(pl.date("year", "month", 1).dt.month_end() <= end)
        .with_columns(
            pl.when(pl.col("valid") == pl.date("year", "month", 1).dt.month_end().dt.day()).then(pl.col("total").round(1)).alias("et0_mm")
        )
    )
    first, last = NORMAL_PERIOD
    normal = (
        months.filter(pl.col("et0_mm").is_not_null() & pl.col("year").is_between(first, last))
        .group_by("municipality_id", "month")
        .agg(pl.col("et0_mm").mean().round(1).alias("et0_normal_mm"), pl.len().alias("years"))
        .with_columns(pl.when(pl.col("years") >= NORMAL_MIN_YEARS).then(pl.col("et0_normal_mm")).alias("et0_normal_mm"))
        .select("municipality_id", "month", "et0_normal_mm")
    )
    return months.join(normal, on=["municipality_id", "month"], how="left").select(list(schema)).cast(schema)


def climate_month(series: pl.DataFrame, municipalities: pl.DataFrame, end: date, lapse_rate: dict[str, Any] | None = None) -> pl.DataFrame:
    """La tabla `climate_month`: la lluvia de cada mes de cada municipio (la de su celda de POWER), su normal y su año
    seco, la ET0 por Penman-Monteith y su normal, y la humedad del suelo.

    - Un mes sin el 90 % de sus días con lluvia no tiene total y, si no le queda ningún dato, no se publica (R1).
    - La normal y el año seco de la lluvia: el promedio y el percentil 20 de 1991 a 2020, con 24 años completos.
    - La ET0 (HU-143) sale de `municipality_et0`: nula sin altitud o si al mes le falta un día de alguna variable.
    - La humedad del suelo (HU-205) es el promedio del mes de la de POWER, de 0 a 1; sin el 90 % de sus días, nula. Es la
      de un modelo y de una celda de unos 55 × 70 km: un dato de la zona, no del lote (R10).
    - `quality = ok` solo con todo: la lluvia de todos los días, su normal y su año seco, la ET0 y su normal, y la humedad
      de todos los días. Si falta algo, `partial` (R1).
    """
    if series.is_empty():
        return pl.DataFrame(schema=MONTH_SCHEMA)
    places = municipalities.drop_nulls(["lat", "lon"])
    places = places.select(
        "municipality_id",
        pl.Series("cell", [cell_of(lat, lon) for lat, lon in places.select("lat", "lon").iter_rows()], dtype=pl.String),
    )
    # Un mes sin la lluvia ni la humedad no tiene ningún dato: no se publica (R1).
    months = cell_months(series, end).filter(pl.any_horizontal(pl.col(c).is_not_null() for c in ("precip_mm", *WETNESS)))
    evapo = municipality_et0(series, municipalities, lapse_rate, end)
    complete = (
        (pl.col("days_quality") == "ok")
        & pl.col("wetness_complete")
        & pl.all_horizontal(pl.col(c).is_not_null() for c in ("precip_normal_mm", "precip_dry_mm", "et0_mm", "et0_normal_mm"))
    )
    return (
        places.join(months, on="cell")
        .join(evapo, on=["municipality_id", "year", "month"], how="left")
        .select(
            "municipality_id",
            "year",
            "month",
            "precip_mm",
            "precip_normal_mm",
            "precip_dry_mm",
            "et0_mm",
            "et0_normal_mm",
            *WETNESS,
            pl.when(complete).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .cast(MONTH_SCHEMA)
        .sort("municipality_id", "year", "month")
    )


def source(series: pl.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8). Dice siempre que es un reanálisis y de qué tamaño es su celda."""
    with_data = series.filter(pl.col("temp_min_c").is_not_null() | pl.col("temp_max_c").is_not_null())
    period = f"Del {with_data['date'].min()} al {with_data['date'].max()}" if with_data.height else None
    downloaded = (meta.get("downloaded_at") or "")[:10]
    version = (meta.get("api_version") or "").removeprefix("v") or "2.x.x"
    return {
        "source_id": SOURCE_ID,
        "name": "NASA POWER · Datos diarios por punto (comunidad AG)",
        "institution": "NASA Langley Research Center, proyecto POWER (Prediction Of Worldwide Energy Resources)",
        "url": PAGE_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": f"{len(meta.get('elevations', {}))} celdas de 0,5° × 0,625° que cubren la región",
        "license": (
            "La página de POWER no da una licencia; pide citar «The data was obtained from National Aeronautics and Space "
            "Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded "
            f"through the NASA Earth Science Division.» y «The data was obtained from the POWER Project's Daily {version} "
            f"version on {downloaded.replace('-', '/')}.» (https://power.larc.nasa.gov/docs/referencing/)"
        ),
        "notes": (
            "Es un reanálisis (MERRA-2 y GEOS-IT): un modelo con observaciones asimiladas, no una observación directa. "
            "Celda de 0,5° de latitud por 0,625° de longitud (unos 55 × 70 km): es un dato de la zona, no del lote. "
            "Temperatura mínima y máxima a 2 m (T2M_MIN, T2M_MAX), lluvia corregida (PRECTOTCORR), humedad del suelo de los "
            "primeros 5 cm y de la zona de raíces (GWETTOP, GWETROOT, de 0 a 1, de un modelo), radiación solar "
            "(ALLSKY_SFC_SW_DWN, desde 1984), viento a 2 m (WS2M) y humedad relativa a 2 m (RH2M). Las temperaturas se "
            "corrigen por altitud con la altura de la celda que da POWER, la altitud del municipio y el gradiente térmico de "
            "pipeline/region.yaml. La ET0 de climate_month se calcula con estas variables por Penman-Monteith de FAO-56 "
            "(fuente fao_56). Los días sin dato (-999) quedan nulos, nunca rellenos."
        ),
    }
