"""HU-212, PR B: forma de los cinco criterios de `soil_health` y los cálculos de `nitrogen` y `pest_break` (R3, R8).

Compara estrategias según reglas con fuente: no predice cuánto mejora el suelo (decisión 4). Un dato o una regla que
falta nunca da un nivel (R1, R8). `organic_carbon`, `soil_cover` y `erosion` los calculan los PR C y D: aquí quedan
`insufficient_data`. Función pura y determinista (R4, R6).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SOIL_CRITERIA = ("nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion")
TEAM_CRITERION = "criterio_equipo_2026"
TEAM_NOTE = "criterio del equipo, pendiente de validar por un agrónomo"

_RANK = {"favorable": 2, "moderate": 1, "unfavorable": 0}
_PENDING = "Este criterio todavía no se calcula en esta versión del motor"


@dataclass(frozen=True)
class HealthRule:
    """Una regla `kind = health` de `rotation_rules`, con su fuente (R8)."""

    rule_id: str
    criterion: str
    condition_type: str
    params: Mapping[str, Any]
    levels: Mapping[str, Any]
    reason_template: str
    source_id: str


@dataclass(frozen=True)
class SoilCrop:
    """Lo que `soil_health` lee de la ficha de un cultivo, abono verde o descanso."""

    crop_id: str
    kind: str
    family: str | None
    secondary_families: tuple[str, ...]
    fixes_nitrogen: bool | None


@dataclass(frozen=True)
class Criterion:
    status: str
    level: str | None
    reasons: tuple[str, ...]
    rule_ids: tuple[str, ...]
    source_ids: tuple[str, ...]


def level_from_cuts(value: float, levels: Mapping[str, Any], more_is_better: bool = True) -> str:
    """`favorable` si el valor llega al corte favorable; si no, `moderate` si llega al moderado; si no, `unfavorable`.
    Con `more_is_better=False` los cortes son máximos. Con `moderate == favorable` no hay franja intermedia."""
    favorable, moderate = levels["favorable"], levels.get("moderate", levels["favorable"])
    reaches = (lambda cut: value >= cut) if more_is_better else (lambda cut: value <= cut)
    if reaches(favorable):
        return "favorable"
    return "moderate" if reaches(moderate) else "unfavorable"


def _text(reason: str, rule: HealthRule) -> str:
    """La razón de una regla del equipo termina con la nota de «criterio del equipo» (R8, decisión 16)."""
    return f"{reason}. {TEAM_NOTE}" if rule.source_id == TEAM_CRITERION else reason


def _no_data(reason: str, rule: HealthRule | None) -> Criterion:
    """`insufficient_data` sin nivel (R1). Con regla lleva sus ids y fuente; sin regla, vacíos (R8)."""
    if rule is None:
        return Criterion("insufficient_data", None, (reason,), (), ())
    return Criterion("insufficient_data", None, (_text(reason, rule),), (rule.rule_id,), (rule.source_id,))


def _available(level: str, reason: str, rule: HealthRule) -> Criterion:
    return Criterion("available", level, (_text(reason, rule),), (rule.rule_id,), (rule.source_id,))


def _nitrogen(sequence: Sequence[str], crops: Mapping[str, SoilCrop], rule: HealthRule) -> Criterion:
    """Ciclos con `fixes_nitrogen`. Un dato nulo sin conteo suficiente es `insufficient_data` (supuesto 5)."""
    flags = [c.fixes_nitrogen if (c := crops.get(crop_id)) else None for crop_id in sequence]
    count = flags.count(True)
    if None in flags and level_from_cuts(count, rule.levels) != "favorable":
        return _no_data("Falta el dato de fijación de nitrógeno de algún cultivo de la estrategia", rule)
    return _available(level_from_cuts(count, rule.levels), rule.reason_template.format(count=count), rule)


def _families(crop_id: str, crops: Mapping[str, SoilCrop]) -> set[str]:
    crop = crops.get(crop_id)
    if crop is None:
        return set()  # el descanso y lo que no está en el catálogo no aportan familia
    return {f for f in (crop.family, *crop.secondary_families) if f}


def _pest_break(sequence: Sequence[str], previous: Sequence[str], crops: Mapping[str, SoilCrop], rule: HealthRule) -> Criterion:
    """Peor vuelta de `params["family"]` en los ciclos de la estrategia, buscando hacia atrás su aparición anterior
    (en la estrategia o en los `min_cycles + 1` cultivos anteriores más recientes). Sin vuelta, `favorable`."""
    family = rule.params.get("family")
    if not family:
        return _no_data("La regla no dice la familia que debe esperar", rule)
    kept = list(previous[: int(rule.params.get("min_cycles", 0)) + 1])
    timeline = [*reversed(kept), *sequence]
    start = len(kept)
    returns = []  # (rango del nivel, ciclos entre apariciones, posición)
    for i in range(start, len(timeline)):
        if family not in _families(timeline[i], crops):
            continue
        back = next((j for j in range(i - 1, -1, -1) if family in _families(timeline[j], crops)), None)
        if back is not None:
            cycles = i - back - 1
            returns.append((_RANK[level_from_cuts(cycles, rule.levels)], cycles, i))
    if not returns:
        return _available("favorable", f"La familia {family} no vuelve al terreno en los ciclos revisados", rule)
    rank, cycles, _ = min(returns)
    level = next(name for name, value in _RANK.items() if value == rank)
    return _available(level, rule.reason_template.format(family=family, cycles=cycles), rule)


def soil_health(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    previous_crop_ids: Sequence[str],
    rules: Sequence[HealthRule],
    soil: object | None = None,
    slope: object | None = None,
    cycle_days: Sequence[int | None] | None = None,
    gap_days: Sequence[int | None] | None = None,
) -> dict[str, Criterion]:
    """Los cinco criterios de una estrategia. `sequence` es el `crop_id` de cada ciclo, en orden; `previous_crop_ids`
    va del más reciente al más antiguo. Sin regla con fuente para un criterio, `insufficient_data` con ids vacíos."""
    by_criterion: dict[str, HealthRule] = {}
    for rule in sorted(rules, key=lambda r: r.rule_id):
        if rule.source_id:
            by_criterion.setdefault(rule.criterion, rule)
    result: dict[str, Criterion] = {}
    for name in SOIL_CRITERIA:
        rule = by_criterion.get(name)
        if rule is None:
            result[name] = _no_data("No hay una regla con fuente para este criterio", None)
        elif name == "nitrogen":
            result[name] = _nitrogen(sequence, crops, rule)
        elif name == "pest_break":
            result[name] = _pest_break(sequence, previous_crop_ids, crops, rule)
        else:
            result[name] = _no_data(_PENDING, rule)
    return result
