"""El orden de las ventanas por factor limitante y prioridades (HU-192; specs/01-reglas.md, «Orden de las ventanas» y
«Las prioridades del agricultor»).

Primero el factor que más limita (ley del mínimo, por decenas), después el promedio ponderado por los pesos; las
ventanas con una señal crítica que cuenta van al final y nunca entran a `best_windows` (R2); empate: la más temprana
(R4). Una señal sin datos o que no aplica no califica (R1).

Decisiones de esta prueba (docs/registro-de-decisiones.md, 14 de noviembre de 2026):
- Un peso que falta en el mapa de pesos vale 0; un peso negativo, también. El motor no valida el rango de 0 a 5 (lo
  hace la API): un peso mayor que 5 se usa tal cual.
- La decena alta es 90 a 100, una sola.
- Si las señales que cuentan y califican tienen todas peso 0 (solo cuentan por ser riesgo grave de clima),
  `weighted_score` es nulo y `limiting_score` sí tiene valor.
- Sin ninguna señal que cuente y califique: `limiting_signal`, `limiting_score` y `weighted_score` nulos y
  `high_risk` falso; esas ventanas van al final, después de las de alto riesgo, por fecha.
"""

from datetime import date, timedelta

import pytest

from backend.engine.signal_score import CLIMATE_CRITICAL_SIGNALS, SignalScore, counts
from backend.engine.stages import StageSpan, crop_window, monthly_sowing_windows
from backend.engine.window_order import RankedWindow, WindowSignals, best_windows, limiting_decade, order_windows

SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
ALL_3 = dict.fromkeys(SIGNALS, 3)

INSUFFICIENT = SignalScore("insufficient_data", None, None, False)
NOT_APPLICABLE = SignalScore("not_applicable", None, None, False)


def sig(score: int, critical: bool = False) -> SignalScore:
    """Una señal calificada, con el nivel que corresponde a su calificación (70+, 40-69, <40)."""
    if score >= 70:
        level = "favorable"
    elif score >= 40:
        level = "moderate"
    else:
        level = "unfavorable"
    assert not critical or level == "unfavorable", "una señal crítica es desfavorable"
    return SignalScore("available", score, level, critical)


def window(month: int, year: int = 2027, **signals: SignalScore) -> WindowSignals:
    """Una ventana sembrada el día 1 de `month`; las señales que no se dan quedan sin datos."""
    start = date(year, month, 1)
    full = {name: signals.get(name, INSUFFICIENT) for name in SIGNALS}
    return WindowSignals(sowing_start=start, harvest_estimate=start + timedelta(days=150), signals=full)


def starts(ranked) -> list[date]:
    return [w.sowing_start for w in ranked]


# ------------------------------------------------------------------ qué señal cuenta


def test_los_riesgos_graves_de_clima_son_agua_heladas_y_calor():
    assert frozenset({"water", "frost", "heat"}) == CLIMATE_CRITICAL_SIGNALS


@pytest.mark.parametrize("signal", SIGNALS)
@pytest.mark.parametrize("weight", [1, 3, 5])
@pytest.mark.parametrize("critical", [False, True])
def test_una_senal_con_peso_cuenta(signal, weight, critical):
    assert counts(signal, weight, critical) is True


@pytest.mark.parametrize("signal", SIGNALS)
def test_una_senal_con_peso_0_no_critica_no_cuenta(signal):
    assert counts(signal, 0, False) is False


@pytest.mark.parametrize("signal", ["water", "frost", "heat"])
def test_un_riesgo_grave_de_clima_cuenta_aunque_su_peso_sea_0(signal):
    assert counts(signal, 0, True) is True


@pytest.mark.parametrize("signal", ["soil", "supply", "market"])
def test_una_senal_critica_que_no_es_de_clima_con_peso_0_no_cuenta(signal):
    assert counts(signal, 0, True) is False


# ------------------------------------------------------------------ casos de referencia


def test_alto_riesgo_con_el_balance_mas_alto_no_queda_primera_ni_entra_en_las_mejores():
    risky = window(1, water=sig(100), frost=sig(25, critical=True), heat=sig(100), soil=sig(100), supply=sig(100), market=sig(100))
    good = window(2, **dict.fromkeys(SIGNALS, sig(70)))
    fair = window(3, **dict.fromkeys(SIGNALS, sig(60)))

    ranked = order_windows([risky, good, fair], ALL_3)

    assert starts(ranked) == [good.sowing_start, fair.sowing_start, risky.sowing_start]
    last = ranked[-1]
    assert (last.high_risk, last.limiting_signal, last.limiting_score) == (True, "frost", 25)
    assert last.weighted_score == 88  # (25 + 5 × 100) / 6 = 87,5: la más alta de las tres
    assert last.weighted_score > ranked[0].weighted_score
    assert risky.sowing_start not in starts(best_windows(ranked))
    assert starts(best_windows(ranked)) == [good.sowing_start, fair.sowing_start]


