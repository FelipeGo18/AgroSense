"""Las razones del orden de una estrategia sugerida (HU-083; specs/01-reglas.md, «Estrategias de rotación»).

Plantillas fijas. Cada razón cita un criterio, una señal o una regla que el motor ya evaluó y con el mismo número que
muestra la respuesta (R5): ninguna dice cuánto va a mejorar el suelo ni cuánto se va a cosechar (decisión 4). En orden:

1. **Lo que más suma al total:** el criterio que califica con la mayor calificación por su prioridad. Sin total, por
   qué no lo tiene y que va al final.
2. **Frente a la rotación actual** (si hay `vs_current`, HU-223): el criterio en que más gana o, si no gana en ninguno,
   en el que más pierde, con la regla de la que sale ese criterio.
3. **Salud del suelo** (si algún criterio de HU-212 tiene nivel): el primero `favorable` en el orden de
   `SOIL_CRITERIA` o, sin ninguno, el primero con nivel, con su razón tal como la da `soil_health` (si su regla es del
   equipo, con «criterio del equipo», R8; la fuente va en `source_ids` de ese criterio, no en el texto).
4. **El factor que más limita:** la señal y el ciclo de `risk`, con su calificación.

Si con eso quedan menos de dos, se agrega que ninguna regla de rotación del catálogo la descarta, que es cierto de toda
estrategia sugerida (pasó el filtro de HU-081). Una razón cuyo dato falta no se escribe: no se rellena (R1). Así
salen siempre de 2 a 4 razones, como pide el contrato. Python puro (R6).
"""

from collections.abc import Mapping, Sequence

from backend.engine.rotations.ranking import CRITERIA, CycleScores, StrategyScores, limiting_score
from backend.engine.rotations.soil_health import SOIL_CRITERIA, Criterion
from backend.engine.signal_score import AVAILABLE, weight_of
from backend.engine.traffic_light import SIGNAL_NAMES_ES

MAX_REASONS = 4

CRITERION_NAMES = {"water": "agua", "soil": "suelo", "income": "ingreso", "risk": "riesgo"}
# De dónde sale cada criterio (specs/01-reglas.md, «Cómo se ordenan»).
CRITERION_RULES = {
    "water": "el promedio de la calificación de agua de sus ciclos",
    "soil": "el promedio de los cinco criterios de salud del suelo",
    "income": "el promedio de la oferta y el mercado de sus ciclos, con el abono verde y el descanso en 0",
    "risk": "el factor que más limita entre sus ciclos",
}
SOIL_CRITERION_NAMES = {
    "nitrogen": "nitrógeno",
    "organic_carbon": "carbono orgánico",
    "soil_cover": "suelo cubierto",
    "pest_break": "corte de plagas",
    "erosion": "erosión",
}
LEVEL_NAMES = {"favorable": "favorable", "moderate": "moderado", "unfavorable": "desfavorable"}
PASSES_RULES = "Ninguna regla de rotación del catálogo la descarta"
NO_TOTAL_WEIGHTS = "Los criterios que califican tienen prioridad 0: no tiene total y va al final del orden"
NO_TOTAL_DATA = "Ningún criterio califica con los datos que hay: no tiene total y va al final del orden"


def _top_criterion(scores: StrategyScores, priorities: Mapping[str, float | None]) -> str | None:
    if scores.total_score is None:
        if any(score is not None for score in scores.scores.values()):
            return NO_TOTAL_WEIGHTS
        return NO_TOTAL_DATA
    rated = [(score * weight_of(priorities, name), name) for name in CRITERIA if (score := scores.scores.get(name)) is not None]
    rated = [(value, name) for value, name in rated if weight_of(priorities, name) > 0]
    if not rated:
        return None
    best = max(value for value, _ in rated)
    name = next(name for value, name in rated if value == best)  # empate: el primero en `CRITERIA` (R4)
    weight = weight_of(priorities, name)
    weight_text = f"{weight:g}".replace(".", ",")
    score = scores.scores[name]
    return f"Lo que más suma a su total es el criterio de {CRITERION_NAMES[name]}: {score} de 100, con prioridad {weight_text} de 5"


def _versus_current(vs_current: Mapping[str, int | None] | None) -> str | None:
    if not vs_current:
        return None
    rated = [(diff, name) for name in CRITERIA if (diff := vs_current.get(name)) is not None]
    if not rated:
        return None
    best = max(diff for diff, _ in rated)
    if best > 0:
        name = next(name for diff, name in rated if diff == best)
        change = f"sale {best} {'punto' if best == 1 else 'puntos'} mejor"
    else:
        worst = min(diff for diff, _ in rated)
        if worst == 0:
            names = ", ".join(CRITERION_NAMES[name] for _, name in rated)
            return f"Frente a su rotación actual queda igual en los criterios que se pueden comparar ({names})"
        name = next(name for diff, name in rated if diff == worst)
        change = f"sale {-worst} {'punto' if worst == -1 else 'puntos'} peor"
    return f"Frente a su rotación actual {change} en {CRITERION_NAMES[name]}: ese criterio es {CRITERION_RULES[name]}"


def _soil(soil_health: Mapping[str, Criterion]) -> str | None:
    rated = [(name, c) for name in SOIL_CRITERIA if (c := soil_health.get(name)) and c.status == AVAILABLE and c.level and c.reasons]
    if not rated:
        return None
    name, criterion = next(((n, c) for n, c in rated if c.level == "favorable"), rated[0])
    level = LEVEL_NAMES.get(criterion.level or "", criterion.level)
    return f"Salud del suelo, {SOIL_CRITERION_NAMES[name]} {level}: {criterion.reasons[0]}"


def _limiting(scores: StrategyScores, cycles: Sequence[CycleScores]) -> str | None:
    risk = scores.scores.get("risk")
    if risk is None:
        return None
    # El primer ciclo con la calificación de `risk` (R4); es la misma cuenta de `criteria`.
    found = next(((n, c) for n, c in enumerate(cycles, start=1) if limiting_score(c) == risk), None)
    if found is None:
        raise ValueError(f"Ningún ciclo de {scores.crop_ids} tiene el riesgo {risk}: los ciclos no son los de sus criterios")
    number, cycle = found
    signal = cycle.limiting_signal or ""
    return f"El factor que más limita entre sus ciclos es {SIGNAL_NAMES_ES.get(signal, signal)} del ciclo {number}: {risk} de 100"


def strategy_reasons(
    scores: StrategyScores,
    priorities: Mapping[str, float | None],
    cycles: Sequence[CycleScores],
    soil_health: Mapping[str, Criterion],
    vs_current: Mapping[str, int | None] | None = None,
) -> tuple[str, ...]:
    """Las razones de una estrategia sugerida, de 2 a 4, con los mismos `cycles` y `soil_health` con que se calcularon
    sus `scores` (HU-082) y, si hay rotación actual, su `vs_current` (HU-223)."""
    reasons = [
        text
        for text in (
            _top_criterion(scores, priorities),
            _versus_current(vs_current),
            _soil(soil_health),
            _limiting(scores, cycles),
        )
        if text is not None
    ]
    if len(reasons) < 2:
        reasons.append(PASSES_RULES)
    return tuple(reasons[:MAX_REASONS])
