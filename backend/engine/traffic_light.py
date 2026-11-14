"""El semáforo de una ventana de siembra: la luz, la acción sugerida y sus razones, con unos pesos (HU-074;
specs/01-reglas.md, «Agregación del semáforo», «Las prioridades del agricultor» y «Aptitud del cultivo en la zona»).

Función pura (R6): recibe la aptitud ya decidida (HU-191), las calificaciones de las señales de la ventana, ya
calculadas (`backend/engine/signal_score.py`, HU-196), y unos pesos ya leídos. No lee archivos, ni la base de datos,
ni el reloj. La API la llama dos veces por ventana: con los pesos de quien consulta (`overall`, `farmer`) y con los
de `weights.yaml` (`overall_default`, `default`); `weights_basis` de la respuesta lo pone la API (HU-076).

Qué cuenta y qué califica, el peso efectivo, el factor limitante y el alto riesgo salen de las mismas primitivas que
el orden de las ventanas (`rated_signals`, `weight_of`, `limiting`, `high_risk` y `signal_order` de
`signal_score.py`): el semáforo y el orden nunca leen distinto una misma ventana.

Las reglas, en orden (el detalle está en el docstring de `traffic_light`):

0. Cultivo no apto: `red` y `rotate`, sin mirar las señales.
1. `water` con peso mayor que 0 y sin calificación: `not_evaluable` y `review_data`, sin factor limitante (como el
   ejemplo `DIAGNOSIS_NOT_EVALUABLE` del contrato); el alto riesgo sí se calcula, para no esconder un riesgo grave.
2. Alguna señal que cuenta es desfavorable y crítica, o dos que cuentan son desfavorables (con el nivel efectivo):
   `red`.
3. Hay al menos una señal que cuenta, ninguna es desfavorable (nivel efectivo) y `water` es `favorable` o no cuenta:
   `green`.
4. Si no (incluida la ventana sin ninguna señal que cuente y califique: no hay evidencia de nada, ni a favor ni en
   contra, igual que en HU-192): `yellow`.
5. Las señales sin datos o que no aplican no cambian la luz; las sin datos van a las limitaciones
   (`missing_data_limitations`, aparte porque no depende de los pesos).

**Nivel efectivo:** con peso 4 o más, un `moderate` cuenta como `unfavorable` para la luz («Las prioridades del
agricultor»). Solo cambia la luz y la acción: el factor limitante y el alto riesgo usan el nivel y la calificación
reales.

**Acción (specs/01-reglas.md, bajo la tabla de acciones; aprobado por Felipe el 14 de noviembre de 2026,
docs/registro-de-decisiones.md):** la tabla de acciones se aplica sobre las señales que cuentan
con nivel **efectivo** `unfavorable`, no el real. Por qué: (a) la HU llama a la helada `moderate`
con peso 4 «una de las dos desfavorables que cuentan» (ejemplo `DIAGNOSIS_OK` del contrato); (b) con el nivel real,
un rojo por dos `moderate` con peso 4 o más dejaría vacío el conjunto de desfavorables y daría `other_window` aunque
una fuera la oferta; (c) es el porqué de la tabla: si lo que impide el verde es la oferta, el suelo o el mercado,
«cambiar de fecha no los arregla».
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from backend.engine.signal_score import (
    AVAILABLE,
    FAVORABLE,
    INSUFFICIENT_DATA,
    MODERATE,
    UNFAVORABLE,
    RatedSignal,
    SignalScore,
    high_risk,
    limiting,
    rated_signals,
    signal_order,
    weight_of,
)
from backend.engine.suitability import INSUFFICIENT_DATA as SUITABILITY_INSUFFICIENT_DATA
from backend.engine.suitability import NOT_SUITABLE, SUITABLE
from common.signals import P0_SIGNALS

GREEN = "green"
YELLOW = "yellow"
RED = "red"
NOT_EVALUABLE = "not_evaluable"

SOW = "sow"
OTHER_WINDOW = "other_window"
ROTATE = "rotate"
REVIEW_DATA = "review_data"

FARMER = "farmer"
DEFAULT = "default"
WEIGHTS_BASES = frozenset({FARMER, DEFAULT})

SUITABILITY_LEVELS = frozenset({SUITABLE, NOT_SUITABLE, SUITABILITY_INSUFFICIENT_DATA})

# Con un peso de al menos este valor, un `moderate` cuenta como `unfavorable` para la luz («Las prioridades del
# agricultor»: 4 a 5, «me importa mucho»). Queda en el código, no en `weights.yaml`, porque la spec fija el corte en 4:
# si se quiere ajustable, es deuda que pasa por la spec.
HIGH_WEIGHT = 4

# Las señales que cambiar de fecha no arregla: si alguna es desfavorable, la acción es rotar. Las demás señales del
# P0 son las de clima de la tabla de acciones, que son los riesgos graves de clima (`CLIMATE_CRITICAL_SIGNALS` de
# `signal_score.py`; `excess_rain` se suma allí cuando exista, P1): «si no es de rotar, es de clima» no necesita un
# segundo conjunto. Una prueba comprueba que las dos parten `P0_SIGNALS`.
ROTATE_SIGNALS = frozenset({"soil", "supply", "market"})

# Cómo se nombra cada señal en las razones.
SIGNAL_NAMES_ES: Mapping[str, str] = {
    "water": "el agua",
    "frost": "la helada",
    "heat": "el calor",
    "soil": "el suelo",
    "supply": "la oferta",
    "market": "el mercado",
}

REASON_PREFIXES: Mapping[str, str] = {FARMER: "Con sus prioridades", DEFAULT: "Con el criterio de AgroSense"}

LIGHT_NAMES_ES: Mapping[str, str] = {GREEN: "verde", YELLOW: "amarilla", RED: "roja"}

# El texto del contrato para un cultivo no apto (el mismo de `backend/api/calc_examples.py`). El dato que lo excluye
# va en la razón de `suitability`, no aquí.
NOT_SUITABLE_REASON = "Este cultivo no se da en su zona: elija otro"


@dataclass(frozen=True)
class TrafficLight:
    """La luz de una ventana con unos pesos: `light` y `action` (valores del contrato), `high_risk` (alguna señal que
    cuenta es desfavorable y crítica), `limiting_signal` (la que cuenta con la calificación más baja; None si ninguna
    califica o si la luz es `not_evaluable`) y `reasons` en español que solo citan señales evaluadas (R5)."""

    light: str
    action: str
    high_risk: bool
    limiting_signal: str | None
    reasons: tuple[str, ...]


def traffic_light(suitability: str, signals: Mapping[str, SignalScore], weights: Mapping[str, float], weights_basis: str) -> TrafficLight:
    """La luz, la acción y las razones de una ventana con `weights`.

    `suitability`: el `level` de la aptitud ya decidido (HU-191): `suitable`, `not_suitable` o `insufficient_data`.
    `signals`: las calificaciones de la ventana por nombre; una señal ausente del mapa vale lo mismo que sin datos.
    `weights`: los pesos por señal; uno que falta o es negativo vale 0 (`weight_of`). El motor no valida el rango:
    un peso mayor que 5 se trata como alto (4 o más).
    `weights_basis`: `farmer` o `default`; solo cambia cómo empiezan las razones («Con sus prioridades» o «Con el
    criterio de AgroSense»).

    Reglas, en orden:

    `rated = rated_signals(signals, weights)`. Desde la regla 1, `high_risk` es `high_risk(rated)`; desde la regla 2,
    `limiting_signal` es el nombre de `limiting(rated)` (o None). Ninguno de los dos usa el nivel efectivo.

    0. `suitability == not_suitable`: `red`, `rotate`, `high_risk` falso, `limiting_signal` None; no se miran las
       señales. `insufficient_data` no bloquea: se sigue como `suitable`.
    1. Si el peso efectivo de `water` es mayor que 0 (solo el peso, no `counts`: sin dato no hay `critical`) y
       `water` no está en `rated` (falta del mapa, no es `available` o no tiene `score`): `not_evaluable` y
       `review_data`. `limiting_signal` es None: sin el agua no hay un factor limitante que mostrar (ejemplo
       `DIAGNOSIS_NOT_EVALUABLE` del contrato). `high_risk` sí se calcula, y la razón nombra las críticas, para no
       esconder una helada o un calor crítico. Con peso 0 esta regla no aplica.
    2. El nivel efectivo de cada señal de `rated` es `unfavorable` si su peso efectivo es 4 o más y su nivel real es
       `moderate`; si no, el real. `red` si `high_risk(rated)` o si dos o más tienen nivel efectivo `unfavorable`.
    3. `green` si `rated` no está vacía, ninguna tiene nivel efectivo `unfavorable` y `water` no está en `rated` o su
       nivel real es `favorable`.
    4. Si no, `yellow`. Incluye `rated` vacía (con esos pesos ninguna señal que cuenta califica; por ejemplo, peso
       solo en la oferta y el mercado, sin datos): no hay evidencia de nada, ni a favor ni en contra, así que nunca es
       `green` (consistente con HU-192, donde ese mismo caso tampoco se recomienda); la razón lo dice explícitamente.

    Acción, sobre las señales de `rated` con nivel efectivo `unfavorable` (specs/01-reglas.md, bajo la tabla de
    acciones; ver el docstring del módulo): `green` → `sow`; `yellow` o `red` → `rotate` si alguna es de
    `ROTATE_SIGNALS`, si no `other_window`. En rojo siempre hay al menos una desfavorable efectiva: no hay caso vacío.

    Razones (R5: solo citan señales evaluadas; es historia, nunca pronóstico):

    - Regla 0: el cultivo no se da en la zona y conviene elegir otro.
    - Regla 1: falta el dato de agua y no se puede evaluar; si hay señales críticas que cuentan, las nombra.
    - Desde la regla 2 empiezan con «Con sus prioridades» (`farmer`) o «Con el criterio de AgroSense» (`default`).
    - `red` y `yellow`: nombran las desfavorables efectivas con su calificación; una crítica lo dice y una
      `moderate` subida por su peso lleva «(pesa N)». Un amarillo sin desfavorables dice que el agua no es favorable;
      un amarillo con `rated` vacía dice que ninguna señal que cuenta tiene calificación y que no hay evidencia de
      riesgo ni de que sea buena.
    - `green`: ninguna señal que cuenta es desfavorable (y al menos una cuenta).
    - Desde la regla 2, cada señal disponible `unfavorable` que no cuenta por su peso 0 se dice aparte («Con peso 0, la
      oferta es desfavorable pero no cuenta para la luz»).

    `ValueError` si `suitability` o `weights_basis` no son de los valores permitidos.
    """
    if suitability not in SUITABILITY_LEVELS:
        raise ValueError(f"aptitud desconocida: {suitability!r}")
    if weights_basis not in WEIGHTS_BASES:
        raise ValueError(f"base de pesos desconocida: {weights_basis!r}")
    if suitability == NOT_SUITABLE:
        return TrafficLight(RED, ROTATE, False, None, (NOT_SUITABLE_REASON,))

    rated = rated_signals(signals, weights)
    risk = high_risk(rated)
    rated_names = {name for name, _, _ in rated}
    if weight_of(weights, "water") > 0 and "water" not in rated_names:
        return TrafficLight(NOT_EVALUABLE, REVIEW_DATA, risk, None, _missing_water_reasons(rated))

    lowest = limiting(rated)
    limiting_name = None if lowest is None else lowest[0]

    unfavorable = tuple(item for item in rated if _effective_level(item) == UNFAVORABLE)
    light = _light(rated, unfavorable, risk)
    action = SOW if light == GREEN else _non_green_action(unfavorable)
    reasons = (_light_reason(light, REASON_PREFIXES[weights_basis], rated, unfavorable), *_ignored_reasons(signals, rated_names))
    return TrafficLight(light, action, risk, limiting_name, reasons)


def missing_data_limitations(signals: Mapping[str, SignalScore]) -> tuple[str, ...]:
    """Una limitación en español por cada señal con `status = insufficient_data` (no por `not_applicable`), en el
    orden de `signal_order` (reglas 1 y 5 de «Agregación del semáforo»: la señal sin datos se dice). Una señal del P0
    ausente del mapa vale lo mismo que sin datos: no desaparece en silencio (R1).

    No depende de los pesos: la API la llama una vez por ventana, no una por luz. Por eso el texto no dice si la señal
    cambia la luz (sin el agua, con peso, la luz es `not_evaluable`).
    """
    names = sorted(set(P0_SIGNALS) | set(signals), key=signal_order)
    return tuple(
        f"Sin datos para la zona: {SIGNAL_NAMES_ES.get(name, name)} no se evaluó."
        for name in names
        if name not in signals or signals[name].status == INSUFFICIENT_DATA
    )


def _effective_level(item: RatedSignal) -> str | None:
    """El nivel para la luz y la acción: con peso 4 o más, un `moderate` cuenta como `unfavorable`. Nunca se usa para
    el factor limitante ni para el alto riesgo."""
    _, signal, weight = item
    if weight >= HIGH_WEIGHT and signal.level == MODERATE:
        return UNFAVORABLE
    return signal.level


def _light(rated: tuple[RatedSignal, ...], unfavorable: tuple[RatedSignal, ...], risk: bool) -> str:
    """Reglas 2 a 4. Sin ninguna señal que cuente y califique (`rated` vacía, por ejemplo con peso solo en la oferta y
    el mercado, los dos sin datos, y sin riesgo grave de clima), nunca es `green`: no hay evidencia de nada, ni a favor
    ni en contra (consistente con HU-192, donde ese mismo caso tampoco se recomienda). Queda `yellow`, con la razón que
    lo dice."""
    if risk or len(unfavorable) >= 2:
        return RED
    water = _find(rated, "water")
    if rated and not unfavorable and (water is None or water[1].level == FAVORABLE):
        return GREEN
    return YELLOW


def _non_green_action(unfavorable: tuple[RatedSignal, ...]) -> str:
    """La tabla de acciones en amarillo y rojo: rotar si cambiar de fecha no arregla alguna desfavorable."""
    return ROTATE if any(name in ROTATE_SIGNALS for name, _, _ in unfavorable) else OTHER_WINDOW


def _find(rated: tuple[RatedSignal, ...], name: str) -> RatedSignal | None:
    return next((item for item in rated if item[0] == name), None)


def _describe(item: RatedSignal) -> str:
    """Una señal evaluada con su calificación; si es crítica, o si cuenta como desfavorable por su peso, lo dice."""
    name, signal, weight = item
    text = f"{SIGNAL_NAMES_ES.get(name, name)} califica {signal.score} de 100"
    if high_risk((item,)):
        return f"{text} y es crítica"
    if signal.level != _effective_level(item):
        return f"{text} (pesa {weight:g})"
    return text


def _missing_water_reasons(rated: tuple[RatedSignal, ...]) -> tuple[str, ...]:
    """Regla 1: falta el agua; si hay riesgos graves que cuentan, no se esconden."""
    reasons = ["Sin datos de agua para la zona: la luz no se puede evaluar. Revise los datos."]
    critical = [_describe(item) for item in rated if high_risk((item,))]
    if critical:
        reasons.append(f"Aun así, en la historia de la zona: {'; '.join(critical)}.")
    return tuple(reasons)


def _light_reason(light: str, prefix: str, rated: tuple[RatedSignal, ...], unfavorable: tuple[RatedSignal, ...]) -> str:
    """La razón principal de las reglas 2 a 4."""
    head = f"{prefix}, la luz es {LIGHT_NAMES_ES[light]}"
    if unfavorable:
        return f"{head}: {'; '.join(_describe(item) for item in unfavorable)}."
    if not rated:
        return f"{head}: con esas prioridades ninguna señal que cuenta tiene calificación; no hay evidencia de riesgo ni de que sea buena."
    if light == YELLOW:
        return f"{head}: {_describe(_find(rated, 'water'))} y no es favorable."
    return f"{head}: ninguna señal que cuenta es desfavorable."


def _ignored_reasons(signals: Mapping[str, SignalScore], rated_names: set[str]) -> tuple[str, ...]:
    """Las señales desfavorables que no cuentan por su peso 0: se muestran, pero no cambian la luz."""
    return tuple(
        f"Con peso 0, {SIGNAL_NAMES_ES.get(name, name)} es desfavorable pero no cuenta para la luz."
        for name in sorted(signals, key=signal_order)
        if name not in rated_names and signals[name].status == AVAILABLE and signals[name].level == UNFAVORABLE
    )
