"""Catálogo agronómico: lee `catalog/crops.yaml`, lo valida y arma las tablas `crops` y `crop_stages` (EP-06).

Validaciones (si una falla, no se publica nada):
- R8: todo valor no nulo cita una fuente que está en `sources`; un valor nulo dice por qué (nota).
- Contrato: `crop_id` en `snake_case` sin repetir; `kind` y `archetype` de los valores permitidos; etapas conocidas, con
  días mayores que cero; `kc` entre 0 y 2.
- Decisión 16: `secondary_families` es una lista de textos con fuente (vacía si falta), sin repetidos, sin la `family` de la
  propia ficha y con valores que son la `family` de alguna ficha del catálogo.
- HU-199: cada óptimo cae dentro de su rango absoluto (un límite nulo con fuente es un rango abierto).
"""

import re
from pathlib import Path
from typing import Any

import polars as pl
import yaml

CATALOG_FILE = Path("catalog/crops.yaml")
KINDS = {"crop", "cover", "fallow"}
ARCHETYPES = {
    "tuber", "root", "bulb", "leafy", "cereal", "climbing_legume", "bush_legume", "creeping", "tall_grass",
    "shrub_fruit", "tree_fruit", "cover", "fallow",
}  # fmt: skip
STAGES = ("initial", "development", "mid", "late")
# Los rangos que tienen óptimo y absoluto: (mínimo absoluto, mínimo óptimo, máximo óptimo, máximo absoluto).
RANGES = {
    "tmean": ("tmean_min_c", "tmean_opt_min_c", "tmean_opt_max_c", "tmean_max_c"),
    "temp": ("temp_min_c", "temp_opt_min_c", "temp_opt_max_c", "heat_max_c"),
    "rain": ("rain_min_mm", "rain_opt_min_mm", "rain_opt_max_mm", "rain_max_mm"),
    "ph": ("ph_min", "ph_opt_min", "ph_opt_max", "ph_max"),
}
# Las columnas de `crops` del contrato que salen de un valor con fuente.
FIELDS = (
    "name_es", "kind", "archetype", "family", "water_need", "root_type", "fixes_nitrogen",
    *RANGES["tmean"], "base_temp_c", "temp_min_c", "temp_opt_min_c", "temp_opt_max_c", "heat_max_c",
    *RANGES["rain"], *RANGES["ph"], "frost_killing_c",
)  # fmt: skip
# El orden de las columnas de `crops` es el del contrato: `secondary_families` va tras `family`.
ORDER = ("crop_id", *FIELDS[:4], "secondary_families", *FIELDS[4:], "cycle_months", "source_ids")


class CatalogError(ValueError):
    """El catálogo no cumple el contrato o una regla. El mensaje dice qué hay que corregir."""


def load(path: Path = CATALOG_FILE) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}: sin catálogo no hay fichas de cultivos.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _value(crop_id: str, field: str, entry: Any, known: set[str]) -> Any:
    """El valor de un campo, comprobando que cite una fuente que existe o que diga por qué es nulo (R8)."""
    if entry is None:
        return None
    if not isinstance(entry, dict) or "v" not in entry:
        raise CatalogError(f"{crop_id}.{field}: debe ser {{v: valor, s: fuente}}.")
    value, source = entry["v"], entry.get("s")
    if value is not None and source not in known:
        raise CatalogError(f"{crop_id}.{field}: el valor {value!r} no cita una fuente de `sources` (R8).")
    if value is None and not (entry.get("n") or source):
        raise CatalogError(f"{crop_id}.{field}: está nulo y no dice por qué.")
    return value


def _secondary_families(crop_id: str, crop: dict[str, Any], known: set[str]) -> tuple[list[str], str | None]:
    """Las otras familias de una ficha que mezcla especies, con su fuente. Ausente o vacía: lista vacía (R1, R8)."""
    entry = crop.get("secondary_families")
    value = _value(crop_id, "secondary_families", entry, known)
    if value is None or value == []:
        return [], None
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise CatalogError(f"{crop_id}.secondary_families: debe ser una lista de textos no vacíos.")
    if len(set(value)) != len(value):
        raise CatalogError(f"{crop_id}.secondary_families: hay familias repetidas: {value}.")
    # Ordenada: la publicación no depende del orden del YAML (R4).
    return sorted(value), entry["s"]


def _check_ranges(crop_id: str, row: dict[str, Any]) -> None:
    for name, (low, opt_low, opt_high, high) in RANGES.items():
        values = [row.get(k) for k in (low, opt_low, opt_high, high)]
        a, b, c, d = values
        if b is not None and c is not None and b > c:
            raise CatalogError(f"{crop_id}: en `{name}` el óptimo mínimo ({b}) es mayor que el máximo ({c}).")
        if a is not None and b is not None and b < a:
            raise CatalogError(f"{crop_id}: en `{name}` el óptimo ({b}) queda por debajo del mínimo absoluto ({a}).")
        if d is not None and c is not None and c > d:
            raise CatalogError(f"{crop_id}: en `{name}` el óptimo ({c}) queda por encima del máximo absoluto ({d}).")


