"""El diagnóstico de una ventana de siembra con todo ya leído (HU-076; specs/01-reglas.md, «Agregación del semáforo»).

Junta lo que ya decidió cada parte del motor y decide lo que queda: las dos luces, las limitaciones de la respuesta y
con qué pesos se buscan las mejores ventanas. La API (`backend/api/calculations.py`) solo valida la consulta, lee el
dataset, llama al motor y arma la respuesta (R6).

- **Las dos luces** (HU-074): `traffic_light` con los pesos de quien consulta y con los de AgroSense.
- **Las limitaciones**, sin repetir y en un orden fijo (R4): la de la temperatura del lote, la de la aptitud sin datos,
  el riego sin dato, lo que dice cada señal y las señales sin datos. El riego sin dato se dice con o sin lote (contrato,
  cuerpo de `/diagnostics`; EP-16), salvo con el cultivo no apto: sin ventana no se evaluó nada sin riego (regla 0).
- **Las mejores ventanas** se buscan cuando alguna de las dos luces da `other_window`, con los pesos de quien consulta
  si es la suya (docs/registro-de-decisiones.md, 14 de noviembre de 2026); si no, con los de AgroSense.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from backend.engine.signal_score import INSUFFICIENT_DATA, Scored, signal_scores
from backend.engine.suitability import NOT_SUITABLE
from backend.engine.traffic_light import DEFAULT, OTHER_WINDOW, TrafficLight, missing_data_limitations, traffic_light

IRRIGATION_UNKNOWN = "Sin dato de riego: se evaluó como sin riego"
# Las señales cuya razón ya dice por qué no tienen dato: el agua (la lluvia de su fuente, la ET0 o el balance hídrico),
# el suelo (sin suelo para la zona, sin el rango de pH de la ficha o sin etapas) y la oferta (que esta versión todavía
# no la evalúa, hasta HU-072). Esa razón es su limitación; no se agrega «Sin datos para la zona» encima (R5).
OWN_MISSING_REASON = ("water", "soil", "supply")


def irrigation_used(has_lot: bool, lot_irrigated: bool | None, requested: bool | None) -> bool | None:
    """El riego con que se evalúa: con lote, siempre el del lote, también si el lote no lo dice (nulo, que se evalúa
    como sin riego; contrato y EP-16); sin lote, el de la consulta. Es el que devuelve el eco de la respuesta."""
    return lot_irrigated if has_lot else requested


def evaluates_windows(suitability_level: str) -> bool:
    """Si se evalúa la ventana: no con un cultivo que no se da en la zona (regla 0 del semáforo)."""
    return suitability_level != NOT_SUITABLE


class SignalOutcome(Scored, Protocol):
    """Lo que el diagnóstico lee de cada señal de la ventana: su calificación (`Scored`), sus razones y sus limitaciones
    (las cumplen todas las señales del motor)."""

    reasons: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class Diagnosis:
    overall: TrafficLight
    overall_default: TrafficLight
    limitations: tuple[str, ...]
    # Con qué pesos se ordenan las mejores ventanas; None si ninguna luz da `other_window` (no se buscan).
    best_windows_weights: Mapping[str, int] | None


def diagnose(
    suitability_level: str,
    suitability_reasons: Sequence[str],
    zone_limitation: str | None,
    irrigated: bool | None,
    signals: Mapping[str, SignalOutcome] | None,
    weights: Mapping[str, int],
    weights_basis: str,
    default_weights: Mapping[str, int],
) -> Diagnosis:
    """El diagnóstico de la ventana. `signals` es nulo cuando el cultivo no es apto: no hay ventana que evaluar."""
    scores = signal_scores(signals) if signals is not None else {}
    overall = traffic_light(suitability_level, scores, weights, weights_basis)
    overall_default = traffic_light(suitability_level, scores, default_weights, DEFAULT)
    if overall.action == OTHER_WINDOW:
        best_windows_weights = weights
    elif overall_default.action == OTHER_WINDOW:
        best_windows_weights = default_weights
    else:
        best_windows_weights = None
    return Diagnosis(
        overall,
        overall_default,
        _limitations(suitability_level, suitability_reasons, zone_limitation, irrigated, signals),
        best_windows_weights,
    )


def _limitations(
    suitability_level: str,
    suitability_reasons: Sequence[str],
    zone_limitation: str | None,
    irrigated: bool | None,
    signals: Mapping[str, SignalOutcome] | None,
) -> tuple[str, ...]:
    items = [zone_limitation] if zone_limitation else []
    if suitability_level == INSUFFICIENT_DATA:
        items.extend(suitability_reasons)
    if irrigated is None and evaluates_windows(suitability_level):
        items.append(IRRIGATION_UNKNOWN)
    if signals is not None:
        items.extend(text for signal in signals.values() for text in signal.limitations)
        own = {name: signals[name].reasons[0] for name in OWN_MISSING_REASON if name in signals and signals[name].reasons}
        items.extend(missing_data_limitations(signal_scores(signals), own))
    return tuple(dict.fromkeys(items))
