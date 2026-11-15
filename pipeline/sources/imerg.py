"""Lluvia por satélite de GPM IMERG por municipio (HU-207): la tabla `precip_month`.

El producto es el mensual de la corrida final (Final Run) de IMERG, versión 07 (`GPM_3IMERGM`, colección
`C2723754851-GES_DISC` en el CMR de la NASA): celdas de 0,1° (unos 11 km), calibrado cada mes con los pluviómetros del
GPCC. La versión 07 empieza en enero de 1998 y su corrida final llega hasta septiembre de 2025 (consultado en el CMR el
11 de noviembre de 2026). Cada archivo mundial pesa unos 18 MB; se baja solo el recuadro de la región (R1: lo que falta
no se rellena).

La lluvia de un municipio es el promedio de las celdas que tocan su polígono, ponderado por el área de cada celda que
cae dentro. La lluvia de NASA POWER sigue en `climate_month`: las dos se muestran juntas y nunca se mezclan.
"""

import calendar
import json
import math
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import shapely

from common.logging import get_logger
from pipeline.climate_normals import Normal
from pipeline.settings import get_settings
from pipeline.sources.fetch import DownloadError, fetch

log = get_logger("agrosense.pipeline.imerg")

SOURCE_ID = "imerg"
COLLECTION_ID = "C2723754851-GES_DISC"
PRODUCT = "GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07 (GPM_3IMERGM)"
DOI_URL = "https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07"
# El catálogo de la NASA (CMR) no pide cuenta; los datos sí: OPeNDAP de Earthdata, con el token de la cuenta.
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
OPENDAP_URL = "https://opendap.earthdata.nasa.gov/collections/{collection}/granules/{granule}.dap.csv"
STEP = 0.1
# Valor de «sin dato» de IMERG (`_FillValue` de `precipitation`).
FILL = -9999.9
CACHE = Path("data/raw/imerg")
META_FILE = "imerg.meta.json"
ATTEMPTS = 3
PAUSE_S = 10
WORKERS = 4

CELL_MONTH_SCHEMA = {"row": pl.Int32, "col": pl.Int32, "year": pl.Int16, "month": pl.Int8, "precip_mm": pl.Float64}
WEIGHT_SCHEMA = {"municipality_id": pl.String, "row": pl.Int32, "col": pl.Int32, "weight": pl.Float64}
PRECIP_MONTH_SCHEMA = {
    "municipality_id": pl.String,
    "year": pl.Int16,
    "month": pl.Int8,
    "source_id": pl.String,
    "precip_mm": pl.Float64,
    "precip_normal_mm": pl.Float64,
    "precip_dry_mm": pl.Float64,
    "normal_period": pl.String,
    "quality": pl.String,
}


def normal_from_region(region: dict[str, Any]) -> Normal | None:
    """El periodo normal de IMERG (`imerg_normal` en `region.yaml`) con los cortes de `climate_normal`.

    IMERG no tiene 1991-2020: su normal es otra y la respuesta dice cuál (`normal_period`). Nunca se completa con años de
    NASA POWER (R1).
    """
    config, base = region.get("imerg_normal"), Normal.from_region(region)
    if config is None or base is None:
        return None
    return Normal(
        first_year=int(config["first_year"]),
        last_year=int(config["last_year"]),
        min_years=int(config["min_years"]),
        min_day_share=base.min_day_share,
        dry_quantile=base.dry_quantile,
    )


def cell_index(lat: float, lon: float) -> tuple[int, int]:
    """La fila y la columna de la celda de IMERG que contiene el punto. La fila 0 empieza en 90° S; la columna 0, en
    180° O."""
    return math.floor((lat + 90) / STEP), math.floor((lon + 180) / STEP)


def cell_box(row: int, col: int) -> shapely.Polygon:
    lat0, lon0 = -90 + row * STEP, -180 + col * STEP
    return shapely.box(lon0, lat0, lon0 + STEP, lat0 + STEP)


def window(boundaries: pl.DataFrame) -> tuple[int, int, int, int]:
    """Las filas y columnas (primera y última, incluidas) del recuadro que cubre todos los municipios: lo que se baja."""
    x0, y0, x1, y1 = shapely.total_bounds(shapely.from_wkb(boundaries["geometry"].to_list()))
    row0, col0 = cell_index(y0, x0)
    row1, col1 = cell_index(y1, x1)
    return row0, row1, col0, col1


