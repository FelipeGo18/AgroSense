"""Motivos `rule` de las reglas `filter` de rotación (HU-081, fase 1; R3; specs/02-contratos.md, «Reglas de rotación
como datos»). Una regla violada excluye la estrategia, con su motivo y la fuente de la regla (R8).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from backend.engine.rotations.candidates import CropInfo


@dataclass(frozen=True)
class FilterRule:
    """Una fila de `rotation_rules` de tipo `filter`, ya leída."""

    rule_id: str
    condition_type: str
    params: Mapping[str, Any]
    reason_template: str
    source_id: str


@dataclass(frozen=True)
class Motive:
    """Un motivo de exclusión o de incidencia de una estrategia. `kind` es 'rule' en esta fase; `cycle` empieza en 1."""

    kind: str
    cycle: int
    reason: str
    source_ids: tuple[str, ...]
    rule_id: str | None = None
    signal: str | None = None
    crop_id: str | None = None


def _families(crop: CropInfo | None, secondary: bool = False) -> set[str]:
    if crop is None:
        return set()
    found = {crop.family} if crop.family else set()
    return found | set(crop.secondary_families) if secondary else found


def _same_family(rule: FilterRule, prev: CropInfo | None, cur: CropInfo | None) -> str | None:
    """Familia repetida entre dos ciclos seguidos: compara solo `family`; una nula nunca cuenta (R1)."""
    if prev is None or cur is None or not prev.family or prev.family != cur.family:
        return None
    wanted = rule.params.get("families")
    return cur.family if wanted is None or cur.family in wanted else None


def _return_gap(rule: FilterRule, history: list[CropInfo | None]) -> int | None:
    """Ciclos de otras familias desde la aparición anterior de `params["family"]` hasta el último ciclo de
    `history` (del más reciente al más antiguo; el primero es el ciclo evaluado). None si ese ciclo no tiene la
    familia, si no hay aparición anterior o si los ciclos intermedios no son menos que `min_cycles`."""
    family = rule.params["family"]
    if family not in _families(history[0], secondary=True):
        return None
    for gap, crop in enumerate(history[1:]):
        if family in _families(crop, secondary=True):
            return gap if gap < rule.params["min_cycles"] else None
    return None


def rule_motives(
    sequence: Sequence[str],
    previous_crop_ids: Sequence[str],
    crops: Mapping[str, CropInfo],
    rules: Sequence[FilterRule],
) -> list[Motive]:
    """Motivos `rule` de una secuencia, por ciclo y luego por `rule_id` (R4).

    Revisa los pares (cultivo anterior más reciente = `previous_crop_ids[0]`, ciclo 1) y (ciclo i, ciclo i+1) para
    `same_family_consecutive`, y para `family_return_min_cycles` cuenta hacia atrás los ciclos intermedios; el
    descanso es un ciclo sin la familia y los cultivos anteriores son ciclos previos, el más reciente primero.
    Un `condition_type` desconocido lanza `ValueError` con el `rule_id`."""
    for rule in rules:
        if rule.condition_type not in ("same_family_consecutive", "family_return_min_cycles"):
            raise ValueError(f"Regla {rule.rule_id}: condition_type desconocido {rule.condition_type!r}")
    chain = [crops.get(c) for c in sequence]
    before = [crops.get(c) for c in previous_crop_ids]
    motives: list[Motive] = []
    for i in range(len(chain)):
        for rule in sorted(rules, key=lambda r: r.rule_id):
            if rule.condition_type == "same_family_consecutive":
                prev = chain[i - 1] if i > 0 else (before[0] if before else None)
                family = _same_family(rule, prev, chain[i])
                reason = rule.reason_template.format(family=family) if family else None
            else:
                gap = _return_gap(rule, [*chain[i::-1], *before])
                reason = rule.reason_template.format(family=rule.params["family"], cycles=gap) if gap is not None else None
            if reason:
                motives.append(Motive("rule", i + 1, reason, (rule.source_id,), rule_id=rule.rule_id))
    return motives
