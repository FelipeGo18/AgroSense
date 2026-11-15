"""La señal de suelo: si el pH estimado del suelo de la zona está en el rango que tolera el cultivo (HU-183;
specs/01-reglas.md, «Señales de una ventana» y «Cómo se califica cada señal»).

- **La calificación** es la curva de HU-196 sobre `ph` de `soil_municipality` (la mediana del pH de las celdas del
  municipio; contrato, tabla `soil_municipality`, y `variable: ph` de `thresholds.yaml`): 100 entre `ph_opt_min` y
  `ph_opt_max`, 0 fuera de `ph_min`–`ph_max` y una recta entre ambos. La calificación, el nivel y si es crítica salen
  solo de `score_signal`; aquí no se interpola.
- **El nivel sale de la calificación**, como en las demás señales: el valor estimado (`ph`) decide. El intervalo
  `ph_p05`–`ph_p95` es la incertidumbre del mapa (SoilGrids: los percentiles 5 y 95 son los límites de un intervalo de
  predicción del 90 %, «una medida de la incertidumbre»; la mediana «puede usarse como predicción», ISRIC) y solo cambia
  el nivel en un caso: si **todo** el intervalo queda fuera de lo que tolera el cultivo (`outside_tolerated`), el nivel
  es `unfavorable`. Si solo una parte queda fuera (`crosses_tolerated`), la razón lo dice y el nivel no cambia: en la
  región piloto el intervalo mide de 2,4 a más de 3 unidades de pH en todos los municipios y siempre cruza algún límite,
  así que limitar el nivel por eso dejaba el suelo en `moderate` en casi toda la región para todos los cultivos y la
  señal no distinguía nada (decisión del 14 nov 2026, `docs/registro-de-decisiones.md`). La incertidumbre se dice como
  pide R10: el intervalo en la razón y el análisis de suelo del lote.
  Tocar un borde no es quedar fuera, igual que en las estrategias (`ph_motives`, `backend/engine/rotations/
  exclusions.py`, que usa esta misma `outside_tolerated`): `ph_max < p05` o `ph_min > p95`, estricto. Cruzar es que una
  parte del intervalo quede fuera (`p05 < ph_min` o `p95 > ph_max`) sin que quede todo.
  Sin los dos percentiles (nulos o NaN), la curva califica con `ph` y la lectura del intervalo no se hace: se dice en
  las limitaciones (R1). No se inventa un intervalo.
- **Nunca crítica** (R10): el suelo es una estimación de un mapa de 250 m. `critical` es siempre falso, también si un
  umbral cambiara: con suelo desfavorable la luz solo llega a rojo junto con otra señal desfavorable (R2).
- **Sin datos** (sin fila del municipio o con `ph` nulo o NaN) o con un cultivo sin su rango de pH completo:
  `insufficient_data`, nivel y calificación nulos, y la razón también en las limitaciones (R1). El pipeline no publica
  un valor de la ficha que no cite una fuente (`pipeline/catalog.py`, `_value`, R8; lo vigila el caso `ph_min` sin
  fuente de `tests/pipeline/test_catalogo.py::test_un_catalogo_que_no_cumple_no_se_publica`), así que un límite nulo
  es un límite sin fuente.
- **Sin ventana** (un cultivo sin etapas publicadas) el suelo tampoco se califica, como las demás señales (HU-076,
  `docs/registro-de-decisiones.md`): `soil_without_stages`, con la misma razón que las heladas y el calor.
- **La razón** da el pH estimado con su intervalo frente al óptimo y al rango que tolera el cultivo, dice que es una
  estimación de 250 m y pide un análisis de suelo del lote (R10, `ESTIMATE_LABEL`).

El suelo no cambia con la fecha: la API calcula esta señal una vez por consulta y la misma va en todas las ventanas que
existen.

Función pura (R6): el suelo llega ya leído (`ZoneSoilPh`, de `backend/api/soil_signals.py`), la ficha como un mapa de
sus columnas y los umbrales ya validados. No abre archivos ni importa la API.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.engine.sensitive_signal import no_stages_reason
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, UNFAVORABLE, score_signal
from common.text import format_decimal, of

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

SOIL = "soil"
INDICATOR = "ph"
# El rótulo de estimación que lleva toda razón de la señal (R10), con las palabras del rótulo de la web (HU-185).
ESTIMATE_LABEL = "Estimación de un mapa global de 250 m (SoilGrids): confírmelo con un análisis de suelo de su lote"
NO_SOIL_REASON = "Sin pH estimado del suelo para la zona: el suelo no se evaluó"


@dataclass(frozen=True)
class ZoneSoilPh:
    """El pH estimado del suelo de la zona (`soil_municipality`): `ph` es la mediana de las celdas y `ph_p05`, `ph_p95`
    la mediana de los percentiles 5 y 95 de cada celda. Cualquiera puede ser nulo (R1)."""

    ph: float | None
    ph_p05: float | None
    ph_p95: float | None


@dataclass(frozen=True)
class SoilSignalResult:
    """La señal `soil`, con los nombres de campo del contrato y la misma forma que las demás señales de la ventana
    (`ClimateSignalResult`, `MarketSignalResult`). No trae `counts`: lo deciden los pesos en el semáforo (HU-074)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()


