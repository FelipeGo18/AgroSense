"""Reconstruye `data/published/` desde la caché (specs/02-contratos.md, «Tablas publicadas»).

    uv run python -m pipeline.build              # lee la caché de data/raw/ y publica
    uv run python -m pipeline.build --descargar  # antes, baja otra vez las fuentes a la caché
    uv run python -m pipeline.build --verificar  # solo revisa que data/published coincida con su manifiesto (HU-123)

Por ahora publica `municipalities` (DIVIPOLA del DANE, HU-044), `market_price_day` y `market_price_season` (SIPSA del
DANE, HU-221), `market_month` (SIPSA por cultivo, HU-051), `sources` y `manifest.json`. Cada tabla pasa por las
validaciones antes de escribirse: si una falla, no se publica nada (R7, R8). También se valida el mapeo de los
productos de SIPSA a los cultivos (`sipsa_crops.yaml`, HU-003) contra los precios que se publican. Al terminar, lo
publicado se revisa contra su manifiesto (HU-123).

Cada paso deja una línea en la terminal con la fuente, las filas leídas y las descartadas con su motivo (HU-177). Usa la
misma configuración de logs que la API (`backend/config/logging.py`): nivel y formato con `AGROSENSE_LOG_LEVEL` y
`AGROSENSE_LOG_FORMAT`, sin depender de la base de datos.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from backend.config.logging import configure, get_logger
from pipeline.sources import dane, sipsa

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


def validate_market(prices: pl.DataFrame, sources: pl.DataFrame) -> None:
    """La llave (producto, central, día) no se repite; hay precio medio, y el mínimo y el máximo, si están, lo encierran
    (R1, R8). Se tolera un peso: el DANE redondea el medio («1563» con mínimo y máximo de 1562,5)."""
    if prices.is_empty():
        raise ValidationError("`market_price_day` quedó vacía: revise las centrales de region.yaml.")
    repeated = prices.filter(pl.struct("product_id", "market_id", "date").is_duplicated())
    if not repeated.is_empty():
        raise ValidationError(f"Precios repetidos para un mismo producto, central y día: {repeated.head(3).to_dicts()}")
    bad = prices.filter(
        pl.col("avg_cop_kg").is_null()
        | (pl.col("avg_cop_kg") <= 0)
        | (pl.col("min_cop_kg") > pl.col("avg_cop_kg") + 1).fill_null(False)
        | (pl.col("avg_cop_kg") > pl.col("max_cop_kg") + 1).fill_null(False)
    )
    if not bad.is_empty():
        raise ValidationError(f"Precios sin promedio o con el medio fuera del mínimo y el máximo: {bad.head(3).to_dicts()}")
    unknown = set(prices["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"Precios con una fuente que no está en `sources`: {sorted(unknown)}")


def validate_crops(crops: Any, prices: pl.DataFrame) -> None:
    """El mapeo de `sipsa_crops.yaml` (HU-003): cada cultivo tiene un producto que SIPSA publica en la región, o ninguno y
    el porqué (R1). Un producto no da el precio de dos cultivos: dos productos tampoco se promedian (decisión 11)."""
    if not isinstance(crops, dict) or not crops:
        raise ValidationError("`sipsa_crops.yaml` no trae cultivos en `crops`.")
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


def publish(
    region: dict[str, Any],
    municipalities: pl.DataFrame,
    sources: pl.DataFrame,
    folder: Path = PUBLISHED,
    prices: pl.DataFrame | None = None,
    crops: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto. Las tablas salen ordenadas por su llave: mismos datos, mismos archivos (R4).

    Con `crops` (el mapeo de `sipsa_crops.yaml`), lo valida contra los precios y publica además `market_month` (HU-051).
    Todo se valida antes de escribir nada.
    """
    validate(municipalities, sources)
    season = month = None
    if prices is not None:
        validate_market(prices, sources)
        season = sipsa.seasonal(prices)
    if crops is not None:
        if prices is None:
            raise ValidationError("El mapeo de `sipsa_crops.yaml` se valida contra los precios de SIPSA, y no hay precios.")
        validate_crops(crops, prices)
        month = sipsa.monthly(prices, season, crops)
        validate_market_month(month, crops, sources)
    folder.mkdir(parents=True, exist_ok=True)
    tables = {"municipalities": municipalities, "sources": sources.sort("source_id")}
    if prices is not None:
        tables |= {"market_price_day": prices, "market_price_season": season}
    if month is not None:
        tables["market_month"] = month
    for name, table in tables.items():
        table.write_parquet(folder / f"{name}.parquet")
        log.info("table_written", table=name, rows=table.height, detail=f"{name}: {table.height} filas escritas en {folder}")
    manifest = {
        "dataset_version": region["dataset_version"],
        # Las reglas agronómicas (catálogo) todavía no existen: no hay versión que decir.
        "rules_version": None,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "region": region["region"],
        # Los periodos de «Qué cambió» llegan con HU-216.
        "periods": [],
        "tables": {
            "municipalities": {"rows": municipalities.height, "coverage": region["region"]["name"]},
            "sources": {"rows": sources.height, "coverage": "todas las fuentes de lo publicado"},
        },
    }
    if prices is not None:
        manifest["tables"]["market_price_day"] = {
            "rows": prices.height,
            "coverage": f"{' · '.join(sorted(set(prices['market'].to_list())))}; del {prices['date'].min()} al {prices['date'].max()}",
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
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def build(download: bool = False, folder: Path = PUBLISHED, cache: Path = dane.CACHE, market_cache: Path = sipsa.CACHE) -> dict[str, Any]:
    region = load_region()
    version, name = region["dataset_version"], region["region"]["name"]
    log.info("pipeline_started", dataset_version=version, detail=f"Reconstruyendo el dataset {version} de {name}")
    if download:
        log.info("source_downloading", source=dane.SOURCE_ID, detail=f"Bajando DIVIPOLA del DANE a {cache}")
        dane.download(cache)
        log.info("source_downloading", source=sipsa.SOURCE_ID, detail=f"Bajando SIPSA del DANE a {market_cache} (unos 300 MB)")
        sipsa.download(market_cache)
    rows, meta = dane.read_cache(cache)
    municipalities = dane.municipalities(rows, region["region"]["departments"])
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
    counts: Counter[str] = Counter()
    prices, downloaded_at = sipsa.read_cache(region["region"]["markets"], market_cache, counts)
    rejected = counts["other_market"] + counts["no_average"]
    log.info(
        "source_read",
        source=sipsa.SOURCE_ID,
        rows_read=counts["read"],
        rows_kept=prices.height,
        rows_rejected=rejected,
        reasons={"other_market": counts["other_market"], "no_average": counts["no_average"]},
        detail=f"SIPSA: {counts['read']} filas leídas, {prices.height} de las centrales de la región y {rejected} descartadas: "
        f"{counts['other_market']} de otras centrales y {counts['no_average']} sin precio medio ese día (R1)",
    )
    sources = pl.DataFrame([dane.source(meta), sipsa.source(prices, downloaded_at)])
    return publish(region, municipalities, sources, folder, prices, load_crops())


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye data/published desde la caché.")
    parser.add_argument("--descargar", action="store_true", help="Baja otra vez las fuentes a data/raw/ antes de publicar.")
    parser.add_argument("--verificar", action="store_true", help="No publica: solo revisa que data/published coincida con su manifiesto.")
    args = parser.parse_args()
    # El pipeline no usa la base de datos: lee solo el nivel y el formato de los logs, no toda la configuración de la API.
    configure(os.environ.get("AGROSENSE_LOG_LEVEL", "INFO"), os.environ.get("AGROSENSE_LOG_FORMAT", "console"))
    expected = load_region()["dataset_version"]
    try:
        if not args.verificar:
            build(download=args.descargar)
        manifest = verify(PUBLISHED, expected)
    except (FileNotFoundError, ValidationError) as error:
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
