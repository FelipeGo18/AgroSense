"""Los ciclos de una estrategia con sus fechas (HU-213; specs/01-reglas.md, «Estrategias de rotación», paso 1).

El primer ciclo se siembra en `sowing_date`. Cada ciclo siguiente se siembra el lunes siguiente a la cosecha estimada
del anterior (decisión 15): de 0 a 6 días después, y una cosecha en lunes se resiembra ese mismo día. La duración de un
cultivo o de un abono verde sale de sus etapas por calendario (HU-220, `crop_window`); la de un descanso, de
`fallow_days` de su ficha (HU-063). El descanso no tiene ventana ni diagnóstico.

Las fechas de los ciclos, los días de cada uno y los huecos entre ellos que recibe `soil_health` (HU-212) salen de este
mismo cálculo (R4). Son funciones puras: no leen el reloj ni archivos (R4, R6).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from backend.engine.stages import CALENDAR, CropWindow, StageSpan, crop_window

MONDAY = 0


def next_sowing(harvest: date) -> date:
    """El lunes siguiente a la cosecha estimada: de 0 a 6 días después; si la cosecha cae en lunes, ese mismo día."""
    return harvest + timedelta(days=(MONDAY - harvest.weekday()) % 7)


@dataclass(frozen=True)
class PlannedCycle:
    """Un ciclo con sus fechas. `window` es nula en el descanso (no tiene diagnóstico); `gap_days` son los días entre la
    cosecha estimada y la siembra del ciclo siguiente, nulo en el último."""

    cycle: int
    crop_id: str
    sowing_date: date
    harvest_estimate: date
    window: CropWindow | None
    gap_days: int | None
    harvest_basis: str = CALENDAR

    @property
    def days(self) -> int:
        return (self.harvest_estimate - self.sowing_date).days


def plan_cycles(
    sequence: Sequence[str],
    stages: Mapping[str, Sequence[StageSpan]],
    fallow_days: Mapping[str, int | None],
    sowing_date: date,
) -> tuple[PlannedCycle, ...] | None:
    """Los ciclos de `sequence` desde `sowing_date`, en orden.

    `fallow_days` trae los descansos del catálogo (`crop_id` → días de su ficha, o nulo sin dato); los demás `crop_id`
    son cultivos o abonos verdes, con sus etapas en `stages`. Si a un ciclo le falta la duración (un cultivo sin etapas,
    o un descanso sin días), devuelve `None`: sin su cosecha estimada no se puede fechar el siguiente, y no se inventa
    (R1)."""
    dated: list[tuple[str, date, date, CropWindow | None]] = []
    sowing = sowing_date
    for crop_id in sequence:
        if crop_id in fallow_days:
            days = fallow_days[crop_id]
            if days is None or days <= 0:
                return None
            window, harvest = None, sowing + timedelta(days=days)
        else:
            window = crop_window(list(stages.get(crop_id, ())), sowing)
            if window is None:
                return None
            harvest = window.harvest_estimate
        dated.append((crop_id, sowing, harvest, window))
        sowing = next_sowing(harvest)
    return tuple(
        PlannedCycle(
            cycle=number,
            crop_id=crop_id,
            sowing_date=start,
            harvest_estimate=harvest,
            window=window,
            gap_days=(dated[number][1] - harvest).days if number < len(dated) else None,
        )
        for number, (crop_id, start, harvest, window) in enumerate(dated, start=1)
    )


def cycle_days(cycles: Sequence[PlannedCycle]) -> tuple[int, ...]:
    """Los días de cada ciclo, de la siembra a la cosecha estimada (`cycle_days` de `soil_health`)."""
    return tuple(cycle.days for cycle in cycles)


def gap_days(cycles: Sequence[PlannedCycle]) -> tuple[int | None, ...]:
    """Los días de suelo descubierto después de cada ciclo, nulo en el último (`gap_days` de `soil_health`)."""
    return tuple(cycle.gap_days for cycle in cycles)
