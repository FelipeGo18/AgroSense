"""Calificación de 0 a 100 de una señal con su curva, su nivel y si es crítica (HU-196; specs/01-reglas.md, «Cómo se
califica cada señal»).

Función pura (R6): recibe el valor medido en la zona, los umbrales ya leídos y validados (`Thresholds`, de
`backend/config/thresholds.py`, HU-075) y los límites de la ficha del cultivo ya leídos. No abre archivos ni revalida
la configuración: la forma de `thresholds.yaml` (curvas ordenadas, `crop` solo en `heat` y `soil`, `soil` sin
`critical_below`) la garantiza `load_thresholds`. La única curva es la de `backend/engine/curve.py` (`crop_curve` y
`score_from_curve`): aquí no se interpola.

`Thresholds` se importa solo para el tipado: el motor no carga en tiempo de ejecución un módulo que importa yaml y
lee archivos.

Qué curva usa cada señal (`thresholds.signals[signal].curve`):

- Una tupla de puntos (valor, calificación) (hoy `water` y `frost`): la curva fija de `thresholds.yaml`, igual para
  todos los cultivos. Los límites de la ficha no se usan.
- `"crop"` (hoy `heat` y `soil`): la curva sale de la ficha del cultivo (`crop_limits`), con los límites de
  `CROP_LIMITS`:
  - `heat`: dos puntos, 100 en `temp_opt_max_c` y 0 en `heat_max_c`. Sin límite inferior: el frío no es calor.
  - `soil`: cuatro puntos, `crop_curve(ph_min, ph_opt_min, ph_opt_max, ph_max)`.
- `None` (hoy `supply` y `market`): sin fuente para los cortes; la señal es `insufficient_data` siempre (R1, R8).

Sin el valor medido, o sin alguno de los límites de la ficha que pide la curva: `insufficient_data`, con `score` y
`level` nulos y `critical` falso (R1). Un NaN (en el valor o en un límite de la ficha) cuenta como sin dato. Nunca se
usa un límite «típico».

`score` es el entero que ve el agricultor (el contrato tipa `Score` como `int`): se redondea hacia arriba desde la
mitad (`floor(x + 0,5)`, nunca el redondeo al par de `round()`) antes de decidir nada más, para que el nivel y si es
crítica salgan del mismo número que se muestra, no de un decimal que nadie ve (69,6 tiene que dar 70 y `favorable`,
no quedarse en `moderate` con un 70 en pantalla).

El nivel sale de ese entero contra `thresholds.favorable` y `thresholds.moderate`: `score >= favorable` es
`favorable`; `score >= moderate` es `moderate`; si no, `unfavorable`. Es crítica si `critical_below` no es nulo y
ese mismo entero `< critical_below` (estricto). `soil` nunca es crítica (R10) porque su `critical_below` es siempre
nulo.

`not_applicable` (heladas o calor cuando ninguna etapa es sensible) no lo decide esta función: lo decide quien la
llama, antes de pedir la calificación. Una señal que no está en los umbrales da `KeyError`: es un error de
programación.

Aquí viven también las primitivas de las señales que **cuentan** y **califican**, que comparten el orden de las
ventanas (HU-192, `window_order.py`) y el semáforo (HU-074, `traffic_light.py`), para que los dos lean lo mismo:
`counts`, `weight_of`, `signal_order`, `rated_signals` (con su tipo `RatedSignal`), `limiting` y `high_risk`. También
viven aquí los valores de `status` (`AVAILABLE`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`), una sola vez para todo el
motor.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from backend.engine.curve import CurvePoint, crop_curve, score_from_curve
from common.signals import P0_SIGNALS
from common.text import of

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

# Los valores de `status` del contrato: la única definición del motor (los demás módulos los importan de aquí).
AVAILABLE = "available"
INSUFFICIENT_DATA = "insufficient_data"
NOT_APPLICABLE = "not_applicable"

FAVORABLE = "favorable"
MODERATE = "moderate"
UNFAVORABLE = "unfavorable"

# Los riesgos graves de clima: críticos, cuentan siempre, aunque su peso sea 0 (R2). `excess_rain` se suma cuando
# exista (P1); hoy no hay esa señal y no se inventa (R5).
CLIMATE_CRITICAL_SIGNALS = frozenset({"water", "frost", "heat"})

# El mismo valor que `backend.config.thresholds.FROM_CROP` (una prueba lo comprueba).
FROM_CROP = "crop"

# Los límites de la ficha (columnas de `crops`) que pide cada señal cuya curva sale del cultivo, en el orden de la
# curva. Sus llaves son las de `backend.config.thresholds.CROP_CURVES` (una prueba lo comprueba).
CROP_LIMITS: dict[str, tuple[str, ...]] = {
    "heat": ("temp_opt_max_c", "heat_max_c"),
    "soil": ("ph_min", "ph_opt_min", "ph_opt_max", "ph_max"),
}


@dataclass(frozen=True)
class SignalScore:
    """Calificación de una señal: `status` es `available` o `insufficient_data`; `score` es el entero de 0 a 100
    que ve el agricultor, o None; `level` `favorable`, `moderate`, `unfavorable` o None; `critical` es falso
    siempre que no hay calificación."""

    status: str
    score: int | None
    level: str | None
    critical: bool


# Una señal que cuenta y califica, como la devuelve `rated_signals`: (nombre, calificación, peso efectivo).
RatedSignal = tuple[str, SignalScore, float]


def round_half_up(value: float) -> int:
    """Redondea hacia arriba desde la mitad: nunca el redondeo al par de `round()` (`round(68.5)` da 68, pero
    aquí 68,5 tiene que dar 69). Lo usan las calificaciones (0-100) y los porcentajes de las razones (en valor
    absoluto): `value` nunca es negativo, así que no hace falta `math.copysign`."""
    return math.floor(value + 0.5)


def counts(signal: str, weight: float, critical: bool) -> bool:
    """Si una señal «cuenta» para la luz y para el orden de las ventanas (specs/01-reglas.md, «Agregación del
    semáforo» y «Las prioridades del agricultor»): la que tiene peso mayor que 0, más los riesgos graves de clima
    (`water`, `frost` o `heat` críticos), que cuentan siempre, aunque su peso sea 0 (R2).

    Es la única definición del motor: la comparten el orden de las ventanas (HU-192, `window_order.py`) y el
    semáforo (HU-074), que debe reutilizarla, no reimplementarla. Una señal crítica que no es de clima (`soil`,
    `supply`, `market`) con peso 0 no cuenta.
    """
    return weight > 0 or (signal in CLIMATE_CRITICAL_SIGNALS and critical)


def weight_of(weights: Mapping[str, float | None], name: str) -> float:
    """El peso efectivo de una señal: el del mapa, o 0 si falta, es None, NaN o negativo (un peso que falta vale 0).
    El motor no valida el rango de 0 a 5 (lo hace la API con 422): un peso mayor que 5 se devuelve tal cual."""
    weight = weights.get(name)
    if weight is None or math.isnan(weight):
        return 0
    return max(weight, 0)


def signal_order(name: str) -> tuple[int, str]:
    """El orden fijo de las señales para desempatar y para listar (R4): las del P0 en el orden del contrato
    (`P0_SIGNALS`) y las demás al final, por nombre. No depende del orden del mapa recibido."""
    if name in P0_SIGNALS:
        return (P0_SIGNALS.index(name), name)
    return (len(P0_SIGNALS), name)


def rated_signals(signals: Mapping[str, SignalScore], weights: Mapping[str, float | None]) -> tuple[RatedSignal, ...]:
    """Las señales que cuentan (`counts`, con su peso efectivo de `weight_of`) y califican (`status = available` con
    `score`), como `(nombre, calificación, peso efectivo)`, en el orden de `signal_order`.

    Una señal sin datos, que no aplica o `available` sin calificación no califica: no entra (R1). Un riesgo grave de
    clima con peso 0 sí entra, con peso 0.
    """
    rated = []
    for name, signal in signals.items():
        weight = weight_of(weights, name)
        if signal.status == AVAILABLE and signal.score is not None and counts(name, weight, signal.critical):
            rated.append((name, signal, weight))
    return tuple(sorted(rated, key=lambda item: signal_order(item[0])))


def limiting(rated: Sequence[RatedSignal]) -> tuple[str, SignalScore] | None:
    """El factor que más limita (ley del mínimo): la señal de `rated` con la calificación más baja; en un empate, la
    primera en `signal_order`. None si `rated` está vacía."""
    if not rated:
        return None
    name, signal, _ = min(rated, key=lambda item: (item[1].score, signal_order(item[0])))
    return name, signal


def is_grave(score: SignalScore) -> bool:
    """Si una señal es `unfavorable` **y** crítica (R2): la única definición de «riesgo grave» de una señal."""
    return score.critical and score.level == UNFAVORABLE


def high_risk(rated: Sequence[RatedSignal]) -> bool:
    """Si alguna señal de `rated` es `unfavorable` **y** crítica (R2: «desfavorable y crítica»). La única definición
    de alto riesgo del motor: la usan el orden de las ventanas y el semáforo.

    Con los umbrales de `thresholds.yaml` 1.0.0, toda señal crítica es además desfavorable (el `critical_below` de
    cada señal no pasa del corte de `moderate`), así que exigir las dos condiciones no cambia ningún resultado de
    hoy; lo hace explícito por si un umbral se mueve.
    """
    return any(is_grave(signal) for _, signal, _ in rated)


def score_signal(
    signal: str,
    value: float | None,
    thresholds: Thresholds,
    crop_limits: Mapping[str, float | None] | None = None,
) -> SignalScore:
    """Califica `value` para `signal` con su curva de `thresholds` (y de `crop_limits` si la curva es `"crop"`).

    `thresholds`: los umbrales ya validados por `load_thresholds` (HU-075); se confía en su forma.
    `crop_limits`: los límites de la ficha del cultivo por nombre de columna (por ejemplo `{"heat_max_c": 30.0}`);
    una llave ausente vale lo mismo que None. Se ignora cuando la curva es fija.

    Igual que la aptitud de HU-191: un dato que falta (None, llave ausente o NaN) da `insufficient_data`. En cambio,
    `inf` y `-inf` no son «sin dato»: quedan fuera de los extremos de la curva y se califican con el punto extremo
    de ese lado (por ejemplo, `water` con `inf` da 100 y `frost` con `inf` da 0). Una ficha
    incoherente (por ejemplo `heat_max_c` por debajo de `temp_opt_max_c`, o los `ph_*` desordenados) deja una curva
    desordenada y pasa el `ValueError` de `score_from_curve`: es un error de datos del catálogo y tiene que fallar
    ruidoso, no esconderse detrás de una calificación o de un «sin datos».
    """
    config = thresholds.signals[signal]
    curve = config.curve
    if curve is None or missing(value):
        return _insufficient()

    if curve == FROM_CROP:
        points = _crop_points(signal, crop_limits or {})
        if points is None:
            return _insufficient()
    else:
        points = curve

    score = round_half_up(score_from_curve(points, float(value)))
    if score >= thresholds.favorable:
        level = FAVORABLE
    elif score >= thresholds.moderate:
        level = MODERATE
    else:
        level = UNFAVORABLE
    critical = config.critical_below is not None and score < config.critical_below
    return SignalScore(AVAILABLE, score, level, critical)


def missing(value: float | None) -> bool:
    """Sin dato: None o NaN (R1). Un NaN no se califica: no tiene tramo en la curva."""
    return value is None or math.isnan(float(value))


def _insufficient() -> SignalScore:
    return SignalScore(INSUFFICIENT_DATA, None, None, False)


def _crop_points(signal: str, crop_limits: Mapping[str, float | None]) -> tuple[CurvePoint, ...] | None:
    """Puntos de la curva de la ficha, o None si falta algún límite (R1: nunca un límite «típico»)."""
    limits = [crop_limits.get(field) for field in CROP_LIMITS[signal]]
    if any(missing(limit) for limit in limits):
        return None
    if signal == "heat":
        temp_opt_max, heat_max = limits
        return (float(temp_opt_max), 100.0), (float(heat_max), 0.0)
    return crop_curve(*limits)


def no_stages_reason(crop_name: str) -> str:
    """La razón de una señal que no se evalúa porque el cultivo no tiene etapas publicadas (sin ventana). La comparten
    las heladas, el calor y el suelo."""
    return f"Sin las etapas {of(crop_name)}: la señal no se evalúa"


class Scored(Protocol):
    """Lo que el semáforo y el orden leen de una señal ya calculada (`SignalScore` y los resultados de cada señal)."""

    status: str
    score: int | None
    level: str | None
    critical: bool


def signal_scores(signals: Mapping[str, Scored]) -> dict[str, SignalScore]:
    """Las calificaciones que leen el semáforo y el orden de las ventanas, de las señales ya calculadas."""
    return {name: SignalScore(signal.status, signal.score, signal.level, signal.critical) for name, signal in signals.items()}