def test_una_senal_en_15_con_el_promedio_mas_alto_queda_detras_de_una_con_todas_en_60_o_mas():
    # El suelo nunca es crítico (R10): la ventana con 15 no es de alto riesgo, pero su factor limitante la baja.
    low = window(1, water=sig(100), frost=sig(100), heat=sig(100), soil=sig(15), supply=sig(100), market=sig(100))
    even = window(2, water=sig(60), frost=sig(65), heat=sig(65), soil=sig(60), supply=sig(60), market=sig(60))

    ranked = order_windows([low, even], ALL_3)

    assert starts(ranked) == [even.sowing_start, low.sowing_start]
    assert (ranked[1].limiting_signal, ranked[1].limiting_score, ranked[1].high_risk) == ("soil", 15, False)
    assert ranked[1].weighted_score == 86 and ranked[0].weighted_score == 62
    assert ranked[0].limiting_score == 60


def test_sin_senal_que_cuente_todo_es_nulo_y_va_despues_de_las_de_alto_riesgo():
    weights = {**ALL_3, "soil": 0}
    nothing = window(1, water=INSUFFICIENT, frost=NOT_APPLICABLE, heat=NOT_APPLICABLE)
    only_zero_weight = window(2, water=INSUFFICIENT, frost=NOT_APPLICABLE, heat=NOT_APPLICABLE, soil=sig(90))
    risky = window(3, water=sig(20, critical=True), frost=sig(80), heat=sig(80), soil=sig(80))
    normal = window(4, water=sig(80), frost=sig(80), heat=sig(80), soil=sig(80))

    ranked = order_windows([only_zero_weight, risky, nothing, normal], weights)

    assert starts(ranked) == [normal.sowing_start, risky.sowing_start, nothing.sowing_start, only_zero_weight.sowing_start]
    for empty in ranked[2:]:
        assert (empty.limiting_signal, empty.limiting_score, empty.weighted_score, empty.high_risk) == (None, None, None, False)
    assert starts(best_windows(ranked)) == [normal.sowing_start]


def test_en_la_misma_decena_desempata_el_promedio_ponderado():
    # A y B tienen el factor limitante en la decena del 60; C en la del 70.
    a = window(5, water=sig(62), frost=sig(90), heat=sig(90), soil=sig(90), supply=sig(90), market=sig(90))
    b = window(1, water=sig(68), frost=sig(70), heat=sig(70), soil=sig(70), supply=sig(70), market=sig(70))
    c = window(9, **dict.fromkeys(SIGNALS, sig(70)))

    ranked = order_windows([b, c, a], ALL_3)

    assert starts(ranked) == [c.sowing_start, a.sowing_start, b.sowing_start]
    assert [w.limiting_score for w in ranked] == [70, 62, 68]
    assert [w.weighted_score for w in ranked] == [70, 85, 70]  # (62 + 450) / 6 = 85,3; (68 + 350) / 6 = 69,7


def test_en_empate_total_gana_la_ventana_mas_temprana():
    same = dict.fromkeys(SIGNALS, sig(75))
    late, early, middle = window(10, **same), window(2, **same), window(6, **same)

    ranked = order_windows([late, early, middle], ALL_3)

    assert starts(ranked) == [early.sowing_start, middle.sowing_start, late.sowing_start]


