"""Los datos de la señal de mercado (HU-073, decisión 17): qué central le toca a cada municipio y a cada cultivo, y la
historia del precio del mes de cosecha, leídos del dataset publicado (`data/published/`, el de la demo) y del de ejemplo
de las pruebas."""

from dataclasses import replace

import polars as pl
import pytest

from backend.api.market_signal import MarketChoice, market_choice, market_for, market_history, market_in
from backend.dataset import load
from backend.engine.market_signal import CROP_OVERRIDE, DEPARTMENT, NO_DATA_REASON, UNRATED_REASON
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from pipeline.build import PUBLISHED

OVERRIDE_REASON = "Tunja no publica papa negra desde el 27 de julio de 2021; su temporada es casi la de Corabastos"


@pytest.fixture(scope="module")
def published():
    """El dataset real publicado, con `market_month` y los mapas de centrales del manifiesto."""
    return load(PUBLISHED)


def municipality_of(dataset, department_id):
    return next(m for m in dataset.municipalities.values() if m.department_id == department_id)


def test_market_month_trae_los_anos_por_encima_y_por_debajo(published):
    table = published.market_month
    assert {"seasonal_index", "years", "years_above", "years_below", "first_year", "last_year"} <= set(table.columns)
    assert table.filter(pl.col("years_above") + pl.col("years_below") > pl.col("years")).is_empty()


def test_la_papa_de_corabastos_en_septiembre_es_la_de_la_spec(published):
    """El criterio de HU-073: 0 años por encima, 5 por debajo (2021–2025) e índice 0,774."""
    row = published.market_month.filter((pl.col("crop_id") == "papa") & (pl.col("market_id") == "1") & (pl.col("month") == 9)).row(
        0, named=True
    )
    assert (row["years_above"], row["years_below"], row["years"], row["seasonal_index"]) == (0, 5, 5, 0.774)
    assert (row["first_year"], row["last_year"]) == (2021, 2025)


def test_sin_market_month_publicado_queda_nulo_y_lo_demas_carga(dataset):
    """El dataset de ejemplo no publica precios: `market_month` es nulo (R1) y el resto se lee igual."""
    loaded = load(dataset)
    assert loaded.market_month is None
    assert loaded.municipalities


def test_el_manifiesto_trae_los_mapas_de_centrales(published):
    assert published.region["department_markets"] == {"15": "9", "25": "1"}
    assert published.region["crop_market_overrides"] == {"15": {"papa": {"market_id": "1", "reason": OVERRIDE_REASON}}}


def test_boyaca_vende_en_tunja_y_cundinamarca_en_corabastos(published):
    assert market_for(published, published.municipalities["15001"]) == "9"
    assert market_for(published, municipality_of(published, "25")) == "1"


def test_la_papa_de_boyaca_usa_corabastos_y_dice_por_que(published):
    """Tunja no publica papa negra con 3 años completos: se usa la central de `crop_market_overrides`."""
    assert market_choice(published, published.municipalities["15001"], "papa") == MarketChoice("1", CROP_OVERRIDE, OVERRIDE_REASON)
    result = market_in(published, published.municipalities["15001"], "papa", "la papa", 9)
    assert result.status == AVAILABLE and result.level is None and result.score is None
    assert result.price_history.market_basis == CROP_OVERRIDE
    assert result.reasons[-1] == f"Se usa Corabastos: {OVERRIDE_REASON}"


def test_la_arveja_de_boyaca_usa_tunja(published):
    assert market_choice(published, published.municipalities["15001"], "arveja") == MarketChoice("9", DEPARTMENT)
    result = market_in(published, published.municipalities["15001"], "arveja", "la arveja", 5)
    assert result.price_history.market_id == "9" and result.price_history.market_basis == DEPARTMENT
    assert result.reasons[1].startswith("En Tunja, en mayo (el mes en que saldría su cosecha), el precio de la arveja")


def test_la_papa_de_cundinamarca_usa_su_central(published):
    assert market_choice(published, municipality_of(published, "25"), "papa") == MarketChoice("1", DEPARTMENT)


def test_un_departamento_fuera_del_mapa_no_tiene_central(published):
    """Nunca se usa otra central por defecto (R1)."""
    outside = replace(published.municipalities["15001"], department_id="05")
    assert market_for(published, outside) is None
    assert market_choice(published, outside, "papa") is None
    assert market_in(published, outside, "papa", "la papa", 9).status == INSUFFICIENT_DATA


def test_sin_la_central_del_cultivo_la_papa_de_boyaca_no_tiene_historia(published):
    """Sin `crop_market_overrides`, la papa de Boyacá se queda en Tunja, que no tiene filas: sin datos (R1)."""
    without = replace(published, region={k: v for k, v in published.region.items() if k != "crop_market_overrides"})
    assert market_choice(without, without.municipalities["15001"], "papa") == MarketChoice("9", DEPARTMENT)
    result = market_in(without, without.municipalities["15001"], "papa", "la papa", 9)
    assert (result.status, result.reasons, result.price_history) == (INSUFFICIENT_DATA, (NO_DATA_REASON,), None)


@pytest.mark.parametrize("crop_id", ["haba", "maiz"])
def test_un_cultivo_sin_producto_en_sipsa_no_tiene_historia(published, crop_id):
    assert market_in(published, published.municipalities["15001"], crop_id, "el cultivo", 4).status == INSUFFICIENT_DATA


def test_sin_mes_sin_central_o_sin_market_month_no_hay_historia(published):
    boyaca = published.municipalities["15001"]
    assert market_in(published, boyaca, "papa", "la papa", None).status == INSUFFICIENT_DATA
    assert market_history(published, None, "papa", 4).history is None
    assert market_history(replace(published, market_month=None), MarketChoice("1", DEPARTMENT), "papa", 4).history is None


def test_la_historia_trae_lo_de_la_tabla(published):
    found = market_history(published, MarketChoice("1", DEPARTMENT), "papa", 4)
    row = published.market_month.filter((pl.col("crop_id") == "papa") & (pl.col("market_id") == "1") & (pl.col("month") == 4)).row(
        0, named=True
    )
    history = found.history
    assert (history.seasonal_index, history.years, history.years_above, history.years_below) == (
        row["seasonal_index"],
        row["years"],
        row["years_above"],
        row["years_below"],
    )
    assert (history.market, history.product_id, history.source_id) == ("Corabastos (Bogotá)", "papa-negra", "dane_sipsa")
    assert found.product_name == "Papa negra"


def test_la_misma_consulta_da_la_misma_senal(published):
    """R4."""
    first = market_in(published, published.municipalities["15001"], "papa", "la papa", 12)
    assert first.reasons[0] == UNRATED_REASON
    assert all(market_in(published, published.municipalities["15001"], "papa", "la papa", 12) == first for _ in range(3))
