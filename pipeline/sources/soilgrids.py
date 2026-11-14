"""Suelo de la región: SoilGrids 2.0 de ISRIC (HU-181; specs/02-contratos.md, `grid_cells` y `soil_municipality`).

SoilGrids da, en píxeles de 250 m, el pH en agua, el carbono orgánico, el nitrógeno y la arcilla, la arena y el limo por
capas (0-5, 5-15 y 15-30 cm), con su media y sus percentiles 5 y 95. Es un modelo (aprendizaje automático sobre perfiles
de suelo y covariables), no una medición del lote (R10).

- Se baja por WCS (`maps.isric.org`, sin cuenta), por mosaicos de 1°, en la rejilla común de 0,0025° (WGS84). El
  servidor lleva su proyección (Homolosine) a esa rejilla con vecino más cercano: el valor de cada celda es el del píxel
  de SoilGrids que contiene su centro, como pide el contrato.
- De 0 a 30 cm: el promedio de las tres capas ponderado por su grosor (5, 10 y 15 cm). Si falta una capa, la propiedad
  queda nula: no se rellena (R1). Los percentiles 5 y 95 del pH y del carbono orgánico se promedian igual, capa por capa;
  es una aproximación del intervalo de 0 a 30 cm, porque los percentiles no se suman, y se dice en `sources`.
- Un píxel en 0 es «sin dato» (agua, zona urbana o fuera del mapa): ninguna de estas propiedades vale 0 en un suelo.
- La clase de textura sale de la arcilla, la arena y el limo con el triángulo de texturas del USDA, con los nombres en
  español que usa el IGAC.
"""

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import tifffile

from common.logging import get_logger
from pipeline import schema
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.soilgrids")

