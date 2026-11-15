"""El orden de las estrategias por las prioridades de la rotación (HU-082; specs/01-reglas.md, «Estrategias de
rotación», «Cómo se ordenan»; decisión 15).

Cuatro criterios de 0 a 100, cada uno con su regla:

- `water`: el promedio de la calificación de la señal `water` de los ciclos con diagnóstico;
- `soil`: los cinco criterios de salud del suelo (HU-212, `soil_score`);
- `income`: el promedio, ciclo por ciclo, de la calificación de `supply` y de `market` que tengan dato; un abono verde o
  un descanso no deja cosecha y vale 0. Es el único lugar donde la oferta entra a las estrategias (decisión 12);
- `risk`: el factor que más limita entre todos los ciclos, el menor `limiting_score` (ley del mínimo). Es la calificación
  del `limiting_signal` que muestra cada ciclo (el de la luz `light`, con los pesos de quien consulta): un ciclo
  `not_evaluable` no muestra factor limitante y no cuenta.

Un ciclo sin el dato no cuenta y, en `water` y `risk`, se dice; un criterio sin ningún ciclo con dato no califica, no
entra al total y va a las limitaciones (R1). `total_score` es el promedio de los criterios que califican ponderado por
las prioridades de la rotación (un entero de 0 a 5 por criterio); con todas esas prioridades en 0 no hay total.

Lo que se muestra es lo que decide: los criterios se redondean (mitad hacia arriba) y el total y el orden se calculan con
esos mismos enteros. Hasta 10 estrategias; empate de `total_score`: gana la de `risk` más alto y después la de
`crop_ids` primero en orden alfabético (R4). Solo ordena las que ya pasaron el filtro (HU-081): nunca rescata una
excluida. Python puro, sin leer archivos (R6).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from backend.engine.rotations.candidates import FALLOW
from backend.engine.rotations.soil_health import Criterion, soil_score
from backend.engine.signal_score import AVAILABLE, SignalScore, round_half_up, weight_of

CRITERIA = ("water", "soil", "income", "risk")
CROP, COVER = "crop", "cover"
LIMIT = 10

# Qué se dice cuando un criterio no califica (R1, R5).
NO_CRITERION = {
    "water": "Ningún ciclo tiene calificación de agua: el criterio de agua no califica y no entra al total",
    "soil": "Ningún criterio de salud del suelo tiene dato: el criterio de suelo no califica y no entra al total",
    "income": "Ningún cultivo tiene dato de oferta ni de mercado: el criterio de ingreso no califica y no entra al total",
    "risk": "Ningún ciclo tiene un factor limitante calificado: el criterio de riesgo no califica y no entra al total",
}
NO_TOTAL = "Todas las prioridades de los criterios que califican están en 0: la estrategia no tiene total y va al final"


def _missing_cycle(cycle: int, what: str) -> str:
    return f"El ciclo {cycle} no tiene {what}: no cuenta en ese criterio"


@dataclass(frozen=True)
class CycleScores:
    """Lo que el orden lee de un ciclo: su `kind` (`crop`, `cover` o `fallow`), las calificaciones de sus señales y el
    factor que más limita de su luz `light`, del mismo diagnóstico de `/diagnostics` (HU-213). `signals` es nulo sin
    diagnóstico (un descanso o un cultivo no apto); `limiting_signal`, también con la luz `not_evaluable`."""

    kind: str
    signals: Mapping[str, SignalScore] | None
    limiting_signal: str | None = None


@dataclass(frozen=True)
class StrategyScores:
    """Los cuatro criterios (nulo el que no califica), el total y lo que se dice de los datos que faltan."""

    crop_ids: tuple[str, ...]
    scores: Mapping[str, int | None]
    total_score: int | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class RankedStrategy(StrategyScores):
    rank: int


def _score(signal: SignalScore | None) -> int | None:
    """La calificación de una señal que califica; nula sin datos, si no aplica o sin calificación (R1)."""
    if signal is None or signal.status != AVAILABLE:
        return None
    return signal.score


def limiting_score(cycle: CycleScores) -> int | None:
    """La calificación del factor que más limita que muestra el ciclo; nula sin diagnóstico o sin factor limitante."""
    if cycle.signals is None or cycle.limiting_signal is None:
        return None
    return _score(cycle.signals.get(cycle.limiting_signal))


def _mean(values: Sequence[float]) -> int | None:
    return round_half_up(sum(values) / len(values)) if values else None


def criteria(
    crop_ids: Sequence[str],
    cycles: Sequence[CycleScores],
    soil_health: Mapping[str, Criterion],
) -> tuple[dict[str, int | None], tuple[str, ...]]:
    """Los cuatro criterios de una estrategia y sus limitaciones, en el orden de `CRITERIA` (R4)."""
    if len(crop_ids) != len(cycles):
        raise ValueError(f"La estrategia {tuple(crop_ids)} tiene {len(crop_ids)} ciclos y {len(cycles)} calificaciones")
    limitations: list[str] = []
    water: list[int] = []
    risk: list[int] = []
    income: list[float] = []
    crop_with_income = False
    for number, cycle in enumerate(cycles, start=1):
        if cycle.signals is None and cycle.kind != FALLOW:
            # Un cultivo o abono verde no apto no tiene señales: no cuenta en `water` ni en `risk` y se dice (R1).
            limitations.append(_missing_cycle(number, "diagnóstico"))
        if cycle.signals is not None:
            score = _score(cycle.signals.get("water"))
            if score is None:
                limitations.append(_missing_cycle(number, "calificación de agua"))
            else:
                water.append(score)
            lowest = limiting_score(cycle)
            if lowest is None:
                limitations.append(_missing_cycle(number, "un factor limitante calificado"))
            else:
                risk.append(lowest)
        if cycle.kind == CROP:
            market = [s for s in (_score((cycle.signals or {}).get(n)) for n in ("supply", "market")) if s is not None]
            if market:
                income.append(sum(market) / len(market))
                crop_with_income = True
            else:
                limitations.append(_missing_cycle(number, "calificación de oferta ni de mercado"))
        elif cycle.kind in (COVER, FALLOW):
            # Un abono verde o un descanso no deja cosecha: vale 0 en el ingreso.
            income.append(0)
    result = {
        "water": _mean(water),
        "soil": soil_score(soil_health),
        "income": _mean(income) if crop_with_income else None,
        "risk": min(risk) if risk else None,
    }
    limitations.extend(NO_CRITERION[name] for name in CRITERIA if result[name] is None)
    return result, tuple(dict.fromkeys(limitations))


def total_score(scores: Mapping[str, int | None], priorities: Mapping[str, float | None]) -> int | None:
    """El promedio de los criterios que califican, ponderado por las prioridades de la rotación. Nulo si ninguno
    califica o si todos los que califican tienen prioridad 0."""
    rated = [(score, weight_of(priorities, name)) for name, score in scores.items() if score is not None]
    weight = sum(w for _, w in rated)
    if weight == 0:
        return None
    return round_half_up(sum(score * w for score, w in rated) / weight)


def score_strategy(
    crop_ids: Sequence[str],
    cycles: Sequence[CycleScores],
    soil_health: Mapping[str, Criterion],
    priorities: Mapping[str, float | None],
) -> StrategyScores:
    """Los criterios y el total de una estrategia. También sirve para la rotación actual (HU-223), que no entra al orden."""
    scores, limitations = criteria(crop_ids, cycles, soil_health)
    total = total_score(scores, priorities)
    if total is None and any(score is not None for score in scores.values()):
        limitations = (*limitations, NO_TOTAL)
    return StrategyScores(tuple(crop_ids), scores, total, limitations)


def _order_key(strategy: StrategyScores) -> tuple:
    """Total más alto primero (sin total, al final); empate: `risk` más alto (sin `risk`, después) y `crop_ids` (R4)."""
    total, risk = strategy.total_score, strategy.scores.get("risk")
    return (total is None, -(total or 0), risk is None, -(risk or 0), strategy.crop_ids)


def rank_strategies(strategies: Sequence[StrategyScores], limit: int = LIMIT) -> tuple[RankedStrategy, ...]:
    """Las estrategias en orden, con su `rank` desde 1, cortadas en `limit`. Misma entrada, mismo orden (R4)."""
    ordered = sorted(strategies, key=_order_key)[:limit]
    return tuple(
        RankedStrategy(s.crop_ids, s.scores, s.total_score, s.limitations, rank=number) for number, s in enumerate(ordered, start=1)
    )
