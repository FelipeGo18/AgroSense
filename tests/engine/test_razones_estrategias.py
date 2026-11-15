"""HU-083: las razones del orden de una estrategia (`backend/engine/rotations/reasons.py`).

Las calificaciones y los criterios de salud del suelo son inventados para la prueba, con la forma que da `soil_health`
(HU-212); no salen de ningún dataset ni de las reglas del catálogo.
"""

import re

import pytest

from backend.engine.rotations.ranking import CycleScores, score_strategy
from backend.engine.rotations.reasons import NO_TOTAL_DATA, NO_TOTAL_WEIGHTS, PASSES_RULES, strategy_reasons
from backend.engine.rotations.soil_health import TEAM_NOTE, Criterion
from backend.engine.signal_score import SignalScore
from tests.engine.test_salud_del_suelo_motor import _sh

EQUAL = {"water": 3, "soil": 3, "income": 3, "risk": 3}
WEIGHTS = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
FALLOW = CycleScores("fallow", None)
NO_DATA = SignalScore("insufficient_data", None, None, False)


def crop(water=80, frost=90, heat=95, soil=70, supply=60, kind="crop") -> CycleScores:
    values = {"water": water, "frost": frost, "heat": heat, "soil": soil, "supply": supply, "market": None}
    signals = {
        n: NO_DATA if v is None else SignalScore("available", v, "favorable" if v >= 70 else "moderate", False) for n, v in values.items()
    }
    return CycleScores(kind, signals)


NITROGEN = Criterion(
    "available",
    "favorable",
    ("Ciclos con leguminosa, que fija nitrógeno del aire: 2. Compara estrategias por reglas; no dice cuánto nitrógeno queda en el suelo",),
    ("REGLA_ID",),
    ("FUENTE_ID",),
)
COVER_MODERATE = Criterion(
    "available",
    "moderate",
    (f"El suelo queda cubierto por un cultivo o un abono verde el 65 % del tiempo que dura la estrategia. {TEAM_NOTE}",),
    ("REGLA_ID",),
    ("criterio_equipo_2026",),
)
NO_LEVEL = Criterion("insufficient_data", None, ("Falta la pendiente del terreno",), (), ())


def reasons_for(cycles, soil_health, priorities=EQUAL, vs_current=None):
    crop_ids = tuple(f"c{n}" for n in range(len(cycles)))
    scores = score_strategy(crop_ids, cycles, soil_health, WEIGHTS, priorities)
    return scores, strategy_reasons(scores, priorities, cycles, soil_health, WEIGHTS, vs_current)


def test_las_cuatro_razones_citan_lo_que_el_motor_evaluo():
    """Agua 80, suelo 100 (nitrógeno favorable), ingreso (60 + 55 + 0) / 3 = 38,3 → 38 y riesgo 55 (la oferta del
    ciclo 2). Con prioridades 3, 5, 1 y 3: lo que más suma es el suelo (100 × 5)."""
    cycles = (crop(supply=60), crop(supply=55), FALLOW)
    priorities = {"water": 3, "soil": 5, "income": 1, "risk": 3}
    scores, reasons = reasons_for(
        cycles, {"nitrogen": NITROGEN}, priorities, {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15}
    )
    assert scores.scores == {"water": 80, "soil": 100, "income": 38, "risk": 55}
    assert reasons == (
        "Lo que más suma a su total es el criterio de suelo: 100 de 100, con prioridad 5 de 5",
        "Frente a su rotación actual sale 38 puntos mejor en suelo: ese criterio es el promedio de los cinco criterios de salud del suelo",
        f"Salud del suelo, nitrógeno favorable: {NITROGEN.reasons[0]}",
        "El factor que más limita entre sus ciclos es la oferta del ciclo 2: 55 de 100",
    )


def test_sin_rotacion_actual_no_hay_razon_frente_a_ella():
    _, reasons = reasons_for((crop(), crop(supply=55)), {"nitrogen": NITROGEN})
    assert not any("rotación actual" in r for r in reasons)
    assert len(reasons) == 3


def test_frente_a_la_actual_sin_ganancia_dice_donde_pierde():
    _, reasons = reasons_for((crop(),), {}, vs_current={"water": 0, "soil": None, "income": -9, "risk": -1, "total": -3})
    income = "el promedio de la oferta y el mercado de sus ciclos, con el abono verde y el descanso en 0"
    assert f"Frente a su rotación actual sale 9 puntos peor en ingreso: ese criterio es {income}" in reasons


def test_frente_a_la_actual_sin_diferencias_lo_dice_y_un_criterio_nulo_no_se_compara():
    _, reasons = reasons_for((crop(),), {}, vs_current={"water": 0, "soil": None, "income": 0, "risk": 0, "total": 0})
    assert "Frente a su rotación actual queda igual en los criterios que se pueden comparar (agua, ingreso, riesgo)" in reasons
    _, reasons = reasons_for((crop(),), {}, vs_current={"water": None, "soil": None, "income": None, "risk": None, "total": None})
    assert not any("rotación actual" in r for r in reasons)


def test_un_punto_en_singular():
    _, reasons = reasons_for((crop(),), {}, vs_current={"water": 1, "soil": None, "income": None, "risk": None, "total": 1})
    assert any(r.startswith("Frente a su rotación actual sale 1 punto mejor en agua") for r in reasons)


