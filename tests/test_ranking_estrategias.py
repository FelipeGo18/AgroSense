"""HU-082: lo que el orden de las estrategias lee de cada ciclo (`StrategyCycles.cycle_scores`), con el dataset de
ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá, desde el 1 de abril de 2027."""

from backend.api.strategy_cycles import StrategyCycles
from backend.engine.rotations.ranking import NO_CRITERION, criteria
from tests.test_ciclos_estrategia import strategy
from tests.test_ciclos_estrategia import today as today  # noqa: F401 (fixture: «hoy» fijo)
from tests.test_diagnostico import EXAMPLES, NO_WATER, use


def test_cada_ciclo_da_su_kind_y_las_calificaciones_de_su_diagnostico(monkeypatch):
    use(monkeypatch, EXAMPLES)
    cycles: StrategyCycles = strategy()
    planned = cycles.plan(("papa", "arveja", "descanso"))
    assert planned is not None
    found = cycles.cycle_scores(planned)
    assert [c.kind for c in found] == ["crop", "crop", "fallow"]
    assert found[2].signals is None
    contract = cycles.cycles(planned)
    for scores, cycle in zip(found[:2], contract[:2], strict=True):
        assert cycle.diagnosis is not None and cycle.diagnosis.signals is not None and scores.signals is not None
        assert {n: (s.status, s.score, s.level, s.critical) for n, s in scores.signals.items()} == {
            n: (s.status, s.score, s.level, s.critical) for n, s in cycle.diagnosis.signals.items()
        }
        # El factor limitante que lee `risk` es el que muestra el ciclo.
        assert scores.limiting_signal == cycle.limiting_signal
    # En el ejemplo la papa y la arveja no tienen dato de agua: su luz es `not_evaluable`, sin factor limitante, así
    # que el agua y el riesgo no califican y se dice (R1).
    assert [c.diagnosis.signals["water"].status for c in contract[:2] if c.diagnosis and c.diagnosis.signals] == ["insufficient_data"] * 2
    assert [c.light for c in contract[:2]] == ["not_evaluable"] * 2
    scores, limitations = criteria(("papa", "arveja", "descanso"), found, {})
    assert (scores["water"], scores["risk"]) == (None, None)
    assert {NO_CRITERION["water"], NO_CRITERION["risk"]} <= set(limitations)


def test_con_peso_cero_en_el_agua_el_riesgo_es_el_menor_factor_limitante_que_muestran_los_ciclos(monkeypatch):
    """Sin peso en el agua la luz no es `not_evaluable`: cada ciclo muestra su factor limitante y `risk` es el menor de
    sus calificaciones."""
    use(monkeypatch, EXAMPLES)
    cycles: StrategyCycles = strategy(priorities=NO_WATER)
    planned = cycles.plan(("papa", "arveja", "descanso"))
    assert planned is not None
    contract = cycles.cycles(planned)
    shown = [c.diagnosis.signals[c.limiting_signal].score for c in contract if c.diagnosis and c.diagnosis.signals and c.limiting_signal]
    assert len(shown) == 2
    scores, _ = criteria(("papa", "arveja", "descanso"), cycles.cycle_scores(planned), {})
    assert scores["risk"] == min(shown)
