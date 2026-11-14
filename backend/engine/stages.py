"""Las etapas de un cultivo por calendario (HU-220; specs/01-reglas.md, «La ventana de siembra»).

La duración de cada etapa sale de la ficha del cultivo (`crop_stages.days`). Desde una fecha de siembra:

- la **ventana** va del día de la siembra (día 0) al día anterior a la cosecha estimada;
- la **cosecha estimada** es la siembra más la suma de las etapas (`harvest_basis = calendar`);
- la **etapa de hoy** de una temporada en curso es la que contiene el día que lleva desde la siembra.

Es una estimación por calendario, no una observación del lote. Son funciones puras: no leen el reloj ni archivos; la
fecha de hoy y las etapas llegan como argumentos (R4, R6).
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from common.dates import add_months

CALENDAR = "calendar"
# Para qué riesgo se pregunta si una etapa es sensible (columnas `frost_sensitive` y `heat_sensitive` de `crop_stages`).
FROST, HEAT = "frost", "heat"
# Si un riesgo se evalúa en la ventana (los valores de `status` del contrato).
AVAILABLE, NOT_APPLICABLE, INSUFFICIENT_DATA = "available", "not_applicable", "insufficient_data"


@dataclass(frozen=True)
class StageSpan:
    stage: str
    days: int
    # Lo que dice la ficha de cada etapa. Nulo: la ficha no lo dice con fuente (R1, R8).
    kc: float | None = None
    frost_sensitive: bool | None = None
    heat_sensitive: bool | None = None

    def sensitive(self, risk: str) -> bool | None:
        return self.frost_sensitive if risk == FROST else self.heat_sensitive


@dataclass(frozen=True)
class StageToday:
    # Nula si el cultivo no tiene etapas (por ejemplo, el descanso).
    stage: str | None
    # Qué tanto de la etapa lleva, de 0 a 100.
    stage_progress_pct: float | None
    # Días desde la siembra (el día de la siembra es el 0).
    days_since_sowing: int
    harvest_estimate: date | None
    # Ya pasó la cosecha estimada y no se ha registrado la cosecha: la etapa se queda en la última, al 100 %.
    harvest_due: bool
    stage_method: str = CALENDAR


@dataclass(frozen=True)
class StagePeriod:
    """Una etapa dentro de la ventana: del día `start` al día `end`, los dos incluidos."""

    span: StageSpan
    start: date
    end: date


@dataclass(frozen=True)
class WindowMonth:
    """Un mes que toca la ventana, con las etapas que caen en él. `year` es el del mes: en una ventana que pasa de
    diciembre a enero, enero es del año siguiente."""

    year: int
    month: int
    days: int
    stages: tuple[str, ...]
    periods: tuple[StagePeriod, ...]

    def sensitive(self, risk: str) -> bool | None:
        """Si alguna de sus etapas es sensible a `risk`. Nulo si ninguna lo es y alguna no lo dice (R1)."""
        values = [period.span.sensitive(risk) for period in self.periods]
        if any(values):
            return True
        return None if any(value is None for value in values) else False


@dataclass(frozen=True)
class SensitiveMonths:
    """Los meses de la ventana en que el cultivo está en una etapa sensible a un riesgo, y si el riesgo se evalúa:

    - `available`: la ficha dice la sensibilidad de todas las etapas y alguna es sensible;
    - `not_applicable`: ninguna etapa es sensible;
    - `insufficient_data`: alguna etapa no dice si es sensible, y no se sabe en qué meses mirar (R1).
    """

    status: str
    months: tuple[WindowMonth, ...]


@dataclass(frozen=True)
class CropWindow:
    sowing_date: date
    harvest_estimate: date
    periods: tuple[StagePeriod, ...]
    harvest_basis: str = CALENDAR

    @property
    def last_day(self) -> date:
        return self.harvest_estimate - timedelta(days=1)

    @property
    def length_days(self) -> int:
        return (self.harvest_estimate - self.sowing_date).days

    def stage_on(self, day: date) -> StageSpan | None:
        """La etapa de un día. Nula si el día no está en la ventana."""
        return next((period.span for period in self.periods if period.start <= day <= period.end), None)

    def months(self) -> tuple[WindowMonth, ...]:
        """Los meses que toca la ventana, en orden, con los días de cada uno que caen en ella."""
        result = []
        first = date(self.sowing_date.year, self.sowing_date.month, 1)
        current = first
        while current <= self.last_day:
            following = date(*add_months(current.year, current.month, 1), 1)
            start, end = max(current, self.sowing_date), min(following - timedelta(days=1), self.last_day)
            periods = tuple(
                StagePeriod(period.span, max(period.start, start), min(period.end, end))
                for period in self.periods
                if period.start <= end and period.end >= start
            )
            result.append(
                WindowMonth(
                    year=current.year,
                    month=current.month,
                    days=(end - start).days + 1,
                    stages=tuple(period.span.stage for period in periods),
                    periods=periods,
                )
            )
            current = following
        return tuple(result)

    def sensitive_months(self, risk: str) -> SensitiveMonths:
        """Los meses en etapa sensible a `risk` (`frost` o `heat`), con el estado de la señal que los usa."""
        if risk not in (FROST, HEAT):
            raise ValueError(f"Riesgo desconocido: {risk!r}. Es «{FROST}» o «{HEAT}».")
        values = [period.span.sensitive(risk) for period in self.periods]
        if any(value is None for value in values):
            return SensitiveMonths(INSUFFICIENT_DATA, ())
        if not any(values):
            return SensitiveMonths(NOT_APPLICABLE, ())
        return SensitiveMonths(AVAILABLE, tuple(month for month in self.months() if month.sensitive(risk)))


def crop_window(stages: list[StageSpan], sowing_date: date) -> CropWindow | None:
    """La ventana de un cultivo sembrado en `sowing_date`, con sus etapas en orden.

    Sin etapas, o con una etapa sin días, no hay ventana: devuelve `None` y las señales que la necesitan quedan en
    `insufficient_data` (R1). El descanso no tiene etapas: su duración la dice su ficha, no esta función.
    """
    if not stages or any(span.days <= 0 for span in stages):
        return None
    periods = []
    start = sowing_date
    for span in stages:
        end = start + timedelta(days=span.days - 1)
        periods.append(StagePeriod(span, start, end))
        start = end + timedelta(days=1)
    return CropWindow(sowing_date=sowing_date, harvest_estimate=start, periods=tuple(periods))


def monthly_sowing_windows(stages: list[StageSpan], start: date, months: int = 12) -> tuple[CropWindow, ...]:
    """Una ventana por mes de siembra, desde `start` y durante `months` meses (HU-192; specs/01-reglas.md, «La
    ventana de siembra»: las ventanas se comparan por mes).

    El mes `i` se cuenta desde `start`, no encadenado desde el mes anterior: el mismo día del mes, recortado al último
    día si ese mes es más corto (el 31 de enero da el 28 o 29 de febrero y vuelve al 31 en marzo). Cada ventana es la
    de `crop_window` para esa fecha, la misma que usa el diagnóstico. Si `crop_window` no da ventana (sin etapas o con
    una etapa sin días), ese mes se omite (R1). `start` entra como argumento: el motor no lee el reloj (R4).
    """
    windows = []
    for offset in range(months):
        year, month = add_months(start.year, start.month, offset)
        sowing = date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
        window = crop_window(stages, sowing)
        if window is not None:
            windows.append(window)
    return tuple(windows)


def stage_today(stages: list[StageSpan], sowing_date: date, today: date) -> StageToday:
    """La etapa de `today` para un cultivo sembrado en `sowing_date`, con las etapas en orden."""
    day = max((today - sowing_date).days, 0)
    window = crop_window(stages, sowing_date)
    if window is None:
        return StageToday(stage=None, stage_progress_pct=None, days_since_sowing=day, harvest_estimate=None, harvest_due=False)
    current = sowing_date + timedelta(days=day)
    for period in window.periods:
        if current <= period.end:
            progress = round((current - period.start).days / period.span.days * 100, 1)
            return StageToday(period.span.stage, progress, day, window.harvest_estimate, harvest_due=False)
    return StageToday(stages[-1].stage, 100.0, day, window.harvest_estimate, harvest_due=True)