def weights(boundaries: pl.DataFrame) -> pl.DataFrame:
    """Cuánto de cada celda cae dentro de cada municipio: `municipality_id`, `row`, `col`, `weight`.

    El peso es el área de la parte de la celda dentro del polígono, en grados cuadrados por el coseno de la latitud (a
    estas latitudes, proporcional al área en km²). Una celda que solo toca el borde, sin área, no cuenta.
    """
    rows = []
    for municipality_id, wkb in boundaries.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        x0, y0, x1, y1 = shapely.bounds(geometry)
        row0, col0 = cell_index(y0, x0)
        row1, col1 = cell_index(y1, x1)
        for row in range(row0, row1 + 1):
            for col in range(col0, col1 + 1):
                area = shapely.area(shapely.intersection(geometry, cell_box(row, col)))
                if area > 0:
                    lat = -90 + (row + 0.5) * STEP
                    rows.append((municipality_id, row, col, area * math.cos(math.radians(lat))))
    return pl.DataFrame(rows, schema=WEIGHT_SCHEMA, orient="row").sort("municipality_id", "row", "col")


def monthly_total_mm(rate_mm_h: float | None, year: int, month: int) -> float | None:
    """IMERG mensual da la lluvia como tasa media del mes en mm/h: el total es la tasa por las horas del mes."""
    if rate_mm_h is None or math.isnan(rate_mm_h) or rate_mm_h < 0:
        return None
    return rate_mm_h * 24 * calendar.monthrange(year, month)[1]


def precip_month(cell_months: pl.DataFrame, cell_weights: pl.DataFrame, normal: Normal) -> pl.DataFrame:
    """La tabla `precip_month`: la lluvia de IMERG de cada municipio en cada mes, su normal y su año seco.

    - `precip_mm` es el promedio ponderado por área de las celdas con dato. Si las celdas con dato cubren todo el
      municipio, el mes está completo; si cubren al menos `min_day_share` (el 90 %), es `partial`; con menos, la fila no
      se publica (R1).
    - La normal y el año seco salen de los meses completos del periodo de `imerg_normal`, con al menos `min_years` años.
      Sin años suficientes quedan nulos y el mes es `partial`.
    - `quality = ok` solo con el mes completo, su normal y su año seco.
    """
    if cell_months.is_empty() or cell_weights.is_empty():
        return pl.DataFrame(schema=PRECIP_MONTH_SCHEMA)
    total = cell_weights.group_by("municipality_id").agg(pl.col("weight").sort().sum().alias("total_weight"))
    valid = pl.col("precip_mm").is_not_null()
    months = (
        cell_weights.join(cell_months, on=["row", "col"])
        .group_by("municipality_id", "year", "month")
        .agg(
            (pl.col("precip_mm") * pl.col("weight")).filter(valid).sort().sum().alias("weighted"),
            pl.col("weight").filter(valid).sort().sum().alias("valid_weight"),
        )
        .join(total, on="municipality_id")
        .with_columns((pl.col("valid_weight") / pl.col("total_weight")).alias("share"))
        .filter(pl.col("valid_weight") > 0)
        .filter(pl.col("share") >= normal.min_day_share - 1e-9)
        .with_columns(
            (pl.col("weighted") / pl.col("valid_weight")).round(1).alias("precip_mm"),
            (pl.col("share") >= 1 - 1e-9).alias("complete"),
        )
    )
    rain_normal = (
        months.filter(pl.col("complete") & pl.col("year").is_between(normal.first_year, normal.last_year))
        .group_by("municipality_id", "month")
        .agg(
            pl.col("precip_mm").sort().mean().round(1).alias("precip_normal_mm"),
            pl.col("precip_mm").quantile(normal.dry_quantile, interpolation="linear").round(1).alias("precip_dry_mm"),
            pl.len().alias("years"),
        )
        .filter(pl.col("years") >= normal.min_years)
        .with_columns(pl.lit(f"{normal.first_year}-{normal.last_year}").alias("normal_period"))
        .select("municipality_id", "month", "precip_normal_mm", "precip_dry_mm", "normal_period")
    )
    complete = pl.col("complete") & pl.col("precip_normal_mm").is_not_null() & pl.col("precip_dry_mm").is_not_null()
    return (
        months.join(rain_normal, on=["municipality_id", "month"], how="left")
        .select(
            "municipality_id",
            "year",
            "month",
            pl.lit(SOURCE_ID).alias("source_id"),
            "precip_mm",
            "precip_normal_mm",
            "precip_dry_mm",
            "normal_period",
            pl.when(complete).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
        )
        .cast(PRECIP_MONTH_SCHEMA)
        .sort("municipality_id", "year", "month")
    )