def outside_tolerated(ph_min: float, ph_max: float, p05: float, p95: float) -> bool:
    """Si todo el intervalo estimado del suelo queda fuera de lo que tolera el cultivo. Tocar un borde no cuenta. La
    comparten esta señal y el descarte `soil_ph` de las estrategias, para que digan lo mismo."""
    return ph_max < p05 or ph_min > p95


def crosses_tolerated(ph_min: float, ph_max: float, p05: float, p95: float) -> bool:
    """Si una parte del intervalo queda fuera de lo que tolera el cultivo y otra no."""
    return (p05 < ph_min or p95 > ph_max) and not outside_tolerated(ph_min, ph_max, p05, p95)


def soil_signal(soil: ZoneSoilPh | None, crop_limits: Mapping[str, Any], thresholds: Thresholds, crop_name: str) -> SoilSignalResult:
    """La señal `soil` del cultivo en la zona. `soil` nulo: el municipio no tiene suelo publicado. `crop_limits` es la
    ficha (al menos `ph_min`, `ph_opt_min`, `ph_opt_max` y `ph_max`); `crop_name` lleva su artículo («la papa»)."""
    if soil is None or _missing(soil.ph):
        return _insufficient(NO_SOIL_REASON)
    score = score_signal(SOIL, soil.ph, thresholds, crop_limits)
    if score.status != AVAILABLE or score.score is None:
        return _insufficient(
            f"La ficha {of(crop_name)} no trae con fuente su rango de pH (ph_min, ph_opt_min, ph_opt_max y ph_max): el suelo no se califica"
        )
    ph = float(soil.ph)
    ph_min, ph_opt_min, ph_opt_max, ph_max = (float(crop_limits[k]) for k in ("ph_min", "ph_opt_min", "ph_opt_max", "ph_max"))
    tolerated = f"({format_decimal(ph_min)} a {format_decimal(ph_max)})"
    level = score.level
    if _missing(soil.ph_p05) or _missing(soil.ph_p95):
        head = f"pH estimado de {format_decimal(ph)}"
        interval = f"{crop_name[:1].upper()}{crop_name[1:]} tolera de {format_decimal(ph_min)} a {format_decimal(ph_max)}"
        limitations: tuple[str, ...] = (
            "Sin el rango del pH estimado de la zona (percentiles 5 y 95): no se revisó si parte del suelo queda fuera de "
            f"lo que tolera {crop_name}",
        )
    else:
        p05, p95 = float(soil.ph_p05), float(soil.ph_p95)
        head = f"pH estimado de {format_decimal(ph)} (de {format_decimal(p05)} a {format_decimal(p95)})"
        limitations = ()
        if outside_tolerated(ph_min, ph_max, p05, p95):
            level = UNFAVORABLE
            interval = f"Todo ese rango queda fuera de lo que tolera {tolerated}"
        elif crosses_tolerated(ph_min, ph_max, p05, p95):
            # El rango es la incertidumbre del mapa: se dice, pero el nivel lo da el pH estimado (ver el módulo).
            interval = f"Es un rango amplio y parte de él queda fuera de lo que tolera {tolerated}"
        else:
            interval = f"Todo ese rango está dentro de lo que tolera {tolerated}"
    relation = _relation(ph, ph_min, ph_opt_min, ph_opt_max, ph_max, crop_name, tolerated)
    reason = f"{head}, {relation}. {interval}. {ESTIMATE_LABEL}"
    # Nunca crítica (R10), aunque un umbral cambiara.
    return SoilSignalResult(AVAILABLE, level, False, score.score, (INDICATOR,), (reason,), limitations)


def soil_without_stages(crop_name: str) -> SoilSignalResult:
    """Sin etapas del cultivo no hay ventana, y sin ventana ninguna señal se califica, tampoco el suelo (HU-076,
    `docs/registro-de-decisiones.md`: «`window` nulo, señales sin datos»). Lleva la misma razón que las heladas y el
    calor en ese caso (`no_stages_reason`), también en las limitaciones (R1)."""
    return _insufficient(no_stages_reason(crop_name))


def _relation(ph: float, ph_min: float, ph_opt_min: float, ph_opt_max: float, ph_max: float, crop_name: str, tolerated: str) -> str:
    """Dónde cae el pH estimado frente a la ficha: en el óptimo, más ácido o más alcalino que el óptimo, o fuera de lo
    que tolera. El borde de lo que tolera cuenta como adentro, como en `outside_tolerated`."""
    optimum = f"({format_decimal(ph_opt_min)} a {format_decimal(ph_opt_max)})"
    if ph < ph_min:
        return f"más ácido de lo que tolera {crop_name} {tolerated}"
    if ph > ph_max:
        return f"más alcalino de lo que tolera {crop_name} {tolerated}"
    if ph < ph_opt_min:
        return f"más ácido que el óptimo {of(crop_name)} {optimum}"
    if ph > ph_opt_max:
        return f"más alcalino que el óptimo {of(crop_name)} {optimum}"
    return f"dentro del óptimo {of(crop_name)} {optimum}"


def _missing(value: float | None) -> bool:
    return value is None or math.isnan(float(value))


def _insufficient(reason: str) -> SoilSignalResult:
    """Sin calificación: nivel y calificación nulos, no crítica, y el porqué también en las limitaciones (R1)."""
    return SoilSignalResult(INSUFFICIENT_DATA, None, False, None, (), (reason,), (reason,))
