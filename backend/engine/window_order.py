"""El orden de las ventanas de siembra: primero el factor que más limita, después las prioridades (HU-192;
specs/01-reglas.md, «Orden de las ventanas» y «Las prioridades del agricultor»).

Funciones puras (R6): reciben las calificaciones de cada ventana, ya calculadas con el mismo cálculo del diagnóstico
(`backend/engine/signal_score.py`), y los pesos de quien consulta (o los de AgroSense). No califican ni redondean
señales por su cuenta, no leen archivos ni el reloj.

Para cada ventana, entre las señales que **cuentan** y **califican** (`rated_signals` de `signal_score.py`, la misma
lista que usa el semáforo de HU-074):

- `limiting_signal` y `limiting_score`: la señal más baja (`limiting`, ley del mínimo).
- `weighted_score`: el promedio de sus calificaciones ponderado por sus pesos efectivos (`weight_of`), redondeado
  hacia arriba desde la mitad. Nulo si la suma de sus pesos es 0 (solo cuentan riesgos graves de clima con peso 0):
  no hay prioridades que promediar. El motor no valida el rango de 0 a 5 (lo hace la API con 422): un peso mayor
  que 5 se usa tal cual en el promedio.
- `high_risk`: alguna es desfavorable y crítica (`high_risk`, R2).

Qué cuenta, qué califica, el peso efectivo y el desempate viven en `signal_score.py`; aquí solo se promedia y se
ordena. Sin ninguna señal que cuente y califique, los tres valores son nulos y `high_risk` es falso: no hay evidencia de
riesgo, solo falta de datos.

El orden (R2, R4):

1. Las ventanas con factor limitante y sin alto riesgo; después las de alto riesgo (traen al menos información real);
   al final, las que no tienen ninguna señal que cuente y califique, por fecha.
2. En los dos primeros grupos: la decena del factor limitante, de mayor a menor (60 a 69 es una decena; la alta es
   90 a 100: un factor limitante de 100 no forma una decena propia); dentro de la decena, el promedio ponderado de
   mayor a menor, con los promedios nulos al final de su decena.
3. Con peso 4 o 5 en `market` («me importa mucho»; HU-240, decisión 17), entre la decena y el promedio ponderado va el
   precio del mes de cosecha (`harvest_price`, la historia de HU-073): primero la ventana cuyo mes estuvo más años por
   encima del promedio de su año (`years_above` / `years`, como fracción exacta), en empate la de mayor
   `seasonal_index`, y las que no tienen historia (o sin los años contados) al final de su decena. El precio nunca saca
   a una ventana de su decena ni de su grupo, así que nunca sube una de alto riesgo (R2), y no toca la luz: el mercado
   no califica. Con peso de 0 a 3 (el de AgroSense es 1) no entra. Cuenta años y no promedia el índice: un año muy caro
   sube el índice de un mes que casi siempre estuvo por debajo.
4. Empate: la ventana más temprana.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from backend.engine.market_signal import PriceHistory
from backend.engine.signal_score import SignalScore, high_risk, limiting, rated_signals, round_half_up, weight_of
from backend.engine.traffic_light import HIGH_WEIGHT

# Grupos del orden: primero las calificadas sin alto riesgo, después las de alto riesgo, al final las sin calificar.
_RANKED, _HIGH_RISK, _UNRATED = 0, 1, 2


@dataclass(frozen=True)
class WindowSignals:
    """Una ventana de siembra con las calificaciones de sus señales (las mismas que daría su diagnóstico)."""

    sowing_start: date
    harvest_estimate: date
    signals: Mapping[str, SignalScore]
    # La historia del precio del mes de cosecha (`signals.market.price_history`, HU-073), o None sin historia. Solo
    # ordena con peso 4 o 5 en `market` (HU-240).
    harvest_price: PriceHistory | None = None


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
    rated = rated_signals(window.signals, weights)
    lowest = limiting(rated)
    if lowest is None:
        return RankedWindow(window.sowing_start, window.harvest_estimate, None, None, None, False)

    limiting_name, limiting_signal = lowest
    total_weight = sum(weight for _, _, weight in rated)
    weighted = None if total_weight <= 0 else round_half_up(sum(signal.score * weight for _, signal, weight in rated) / total_weight)
    return RankedWindow(
        sowing_start=window.sowing_start,
        harvest_estimate=window.harvest_estimate,
        limiting_signal=limiting_name,
        limiting_score=limiting_signal.score,
        weighted_score=weighted,
        high_risk=high_risk(rated),
    )


def order_windows(windows: Iterable[WindowSignals], weights: Mapping[str, float]) -> tuple[RankedWindow, ...]:
    """Las ventanas calificadas y ordenadas: la posición en la tupla es su puesto. Mismas ventanas y pesos, mismo
    orden, sin importar el orden de entrada (R4)."""
    by_price = weight_of(weights, "market") >= HIGH_WEIGHT
    ranked = [(rank_window(window, weights), _price_key(window.harvest_price) if by_price else _NO_PRICE) for window in windows]
    return tuple(window for window, _ in sorted(ranked, key=lambda pair: _order_key(*pair)))


def best_windows(ranked: Sequence[RankedWindow], limit: int = 3) -> tuple[RankedWindow, ...]:
    """Las mejores ventanas: hasta `limit`, en el orden recibido, sin las de alto riesgo ni las que no tienen
    calificación. Filtra explícitamente, no confía en el orden: una ventana de alto riesgo nunca entra (R2), y no se
    recomienda lo que no se puede evaluar (R1)."""
    return tuple(window for window in ranked if not window.high_risk and window.limiting_score is not None)[:limit]


def limiting_decade(limiting_score: int) -> int:
    """La decena del factor limitante, de 0 a 9 (60 a 69 es la 6). La alta es 90 a 100, una sola: un factor
    limitante de 100 no forma una decena propia."""
    return min(limiting_score // 10, 9)


# El término del precio cuando no ordena (peso de 0 a 3): igual para todas las ventanas, así que no cambia nada.
_NO_PRICE: tuple[bool, Fraction, float] = (False, Fraction(0), 0.0)


def _price_key(history: PriceHistory | None) -> tuple[bool, Fraction, float]:
    """El término del precio en la llave (HU-240): sin historia al final; después, más años por encima primero (la
    fracción exacta, sin redondeo: R4) y, en empate, mayor `seasonal_index`."""
    if history is None or history.years_above is None or history.years <= 0:
        return (True, Fraction(0), 0.0)
    return (False, -Fraction(history.years_above, history.years), -history.seasonal_index)


def _order_key(window: RankedWindow, price: tuple[bool, Fraction, float]) -> tuple:
    """La llave del orden: grupo, decena del factor limitante (de mayor a menor), el precio del mes de cosecha (solo
    con peso 4 o 5 en `market`), promedio ponderado (de mayor a menor, los nulos al final de su decena) y, en empate,
    la ventana más temprana."""
    if window.limiting_score is None:
        return (_UNRATED, 0, *_NO_PRICE, False, 0, window.sowing_start)
    group = _HIGH_RISK if window.high_risk else _RANKED
    weighted = window.weighted_score
    return (group, -limiting_decade(window.limiting_score), *price, weighted is None, -(weighted or 0), window.sowing_start)