def build(catalog: dict[str, Any]) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Valida el catálogo y devuelve las tablas `crops`, `crop_stages` y las fuentes del catálogo."""
    sources = catalog.get("sources") or []
    known = {s["source_id"] for s in sources}
    crops, stages, seen = [], [], set()
    for crop in catalog.get("crops") or []:
        crop_id = crop.get("crop_id", "")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", crop_id):
            raise CatalogError(f"`crop_id` {crop_id!r} debe ir en snake_case, sin tildes.")
        if crop_id in seen:
            raise CatalogError(f"`crop_id` repetido: {crop_id}.")
        seen.add(crop_id)
        row: dict[str, Any] = {"crop_id": crop_id}
        cited: set[str] = set()
        for field in FIELDS:
            entry = crop.get(field)
            row[field] = _value(crop_id, field, entry, known)
            if isinstance(entry, dict) and entry.get("v") is not None:
                cited.add(entry["s"])
        row["secondary_families"], secondary_source = _secondary_families(crop_id, crop, known)
        if secondary_source:
            cited.add(secondary_source)
        if row["kind"] not in KINDS:
            raise CatalogError(f"{crop_id}: `kind` {row['kind']!r} no es uno de {sorted(KINDS)}.")
        if row["archetype"] is not None and row["archetype"] not in ARCHETYPES:
            raise CatalogError(f"{crop_id}: `archetype` {row['archetype']!r} no es uno de los del contrato.")
        _check_ranges(crop_id, row)
        days = 0
        for stage in (crop.get("stages") or {}).get("list") or []:
            name = stage.get("stage")
            if name not in STAGES:
                raise CatalogError(f"{crop_id}: etapa {name!r} no es una de {list(STAGES)}.")
            if not isinstance(stage.get("days"), int) or stage["days"] <= 0:
                raise CatalogError(f"{crop_id}.{name}: `days` debe ser un entero mayor que cero.")
            if stage.get("s") not in known:
                raise CatalogError(f"{crop_id}.{name}: la etapa no cita una fuente de `sources` (R8).")
            kc = stage.get("kc")
            if kc is not None and not 0 < kc <= 2:
                raise CatalogError(f"{crop_id}.{name}: `kc` {kc} fuera de 0 a 2.")
            cited.add(stage["s"])
            days += stage["days"]
            stages.append(
                {
                    "crop_id": crop_id,
                    "stage": name,
                    "order": STAGES.index(name),
                    "days": stage["days"],
                    "kc": kc,
                    # Sin fuente de grados-día: nulo (P1, HU-150).
                    "gdd": None,
                    "frost_sensitive": stage.get("frost_sensitive"),
                    "heat_sensitive": stage.get("heat_sensitive"),
                    "source_id": stage["s"],
                }
            )
        if row["kind"] != "fallow" and days == 0:
            raise CatalogError(f"{crop_id}: un cultivo o abono verde necesita sus etapas con su duración.")
        # Derivado de las etapas: días entre 30,44 (un mes promedio), con un decimal.
        row["cycle_months"] = round(days / 30.44, 1) if days else None
        row["source_ids"] = sorted(cited)
        crops.append(row)
    if not crops:
        raise CatalogError("El catálogo no tiene cultivos.")
    families = {r["family"] for r in crops if r["family"] is not None}
    for r in crops:
        for family in r["secondary_families"]:
            if family == r["family"]:
                raise CatalogError(f"{r['crop_id']}.secondary_families: {family!r} es la `family` de la propia ficha.")
            if family not in families:
                raise CatalogError(f"{r['crop_id']}.secondary_families: {family!r} no es la `family` de ninguna ficha del catálogo.")
    numeric = [f for f in FIELDS if f.endswith(("_c", "_mm")) or f.startswith("ph_")]
    # Las cifras van todas como decimales, aunque la fuente las dé enteras (mismo tipo en cada columna, R4).
    # Un texto sin fuente en todos los cultivos queda nulo, pero su columna sigue siendo texto (HU-011: el tipo es el del
    # contrato, no el que adivina Polars de una columna vacía).
    text = ["name_es", "kind", "archetype", "family", "water_need", "root_type"]
    crops_table = (
        pl.DataFrame(crops, infer_schema_length=None)
        .with_columns(
            pl.col(numeric).cast(pl.Float64),
            pl.col(text).cast(pl.String),
            pl.col("fixes_nitrogen").cast(pl.Boolean),
            pl.col("secondary_families").cast(pl.List(pl.String)),
        )
        .select(*ORDER)
        .sort("crop_id")
    )
    stages_schema = {
        "crop_id": pl.String, "stage": pl.String, "order": pl.Int8, "days": pl.Int32, "kc": pl.Float64, "gdd": pl.Float64,
        "frost_sensitive": pl.Boolean, "heat_sensitive": pl.Boolean, "source_id": pl.String,
    }  # fmt: skip
    stages_table = pl.DataFrame(stages, schema=stages_schema).sort("crop_id", "order").drop("order")
    sources_table = pl.DataFrame(sources, infer_schema_length=None)
    return crops_table, stages_table, sources_table
