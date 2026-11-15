"""HU-082: el orden de las estrategias por las prioridades de la rotación (`backend/engine/rotations/ranking.py`).

Valores contados a mano. Las calificaciones de las señales son inventadas para la prueba, no salen de ningún dataset.
"""

import pytest

from backend.engine.rotations.ranking import (
    NO_CRITERION,
    NO_TOTAL,
    CycleScores,
    StrategyScores,
    criteria,
    rank_strategies,
    score_strategy,
    total_score,
)
from backend.engine.rotations.soil_health import Criterion
from backend.engine.signal_score import SignalScore

EQUAL = {"water": 3, "soil": 3, "income": 3, "risk": 3}
SIGNAL_WEIGHTS = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
NO_DATA = SignalScore("insufficient_data", None, None, False)


def score(value: int, critical: bool = False) -> SignalScore:
    level = "favorable" if value >= 70 else "moderate" if value >= 40 else "unfavorable"
    return SignalScore("available", value, level, critical)


def crop(water=80, frost=90, heat=95, soil=70, supply=60, market=None, kind="crop") -> CycleScores:
    values = {"water": water, "frost": frost, "heat": heat, "soil": soil, "supply": supply, "market": market}
    return CycleScores(kind, {name: NO_DATA if v is None else score(v) for name, v in values.items()})


FALLOW = CycleScores("fallow", None)


def health(*levels: str | None) -> dict[str, Criterion]:
    names = ("nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion")
    return {
        name: Criterion("available" if level else "insufficient_data", level, (), (), ()) for name, level in zip(names, levels, strict=True)
    }


GOOD_SOIL = health("favorable", "favorable", "favorable", "moderate", None)  # (100 + 100 + 100 + 50) / 4 = 87,5 → 88
POOR_SOIL = health("unfavorable", "moderate", "unfavorable", "moderate", None)  # (0 + 50 + 0 + 50) / 4 = 25


