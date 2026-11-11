"""Reconstruye `data/published/` desde la caché (specs/02-contratos.md, «Tablas publicadas»).

    uv run python -m pipeline.build              # lee la caché de data/raw/ y publica
    uv run python -m pipeline.build --descargar  # antes, baja otra vez las fuentes a la caché
    uv run python -m pipeline.build --verificar  # solo revisa que data/published coincida con su manifiesto (HU-123)

Por ahora publica `municipalities` (DIVIPOLA del DANE, HU-044, con la altura de su celda de NASA POWER),
`municipality_boundaries` (MGN del DANE, HU-044), el catálogo (`crops` y `crop_stages`, HU-061), `rotation_rules` (las
reglas de rotación de `catalog/rotation_rules.yaml`, HU-062), `climate_day` (NASA
POWER, HU-041), `market_price_day` y `market_price_season` (SIPSA del DANE, HU-221), `market_price_latest` (el último
precio de cada producto, HU-221), `market_month` (SIPSA por cultivo, HU-051), `sources` y `manifest.json`. Cada tabla
pasa por las validaciones y por su esquema del contrato (`pipeline/schema.py`, HU-011) antes de escribirse: si una
falla, no se publica nada (R7, R8).
También se valida el mapeo de los productos de SIPSA a los cultivos (`sipsa_crops.yaml`, HU-003) contra los precios que
se publican. Al terminar, lo publicado se revisa contra su manifiesto (HU-123).

Si falta la caché de NASA POWER o la de SIPSA, se publica lo demás sin esas tablas y el log lo dice (`source_missing`):
no hace falta bajar el clima ni los precios para reconstruir los municipios. `climate_day` solo se publica con los
municipios que tienen altitud (NASADEM, HU-206): sin ella la temperatura no se puede corregir y no se publica sin
corregir (R1).

Cada paso deja una línea en la terminal con la fuente, las filas leídas y las descartadas con su motivo (HU-177). Usa la
misma configuración de logs que la API (`common/logging.py`, que no depende del backend): nivel y formato con
`AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT`, sin depender de la base de datos.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl
import shapely
import yaml

from common import signal_sources
from common.logging import configure, get_logger
from pipeline import catalog as crops_catalog
from pipeline import climate_normals, rotation_rules, schema
from pipeline.settings import get_settings
from pipeline.sources import dane, dane_mgn, nasa_power, nasadem, sipsa, sipsa_boletin

REGION_FILE = Path(__file__).with_name("region.yaml")
CROPS_FILE = Path(__file__).with_name("sipsa_crops.yaml")
PUBLISHED = Path("data/published")

log = get_logger("agrosense.pipeline")

# Como pide el catálogo de cultivos (HU-061): `snake_case`, sin tildes.
CROP_ID = re.compile(r"^[a-z][a-z0-9_]*$")
CROP_FIELDS = {"product_id", "notes", "reason"}


class ValidationError(ValueError):
    """Lo publicado no cumple el contrato. El mensaje dice qué falla."""


def load_region(path: Path = REGION_FILE) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_crops(path: Path = CROPS_FILE) -> dict[str, Any]:
    """Qué producto de SIPSA da el precio de cada cultivo (HU-003): `crop_id` → `product_id`, `notes` y `reason`."""
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("crops")


def validate(municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """R7: una sola llave territorial, de 5 dígitos y sin repetir. R8: toda fila apunta a una fuente que existe."""
    if municipalities.is_empty():
        raise ValidationError("`municipalities` quedó vacía: revise los departamentos de region.yaml.")
    bad = municipalities.filter(~pl.col("municipality_id").str.contains(r"^\d{5}$"))
    if not bad.is_empty():
        raise ValidationError(f"`municipality_id` que no son DIVIPOLA de 5 dígitos: {bad['municipality_id'].to_list()[:5]}")
    repeated = municipalities.filter(pl.col("municipality_id").is_duplicated())
    if not repeated.is_empty():
        raise ValidationError(f"`municipality_id` repetidos: {sorted(set(repeated['municipality_id'].to_list()))[:5]}")
    unnamed = municipalities.filter(pl.col("name").is_null() | (pl.col("name").str.strip_chars() == ""))
    if not unnamed.is_empty():
        raise ValidationError(f"Municipios sin nombre: {unnamed['municipality_id'].to_list()[:5]}")
    outside = municipalities.filter(~pl.col("lat").is_between(-90, 90) | ~pl.col("lon").is_between(-180, 180))
    if not outside.is_empty():
        raise ValidationError(f"Coordenadas fuera de rango: {outside['municipality_id'].to_list()[:5]}")
    known = set(sources["source_id"].to_list())
    cited = {source_id for ids in municipalities["source_ids"].to_list() for source_id in ids}
    if not cited or cited - known:
        raise ValidationError(f"Filas sin fuente o con una fuente que no está en `sources`: {sorted(cited - known) or 'sin source_ids'}")


def validate_boundaries(boundaries: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """Cada municipio publicado tiene un solo límite, válido, de área mayor que cero, y con una fuente que existe (R7, R8)."""
    ids, wanted = boundaries["municipality_id"].to_list(), set(municipalities["municipality_id"].to_list())
    if len(ids) != len(set(ids)):
        raise ValidationError("`municipality_boundaries` tiene municipios repetidos.")
    missing, extra = sorted(wanted - set(ids)), sorted(set(ids) - wanted)
    if missing or extra:
        raise ValidationError(f"Límites que no cuadran con `municipalities`: faltan {missing[:5]}, sobran {extra[:5]}")
    for municipality_id, wkb in boundaries.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        if geometry.geom_type not in ("Polygon", "MultiPolygon") or not geometry.is_valid or geometry.area <= 0:
            raise ValidationError(f"El límite de {municipality_id} no es un polígono válido.")
    unknown = set(boundaries["source_id"].to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"Límites con una fuente que no está en `sources`: {sorted(unknown)}")


def validate_market(prices: pl.DataFrame, sources: pl.DataFrame) -> None:
    """Las reglas de los precios (`sipsa.validate`), con las fuentes de lo que se publica (R1, R8)."""
    try:
        sipsa.validate(prices, set(sources["source_id"].to_list()))
    except sipsa.PricesError as error:
        raise ValidationError(str(error)) from error


def validate_crops(crops: Any, prices: pl.DataFrame, catalog_ids: set[str] | None = None) -> None:
    """El mapeo de `sipsa_crops.yaml` (HU-003): cada cultivo tiene un producto que SIPSA publica en la región, o ninguno y
    el porqué (R1). Un producto no da el precio de dos cultivos: dos productos tampoco se promedian (decisión 11).

    Con `catalog_ids` (los `crop_id` de `catalog/crops.yaml`), cada cultivo del mapeo tiene que estar en el catálogo: los
    identificadores salen de un solo lugar y un `crop_id` mal escrito no se publica."""
    if not isinstance(crops, dict) or not crops:
        raise ValidationError("`sipsa_crops.yaml` no trae cultivos en `crops`.")
    if catalog_ids is not None:
        unknown = sorted(set(crops) - catalog_ids)
        if unknown:
            raise ValidationError(f"Cultivos de `sipsa_crops.yaml` que no están en `catalog/crops.yaml`: {unknown}.")
    published = set(prices["product_id"].unique().to_list())
    owners: dict[str, str] = {}
    for crop_id, entry in crops.items():
        if not isinstance(crop_id, str) or not CROP_ID.match(crop_id):
            raise ValidationError(f"`crop_id` inválido en `sipsa_crops.yaml`: {crop_id!r}. Va en snake_case y sin tildes.")
        if not isinstance(entry, dict) or "product_id" not in entry:
            raise ValidationError(f"{crop_id}: falta `product_id` en `sipsa_crops.yaml` (nulo si SIPSA no tiene el cultivo).")
        unknown = set(entry) - CROP_FIELDS
        if unknown:
            raise ValidationError(f"{crop_id}: campos que no se conocen en `sipsa_crops.yaml`: {sorted(unknown)}.")
        product = entry["product_id"]
        if product is None:
            if not str(entry.get("reason") or "").strip():
                raise ValidationError(f"{crop_id}: sin producto de SIPSA hay que decir por qué en `reason` (R1).")
            continue
        if not isinstance(product, str) or product not in published:
            raise ValidationError(f"{crop_id}: el producto {product!r} no está en los precios de SIPSA que se publican.")
        if product in owners:
            raise ValidationError(f"El producto {product!r} da el precio de dos cultivos: {owners[product]} y {crop_id}.")
        owners[product] = crop_id


def validate_market_month(month: pl.DataFrame, crops: dict[str, Any], sources: pl.DataFrame) -> None:
    """`market_month` (HU-051): llave sin repetir, meses de 1 a 12, índice y precio presentes y positivos, el producto que
    dice el mapeo y una fuente que existe (R1, R8). Vacía es válida: sin años completos no hay índice que publicar."""
    repeated = month.filter(pl.struct("crop_id", "market_id", "month").is_duplicated())
    if not repeated.is_empty():
        raise ValidationError(f"`market_month` repite cultivo, central y mes: {repeated.head(3).to_dicts()}")
    bad = month.filter(
        ~pl.col("month").is_between(1, 12)
        | pl.col("seasonal_index").is_null()
        | (pl.col("seasonal_index") <= 0)
        | pl.col("price_cop_kg").is_null()
        | (pl.col("price_cop_kg") <= 0)
        | ~pl.col("quality").is_in(["ok", "partial"])
    )
    if not bad.is_empty():
        raise ValidationError(f"`market_month` con mes, índice, precio o calidad fuera de lo permitido: {bad.head(3).to_dicts()}")
    expected = {crop_id: entry.get("product_id") for crop_id, entry in crops.items()}
    wrong = [row for row in month.select("crop_id", "product_id").unique().iter_rows() if expected.get(row[0]) != row[1]]
    if wrong:
        raise ValidationError(f"`market_month` con un producto que no es el de `sipsa_crops.yaml`: {sorted(wrong)[:3]}")
    unknown = set(month["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`market_month` con una fuente que no está en `sources`: {sorted(unknown)}")


def validate_climate(climate: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`climate_day` solo trae municipios publicados (R7) y cita fuentes que existen (R8)."""
    extra = set(climate["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`climate_day` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    unknown = set(climate["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`climate_day` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_climate_month(month: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`climate_month` solo trae municipios publicados (R7), meses de 1 a 12, lluvia no negativa y fuentes que existen
    (R8)."""
    extra = set(month["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`climate_month` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = month.filter(~pl.col("month").is_between(1, 12) | (pl.col("precip_mm") < 0) | (pl.col("precip_normal_mm") < 0))
    if not bad.is_empty():
        raise ValidationError(f"`climate_month` con un mes o una lluvia fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(month["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`climate_month` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_grid(grid: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`grid_cells` solo trae celdas de municipios publicados (R7) y cita fuentes que existen (R8)."""
    extra = set(grid["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`grid_cells` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    unknown = set(grid["source_ids"].explode().drop_nulls().unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`grid_cells` cita una fuente que no está en `sources`: {sorted(unknown)}")


def publish(
    region: dict[str, Any],
    municipalities: pl.DataFrame,
    sources: pl.DataFrame,
    folder: Path = PUBLISHED,
    boundaries: pl.DataFrame | None = None,
    crops: tuple[str, pl.DataFrame, pl.DataFrame] | None = None,
    prices: pl.DataFrame | None = None,
    crop_products: dict[str, Any] | None = None,
    climate: pl.DataFrame | None = None,
    grid: pl.DataFrame | None = None,
    climate_month: pl.DataFrame | None = None,
    rules: pl.DataFrame | None = None,
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto. Las tablas salen ordenadas por su llave: mismos datos, mismos archivos (R4).

    `crops` es el catálogo agronómico (versión, `crops` y `crop_stages`). Con `crop_products` (el mapeo de
    `sipsa_crops.yaml`), lo valida contra los precios y publica además `market_month` (HU-051). `climate`
    (`climate_day`), `climate_month` (HU-042) y `grid` (`grid_cells`, HU-206) solo se escriben si traen filas: una tabla vacía no es un dato
    (R1). Todo se valida antes de escribir nada.
    """
    validate(municipalities, sources)
    if boundaries is not None:
        validate_boundaries(boundaries, municipalities, sources)
    season = month = latest = None
    if prices is not None:
        validate_market(prices, sources)
        season = sipsa.seasonal(prices)
        # El último precio de cada producto, con el de hace una semana y el cambio: la API solo lo filtra (HU-221).
        latest = sipsa.latest(prices)
    if crop_products is not None:
        if prices is None:
            raise ValidationError("El mapeo de `sipsa_crops.yaml` se valida contra los precios de SIPSA, y no hay precios.")
        validate_crops(crop_products, prices, set(crops[1]["crop_id"].to_list()) if crops is not None else None)
        month = sipsa.monthly(prices, season, crop_products)
        validate_market_month(month, crop_products, sources)
    has_climate = climate is not None and not climate.is_empty()
    if has_climate:
        validate_climate(climate, municipalities, sources)
    has_month = climate_month is not None and not climate_month.is_empty()
    if has_month:
        validate_climate_month(climate_month, municipalities, sources)
    has_grid = grid is not None and not grid.is_empty()
    if has_grid:
        validate_grid(grid, municipalities, sources)
    # HU-011: cada tabla tiene exactamente la forma del contrato (columnas, tipos, llave y `quality`) antes de escribir.
    # `sources` junta filas de varias fuentes: va con las columnas del contrato, en su orden. Una fuente sin cita (por
    # ejemplo, las del catálogo) queda con `citation` nula, no inventada (R1).
    source_columns = list(schema.TABLES["sources"].columns)
    sources = sources.with_columns(pl.lit(None, dtype=pl.String).alias(col) for col in source_columns if col not in sources.columns)
    tables = {"municipalities": municipalities, "sources": sources.select(source_columns).sort("source_id")}
    if boundaries is not None:
        tables["municipality_boundaries"] = boundaries
    if crops is not None:
        tables["crops"], tables["crop_stages"] = crops[1], crops[2]
    if rules is not None:
        tables["rotation_rules"] = rules
    if has_climate:
        tables["climate_day"] = climate
    if has_month:
        tables["climate_month"] = climate_month
    if has_grid:
        tables["grid_cells"] = grid
    if prices is not None:
        tables |= {"market_price_day": prices, "market_price_latest": latest, "market_price_season": season}
    if month is not None:
        tables["market_month"] = month
    for name, table in tables.items():
        tables[name] = schema.typed(name, table)
        try:
            schema.check(name, tables[name])
        except schema.SchemaError as error:
            raise ValidationError(str(error)) from error
    folder.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.write_parquet(folder / f"{name}.parquet")
        log.info("table_written", table=name, rows=table.height, detail=f"{name}: {table.height} filas escritas en {folder}")
    manifest = {
        "dataset_version": region["dataset_version"],
        # La versión del catálogo agronómico (fichas y, cuando existan, reglas de rotación). Sin catálogo, nula.
        "rules_version": crops[0] if crops is not None else None,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "region": region["region"],
        # Los periodos de «Qué cambió» llegan con HU-216.
        "periods": [],
        "tables": {
            "municipalities": {"rows": municipalities.height, "coverage": region["region"]["name"]},
            "sources": {"rows": sources.height, "coverage": "todas las fuentes de lo publicado"},
        },
    }
    if boundaries is not None:
        manifest["tables"]["municipality_boundaries"] = {"rows": boundaries.height, "coverage": region["region"]["name"]}
    if crops is not None:
        manifest["tables"]["crops"] = {"rows": crops[1].height, "coverage": "cultivos del MVP"}
        manifest["tables"]["crop_stages"] = {"rows": crops[2].height, "coverage": "cultivos del MVP"}
    if rules is not None:
        manifest["tables"]["rotation_rules"] = {"rows": rules.height, "coverage": "reglas de rotación de los cultivos del MVP"}
    if has_climate:
        days = f"del {climate['date'].min()} al {climate['date'].max()}"
        coverage = f"{climate['municipality_id'].n_unique()} municipios con altitud, {days}"
        manifest["tables"]["climate_day"] = {"rows": climate.height, "coverage": coverage}
    if has_month:
        normal = climate_normals.Normal.from_region(region)
        years = f"de {climate_month['year'].min()} a {climate_month['year'].max()}"
        period = f"; normal {normal.first_year}-{normal.last_year}" if normal is not None else ""
        coverage = f"{climate_month['municipality_id'].n_unique()} municipios, meses completos {years}{period}"
        manifest["tables"]["climate_month"] = {"rows": climate_month.height, "coverage": coverage}
    if has_grid:
        coverage = f"Celdas de 0,0025° de {grid['municipality_id'].n_unique()} municipios; sin suelo hasta HU-181"
        manifest["tables"]["grid_cells"] = {"rows": grid.height, "coverage": coverage}
    if prices is not None:
        manifest["tables"]["market_price_day"] = {
            "rows": prices.height,
            "coverage": f"{' · '.join(sorted(set(prices['market'].to_list())))}; del {prices['date'].min()} al {prices['date'].max()}",
        }
        manifest["tables"]["market_price_latest"] = {
            "rows": latest.height,
            "coverage": "El último precio de cada producto en cada central, con el de hace una semana y el cambio",
        }
        manifest["tables"]["market_price_season"] = {
            "rows": season.height,
            "coverage": f"Productos con al menos {sipsa.MIN_YEARS} años completos de precios",
        }
    if month is not None:
        crops_with_rows = ", ".join(sorted(set(month["crop_id"].to_list()))) or "ningún cultivo"
        manifest["tables"]["market_month"] = {
            "rows": month.height,
            "coverage": f"{crops_with_rows}: índice estacional y precio de cada mes del último año completo, por central",
        }
    # Siempre con LF: en Windows `write_text` escribe CRLF, y el archivo cambiaría según quién publica (R4).
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (folder / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
    return manifest


def verify(folder: Path = PUBLISHED, dataset_version: str | None = None) -> dict[str, Any]:
    """HU-123: lo publicado en `folder` coincide con su manifiesto. Cada tabla que nombra existe y tiene las filas que dice,
    no hay tablas que no nombre y, con `dataset_version`, la versión es esa (la de `region.yaml`). Devuelve el manifiesto.

    Así se sabe que una carpeta copiada o reconstruida es la de la demo, y no una a medias o mezclada con otra (R4).
    """
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise ValidationError(f"No hay `manifest.json` en {folder}: publique con `uv run python -m pipeline.build`.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = manifest.get("tables") or {}
    problems = []
    if dataset_version is not None and manifest.get("dataset_version") != dataset_version:
        problems.append(f"el manifiesto es de la versión {manifest.get('dataset_version')} y `region.yaml` dice {dataset_version}")
    for name, info in listed.items():
        path = folder / f"{name}.parquet"
        if not path.exists():
            problems.append(f"falta `{name}.parquet`")
            continue
        rows = pl.scan_parquet(path).select(pl.len()).collect().item()
        if rows != info.get("rows"):
            problems.append(f"`{name}` tiene {rows} filas y el manifiesto dice {info.get('rows')}")
    extra = sorted(path.name for path in folder.glob("*.parquet") if path.stem not in listed)
    if extra:
        problems.append(f"tablas que el manifiesto no nombra: {extra}")
    if problems:
        raise ValidationError(f"Lo publicado en {folder} no coincide con su manifiesto: {'; '.join(problems)}.")
    return manifest


def terrain_from_cache(
    municipalities: pl.DataFrame, boundaries: pl.DataFrame, cache: Path
) -> tuple[pl.DataFrame, pl.DataFrame | None, list[dict[str, Any]]]:
    """La altitud y la pendiente de NASADEM (HU-206): los municipios con las suyas, `grid_cells` y su fuente.

    Sin la caché de NASADEM devuelve los municipios como estaban, sin rejilla y sin fuente nueva: lo demás se publica, y
    el clima diario no, porque sin altitud no se corrige (R1).
    """
    try:
        cells, meta = nasadem.read_cache(boundaries, cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=nasadem.SOURCE_ID, detail=f"Se publica sin la altitud de NASADEM: {error}")
        return municipalities, None, []
    terrain = nasadem.municipality_terrain(cells, municipalities)
    municipalities = nasadem.with_terrain(municipalities, terrain)
    empty = cells.filter(pl.col("altitude_m").is_null()).height
    log.info(
        "source_read",
        source=nasadem.SOURCE_ID,
        rows_read=cells.height,
        rows_kept=cells.height - empty,
        rows_rejected=empty,
        reasons={"no_valid_pixels": empty},
        detail=f"NASADEM: {cells.height} celdas de 250 m en {terrain.height} municipios; {empty} sin ningún píxel válido "
        "quedan con la altitud nula (R1)",
    )
    return municipalities, nasadem.grid_cells(cells), [nasadem.source(meta)]


def climate_from_cache(
    region: dict[str, Any], municipalities: pl.DataFrame, cache: Path
) -> tuple[pl.DataFrame, pl.DataFrame | None, pl.DataFrame | None, list[dict[str, Any]]]:
    """El clima de NASA POWER (HU-041, HU-042): los municipios con la altura de su celda, `climate_day`,
    `climate_month` y sus fuentes.

    Sin la caché de POWER devuelve los municipios como estaban, sin clima y sin fuentes nuevas: lo demás se publica igual.
    """
    try:
        series, meta = nasa_power.read_cache(nasa_power.cells(municipalities), cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=nasa_power.SOURCE_ID, detail=f"Se publica sin el clima de NASA POWER: {error}")
        return municipalities, None, None, []
    municipalities = nasa_power.with_cell_elevation(municipalities, meta["elevations"])
    lapse = region.get("temperature_lapse_rate")
    climate = nasa_power.climate_day(series, municipalities, lapse)
    # La lluvia no se corrige por altitud: sale para todos los municipios con coordenadas. La ET0 sí necesita la altitud.
    normal = climate_normals.Normal.from_region(region)
    if normal is None:
        log.warning("climate_normal_missing", table="climate_month", detail="region.yaml no trae climate_normal: no hay climate_month")
        month = None
    else:
        month = nasa_power.climate_month(series, municipalities, date.fromisoformat(meta["requested_end"]), normal, climate)
    sources = [nasa_power.source(series, meta)]
    if lapse is not None:
        sources.append(lapse["source"])
    without = municipalities.filter(pl.col("altitude_m").is_null()).height
    if without:
        log.warning(
            "climate_not_corrected",
            table="climate_day",
            municipalities=without,
            detail=f"{without} municipios sin altitud de NASADEM (HU-206): no tienen filas en climate_day",
        )
    if lapse is None:
        log.warning("climate_not_corrected", table="climate_day", detail="region.yaml no trae temperature_lapse_rate")
    return municipalities, climate, month, sources


def build(
    download: bool = False,
    folder: Path = PUBLISHED,
    cache: Path = dane.CACHE,
    market_cache: Path | None = None,
    power_cache: Path | None = None,
    dem_cache: Path | None = None,
) -> dict[str, Any]:
    # Las cachés de SIPSA, NASA POWER y NASADEM se buscan al correr, no al importar: así las pruebas las apuntan a una
    # carpeta vacía y nunca leen las de quien las corre.
    market_cache = market_cache or sipsa.CACHE
    power_cache = power_cache or nasa_power.CACHE
    dem_cache = dem_cache or nasadem.CACHE
    region = load_region()
    version, name = region["dataset_version"], region["region"]["name"]
    departments = region["region"]["departments"]
    log.info("pipeline_started", dataset_version=version, detail=f"Reconstruyendo el dataset {version} de {name}")
    if download:
        log.info("source_downloading", source=dane.SOURCE_ID, detail=f"Bajando DIVIPOLA del DANE a {cache}")
        dane.download(cache)
        log.info("source_downloading", source=dane_mgn.SOURCE_ID, detail=f"Bajando los límites municipales del DANE a {cache}")
        dane_mgn.download(departments, cache)
        log.info("source_downloading", source=sipsa.SOURCE_ID, detail=f"Bajando SIPSA del DANE a {market_cache} (unos 300 MB)")
        sipsa.download(market_cache)
    rows, meta = dane.read_cache(cache)
    municipalities = dane.municipalities(rows, departments)
    outside = len(rows) - municipalities.height
    log.info(
        "source_read",
        source=dane.SOURCE_ID,
        rows_read=len(rows),
        rows_kept=municipalities.height,
        rows_rejected=outside,
        reasons={"outside_region": outside},
        detail=f"DIVIPOLA: {len(rows)} filas leídas, {municipalities.height} de la región y {outside} descartadas por ser de "
        "otros departamentos",
    )
    features, mgn_meta = dane_mgn.read_cache(departments, cache)
    boundaries = dane_mgn.boundaries(features)
    if download:
        nasadem.download(nasadem.tiles(boundaries), dem_cache)
        nasa_power.download(nasa_power.cells(municipalities), power_cache)
    # Primero la altitud: el clima se corrige con ella (HU-044).
    municipalities, grid, terrain_sources = terrain_from_cache(municipalities, boundaries, dem_cache)
    municipalities, climate, climate_month, climate_sources = climate_from_cache(region, municipalities, power_cache)
    # La temperatura media anual (HU-044), con el periodo normal de `region.yaml`: la usa el filtro de aptitud.
    normal = climate_normals.Normal.from_region(region)
    if climate is not None and not climate.is_empty():
        if normal is None:
            log.warning("climate_normal_missing", detail="region.yaml no trae climate_normal: tmean_annual_c queda nula")
        else:
            tmean = climate_normals.tmean_annual(climate, normal)
            municipalities = climate_normals.with_tmean(municipalities, tmean)
            missing = municipalities.filter(pl.col("tmean_annual_c").is_null()).height
            log.info(
                "tmean_annual_computed",
                municipalities=municipalities.height - missing,
                detail=f"Temperatura media anual de {normal.first_year}-{normal.last_year}: {municipalities.height - missing} "
                f"municipios; {missing} sin años suficientes quedan nulos (R1)",
            )
    catalog = crops_catalog.load()
    crops_table, stages_table, catalog_sources = crops_catalog.build(catalog)
    # Las reglas citan las fuentes de las fichas y las suyas, y usan las familias de las fichas (HU-062).
    rules_table, rules_sources = rotation_rules.build(
        rotation_rules.load(),
        crop_sources=catalog.get("sources") or [],
        known_families=set(crops_table["family"].drop_nulls().to_list()),
        expected_version=catalog["version"],
    )
    own = [dane.source(meta), dane_mgn.source(mgn_meta)]
    prices = crop_products = None
    counts: Counter[str] = Counter()
    try:
        prices, downloaded_at = sipsa.read_cache(region["region"]["markets"], market_cache, counts)
    except FileNotFoundError as error:
        # Sin la caché de SIPSA (unos 300 MB) se publica lo demás, sin las tablas de precios: no se inventan (R1), y el
        # manifiesto dice qué trae. Así reconstruir los municipios no obliga a bajar los precios.
        log.warning("source_missing", source=sipsa.SOURCE_ID, detail=f"Se publica sin los precios de SIPSA: {error}")
    else:
        rejected = counts["other_market"] + counts["no_average"]
        log.info(
            "source_read",
            source=sipsa.SOURCE_ID,
            rows_read=counts["read"],
            rows_kept=prices.height,
            rows_rejected=rejected,
            reasons={"other_market": counts["other_market"], "no_average": counts["no_average"]},
            detail=f"SIPSA: {counts['read']} filas leídas, {prices.height} de las centrales de la región y {rejected} "
            f"descartadas: {counts['other_market']} de otras centrales y {counts['no_average']} sin precio medio ese día (R1)",
        )
        own.append(sipsa.source(prices, downloaded_at))
        crop_products = load_crops()
    sources = pl.concat([pl.DataFrame([*own, *terrain_sources, *climate_sources]), catalog_sources, rules_sources], how="diagonal_relaxed")
    check_signal_sources(region["region"]["id"], set(sources["source_id"].to_list()))
    crops = (catalog["version"], crops_table, stages_table)
    return publish(
        region, municipalities, sources, folder, boundaries, crops, prices, crop_products, climate, grid, climate_month, rules_table
    )


SIGNAL_SOURCES_FILE = signal_sources.SIGNAL_SOURCES_FILE
# Las fuentes que tienen adaptador en el pipeline: si una no se publica, es porque falta su caché, no un error.
ADAPTERS = frozenset(module.SOURCE_ID for module in (dane, dane_mgn, sipsa, sipsa_boletin, nasa_power, nasadem))


def check_signal_sources(region_id: str, published: set[str]) -> None:
    """`catalog/sources.yaml` contra lo que se va a publicar (HU-122, R8): una fuente que no está en `sources`, ni tiene
    adaptador, ni está en `planned` hace fallar el pipeline. Una con adaptador que esta vez no se publica (falta su caché)
    solo se dice en el log: su señal será `insufficient_data` (R1)."""
    try:
        config = signal_sources.load_signal_sources(SIGNAL_SOURCES_FILE)
        missing = signal_sources.check_sources(config, region_id, published, set(ADAPTERS))
    except signal_sources.SignalSourcesError as error:
        raise ValidationError(str(error)) from error
    for source in missing:
        log.warning("signal_source_missing", source=source, detail=f"catalog/sources.yaml usa {source}, que no se publica esta vez")
    planned = sorted(config.planned)
    log.info(
        "signal_sources_checked",
        version=config.version,
        planned=planned,
        detail=f"catalog/sources.yaml {config.version}: fuentes por llegar {', '.join(planned) or 'ninguna'}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye data/published desde la caché.")
    parser.add_argument("--descargar", action="store_true", help="Baja otra vez las fuentes a data/raw/ antes de publicar.")
    parser.add_argument("--verificar", action="store_true", help="No publica: solo revisa que data/published coincida con su manifiesto.")
    args = parser.parse_args()
    # El pipeline no usa la base de datos: lee su configuración de `pipeline/settings.py`, no la de la API.
    settings = get_settings()
    configure(settings.log_level, settings.log_format)
    expected = load_region()["dataset_version"]
    try:
        if not args.verificar:
            build(download=args.descargar)
        manifest = verify(PUBLISHED, expected)
    except (
        FileNotFoundError,
        ValidationError,
        crops_catalog.CatalogError,
        rotation_rules.RotationRulesError,
        nasa_power.DownloadError,
        nasadem.TileError,
    ) as error:
        event = "dataset_mismatch" if args.verificar else "dataset_not_published"
        log.error(event, detail=f"{'Lo publicado no pasó la revisión' if args.verificar else 'No se publicó nada'}: {error}")
        sys.exit(1)
    tables = ", ".join(f"{name} ({info['rows']} filas)" for name, info in manifest["tables"].items())
    verb = "revisado: coincide con su manifiesto" if args.verificar else "publicado y revisado contra su manifiesto"
    log.info(
        "dataset_verified" if args.verificar else "dataset_published",
        dataset_version=manifest["dataset_version"],
        tables=len(manifest["tables"]),
        detail=f"Dataset {manifest['dataset_version']} {verb} en {PUBLISHED}: {tables}",
    )


if __name__ == "__main__":
    main()
