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

**La historia del terreno** (decisión 6) sale una sola vez por consulta de `terrain_history` (HU-081), y `filter` y
`soil_health` la pasan igual al filtro y a la salud del suelo de todas las estrategias, sugeridas y actual (R4). Pasar
el catálogo, las reglas y el suelo a los tipos del motor es de la ruta (HU-084).
"""

from collections.abc import Mapping, Sequence
from datetime import date

from backend.api.calc_models import Cycle
from backend.api.window_diagnosis import WindowDiagnosis, WindowQuery, diagnose_window
from backend.engine.market_signal import MarketSignalResult, harvest_years_share
from backend.engine.rotations.candidates import FALLOW, CropInfo
from backend.engine.rotations.cycles import PlannedCycle, cycle_days, gap_days, plan_cycles
from backend.engine.rotations.exclusions import (
    CycleDiagnosis,
    Diagnoser,
    FilterResult,
    SignalReason,
    SoilPh,
    SuitabilityExplainer,
    filter_strategies,
)
from backend.engine.rotations.history import terrain_history
from backend.engine.rotations.ranking import CycleScores
from backend.engine.rotations.rules import FilterRule
from backend.engine.rotations.soil_health import Criterion, HealthRule, SlopeInfo, SoilCarbon, SoilCrop, soil_health
from backend.engine.signal_score import SignalScore, signal_scores
from common import signal_sources


class StrategyCycles:
    """Los ciclos de las estrategias de una consulta que empiezan en `sowing_date`, con los diagnósticos en caché y la
    historia del terreno de la consulta (`previous_crop_ids` y `current_crop_ids` del cuerpo de `/rotations`)."""

    def __init__(
        self,
        query: WindowQuery,
        sowing_date: date,
        previous_crop_ids: Sequence[str] = (),
        current_crop_ids: Sequence[str] | None = None,
    ) -> None:
        self.query = query
        self.sowing_date = sowing_date
        self.history = terrain_history(previous_crop_ids, current_crop_ids)
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

    def cycle_scores(self, planned: Sequence[PlannedCycle]) -> tuple[CycleScores, ...]:
        """Lo que el orden de las estrategias (HU-082) lee de cada ciclo: su `kind` del catálogo, las calificaciones de
        sus señales, las mismas de `cycles`, y para el ingreso (HU-241) el porcentaje de años en que el mes de su cosecha
        tuvo mejor precio, de la misma historia de `signals.market.price_history`. Nulas en el descanso, que no tiene
        diagnóstico. El factor que más limita lo calcula el orden con los pesos de quien consulta (`self.query.weights`)."""
        result = []
        for cycle in planned:
            found = self.diagnosis(cycle)
            signals = None if found is None or found.signals is None else signal_scores(found.signals)
            market = None if found is None or found.signals is None else found.signals.get("market")
            share = harvest_years_share(market.price_history) if isinstance(market, MarketSignalResult) else None
            result.append(CycleScores(self.query.dataset.crops[cycle.crop_id]["kind"], signals, share))
        return tuple(result)

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

    def filter(
        self,
        candidates: Sequence[Sequence[str]],
        crops: Mapping[str, CropInfo],
        rules: Sequence[FilterRule],
        soil: SoilPh | None,
        explain: SuitabilityExplainer,
        limit: int = 10,
    ) -> FilterResult:
        """El filtro de HU-081 con la historia del terreno de la consulta, la temperatura de la zona (o del lote) con que
        se decide la aptitud y el diagnóstico de cada ciclo para el alto riesgo."""
        return filter_strategies(
            candidates,
            self.history.crop_ids,
            crops,
            rules,
            self.query.zone.tmean_annual_c,
            soil,
            explain,
            self.diagnoser(),
            limit,
            history_basis=self.history.basis,
        )

    def soil_health(
        self,
        planned: Sequence[PlannedCycle],
        crops: Mapping[str, SoilCrop],
        rules: Sequence[HealthRule],
        soil: SoilCarbon | None = None,
        slope: SlopeInfo | None = None,
    ) -> dict[str, Criterion]:
        """La salud del suelo de HU-212 con la historia del terreno de la consulta y los días y huecos de estos mismos
        ciclos (R4)."""
        return soil_health(
            [cycle.crop_id for cycle in planned],
            crops,
            self.history.crop_ids,
            rules,
            soil,
            slope,
            cycle_days(planned),
            gap_days(planned),
            history_basis=self.history.basis,
        )


def _source_ids(source: signal_sources.SignalSource | None) -> tuple[str, ...]:
    """La fuente que calcula la señal y, en el agua, la de la ET0. Vacía si `sources.yaml` no la nombra."""
    if source is None:
        return ()
    return (source.used, source.et0) if source.et0 else (source.used,)
