"""La señal de calor: si en los meses en que el cultivo está en una etapa sensible al calor suele hacer más calor del
que aguanta (HU-190; specs/01-reglas.md, «Señales de una ventana» y «Cómo se califica cada señal»).

El valor es `tmax_p90_c` de `climate_risk_month` (la máxima que se supera uno de cada diez días del mes, en el periodo
normal), y de los meses sensibles se toma **el más alto**: el peor caso. Un calor que daña en cualquiera de los meses
sensibles basta, igual que las heladas cuentan una helada en cualquiera de ellos y que la ventana vale lo que su
factor más bajo (R2, ley del mínimo); un promedio escondería el mes que daña. Decisión del 14 de noviembre de 2026,
pendiente de aprobación de Felipe (docs/registro-de-decisiones.md).

- `climate_risk_month` es climatológica (un valor por mes del año): los meses de la ventana se buscan solo por número
  de mes, y una ventana de más de doce meses no cuenta dos veces el mismo mes.
- Un mes sensible se califica solo si su fila es `ok` y trae `tmax_p90_c` (no nulo ni NaN). Uno sin dato o `partial`
  (con menos años que los que pide el periodo normal) no cuenta y va a las limitaciones; si ninguno tiene,
  `insufficient_data` (R1). La razón nombra solo los meses que se evaluaron (R5).
- La curva sale de la ficha (`temp_opt_max_c` → 100, `heat_max_c` → 0, sin límite inferior) y la calificación, el
  nivel y si es crítica salen solo de `score_signal` (HU-196). Sin esos límites con fuente: `insufficient_data` (R1, R8).

Función pura (R6): las filas por mes llegan ya leídas para el municipio, sin filtrar (`backend/api/climate_signals.py`);
qué fila sirve lo decide esta señal. Es historia de la zona, nunca un pronóstico (decisión 4).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.engine.sensitive_signal import (
    COMPLETE,
    WHOLE_CROP,
    ClimateNormal,
    ClimateSignalResult,
    insufficient,
    months_phrase,
    not_evaluated,
    period_phrase,
    scored,
    sensitive_window,
)
from backend.engine.signal_score import AVAILABLE, score_signal
from backend.engine.stages import HEAT, CropWindow, WindowMonth
from common.months import month_name
from common.text import format_number

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

INDICATOR = "tmax_p90_c"


@dataclass(frozen=True)
class HeatMonth:
    """Una fila de `climate_risk_month`: la máxima p90 de un mes del año (nula si no hay dato) y si el mes tiene los
    años que pide el periodo normal (`quality`)."""

    tmax_p90_c: float | None
    quality: str

    def usable(self) -> bool:
        return self.quality == COMPLETE and _has_value(self.tmax_p90_c)


def heat_signal(
    window: CropWindow | None,
    heat_months: Mapping[int, HeatMonth],
    crop_limits: Mapping[str, Any],
    normal: ClimateNormal | None,
    thresholds: Thresholds,
    crop_name: str,
) -> ClimateSignalResult:
    """La señal `heat` de la ventana (nula si el cultivo no tiene etapas). `heat_months` va por mes (1 a 12);
    `crop_limits` es la ficha del cultivo (al menos `temp_opt_max_c` y `heat_max_c`); `crop_name` lleva su artículo
    («la papa»)."""
    plan = sensitive_window(window, HEAT, crop_name, normal)
    if isinstance(plan, ClimateSignalResult):
        return plan
    with_data = [month for month in plan.months if month.month in heat_months and heat_months[month.month].usable()]
    if not with_data:
        return insufficient(f"Sin datos de temperatura máxima de la zona en {plan.where()}", plan.limitations)
    limitations = _skipped(plan.months, heat_months) + plan.limitations
    distinct = _distinct(with_data)
    # El más alto; en un empate, el primero de la ventana.
    hottest = max((month.month for month in distinct), key=lambda month: heat_months[month].tmax_p90_c)
    value = heat_months[hottest].tmax_p90_c
    score = score_signal(HEAT, value, thresholds, crop_limits)
    if score.status != AVAILABLE:
        reason = (
            f"Los límites de temperatura de la ficha de {crop_name} (temp_opt_max_c y heat_max_c) no están completos "
            "con fuente: el calor no se califica"
        )
        return insufficient(reason, limitations)
    # La frase va sobre los meses evaluados en orden cronológico, con su año: una ventana de más de doce meses dice
    # hasta dónde llega de verdad. Sin repetir meses solo van el máximo y las limitaciones.
    when = months_phrase(with_data)
    stages = plan.stage_names(with_data)
    where = f"en {stages} ({when})" if stages == WHOLE_CROP else _months_first(when, stages)
    hottest_note = f" (el mes más caluroso, {month_name(hottest)})" if len(distinct) > 1 else ""
    reason = (
        f"{period_phrase(plan.normal).capitalize()}, {where}, "
        f"la máxima pasó de {format_number(value)} °C uno de cada diez días{hottest_note}; "
        f"{crop_name} aguanta hasta {format_number(float(crop_limits['heat_max_c']))} °C"
    )
    return scored(score, INDICATOR, reason, limitations)


def _distinct(months: Sequence[WindowMonth]) -> list[WindowMonth]:
    """Cada mes del año una vez, en su primera aparición: la tabla es climatológica, y una ventana de más de doce meses
    no cuenta (ni nombra) dos veces el mismo mes."""
    first: dict[int, WindowMonth] = {}
    for month in months:
        first.setdefault(month.month, month)
    return list(first.values())


def _months_first(when: str, stages: str) -> str:
    """«de septiembre a noviembre (la etapa media y la etapa final)», «en octubre (la etapa media)»."""
    return f"{when if when.startswith('de ') else f'en {when}'} ({stages})"


def _skipped(months: tuple[WindowMonth, ...], heat_months: Mapping[int, HeatMonth]) -> tuple[str, ...]:
    """Las limitaciones de los meses sensibles que no se califican: sin dato, o `partial` (R1). Cada mes una vez."""
    missing: list[WindowMonth] = []
    partial: list[WindowMonth] = []
    for month in _distinct(months):
        row = heat_months.get(month.month)
        if row is None or not _has_value(row.tmax_p90_c):
            missing.append(month)
        elif row.quality != COMPLETE:
            partial.append(month)
    notes = []
    if missing:
        notes.append(f"Sin temperatura máxima de la zona en {months_phrase(missing)}: {not_evaluated(missing)} para el calor")
    if partial:
        notes.append(
            f"La temperatura máxima de la zona en {months_phrase(partial)} tiene menos años que los que pide el periodo: "
            f"{not_evaluated(partial)} para el calor"
        )
    return tuple(notes)


def _has_value(value: float | None) -> bool:
    return value is not None and not math.isnan(value)
