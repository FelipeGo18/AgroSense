"""Catálogo agronómico: lee `catalog/crops.yaml`, lo valida y arma las tablas `crops` y `crop_stages` (EP-06).

Validaciones (si una falla, no se publica nada):
- R8: todo valor no nulo cita una fuente que está en `sources`; un valor nulo dice por qué (nota).
- Contrato: `crop_id` en `snake_case` sin repetir; `kind` y `archetype` de los valores permitidos; etapas conocidas, con
  días mayores que cero; `kc` entre 0 y 2.
- Decisión 16: `secondary_families` es una lista de textos con fuente (vacía si falta), sin repetidos, sin la `family` de la
  propia ficha y con valores que son la `family` de alguna ficha del catálogo.
- HU-199: cada óptimo cae dentro de su rango absoluto (un límite nulo con fuente es un rango abierto).
- HU-227: `forage` es verdadero o falso con su fuente (R8), o nulo; el descanso no lleva valor.
- HU-063: `fallow_days` es solo del descanso, un entero de días mayor que cero (o nulo con nota), y el descanso no lleva
  etapas. Su `cycle_months` sale de esos días.
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
ARTICLES = {"el", "la"}
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
    "name_es", "article", "kind", "archetype", "family", "water_need", "root_type", "fixes_nitrogen", "forage",
    *RANGES["tmean"], "base_temp_c", "temp_min_c", "temp_opt_min_c", "temp_opt_max_c", "heat_max_c",
    *RANGES["rain"], *RANGES["ph"], "frost_killing_c", "root_depth_min_m", "root_depth_max_m", "depletion_p",
    "fallow_days",
)  # fmt: skip
# La raíz (FAO-56, tabla 22; HU-144): profundidad en m y fracción de 0 a 1.
ROOT_FIELDS = ("root_depth_min_m", "root_depth_max_m", "depletion_p")
# Un mes promedio, para `cycle_months` (contrato).
DAYS_PER_MONTH = 30.44
# El orden de las columnas de `crops` es el del contrato: `secondary_families` va tras `family`.
_FAMILY = FIELDS.index("family") + 1
ORDER = ("crop_id", *FIELDS[:_FAMILY], "secondary_families", *FIELDS[_FAMILY:], "cycle_months", "source_ids")


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


def _sensitivity(crop_id: str, stage: str, entry: dict[str, Any], field: str, known: set[str]) -> tuple[bool | None, str | None]:
    """Si la helada o el calor dañan en una etapa (`frost_sensitive`, `heat_sensitive`), con su propia fuente (HU-142,
    aprobado por Felipe el 13 de noviembre de 2026): `{v: true, s: fuente}`. La fuente es otra que la de los días y el Kc
    de la etapa, así que va aparte (`frost_source_id`, `heat_source_id`). Sin dato con fuente, los dos nulos (R1, R8)."""
    value = entry.get(field)
    if value is None:
        return None, None
    if not isinstance(value, dict) or "v" not in value:
        raise CatalogError(f"{crop_id}.{stage}: `{field}` va como {{v: true o false, s: fuente}}, con su fuente (R8).")
    if value["v"] is None:
        return None, None
    if not isinstance(value["v"], bool):
        raise CatalogError(f"{crop_id}.{stage}: `{field}` debe ser true o false, no {value['v']!r}.")
    if value.get("s") not in known:
        raise CatalogError(f"{crop_id}.{stage}: `{field}` no cita una fuente de `sources` (R8).")
    return value["v"], value["s"]


def _check_root(crop_id: str, row: dict[str, Any]) -> None:
    """La raíz va completa o nula, con la mínima no mayor que la máxima, de 0 a 3 m, y `p` entre 0 y 1 (HU-144)."""
    low, high, p = (row.get(k) for k in ROOT_FIELDS)
    if {low is None, high is None, p is None} == {True, False}:
        raise CatalogError(f"{crop_id}: la raíz va completa (profundidad mínima, máxima y `depletion_p`) o nula.")
    if low is None:
        return
    if not 0 < low <= high <= 3:
        raise CatalogError(f"{crop_id}: la profundidad de la raíz ({low} a {high} m) debe ir de 0 a 3 m, la mínima primero.")
    if not 0 < p < 1:
        raise CatalogError(f"{crop_id}: `depletion_p` {p} debe estar entre 0 y 1.")


def _check_fallow(crop_id: str, row: dict[str, Any], has_stages: bool) -> None:
    """`fallow_days` es solo del descanso (HU-063, decisión 7 del PR #109): un entero de días mayor que cero, o nulo con su
    nota (R1). Un descanso no lleva etapas: su duración es esa y no hay dos maneras de contarla."""
    days = row.get("fallow_days")
    if row["kind"] != "fallow":
        if days is not None:
            raise CatalogError(f"{crop_id}: `fallow_days` es solo del descanso; la duración de un cultivo sale de sus etapas.")
        return
    if has_stages:
        raise CatalogError(f"{crop_id}: un descanso no lleva etapas; su duración es `fallow_days`.")
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days <= 0):
        raise CatalogError(f"{crop_id}: `fallow_days` {days!r} debe ser un entero de días mayor que cero.")


def _check_forage(crop_id: str, row: dict[str, Any], crop: dict[str, Any]) -> None:
    """`forage` (HU-227, aprobado por Felipe el 15 de noviembre de 2026): `true` o `false` con su fuente (`_value` ya exige que
    exista, R8), o nulo si no hay fuente (R1). Un descanso (`kind = fallow`) no lleva valor: no es un cultivo ni un abono verde.
    Un cultivo o un abono verde lleva siempre la clave `forage` (con `v: null` y su porqué si no hay fuente): una ficha que
    la omite no se publica en silencio (revisión de Haider del #161)."""
    if row["kind"] != "fallow" and "forage" not in crop:
        raise CatalogError(f"{crop_id}: falta la clave `forage` (use `v: null` con `n` si no hay fuente, R1).")
    value = row.get("forage")
    if value is None:
        return
    if not isinstance(value, bool):
        raise CatalogError(f"{crop_id}: `forage` debe ser true, false o nulo, no {value!r}.")
    if row["kind"] == "fallow":
        raise CatalogError(f"{crop_id}: un descanso no lleva `forage`: no es un cultivo ni un abono verde.")


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
        if row["article"] not in ARTICLES:
            raise CatalogError(f"{crop_id}: `article` {row['article']!r} debe ser uno de {sorted(ARTICLES)}.")
        _check_forage(crop_id, row, crop)
        _check_ranges(crop_id, row)
        _check_root(crop_id, row)
        _check_fallow(crop_id, row, bool((crop.get("stages") or {}).get("list")))
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
            frost, frost_source = _sensitivity(crop_id, name, stage, "frost_sensitive", known)
            heat, heat_source = _sensitivity(crop_id, name, stage, "heat_sensitive", known)
            cited.update(s for s in (frost_source, heat_source) if s is not None)
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
                    "frost_sensitive": frost,
                    "frost_source_id": frost_source,
                    "heat_sensitive": heat,
                    "heat_source_id": heat_source,
                    "source_id": stage["s"],
                }
            )
        if row["kind"] != "fallow" and days == 0:
            raise CatalogError(f"{crop_id}: un cultivo o abono verde necesita sus etapas con su duración.")
        # Derivado de las etapas (o, en el descanso, de `fallow_days`): días entre 30,44 (un mes promedio), con un decimal.
        if row["kind"] == "fallow":
            days = row["fallow_days"] or 0
        row["cycle_months"] = round(days / DAYS_PER_MONTH, 1) if days else None
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
    numeric = [f for f in FIELDS if f.endswith(("_c", "_mm")) or f.startswith("ph_") or f in ROOT_FIELDS]
    # Las cifras van todas como decimales, aunque la fuente las dé enteras (mismo tipo en cada columna, R4).
    # Un texto sin fuente en todos los cultivos queda nulo, pero su columna sigue siendo texto (HU-011: el tipo es el del
    # contrato, no el que adivina Polars de una columna vacía).
    text = ["name_es", "article", "kind", "archetype", "family", "water_need", "root_type"]
    crops_table = (
        pl.DataFrame(crops, infer_schema_length=None)
        .with_columns(
            pl.col(numeric).cast(pl.Float64),
            pl.col(text).cast(pl.String),
            pl.col(["fixes_nitrogen", "forage"]).cast(pl.Boolean),
            pl.col("fallow_days").cast(pl.Int32),
            pl.col("secondary_families").cast(pl.List(pl.String)),
        )
        .select(*ORDER)
        .sort("crop_id")
    )
    stages_schema = {
        "crop_id": pl.String, "stage": pl.String, "order": pl.Int8, "days": pl.Int32, "kc": pl.Float64, "gdd": pl.Float64,
        "frost_sensitive": pl.Boolean, "frost_source_id": pl.String, "heat_sensitive": pl.Boolean,
        "heat_source_id": pl.String, "source_id": pl.String,
    }  # fmt: skip
    stages_table = pl.DataFrame(stages, schema=stages_schema).sort("crop_id", "order").drop("order")
    sources_table = pl.DataFrame(sources, infer_schema_length=None)
    return crops_table, stages_table, sources_table
