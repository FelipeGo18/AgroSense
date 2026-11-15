"""Lo que comparten las señales de heladas (HU-077) y calor (HU-190): las dos se miden solo en los meses de la ventana en
que el cultivo está en una etapa sensible (`CropWindow.sensitive_months`, HU-142 y HU-220), y las dos dicen lo mismo
cuando no se evalúan (specs/01-reglas.md, «Señales de una ventana»).

- `sensitive_window` traduce la ventana a una de dos cosas: el resultado de una señal que no se evalúa (`not_applicable`
  o `insufficient_data`, con su razón) o los meses que sí se evalúan (`SensitiveWindow`), con la limitación de los
  meses `unknown` (los de etapas sin el dato con fuente, que no se evalúan, R1). Una ventana nula (un cultivo sin
  etapas, como el descanso) se resuelve aquí, una sola vez para las dos señales.
- `ClimateSignalResult` es el resultado de las dos señales, con los nombres de campo del contrato.
- Los textos de las razones (meses, etapas y periodo) se arman aquí una sola vez; los números y las listas, con
  `common/text.py`, el mismo formato que la razón de la aptitud.

Funciones puras (R6): no leen archivos, ni el dataset, ni la configuración; el periodo normal llega ya leído
(`ClimateNormal`). Es historia de la zona, nunca un pronóstico (decisión 4).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, SignalScore
from backend.engine.stages import FROST, HEAT, NOT_APPLICABLE, CropWindow, WindowMonth
from common.months import month_name
from common.text import join, of

# `quality` de las tablas del clima por mes (`climate_frost_month`, `climate_risk_month`): el mes está completo (en
# `climate_risk_month`, con al menos los años que pide el periodo normal). Cualquier otro valor (`partial`) no basta
# para decir que no pasó nada (R1).
COMPLETE = "ok"

# A qué es sensible el cultivo, como se dice en una razón.
SENSITIVE_TO = {FROST: "sensible a la helada", HEAT: "sensible al calor"}
# Las etapas de FAO-56 (`crop_stages.stage`), nombradas como las dice el manual y como las muestra la web
# (`web/src/features/farm/seasons.ts`, `STAGE_NAMES`, que en la ficha abrevia «Desarrollo»): sin inventar otras
# («floración», «llenado»).
STAGE_NAMES = {"initial": "la etapa inicial", "development": "la etapa de desarrollo", "mid": "la etapa media", "late": "la etapa final"}
# Cuando el cultivo es sensible en todas las etapas de la ventana, se dice así en vez de enumerarlas.
WHOLE_CROP = "todo el cultivo"


@dataclass(frozen=True)
class ClimateNormal:
    """El periodo normal del clima (`climate_normal` de `pipeline/region.yaml`, que la API lee del manifiesto y valida):
    los años que se cuentan, del primero al último incluidos, y cuántos tienen que tener dato."""

    first_year: int
    last_year: int
    min_years: int


@dataclass(frozen=True)
class ClimateSignalResult:
    """La señal `frost` o `heat` de una ventana, con los nombres de campo del contrato (specs/02-contratos.md).

    No trae `counts`: si la señal cuenta para la luz lo deciden los pesos en el semáforo (HU-074) y lo pone el
    ensamblado de la respuesta (HU-076), no esta señal. `limitations` son las de la señal: los meses que no se
    evaluaron, el aviso fijo de la fuente y, si no hay calificación por falta de datos, el porqué (R1).
    """

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SensitiveWindow:
    """Lo que una señal evalúa: la fecha de siembra; los meses en etapa sensible a `risk`, en orden; si el cultivo es
    sensible en todas las etapas de la ventana; las limitaciones que ya se saben (los meses `unknown` y los avisos de
    quien llama); y el periodo normal, que aquí ya no es nulo."""

    sowing_date: date
    risk: str
    months: tuple[WindowMonth, ...]
    whole_crop: bool
    limitations: tuple[str, ...]
    normal: ClimateNormal

    def stage_names(self, months: Sequence[WindowMonth] | None = None) -> str:
        """Las etapas sensibles de esos meses (todos los sensibles si no se dicen): «la etapa media y la etapa final», o
        «todo el cultivo» si es sensible en todas sus etapas y se evalúan todos sus meses."""
        months = self.months if months is None else tuple(months)
        if self.whole_crop and months == self.months:
            return WHOLE_CROP
        return _stage_names(_stages(months, True, self.risk))

    def where(self, months: Sequence[WindowMonth] | None = None) -> str:
        """«la etapa media (de octubre a diciembre)» o «todo el cultivo (de agosto a enero)»."""
        months = self.months if months is None else months
        return f"{self.stage_names(months)} ({months_phrase(months)})"


def sensitive_window(
    window: CropWindow | None, risk: str, crop_name: str, normal: ClimateNormal | None, notices: tuple[str, ...] = ()
) -> ClimateSignalResult | SensitiveWindow:
    """Los meses que evalúa la señal de `risk` (`frost` o `heat`), o el resultado si no se evalúa.

    `window` es la de `crop_window`, nula si el cultivo no tiene etapas (el descanso): sin etapas no se sabe qué meses
    son sensibles y la señal es `insufficient_data` (R1). `crop_name` es el nombre con su artículo («la papa»).
    `notices` son avisos fijos que van en las limitaciones en toda respuesta, se evalúe o no la señal (el
    `frost_caveat` de la región). Sin el periodo normal (un dataset publicado sin él) no se puede decir qué años se
    cuentan: `insufficient_data` (R1).
    """
    if window is None:
        return insufficient(no_stages_reason(crop_name), notices)
    sensitive = window.sensitive_months(risk)
    sensitive_to = SENSITIVE_TO[risk]
    if sensitive.status == NOT_APPLICABLE:
        reason = f"Según su ficha, ninguna etapa {of(crop_name)} es {sensitive_to}"
        return ClimateSignalResult(NOT_APPLICABLE, None, False, None, (), (reason,), notices)
    if sensitive.status == INSUFFICIENT_DATA:
        return insufficient(
            f"La ficha {of(crop_name)} no dice con fuente si alguna etapa es {sensitive_to}: la señal no se evalúa", notices
        )
    if normal is None:
        return insufficient("Sin el periodo de referencia del clima de la zona: la señal no se evalúa", notices)
    unknown = ()
    if sensitive.unknown:
        unknown = (
            f"La ficha {of(crop_name)} no dice con fuente si es {sensitive_to} en "
            f"{_stage_names(_stages(sensitive.unknown, None, risk))} ({months_phrase(sensitive.unknown)}): "
            f"{not_evaluated(sensitive.unknown)}",
        )
    whole_crop = all(period.span.sensitive(risk) for period in window.periods)
    return SensitiveWindow(window.sowing_date, risk, sensitive.months, whole_crop, unknown + notices, normal)


def no_stages_reason(crop_name: str) -> str:
    """La razón de una señal que no se evalúa porque el cultivo no tiene etapas publicadas (sin ventana). La comparten
    las heladas, el calor y el suelo (HU-183), que sin ventana tampoco se califica."""
    return f"Sin las etapas {of(crop_name)}: la señal no se evalúa"


def insufficient(reason: str, limitations: tuple[str, ...] = ()) -> ClimateSignalResult:
    """Sin calificación por falta de datos: nivel y `score` nulos, no crítica, y el porqué también en las limitaciones."""
    return ClimateSignalResult(INSUFFICIENT_DATA, None, False, None, (), (reason,), (reason, *limitations))


def scored(score: SignalScore, indicator: str, reason: str, limitations: tuple[str, ...]) -> ClimateSignalResult:
    """Con la calificación de `score_signal`, que ya dio el nivel y si es crítica (HU-196)."""
    return ClimateSignalResult(AVAILABLE, score.level, score.critical, score.score, (indicator,), (reason,), limitations)


def period_phrase(normal: ClimateNormal) -> str:
    """«de 1991 a 2020»."""
    return f"de {normal.first_year} a {normal.last_year}"


def months_phrase(months: Sequence[WindowMonth]) -> str:
    """«diciembre», «de noviembre a enero» si los meses son seguidos, o «octubre y diciembre» si no lo son.

    Los meses llegan en orden cronológico, con su año. Un mes a doce meses o más del primero repetiría el nombre de un
    mes anterior y se dice con su año, contado desde el año del primero: «de agosto a octubre del año siguiente» (R5:
    una ventana de agosto de 2026 a octubre de 2027 no es «de agosto a octubre» ni «de agosto a julio»).
    """
    first = months[0]
    names = [_dated_name(first, month) for month in months]
    if len(names) == 1:
        return names[0]
    consecutive = all(
        (after.year, after.month) == (before.year + before.month // 12, before.month % 12 + 1) for before, after in pairwise(months)
    )
    return f"de {names[0]} a {names[-1]}" if consecutive else join(names)


# Cuántos años después del primer mes cae un mes, como se dice tras su nombre.
_YEARS_LATER = {1: "del año siguiente", 2: "de dos años después", 3: "de tres años después"}


def _dated_name(first: WindowMonth, month: WindowMonth) -> str:
    """El nombre del mes, con su año relativo al del primero si está a doce meses o más de él."""
    name = month_name(month.month)
    if (month.year - first.year) * 12 + month.month - first.month < 12:
        return name
    offset = month.year - first.year
    return f"{name} {_YEARS_LATER.get(offset, f'de {offset} años después')}"


def not_evaluated(months: Sequence[WindowMonth]) -> str:
    """«ese mes no se evaluó» o «esos meses no se evaluaron»."""
    return "esos meses no se evaluaron" if len(months) > 1 else "ese mes no se evaluó"


def _stages(months: Sequence[WindowMonth], sensitive: bool | None, risk: str) -> tuple[str, ...]:
    """Las etapas de esos meses cuya sensibilidad a `risk` es `sensitive`, en orden y sin repetir."""
    found = [period.span.stage for month in months for period in month.periods if period.span.sensitive(risk) is sensitive]
    return tuple(dict.fromkeys(found))


def _stage_names(stages: Iterable[str]) -> str:
    return join(STAGE_NAMES[stage] for stage in stages)