def test_con_el_mismo_promedio_en_la_misma_decena_gana_la_mas_temprana_no_el_limitante_mas_alto():
    weights = {"water": 3, "frost": 3, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    early = window(3, water=sig(61), frost=sig(79))  # limitante 61, promedio 70
    late = window(5, water=sig(69), frost=sig(71))  # limitante 69, promedio 70

    ranked = order_windows([late, early], weights)

    assert starts(ranked) == [early.sowing_start, late.sowing_start]
    assert [w.weighted_score for w in ranked] == [70, 70]


def test_el_orden_cruza_el_ano_por_fecha_no_por_mes():
    same = dict.fromkeys(SIGNALS, sig(75))
    january_next = window(1, year=2027, **same)
    december = window(12, year=2026, **same)

    ranked = order_windows([january_next, december], ALL_3)

    assert starts(ranked) == [december.sowing_start, january_next.sowing_start]


def test_sin_datos_y_no_aplica_no_califican_ni_cambian_el_minimo():
    w = window(1, water=sig(80), frost=NOT_APPLICABLE, heat=INSUFFICIENT, soil=sig(75), supply=INSUFFICIENT, market=INSUFFICIENT)

    (ranked,) = order_windows([w], ALL_3)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("soil", 75, False)
    assert ranked.weighted_score == 78  # (80 × 3 + 75 × 3) / 6 = 77,5, hacia arriba


def test_un_riesgo_grave_de_clima_con_peso_0_cuenta_para_el_minimo_y_el_alto_riesgo_no_para_el_promedio():
    weights = {**ALL_3, "frost": 0}
    w = window(1, water=sig(90), frost=sig(10, critical=True), heat=sig(80), soil=sig(70))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("frost", 10, True)
    assert ranked.weighted_score == 80  # (90 + 80 + 70) × 3 / 9: la helada no aporta


def test_con_peso_0_una_senal_de_clima_no_critica_no_cuenta():
    weights = {**ALL_3, "frost": 0}
    w = window(1, water=sig(90), frost=sig(45), heat=sig(80), soil=sig(70))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("soil", 70, False)
    assert ranked.weighted_score == 80


def test_una_senal_critica_que_no_es_de_clima_con_peso_0_no_marca_alto_riesgo():
    weights = {**ALL_3, "market": 0}
    w = window(1, water=sig(90), frost=sig(90), heat=sig(90), soil=sig(90), supply=sig(90), market=sig(5, critical=True))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_score, ranked.high_risk) == (90, False)
    assert ranked.limiting_signal in {"water", "frost", "heat", "soil", "supply"}
    assert ranked.weighted_score == 90


def test_con_todos_los_pesos_en_0_solo_cuenta_el_riesgo_grave_y_no_hay_promedio():
    weights = dict.fromkeys(SIGNALS, 0)
    w = window(1, water=sig(20, critical=True), frost=sig(90), heat=sig(90), soil=sig(90), supply=sig(90), market=sig(90))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("water", 20, True)
    assert ranked.weighted_score is None


def test_sin_promedio_va_al_final_de_su_decena():
    weights = {"water": 0, "frost": 3, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    no_average = window(1, water=sig(20, critical=True), frost=INSUFFICIENT)
    with_average = window(2, water=sig(25, critical=True), frost=sig(90))

    ranked = order_windows([no_average, with_average], weights)

    assert starts(ranked) == [with_average.sowing_start, no_average.sowing_start]
    assert [w.weighted_score for w in ranked] == [90, None]
    assert all(w.high_risk for w in ranked)


def test_un_peso_que_falta_vale_0():
    weights = {"water": 3}
    w = window(1, water=sig(80), frost=sig(50), heat=sig(45))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.weighted_score, ranked.high_risk) == ("water", 80, 80, False)


def test_un_riesgo_grave_de_clima_sin_peso_en_el_mapa_cuenta_igual():
    weights = {"water": 3}
    w = window(1, water=sig(80), heat=sig(12, critical=True))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.weighted_score, ranked.high_risk) == ("heat", 12, 80, True)


