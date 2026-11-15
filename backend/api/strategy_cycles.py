"""Los ciclos de una estrategia con su diagnóstico, con la forma del contrato (HU-213; `strategies[].cycles` de
`POST /api/v1/rotations`).

Las fechas salen del motor (`backend/engine/rotations/cycles.py`: el lunes siguiente a la cosecha estimada, y el
descanso con los días de su ficha). El diagnóstico de cada ciclo sale de `diagnose_window`, la misma función que
`/diagnostics`, con la consulta ya leída (`window_query`): los pesos de `signal_priorities` o, sin ellos, los de
`weights.yaml`, y con `lot_id`, el suelo, la altitud y el riego del lote. Un ciclo que cae más de doce meses después de
hoy se evalúa igual, con la historia de la zona: aquí no se mira la fecha de hoy (R4).

Muchas estrategias comparten ciclos (el mismo cultivo en la misma fecha): cada diagnóstico se calcula una sola vez por
cultivo y fecha en una consulta (`StrategyCycles`). Para el alto riesgo del filtro (HU-081, fase 2), `diagnoser` da las
calificaciones de cada ciclo con su razón y la fuente que calcula cada señal en la región (R2, R8). No guarda nada (R9).
"""

from collections.abc import Sequence
from datetime import date

from backend.api.calc_models import Cycle
from backend.api.window_diagnosis import WindowDiagnosis, WindowQuery, diagnose_window
from backend.engine.rotations.candidates import FALLOW
from backend.engine.rotations.cycles import PlannedCycle, plan_cycles
from backend.engine.rotations.exclusions import CycleDiagnosis, Diagnoser, SignalReason
from backend.engine.signal_score import SignalScore
from common import signal_sources


class StrategyCycles:
    """Los ciclos de las estrategias de una consulta que empiezan en `sowing_date`, con los diagnósticos en caché."""

    def __init__(self, query: WindowQuery, sowing_date: date) -> None:
        self.query = query
        self.sowing_date = sowing_date
        crops = query.dataset.crops
        # Los descansos del catálogo con los días de su ficha (HU-063); nulo si la ficha no los trae (R1).
        self._fallow_days = {crop_id: crop.get("fallow_days") for crop_id, crop in crops.items() if crop.get("kind") == FALLOW}
        self._diagnoses: dict[tuple[str, date], WindowDiagnosis] = {}

    def plan(self, sequence: Sequence[str]) -> tuple[PlannedCycle, ...] | None:
        """Las fechas de los ciclos de `sequence`; `None` si a algún ciclo le falta la duración (R1)."""
        return plan_cycles(sequence, self.query.dataset.stages, self._fallow_days, self.sowing_date)

    def diagnosis(self, cycle: PlannedCycle) -> WindowDiagnosis | None:
        """El diagnóstico del ciclo, como el de `/diagnostics` para el mismo cultivo y fecha. Nulo en el descanso."""
        if cycle.window is None:
            return None
        key = (cycle.crop_id, cycle.sowing_date)
        if key not in self._diagnoses:
            self._diagnoses[key] = diagnose_window(self.query, cycle.crop_id, cycle.sowing_date)
        return self._diagnoses[key]

    def cycles(self, planned: Sequence[PlannedCycle]) -> list[Cycle]:
        """Los ciclos con la forma del contrato: la luz con los pesos de quien consulta (`light`) y con los de AgroSense
        (`light_default`), el factor que más limita y el alto riesgo de esa luz, y el diagnóstico completo de la
        ventana. En un descanso, `light`, `light_default`, `limiting_signal` y `diagnosis` vienen nulos."""
        result = []
        for cycle in planned:
            found = self.diagnosis(cycle)
            core = None if found is None else found.core
            result.append(
                Cycle(
                    cycle=cycle.cycle,
                    crop_id=cycle.crop_id,
                    sowing_date=cycle.sowing_date,
                    harvest_estimate=cycle.harvest_estimate,
                    harvest_basis=cycle.harvest_basis,
                    light=None if core is None else core.overall.light,
                    light_default=None if core is None else core.overall_default.light,
                    limiting_signal=None if core is None else core.overall.limiting_signal,
                    high_risk=False if core is None else core.overall.high_risk,
                    diagnosis=core,
                )
            )
        return result

    def signal_reasons(self, planned: Sequence[PlannedCycle]) -> list[CycleDiagnosis | None]:
        """Lo que el filtro lee de cada ciclo para el alto riesgo: la calificación de cada señal, su primera razón y la
        fuente que la calcula en la región (`catalog/sources.yaml`; en el agua, la de la lluvia y la de la ET0). Nulo en
        el descanso y en un cultivo no apto, que no tienen señales."""
        # Se lee del módulo, como en `calculations`: las pruebas lo cambian en él (`tests/conftest.py`).
        sources = signal_sources.get_signal_sources().for_region(self.query.dataset.region["id"])
        result: list[CycleDiagnosis | None] = []
        for cycle in planned:
            found = self.diagnosis(cycle)
            if found is None or found.signals is None:
                result.append(None)
                continue
            result.append(
                {
                    name: SignalReason(
                        SignalScore(signal.status, signal.score, signal.level, signal.critical),
                        signal.reasons[0] if signal.reasons else "",
                        _source_ids(sources.get(name)),
                    )
                    for name, signal in found.signals.items()
                }
            )
        return result

    def diagnoser(self) -> Diagnoser:
        """El `diagnose` de `filter_strategies` (HU-081): un diagnóstico por ciclo de la secuencia. Una secuencia que no
        se puede fechar es un error de quien llama: tiene que mirar `plan` antes (un ciclo sin revisar podría esconder
        un riesgo grave, R2)."""

        def diagnose(sequence: Sequence[str]) -> list[CycleDiagnosis | None]:
            planned = self.plan(sequence)
            if planned is None:
                raise ValueError(f"La estrategia {tuple(sequence)} no se puede fechar: a un ciclo le falta la duración")
            return self.signal_reasons(planned)

        return diagnose


def _source_ids(source: signal_sources.SignalSource | None) -> tuple[str, ...]:
    """La fuente que calcula la señal y, en el agua, la de la ET0. Vacía si `sources.yaml` no la nombra."""
    if source is None:
        return ()
    return (source.used, source.et0) if source.et0 else (source.used,)
