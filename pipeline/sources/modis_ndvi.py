"""Verdor del campo por municipio con MODIS NDVI (HU-208): `ndvi_municipality` y `ndvi_municipality_normal`.

El producto es MOD13Q1 versión 061 (satélite Terra, colección `C1748066515-LPCLOUD` en el CMR de la NASA): el NDVI en
píxeles de 250 m, en compuestos de 16 días (23 por año), desde febrero de 2000. Cada tesela pesa unos 175 MB; por
OPeNDAP se baja solo el recuadro de la región de la tesela `h10v08`, con dos capas: el NDVI y la confiabilidad del
píxel (`pixel_reliability`). Pide una cuenta de NASA Earthdata, como IMERG.

- **Desde 2023:** OPeNDAP solo sirve completos los compuestos desde 2023; de los anteriores responden 130 de 484 y el
  resto da 404 (comprobado el 14 de noviembre de 2026). Se baja desde el primer año de la normal (`ndvi.normal` en
  `region.yaml`) y nunca se completa con otro producto (R1).

- **Muestra:** se toma un píxel de cada `sample_step` en filas y en columnas (`ndvi` en `region.yaml`; con 4, un
  píxel de 250 m por cada kilómetro). Cada píxel va con el municipio que contiene su centro. Bajar todos los píxeles
  son unos 5 GB; la mediana de un municipio casi no cambia con la muestra.
- **Nubes:** un píxel es válido si su confiabilidad es 0 (bueno) o 1 (marginal); 2 es nieve o hielo, 3 es nube y -1 es
  sin dato (guía del usuario de MOD13, tabla 4). `valid_pixels_pct` es el porcentaje de píxeles válidos del municipio.
- **`ndvi_median`** es la mediana de los píxeles válidos. Con menos de `min_valid_pct` válidos, el periodo es `partial`;
  sin ninguno, no se publica. Nunca se interpola (R1).
- **`ndvi_municipality_normal`** es el promedio 2023–2025, por periodo del año, de los `ndvi_median` que salieron `ok`.
  Se llama «promedio» y no normal: son 3 años, no un clima de 30 (R5; revisión de Haider del PR #126). Con menos de
  `min_publish_years` años `ok` (2) no hay fila: un solo año no es un promedio. Con menos de `min_years` (3), `partial`.

Sin máscara de cultivos: el valor es de todo el municipio, con sus bosques, páramos y ciudades, y se dice (R10). El
NDVI es contraste, no una señal: no cambia la luz ni el orden de las ventanas.
"""

import gzip
import json
import math
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import shapely

from common.logging import get_logger
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.modis_ndvi")

SOURCE_ID = "modis_ndvi"
COLLECTION_ID = "C1748066515-LPCLOUD"
VERSION = "061"
PRODUCT = "MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)"
DOI_URL = "https://doi.org/10.5067/MODIS/MOD13Q1.061"
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
OPENDAP_URL = "https://opendap.earthdata.nasa.gov/collections/{collection}/granules/{granule}.dap.csv"
GROUP = "/MODIS_Grid_16DAY_250m_500m_VI/Data_Fields"
NDVI_FIELD = "_250m_16_days_NDVI"
RELIABILITY_FIELD = "_250m_16_days_pixel_reliability"
# La tesela de la rejilla sinusoidal de MODIS que cubre la región piloto: de 0° a 10° N y, en x, de -80° a -70°.
TILE = "h10v08"
TILE_H, TILE_V = 10, 8
PIXELS = 4800
PIXELS_PER_DEGREE = 480
# El NDVI viene multiplicado por 10 000; fuera de -2000 a 10 000 es el valor de relleno (-3000).
SCALE = 0.0001
NDVI_MIN, NDVI_MAX = -2000, 10000
# Confiabilidad del píxel que se acepta: 0 (bueno) y 1 (marginal).
RELIABLE = (0, 1)
PERIODS = 23
CACHE = Path("data/raw/modis_ndvi")
META_FILE = "modis_ndvi.meta.json"
ATTEMPTS = 4
PAUSE_S = 10
WORKERS = 4

NDVI_SCHEMA = {
    "municipality_id": pl.String,
    "year": pl.Int16,
    "period": pl.Int8,
    "ndvi_median": pl.Float64,
    "valid_pixels_pct": pl.Float64,
    "quality": pl.String,
    "source_id": pl.String,
}
NORMAL_SCHEMA = {
    "municipality_id": pl.String,
    "period": pl.Int8,
    "ndvi_normal": pl.Float64,
    "years": pl.Int16,
    "quality": pl.String,
    "source_id": pl.String,
}

