"""Señal de mercado sin calificar (HU-073, decisión 17; specs/01-reglas.md, «Señales de una ventana»). Con historia de
precio, la señal es `available` con nivel y calificación nulos: se muestra, pero nunca cambia la luz, la acción, el
factor limitante ni el orden. Sin historia, `insufficient_data` (R1). Es historia de precios, nunca un pronóstico
(decisión 4)."""

from dataclasses import replace
from datetime import date

import pytest

from backend.api.calc_examples import SIGNALS_OK
from backend.engine.market_signal import (
    CROP_OVERRIDE,
    DEPARTMENT,
    NO_DATA_REASON,
    UNRATED_LIMITATION,
    UNRATED_REASON,
    MarketSignalResult,
    PriceHistory,
    market_signal,
)
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, SignalScore, signal_scores
from backend.engine.traffic_light import traffic_light
from backend.engine.window_order import WindowSignals, order_windows
from tests.textos import speaks_as_forecast

# La papa negra de Corabastos en septiembre, como está publicada (2021–2025): 0 años por encima y 5 por debajo.
SEPTEMBER = PriceHistory(
    market_id="1",
    market="Corabastos (Bogotá)",
    market_basis=DEPARTMENT,
    product_id="papa-negra",
    month=9,
    seasonal_index=0.774,
    years=5,
    years_above=0,
    years_below=5,
    first_year=2021,
    last_year=2025,
    source_id="dane_sipsa",
)
OVERRIDE_REASON = "Tunja no publica papa negra desde el 27 de julio de 2021; su temporada es casi la de Corabastos"


def test_sin_historia_es_sin_datos_con_la_razon_del_contrato():
    assert market_signal(None, "la papa") == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_con_historia_es_disponible_sin_calificar():
    result = market_signal(SEPTEMBER, "la papa", "la papa negra")
    assert (result.status, result.level, result.score, result.critical) == (AVAILABLE, None, None, False)
    assert result.indicators == ("seasonal_index",)
    assert result.limitations == (UNRATED_LIMITATION,)
    assert result.price_history == SEPTEMBER


def test_la_razon_cuenta_los_anos_de_la_tabla():
    reasons = market_signal(SEPTEMBER, "la papa", "la papa negra").reasons
    assert reasons == (
        UNRATED_REASON,
        "En Corabastos, en septiembre (el mes en que saldría su cosecha), el precio de la papa negra "
        "estuvo por encima del promedio de su año en 0 de 5 años (2021–2025) y por debajo en 5; en promedio, 23 % por "
        "debajo. Así fue en la historia: no es un pronóstico del precio. Fuente: DANE",
    )


@pytest.mark.parametrize(
    "index,text",
    [
        (1.259, "en promedio, 26 % por encima"),
        (0.961, "en promedio, 4 % por debajo"),
        (1.125, "en promedio, 13 % por encima"),
        (0.995, "en promedio, 1 % por debajo"),
        (1.005, "en promedio, 1 % por encima"),
        (1.0, "en promedio, igual al de su año"),
    ],
)
def test_el_promedio_redondea_desde_la_mitad_hacia_arriba(index, text):
    """12,5 % da 13 y no 12 (el `round` de Python va al par); 0,995 y 1,005 son simétricos (1 %)."""
    assert text in market_signal(replace(SEPTEMBER, seasonal_index=index), "la papa").reasons[1]


def test_sin_periodo_no_lo_inventa():
    reason = market_signal(replace(SEPTEMBER, first_year=None, last_year=None), "la papa").reasons[1]
    assert "en 0 de 5 años y por debajo en 5" in reason and "None" not in reason


def test_un_ano_igual_al_promedio_se_dice_para_que_los_anos_cuadren():
    """Un mes justo en el promedio de su año no cuenta en ninguno (contrato); la razón lo dice (revisión del PR #158)."""
    tie = replace(SEPTEMBER, years_above=3, years_below=1, seasonal_index=1.0)
    assert (
        "en 3 de 5 años (2021–2025) y por debajo en 1, y en 1 quedó igual; en promedio, igual al de su año"
        in (market_signal(tie, "la papa").reasons[1])
    )
    assert "quedó igual" not in market_signal(SEPTEMBER, "la papa").reasons[1]