def test_los_cuatro_criterios_de_una_estrategia():
    """Papa, arveja y descanso. Agua: (80 + 71) / 2 = 75,5 → 76. Riesgo: el menor factor limitante, 55 (la oferta de la
    arveja). Ingreso: papa 60 (sin mercado), arveja (55 + 64) / 2 = 59,5, descanso 0 → 119,5 / 3 = 39,83 → 40."""
    cycles = (crop(water=80, supply=60), crop(water=71, supply=55, market=64), FALLOW)
    found, limitations = criteria(("papa", "arveja", "descanso"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert found == {"water": 76, "soil": 88, "income": 40, "risk": 55}
    assert limitations == ()


def test_el_abono_verde_vale_cero_en_el_ingreso_y_cuenta_en_agua_y_riesgo():
    cycles = (crop(water=90, supply=80), crop(water=60, supply=None, kind="cover"))
    found, _ = criteria(("papa", "avena_vicia"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert found == {"water": 75, "soil": 88, "income": 40, "risk": 60}


def test_el_riesgo_usa_los_pesos_de_quien_consulta():
    """Con peso 0 en la oferta, la oferta de 50 no cuenta: el factor limitante es el suelo (70). Una helada crítica
    cuenta aunque su peso sea 0 (R2)."""
    assert criteria(("papa",), (crop(supply=50),), GOOD_SOIL, {**SIGNAL_WEIGHTS, "supply": 0})[0]["risk"] == 70
    frost = CycleScores("crop", {"water": score(80), "frost": score(20, critical=True), "supply": score(90)})
    assert criteria(("papa",), (frost,), GOOD_SOIL, {**SIGNAL_WEIGHTS, "frost": 0})[0]["risk"] == 20


def test_un_ciclo_sin_agua_cuenta_en_el_riesgo_con_sus_otras_senales():
    """Aprobado por Haider (15 nov 2026, PR #146): sin dato de agua la luz del ciclo es `not_evaluable`, pero su riesgo
    es el mínimo de sus otras señales que cuentan y califican. Con el calor en 10, `risk` baja a 10: que falte el agua
    nunca mejora el riesgo (R1). La limitación dice que a ese ciclo le falta el agua."""
    cycles = (crop(water=None, heat=10), crop(water=60, supply=70))
    found, limitations = criteria(("papa", "arveja"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert found["risk"] == 10
    assert "El ciclo 1 no tiene calificación de agua: no cuenta en ese criterio" in limitations
    assert not any("factor limitante" in text for text in limitations)


def test_un_ciclo_sin_ninguna_senal_que_cuente_y_califique_no_cuenta_en_el_riesgo_y_se_dice():
    cycles = (crop(water=None, frost=None, heat=None, soil=None, supply=None), crop(water=60, supply=70))
    found, limitations = criteria(("papa", "arveja"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert found["risk"] == 60
    assert "El ciclo 1 no tiene un factor limitante calificado: no cuenta en ese criterio" in limitations


def test_un_criterio_sin_datos_es_nulo_no_entra_al_total_y_va_a_las_limitaciones():
    """Sin oferta ni mercado en ningún cultivo, el ingreso es nulo, aunque el descanso valga 0: nunca se rellena (R1).
    El total es el promedio de los otros tres: (80 + 88 + 80) / 3 = 82,67 → 83."""
    cycles = (crop(water=80, frost=90, heat=95, soil=80, supply=None), FALLOW)
    result = score_strategy(("papa", "descanso"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS, EQUAL)
    assert result.scores == {"water": 80, "soil": 88, "income": None, "risk": 80}
    assert result.total_score == 83
    assert NO_CRITERION["income"] in result.limitations
    assert "El ciclo 1 no tiene calificación de oferta ni de mercado: no cuenta en ese criterio" in result.limitations


def test_sin_salud_del_suelo_el_suelo_no_califica():
    result = score_strategy(("papa",), (crop(),), health(None, None, None, None, None), SIGNAL_WEIGHTS, EQUAL)
    assert result.scores["soil"] is None
    assert NO_CRITERION["soil"] in result.limitations


def test_un_ciclo_sin_agua_no_cuenta_y_se_dice():
    cycles = (crop(water=None), crop(water=60))
    found, limitations = criteria(("papa", "arveja"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert found["water"] == 60
    assert "El ciclo 1 no tiene calificación de agua: no cuenta en ese criterio" in limitations


def test_un_ciclo_no_apto_no_tiene_diagnostico_y_se_dice():
    """La rotación actual puede traer un cultivo no apto (decisión 14): sin señales, no cuenta en agua ni en riesgo."""
    cycles = (CycleScores("crop", None), crop(water=60, supply=70))
    found, limitations = criteria(("papa", "arveja"), cycles, GOOD_SOIL, SIGNAL_WEIGHTS)
    assert (found["water"], found["risk"]) == (60, 60)
    assert "El ciclo 1 no tiene diagnóstico: no cuenta en ese criterio" in limitations


def test_sin_ningun_ciclo_con_diagnostico_agua_y_riesgo_no_califican():
    result = score_strategy(("descanso",), (FALLOW,), GOOD_SOIL, SIGNAL_WEIGHTS, EQUAL)
    assert result.scores == {"water": None, "soil": 88, "income": None, "risk": None}
    assert result.total_score == 88
    assert [NO_CRITERION[name] for name in ("water", "income", "risk")] == list(result.limitations)


def test_el_total_se_pondera_por_las_prioridades():
    scores = {"water": 80, "soil": 40, "income": 60, "risk": 50}
    assert total_score(scores, EQUAL) == 58  # 230 / 4 = 57,5 → 58
    assert total_score(scores, {"water": 5, "soil": 1, "income": 0, "risk": 2}) == 68  # (400 + 40 + 100) / 8 = 67,5 → 68
    assert total_score(scores, {"water": 0, "soil": 5, "income": 0, "risk": 0}) == 40


def test_con_todas_las_prioridades_en_cero_no_hay_total():
    zero = {"water": 0, "soil": 0, "income": 0, "risk": 0}
    result = score_strategy(("papa",), (crop(),), GOOD_SOIL, SIGNAL_WEIGHTS, zero)
    assert result.total_score is None
    assert NO_TOTAL in result.limitations
    # Solo cuentan las prioridades de los criterios que califican: el agua con 5 no da total si el agua es nula.
    assert total_score({"water": None, "soil": 70, "income": None, "risk": 40}, {**zero, "water": 5}) is None


def test_una_prioridad_que_falta_vale_cero():
    assert total_score({"water": 80, "soil": 40, "income": None, "risk": None}, {"water": 1}) == 80


def test_subir_el_peso_del_suelo_sube_al_abono_verde():
    """Criterio de HU-082: dos estrategias iguales salvo el tercer ciclo. La del abono verde (avena con vicia) cuida el
    suelo (88) y no deja ingreso en ese ciclo; la de arveja deja ingreso, pero su suelo sale peor (25). Agua 80 y riesgo
    60 (la oferta) en las dos; ingreso 60 con arveja y (60 + 60 + 0) / 3 = 40 con el abono verde.

    Con el suelo en 0 y el ingreso en 5: arveja (240 + 300 + 180) / 11 = 65,45 → 65; abono verde (240 + 200 + 180) / 11
    = 56,36 → 56. Con el suelo en 5: arveja (240 + 125 + 300 + 180) / 16 = 52,81 → 53; abono verde (240 + 440 + 200 +
    180) / 16 = 66,25 → 66."""
    sowed = (crop(water=80, supply=60), crop(water=80, supply=60))
    options = (
        (("papa", "maiz", "arveja"), (*sowed, crop(water=80, supply=60)), POOR_SOIL),
        (("papa", "maiz", "avena_vicia"), (*sowed, crop(water=80, supply=None, kind="cover")), GOOD_SOIL),
    )

    def order(priorities):
        found = [score_strategy(ids, cycles, soil, SIGNAL_WEIGHTS, priorities) for ids, cycles, soil in options]
        assert [(s.scores["water"], s.scores["income"], s.scores["risk"]) for s in found] == [(80, 60, 60), (80, 40, 60)]
        return [(s.crop_ids[-1], s.total_score) for s in rank_strategies(found)]

    low_soil = {"water": 3, "soil": 0, "income": 5, "risk": 3}
    assert order(low_soil) == [("arveja", 65), ("avena_vicia", 56)]
    assert order({**low_soil, "soil": 5}) == [("avena_vicia", 66), ("arveja", 53)]


def strategy(crop_ids: tuple[str, ...], total: int | None, risk: int | None = 50) -> StrategyScores:
    return StrategyScores(crop_ids, {"water": 50, "soil": 50, "income": 50, "risk": risk}, total, ())


def test_empate_de_total_gana_el_riesgo_mas_alto_y_despues_los_crop_ids():
    ranked = rank_strategies(
        [
            strategy(("zanahoria", "arveja"), 70, risk=60),
            strategy(("papa", "haba"), 70, risk=60),
            strategy(("arveja", "papa"), 70, risk=40),
            strategy(("haba", "papa"), 70, risk=None),
            strategy(("cebada", "papa"), 80, risk=10),
        ]
    )
    assert [(s.rank, s.crop_ids) for s in ranked] == [
        (1, ("cebada", "papa")),
        (2, ("papa", "haba")),
        (3, ("zanahoria", "arveja")),
        (4, ("arveja", "papa")),
        (5, ("haba", "papa")),
    ]


def test_sin_total_va_al_final():
    ranked = rank_strategies([strategy(("arveja", "papa"), None, risk=100), strategy(("papa", "haba"), 0)])
    assert [(s.rank, s.crop_ids, s.total_score) for s in ranked] == [(1, ("papa", "haba"), 0), (2, ("arveja", "papa"), None)]


def test_hasta_diez_estrategias():
    many = [strategy((f"cultivo_{n:02d}", "papa"), n) for n in range(15)]
    ranked = rank_strategies(many)
    assert len(ranked) == 10
    assert [s.total_score for s in ranked] == list(range(14, 4, -1))
    assert [s.rank for s in ranked] == list(range(1, 11))


def test_misma_entrada_mismo_orden_sin_importar_el_orden_de_llegada():
    many = [strategy((f"cultivo_{n % 4}", f"otro_{n}"), 50 + n % 3, risk=n % 2 * 10) for n in range(12)]
    first = rank_strategies(many)
    assert rank_strategies(list(reversed(many))) == first
    assert rank_strategies(many) == first


def test_ciclos_y_calificaciones_deben_coincidir():
    with pytest.raises(ValueError, match="2 ciclos y 1 calificaciones"):
        criteria(("papa", "arveja"), (crop(),), GOOD_SOIL, SIGNAL_WEIGHTS)