# (fila inicial, fila final, columna inicial, columna final, paso): los píxeles de la tesela que se bajan.
Area = tuple[int, int, int, int, int]


@dataclass(frozen=True)
class Config:
    """La configuración del verdor en `region.yaml` (`ndvi`)."""

    sample_step: int
    min_valid_pct: float
    first_year: int
    last_year: int
    min_years: int
    min_publish_years: int


def config_from_region(region: dict[str, Any]) -> Config | None:
    """Sin el bloque `ndvi` en `region.yaml` no hay verdor: no se inventan cortes."""
    block = region.get("ndvi")
    if block is None:
        return None
    normal = block["normal"]
    return Config(
        sample_step=int(block["sample_step"]),
        min_valid_pct=float(block["min_valid_pct"]),
        first_year=int(normal["first_year"]),
        last_year=int(normal["last_year"]),
        min_years=int(normal["min_years"]),
        min_publish_years=int(normal["min_publish_years"]),
    )


def period_of(day_of_year: int) -> int:
    """El compuesto de 16 días del año (1 a 23) que empieza en ese día: el día 1 es el 1 y el 353, el 23."""
    return (day_of_year - 1) // 16 + 1


def pixel_center(row: int, col: int) -> tuple[float, float]:
    """Latitud y longitud del centro de un píxel de la tesela, en la proyección sinusoidal de MODIS: las filas bajan
    desde el borde norte de la tesela y las columnas van en grados de longitud por el coseno de la latitud."""
    lat = 90 - TILE_V * 10 - (row + 0.5) / PIXELS_PER_DEGREE
    x = -180 + TILE_H * 10 + (col + 0.5) / PIXELS_PER_DEGREE
    return lat, x / math.cos(math.radians(lat))


def pixel_of(lat: float, lon: float) -> tuple[float, float]:
    """Fila y columna (con decimales) de un punto en la tesela."""
    row = (90 - TILE_V * 10 - lat) * PIXELS_PER_DEGREE
    col = (lon * math.cos(math.radians(lat)) + 180 - TILE_H * 10) * PIXELS_PER_DEGREE
    return row, col


def window(boundaries: pl.DataFrame, step: int) -> Area:
    """El recuadro de píxeles de la tesela que cubre los municipios. Falla si la región se sale de la tesela: habría
    que bajar otra, y no se publica un verdor a medias (R1)."""
    bounds = shapely.bounds(shapely.from_wkb(boundaries["geometry"].to_list()))
    west, south, east, north = bounds[:, 0].min(), bounds[:, 1].min(), bounds[:, 2].max(), bounds[:, 3].max()
    corners = [pixel_of(lat, lon) for lat in (south, north) for lon in (west, east)]
    row0, row1 = math.floor(min(r for r, _ in corners)), math.ceil(max(r for r, _ in corners))
    col0, col1 = math.floor(min(c for _, c in corners)), math.ceil(max(c for _, c in corners))
    if row0 < 0 or col0 < 0 or row1 >= PIXELS or col1 >= PIXELS:
        raise ValueError(f"La región se sale de la tesela {TILE} de MODIS: filas {row0} a {row1}, columnas {col0} a {col1}")
    return row0, row1, col0, col1, step


def shape(area: Area) -> tuple[int, int]:
    """Cuántas filas y columnas trae la muestra del recuadro."""
    row0, row1, col0, col1, step = area
    return (row1 - row0) // step + 1, (col1 - col0) // step + 1


def pixel_municipality(boundaries: pl.DataFrame, area: Area) -> np.ndarray:
    """Para cada píxel de la muestra, el índice de su municipio en la lista ordenada de `municipality_id`, o -1 si su
    centro no cae en ninguno. Un centro justo en el límite de dos va con el de llave menor (R4)."""
    row0, _, col0, _, step = area
    rows, cols = shape(area)
    lat = np.array([pixel_center(row0 + i * step, 0)[0] for i in range(rows)])
    x = -180 + TILE_H * 10 + (col0 + np.arange(cols) * step + 0.5) / PIXELS_PER_DEGREE
    lats = np.repeat(lat[:, None], cols, axis=1)
    lons = x[None, :] / np.cos(np.radians(lats))
    owner = np.full((rows, cols), -1, dtype=np.int32)
    ordered = boundaries.sort("municipality_id", descending=True)
    ids = sorted(boundaries["municipality_id"].to_list())
    for municipality_id, wkb in ordered.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        west, south, east, north = shapely.bounds(geometry)
        near = (lats >= south) & (lats <= north) & (lons >= west) & (lons <= east)
        if not near.any():
            continue
        inside = shapely.contains_xy(geometry, lons[near], lats[near])
        block = owner[near]
        block[inside] = ids.index(municipality_id)
        owner[near] = block
    return owner


