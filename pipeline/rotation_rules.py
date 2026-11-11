"""Reglas de rotación como datos: lee `catalog/rotation_rules.yaml`, lo valida y arma la tabla `rotation_rules` (HU-062).

Solo `load` abre archivos; `parse_rule` y `build` son funciones puras. Lo que se conoce de afuera (las fuentes y las
familias de las fichas) entra por parámetro, para que el mismo validador sirva al catálogo real y a los ejemplos.

Validaciones (si una falla, no se publica nada y el mensaje nombra `rule_id.campo`):
- La lista cerrada de `pipeline/schema.py` (`CONDITION_TYPES`): `kind`, `criterion`, llaves y valores de `params` y de
  `levels`, cortes coherentes y marcadores admitidos en `reason_template` (el motor solo llena esos, R5).
- R8: cada regla cita una fuente que está en `sources`; una fuente de los dos catálogos tiene los mismos datos en los dos.
- R4: `version` igual a la de `crops.yaml` (es `rules_version`), `rule_id` sin repetir, filas ordenadas por `rule_id` y
  `params` y `levels` en JSON con las llaves ordenadas; las listas (`params.families`) se publican ordenadas.

Una regla leída es inmutable: `RotationRule.params` y `levels` son una copia profunda del YAML, con los mapas de solo
lectura (`MappingProxyType`) y las listas como tuplas. `table` las vuelve a JSON.
"""

import copy
import json
import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import polars as pl
import yaml

from pipeline import schema

RULES_FILE = Path("catalog/rotation_rules.yaml")
RULE_FIELDS = ("rule_id", "kind", "criterion", "condition_type", "params", "levels", "reason_template", "source_id")
# Llaves que una regla puede omitir en el YAML: omitidas valen nulo.
OPTIONAL_FIELDS = ("criterion", "levels")


class RotationRulesError(ValueError):
    """Las reglas de rotación no cumplen el contrato. El mensaje dice qué regla y qué campo hay que corregir."""


@dataclass(frozen=True)
class RotationRule:
    """Una regla ya validada contra su tipo de condición. `params` y `levels` son de solo lectura (ver `_freeze`)."""

    rule_id: str
    kind: str
    criterion: str | None
    condition_type: str
    params: Mapping[str, Any]
    levels: Mapping[str, Any] | None
    reason_template: str
    source_id: str


def load(path: Path = RULES_FILE) -> dict[str, Any]:
    """Lee el YAML de las reglas. Es la única función de este módulo que abre archivos."""
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}: sin reglas de rotación no hay filtros ni salud del suelo (HU-062).")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RotationRulesError(f"{path} no es YAML válido: {error}") from error


def _is_number(value: Any) -> bool:
    # `bool` es un `int` en Python: «true» no es un número.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _freeze(value: Any) -> Any:
    """Copia profunda de solo lectura: mapas como `MappingProxyType` y listas como tuplas."""
    value = copy.deepcopy(value)

    def freeze(item: Any) -> Any:
        if isinstance(item, dict):
            return MappingProxyType({key: freeze(inner) for key, inner in item.items()})
        if isinstance(item, list):
            return tuple(freeze(inner) for inner in item)
        return item

    return freeze(value)


def _thaw(value: Any) -> Any:
    """De vuelta a tipos de JSON. Las listas salen ordenadas: hoy la única es `params.families`, un conjunto (R4)."""
    if isinstance(value, Mapping):
        return {key: _thaw(inner) for key, inner in value.items()}
    if isinstance(value, tuple | list):
        return sorted(_thaw(inner) for inner in value)
    return value


