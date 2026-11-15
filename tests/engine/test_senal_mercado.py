"""Señal de mercado (HU-073; decisión 17; specs/01-reglas.md, «Oferta y mercado sin calificar»).

Con la historia del precio del mes de cosecha, la señal es `available` sin calificar (`level` y `score` nulos,
`critical` falso) y cuenta años; sin historia, `insufficient_data` (R1). Es historia de precios, nunca un pronóstico
(decisión 4). Los valores de Corabastos son los del ejemplo del contrato (2021–2025); los demás son de prueba.
"""

from dataclasses import replace

import pytest

from backend.api.calc_examples import SIGNALS_OK
from backend.engine.market_signal import (
    INDICATORS,
    NO_COUNT_REASON,
    NO_DATA_REASON,
    UNRATED_LIMITATION,
    UNRATED_REASON,
    MarketSignalResult,
    PriceHistory,
    harvest_years_share,
    market_signal,
)
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from tests.textos import FORECAST_WORDS

DECEMBER = PriceHistory(
    market_id="1",
    market="Corabastos (Bogotá)",
    market_basis="department",
    product_id="papa-negra",
    month=12,
    seasonal_index=1.07,
    years=5,
    years_above=3,
    years_below=2,
    first_year=2021,
    last_year=2025,
    source_id="dane_sipsa",
    product_name="la papa negra",
)
CONTRACT_REASON = (
    "En Corabastos, en diciembre (el mes en que saldría su cosecha), el precio de la papa negra estuvo por encima del "
    "promedio de su año en 3 de 5 años (2021–2025) y por debajo en 2; en promedio, 7 % por encima. Así fue en la "
    "historia: no es un pronóstico del precio. Fuente: DANE"
)


def test_sin_historia_es_sin_datos_con_la_razon_del_contrato():
    assert market_signal(None) == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))


def test_con_historia_es_available_sin_calificar():
    """Decisión 17: el dato existe, pero no se califica (R1 separa disponibilidad y nivel)."""
    result = market_signal(DECEMBER)
    assert (result.status, result.level, result.score, result.critical) == (AVAILABLE, None, None, False)
    assert result.indicators == INDICATORS == ("seasonal_index", "years_above", "years_below")
    assert result.price_history == DECEMBER
    assert result.limitations == (UNRATED_LIMITATION,)


def test_las_razones_son_las_del_contrato():
    assert market_signal(DECEMBER).reasons == (UNRATED_REASON, CONTRACT_REASON)
    assert SIGNALS_OK["market"]["reasons"] == [UNRATED_REASON, CONTRACT_REASON]


def test_el_ejemplo_del_contrato_trae_la_misma_historia():
    expected = {k: v for k, v in vars(DECEMBER).items() if k not in ("product_name", "override_reason")}
    assert SIGNALS_OK["market"]["price_history"] == expected


def test_la_papa_de_septiembre_estuvo_siempre_por_debajo():
    """El caso de HU-073: papa negra de Corabastos en septiembre, 0 de 5 por encima y 5 por debajo, índice 0,774."""
    september = replace(DECEMBER, month=9, seasonal_index=0.774, years_above=0, years_below=5)
    (_, reason) = market_signal(september).reasons
    assert "en septiembre" in reason
    assert "por encima del promedio de su año en 0 de 5 años (2021–2025) y por debajo en 5; en promedio, 23 % por debajo" in reason


def test_un_ano_igual_al_promedio_no_cuenta_en_ninguno_y_se_dice():
    tie = replace(DECEMBER, years_above=2, years_below=2)
    (_, reason) = market_signal(tie).reasons
    assert "en 2 de 5 años (2021–2025) y por debajo en 2, y en 1 quedó en el promedio de su año;" in reason


def test_con_central_por_cultivo_una_razon_dice_por_que():
    why = "Tunja no publica papa negra desde el 27 de julio de 2021; su temporada es casi la de Corabastos"
    override = replace(DECEMBER, market_basis="crop_override", override_reason=why)
    assert market_signal(override).reasons == (UNRATED_REASON, f"Se usa la central de Corabastos (Bogotá): {why}", CONTRACT_REASON)


def test_un_dataset_sin_los_anos_contados_no_inventa_el_conteo():
    """Un `market_month` publicado antes de HU-073: la señal es `insufficient_data` y lo dice como razón y limitación."""
    old = replace(DECEMBER, years_above=None, years_below=None, first_year=None, last_year=None)
    result = market_signal(old)
    assert result == MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_COUNT_REASON,), (NO_COUNT_REASON,))
    assert harvest_years_share(old) is None


@pytest.mark.parametrize(
    "index,text",
    [
        (1.125, "en promedio, 13 % por encima"),
        (0.875, "en promedio, 13 % por debajo"),
        (0.995, "en promedio, 1 % por debajo"),
        (1.005, "en promedio, 1 % por encima"),
        (1.0, "en promedio, como el promedio de su año"),
    ],
)
def test_el_promedio_redondea_desde_la_mitad_hacia_arriba(index, text):
    """12,5 % da 13 y no 12 (el `round` de Python va al par); 0,995 y 1,005 son simétricos (1 %)."""
    assert text in market_signal(replace(DECEMBER, seasonal_index=index)).reasons[-1]


def test_sin_periodo_no_inventa_los_anos():
    reason = market_signal(replace(DECEMBER, first_year=None)).reasons[-1]
    assert "(" not in reason.split("años", 1)[1].split(";", 1)[0] and "None" not in reason


@pytest.mark.parametrize("index", [0.774, 0.961, 1.0, 1.063, 1.259])
def test_las_razones_no_hablan_como_pronostico_ni_dan_veredicto(index):
    for reason in market_signal(replace(DECEMBER, seasonal_index=index)).reasons:
        without_label = reason.replace("no es un pronóstico", "")
        assert not FORECAST_WORDS.search(without_label), reason
        assert "precio bajo" not in reason.replace("qué es un precio bajo", "") and "precio alto" not in reason
        assert "HU-" not in reason and ".parquet" not in reason and ".yaml" not in reason


def test_una_base_de_central_desconocida_es_un_error():
    with pytest.raises(ValueError):
        market_signal(replace(DECEMBER, market_basis="otra"))


@pytest.mark.parametrize("above,years,share", [(0, 5, 0), (5, 5, 100), (3, 5, 60), (1, 3, 100 / 3)])
def test_la_frecuencia_del_ingreso_es_cien_por_los_anos_por_encima_sobre_los_anos(above, years, share):
    """HU-241: 100 × `years_above` / `years`."""
    history = replace(DECEMBER, years=years, years_above=above, years_below=years - above)
    assert harvest_years_share(history) == pytest.approx(share)
    assert harvest_years_share(None) is None


def test_mismo_dato_mismo_resultado():
    """R4."""
    first = market_signal(DECEMBER)
    assert all(market_signal(DECEMBER) == first for _ in range(5))


def test_el_resultado_es_inmutable():
    result = market_signal(DECEMBER)
    with pytest.raises(AttributeError):
        result.score = 0  # type: ignore[misc]
