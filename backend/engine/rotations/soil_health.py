"""HU-212, PR B: forma de los cinco criterios de `soil_health` y los cálculos de `nitrogen` y `pest_break` (R3, R8).

Compara estrategias según reglas con fuente: no predice cuánto mejora el suelo (decisión 4). Un dato o una regla que
falta nunca da un nivel (R1, R8). Los cinco criterios están calculados; `soil_score` resume los niveles en 0 a 100 para
el criterio `soil` del ranking. Función pura y determinista (R4, R6).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from backend.engine.signal_score import round_half_up

SOIL_CRITERIA = ("nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion")
TEAM_CRITERION = "criterio_equipo_2026"
TEAM_NOTE = "criterio del equipo, pendiente de validar por un agrónomo"

_RANK = {"favorable": 2, "moderate": 1, "unfavorable": 0}
DAYS_PER_MONTH = 30.4
_POINTS = {"favorable": 100, "moderate": 50, "unfavorable": 0}


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
class SoilCarbon:
    """Carbono orgánico estimado del suelo (SoilGrids, 250 m) y su rango p05 a p95, en g/kg (R10)."""

    soc_g_kg: float | None
    soc_p05: float | None
    soc_p95: float | None
    source_id: str


@dataclass(frozen=True)
class SlopeInfo:
    """Pendiente estimada del terreno (NASADEM), del lote o del municipio: un dato de la zona, no medido (R10)."""

    slope_pct: float | None
    source_id: str
    basis: str  # `lot` o `municipality`


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


def _dec(value: float) -> str:
    """Un decimal con coma decimal, como se muestran los números de las razones."""
    return f"{value:.1f}".replace(".", ",")


def _organic_carbon(sequence: Sequence[str], crops: Mapping[str, SoilCrop], soil: SoilCarbon | None, rule: HealthRule) -> Criterion:
    """Ciclos de abono verde o descanso (los residuos no cuentan) contra los cortes del carbono bajo o normal."""
    if soil is None or soil.soc_g_kg is None:
        return _no_data("Falta el carbono orgánico del suelo de la zona", rule)
    count = sum(1 for c in sequence if (crop := crops.get(c)) and crop.kind in ("cover", "fallow"))
    low = soil.soc_g_kg < rule.params["soc_low_g_kg"]
    level = level_from_cuts(count, rule.levels["low" if low else "normal"])
    soc_range = f"{_dec(soil.soc_p05)} a {_dec(soil.soc_p95)}" if soil.soc_p05 is not None and soil.soc_p95 is not None else "sin rango"
    reason = rule.reason_template.format(count=count, soc_level="bajo" if low else "normal", soc_range=soc_range)
    return Criterion("available", level, (_text(reason, rule),), (rule.rule_id,), (rule.source_id, soil.source_id))


def _day_counts(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    cycle_days: Sequence[int | None] | None,
    gap_days: Sequence[int | None] | None,
) -> tuple[int, int, int] | None:
    """(días cubiertos, días de descanso, días totales con huecos), o `None` si falta la duración de algún ciclo."""
    if not cycle_days or len(cycle_days) != len(sequence) or None in cycle_days:
        return None
    pairs = [(crops.get(c), d) for c, d in zip(sequence, cycle_days, strict=True)]
    covered = sum(d for crop, d in pairs if crop and crop.kind in ("crop", "cover"))
    fallow = sum(d for crop, d in pairs if crop and crop.kind == "fallow")
    return covered, fallow, sum(cycle_days) + sum(g or 0 for g in gap_days or ())


def _soil_cover(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    cycle_days: Sequence[int | None] | None,
    gap_days: Sequence[int | None] | None,
    rule: HealthRule,
) -> Criterion:
    """Porcentaje del tiempo con cultivo o abono verde; el descanso y los huecos son suelo descubierto."""
    counts = _day_counts(sequence, crops, cycle_days, gap_days)
    if counts is None:
        return _no_data("Falta la duración de algún ciclo de la estrategia", rule)
    covered, _, total = counts
    if total <= 0:
        return _no_data("La estrategia no tiene días que medir", rule)
    pct = covered / total * 100  # sin redondear: el nivel no depende de cómo se muestra
    return _available(level_from_cuts(pct, rule.levels), rule.reason_template.format(pct=_dec(pct)), rule)


def _erosion(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    slope: SlopeInfo | None,
    cycle_days: Sequence[int | None] | None,
    gap_days: Sequence[int | None] | None,
    rule: HealthRule,
) -> Criterion:
    """Con pendiente desde `slope_pct_from`, los meses de descanso y huecos pasan por los cortes máximos; con menos
    pendiente el suelo descubierto no cuenta y no hacen falta las duraciones."""
    if slope is None or slope.slope_pct is None:
        return _no_data("Falta la pendiente del terreno de la zona", rule)
    sources = (rule.source_id, slope.source_id)
    cut = rule.params["slope_pct_from"]
    if slope.slope_pct < cut:
        reason = (
            f"Pendiente estimada del terreno: {_dec(slope.slope_pct)} % (dato de la zona, no medido en su lote), por debajo "
            f"de {cut} %: con esa pendiente el suelo descubierto no se cuenta para la erosión"
        )
        return Criterion("available", "favorable", (_text(reason, rule),), (rule.rule_id,), sources)
    counts = _day_counts(sequence, crops, cycle_days, gap_days)
    if counts is None:
        return _no_data("Falta la duración de algún ciclo de la estrategia", rule)
    months = (counts[1] + counts[2] - sum(cycle_days)) / DAYS_PER_MONTH  # descanso + huecos, sin redondear
    reason = rule.reason_template.format(slope=_dec(slope.slope_pct), months=_dec(months))
    return Criterion(
        "available", level_from_cuts(months, rule.levels, more_is_better=False), (_text(reason, rule),), (rule.rule_id,), sources
    )


def soil_score(criteria: Mapping[str, Criterion]) -> int | None:
    """Puntaje 0 a 100 del criterio `soil` del ranking: promedio de los criterios con nivel (100, 50 o 0), mitad hacia
    arriba. Sin ninguno con nivel, `None` (R1)."""
    points = [_POINTS[c.level] for c in criteria.values() if c.level in _POINTS]
    return round_half_up(sum(points) / len(points)) if points else None


def soil_health(
    sequence: Sequence[str],
    crops: Mapping[str, SoilCrop],
    previous_crop_ids: Sequence[str],
    rules: Sequence[HealthRule],
    soil: SoilCarbon | None = None,
    slope: SlopeInfo | None = None,
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
        elif name == "organic_carbon":
            result[name] = _organic_carbon(sequence, crops, soil, rule)
        elif name == "soil_cover":
            result[name] = _soil_cover(sequence, crops, cycle_days, gap_days, rule)
        else:
            result[name] = _erosion(sequence, crops, slope, cycle_days, gap_days, rule)
    return result
