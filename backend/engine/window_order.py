"""El orden de las ventanas de siembra: primero el factor que más limita, después las prioridades (HU-192;
specs/01-reglas.md, «Orden de las ventanas» y «Las prioridades del agricultor»).

Funciones puras (R6): reciben las calificaciones de cada ventana, ya calculadas con el mismo cálculo del diagnóstico
(`backend/engine/signal_score.py`), y los pesos de quien consulta (o los de AgroSense). No califican ni redondean
señales por su cuenta, no leen archivos ni el reloj.

Para cada ventana, entre las señales que **cuentan** (`counts`: peso mayor que 0, o riesgo grave de clima) y
**califican** (`status = available` con calificación):

- `limiting_signal` y `limiting_score`: la señal más baja (ley del mínimo). En un empate, la primera en el orden de
  las señales de la ventana.
- `weighted_score`: el promedio de sus calificaciones ponderado por los pesos, redondeado hacia arriba desde la mitad.
  Nulo si la suma de sus pesos es 0 (solo cuentan riesgos graves de clima con peso 0): no hay prioridades que
  promediar.
- `high_risk`: alguna es crítica (R2).

Una señal sin datos o que no aplica, o `available` sin calificación, no califica: no entra al mínimo ni al promedio
(R1). Un peso que falta vale 0 y un peso negativo se trata como 0, para `counts` y para el promedio: un riesgo grave
de clima cuenta igual. El motor no valida el rango de 0 a 5 (lo hace la API con 422): un peso mayor que 5 se usa tal
cual en el promedio.
Sin ninguna señal que cuente y califique, los tres valores son nulos y `high_risk` es falso: no hay evidencia de
riesgo, solo falta de datos.

El orden (R2, R4):

1. Las ventanas con factor limitante y sin alto riesgo; después las de alto riesgo (traen al menos información real);
   al final, las que no tienen ninguna señal que cuente y califique, por fecha.
2. En los dos primeros grupos: la decena del factor limitante, de mayor a menor (60 a 69 es una decena; la alta es
   90 a 100: un factor limitante de 100 no forma una decena propia); dentro de la decena, el promedio ponderado de
   mayor a menor, con los promedios nulos al final de su decena.
3. Empate: la ventana más temprana.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from backend.engine.signal_score import AVAILABLE, SignalScore, counts, round_half_up

# Grupos del orden: primero las calificadas sin alto riesgo, después las de alto riesgo, al final las sin calificar.
_RANKED, _HIGH_RISK, _UNRATED = 0, 1, 2


@dataclass(frozen=True)
class WindowSignals:
    """Una ventana de siembra con las calificaciones de sus señales (las mismas que daría su diagnóstico)."""

    sowing_start: date
    harvest_estimate: date
    signals: Mapping[str, SignalScore]


@dataclass(frozen=True)
class RankedWindow:
    """Una ventana con su factor limitante, su promedio ponderado y si es de alto riesgo. Los tres valores son nulos
    cuando ninguna señal cuenta y califica (R1)."""

    sowing_start: date
    harvest_estimate: date
    limiting_signal: str | None
    limiting_score: int | None
    weighted_score: int | None
    high_risk: bool


def rank_window(window: WindowSignals, weights: Mapping[str, float]) -> RankedWindow:
    """El factor limitante, el promedio ponderado y el alto riesgo de una ventana con esos pesos."""
    rated = []
    for name, signal in window.signals.items():
        weight = _weight(weights, name)
        if signal.status == AVAILABLE and signal.score is not None and counts(name, weight, signal.critical):
            rated.append((name, signal, weight))
    if not rated:
        return RankedWindow(window.sowing_start, window.harvest_estimate, None, None, None, False)

    limiting_name, limiting, _ = min(rated, key=lambda item: item[1].score)
    total_weight = sum(weight for _, _, weight in rated)
    weighted = None if total_weight <= 0 else round_half_up(sum(signal.score * weight for _, signal, weight in rated) / total_weight)
    return RankedWindow(
        sowing_start=window.sowing_start,
        harvest_estimate=window.harvest_estimate,
        limiting_signal=limiting_name,
        limiting_score=limiting.score,
        weighted_score=weighted,
        high_risk=any(signal.critical for _, signal, _ in rated),
    )


def order_windows(windows: Iterable[WindowSignals], weights: Mapping[str, float]) -> tuple[RankedWindow, ...]:
    """Las ventanas calificadas y ordenadas: la posición en la tupla es su puesto. Mismas ventanas y pesos, mismo
    orden, sin importar el orden de entrada (R4)."""
    return tuple(sorted((rank_window(window, weights) for window in windows), key=_order_key))


def best_windows(ranked: Sequence[RankedWindow], limit: int = 3) -> tuple[RankedWindow, ...]:
    """Las mejores ventanas: hasta `limit`, en el orden recibido, sin las de alto riesgo ni las que no tienen
    calificación. Filtra explícitamente, no confía en el orden: una ventana de alto riesgo nunca entra (R2), y no se
    recomienda lo que no se puede evaluar (R1)."""
    return tuple(window for window in ranked if not window.high_risk and window.limiting_score is not None)[:limit]


def limiting_decade(limiting_score: int) -> int:
    """La decena del factor limitante, de 0 a 9 (60 a 69 es la 6). La alta es 90 a 100, una sola: un factor
    limitante de 100 no forma una decena propia."""
    return min(limiting_score // 10, 9)


def _weight(weights: Mapping[str, float], name: str) -> float:
    """El peso de una señal: 0 si falta o es negativo."""
    return max(weights.get(name, 0), 0)


def _order_key(window: RankedWindow) -> tuple:
    """La llave del orden: grupo, decena del factor limitante (de mayor a menor), promedio ponderado (de mayor a
    menor, los nulos al final de su decena) y, en empate, la ventana más temprana."""
    if window.limiting_score is None:
        return (_UNRATED, 0, False, 0, window.sowing_start)
    group = _HIGH_RISK if window.high_risk else _RANKED
    weighted = window.weighted_score
    return (group, -limiting_decade(window.limiting_score), weighted is None, -(weighted or 0), window.sowing_start)