def _check_value(where: str, value: Any, spec: schema.Value, known_families: set[str], order: str | None) -> None:
    """Un valor de `params` o de `levels` cumple lo que su tipo de condición admite."""
    if value is None:
        if not spec.nullable:
            raise RotationRulesError(f"{where}: no puede ser nulo.")
        return
    if spec.type == "object":
        _check_object(where, value, spec.keys or {}, known_families, order)
        return
    if spec.type == "family":
        if not isinstance(value, str) or value not in known_families:
            raise RotationRulesError(f"{where}: la familia {value!r} no está en ninguna ficha ({sorted(known_families)}).")
        return
    if spec.type == "families":
        if not isinstance(value, list) or not value:
            raise RotationRulesError(f"{where}: debe ser una lista de familias o nulo (todas).")
        unknown = [family for family in value if not isinstance(family, str) or family not in known_families]
        if unknown:
            raise RotationRulesError(f"{where}: familias que no están en ninguna ficha: {unknown} (hay {sorted(known_families)}).")
        if len(set(value)) != len(value):
            raise RotationRulesError(f"{where}: una familia se repite.")
        return
    if spec.type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise RotationRulesError(f"{where}: debe ser un entero, no {value!r}.")
    elif spec.type == "number":
        if not _is_number(value):
            raise RotationRulesError(f"{where}: debe ser un número, no {value!r}.")
    else:
        # `schema.check_condition_types` lo impide al importar; si llega aquí, es un error de programación.
        raise ValueError(f"{where}: tipo de valor {spec.type!r} desconocido en `schema.CONDITION_TYPES`.")
    if spec.minimum is not None and (value <= spec.minimum if spec.strict_minimum else value < spec.minimum):
        sign = ">" if spec.strict_minimum else "≥"
        raise RotationRulesError(f"{where}: {value} debe ser {sign} {spec.minimum}.")
    if spec.maximum is not None and value > spec.maximum:
        raise RotationRulesError(f"{where}: {value} debe ser ≤ {spec.maximum}.")


def _check_object(where: str, value: Any, keys: Mapping[str, schema.Value], known_families: set[str], order: str | None) -> None:
    """`params` o `levels` (o un grupo de `levels`) es un objeto con exactamente las llaves de su tipo, y cada valor
    cumple lo suyo. En `levels` (`order` no nulo), un objeto con las llaves de un par de cortes revisa su sentido."""
    if not isinstance(value, dict):
        raise RotationRulesError(f"{where}: debe ser un objeto (un mapa YAML), no {value!r}.")
    missing, extra = sorted(set(keys) - set(value)), sorted(set(value) - set(keys))
    if missing or extra:
        raise RotationRulesError(f"{where}: llaves distintas de las de su tipo (faltan {missing}, sobran {extra}).")
    for key, spec in keys.items():
        _check_value(f"{where}.{key}", value[key], spec, known_families, order)
    if order is not None and set(keys) == schema.CUT_KEYS:
        _check_order(where, value, order)


def _check_order(where: str, levels: dict[str, Any], order: str) -> None:
    """Los cortes son coherentes: con cortes mínimos (`higher_is_better`), `moderate <= favorable`; con máximos
    (`lower_is_better`), `favorable <= moderate`.

    `moderate == favorable` quiere decir «sin franja intermedia» (decisión del 9 de noviembre de 2026): el nivel es
    `favorable` desde ese valor y `unfavorable` del otro lado; nunca `moderate`.
    """
    favorable, moderate = levels["favorable"], levels["moderate"]
    if order == "higher_is_better":
        if moderate > favorable:
            raise RotationRulesError(
                f"{where}: `moderate` ({moderate}) no puede ser mayor que `favorable` ({favorable}); "
                "si son iguales, no hay franja intermedia."
            )
    elif order == "lower_is_better":
        if moderate < favorable:
            raise RotationRulesError(
                f"{where}: los cortes son máximos, así que `moderate` ({moderate}) no puede ser menor que "
                f"`favorable` ({favorable}); si son iguales, no hay franja intermedia."
            )
    else:
        # `schema.check_condition_types` lo impide al importar; si llega aquí, es un error de programación.
        raise ValueError(f"{where}: sentido de cortes {order!r} desconocido; los sentidos son {list(schema.LEVELS_ORDERS)}.")


def _check_template(rule_id: str, template: Any, placeholders: tuple[str, ...]) -> None:
    """La razón es un texto y solo usa los marcadores que el motor llena para su tipo (R5)."""
    if not isinstance(template, str) or not template.strip():
        raise RotationRulesError(f"{rule_id}.reason_template: debe ser un texto no vacío.")
    try:
        fields = [(name, spec, conversion) for _, name, spec, conversion in string.Formatter().parse(template) if name is not None]
    except ValueError as error:
        raise RotationRulesError(f"{rule_id}.reason_template: llaves mal cerradas ({error}).") from error
    for name, spec, conversion in fields:
        if name not in placeholders or spec or conversion:
            raise RotationRulesError(f"{rule_id}.reason_template: el marcador {{{name}}} no se admite; admite {list(placeholders)}.")


