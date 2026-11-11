"""Esquema de las tablas publicadas (HU-011): la tabla «Tablas publicadas» de `specs/02-contratos.md`, en código.

Cada tabla dice su llave, sus columnas con su tipo y su unidad, y si es P0 o P1. `check` compara una tabla con su
esquema: mismas columnas, en el mismo orden, con el mismo tipo; llave sin repetir y sin nulos; `quality` solo con sus
valores. El pipeline la corre antes de publicar y las pruebas la corren sobre lo publicado y sobre los ejemplos.

Si el contrato cambia, cambia aquí también (y se registra en `docs/decisiones.md`): las pruebas fallan si no coinciden.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import polars as pl

# Valores permitidos de `quality` en todas las tablas (contrato, «Valores de `quality`», decisión 15).
QUALITY = ("ok", "partial")
# La rejilla común de 250 m (contrato, «La rejilla de 250 m»): `cell_id` = "{fila}_{columna}".
GRID_STEP_DEG = 0.0025

S, F, I8, I16, I32, I64, B = pl.String, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Boolean
IDS = pl.List(pl.String)


@dataclass(frozen=True)
class Column:
    dtype: pl.DataType
    unit: str = ""
    nullable: bool = True


@dataclass(frozen=True)
class Table:
    key: tuple[str, ...]
    columns: dict[str, Column]
    priority: str = "P0"
    hu: str = ""
    notes: str = ""
    # Columnas de fuente: `source_id` (una) o `source_ids` (lista), para revisar R8.
    source_column: str = field(default="source_id")


def c(dtype: pl.DataType, unit: str = "", nullable: bool = True) -> Column:
    return Column(dtype, unit, nullable)


def cell_id(lat: float, lon: float) -> str:
    """La celda de la rejilla común que contiene un punto: fila y columna desde (90° N, 180° O)."""
    row = int((90 - lat) // GRID_STEP_DEG)
    col = int((lon + 180) // GRID_STEP_DEG)
    return f"{row}_{col}"


def cell_center(cell: str) -> tuple[float, float]:
    """El centro (lat, lon) de una celda de la rejilla común."""
    row, col = (int(part) for part in cell.split("_"))
    return 90 - (row + 0.5) * GRID_STEP_DEG, -180 + (col + 0.5) * GRID_STEP_DEG


SOIL = {
    "ph": c(F, "pH"),
    "ph_p05": c(F, "pH"),
    "ph_p95": c(F, "pH"),
    "soc_g_kg": c(F, "g/kg"),
    "soc_p05": c(F, "g/kg"),
    "soc_p95": c(F, "g/kg"),
    "nitrogen_g_kg": c(F, "g/kg"),
    "clay_pct": c(F, "%"),
    "sand_pct": c(F, "%"),
    "silt_pct": c(F, "%"),
    "texture_class": c(S, "clase USDA"),
}

TABLES: dict[str, Table] = {
    "municipalities": Table(
        key=("municipality_id",),
        columns={
            "municipality_id": c(S, "DIVIPOLA, 5 dígitos", False),
            "name": c(S, "", False),
            "department_id": c(S, "", False),
            "department": c(S, "", False),
            "lat": c(F, "grados"),
            "lon": c(F, "grados"),
            "altitude_m": c(F, "m"),
            "climate_cell_elevation_m": c(F, "m"),
            "tmean_annual_c": c(F, "°C"),
            "slope_pct": c(F, "%"),
            "source_ids": c(IDS, "", False),
        },
        hu="HU-044, HU-206",
        source_column="source_ids",
    ),
    "crops": Table(
        key=("crop_id",),
        columns={
            "crop_id": c(S, "", False),
            "name_es": c(S, "", False),
            "kind": c(S, "crop, cover o fallow", False),
            "archetype": c(S),
            "family": c(S),
            "secondary_families": c(IDS, "", False),
            "water_need": c(S),
            "root_type": c(S),
            "fixes_nitrogen": c(B),
            "tmean_min_c": c(F, "°C"),
            "tmean_opt_min_c": c(F, "°C"),
            "tmean_opt_max_c": c(F, "°C"),
            "tmean_max_c": c(F, "°C"),
            "base_temp_c": c(F, "°C"),
            "temp_min_c": c(F, "°C"),
            "temp_opt_min_c": c(F, "°C"),
            "temp_opt_max_c": c(F, "°C"),
            "heat_max_c": c(F, "°C"),
            "rain_min_mm": c(F, "mm/año"),
            "rain_opt_min_mm": c(F, "mm/año"),
            "rain_opt_max_mm": c(F, "mm/año"),
            "rain_max_mm": c(F, "mm/año"),
            "ph_min": c(F, "pH"),
            "ph_opt_min": c(F, "pH"),
            "ph_opt_max": c(F, "pH"),
            "ph_max": c(F, "pH"),
            "frost_killing_c": c(F, "°C"),
            "cycle_months": c(F, "meses"),
            "source_ids": c(IDS, "", False),
        },
        hu="HU-061, HU-199",
        source_column="source_ids",
    ),
    "crop_stages": Table(
        key=("crop_id", "stage"),
        columns={
            "crop_id": c(S, "", False),
            "stage": c(S, "initial, development, mid o late", False),
            "days": c(I32, "días", False),
            "kc": c(F),
            "gdd": c(F, "°C·día"),
            "frost_sensitive": c(B),
            "heat_sensitive": c(B),
            "source_id": c(S, "", False),
        },
        hu="HU-142",
    ),
    "rotation_rules": Table(
        key=("rule_id",),
        columns={
            "rule_id": c(S, "", False),
            "kind": c(S, "filter o health", False),
            "criterion": c(S, "criterio de soil_health"),
            "condition_type": c(S, "lista cerrada del contrato", False),
            "params": c(S, "JSON", False),
            "levels": c(S, "JSON"),
            "reason_template": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-062",
    ),
    "climate_risk_week": Table(
        key=("municipality_id", "week"),
        columns={
            "municipality_id": c(S, "", False),
            "week": c(I8, "1 a 52", False),
            "frost_freq_pct": c(F, "%"),
            "tmax_p90_c": c(F, "°C"),
            "precip_normal_mm": c(F, "mm"),
            "precip_dry_mm": c(F, "mm"),
            "et0_normal_mm": c(F, "mm"),
            "heavy_rain_days_mean": c(F, "días"),
            "dry_window_freq_pct": c(F, "%"),
            "blight_days_mean": c(F, "días"),
            "years": c(I16, "años"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        priority="P1",
        hu="HU-193",
    ),
    "climate_day": Table(
        key=("municipality_id", "date"),
        columns={
            "municipality_id": c(S, "", False),
            "date": c(pl.Date, "", False),
            "temp_min_c": c(F, "°C"),
            "temp_max_c": c(F, "°C"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-041",
    ),
    "climate_normal_doy": Table(
        key=("municipality_id", "doy"),
        columns={
            "municipality_id": c(S, "", False),
            "doy": c(I16, "1 a 366", False),
            "temp_min_c": c(F, "°C"),
            "temp_max_c": c(F, "°C"),
            "source_id": c(S, "", False),
        },
        priority="P1",
        hu="HU-186",
    ),
    "climate_risk_month": Table(
        key=("municipality_id", "month"),
        columns={
            "municipality_id": c(S, "", False),
            "month": c(I8, "1 a 12", False),
            "frost_freq_pct": c(F, "%"),
            "frost_days_mean": c(F, "días"),
            "tmax_p90_c": c(F, "°C"),
            "heavy_rain_days_mean": c(F, "días (P1)"),
            "dry_window_freq_pct": c(F, "% (P1)"),
            "blight_days_mean": c(F, "días (P1)"),
            "years": c(I16, "años"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-045",
    ),
    "climate_month": Table(
        key=("municipality_id", "year", "month"),
        columns={
            "municipality_id": c(S, "", False),
            "year": c(I16, "", False),
            "month": c(I8, "1 a 12", False),
            "precip_mm": c(F, "mm"),
            "precip_normal_mm": c(F, "mm"),
            "precip_dry_mm": c(F, "mm"),
            "et0_mm": c(F, "mm"),
            "et0_normal_mm": c(F, "mm"),
            "soil_wetness_top": c(F, "fracción 0 a 1"),
            "soil_wetness_root": c(F, "fracción 0 a 1"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-042, HU-143, HU-205",
    ),
    "precip_month": Table(
        key=("municipality_id", "year", "month", "source_id"),
        columns={
            "municipality_id": c(S, "", False),
            "year": c(I16, "", False),
            "month": c(I8, "1 a 12", False),
            "source_id": c(S, "", False),
            "precip_mm": c(F, "mm"),
            "precip_normal_mm": c(F, "mm"),
            "precip_dry_mm": c(F, "mm"),
            "normal_period": c(S, "años, como «2001-2024»"),
            "quality": c(S, "", False),
        },
        hu="HU-207",
    ),
    "soil_moisture_month": Table(
        key=("municipality_id", "year", "month", "source_id"),
        columns={
            "municipality_id": c(S, "", False),
            "year": c(I16, "", False),
            "month": c(I8, "1 a 12", False),
            "source_id": c(S, "", False),
            "sm_surface_m3_m3": c(F, "m³/m³"),
            "sm_rootzone_m3_m3": c(F, "m³/m³"),
            "quality": c(S, "", False),
        },
        hu="HU-210",
    ),
    "ndvi_municipality": Table(
        key=("municipality_id", "year", "period"),
        columns={
            "municipality_id": c(S, "", False),
            "year": c(I16, "", False),
            "period": c(I8, "1 a 23 (16 días)", False),
            "ndvi_median": c(F, "-1 a 1"),
            "valid_pixels_pct": c(F, "%"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-208",
    ),
    "ndvi_municipality_normal": Table(
        key=("municipality_id", "period"),
        columns={
            "municipality_id": c(S, "", False),
            "period": c(I8, "1 a 23", False),
            "ndvi_normal": c(F, "-1 a 1"),
            "years": c(I16, "años"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-208",
    ),
    "ndvi_grid": Table(
        key=("cell_id", "period"),
        columns={
            "cell_id": c(S, "rejilla común", False),
            "period": c(I8, "1 a 23", False),
            "ndvi_normal": c(F, "-1 a 1"),
            "years": c(I16, "años"),
            "valid_pct": c(F, "%"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        priority="P1",
        hu="HU-209",
    ),
    "climate_change_month": Table(
        key=("municipality_id", "period_id", "month", "source_id"),
        columns={
            "municipality_id": c(S, "", False),
            "period_id": c(S, "", False),
            "month": c(I8, "1 a 12", False),
            "source_id": c(S, "", False),
            "frost_freq_pct": c(F, "%"),
            "tmax_p90_c": c(F, "°C"),
            "precip_normal_mm": c(F, "mm"),
            "years": c(I16, "años"),
            "quality": c(S, "", False),
        },
        hu="HU-216",
    ),
    "supply_semester": Table(
        key=("municipality_id", "crop_id", "year", "semester", "source_id"),
        columns={
            "municipality_id": c(S, "", False),
            "crop_id": c(S, "", False),
            "year": c(I16, "", False),
            "semester": c(S, "A o B", False),
            "source_id": c(S, "", False),
            "planted_ha": c(F, "ha"),
            "harvested_ha": c(F, "ha"),
            "production_t": c(F, "t"),
            "yield_t_ha": c(F, "t/ha"),
            "planted_change_pct": c(F, "%"),
            "dept_share_pct": c(F, "%"),
            "preliminary": c(B),
            "quality": c(S, "", False),
        },
        hu="HU-031, HU-032",
    ),
    "market_month": Table(
        key=("crop_id", "market_id", "month"),
        columns={
            "crop_id": c(S, "", False),
            "market_id": c(S, "", False),
            "month": c(I8, "1 a 12", False),
            "price_cop_kg": c(I64, "COP/kg"),
            "volume_t": c(F, "t"),
            "seasonal_index": c(F, "1 = un mes como cualquiera"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        priority="P1",
        hu="HU-051",
        notes="Sus columnas cambian con el PR de SIPSA (HU-051): se actualizan aquí cuando entre.",
    ),
    "municipality_boundaries": Table(
        key=("municipality_id",),
        columns={
            "municipality_id": c(S, "", False),
            "geometry": c(pl.Binary, "WKB, WGS84", False),
            "source_id": c(S, "", False),
        },
        hu="HU-044",
    ),
    "grid_cells": Table(
        key=("cell_id",),
        columns={
            "cell_id": c(S, "rejilla común", False),
            "lat": c(F, "grados", False),
            "lon": c(F, "grados", False),
            "municipality_id": c(S, "", False),
            "altitude_m": c(F, "m"),
            "slope_pct": c(F, "%"),
            **SOIL,
            "quality": c(S, "", False),
            "source_ids": c(IDS, "", False),
        },
        hu="HU-206, HU-181",
        source_column="source_ids",
    ),
    "soil_municipality": Table(
        key=("municipality_id",),
        columns={
            "municipality_id": c(S, "", False),
            **SOIL,
            "cells": c(I32, "celdas"),
            "quality": c(S, "", False),
            "source_id": c(S, "", False),
        },
        hu="HU-181",
    ),
    "sources": Table(
        key=("source_id",),
        columns={
            "source_id": c(S, "", False),
            "name": c(S, "", False),
            "institution": c(S),
            "url": c(S),
            "downloaded_at": c(S, "fecha ISO"),
            "period_covered": c(S),
            "coverage": c(S),
            "license": c(S),
            "notes": c(S),
        },
        hu="HU-122",
        source_column="",
    ),
}


def _frozen(mapping: Mapping[str, "Value"] | None) -> Mapping[str, "Value"] | None:
    # Copia y envuelve: el `dict` original no queda a la vista, así que nadie cambia la spec después de importarla.
    return None if mapping is None else MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class Value:
    """Qué admite un valor de `params` o de `levels` de una regla de rotación.

    `type` es uno de `VALUE_TYPES`: `family` (una familia de las fichas), `families` (lista de familias), `integer`,
    `number` u `object` (un objeto anidado con exactamente las llaves de `keys`, por ejemplo los cortes de un grupo de
    `organic_matter_cycles`, decisión 16). Los límites son inclusivos salvo `strict_minimum`; `nullable` deja el valor
    nulo (en `families`, nulo es «todas las familias»). `keys` se guarda como un mapa de solo lectura.
    """

    type: str
    minimum: float | None = None
    maximum: float | None = None
    strict_minimum: bool = False
    nullable: bool = False
    keys: Mapping[str, "Value"] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "keys", _frozen(self.keys))


@dataclass(frozen=True)
class ConditionSpec:
    """Un tipo de condición de la lista cerrada de «Reglas de rotación como datos» (contrato, HU-062).

    - `kinds`: los `kind` que admite (`filter`, `health`).
    - `criterion`: el criterio de `soil_health` que decide en un `health`; nulo si solo es `filter`.
    - `params_keys` y `levels_keys`: las llaves exactas de `params` y de `levels`, con lo que admite cada valor. Un
      tipo con `health` siempre tiene `levels_keys`; uno que solo es `filter`, nunca. Un valor `object` de `levels` es un
      grupo de cortes (decisión 16: `low` y `normal` de `organic_matter_cycles`).
    - `levels_order`: `higher_is_better` (los cortes son mínimos) o `lower_is_better` (los cortes son máximos). Vale para
      cada par `favorable`/`moderate` de `levels`, también dentro de un grupo. Obligatorio si hay `levels_keys`. Con
      `higher_is_better`, `moderate <= favorable`; con `lower_is_better`, `favorable <= moderate`. `moderate ==
      favorable` quiere decir «sin franja intermedia»: el nivel es `favorable` desde ese valor y `unfavorable` del otro
      lado, nunca `moderate`.
    - `placeholders`: los `{marcadores}` que admite `reason_template`; el motor solo llena estos (R5).
    - `params_equal_levels`: pares (`params`, `levels`) que deben valer lo mismo en un `health`.

    `params_keys` y `levels_keys` se guardan como mapas de solo lectura.
    """

    kinds: tuple[str, ...]
    criterion: str | None
    params_keys: Mapping[str, Value]
    levels_keys: Mapping[str, Value] | None
    levels_order: str | None
    placeholders: tuple[str, ...]
    params_equal_levels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "params_keys", _frozen(self.params_keys))
        object.__setattr__(self, "levels_keys", _frozen(self.levels_keys))


RULE_KINDS = ("filter", "health")
LEVELS_ORDERS = ("higher_is_better", "lower_is_better")
VALUE_TYPES = ("family", "families", "integer", "number", "object")
# Las llaves de un par de cortes: desde qué valor el criterio es `favorable` o `moderate` (menos que eso, `unfavorable`).
CUT_KEYS = frozenset({"favorable", "moderate"})
_CYCLES = Value("integer", minimum=0)
CONDITION_TYPES: Mapping[str, ConditionSpec] = MappingProxyType({
    "same_family_consecutive": ConditionSpec(
        kinds=("filter",),
        criterion=None,
        params_keys={"families": Value("families", nullable=True)},
        levels_keys=None,
        levels_order=None,
        placeholders=("family",),
    ),
    "family_return_min_cycles": ConditionSpec(
        kinds=("filter", "health"),
        criterion="pest_break",
        params_keys={"family": Value("family"), "min_cycles": Value("integer", minimum=1)},
        levels_keys={"favorable": _CYCLES, "moderate": _CYCLES},
        levels_order="higher_is_better",
        placeholders=("family", "cycles"),
        params_equal_levels=(("min_cycles", "favorable"),),
    ),
    "legume_cycles": ConditionSpec(
        kinds=("health",),
        criterion="nitrogen",
        params_keys={},
        levels_keys={"favorable": _CYCLES, "moderate": _CYCLES},
        levels_order="higher_is_better",
        placeholders=("count",),
    ),
    "organic_matter_cycles": ConditionSpec(
        kinds=("health",),
        criterion="organic_carbon",
        params_keys={"soc_low_g_kg": Value("number", minimum=0, strict_minimum=True)},
        # Decisión 16 (`docs/decisiones.md`): un grupo de cortes con el suelo bajo y otro con el suelo normal, los dos
        # obligatorios. Con el carbono bajo, `favorable` pide al menos un ciclo de abono verde o descanso.
        levels_keys={
            "low": Value("object", keys={"favorable": Value("integer", minimum=1), "moderate": _CYCLES}),
            "normal": Value("object", keys={"favorable": _CYCLES, "moderate": _CYCLES}),
        },
        levels_order="higher_is_better",
        # `{soc_range}`: el rango p05–p95 del carbono estimado (R10: el suelo es una estimación de 250 m y se dice).
        placeholders=("count", "soc_level", "soc_range"),
    ),
    "covered_months_pct": ConditionSpec(
        kinds=("health",),
        criterion="soil_cover",
        params_keys={},
        levels_keys={"favorable": Value("number", 0, 100), "moderate": Value("number", 0, 100)},
        levels_order="higher_is_better",
        placeholders=("pct",),
    ),
    "bare_months_on_slope": ConditionSpec(
        kinds=("health",),
        criterion="erosion",
        params_keys={"slope_pct_from": Value("number", minimum=0)},
        levels_keys={"favorable": Value("number", minimum=0), "moderate": Value("number", minimum=0)},
        levels_order="lower_is_better",
        placeholders=("slope", "months"),
    ),
})  # fmt: skip


def _check_value_spec(where: str, value: Value, *, in_levels: bool) -> None:
    if value.type not in VALUE_TYPES:
        raise ValueError(f"{where}: tipo de valor {value.type!r} desconocido; los tipos son {list(VALUE_TYPES)}.")
    if (value.type == "object") != (value.keys is not None):
        raise ValueError(f"{where}: `keys` va solo, y siempre, en un valor de tipo `object`.")
    numeric = value.type in ("integer", "number")
    if not numeric and (value.minimum is not None or value.maximum is not None or value.strict_minimum):
        raise ValueError(f"{where}: los límites solo valen en `integer` o `number`.")
    if value.strict_minimum and value.minimum is None:
        raise ValueError(f"{where}: `strict_minimum` sin `minimum`.")
    if in_levels and value.type in ("family", "families"):
        raise ValueError(f"{where}: un corte de `levels` es un número o un grupo de cortes, no una familia.")
    if value.type == "object":
        _check_keys_spec(where, value.keys or {}, in_levels=in_levels)


def _check_keys_spec(where: str, keys: Mapping[str, Value], *, in_levels: bool) -> None:
    for key, value in keys.items():
        _check_value_spec(f"{where}.{key}", value, in_levels=in_levels)
    if not in_levels:
        return
    # En `levels`, cada objeto es un par de cortes o un conjunto de grupos de cortes; nunca una mezcla.
    groups = [key for key, value in keys.items() if value.type == "object"]
    if groups and len(groups) != len(keys):
        raise ValueError(f"{where}: mezcla grupos de cortes con cortes sueltos.")
    if not groups and set(keys) != CUT_KEYS:
        raise ValueError(f"{where}: un par de cortes tiene exactamente las llaves {sorted(CUT_KEYS)}, no {sorted(keys)}.")


def check_condition_types(types: Mapping[str, ConditionSpec]) -> None:
    """Autocomprobación de la lista cerrada. Un error aquí es de programación: `ValueError` al importar el módulo."""
    for name, spec in types.items():
        where = f"CONDITION_TYPES[{name!r}]"
        if not spec.kinds or not set(spec.kinds) <= set(RULE_KINDS):
            raise ValueError(f"{where}.kinds: {spec.kinds!r} debe ser parte de {list(RULE_KINDS)}.")
        health = "health" in spec.kinds
        if health != (spec.criterion is not None):
            raise ValueError(f"{where}.criterion: va solo, y siempre, en un tipo que admite `health`.")
        if health != (spec.levels_keys is not None):
            raise ValueError(f"{where}.levels_keys: va solo, y siempre, en un tipo que admite `health`.")
        if spec.levels_keys is None and spec.levels_order is not None:
            raise ValueError(f"{where}.levels_order: sin `levels_keys` no hay cortes que ordenar.")
        if spec.levels_keys is not None and spec.levels_order not in LEVELS_ORDERS:
            raise ValueError(f"{where}.levels_order: {spec.levels_order!r} debe ser uno de {list(LEVELS_ORDERS)}.")
        _check_keys_spec(f"{where}.params_keys", spec.params_keys, in_levels=False)
        if spec.levels_keys is not None:
            _check_keys_spec(f"{where}.levels_keys", spec.levels_keys, in_levels=True)
        for param, level in spec.params_equal_levels:
            if param not in spec.params_keys or level not in (spec.levels_keys or {}):
                raise ValueError(f"{where}.params_equal_levels: ({param!r}, {level!r}) nombra llaves que no existen.")
        if not all(isinstance(p, str) and p.isidentifier() for p in spec.placeholders):
            raise ValueError(f"{where}.placeholders: cada marcador es un nombre sin espacios.")


check_condition_types(CONDITION_TYPES)


class SchemaError(ValueError):
    """Una tabla no cumple su esquema del contrato. El mensaje dice qué falla."""


def typed(name: str, table: pl.DataFrame) -> pl.DataFrame:
    """Le da el tipo del contrato a las columnas que quedaron sin tipo (`Null`) porque todos sus valores son nulos.

    Solo toca esas columnas: un valor que no cabe en su tipo sigue siendo un error de `check`, no se convierte.
    """
    columns = TABLES[name].columns
    untyped = [col for col in table.columns if col in columns and table.schema[col] == pl.Null]
    return table.with_columns(pl.col(col).cast(columns[col].dtype) for col in untyped) if untyped else table


def check(name: str, table: pl.DataFrame) -> None:
    """La tabla cumple su esquema: columnas, orden, tipos, nulos donde no se permiten, llave única y `quality`."""
    if name not in TABLES:
        raise SchemaError(f"`{name}` no es una tabla del contrato.")
    spec = TABLES[name]
    expected = list(spec.columns)
    if table.columns != expected:
        missing = [col for col in expected if col not in table.columns]
        extra = [col for col in table.columns if col not in spec.columns]
        raise SchemaError(f"`{name}`: columnas distintas del contrato (faltan {missing}, sobran {extra}, o cambia el orden).")
    for col, column in spec.columns.items():
        actual = table.schema[col]
        if actual != column.dtype:
            raise SchemaError(f"`{name}.{col}` es {actual} y el contrato dice {column.dtype}.")
        if not column.nullable and table[col].null_count():
            raise SchemaError(f"`{name}.{col}` tiene nulos y el contrato no los permite.")
    repeated = table.select(spec.key).filter(pl.struct(list(spec.key)).is_duplicated())
    if not repeated.is_empty():
        raise SchemaError(f"`{name}`: la llave {list(spec.key)} se repite, por ejemplo {repeated.head(2).to_dicts()}.")
    if "quality" in spec.columns:
        bad = set(table["quality"].unique().to_list()) - set(QUALITY)
        if bad:
            raise SchemaError(f"`{name}.quality` tiene valores fuera de {list(QUALITY)}: {sorted(bad)}.")


def cited_sources(name: str, table: pl.DataFrame) -> set[str]:
    """Las fuentes que cita una tabla, para revisar que existan en `sources` (R8)."""
    column = TABLES[name].source_column
    if not column or column not in table.columns:
        return set()
    if TABLES[name].columns[column].dtype == IDS:
        return {source for ids in table[column].drop_nulls().to_list() for source in ids}
    return set(table[column].drop_nulls().to_list())