def test_el_promedio_se_redondea_hacia_arriba_desde_la_mitad_no_al_par():
    weights = {"water": 1, "frost": 1, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    w = window(1, water=sig(70), frost=sig(75))

    (ranked,) = order_windows([w], weights)

    assert ranked.weighted_score == 73  # 72,5: round() daría 72


def test_el_promedio_pondera_por_los_pesos():
    weights = {"water": 5, "frost": 1, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    w = window(1, water=sig(90), frost=sig(30))

    (ranked,) = order_windows([w], weights)

    assert ranked.weighted_score == 80  # (90 × 5 + 30) / 6


def test_un_peso_negativo_en_una_senal_no_critica_vale_0_y_no_cuenta():
    weights = {**ALL_3, "soil": -2}
    w = window(1, water=sig(90), frost=sig(80), heat=sig(85), soil=sig(40))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("frost", 80, False)
    assert ranked.weighted_score == 85  # (90 + 80 + 85) × 3 / 9: el suelo no aporta ni resta


def test_un_peso_negativo_en_una_helada_critica_cuenta_para_el_minimo_y_el_alto_riesgo_no_para_el_promedio():
    weights = {**ALL_3, "frost": -4}
    w = window(1, water=sig(90), frost=sig(10, critical=True), heat=sig(80), soil=sig(70))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("frost", 10, True)
    assert ranked.weighted_score == 80  # el -4 no entra al promedio: (90 + 80 + 70) × 3 / 9


def test_con_todos_los_pesos_negativos_solo_cuenta_el_riesgo_grave_y_no_hay_promedio():
    weights = dict.fromkeys(SIGNALS, -1)
    w = window(1, water=sig(20, critical=True), frost=sig(90), heat=sig(90))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("water", 20, True)
    assert ranked.weighted_score is None


def test_un_peso_mayor_que_5_se_usa_tal_cual_en_el_promedio():
    weights = {"water": 7, "frost": 1, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    w = window(1, water=sig(90), frost=sig(10))

    (ranked,) = order_windows([w], weights)

    assert ranked.weighted_score == 80  # (90 × 7 + 10) / 8: el motor no recorta; la API valida el rango
    assert (ranked.limiting_signal, ranked.limiting_score, ranked.high_risk) == ("frost", 10, False)


def test_una_senal_available_sin_calificacion_no_califica():
    weights = {**ALL_3}
    w = window(1, water=SignalScore("available", None, None, False), frost=sig(80), heat=sig(75))

    (ranked,) = order_windows([w], weights)

    assert (ranked.limiting_signal, ranked.limiting_score, ranked.weighted_score) == ("heat", 75, 78)


def test_70_y_69_son_decenas_distintas_y_manda_el_factor_limitante_no_el_promedio():
    weights = {"water": 1, "frost": 1, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    seventy = window(2, water=sig(70), frost=sig(70))  # promedio 70
    sixty_nine = window(1, water=sig(69), frost=sig(100))  # promedio 85, más temprana

    ranked = order_windows([sixty_nine, seventy], weights)

    assert starts(ranked) == [seventy.sowing_start, sixty_nine.sowing_start]
    assert [w.weighted_score for w in ranked] == [70, 85]


@pytest.mark.parametrize(("score", "decade"), [(0, 0), (39, 3), (60, 6), (69, 6), (70, 7), (90, 9), (95, 9), (100, 9)])
def test_la_decena_alta_es_de_90_a_100(score, decade):
    assert limiting_decade(score) == decade


def test_100_y_95_estan_en_la_misma_decena_y_manda_el_promedio_ponderado():
    # Con limitante 100, todas las señales que cuentan están en 100 y el promedio también: ninguna ventana de la
    # decena le gana por promedio. La de 95 va segunda por su promedio, no por estar en otra decena.
    weights = {"water": 1, "frost": 1, "heat": 0, "soil": 0, "supply": 0, "market": 0}
    hundred = window(2, water=sig(100), frost=sig(100))
    ninety_five = window(1, water=sig(95), frost=sig(100))
    ninety = window(3, water=sig(90), frost=sig(100))

    ranked = order_windows([ninety, ninety_five, hundred], weights)

    assert starts(ranked) == [hundred.sowing_start, ninety_five.sowing_start, ninety.sowing_start]
    assert len({limiting_decade(w.limiting_score) for w in ranked}) == 1


def test_en_empate_del_minimo_el_limitante_es_una_de_las_empatadas():
    w = window(1, water=sig(55), frost=sig(55), heat=sig(80), soil=sig(90))

    (ranked,) = order_windows([w], ALL_3)

    assert ranked.limiting_score == 55
    assert ranked.limiting_signal in {"water", "frost"}


def test_cada_ventana_conserva_sus_fechas_y_el_resultado_es_una_tupla():
    windows = [window(m, **dict.fromkeys(SIGNALS, sig(50 + m))) for m in (4, 1, 7)]

    ranked = order_windows(windows, ALL_3)

    assert isinstance(ranked, tuple) and all(isinstance(w, RankedWindow) for w in ranked)
    assert sorted((w.sowing_start, w.harvest_estimate) for w in ranked) == sorted((w.sowing_start, w.harvest_estimate) for w in windows)


def test_sin_ventanas_no_hay_orden():
    assert order_windows([], ALL_3) == ()
    assert best_windows(()) == ()


# ------------------------------------------------------------------ mejores ventanas


def ranked_window(month: int, limiting: int | None, weighted: int | None, high_risk: bool) -> RankedWindow:
    start = date(2027, month, 1)
    return RankedWindow(
        sowing_start=start,
        harvest_estimate=start + timedelta(days=150),
        limiting_signal=None if limiting is None else "water",
        limiting_score=limiting,
        weighted_score=weighted,
        high_risk=high_risk,
    )


def test_las_mejores_son_hasta_tres_sin_alto_riesgo_ni_ventanas_sin_calificacion_en_el_orden_dado():
    # Lista mal ordenada a propósito: best_windows filtra, no reordena ni confía en el orden.
    risky = ranked_window(1, 20, 95, True)
    empty = ranked_window(2, None, None, False)
    a, b, c, d = (
        ranked_window(3, 50, 60, False),
        ranked_window(4, 90, 90, False),
        ranked_window(5, 70, 75, False),
        ranked_window(6, 80, 80, False),
    )

    best = best_windows([risky, empty, a, b, c, d])

    assert best == (a, b, c)


def test_las_mejores_respetan_el_limite():
    windows = [ranked_window(m, 80, 80, False) for m in range(1, 6)]
    assert best_windows(windows, limit=1) == (windows[0],)
    assert best_windows(windows, limit=5) == tuple(windows)


def test_las_mejores_pueden_venir_vacias():
    assert best_windows([ranked_window(1, 20, 90, True), ranked_window(2, None, None, False)]) == ()


def test_las_mejores_del_orden_son_las_primeras_que_no_son_de_alto_riesgo():
    windows = [
        window(1, water=sig(30, critical=True), frost=sig(100), heat=sig(100), soil=sig(100), supply=sig(100), market=sig(100)),
        window(2, **dict.fromkeys(SIGNALS, sig(85))),
        window(3, **dict.fromkeys(SIGNALS, sig(65))),
        window(4, **dict.fromkeys(SIGNALS, sig(75))),
        window(5, **dict.fromkeys(SIGNALS, sig(45))),
        window(6),
    ]

    best = best_windows(order_windows(windows, ALL_3))

    assert [w.sowing_start.month for w in best] == [2, 4, 3]
    assert all(not w.high_risk and w.limiting_score is not None for w in best)


# ------------------------------------------------------------------ determinismo y coherencia con el diagnóstico


def test_mismos_datos_mismo_orden():
    windows = [
        window(3, water=sig(62), frost=sig(90)),
        window(1, water=sig(20, critical=True), frost=sig(90)),
        window(7, water=sig(68), frost=sig(70)),
        window(2),
        window(5, water=sig(68), frost=sig(70)),
    ]
    first = order_windows(windows, ALL_3)
    for _ in range(5):
        assert order_windows(windows, ALL_3) == first
        assert best_windows(first) == best_windows(order_windows(list(reversed(windows)), ALL_3))


# Papa: FAO-56, fila «Idaho, USA» (catalog/crops.yaml): 165 días.
PAPA = [
    StageSpan("initial", 45, kc=0.5, frost_sensitive=True),
    StageSpan("development", 30, frost_sensitive=True),
    StageSpan("mid", 70, kc=1.15, frost_sensitive=True),
    StageSpan("late", 20, kc=0.75, frost_sensitive=True),
]


def diagnosis_signals(sowing: date) -> dict[str, SignalScore]:
    """Las calificaciones que daría el diagnóstico de esa fecha (fixture determinista: depende solo del mes)."""
    m = sowing.month
    return {
        "water": sig(40 + 5 * m),
        "frost": sig(15, critical=True) if m in (6, 7) else sig(95 - 3 * m),
        "heat": NOT_APPLICABLE,
        "soil": sig(72),
        "supply": INSUFFICIENT,
        "market": sig(50 + (m * 7) % 40),
    }


def test_una_ventana_del_orden_y_el_diagnostico_de_esa_fecha_dan_las_mismas_calificaciones():
    start = date(2026, 11, 14)
    windows = [
        WindowSignals(sowing_start=w.sowing_date, harvest_estimate=w.harvest_estimate, signals=diagnosis_signals(w.sowing_date))
        for w in monthly_sowing_windows(PAPA, start)
    ]

    ranked = order_windows(windows, ALL_3)

    assert len(ranked) == 12
    for result in ranked:
        diagnosis_window = crop_window(PAPA, result.sowing_start)
        assert result.harvest_estimate == diagnosis_window.harvest_estimate
        scores = {
            name: s.score
            for name, s in diagnosis_signals(result.sowing_start).items()
            if s.status == "available" and s.score is not None and counts(name, ALL_3[name], s.critical)
        }
        assert result.limiting_score == min(scores.values())
        assert scores[result.limiting_signal] == result.limiting_score
        assert result.high_risk == any(s.critical for s in diagnosis_signals(result.sowing_start).values())
    assert {r.sowing_start for r in ranked} == {w.sowing_start for w in windows}
    assert all(r.high_risk for r in ranked[-2:]) and not any(r.high_risk for r in ranked[:-2])
