"""Las razones del orden de una estrategia (HU-083; specs/01-reglas.md, «Estrategias de rotación»).

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
estrategia sugerida (pasó el filtro de HU-081). La rotación actual (decisión 14) empieza por «Es la rotación que usted
viene haciendo» y nunca lleva esa frase: no se descarta aunque viole una regla, y eso va en `issues`. Una razón cuyo
dato falta no se escribe: no se rellena (R1). Así salen siempre de 2 a 4 razones, como pide el contrato.

Las calificaciones se dicen como calificaciones («califica 71 de 100»), y en `risk` se aclara que más alto es menos
riesgo, para que no se lean al revés (revisión de Haider, PR #150). Python puro (R6).
"""

from collections.abc import Mapping, Sequence

from backend.engine.rotations.ranking import CRITERIA, CycleScores, StrategyScores, cycle_limiting
from backend.engine.rotations.soil_health import SOIL_CRITERIA, Criterion
from backend.engine.signal_score import AVAILABLE, weight_of
from backend.engine.traffic_light import SIGNAL_NAMES_ES

MAX_REASONS = 4

CRITERION_NAMES = {"water": "agua", "soil": "suelo", "income": "ingreso", "risk": "riesgo"}
# De dónde sale cada criterio (specs/01-reglas.md, «Cómo se ordenan»).
CRITERION_RULES = {
    "water": "el promedio de la calificación de agua de sus ciclos",
    "soil": "el promedio de los cinco criterios de salud del suelo",
    "income": (
        "el porcentaje de años en que el mes de cosecha de sus ciclos tuvo mejor precio que el resto de su año, con el abono "
        "verde y el descanso en 0"
    ),
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
CURRENT_REASON = "Es la rotación que usted viene haciendo: las demás se comparan contra ella"
SUGGESTED, CURRENT = "suggested", "current"
# En `risk` la calificación es el factor que más limita: más alta es menos riesgo, y se dice para que no se lea al revés.
RISK_SCALE = " (en riesgo, más alto es menos riesgo)"
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
    scale = RISK_SCALE if name == "risk" else ""
    return (
        f"Lo que más suma a su total es el criterio de {CRITERION_NAMES[name]}, que califica {score} de 100{scale}, "
        f"con prioridad {weight_text} de 5"
    )


def _versus_current(vs_current: Mapping[str, int | None] | None) -> str | None:
    if not vs_current:
        return None
    rated = [(diff, name) for name in CRITERIA if (diff := vs_current.get(name)) is not None]
    if not rated:
        return None
    # Es una comparación de calificaciones, no un pronóstico (decisión 4): «califica N puntos más», nunca «sale mejor».
    best = max(diff for diff, _ in rated)
    if best > 0:
        name = next(name for diff, name in rated if diff == best)
        change = f"{best} {'punto' if best == 1 else 'puntos'} más"
    else:
        worst = min(diff for diff, _ in rated)
        if worst == 0:
            names = ", ".join(CRITERION_NAMES[name] for _, name in rated)
            return f"Sus criterios que se pueden comparar ({names}) califican igual que los de su rotación actual"
        name = next(name for diff, name in rated if diff == worst)
        change = f"{-worst} {'punto' if worst == -1 else 'puntos'} menos"
    scale = RISK_SCALE if name == "risk" else ""
    return (
        f"Su criterio de {CRITERION_NAMES[name]} califica {change} que el de su rotación actual{scale}: "
        f"ese criterio es {CRITERION_RULES[name]}"
    )


def _soil(soil_health: Mapping[str, Criterion]) -> str | None:
    rated = [(name, c) for name in SOIL_CRITERIA if (c := soil_health.get(name)) and c.status == AVAILABLE and c.level and c.reasons]
    if not rated:
        return None
    name, criterion = next(((n, c) for n, c in rated if c.level == "favorable"), rated[0])
    level = LEVEL_NAMES.get(criterion.level or "", criterion.level)
    return f"Salud del suelo, {SOIL_CRITERION_NAMES[name]} {level}: {criterion.reasons[0]}"


def _limiting(scores: StrategyScores, cycles: Sequence[CycleScores], signal_weights: Mapping[str, float | None]) -> str | None:
    risk = scores.scores.get("risk")
    if risk is None:
        return None
    # El primer ciclo con la calificación de `risk` (R4); es la misma cuenta de `criteria` (`cycle_limiting`).
    lowest = [(n, found) for n, c in enumerate(cycles, start=1) if (found := cycle_limiting(c, signal_weights)) and found[1] == risk]
    if not lowest:
        raise ValueError(f"Ningún ciclo de {scores.crop_ids} tiene el riesgo {risk}: los ciclos no son los de sus criterios")
    number, (signal, _) = lowest[0]
    name = SIGNAL_NAMES_ES.get(signal, signal)
    return f"El factor que más limita entre sus ciclos es {name} del ciclo {number}, que califica {risk} de 100 (100 es favorable)"


def strategy_reasons(
    scores: StrategyScores,
    priorities: Mapping[str, float | None],
    cycles: Sequence[CycleScores],
    soil_health: Mapping[str, Criterion],
    signal_weights: Mapping[str, float | None],
    vs_current: Mapping[str, int | None] | None = None,
    *,
    kind: str = SUGGESTED,
) -> tuple[str, ...]:
    """Las razones de una estrategia, de 2 a 4, con los mismos `cycles`, `soil_health` y pesos de las señales con que se
    calcularon sus `scores` (HU-082) y, en una sugerida con rotación actual, su `vs_current` (HU-223).

    `kind = current` es la rotación actual (decisión 14): empieza por `CURRENT_REASON`, no se compara con ella misma y
    nunca dice `PASSES_RULES`, que en ella puede ser falso (nunca se descarta: lo que viola va en `issues`)."""
    if kind not in (SUGGESTED, CURRENT):
        raise ValueError(f"kind desconocido: {kind!r}")
    if kind == CURRENT and vs_current is not None:
        raise ValueError("La rotación actual no tiene vs_current: es la referencia")
    reasons = [
        text
        for text in (
            CURRENT_REASON if kind == CURRENT else None,
            _top_criterion(scores, priorities),
            _versus_current(vs_current),
            _soil(soil_health),
            _limiting(scores, cycles, signal_weights),
        )
        if text is not None
    ]
    if len(reasons) < 2 and kind == SUGGESTED:
        reasons.append(PASSES_RULES)
    return tuple(reasons[:MAX_REASONS])