def parse_csv(text: str, area: Area) -> tuple[np.ndarray, np.ndarray]:
    """El NDVI (entero, por 10 000) y la confiabilidad de cada píxel de la respuesta en CSV de OPeNDAP.

    OPeNDAP da una línea por fila («…/_250m_16_days_NDVI[3], v0, v1, …») con un valor por columna. Falla si no trae
    todo el recuadro de las dos capas: así no se lee mal una respuesta distinta.
    """
    rows, cols = shape(area)
    ndvi = np.full((rows, cols), NDVI_MIN - 1, dtype=np.int32)
    reliability = np.full((rows, cols), -1, dtype=np.int32)
    seen = {NDVI_FIELD: 0, RELIABILITY_FIELD: 0}
    pattern = re.compile(rf"{re.escape(GROUP)}/({NDVI_FIELD}|{RELIABILITY_FIELD})\[(\d+)\],(.*)")
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        values = np.array(match.group(3).split(","), dtype=np.int32)
        if values.size != cols:
            raise DownloadError(f"MODIS: una línea trae {values.size} columnas y el recuadro tiene {cols}")
        target = ndvi if match.group(1) == NDVI_FIELD else reliability
        target[int(match.group(2))] = values
        seen[match.group(1)] += 1
    if seen[NDVI_FIELD] != rows or seen[RELIABILITY_FIELD] != rows:
        raise DownloadError(f"MODIS: la respuesta trae {seen} filas y el recuadro tiene {rows} de cada capa")
    return ndvi, reliability


def granules(timeout_s: float) -> list[tuple[int, int, str]]:
    """Los compuestos de la tesela en el catálogo de la NASA (CMR): año, día del año en que empieza y nombre del
    archivo, del más antiguo al más reciente. El CMR no pide cuenta. Falla si alguno no es de la versión esperada."""
    found: list[tuple[int, int, str]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "collection_concept_id": COLLECTION_ID,
                "readable_granule_name": f"*.{TILE}.*",
                "options[readable_granule_name][pattern]": "true",
                "page_size": 2000,
                "page_num": page,
                "sort_key": "start_date",
            }
        )
        request = urllib.request.Request(f"{CMR_URL}?{query}", headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310 - dirección fija
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            entries = json.load(response)["feed"]["entry"]
        for entry in entries:
            match = re.fullmatch(rf"MOD13Q1\.A(\d{{4}})(\d{{3}})\.{TILE}\.(\d{{3}})\.\d+", entry["title"])
            if not match:
                continue
            if match.group(3) != VERSION:
                raise DownloadError(f"MODIS: {entry['title']} no es de la versión {VERSION} que se verificó")
            found.append((int(match.group(1)), int(match.group(2)), entry["title"]))
        if len(entries) < 2000:
            # Un compuesto reprocesado sale dos veces: queda el último que se generó (el de nombre mayor).
            latest = {(year, day): title for year, day, title in sorted(found)}
            return [(year, day, title) for (year, day), title in sorted(latest.items())]
        page += 1


def composite_file(cache: Path, year: int, day: int) -> Path:
    return cache / f"A{year}{day:03d}.csv.gz"


def read_composite(path: Path, area: Area) -> tuple[np.ndarray, np.ndarray]:
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return parse_csv(file.read(), area)


def _fetch_composite(granule: str, area: Area, dest: Path, token: str) -> None:
    settings = get_settings()
    row0, row1, col0, col1, step = area
    box = f"[{row0}:{step}:{row1}][{col0}:{step}:{col1}]"
    constraint = f"{GROUP}/{NDVI_FIELD}{box};{GROUP}/{RELIABILITY_FIELD}{box}"
    url = OPENDAP_URL.format(collection=COLLECTION_ID, granule=urllib.parse.quote(granule, safe=""))
    url += "?dap4.ce=" + urllib.parse.quote(constraint, safe="")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "AgroSense-pipeline"}
    partial = dest.with_name(dest.name + ".download")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers=headers)  # noqa: S310 - dirección fija
            fetch(request, partial, settings.modis_timeout_s, int(settings.modis_max_mb * 2**20))
            text = partial.read_text(encoding="utf-8")
            parse_csv(text, area)
            with gzip.open(dest.with_name(dest.name + ".tmp"), "wt", encoding="utf-8") as out:
                out.write(text)
            dest.with_name(dest.name + ".tmp").replace(dest)
            return
        except OSError as error:
            # Un 401 o un 403 no se arreglan reintentando: el token venció o la cuenta no aprobó LP DAAC.
            code = getattr(error, "code", None)
            reason = f"{type(error).__name__}: {error}"
            if code in (401, 403) or attempt == ATTEMPTS:
                raise DownloadError(f"MODIS: {granule} no bajó ({reason})") from error
            log.warning("source_download_retry", source=SOURCE_ID, granule=granule, attempt=attempt, reason=reason)
            time.sleep(PAUSE_S * attempt)
        finally:
            partial.unlink(missing_ok=True)
            dest.with_name(dest.name + ".tmp").unlink(missing_ok=True)


