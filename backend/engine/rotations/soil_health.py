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
_HISTORY_TEXT = {
    "none": "No hay cultivos anteriores del terreno: solo se revisan los ciclos de la estrategia",
    "current_rotation": "Se supuso que antes del primer ciclo el terreno siguió su rotación actual",
}
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
    """Ciclos con `fixes_nitrogen`. Un dato nulo sin conteo suficiente es `insufficient_data` (supuesto 5). El descanso no
    siembra nada: no fija nitrógeno ni es un dato que falta (como en la aptitud y el pH de HU-081)."""
    flags = [
        c.fixes_nitrogen if (c := crops.get(crop_id)) else None
        for crop_id in sequence
        if (crops.get(crop_id) is None or crops[crop_id].kind != "fallow")
    ]
    count = flags.count(True)
    if None in flags and level_from_cuts(count, rule.levels) != "favorable":
        return _no_data("Falta el dato de fijación de nitrógeno de algún cultivo de la estrategia", rule)
    return _available(level_from_cuts(count, rule.levels), rule.reason_template.format(count=count), rule)


def _families(crop_id: str, crops: Mapping[str, SoilCrop]) -> set[str]:
    crop = crops.get(crop_id)
    if crop is None:
        return set()  # el descanso y lo que no está en el catálogo no aportan familia
    return {f for f in (crop.family, *crop.secondary_families) if f}


def _pest_break_rule(
    sequence: Sequence[str], previous: Sequence[str], crops: Mapping[str, SoilCrop], rule: HealthRule
) -> tuple[str | None, str]:
    """Nivel y razón de una regla `pest_break`: la peor vuelta de `params["family"]` en los ciclos de la estrategia,
    buscando hacia atrás su aparición anterior (en la estrategia o en los `min_cycles + 1` cultivos anteriores más
    recientes). Sin vuelta, `favorable`. Sin `family`, nivel nulo (R1)."""
    family = rule.params.get("family")
    if not family:
        return None, _text(f"La regla {rule.rule_id} no dice la familia que debe esperar", rule)
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
        return "favorable", _text(f"La familia {family} no vuelve al terreno en los ciclos revisados", rule)
    rank, cycles, _ = min(returns)
    level = next(name for name, value in _RANK.items() if value == rank)
    return level, _text(rule.reason_template.format(family=family, cycles=cycles), rule)


def _pest_break(
    sequence: Sequence[str],
    previous: Sequence[str],
    crops: Mapping[str, SoilCrop],
    rules: Sequence[HealthRule],
    history_basis: str,
) -> Criterion:
    """Evalúa cada regla `pest_break` (en orden de `rule_id`); el nivel es el peor de las que se pudieron evaluar. Una
    razón por regla y, una sola vez al final, el texto de la historia si no fue declarada. Ninguna evaluable: sin nivel."""
    ordered = sorted(rules, key=lambda r: r.rule_id)
    results = [(rule, *_pest_break_rule(sequence, previous, crops, rule)) for rule in ordered]
    reasons = [reason for _, _, reason in results]
    rule_ids = tuple(sorted({r.rule_id for r in ordered}))
    source_ids = tuple(sorted({r.source_id for r in ordered}))
    ranks = [_RANK[level] for _, level, _ in results if level is not None]
    if not ranks:
        return Criterion("insufficient_data", None, tuple(reasons), rule_ids, source_ids)
    if history_basis in _HISTORY_TEXT:
        reasons.append(_HISTORY_TEXT[history_basis])
    level = next(name for name, value in _RANK.items() if value == min(ranks))
    return Criterion("available", level, tuple(reasons), rule_ids, source_ids)


def soil_health(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    previous_crop_ids: Sequence[str],
    rules: Sequence[HealthRule],
    soil: object | None = None,
    slope: object | None = None,
    cycle_days: Sequence[int | None] | None = None,
    gap_days: Sequence[int | None] | None = None,
    *,
    history_basis: str | None = None,
) -> dict[str, Criterion]:
    """Los cinco criterios de una estrategia. `sequence` es el `crop_id` de cada ciclo, en orden; `previous_crop_ids`
    va del más reciente al más antiguo. `history_basis` dice de dónde sale: `declared`, `current_rotation` o `none`; sin
    él, `declared` si hay cultivos anteriores y `none` si no. Parámetro interno del motor, no un campo del contrato.
    Sin regla con fuente para un criterio, `insufficient_data` con ids vacíos."""
    if history_basis is None:
        history_basis = "declared" if previous_crop_ids else "none"
    by_criterion: dict[str, HealthRule] = {}
    pest_rules: list[HealthRule] = []
    for rule in sorted(rules, key=lambda r: r.rule_id):
        if rule.source_id:
            if rule.criterion == "pest_break":
                pest_rules.append(rule)
            else:
                by_criterion.setdefault(rule.criterion, rule)
    result: dict[str, Criterion] = {}
    for name in SOIL_CRITERIA:
        rule = by_criterion.get(name)
        if name == "pest_break" and pest_rules:
            result[name] = _pest_break(sequence, previous_crop_ids, crops, pest_rules, history_basis)
        elif name == "pest_break" or rule is None:
            result[name] = _no_data("No hay una regla con fuente para este criterio", None)
        elif name == "nitrogen":
            result[name] = _nitrogen(sequence, crops, rule)
        else:
            result[name] = _no_data(_PENDING, rule)
    return result