def parse_rule(raw: dict[str, Any], *, known_sources: set[str], known_families: set[str]) -> RotationRule:
    """Valida una regla contra su tipo de condición (`schema.CONDITION_TYPES`) y la devuelve como objeto."""
    if not isinstance(raw, dict):
        raise RotationRulesError(f"Cada regla debe ser un objeto, no {raw!r}.")
    rule_id = raw.get("rule_id")
    if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", rule_id):
        raise RotationRulesError(f"`rule_id` {rule_id!r} debe ir en snake_case, sin tildes.")
    unknown = sorted(set(raw) - set(RULE_FIELDS))
    if unknown:
        raise RotationRulesError(f"{rule_id}: campos que no son del contrato: {unknown}.")
    missing = [name for name in RULE_FIELDS if name not in raw and name not in OPTIONAL_FIELDS]
    if missing:
        raise RotationRulesError(f"{rule_id}: faltan los campos {missing}.")

    kind, condition_type = raw["kind"], raw["condition_type"]
    if kind not in schema.RULE_KINDS:
        raise RotationRulesError(f"{rule_id}.kind: {kind!r} no es uno de {list(schema.RULE_KINDS)}.")
    spec = schema.CONDITION_TYPES.get(condition_type) if isinstance(condition_type, str) else None
    if spec is None:
        raise RotationRulesError(
            f"{rule_id}.condition_type: {condition_type!r} no está en la lista cerrada {sorted(schema.CONDITION_TYPES)}."
        )
    if kind not in spec.kinds:
        raise RotationRulesError(f"{rule_id}.kind: `{condition_type}` no admite `{kind}`; admite {list(spec.kinds)}.")

    criterion = raw.get("criterion")
    if kind == "filter" and criterion is not None:
        raise RotationRulesError(f"{rule_id}.criterion: debe ser nulo en un `filter`, no {criterion!r}.")
    if kind == "health" and criterion != spec.criterion:
        raise RotationRulesError(f"{rule_id}.criterion: en `{condition_type}` el criterio es `{spec.criterion}`, no {criterion!r}.")

    params = raw["params"]
    _check_object(f"{rule_id}.params", params, spec.params_keys, known_families, None)

    levels = raw.get("levels")
    if kind == "filter" and levels is not None:
        raise RotationRulesError(f"{rule_id}.levels: debe ser nulo en un `filter`.")
    if kind == "health":
        if levels is None:
            raise RotationRulesError(f"{rule_id}.levels: falta en un `health`: sin cortes no hay nivel.")
        if spec.levels_keys is None or spec.levels_order is None:
            # `schema.check_condition_types` lo impide al importar; si llega aquí, es un error de programación.
            raise ValueError(f"`schema.CONDITION_TYPES[{condition_type!r}]` admite `health` sin `levels_keys` o sin `levels_order`.")
        _check_object(f"{rule_id}.levels", levels, spec.levels_keys, known_families, spec.levels_order)
        for param, level in spec.params_equal_levels:
            if params[param] != levels[level]:
                raise RotationRulesError(
                    f"{rule_id}: `params.{param}` ({params[param]}) debe ser igual a `levels.{level}` ({levels[level]})."
                )

    _check_template(rule_id, raw["reason_template"], spec.placeholders)

    source_id = raw["source_id"]
    if not isinstance(source_id, str) or not source_id.strip():
        raise RotationRulesError(f"{rule_id}.source_id: está vacío; toda regla tiene fuente (R8).")
    if source_id not in known_sources:
        raise RotationRulesError(f"{rule_id}.source_id: {source_id!r} no está en `sources` (R8).")

    return RotationRule(
        rule_id=rule_id,
        kind=kind,
        criterion=criterion,
        condition_type=condition_type,
        params=_freeze(params),
        levels=_freeze(levels),
        reason_template=raw["reason_template"],
        source_id=source_id,
    )


