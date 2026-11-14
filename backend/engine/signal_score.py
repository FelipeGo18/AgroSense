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
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.engine.curve import CurvePoint, crop_curve, score_from_curve

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

AVAILABLE = "available"
INSUFFICIENT_DATA = "insufficient_data"

FAVORABLE = "favorable"
MODERATE = "moderate"
UNFAVORABLE = "unfavorable"

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


def _round_half_up(score: float) -> int:
    """Redondea hacia arriba desde la mitad: nunca el redondeo al par de `round()` (`round(68.5)` da 68, pero
    aquí 68,5 tiene que dar 69). `score` siempre es 0-100, nunca negativo, así que no hace falta `math.copysign`."""
    return math.floor(score + 0.5)


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
    if curve is None or _missing(value):
        return _insufficient()

    if curve == FROM_CROP:
        points = _crop_points(signal, crop_limits or {})
        if points is None:
            return _insufficient()
    else:
        points = curve

    score = _round_half_up(score_from_curve(points, float(value)))
    if score >= thresholds.favorable:
        level = FAVORABLE
    elif score >= thresholds.moderate:
        level = MODERATE
    else:
        level = UNFAVORABLE
    critical = config.critical_below is not None and score < config.critical_below
    return SignalScore(AVAILABLE, score, level, critical)


def _missing(value: float | None) -> bool:
    """Sin dato: None o NaN (R1). Un NaN no se califica: no tiene tramo en la curva."""
    return value is None or math.isnan(float(value))


def _insufficient() -> SignalScore:
    return SignalScore(INSUFFICIENT_DATA, None, None, False)


def _crop_points(signal: str, crop_limits: Mapping[str, float | None]) -> tuple[CurvePoint, ...] | None:
    """Puntos de la curva de la ficha, o None si falta algún límite (R1: nunca un límite «típico»)."""
    limits = [crop_limits.get(field) for field in CROP_LIMITS[signal]]
    if any(_missing(limit) for limit in limits):
        return None
    if signal == "heat":
        temp_opt_max, heat_max = limits
        return (float(temp_opt_max), 100.0), (float(heat_max), 0.0)
    return crop_curve(*limits)
