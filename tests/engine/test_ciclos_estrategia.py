"""HU-213: las fechas de los ciclos de una estrategia (`backend/engine/rotations/cycles.py`).

Las etapas y la duración del descanso son DE EJEMPLO (R5), elegidas para que las fechas se puedan contar a mano: la papa
dura 165 días, la arveja 110 y el descanso 180. El 4 de enero de 2027 es lunes.
"""

from datetime import date

import pytest

from backend.engine.rotations.cycles import cycle_days, gap_days, next_sowing, plan_cycles
from backend.engine.rotations.soil_health import covered_gaps
from backend.engine.stages import CALENDAR, StageSpan

STAGES = {
    "papa": [StageSpan("initial", 45), StageSpan("development", 30), StageSpan("mid", 70), StageSpan("late", 20)],
    "arveja": [StageSpan("initial", 35), StageSpan("development", 25), StageSpan("mid", 30), StageSpan("late", 20)],
}
FALLOW = {"descanso": 180}
MONDAY = date(2027, 1, 4)


@pytest.mark.parametrize(
    ("harvest", "sowing"),
    [
        (date(2027, 1, 4), date(2027, 1, 4)),  # lunes: se resiembra ese mismo día (hueco 0)
        (date(2027, 1, 5), date(2027, 1, 11)),  # martes: 6 días
        (date(2027, 1, 10), date(2027, 1, 11)),  # domingo: 1 día
        (date(2027, 12, 31), date(2028, 1, 3)),  # viernes de fin de año: el lunes es del año siguiente
    ],
)
def test_el_ciclo_siguiente_se_siembra_el_lunes_siguiente_a_la_cosecha(harvest, sowing):
    assert next_sowing(harvest) == sowing
    assert 0 <= (sowing - harvest).days <= 6


def test_papa_arveja_descanso_desde_un_lunes():
    """Papa del 4 de enero al viernes 18 de junio (165 días); arveja del lunes 21 de junio al sábado 9 de octubre
    (110); descanso del lunes 11 de octubre al 8 de abril de 2028 (180, con el 29 de febrero)."""
    cycles = plan_cycles(("papa", "arveja", "descanso"), STAGES, FALLOW, MONDAY)
    assert cycles is not None
    assert [(c.cycle, c.crop_id, c.sowing_date, c.harvest_estimate, c.gap_days) for c in cycles] == [
        (1, "papa", date(2027, 1, 4), date(2027, 6, 18), 3),
        (2, "arveja", date(2027, 6, 21), date(2027, 10, 9), 2),
        (3, "descanso", date(2027, 10, 11), date(2028, 4, 8), None),
    ]
    assert all(c.harvest_basis == CALENDAR for c in cycles)
    # La ventana de un cultivo es la de `crop_window`; el descanso no tiene ventana ni diagnóstico.
    assert cycles[0].window is not None and cycles[0].window.harvest_estimate == date(2027, 6, 18)
    assert cycles[2].window is None


def test_los_dias_y_los_huecos_de_soil_health_salen_del_mismo_calculo():
    """R4: `cycle_days` y `gap_days` son los de las fechas de los ciclos, y `soil_health` los acepta."""
    cycles = plan_cycles(("papa", "arveja", "descanso"), STAGES, FALLOW, MONDAY)
    assert cycles is not None
    assert cycle_days(cycles) == (165, 110, 180)
    assert gap_days(cycles) == (3, 2, None)
    assert covered_gaps(3, gap_days(cycles)) == (3, 2)
    # Cada ciclo empieza donde termina el anterior más su hueco.
    for before, after in zip(cycles, cycles[1:], strict=False):
        assert (after.sowing_date - before.harvest_estimate).days == before.gap_days


def test_el_descanso_primero_dura_lo_de_su_ficha():
    cycles = plan_cycles(("descanso", "papa"), STAGES, FALLOW, MONDAY)
    assert cycles is not None
    # 4 de enero + 180 días = 3 de julio de 2027 (sábado); la papa, el lunes 5 de julio.
    assert [(c.sowing_date, c.harvest_estimate, c.gap_days) for c in cycles] == [
        (date(2027, 1, 4), date(2027, 7, 3), 2),
        (date(2027, 7, 5), date(2027, 12, 17), None),
    ]


@pytest.mark.parametrize(
    ("sequence", "stages", "fallow"),
    [
        (("papa", "descanso"), STAGES, {"descanso": None}),  # el descanso sin días en su ficha
        (("papa", "maiz"), STAGES, FALLOW),  # un cultivo sin etapas
        (("papa", "arveja"), {**STAGES, "arveja": [StageSpan("initial", 0)]}, FALLOW),  # una etapa sin días
    ],
)
def test_sin_la_duracion_de_un_ciclo_no_se_fecha_la_estrategia(sequence, stages, fallow):
    """R1: sin la cosecha de un ciclo no se puede fechar el siguiente; no se inventa una duración."""
    assert plan_cycles(sequence, stages, fallow, MONDAY) is None


def test_misma_entrada_mismas_fechas():
    """R4: dos ejecuciones iguales dan los mismos ciclos."""
    sequence = ("arveja", "papa", "arveja")
    assert plan_cycles(sequence, STAGES, FALLOW, MONDAY) == plan_cycles(sequence, STAGES, FALLOW, MONDAY)