def granules(timeout_s: float) -> list[tuple[int, int, str]]:
    """Los meses que tiene la colección en el catálogo de la NASA (CMR): año, mes y nombre del archivo, del más antiguo
    al más reciente. El CMR no pide cuenta."""
    found: list[tuple[int, int, str]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"collection_concept_id": COLLECTION_ID, "page_size": 2000, "page_num": page, "sort_key": "start_date"}
        )
        request = urllib.request.Request(f"{CMR_URL}?{query}", headers={"User-Agent": "AgroSense-pipeline"})  # noqa: S310 - dirección fija
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            entries = json.load(response)["feed"]["entry"]
        for entry in entries:
            match = re.search(r"3IMERG\.(\d{4})(\d{2})01-", entry["title"])
            if match:
                found.append((int(match.group(1)), int(match.group(2)), entry["title"]))
        if len(entries) < 2000:
            return sorted(found)
        page += 1


def month_file(cache: Path, year: int, month: int) -> Path:
    return cache / f"{year}{month:02d}.csv"


def parse_csv(text: str, area: tuple[int, int, int, int]) -> list[tuple[int, int, float]]:
    """Las tasas de lluvia (mm/h) de la respuesta en CSV de OPeNDAP: `fila, columna, tasa` de cada celda del recuadro.

    OPeNDAP da una línea por columna de longitud («/Grid/precipitation[0][k], v0, v1, …») con un valor por fila de
    latitud. Falla si no trae todo el recuadro: así no se lee mal una respuesta distinta.
    """
    row0, row1, col0, col1 = area
    cells = []
    for line in text.splitlines():
        match = re.match(r"/Grid/precipitation\[0\]\[(\d+)\],(.*)", line.strip())
        if not match:
            continue
        values = [float(v) for v in match.group(2).split(",")]
        if len(values) != row1 - row0 + 1:
            raise DownloadError(f"IMERG: una línea trae {len(values)} filas y el recuadro tiene {row1 - row0 + 1}")
        col = col0 + int(match.group(1))
        cells.extend((row0 + j, col, value) for j, value in enumerate(values))
    expected = (row1 - row0 + 1) * (col1 - col0 + 1)
    if len(cells) != expected:
        raise DownloadError(f"IMERG: la respuesta trae {len(cells)} celdas y el recuadro tiene {expected}")
    return cells


def _fetch_month(granule: str, area: tuple[int, int, int, int], dest: Path, token: str) -> None:
    settings = get_settings()
    row0, row1, col0, col1 = area
    constraint = f"/Grid/precipitation[0][{col0}:{col1}][{row0}:{row1}]"
    url = OPENDAP_URL.format(collection=COLLECTION_ID, granule=urllib.parse.quote(granule, safe=""))
    url += "?dap4.ce=" + urllib.parse.quote(constraint, safe="")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "AgroSense-pipeline"}
    partial = dest.with_name(dest.name + ".download")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers=headers)  # noqa: S310 - dirección fija
            fetch(request, partial, settings.imerg_timeout_s, int(settings.imerg_max_mb * 2**20))
            parse_csv(partial.read_text(encoding="utf-8"), area)
            partial.replace(dest)
            return
        except OSError as error:
            # Un 401 o un 403 no se arreglan reintentando: el token venció o la cuenta no aprobó GES DISC.
            code = getattr(error, "code", None)
            reason = f"{type(error).__name__}: {error}"
            if code in (401, 403) or attempt == ATTEMPTS:
                raise DownloadError(f"IMERG: {granule} no bajó ({reason})") from error
            log.warning("source_download_retry", source=SOURCE_ID, granule=granule, attempt=attempt, reason=reason)
            time.sleep(PAUSE_S * attempt)
        finally:
            partial.unlink(missing_ok=True)


