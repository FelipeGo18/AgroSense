"""Altitud y pendiente: NASADEM (HU-206; specs/02-contratos.md, «La rejilla de 250 m» y `grid_cells`).

Fuente: NASADEM HGT v001 (NASA JPL, distribuido por el LP DAAC), el modelo de elevación de la misión SRTM (febrero de
2000) reprocesado, con píxeles de 1 segundo de arco (unos 30 m). Se baja la copia en GeoTIFF que publica Microsoft
Planetary Computer, que no pide cuenta: un mosaico por grado, de 3601 × 3601 píxeles, con el centro de cada píxel en un
segundo entero (el primero, en la esquina noroeste del grado).

La rejilla común del contrato es de 0,0025° = 9 segundos: cada celda son exactamente 9 × 9 píxeles de NASADEM y un grado
son 400 × 400 celdas. Por celda:

- `altitude_m`: el promedio de sus píxeles.
- `slope_pct`: la mediana de la pendiente de sus píxeles, calculada a 30 m con diferencias centrales
  (`numpy.gradient`), con el tamaño real del píxel en metros a esa latitud. En el borde de un mosaico la diferencia es
  hacia un solo lado.

Un píxel vacío de NASADEM (-32768) no cuenta. Una celda sin ningún píxel válido queda con la altitud y la pendiente
nulas (R1).
"""

import json
import math
import time
import urllib.request
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import shapely
import tifffile

from common.logging import get_logger
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.nasadem")

SOURCE_ID = "nasadem"
PRODUCT = "NASADEM HGT v001"
DOI_URL = "https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001"
TILE_URL = "https://nasademeuwest.blob.core.windows.net/nasadem-cog/v001/NASADEM_HGT_{name}.tif"
# Planetary Computer da un permiso de lectura anónimo, de una hora, para su almacenamiento.
SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/nasadem"

CACHE = Path("data/raw/nasadem")
META_FILE = "nasadem.meta.json"
NODATA = -32768
PIXELS = 3601
PIXELS_PER_DEGREE = 3600
# La rejilla del contrato (decisión 15): 0,0025° por celda.
CELL_DEG = 0.0025
CELLS_PER_DEGREE = 400
PIXELS_PER_CELL = PIXELS_PER_DEGREE // CELLS_PER_DEGREE
# Metros por grado de latitud y, multiplicado por el coseno de la latitud, de longitud (WGS84, cerca del ecuador).
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON = 111_320.0
ATTEMPTS = 3
PAUSE_S = 10

# Las columnas del suelo de `grid_cells` (SoilGrids, HU-181), que van nulas hasta que se publique. Después de ellas,
# `texture_class`.
SOIL_COLUMNS = ("ph", "ph_p05", "ph_p95", "soc_g_kg", "soc_p05", "soc_p95", "nitrogen_g_kg", "clay_pct", "sand_pct", "silt_pct")

CELL_SCHEMA = {
    "cell_id": pl.String,
    "lat": pl.Float64,
    "lon": pl.Float64,
    "altitude_m": pl.Float64,
    "slope_pct": pl.Float64,
    "pixels": pl.Int16,
}


class TileError(ValueError):
    """Un mosaico no es el que se esperaba (tamaño o georreferencia). El mensaje dice qué falla."""


def tile_name(lat: int, lon: int) -> str:
    """El mosaico de NASADEM cuya esquina suroeste es (`lat`, `lon`): «n05w074» va de 5° a 6° N y de 74° a 73° O."""
    return f"{'n' if lat >= 0 else 's'}{abs(lat):02d}{'e' if lon >= 0 else 'w'}{abs(lon):03d}"


def tiles(boundaries: pl.DataFrame) -> list[tuple[int, int]]:
    """Los mosaicos (esquina suroeste en grados) que tocan algún municipio, ordenados (R4)."""
    found: set[tuple[int, int]] = set()
    for geometry in shapely.from_wkb(boundaries["geometry"].to_list()):
        x0, y0, x1, y1 = shapely.bounds(geometry)
        for lat in range(math.floor(y0), math.floor(y1) + 1):
            for lon in range(math.floor(x0), math.floor(x1) + 1):
                if shapely.intersects(geometry, shapely.box(lon, lat, lon + 1, lat + 1)):
                    found.add((lat, lon))
    return sorted(found)


