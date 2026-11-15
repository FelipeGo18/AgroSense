"""Decisión 17 (HU-073): una señal `available` sin calificar (`level` y `score` nulos, `critical` falso), como el
mercado con historia, nunca cambia la luz, la acción, el factor limitante, el promedio ponderado, el alto riesgo ni el
orden de las ventanas, con cualquier peso (R1, R2). Las calificaciones son de prueba.
"""

from datetime import date

import pytest

from backend.engine.market_signal import PriceHistory, market_signal
from backend.engine.signal_score import AVAILABLE, SignalScore, rated_signals, signal_scores
from backend.engine.traffic_light import missing_data_limitations, traffic_light
from backend.engine.window_order import WindowSignals, order_windows, rank_window
from common.signals import P0_SIGNALS

UNRATED = SignalScore(AVAILABLE, None, None, False)
INSUFFICIENT = SignalScore("insufficient_data", None, None, False)
HISTORY = PriceHistory("1", "Corabastos (Bogotá)", "department", "papa-negra", 9, 0.774, 5, 0, 5, 2021, 2025, "dane_sipsa", "la papa negra")


def sig(score: int, critical: bool = False) -> SignalScore:
    level = "favorable" if score >= 70 else "moderate" if score >= 40 else "unfavorable"
    return SignalScore(AVAILABLE, score, level, critical)


WINDOWS = {
    "verde": {"water": sig(90), "frost": sig(85), "heat": sig(95), "soil": sig(80), "supply": INSUFFICIENT},
    "amarilla": {"water": sig(60), "frost": sig(85), "heat": sig(95), "soil": sig(80), "supply": INSUFFICIENT},
    "roja": {"water": sig(90), "frost": sig(20, critical=True), "heat": sig(95), "soil": sig(80), "supply": INSUFFICIENT},
    "sin_agua": {"water": INSUFFICIENT, "frost": sig(85), "heat": sig(95), "soil": sig(30), "supply": INSUFFICIENT},
}
WEIGHTS = [dict.fromkeys(P0_SIGNALS, 3), {**dict.fromkeys(P0_SIGNALS, 1), "market": 5}, {**dict.fromkeys(P0_SIGNALS, 0), "market": 5}]


def test_la_senal_de_mercado_con_historia_es_una_senal_sin_calificar():
    assert signal_scores({"market": market_signal(HISTORY)})["market"] == UNRATED


@pytest.mark.parametrize("weights", WEIGHTS)
@pytest.mark.parametrize("name", sorted(WINDOWS))
@pytest.mark.parametrize("basis", ["farmer", "default"])
def test_el_mercado_sin_calificar_da_la_misma_luz_y_accion_que_sin_mercado(name, weights, basis):
    without = traffic_light("suitable", {**WINDOWS[name], "market": INSUFFICIENT}, weights, basis)
    with_market = traffic_light("suitable", {**WINDOWS[name], "market": UNRATED}, weights, basis)
    assert (with_market.light, with_market.action, with_market.limiting_signal, with_market.high_risk) == (
        without.light, without.action, without.limiting_signal, without.high_risk
    )  # fmt: skip
    assert "mercado" not in " ".join(with_market.reasons)


@pytest.mark.parametrize("weights", WEIGHTS)
def test_el_mercado_sin_calificar_no_es_factor_limitante_ni_entra_al_promedio(weights):
    signals = {**WINDOWS["verde"], "market": UNRATED}
    assert all(name != "market" for name, _, _ in rated_signals(signals, weights))
    window = WindowSignals(date(2027, 4, 1), date(2027, 9, 13), signals)
    alone = WindowSignals(date(2027, 4, 1), date(2027, 9, 13), {**WINDOWS["verde"], "market": INSUFFICIENT})
    ranked, reference = rank_window(window, weights), rank_window(alone, weights)
    assert (ranked.limiting_signal, ranked.limiting_score, ranked.weighted_score, ranked.high_risk) == (
        reference.limiting_signal, reference.limiting_score, reference.weighted_score, reference.high_risk
    )  # fmt: skip


def test_solo_el_mercado_sin_calificar_no_da_evidencia_y_la_luz_es_amarilla():
    """Con peso solo en el mercado, sin calificar: no hay ninguna señal que cuente y califique (regla 3, HU-074)."""
    weights = {**dict.fromkeys(P0_SIGNALS, 0), "market": 5}
    result = traffic_light("suitable", {**WINDOWS["verde"], "market": UNRATED}, weights, "farmer")
    assert (result.light, result.action, result.limiting_signal) == ("yellow", "other_window", None)
    window = rank_window(WindowSignals(date(2027, 4, 1), date(2027, 9, 13), {"market": UNRATED}), weights)
    assert (window.limiting_score, window.weighted_score, window.high_risk) == (None, None, False)


def test_el_mercado_sin_calificar_no_cambia_el_orden_de_las_ventanas():
    windows = [
        WindowSignals(date(2027, m, 1), date(2027, m + 5, 1), {**WINDOWS[n]}) for m, n in zip((1, 2, 3, 4), sorted(WINDOWS), strict=True)
    ]
    with_market = [WindowSignals(w.sowing_start, w.harvest_estimate, {**w.signals, "market": UNRATED}) for w in windows]
    for weights in WEIGHTS:
        assert [w.sowing_start for w in order_windows(windows, weights)] == [w.sowing_start for w in order_windows(with_market, weights)]


def test_sin_calificar_no_es_sin_datos_en_las_limitaciones():
    """Sin calificar no es «sin datos para la zona»: el dato existe. La limitación la pone la señal misma."""
    texts = missing_data_limitations({**WINDOWS["verde"], "market": UNRATED})
    assert not any("mercado" in text for text in texts)
    assert market_signal(HISTORY).limitations == ("La oferta y el mercado se muestran sin calificar: no cambian la luz",)
