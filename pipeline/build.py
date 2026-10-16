"""Reconstruye `data/published/` desde la caché (specs/02-contratos.md, «Tablas publicadas»).

    uv run python -m pipeline.build              # lee la caché de data/raw/ y publica
    uv run python -m pipeline.build --descargar  # antes, baja otra vez las fuentes a la caché

Por ahora publica `municipalities` (DIVIPOLA del DANE, HU-044), `sources` y `manifest.json`. Cada tabla pasa por las
validaciones antes de escribirse: si una falla, no se publica nada (R7, R8).
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import shapely
import yaml

from pipeline.sources import dane, dane_mgn

REGION_FILE = Path(__file__).with_name("region.yaml")
PUBLISHED = Path("data/published")


class ValidationError(ValueError):
    """Lo publicado no cumple el contrato. El mensaje dice qué falla."""


def load_region(path: Path = REGION_FILE) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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


def publish(
    region: dict[str, Any],
    municipalities: pl.DataFrame,
    sources: pl.DataFrame,
    folder: Path = PUBLISHED,
    boundaries: pl.DataFrame | None = None,
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto. Las tablas salen ordenadas por su llave: mismos datos, mismos archivos (R4)."""
    validate(municipalities, sources)
    if boundaries is not None:
        validate_boundaries(boundaries, municipalities, sources)
    folder.mkdir(parents=True, exist_ok=True)
    municipalities.write_parquet(folder / "municipalities.parquet")
    sources.sort("source_id").write_parquet(folder / "sources.parquet")
    if boundaries is not None:
        boundaries.write_parquet(folder / "municipality_boundaries.parquet")
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
    if boundaries is not None:
        manifest["tables"]["municipality_boundaries"] = {"rows": boundaries.height, "coverage": region["region"]["name"]}
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build(download: bool = False, folder: Path = PUBLISHED, cache: Path = dane.CACHE) -> dict[str, Any]:
    region = load_region()
    departments = region["region"]["departments"]
    if download:
        dane.download(cache)
        dane_mgn.download(departments, cache)
    rows, meta = dane.read_cache(cache)
    municipalities = dane.municipalities(rows, departments)
    features, mgn_meta = dane_mgn.read_cache(departments, cache)
    boundaries = dane_mgn.boundaries(features)
    sources = pl.DataFrame([dane.source(meta), dane_mgn.source(mgn_meta)])
    return publish(region, municipalities, sources, folder, boundaries)


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
