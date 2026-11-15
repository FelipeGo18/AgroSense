"""HU-082: lo que el orden de las estrategias lee de cada ciclo (`StrategyCycles.cycle_scores`), con el dataset de
ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá, desde el 1 de abril de 2027."""

from backend.api.calc_models import Cycle
from backend.api.strategy_cycles import StrategyCycles
from backend.engine.rotations.ranking import NO_CRITERION, criteria
from tests.test_ciclos_estrategia import strategy
from tests.test_ciclos_estrategia import today as today  # noqa: F401 (fixture: «hoy» fijo)
from tests.test_diagnostico import EXAMPLES, NO_WATER, use

SEQUENCE = ("papa", "arveja", "descanso")


def lowest_counted(cycle: Cycle) -> int | None:
    """La calificación más baja entre las señales que la respuesta marca con `counts` y que califican: se lee de la
    respuesta, no del motor."""
    assert cycle.diagnosis is not None and cycle.diagnosis.signals is not None
    found = [s.score for s in cycle.diagnosis.signals.values() if s.counts and s.status == "available" and s.score is not None]
    return min(found) if found else None


def test_cada_ciclo_da_su_kind_y_las_calificaciones_de_su_diagnostico(monkeypatch):
    use(monkeypatch, EXAMPLES)
    cycles: StrategyCycles = strategy()
    planned = cycles.plan(SEQUENCE)
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


def test_sin_dato_de_agua_el_riesgo_sale_de_las_otras_senales_que_cuentan(monkeypatch):
    """En el ejemplo la papa y la arveja no tienen dato de agua: su luz es `not_evaluable` y el agua no califica, pero el
    riesgo sale de sus otras señales que cuentan y califican (aprobado por Haider, PR #146): que falte el agua no lo
    mejora (R1). Se compara con lo que muestra la respuesta de cada ciclo (`counts` y `score`)."""
    use(monkeypatch, EXAMPLES)
    cycles: StrategyCycles = strategy()
    planned = cycles.plan(SEQUENCE)
    assert planned is not None
    contract = cycles.cycles(planned)
    assert [c.light for c in contract[:2]] == ["not_evaluable"] * 2
    shown = [lowest_counted(c) for c in contract[:2]]
    assert None not in shown
    scores, limitations = criteria(SEQUENCE, cycles.cycle_scores(planned), {}, cycles.query.weights)
    assert scores["water"] is None and NO_CRITERION["water"] in limitations
    assert scores["risk"] == min(shown)
    assert {f"El ciclo {n} no tiene calificación de agua: no cuenta en ese criterio" for n in (1, 2)} <= set(limitations)


def test_con_peso_cero_en_el_agua_el_riesgo_es_el_menor_factor_limitante_que_muestran_los_ciclos(monkeypatch):
    """Sin peso en el agua la luz no es `not_evaluable`: cada ciclo muestra su factor limitante, y `risk` es la menor de
    sus calificaciones."""
    use(monkeypatch, EXAMPLES)
    cycles: StrategyCycles = strategy(priorities=NO_WATER)
    planned = cycles.plan(SEQUENCE)
    assert planned is not None
    contract = cycles.cycles(planned)
    shown = [c.diagnosis.signals[c.limiting_signal].score for c in contract if c.diagnosis and c.diagnosis.signals and c.limiting_signal]
    assert len(shown) == 2
    scores, _ = criteria(SEQUENCE, cycles.cycle_scores(planned), {}, cycles.query.weights)
    assert scores["risk"] == min(shown)
