"""Reconstruye `data/published/` desde la caché (specs/02-contratos.md, «Tablas publicadas»).

    uv run python -m pipeline.build              # lee la caché de data/raw/ y publica
    uv run python -m pipeline.build --descargar  # antes, baja otra vez las fuentes a la caché

Por ahora publica `municipalities` (DIVIPOLA del DANE, HU-044), `market_price_day` y `market_price_season` (SIPSA del
DANE, HU-221), `sources` y `manifest.json`. Cada tabla pasa por las
validaciones antes de escribirse: si una falla, no se publica nada (R7, R8). También se valida el mapeo de los
productos de SIPSA a los cultivos (`sipsa_crops.yaml`, HU-003) contra los precios que se publican.
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from pipeline.sources import dane, sipsa

REGION_FILE = Path(__file__).with_name("region.yaml")
CROPS_FILE = Path(__file__).with_name("sipsa_crops.yaml")
PUBLISHED = Path("data/published")

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


def publish(
    region: dict[str, Any],
    municipalities: pl.DataFrame,
    sources: pl.DataFrame,
    folder: Path = PUBLISHED,
    prices: pl.DataFrame | None = None,
    crops: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto. Las tablas salen ordenadas por su llave: mismos datos, mismos archivos (R4).

    Con `crops` (el mapeo de `sipsa_crops.yaml`), lo valida contra los precios antes de escribir nada.
    """
    validate(municipalities, sources)
    if prices is not None:
        validate_market(prices, sources)
    if crops is not None:
        if prices is None:
            raise ValidationError("El mapeo de `sipsa_crops.yaml` se valida contra los precios de SIPSA, y no hay precios.")
        validate_crops(crops, prices)
    folder.mkdir(parents=True, exist_ok=True)
    municipalities.write_parquet(folder / "municipalities.parquet")
    sources.sort("source_id").write_parquet(folder / "sources.parquet")
    if prices is not None:
        season = sipsa.seasonal(prices)
        prices.write_parquet(folder / "market_price_day.parquet")
        season.write_parquet(folder / "market_price_season.parquet")
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
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build(download: bool = False, folder: Path = PUBLISHED, cache: Path = dane.CACHE, market_cache: Path = sipsa.CACHE) -> dict[str, Any]:
    region = load_region()
    if download:
        dane.download(cache)
        sipsa.download(market_cache)
    rows, meta = dane.read_cache(cache)
    municipalities = dane.municipalities(rows, region["region"]["departments"])
    prices, downloaded_at = sipsa.read_cache(region["region"]["markets"], market_cache)
    sources = pl.DataFrame([dane.source(meta), sipsa.source(prices, downloaded_at)])
    return publish(region, municipalities, sources, folder, prices, load_crops())


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye data/published desde la caché.")
    parser.add_argument("--descargar", action="store_true", help="Baja otra vez las fuentes a data/raw/ antes de publicar.")
    args = parser.parse_args()
    try:
        manifest = build(download=args.descargar)
    except (FileNotFoundError, ValidationError) as error:
        sys.exit(f"No se publicó nada: {error}")
    tables = ", ".join(f"{name} ({info['rows']} filas)" for name, info in manifest["tables"].items())
    print(f"Dataset {manifest['dataset_version']} publicado en {PUBLISHED}: {tables}.")


if __name__ == "__main__":
    main()