def download(boundaries: pl.DataFrame, cache: Path = CACHE) -> Path:
    """Baja el recuadro de la región de cada mes de IMERG a la caché. Es lo único que usa la red.

    Un mes que ya está en la caché, con el mismo recuadro, no se vuelve a bajar. El manifiesto de la caché (`META_FILE`)
    se escribe al final, solo si bajaron todos los meses: una caché a medias no se usa.
    """
    settings = get_settings()
    secret = settings.earthdata_token.get_secret_value().strip() if settings.earthdata_token else ""
    if not secret:
        raise DownloadError("IMERG pide una cuenta de NASA Earthdata: ponga su token en AGROSENSE_EARTHDATA_TOKEN (.env.example)")
    area = window(boundaries)
    cache.mkdir(parents=True, exist_ok=True)
    meta_path = cache / META_FILE
    old = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta_path.unlink(missing_ok=True)
    if old.get("window") != list(area):
        for path in cache.glob("*.csv"):
            path.unlink()
    months = granules(settings.imerg_timeout_s)
    missing = [(y, m, g) for y, m, g in months if not month_file(cache, y, m).exists()]
    log.info(
        "source_downloading",
        source=SOURCE_ID,
        months=len(missing),
        detail=f"Bajando IMERG: {len(missing)} de {len(months)} meses a {cache}",
    )
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda item: _fetch_month(item[2], area, month_file(cache, item[0], item[1]), secret), missing))
    meta = {
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "product": PRODUCT,
        "collection": COLLECTION_ID,
        "window": list(area),
        "months": [f"{y}-{m:02d}" for y, m, _ in months],
        "versions": sorted({re.sub(r".*\.(V\w+)\.HDF5$", r"\1", g) for _, _, g in months}),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("source_downloaded", source=SOURCE_ID, months=len(months), detail=f"IMERG: {len(months)} meses en {cache}")
    return cache


def read_cache(boundaries: pl.DataFrame, cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """La lluvia de cada celda en cada mes (mm del mes) desde la caché. Sin la caché completa, `FileNotFoundError`."""
    meta_path = cache / META_FILE
    if not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de IMERG en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    row0, row1, col0, col1 = meta["window"]
    need0, need1, needc0, needc1 = window(boundaries)
    if not (row0 <= need0 and need1 <= row1 and col0 <= needc0 and needc1 <= col1):
        raise FileNotFoundError(f"La caché de IMERG en {cache} no cubre la región. Bájela otra vez con --descargar")
    rows = []
    for text in meta["months"]:
        year, month = (int(part) for part in text.split("-"))
        for row, col, rate in parse_csv(month_file(cache, year, month).read_text(encoding="utf-8"), (row0, row1, col0, col1)):
            rows.append((row, col, year, month, monthly_total_mm(rate, year, month)))
    return pl.DataFrame(rows, schema=CELL_MONTH_SCHEMA, orient="row"), meta


def source(table: pl.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
    """La fila de IMERG en `sources` (R8), con la cita que pide la colección."""
    months = meta.get("months", [])
    with_data = table.drop_nulls("precip_mm")
    period = f"De {with_data['year'].min()} a {with_data['year'].max()}, mensual" if with_data.height else None
    downloaded = (meta.get("downloaded_at") or "")[:10]
    citation = (
        "Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J. y Tan, J. (2023). GPM IMERG Final Precipitation L3 1 month "
        "0.1 degree x 0.1 degree V07. Greenbelt, MD, Goddard Earth Sciences Data and Information Services Center (GES DISC). "
    )
    if downloaded:
        citation += f"Consultado el {downloaded}. "
    return {
        "source_id": SOURCE_ID,
        "name": "GPM IMERG Final Run V07 · Lluvia mensual por satélite (GPM_3IMERGM)",
        "institution": "NASA y JAXA, misión GPM (Global Precipitation Measurement); distribuido por GES DISC de la NASA",
        "url": DOI_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": f"{len(months)} meses en celdas de 0,1° (unos 11 km) del recuadro que cubre la región",
        "license": "Datos abiertos de la NASA (política de datos de ESDS): sin restricciones de uso, con cita "
        "(https://disc.gsfc.nasa.gov/data-guidelines)",
        "citation": citation + DOI_URL,
        "notes": (
            "Lluvia estimada por satélite (sensores de microondas e infrarrojo) y calibrada cada mes con los pluviómetros "
            "del GPCC: no es una medición del lote. Celda de 0,1°: un dato de la zona. La lluvia del municipio es el promedio "
            "de las celdas que tocan su polígono, ponderado por área. Un dato que falta (-9999,9) queda nulo, nunca relleno. Se "
            "bajó solo el recuadro de la región por OPeNDAP de Earthdata, con cuenta."
        ),
    }
