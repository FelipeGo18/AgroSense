"""Señal de mercado (HU-073; specs/01-reglas.md, «Señales de una ventana»): el índice estacional del mes de cosecha con
la curva de `thresholds.yaml`. Es historia de precios, nunca un pronóstico (decisión 4)."""

import re

import pytest

from backend.api.calc_examples import SIGNALS_OK
from backend.config.thresholds import load_thresholds
from backend.engine.market_signal import NO_DATA_REASON, MarketSignalResult, market_signal
from backend.engine.signal_score import AVAILABLE, FAVORABLE, INSUFFICIENT_DATA, MODERATE, UNFAVORABLE

FORECAST_WORDS = re.compile(r"\b(va a|irá|subirá|bajará|estará|será|pronostic\w*|predic\w*|futur\w*)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


@pytest.mark.parametrize("index,years", [(None, None), (None, 5), (float("nan"), 5)])
def test_sin_indice_es_sin_datos_con_la_razon_del_contrato(thresholds, index, years):
    assert market_signal(index, years, thresholds) == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_la_razon_sin_datos_es_la_del_contrato():
    """El texto vive en una sola constante del motor; aquí se ancla al ejemplo del contrato (specs/02-contratos.md)."""
    assert SIGNALS_OK["market"]["reasons"] == [NO_DATA_REASON]


@pytest.mark.parametrize(
    "index,score,level,critical,text",
    [
        (1.259, 100, FAVORABLE, False, "un 26 % por encima del promedio de su año"),
        (1.063, 83, FAVORABLE, False, "un 6 % por encima del promedio de su año"),
        (0.961, 57, MODERATE, False, "un 4 % por debajo del promedio de su año"),
        (0.90, 33, UNFAVORABLE, False, "un 10 % por debajo del promedio de su año"),
        (0.774, 0, UNFAVORABLE, True, "un 23 % por debajo del promedio de su año"),
        (1.0, 70, FAVORABLE, False, "ha estado en el promedio de su año"),
    ],
)
def test_con_indice_califica_y_dice_cuanto_arriba_o_abajo(thresholds, index, score, level, critical, text):
    """Los índices de la papa en Corabastos (abril, enero, noviembre y septiembre del dataset publicado), más 0,90 y 1,0.
    A mano, con la curva [[0,85, 0], [0,91, 40], [1,0, 70], [1,15, 100]]: 1,063 -> 70 + 0,063 / 0,15 * 30 = 82,6 -> 83;

    0,961 -> 40 + 0,051 / 0,09 * 30 = 57; 0,90 -> 0,05 / 0,06 * 40 = 33,3 -> 33 (desfavorable, no crítica);
    0,774 -> 0 (crítica); 1,0 -> 70, favorable: el precio promedio no es un riesgo."""
    result = market_signal(index, 5, thresholds)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, score, level, critical)
    assert result.indicators == ("seasonal_index",)
    (reason,) = result.reasons
    assert text in reason
    assert "En 5 años de precios publicados" in reason
    assert "no un pronóstico" in reason


@pytest.mark.parametrize(
    "index,text",
    [
        (1.125, "un 13 % por encima del promedio de su año"),
        (0.875, "un 13 % por debajo del promedio de su año"),
        (0.995, "un 1 % por debajo del promedio de su año"),
        (1.005, "un 1 % por encima del promedio de su año"),
        (1.0, "ha estado en el promedio de su año"),
    ],
)
def test_la_razon_redondea_desde_la_mitad_hacia_arriba(thresholds, index, text):
    """12,5 % da 13 y no 12 (el `round` de Python va al par); 0,995 y 1,005 son simétricos (1 %) aunque el flotante dé 0,49999…"""
    (reason,) = market_signal(index, 5, thresholds).reasons
    assert text in reason


@pytest.mark.parametrize("index", [0.774, 0.961, 1.0, 1.063, 1.259])
def test_la_razon_no_habla_como_pronostico(thresholds, index):
    (reason,) = market_signal(index, 5, thresholds).reasons
    without_label = reason.replace("no un pronóstico", "")
    assert not FORECAST_WORDS.search(without_label), reason
    assert "HU-" not in reason and ".parquet" not in reason and ".yaml" not in reason


def test_la_razon_no_nombra_el_mes(thresholds):
    months = r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b"
    (reason,) = market_signal(1.2, 5, thresholds).reasons
    assert not re.search(months, reason, re.IGNORECASE)


def test_sin_anos_no_inventa_el_periodo(thresholds):
    (reason,) = market_signal(1.2, None, thresholds).reasons
    assert reason.startswith("En los años con precios publicados") and "None" not in reason


def test_mismo_dato_mismo_resultado(thresholds):
    """R4."""
    first = market_signal(0.93, 4, thresholds)
    assert all(market_signal(0.93, 4, thresholds) == first for _ in range(5))


def test_el_resultado_es_inmutable(thresholds):
    result = market_signal(1.1, 5, thresholds)
    with pytest.raises(AttributeError):
        result.score = 0  # type: ignore[misc]