SOURCE_ID = "soilgrids"
TEXTURE_SOURCE_ID = "usda_textura"
WCS_URL = "https://maps.isric.org/mapserv"
CRS = "http://www.opengis.net/def/crs/EPSG/0/4326"
CACHE = Path("data/raw/soilgrids")
META_FILE = "soilgrids.meta.json"
ATTEMPTS = 5
PAUSE_S = 10
WORKERS = 2
CELLS_PER_DEGREE = 400
# Las capas de 0 a 30 cm y su grosor (cm), para el promedio ponderado.
DEPTHS = (("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15))
# Propiedad de SoilGrids → (columna del contrato, divisor a la unidad del contrato, ¿con percentiles 5 y 95?).
# Unidades de SoilGrids: pH × 10; carbono orgánico en dg/kg; nitrógeno en cg/kg; arcilla, arena y limo en g/kg.
PROPERTIES = {
    "phh2o": ("ph", 10, True),
    "soc": ("soc_g_kg", 10, True),
    "nitrogen": ("nitrogen_g_kg", 100, False),
    "clay": ("clay_pct", 10, False),
    "sand": ("sand_pct", 10, False),
    "silt": ("silt_pct", 10, False),
}
# Del percentil de SoilGrids al sufijo de la columna del contrato (`ph_p05`, `soc_p95`).
QUANTILES = {"Q0.05": "p05", "Q0.95": "p95"}
NUMERIC = ("ph", "ph_p05", "ph_p95", "soc_g_kg", "soc_p05", "soc_p95", "nitrogen_g_kg", "clay_pct", "sand_pct", "silt_pct")
# Una celda con suelo vale `ok` en `soil_municipality` si las celdas con suelo son al menos esta parte del municipio.
MIN_CELL_SHARE = 0.9


class TileError(ValueError):
    """Un mosaico no es el que se esperaba (tamaño o georreferencia). El mensaje dice qué falla."""


def coverages() -> list[tuple[str, str]]:
    """Los mapas que se bajan: (propiedad, id de la cobertura en el WCS), en orden (R4)."""
    out = []
    for prop, (_, _, with_quantiles) in PROPERTIES.items():
        stats = ("mean", *QUANTILES) if with_quantiles else ("mean",)
        out.extend((prop, f"{prop}_{depth}_{stat}") for depth, _ in DEPTHS for stat in stats)
    return out


def tile_name(lat: int, lon: int) -> str:
    return f"{'n' if lat >= 0 else 's'}{abs(lat):02d}{'e' if lon >= 0 else 'w'}{abs(lon):03d}"


def _url(prop: str, coverage: str, lat: int, lon: int) -> str:
    params = [
        ("map", f"/map/{prop}.map"),
        ("SERVICE", "WCS"),
        ("VERSION", "2.0.1"),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", coverage),
        ("FORMAT", "GEOTIFF_INT16"),
        ("SUBSET", f"long({lon},{lon + 1})"),
        ("SUBSET", f"lat({lat},{lat + 1})"),
        ("SUBSETTINGCRS", CRS),
        ("OUTPUTCRS", CRS),
        ("SCALESIZE", f"long({CELLS_PER_DEGREE}),lat({CELLS_PER_DEGREE})"),
    ]
    return f"{WCS_URL}?{urllib.parse.urlencode(params)}"


def read_tile(path: Path, lat: int, lon: int) -> np.ndarray:
    """Los valores de un mosaico, tal como vienen de SoilGrids (enteros). Falla si no es el mosaico de (`lat`, `lon`) en
    la rejilla de 0,0025°: así no se lee mal un archivo distinto."""
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        tags = {tag.name: tag.value for tag in page.tags.values()}
        values = page.asarray()
    if values.shape != (CELLS_PER_DEGREE, CELLS_PER_DEGREE):
        raise TileError(f"{path.name}: {values.shape} píxeles, se esperaban {CELLS_PER_DEGREE} × {CELLS_PER_DEGREE}")
    tie, scale = tags.get("ModelTiepointTag"), tags.get("ModelPixelScaleTag")
    if tie is None or scale is None or abs(tie[3] - lon) > 1e-6 or abs(tie[4] - (lat + 1)) > 1e-6:
        raise TileError(f"{path.name}: la esquina noroeste no es ({lat + 1}, {lon})")
    if abs(scale[0] - schema.GRID_STEP_DEG) > 1e-9 or abs(scale[1] - schema.GRID_STEP_DEG) > 1e-9:
        raise TileError(f"{path.name}: el píxel mide {scale[:2]}, no {schema.GRID_STEP_DEG}°")
    return values


def _fetch_tile(prop: str, coverage: str, lat: int, lon: int, cache: Path) -> None:
    settings = get_settings()
    dest = cache / tile_name(lat, lon) / f"{coverage}.tif"
    if dest.exists():
        return
    partial = dest.with_name(dest.name + ".download")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(_url(prop, coverage, lat, lon), headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310
            fetch(request, partial, settings.soilgrids_timeout_s, int(settings.soilgrids_max_mb * 2**20))
            read_tile(partial, lat, lon)
            partial.replace(dest)
            return
        except (OSError, TileError) as error:
            reason = f"{type(error).__name__}: {error}"
            if attempt == ATTEMPTS:
                raise DownloadError(f"SoilGrids: {coverage} de {tile_name(lat, lon)} no bajó ({reason})") from error
            log.warning("source_download_retry", source=SOURCE_ID, coverage=coverage, attempt=attempt, reason=reason)
            time.sleep(PAUSE_S * attempt)
        finally:
            partial.unlink(missing_ok=True)


def download(tile_ids: list[tuple[int, int]], cache: Path = CACHE) -> Path:
    """Baja cada mapa de cada mosaico a la caché. Es lo único que usa la red. Un mapa que ya está no se vuelve a bajar.

    El manifiesto de la caché (`META_FILE`) se escribe al final, solo si bajaron todos: una caché a medias no se usa.
    """
    cache.mkdir(parents=True, exist_ok=True)
    (cache / META_FILE).unlink(missing_ok=True)
    jobs = [(prop, coverage, lat, lon) for lat, lon in tile_ids for prop, coverage in coverages()]
    for lat, lon in tile_ids:
        (cache / tile_name(lat, lon)).mkdir(exist_ok=True)
    log.info("source_downloading", source=SOURCE_ID, maps=len(jobs), detail=f"Bajando SoilGrids: {len(jobs)} mapas a {cache}")
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda job: _fetch_tile(*job, cache), jobs))
    meta = {
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "url": WCS_URL,
        "tiles": [tile_name(lat, lon) for lat, lon in tile_ids],
        "coverages": [coverage for _, coverage in coverages()],
    }
    (cache / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("source_downloaded", source=SOURCE_ID, maps=len(jobs), detail=f"SoilGrids: {len(jobs)} mapas en {cache}")
    return cache


def layered(values: dict[str, np.ndarray], divisor: float) -> np.ndarray:
    """El promedio de 0 a 30 cm de una estadística, ponderado por el grosor de cada capa, en la unidad del contrato. Un
    píxel en 0 en alguna capa es «sin dato» y queda NaN (R1)."""
    total = sum(thickness for _, thickness in DEPTHS)
    stack = np.stack([values[depth].astype(np.float64) for depth, _ in DEPTHS])
    stack[stack <= 0] = np.nan
    weights = np.array([thickness for _, thickness in DEPTHS], dtype=np.float64)[:, None, None]
    return (stack * weights).sum(axis=0) / total / divisor


def tile_soil(cache: Path, lat: int, lon: int) -> pl.DataFrame:
    """El suelo de 0 a 30 cm de cada celda de un mosaico: `cell_id` y las columnas numéricas del contrato."""
    name = tile_name(lat, lon)
    columns: dict[str, np.ndarray] = {}
    for prop, (column, divisor, with_quantiles) in PROPERTIES.items():
        for stat, suffix in (("mean", None), *(QUANTILES.items() if with_quantiles else ())):
            maps = {depth: read_tile(cache / name / f"{prop}_{depth}_{stat}.tif", lat, lon) for depth, _ in DEPTHS}
            key = column if suffix is None else f"{column.split('_')[0]}_{suffix}"
            columns[key] = layered(maps, divisor).ravel()
    row0 = round((90 - (lat + 1)) / schema.GRID_STEP_DEG)
    col0 = round((lon + 180) / schema.GRID_STEP_DEG)
    rows, cols = np.divmod(np.arange(CELLS_PER_DEGREE * CELLS_PER_DEGREE), CELLS_PER_DEGREE)
    cell_ids = [f"{r}_{c}" for r, c in zip(row0 + rows, col0 + cols, strict=True)]
    return pl.DataFrame({"cell_id": cell_ids, **{c: columns[c] for c in NUMERIC}}).with_columns(
        pl.col(c).fill_nan(None).round(2) for c in NUMERIC
    )


def texture_class(clay: float | None, sand: float | None, silt: float | None) -> str | None:
    """La clase de textura del triángulo del USDA (las reglas de la calculadora de texturas del NRCS), con el nombre en
    español. Las tres fracciones se llevan a 100 antes de clasificar. Sin alguna, nula (R1)."""
    if clay is None or sand is None or silt is None or clay + sand + silt <= 0:
        return None
    total = clay + sand + silt
    clay, sand, silt = 100 * clay / total, 100 * sand / total, 100 * silt / total
    if silt + 1.5 * clay < 15:
        return "arenoso"
    if silt + 2 * clay < 30:
        return "arenoso franco"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "franco arenoso"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "franco"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "franco limoso"
    if silt >= 80 and clay < 12:
        return "limoso"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "franco arcillo arenoso"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "franco arcilloso"
    if 27 <= clay < 40 and sand <= 20:
        return "franco arcillo limoso"
    if clay >= 35 and sand > 45:
        return "arcillo arenoso"
    if clay >= 40 and silt >= 40:
        return "arcillo limoso"
    return "arcilloso"


def read_cache(tile_ids: list[tuple[int, int]], cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """El suelo de cada celda de los mosaicos, desde la caché. Sin la caché completa, `FileNotFoundError`."""
    meta_path = cache / META_FILE
    if not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de SoilGrids en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    missing = [tile_name(lat, lon) for lat, lon in tile_ids if tile_name(lat, lon) not in meta.get("tiles", [])]
    if missing:
        raise FileNotFoundError(f"A la caché de SoilGrids en {cache} le faltan mosaicos: {missing}. Bájela con --descargar")
    soil = pl.concat([tile_soil(cache, lat, lon) for lat, lon in tile_ids])
    return soil, meta


def with_soil(grid: pl.DataFrame, soil: pl.DataFrame) -> pl.DataFrame:
    """`grid_cells` con el suelo de SoilGrids. Una celda es `ok` con la altitud y todo el suelo; si le falta algo,
    `partial` (R1). `source_ids` dice qué fuentes tiene cada celda."""
    columns = list(schema.TABLES["grid_cells"].columns)
    textured = soil.with_columns(
        pl.struct("clay_pct", "sand_pct", "silt_pct")
        .map_elements(lambda r: texture_class(r["clay_pct"], r["sand_pct"], r["silt_pct"]), return_dtype=pl.String)
        .alias("texture_class")
    )
    has_soil = pl.all_horizontal(pl.col(c).is_not_null() for c in (*NUMERIC, "texture_class"))
    return (
        grid.drop(*NUMERIC, "texture_class")
        .join(textured, on="cell_id", how="left")
        .with_columns(
            pl.when(has_soil & pl.col("altitude_m").is_not_null() & pl.col("slope_pct").is_not_null())
            .then(pl.lit("ok"))
            .otherwise(pl.lit("partial"))
            .alias("quality"),
            pl.when(pl.any_horizontal(pl.col(c).is_not_null() for c in NUMERIC))
            .then(pl.col("source_ids").list.concat(pl.lit([SOURCE_ID])))
            .otherwise(pl.col("source_ids"))
            .alias("source_ids"),
        )
        .select(columns)
        .sort("cell_id")
    )


def soil_municipality(grid: pl.DataFrame) -> pl.DataFrame:
    """La tabla `soil_municipality`: la mediana de las celdas con suelo de cada municipio (los percentiles también, como
    mediana de los de cada celda) y la textura más frecuente (en empate, la primera en orden alfabético, R4).

    `cells` son las celdas con suelo. `ok` si son al menos el 90 % de las celdas del municipio; si no, `partial`; sin
    ninguna, el municipio no tiene fila (R1).
    """
    columns = list(schema.TABLES["soil_municipality"].columns)
    with_soil = pl.col("ph").is_not_null()
    texture = (
        grid.filter(pl.col("texture_class").is_not_null())
        .group_by("municipality_id", "texture_class")
        .len()
        .sort(["municipality_id", "len", "texture_class"], descending=[False, True, False])
        .unique("municipality_id", keep="first", maintain_order=True)
        .select("municipality_id", "texture_class")
    )
    return (
        grid.group_by("municipality_id")
        .agg(
            *(pl.col(c).filter(pl.col(c).is_not_null()).median().round(2).alias(c) for c in NUMERIC),
            with_soil.sum().cast(pl.Int32).alias("cells"),
            pl.len().alias("all_cells"),
        )
        .filter(pl.col("cells") > 0)
        .join(texture, on="municipality_id", how="left")
        .with_columns(
            pl.when(pl.col("cells") >= MIN_CELL_SHARE * pl.col("all_cells"))
            .then(pl.lit("ok"))
            .otherwise(pl.lit("partial"))
            .alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .select(columns)
        .sort("municipality_id")
    )


def sources(meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Las filas de `sources` (R8): SoilGrids y el triángulo de texturas del USDA."""
    tiles_text = ", ".join(meta.get("tiles", []))
    return [
        {
            "source_id": SOURCE_ID,
            "name": "SoilGrids 2.0: pH, carbono orgánico, nitrógeno y textura de 0 a 30 cm (250 m)",
            "institution": "ISRIC - World Soil Information",
            "url": "https://doi.org/10.5194/soil-7-217-2021",
            "downloaded_at": meta.get("downloaded_at"),
            "period_covered": None,
            "coverage": f"Mundial; bajados los mosaicos de 1° {tiles_text}",
            "license": "CC BY 4.0 (https://www.isric.org/explore/soilgrids/faq-soilgrids)",
            "citation": "Poggio, L., de Sousa, L. M., Batjes, N. H., Heuvelink, G. B. M., Kempen, B., Ribeiro, E. y Rossiter, "
            "D. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7, "
            "217-240. https://doi.org/10.5194/soil-7-217-2021",
            "notes": "Es un modelo de 250 m, no una medición del lote (R10): se recomienda un análisis de suelo. Se baja por WCS "
            "(maps.isric.org) en la rejilla común de 0,0025°, con el valor del píxel que contiene el centro de cada celda. De 0 "
            "a 30 cm: promedio de las capas 0-5, 5-15 y 15-30 cm ponderado por su grosor. Los percentiles 5 y 95 del pH y del "
            "carbono orgánico se promedian igual, capa por capa: es una aproximación del intervalo de 0 a 30 cm. Un píxel en 0 "
            "es «sin dato» y queda nulo.",
        },
        {
            "source_id": TEXTURE_SOURCE_ID,
            "name": "Triángulo de texturas del USDA (calculadora de texturas del NRCS)",
            "institution": "USDA Natural Resources Conservation Service",
            "url": "https://www.nrcs.usda.gov/resources/education-and-teaching-materials/soil-texture-calculator",
            "downloaded_at": meta.get("downloaded_at", "")[:10] or None,
            "period_covered": None,
            "coverage": "Mundial",
            "license": "Obra del gobierno de los Estados Unidos, de dominio público",
            "citation": None,
            "notes": "Las 12 clases de textura del USDA desde la arcilla, la arena y el limo de SoilGrids (`texture_class` de "
            "grid_cells y soil_municipality), con los nombres en español que usa el IGAC (por ejemplo, «franco arcilloso» es "
            "clay loam).",
        },
    ]
