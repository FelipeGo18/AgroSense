"""La etapa de un cultivo por calendario (HU-220; specs/01-reglas.md, «La ventana de siembra»).

La duración de cada etapa sale de la ficha del cultivo (`crop_stages.days`): la etapa de hoy es la que contiene el día
que lleva desde la siembra, y la cosecha estimada es la siembra más la suma de las etapas (`harvest_basis = calendar`).
Es una estimación por calendario, no una observación del lote.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StageSpan:
    stage: str
    days: int


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
    stage_method: str = "calendar"


def stage_today(stages: list[StageSpan], sowing_date: date, today: date) -> StageToday:
    """La etapa de `today` para un cultivo sembrado en `sowing_date`, con las etapas en orden."""
    day = max((today - sowing_date).days, 0)
    total = sum(span.days for span in stages)
    if not stages or total <= 0:
        return StageToday(stage=None, stage_progress_pct=None, days_since_sowing=day, harvest_estimate=None, harvest_due=False)
    harvest = sowing_date + timedelta(days=total)
    start = 0
    for span in stages:
        if day < start + span.days:
            progress = round((day - start) / span.days * 100, 1)
            return StageToday(span.stage, progress, day, harvest, harvest_due=False)
        start += span.days
    return StageToday(stages[-1].stage, 100.0, day, harvest, harvest_due=True)
