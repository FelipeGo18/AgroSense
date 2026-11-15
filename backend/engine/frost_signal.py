"""La señal de heladas: qué tan seguido ha helado en los meses en que el cultivo está en una etapa sensible (HU-077;
specs/01-reglas.md, «Señales de una ventana» y «Cómo se califica cada señal»; specs/02-contratos.md, «Heladas de una
ventana», aprobado por Felipe el 10 de noviembre de 2026).

`frost_freq_pct` es el porcentaje de años con al menos una helada en **cualquiera** de los meses sensibles de la
ventana, no el promedio de los meses, porque así cuentan los años los cortes del ZARC de `thresholds.yaml`. Se cuenta
con `climate_frost_month` (días con helada de cada mes de cada año):

- **Proyección:** cada mes sensible tiene su desfase respecto al año de siembra (0, o 1 si la ventana pasa de diciembre
  a enero). Para cada año `Y` del periodo normal (de `first_year` a `last_year`, incluidos), los meses de ese año son
  `(Y + desfase, mes)`: sembrando en agosto de cualquier año, el enero sensible es el del año siguiente. Por eso la
  razón dice «sembrando de A a B»: el periodo es el de los años de siembra.
- **Un año con helada** tiene algún mes sensible con `frost_days` ≥ 1, sea `ok` o `partial`, aunque le falte otro
  mes: la helada está confirmada. **Un año sin helada** tiene todos sus meses sensibles presentes, `ok` y con
  `frost_days` = 0. **En otro caso** (falta un mes, o uno es `partial`, y en los demás no heló) ese año no cuenta (R1):
  es la lectura literal del contrato («en otro caso (falta dato y no heló) ese año no cuenta»).
- Sin ningún año que cuente, o con menos que `min_years`, la señal es `insufficient_data` (R1).

La calificación, el nivel y si es crítica salen solo de `score_signal` (HU-196). `frost_freq_pct` se le pasa sin
redondear; la razón muestra los años contados y el porcentaje redondeado.

Función pura (R6): las filas de heladas llegan ya leídas y filtradas para el municipio
(`backend/api/climate_signals.py`). Es historia de la zona, nunca un pronóstico (decisión 4).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.engine.sensitive_signal import (
    COMPLETE,
    ClimateNormal,
    ClimateSignalResult,
    insufficient,
    period_phrase,
    scored,
    sensitive_window,
)
from backend.engine.signal_score import round_half_up, score_signal
from backend.engine.stages import FROST, CropWindow, WindowMonth
from common.months import month_name

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

INDICATOR = "frost_freq_pct"


@dataclass(frozen=True)
class FrostMonth:
    """Una fila de `climate_frost_month`: días con helada de un mes de un año, y si el mes está completo (`quality`)."""

    frost_days: int
    quality: str


def frost_signal(
    window: CropWindow | None,
    frost_months: Mapping[tuple[int, int], FrostMonth],
    normal: ClimateNormal | None,
    thresholds: Thresholds,
    crop_name: str,
    caveat: str | None = None,
) -> ClimateSignalResult:
    """La señal `frost` de la ventana (nula si el cultivo no tiene etapas). `frost_months` va por `(año, mes)`;
    `crop_name` lleva su artículo («la papa»).

    `caveat` (el `frost_caveat` de la región en `catalog/sources.yaml`) va en las limitaciones de toda respuesta, se
    evalúe o no la señal (HU-077, aprobado por Felipe el 13 de noviembre de 2026).
    """
    plan = sensitive_window(window, FROST, crop_name, normal, (caveat,) if caveat else ())
    if isinstance(plan, ClimateSignalResult):
        return plan
    normal = plan.normal
    frosty, counted = _count_frost_years(plan.months, plan.sowing_date.year, frost_months, normal)
    sown = f"sembrando {period_phrase(normal)}"
    if counted == 0:
        return insufficient(f"Sin datos de heladas del municipio en {plan.where()}, {sown}", plan.limitations)
    if counted < normal.min_years:
        total = normal.last_year - normal.first_year + 1
        return insufficient(
            f"Sin datos suficientes de heladas en {plan.where()}: solo {counted} de los {total} años, {sown}, "
            f"se pudieron contar y hacen falta {normal.min_years}",
            plan.limitations,
        )
    pct = 100 * frosty / counted
    score = score_signal(FROST, pct, thresholds)
    sowing = f"Sembrando en {month_name(plan.sowing_date.month)}"
    years = f"los {counted} años con dato, {sown}"
    if frosty == 0:
        reason = f"{sowing}, no heló ningún año en {plan.where()}, entre {years}"
    elif frosty == counted:
        reason = f"{sowing}, heló todos los años en {plan.where()}, entre {years}"
    else:
        reason = f"{sowing}, heló en {plan.where()} {round_half_up(pct)} de cada 100 años: en {frosty} de {years}"
    return scored(score, INDICATOR, reason, plan.limitations)


def _count_frost_years(
    months: Sequence[WindowMonth], sowing_year: int, frost_months: Mapping[tuple[int, int], FrostMonth], normal: ClimateNormal
) -> tuple[int, int]:
    """(años con helada, años que cuentan) en el periodo normal, con el método del contrato (ver el docstring del
    módulo)."""
    offsets = [(month.year - sowing_year, month.month) for month in months]
    frosty = counted = 0
    for year in range(normal.first_year, normal.last_year + 1):
        rows = [frost_months.get((year + offset, month)) for offset, month in offsets]
        if any(row is not None and row.frost_days >= 1 for row in rows):
            frosty += 1
            counted += 1
        elif all(row is not None and row.quality == COMPLETE for row in rows):
            counted += 1
    return frosty, counted