def _token(cache: Path, timeout_s: float) -> str:
    request = urllib.request.Request(SAS_URL, headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310 - dirección fija
    path = fetch(request, cache / "token.json", timeout_s, 64 * 1024)
    try:
        return json.loads(path.read_text(encoding="utf-8"))["token"]
    except (ValueError, KeyError) as error:
        raise DownloadError("Planetary Computer no devolvió un permiso de lectura para NASADEM") from error
    finally:
        path.unlink(missing_ok=True)


def download(tile_ids: list[tuple[int, int]], cache: Path = CACHE) -> Path:
    """Baja cada mosaico a la caché, uno por uno y con reintentos. Es lo único que usa la red.

    El manifiesto de la caché (`META_FILE`) se escribe al final, solo si bajaron todos: una caché a medias no se usa.
    """
    settings = get_settings()
    max_bytes = int(settings.nasadem_max_mb * 2**20)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / META_FILE).unlink(missing_ok=True)
    log.info("source_downloading", source=SOURCE_ID, tiles=len(tile_ids), detail=f"Bajando NASADEM: {len(tile_ids)} mosaicos a {cache}")
    token = _token(cache, settings.nasadem_timeout_s)
    for lat, lon in tile_ids:
        name = tile_name(lat, lon)
        dest = cache / f"{name}.tif"
        for attempt in range(1, ATTEMPTS + 1):
            partial = dest.with_name(dest.name + ".download")
            try:
                url = f"{TILE_URL.format(name=name)}?{token}"
                request = urllib.request.Request(url, headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310
                fetch(request, partial, settings.nasadem_timeout_s, max_bytes)
                read_tile(partial, lat, lon)
                partial.replace(dest)
                break
            except (OSError, TileError) as error:
                reason = f"{type(error).__name__}: {error}"
                if attempt == ATTEMPTS:
                    log.error("source_download_failed", source=SOURCE_ID, tile=name, reason=reason, detail=f"No bajó el mosaico {name}")
                    raise DownloadError(f"NASADEM: el mosaico {name} no bajó después de {ATTEMPTS} intentos ({reason})") from error
                log.warning("source_download_retry", source=SOURCE_ID, tile=name, attempt=attempt, reason=reason)
                time.sleep(PAUSE_S * attempt)
                # El permiso dura una hora: si venció a mitad, se pide otro.
                token = _token(cache, settings.nasadem_timeout_s)
            finally:
                partial.unlink(missing_ok=True)
    meta = {
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "product": PRODUCT,
        "url": TILE_URL,
        "tiles": [tile_name(lat, lon) for lat, lon in tile_ids],
    }
    (cache / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("source_downloaded", source=SOURCE_ID, tiles=len(tile_ids), detail=f"NASADEM: {len(tile_ids)} mosaicos en {cache}")
    return cache


def read_tile(path: Path, lat: int, lon: int) -> np.ndarray:
    """La altitud de un mosaico en metros, con los píxeles vacíos en NaN. Falla si no es el mosaico de (`lat`, `lon`)
    con píxeles de 1 segundo centrados en segundos enteros: así no se lee mal un archivo distinto."""
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        tags = {tag.name: tag.value for tag in page.tags.values()}
        if page.shape != (PIXELS, PIXELS):
            raise TileError(f"{path.name}: mide {page.shape} y no {PIXELS} × {PIXELS} píxeles")
        scale = tags.get("ModelPixelScaleTag")
        tiepoint = tags.get("ModelTiepointTag")
        geokeys = list(tags.get("GeoKeyDirectoryTag") or ())
        if scale is None or tiepoint is None or not all(math.isclose(s, 1 / PIXELS_PER_DEGREE) for s in scale[:2]):
            raise TileError(f"{path.name}: el píxel no es de 1 segundo de arco")
        if not (math.isclose(tiepoint[3], lon) and math.isclose(tiepoint[4], lat + 1)):
            raise TileError(f"{path.name}: empieza en ({tiepoint[4]}, {tiepoint[3]}) y no en ({lat + 1}, {lon})")
        # GTRasterTypeGeoKey (1025) = 2: el punto de amarre es el centro del píxel, no su esquina.
        keys = {geokeys[i]: geokeys[i + 3] for i in range(4, len(geokeys) - 3, 4)}
        if keys.get(1025) != 2:
            raise TileError(f"{path.name}: el punto de amarre no es el centro del píxel")
        elevation = page.asarray().astype(np.float32)
    elevation[elevation == NODATA] = np.nan
    return elevation


def tile_cells(elevation: np.ndarray, lat: int, lon: int) -> pl.DataFrame:
    """Las celdas de 0,0025° de un mosaico: promedio de la altitud y mediana de la pendiente de sus 9 × 9 píxeles.

    La última fila y la última columna del mosaico (latitud `lat`, longitud `lon + 1`) se repiten en los mosaicos
    vecinos: no cuentan, para que cada píxel caiga en una sola celda.
    """
    rows = np.arange(PIXELS)
    pixel_lat = lat + 1 - rows / PIXELS_PER_DEGREE
    dy = M_PER_DEG_LAT / PIXELS_PER_DEGREE
    dx = (M_PER_DEG_LON / PIXELS_PER_DEGREE) * np.cos(np.radians(pixel_lat))[:, None]
    dz_dy, dz_dx = np.gradient(elevation)
    slope = 100 * np.hypot(dz_dx / dx, dz_dy / dy)
    n = CELLS_PER_DEGREE
    k = PIXELS_PER_CELL

    def blocks(values: np.ndarray) -> np.ndarray:
        return values[:-1, :-1].reshape(n, k, n, k).transpose(0, 2, 1, 3).reshape(n, n, k * k)

    elev_blocks, slope_blocks = blocks(elevation), blocks(slope)
    valid = np.isfinite(elev_blocks).sum(axis=2)
    with warnings.catch_warnings():
        # Una celda toda vacía avisa «Mean of empty slice»: es lo esperado (queda nula), no un problema.
        warnings.simplefilter("ignore", category=RuntimeWarning)
        altitude = np.nanmean(elev_blocks, axis=2)
        slope_median = np.nanmedian(slope_blocks, axis=2)
    first_row = round((90 - (lat + 1)) * CELLS_PER_DEGREE)
    first_col = round((lon + 180) * CELLS_PER_DEGREE)
    cell_rows = np.repeat(np.arange(first_row, first_row + n), n)
    cell_cols = np.tile(np.arange(first_col, first_col + n), n)
    return pl.DataFrame(
        {
            "cell_id": [f"{r}_{c}" for r, c in zip(cell_rows, cell_cols, strict=True)],
            "lat": 90 - (cell_rows + 0.5) * CELL_DEG,
            "lon": -180 + (cell_cols + 0.5) * CELL_DEG,
            "altitude_m": np.round(altitude.ravel().astype(np.float64), 1),
            "slope_pct": np.round(slope_median.ravel().astype(np.float64), 1),
            "pixels": valid.ravel(),
        },
        schema=CELL_SCHEMA,
        nan_to_null=True,
    )


def assign(cells: pl.DataFrame, boundaries: pl.DataFrame) -> pl.DataFrame:
    """Cada celda con el municipio que contiene su centro (contrato, «La rejilla de 250 m»). Las que no caen en ningún
    municipio de la región no se publican."""
    parts = []
    for municipality_id, wkb in boundaries.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        x0, y0, x1, y1 = shapely.bounds(geometry)
        near = cells.filter(pl.col("lon").is_between(x0, x1) & pl.col("lat").is_between(y0, y1))
        if near.is_empty():
            continue
        inside = shapely.contains_xy(geometry, near["lon"].to_numpy(), near["lat"].to_numpy())
        parts.append(near.filter(pl.Series(inside)).with_columns(pl.lit(municipality_id).alias("municipality_id")))
    if not parts:
        return cells.clear().with_columns(pl.lit(None, dtype=pl.String).alias("municipality_id"))
    # Un centro que cae justo en el límite de dos municipios va con el de llave menor (R4).
    return pl.concat(parts).sort("cell_id", "municipality_id").unique("cell_id", keep="first", maintain_order=True)


def read_cache(boundaries: pl.DataFrame, cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Las celdas de la región, con su municipio, desde la caché. Sin la caché completa, `FileNotFoundError`."""
    meta_path = cache / META_FILE
    needed = tiles(boundaries)
    if not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de NASADEM en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    missing = [tile_name(lat, lon) for lat, lon in needed if tile_name(lat, lon) not in meta.get("tiles", [])]
    if missing:
        raise FileNotFoundError(f"A la caché de NASADEM en {cache} le faltan mosaicos: {missing}. Bájela con --descargar")
    cells = pl.concat([tile_cells(read_tile(cache / f"{tile_name(lat, lon)}.tif", lat, lon), lat, lon) for lat, lon in needed])
    return assign(cells, boundaries), meta


def grid_cells(cells: pl.DataFrame) -> pl.DataFrame:
    """La parte de NASADEM de `grid_cells`. El suelo (HU-181) va nulo hasta que se publique, y por eso todas las celdas
    son `partial`, como dice el contrato: a la celda le falta una fuente (R1)."""
    return cells.select(
        "cell_id",
        "lat",
        "lon",
        "municipality_id",
        "altitude_m",
        "slope_pct",
        *(pl.lit(None, dtype=pl.Float64).alias(name) for name in SOIL_COLUMNS),
        pl.lit(None, dtype=pl.String).alias("texture_class"),
        pl.lit("partial").alias("quality"),
        pl.when(pl.col("altitude_m").is_not_null())
        .then(pl.lit([SOURCE_ID]))
        .otherwise(pl.lit([], dtype=pl.List(pl.String)))
        .alias("source_ids"),
    ).sort("cell_id")


def cell_id_of(lat: float, lon: float) -> str:
    """La celda de la rejilla del contrato que contiene un punto: `"{fila}_{columna}"` («La rejilla de 250 m»)."""
    return f"{math.floor((90 - lat) / CELL_DEG)}_{math.floor((lon + 180) / CELL_DEG)}"


def municipality_terrain(cells: pl.DataFrame, municipalities: pl.DataFrame) -> pl.DataFrame:
    """La altitud y la pendiente de cada municipio (decidido por Felipe el 10 de noviembre de 2026):

    - `altitude_m`: la de la celda que contiene el punto de DIVIPOLA, la cabecera. Es la que corrige la temperatura: ahí
      están el pueblo, las fincas del valle y la estación del IDEAM. La mediana de todo el municipio daría, en Duitama,
      el clima del páramo (3110 m frente a 2527 m).
    - `slope_pct`: la mediana de las celdas del municipio. Para la erosión importa cómo es todo el terreno.
    - `cells`: cuántas celdas con dato tiene el municipio.
    Sin celda de la cabecera con dato, la altitud queda nula (R1).
    """
    points = municipalities.drop_nulls(["lat", "lon"])
    towns = points.select(
        "municipality_id",
        pl.Series("cell_id", [cell_id_of(lat, lon) for lat, lon in points.select("lat", "lon").iter_rows()], dtype=pl.String),
    ).join(cells.select("cell_id", "altitude_m"), on="cell_id", how="left")
    slopes = (
        cells.filter(pl.col("altitude_m").is_not_null())
        .group_by("municipality_id")
        .agg(pl.col("slope_pct").median().round(1).alias("slope_pct"), pl.len().alias("cells"))
    )
    return (
        towns.join(slopes, on="municipality_id", how="full", coalesce=True)
        .select("municipality_id", "altitude_m", "slope_pct", pl.col("cells").fill_null(0))
        .sort("municipality_id")
    )


def source(meta: dict[str, Any]) -> dict[str, Any]:
    """La fila de NASADEM en `sources` (R8)."""
    tiles_text = ", ".join(meta.get("tiles", []))
    return {
        "source_id": SOURCE_ID,
        "name": f"{PRODUCT}: modelo de elevación de 1 segundo de arco (unos 30 m)",
        "institution": "NASA Jet Propulsion Laboratory (JPL); distribuido por el LP DAAC de la NASA y el USGS",
        "url": DOI_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": "Misión SRTM, del 11 al 21 de febrero de 2000",
        "coverage": f"Mundial entre 56° S y 60° N; bajados los mosaicos {tiles_text}",
        "license": "Datos abiertos de la NASA (política de datos de ESDS): sin restricciones de uso, con cita",
        "citation": "NASA JPL (2020). NASADEM Merged DEM Global 1 arc second V001. NASA EOSDIS Land Processes DAAC. "
        "https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001",
        "notes": "Copia en GeoTIFF de Microsoft Planetary Computer, sin cuenta. Altitud de cada celda de 250 m: promedio de "
        "sus 9 × 9 píxeles; pendiente: mediana de la de sus píxeles, calculada a 30 m. La de un municipio es la mediana de "
        "sus celdas.",
    }


def with_terrain(municipalities: pl.DataFrame, terrain: pl.DataFrame) -> pl.DataFrame:
    """`altitude_m` y `slope_pct` de cada municipio (`municipality_terrain`). Un municipio sin dato queda con ellos nulos
    (R1). La fila suma la fuente solo si tiene altitud."""
    return (
        municipalities.drop("altitude_m", "slope_pct")
        .join(terrain.select("municipality_id", "altitude_m", "slope_pct"), on="municipality_id", how="left")
        .select(municipalities.columns)
        .with_columns(
            pl.when(pl.col("altitude_m").is_not_null() & ~pl.col("source_ids").list.contains(SOURCE_ID))
            .then(pl.concat_list("source_ids", pl.lit(SOURCE_ID)).list.sort())
            .otherwise(pl.col("source_ids"))
            .alias("source_ids")
        )
    )