def test_el_suelo_cita_el_primer_criterio_favorable_y_si_no_hay_el_primero_con_nivel():
    _, reasons = reasons_for((crop(),), {"nitrogen": NITROGEN, "soil_cover": COVER_MODERATE})
    assert f"Salud del suelo, nitrógeno favorable: {NITROGEN.reasons[0]}" in reasons
    _, reasons = reasons_for((crop(),), {"soil_cover": COVER_MODERATE, "erosion": NO_LEVEL})
    assert f"Salud del suelo, suelo cubierto moderado: {COVER_MODERATE.reasons[0]}" in reasons


def test_un_criterio_del_equipo_lo_dice_en_la_razon():
    """R8, decisión 16: lo que se apoya en `criterio_equipo_2026` se rotula «criterio del equipo» siempre."""
    _, reasons = reasons_for((crop(),), {"soil_cover": COVER_MODERATE})
    soil = next(r for r in reasons if r.startswith("Salud del suelo"))
    assert TEAM_NOTE in soil


def test_sin_salud_del_suelo_con_nivel_no_hay_razon_de_suelo():
    _, reasons = reasons_for((crop(),), {"erosion": NO_LEVEL})
    assert not any(r.startswith("Salud del suelo") for r in reasons)


def test_el_factor_limitante_es_el_del_riesgo_y_el_primer_ciclo_en_un_empate():
    scores, reasons = reasons_for((crop(supply=50), crop(heat=50, supply=None)), {})
    assert scores.scores["risk"] == 50
    assert "El factor que más limita entre sus ciclos es la oferta del ciclo 1: 50 de 100" in reasons


def test_con_pocos_datos_no_se_rellena_y_se_dice_que_pasa_las_reglas():
    """Un descanso solo y sin salud del suelo: ningún criterio califica, así que no hay total, ni suelo, ni factor
    limitante. Lo único cierto es por qué no tiene total y que pasó las reglas de rotación (R1, R5). Con el suelo
    nulo y prioridad solo en el suelo, los que califican tienen prioridad 0."""
    _, reasons = reasons_for((FALLOW,), {})
    assert reasons == (NO_TOTAL_DATA, PASSES_RULES)
    zero = {"water": 0, "soil": 0, "income": 0, "risk": 0}
    _, reasons = reasons_for((crop(),), {}, priorities={**zero, "soil": 5})
    assert reasons[0] == NO_TOTAL_WEIGHTS
    _, reasons = reasons_for((crop(),), {})
    assert len(reasons) == 2 and reasons[-1] == "El factor que más limita entre sus ciclos es la oferta del ciclo 1: 60 de 100"


def test_lo_que_mas_suma_con_prioridad_cero_no_se_cita():
    """Con el suelo en 100 y prioridad 0, lo que más suma es el agua (80 × 3), no el suelo."""
    _, reasons = reasons_for((crop(),), {"nitrogen": NITROGEN}, priorities={"water": 3, "soil": 0, "income": 1, "risk": 2})
    assert reasons[0] == "Lo que más suma a su total es el criterio de agua: 80 de 100, con prioridad 3 de 5"


# Lo que una razón no puede decir (decisión 4): cuánto mejora el suelo, cuánto se cosecha ni un pronóstico.
FORBIDDEN = re.compile(r"mejorar[áa]|aumentar[áa]|rendimiento|cosechar[áa]|kg|toneladas|t/ha|pronóstico|predice que|garantiza", re.I)


@pytest.mark.parametrize(
    "vs_current",
    [
        None,
        {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15},
        {"water": -4, "soil": None, "income": -2, "risk": 0, "total": -2},
    ],
)
def test_ninguna_razon_dice_cuanto_mejora_el_suelo_ni_cuanto_se_cosecha(vs_current):
    _, reasons = reasons_for((crop(), crop(supply=55), FALLOW), {"nitrogen": NITROGEN, "soil_cover": COVER_MODERATE}, vs_current=vs_current)
    assert 2 <= len(reasons) <= 4
    assert [r for r in reasons if FORBIDDEN.search(r)] == []


def test_los_ciclos_deben_ser_los_de_sus_criterios():
    cycles = (crop(supply=50),)
    scores = score_strategy(("papa",), cycles, {}, WEIGHTS, EQUAL)
    with pytest.raises(ValueError, match="los ciclos no son los de sus criterios"):
        strategy_reasons(scores, EQUAL, (crop(supply=70),), {}, WEIGHTS)


def test_con_las_reglas_del_catalogo_la_razon_de_suelo_es_la_de_soil_health_con_la_nota_del_equipo():
    """Con `soil_health` y las reglas reales de `catalog/rotation_rules.yaml`: avena con vicia, arveja y papa tienen
    dos ciclos con leguminosa; el nitrógeno es favorable y su regla es del equipo (`criterio_equipo_2026`), así que la
    razón de la estrategia lo dice (R8, decisión 16)."""
    health = _sh(("avena_vicia", "arveja", "papa"))
    nitrogen = health["nitrogen"]
    assert (nitrogen.level, nitrogen.rule_ids) == ("favorable", ("leguminosa_en_rotacion",))
    _, reasons = reasons_for((crop(kind="cover"), crop(), crop()), health)
    assert f"Salud del suelo, nitrógeno favorable: {nitrogen.reasons[0]}" in reasons
    assert TEAM_NOTE in nitrogen.reasons[0]


def test_un_ciclo_sin_agua_puede_ser_el_factor_que_mas_limita():
    """Con la regla de Haider (PR #146): sin agua, el ciclo cuenta en el riesgo con sus otras señales; la razón nombra
    esa señal y ese ciclo, con la misma calificación de `risk`."""
    scores, reasons = reasons_for((crop(water=None, heat=10), crop(supply=70)), {})
    assert scores.scores["risk"] == 10
    assert "El factor que más limita entre sus ciclos es el calor del ciclo 1: 10 de 100" in reasons