def test_sin_nombre_del_producto_va_solo_el_cultivo():
    assert "el precio de la papa estuvo" in market_signal(SEPTEMBER, "la papa").reasons[1]


def test_con_la_central_del_cultivo_la_razon_dice_por_que():
    override = replace(SEPTEMBER, market_basis=CROP_OVERRIDE)
    reasons = market_signal(override, "la papa", "la papa negra", OVERRIDE_REASON).reasons
    assert reasons[-1] == f"Se usa Corabastos: {OVERRIDE_REASON}"
    # Con la central del departamento no se dice nada más, aunque llegue un porqué.
    assert len(market_signal(SEPTEMBER, "la papa", "la papa negra", OVERRIDE_REASON).reasons) == 2


def test_la_historia_no_es_veredicto_ni_pronostico():
    """Nunca «precio bajo» ni «precio alto» como veredicto (R5), nunca un pronóstico (decisión 4)."""
    for index in (0.774, 1.0, 1.259):
        reason = market_signal(replace(SEPTEMBER, seasonal_index=index), "la papa", "la papa negra").reasons[1]
        assert "precio bajo" not in reason and "precio alto" not in reason
        assert not speaks_as_forecast(reason), reason
        assert "HU-" not in reason and ".parquet" not in reason and ".yaml" not in reason


def test_mismo_dato_mismo_resultado():
    """R4."""
    first = market_signal(SEPTEMBER, "la papa", "la papa negra")
    assert all(market_signal(SEPTEMBER, "la papa", "la papa negra") == first for _ in range(5))


def test_el_resultado_es_inmutable():
    with pytest.raises(AttributeError):
        market_signal(SEPTEMBER, "la papa").score = 0  # type: ignore[misc]


def test_el_ejemplo_del_contrato_es_sin_calificar():
    example = SIGNALS_OK["market"]
    assert (example["status"], example["level"], example["score"]) == (AVAILABLE, None, None)
    assert example["reasons"][0] == UNRATED_REASON


# --- La señal sin calificar no cambia nada: la luz, la acción, el factor limitante ni el orden (R2) ---------------

CLIMATE = {
    "water": SignalScore(AVAILABLE, 82, "favorable", False),
    "frost": SignalScore(AVAILABLE, 58, "moderate", False),
    "heat": SignalScore(AVAILABLE, 94, "favorable", False),
    "soil": SignalScore(AVAILABLE, 80, "favorable", False),
    "supply": SignalScore(INSUFFICIENT_DATA, None, None, False),
}
WITHOUT = {**CLIMATE, "market": SignalScore(INSUFFICIENT_DATA, None, None, False)}
WITH = {**CLIMATE, **signal_scores({"market": market_signal(SEPTEMBER, "la papa")})}


@pytest.mark.parametrize("market_weight", [0, 1, 3, 4, 5])
def test_con_historia_la_luz_la_accion_y_el_factor_limitante_son_los_mismos(market_weight):
    weights = {"water": 3, "frost": 4, "heat": 2, "soil": 2, "supply": 1, "market": market_weight}
    with_history, without = traffic_light("suitable", WITH, weights, "farmer"), traffic_light("suitable", WITHOUT, weights, "farmer")
    assert (with_history.light, with_history.action, with_history.limiting_signal, with_history.high_risk) == (
        without.light,
        without.action,
        without.limiting_signal,
        without.high_risk,
    )


@pytest.mark.parametrize("market_weight", [1, 5])
def test_con_historia_el_orden_de_las_ventanas_es_el_mismo(market_weight):
    weights = {"water": 3, "frost": 4, "heat": 2, "soil": 2, "supply": 1, "market": market_weight}
    better = {**CLIMATE, "frost": SignalScore(AVAILABLE, 90, "favorable", False)}

    def ranked(market):
        windows = [
            WindowSignals(date(2027, 4, 5), date(2027, 9, 13), {**CLIMATE, "market": market}),
            WindowSignals(date(2027, 5, 3), date(2027, 10, 11), {**better, "market": market}),
        ]
        return [(w.sowing_start, w.limiting_signal, w.limiting_score, w.weighted_score) for w in order_windows(windows, weights)]

    assert ranked(WITH["market"]) == ranked(WITHOUT["market"])