def download(boundaries: pl.DataFrame, config: Config, cache: Path = CACHE) -> Path:
    """Baja el recuadro de la región de cada compuesto a la caché. Es lo único que usa la red.

    Un compuesto que ya está en la caché, con el mismo recuadro, no se vuelve a bajar: si la descarga se corta, al
    repetirla retoma. El manifiesto de la caché (`META_FILE`) se escribe al final, solo si bajaron todos: una caché a
    medias no se usa.
    """
    settings = get_settings()
    secret = settings.earthdata_token.get_secret_value().strip() if settings.earthdata_token else ""
    if not secret:
        raise DownloadError("MODIS pide una cuenta de NASA Earthdata: ponga su token en AGROSENSE_EARTHDATA_TOKEN (.env.example)")
    area = window(boundaries, config.sample_step)
    cache.mkdir(parents=True, exist_ok=True)
    meta_path = cache / META_FILE
    window_path = cache / "window.json"
    old = json.loads(window_path.read_text(encoding="utf-8")) if window_path.exists() else None
    meta_path.unlink(missing_ok=True)
    if old != list(area):
        for path in cache.glob("*.csv.gz"):
            path.unlink()
    window_path.write_text(json.dumps(list(area)), encoding="utf-8")
    # Solo desde el primer año de la normal: antes de 2023 OPeNDAP no sirve la mayoría de los compuestos (ver el módulo).
    composites = [item for item in granules(settings.modis_timeout_s) if item[0] >= config.first_year]
    missing = [(y, d, g) for y, d, g in composites if not composite_file(cache, y, d).exists()]
    log.info(
        "source_downloading",
        source=SOURCE_ID,
        composites=len(missing),
        detail=f"Bajando MODIS NDVI: {len(missing)} de {len(composites)} compuestos a {cache}",
    )
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda item: _fetch_composite(item[2], area, composite_file(cache, item[0], item[1]), secret), missing))
    meta = {
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "product": PRODUCT,
        "collection": COLLECTION_ID,
        "version": VERSION,
        "tile": TILE,
        "window": list(area),
        "composites": [f"{y}{d:03d}" for y, d, _ in composites],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info(
        "source_downloaded", source=SOURCE_ID, composites=len(composites), detail=f"MODIS NDVI: {len(composites)} compuestos en {cache}"
    )
    return cache


def composite_rows(
    ndvi: np.ndarray, reliability: np.ndarray, owner: np.ndarray, ids: list[str], year: int, period: int, min_valid_pct: float
) -> list[tuple[Any, ...]]:
    """Las filas de `ndvi_municipality` de un compuesto: la mediana de los píxeles válidos de cada municipio."""
    inside = owner >= 0
    valid = inside & np.isin(reliability, RELIABLE) & (ndvi >= NDVI_MIN) & (ndvi <= NDVI_MAX)
    total = np.bincount(owner[inside], minlength=len(ids))
    order = np.argsort(owner[valid], kind="stable")
    owners, values = owner[valid][order], ndvi[valid][order]
    starts = np.searchsorted(owners, np.arange(len(ids)), side="left")
    ends = np.searchsorted(owners, np.arange(len(ids)), side="right")
    rows = []
    for index, municipality_id in enumerate(ids):
        count = int(ends[index] - starts[index])
        if count == 0:
            continue
        pct = round(100 * count / int(total[index]), 1)
        median = round(float(np.median(values[starts[index] : ends[index]])) * SCALE, 4)
        rows.append((municipality_id, year, period, median, pct, "ok" if pct >= min_valid_pct else "partial", SOURCE_ID))
    return rows


def read_cache(boundaries: pl.DataFrame, config: Config, cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """`ndvi_municipality` desde la caché. Sin la caché completa, o con otro recuadro, `FileNotFoundError`."""
    hint = "Bájela con: uv run python -m pipeline.build --descargar"
    meta_path = cache / META_FILE
    if not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de MODIS NDVI en {cache}. {hint}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    area: Area = tuple(meta["window"])  # type: ignore[assignment]
    if list(area) != list(window(boundaries, config.sample_step)):
        raise FileNotFoundError(f"La caché de MODIS NDVI en {cache} es de otro recuadro o de otra muestra. {hint}")
    owner = pixel_municipality(boundaries, area)
    ids = sorted(boundaries["municipality_id"].to_list())
    rows: list[tuple[Any, ...]] = []
    for name in meta["composites"]:
        year, day = int(name[:4]), int(name[4:])
        ndvi, reliability = read_composite(composite_file(cache, year, day), area)
        rows.extend(composite_rows(ndvi, reliability, owner, ids, year, period_of(day), config.min_valid_pct))
    meta["pixels"] = int((owner >= 0).sum())
    table = pl.DataFrame(rows, schema=NDVI_SCHEMA, orient="row").sort("municipality_id", "year", "period")
    return table, meta


def ndvi_normal(table: pl.DataFrame, config: Config) -> pl.DataFrame:
    """`ndvi_municipality_normal`: por municipio y periodo del año, el promedio de los `ndvi_median` que salieron `ok` en
    los años del promedio, solo con al menos `min_publish_years` años. Se ordena antes de promediar: mismos datos, mismo
    resultado (R4)."""
    return (
        table.filter(pl.col("year").is_between(config.first_year, config.last_year) & (pl.col("quality") == "ok"))
        .group_by("municipality_id", "period")
        .agg(pl.col("ndvi_median").sort().mean().round(4).alias("ndvi_normal"), pl.len().cast(pl.Int16).alias("years"))
        .filter(pl.col("years") >= config.min_publish_years)
        .with_columns(
            pl.when(pl.col("years") >= config.min_years).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .select(list(NORMAL_SCHEMA))
        .cast(NORMAL_SCHEMA)
        .sort("municipality_id", "period")
    )


def source(table: pl.DataFrame, meta: dict[str, Any], config: Config) -> dict[str, Any]:
    """La fila de MODIS NDVI en `sources` (R8), con la cita que pide el producto."""
    downloaded = (meta.get("downloaded_at") or "")[:10]
    period = f"De {table['year'].min()} a {table['year'].max()}, cada 16 días" if table.height else None
    citation = (
        "Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA EOSDIS Land Processes "
        "Distributed Active Archive Center. https://doi.org/10.5067/MODIS/MOD13Q1.061. "
    )
    if downloaded:
        citation += f"Consultado el {downloaded}. "
    return {
        "source_id": SOURCE_ID,
        "name": "MODIS Terra · Índice de vegetación NDVI de 250 m cada 16 días (MOD13Q1 V061)",
        "institution": "NASA, sensor MODIS del satélite Terra; distribuido por LP DAAC de la NASA y el USGS",
        "url": DOI_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": (
            f"{len(meta.get('composites', []))} compuestos de la tesela {meta.get('tile', TILE)}; {meta.get('pixels', 0)} píxeles de "
            f"250 m dentro de la región, uno de cada {config.sample_step} en filas y columnas"
        ),
        "license": "Datos abiertos de la NASA (EOSDIS), sin restricciones de uso; se cita con su DOI",
        "citation": citation,
        "notes": (
            "Verdor de la zona, no del lote (R10): la mediana de los píxeles sin nubes de todo el municipio, sin máscara de "
            "cultivos (incluye bosques, páramos y ciudades). Un píxel es válido con confiabilidad 0 (bueno) o 1 (marginal). "
            f"Con menos del {config.min_valid_pct:g} % de píxeles válidos el periodo es partial; sin ninguno, no se publica. "
            f"ndvi_municipality_normal es el promedio {config.first_year}-{config.last_year}, no una normal climática: se publica "
            f"con al menos {config.min_publish_years} años y es partial con menos de {config.min_years}. "
            "Es contraste: no cambia la luz ni el orden de las ventanas. La NASA deja de tomar datos de Terra MODIS hacia "
            "enero de 2027."
        ),
    }