def _json(value: Mapping[str, Any] | None) -> str | None:
    # Llaves y listas ordenadas: mismo YAML, mismo texto (R4).
    return None if value is None else json.dumps(_thaw(value), sort_keys=True, ensure_ascii=False)


def table(rules: list[RotationRule]) -> pl.DataFrame:
    """La tabla `rotation_rules` con el esquema del contrato, ordenada por `rule_id`."""
    columns = schema.TABLES["rotation_rules"].columns
    rows = [
        {
            "rule_id": rule.rule_id, "kind": rule.kind, "criterion": rule.criterion, "condition_type": rule.condition_type,
            "params": _json(rule.params), "levels": _json(rule.levels), "reason_template": rule.reason_template,
            "source_id": rule.source_id,
        }
        for rule in rules
    ]  # fmt: skip
    return pl.DataFrame(rows, schema={col: column.dtype for col, column in columns.items()}).sort("rule_id")


def _sources(data: dict[str, Any], crop_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Las fuentes nuevas de este catálogo. Una fuente que también está en `crops.yaml` debe tener los mismos datos."""
    entries = data.get("sources") or []
    if not isinstance(entries, list):
        raise RotationRulesError("`sources` debe ser una lista, con el formato de la de `catalog/crops.yaml`.")
    columns = set(schema.TABLES["sources"].columns)
    by_crop = {source.get("source_id"): source for source in crop_sources}
    seen: set[str] = set()
    new: list[dict[str, Any]] = []
    for source in entries:
        source_id = source.get("source_id") if isinstance(source, dict) else None
        if not isinstance(source_id, str) or not source_id.strip():
            raise RotationRulesError(f"Una fuente de `sources` no tiene `source_id`: {source!r}.")
        if source_id in seen:
            raise RotationRulesError(f"Fuente `{source_id}` repetida en `sources`.")
        seen.add(source_id)
        extra = sorted(set(source) - columns)
        if extra:
            raise RotationRulesError(f"Fuente `{source_id}`: campos que no son de la tabla `sources`: {extra}.")
        if not source.get("name"):
            raise RotationRulesError(f"Fuente `{source_id}`: falta `name`.")
        not_text = sorted(key for key, value in source.items() if value is not None and not isinstance(value, str))
        if not_text:
            raise RotationRulesError(f"Fuente `{source_id}`: {not_text} deben ser texto (una fecha va entre comillas).")
        if source_id in by_crop:
            if source != by_crop[source_id]:
                raise RotationRulesError(
                    f"Fuente `{source_id}`: está en `crops.yaml` y en las reglas con datos distintos. Déjela en uno solo."
                )
            continue
        new.append(source)
    return new


def build(
    data: dict[str, Any], *, crop_sources: list[dict[str, Any]], known_families: set[str], expected_version: str
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Valida las reglas y devuelve la tabla `rotation_rules` y la de las fuentes nuevas de este catálogo."""
    if not isinstance(data, dict):
        raise RotationRulesError("Las reglas de rotación deben tener `version`, `sources` y `rules`.")
    version = data.get("version")
    if version != expected_version:
        raise RotationRulesError(
            f"`version` de las reglas ({version!r}) no es la de `crops.yaml` ({expected_version!r}): "
            "los dos catálogos comparten la versión, que es `rules_version` (decisión 16, `docs/decisiones.md`)."
        )
    new_sources = _sources(data, crop_sources)
    known_sources = {source["source_id"] for source in crop_sources} | {source["source_id"] for source in new_sources}
    entries = data.get("rules")
    if not isinstance(entries, list) or not entries:
        raise RotationRulesError("`rules` debe ser una lista con al menos una regla.")
    rules: list[RotationRule] = []
    seen: set[str] = set()
    for raw in entries:
        rule = parse_rule(raw, known_sources=known_sources, known_families=known_families)
        if rule.rule_id in seen:
            raise RotationRulesError(f"`rule_id` repetido: {rule.rule_id}.")
        seen.add(rule.rule_id)
        rules.append(rule)
    source_columns = schema.TABLES["sources"].columns
    sources_table = pl.DataFrame(
        [{col: source.get(col) for col in source_columns} for source in new_sources],
        schema={col: column.dtype for col, column in source_columns.items()},
    )
    return table(rules), sources_table
