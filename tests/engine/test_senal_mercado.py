"""Señal de mercado (HU-073; specs/01-reglas.md, «Señales de una ventana»). Hoy la curva de `market` de
`thresholds.yaml` es nula (espera una fuente: regla del equipo del 11 de noviembre de 2026), así que la señal siempre es
`insufficient_data`. La rama con índice (la razón) se prueba con una curva de prueba. Es historia de precios, nunca un
pronóstico (decisión 4)."""

import re
from dataclasses import replace

import pytest

from backend.api.calc_examples import SIGNALS_OK
from backend.config.thresholds import SignalThreshold, load_thresholds
from backend.engine.market_signal import NO_DATA_REASON, MarketSignalResult, market_signal
from backend.engine.signal_score import INSUFFICIENT_DATA

FORECAST_WORDS = re.compile(r"\b(va a|irá|subirá|bajará|estará|será|pronostic\w*|predic\w*|futur\w*)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


@pytest.fixture(scope="module")
def with_test_curve(thresholds):
    """Umbrales con una curva hipotética de `market`, SOLO DE PRUEBA: no es la del proyecto (que es nula, sin fuente).
    Sirve para llegar a la razón, que con la configuración real no se alcanza. Estas pruebas afirman sobre el texto de
    la razón, nunca sobre niveles ni calificaciones."""
    market = SignalThreshold(
        variable="seasonal_index",
        unit="",
        curve=((0.5, 0.0), (1.0, 70.0), (1.5, 100.0)),
        critical_below=1,
        source_id="dane_sipsa",
    )
    return replace(thresholds, signals={**thresholds.signals, "market": market})


@pytest.mark.parametrize("index,years", [(None, None), (None, 5), (float("nan"), 5)])
def test_sin_indice_es_sin_datos_con_la_razon_del_contrato(thresholds, index, years):
    assert market_signal(index, years, thresholds) == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_la_razon_sin_datos_es_la_del_contrato():
    """El texto vive en una sola constante del motor; aquí se ancla al ejemplo del contrato (specs/02-contratos.md)."""
    assert SIGNALS_OK["market"]["reasons"] == [NO_DATA_REASON]


@pytest.mark.parametrize("index", [None, 0.774, 0.961, 1.0, 1.063, 1.259])
def test_con_la_curva_nula_siempre_es_sin_datos_aunque_haya_indice(thresholds, index):
    """Sin fuente para los cortes (`curve: null`), un índice válido tampoco califica (R1, R8)."""
    assert market_signal(index, 5, thresholds) == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_la_curva_de_mercado_del_proyecto_es_nula(thresholds):
    assert thresholds.signals["market"].curve is None


@pytest.mark.parametrize(
    "index,text",
    [
        (1.259, "un 26 % por encima del promedio de su año"),
        (0.961, "un 4 % por debajo del promedio de su año"),
        (0.774, "un 23 % por debajo del promedio de su año"),
        (1.0, "ha estado en el promedio de su año"),
    ],
)
def test_la_razon_dice_cuanto_arriba_o_abajo_y_los_anos(with_test_curve, index, text):
    (reason,) = market_signal(index, 5, with_test_curve).reasons
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
def test_la_razon_redondea_desde_la_mitad_hacia_arriba(with_test_curve, index, text):
    """12,5 % da 13 y no 12 (el `round` de Python va al par); 0,995 y 1,005 son simétricos (1 %) aunque el flotante dé 0,49999…"""
    (reason,) = market_signal(index, 5, with_test_curve).reasons
    assert text in reason


@pytest.mark.parametrize("index", [0.774, 0.961, 1.0, 1.063, 1.259])
def test_la_razon_no_habla_como_pronostico(with_test_curve, index):
    (reason,) = market_signal(index, 5, with_test_curve).reasons
    without_label = reason.replace("no un pronóstico", "")
    assert not FORECAST_WORDS.search(without_label), reason
    assert "HU-" not in reason and ".parquet" not in reason and ".yaml" not in reason


def test_la_razon_no_nombra_el_mes(with_test_curve):
    months = r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b"
    (reason,) = market_signal(1.2, 5, with_test_curve).reasons
    assert not re.search(months, reason, re.IGNORECASE)


def test_sin_anos_no_inventa_el_periodo(with_test_curve):
    (reason,) = market_signal(1.2, None, with_test_curve).reasons
    assert reason.startswith("En los años con precios publicados") and "None" not in reason


@pytest.mark.parametrize("fixture_name", ["thresholds", "with_test_curve"])
def test_mismo_dato_mismo_resultado(request, fixture_name):
    """R4."""
    config = request.getfixturevalue(fixture_name)
    first = market_signal(0.93, 4, config)
    assert all(market_signal(0.93, 4, config) == first for _ in range(5))


@pytest.mark.parametrize("fixture_name", ["thresholds", "with_test_curve"])
def test_el_resultado_es_inmutable(request, fixture_name):
    result = market_signal(1.1, 5, request.getfixturevalue(fixture_name))
    with pytest.raises(AttributeError):
        result.score = 0  # type: ignore[misc]
