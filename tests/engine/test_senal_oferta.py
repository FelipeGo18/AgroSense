"""Señal de oferta sin calificar (HU-072, decisión 17; specs/01-reglas.md, «Señales de una ventana»). Con el área de
EVA, la señal es `available` con nivel y calificación nulos: se muestra, pero nunca cambia la luz, la acción, el factor
limitante ni el orden. Sin dato, `insufficient_data` (R1)."""

from dataclasses import replace

import pytest

from backend.engine.market_signal import UNRATED_LIMITATION
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, SignalScore, signal_scores
from backend.engine.supply_signal import NO_DATA_REASON, UNRATED_REASON, SupplySemester, SupplySignalResult, supply_signal
from backend.engine.traffic_light import traffic_light
from tests.textos import speaks_as_forecast

B_2025 = SupplySemester(year=2025, semester="B", preliminary=True, planted_ha=420.0, planted_change_pct=35.0, same_as_previous=False)


def test_sin_dato_es_sin_datos():
    assert supply_signal(None, "papa") == SupplySignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_con_dato_es_disponible_sin_calificar():
    result = supply_signal(B_2025, "papa")
    assert (result.status, result.level, result.score, result.critical) == (AVAILABLE, None, None, False)
    assert result.indicators == ("planted_ha", "planted_change_pct")
    assert result.limitations == (UNRATED_LIMITATION,)
    assert result.semester == B_2025


def test_las_razones_son_las_del_contrato():
    assert supply_signal(B_2025, "papa").reasons == (
        UNRATED_REASON,
        "En 2025 B (último dato, preliminar) EVA registra 420 ha de papa en su municipio, 35 % más que el promedio de los "
        "tres semestres B anteriores",
    )


@pytest.mark.parametrize(
    "change,text",
    [(-40.0, "40 % menos que el promedio"), (0.0, "igual que el promedio"), (12.5, "13 % más que el promedio")],
)
def test_la_variacion_dice_mas_menos_o_igual(change, text):
    assert text in supply_signal(replace(B_2025, planted_change_pct=change), "papa").reasons[1]


def test_sin_variacion_no_la_nombra():
    result = supply_signal(replace(B_2025, planted_change_pct=None), "papa")
    assert result.reasons[1] == "En 2025 B (último dato, preliminar) EVA registra 420 ha de papa en su municipio"
    assert result.indicators == ("planted_ha",)


def test_con_menos_de_tres_semestres_no_dice_los_tres():
    reason = supply_signal(replace(B_2025, complete_baseline=False), "papa").reasons[1]
    assert "los semestres B anteriores con dato (menos de tres)" in reason and "los tres" not in reason


def test_preliminar_y_repetido_aparecen_en_la_razon():
    repeated = supply_signal(replace(B_2025, same_as_previous=True), "papa").reasons[1]
    assert "(último dato, preliminar)" in repeated
    assert repeated.endswith(". EVA trae el mismo valor que en 2024 B")
    final = supply_signal(replace(B_2025, preliminary=False), "papa").reasons[1]
    assert "(último dato)" in final and "preliminar" not in final


def test_ninguna_razon_es_veredicto_ni_pronostico():
    for change in (-60.0, 0.0, 80.0):
        reason = supply_signal(replace(B_2025, planted_change_pct=change, same_as_previous=True), "papa").reasons[1]
        assert not any(word in reason.lower() for word in ("mucho", "poco", "sobreoferta"))
        assert not speaks_as_forecast(reason)


def test_mismo_dato_mismo_resultado():
    """R4."""
    assert all(supply_signal(B_2025, "papa") == supply_signal(B_2025, "papa") for _ in range(5))


CLIMATE = {
    "water": SignalScore(AVAILABLE, 82, "favorable", False),
    "frost": SignalScore(AVAILABLE, 58, "moderate", False),
    "heat": SignalScore(AVAILABLE, 94, "favorable", False),
    "soil": SignalScore(AVAILABLE, 80, "favorable", False),
    "market": SignalScore(INSUFFICIENT_DATA, None, None, False),
}


@pytest.mark.parametrize("supply_weight", [0, 1, 3, 5])
def test_con_dato_la_luz_la_accion_y_el_factor_limitante_son_los_mismos(supply_weight):
    weights = {"water": 3, "frost": 4, "heat": 2, "soil": 2, "supply": supply_weight, "market": 1}
    with_data = {**CLIMATE, **signal_scores({"supply": supply_signal(replace(B_2025, planted_change_pct=80.0), "papa")})}
    without = {**CLIMATE, "supply": SignalScore(INSUFFICIENT_DATA, None, None, False)}
    a, b = traffic_light("suitable", with_data, weights, "farmer"), traffic_light("suitable", without, weights, "farmer")
    assert (a.light, a.action, a.limiting_signal, a.high_risk) == (b.light, b.action, b.limiting_signal, b.high_risk)
