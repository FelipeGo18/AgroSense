"""Los datos de la señal de mercado (HU-073): qué central le toca a cada municipio y el índice estacional del mes de
cosecha, leídos del dataset publicado (`data/published/`, el de la demo) y del de ejemplo de las pruebas."""

from dataclasses import replace

import pytest

from backend.api.market_signal import crop_market, market_for, price_history, seasonal_index
from backend.dataset import load
from pipeline.build import PUBLISHED


@pytest.fixture(scope="module")
def published():
    """El dataset real publicado, con `market_month` y el mapa departamento → central del manifiesto."""
    return load(PUBLISHED)


def municipality_of(dataset, department_id):
    return next(m for m in dataset.municipalities.values() if m.department_id == department_id)


def test_market_month_se_carga_del_dataset_publicado(published):
    assert published.market_month is not None
    assert {"crop_id", "market_id", "month", "seasonal_index", "years"} <= set(published.market_month.columns)


def test_sin_market_month_publicado_queda_nulo_y_lo_demas_carga(dataset):
    """El dataset de ejemplo no publica precios: `market_month` es nulo (R1) y el resto se lee igual."""
    loaded = load(dataset)
    assert loaded.market_month is None
    assert loaded.municipalities


def test_el_manifiesto_trae_el_mapa_de_departamentos_a_centrales(published):
    assert published.region["department_markets"] == {"15": "9", "25": "1"}


def test_boyaca_vende_en_tunja_y_cundinamarca_en_corabastos(published):
    assert market_for(published, published.municipalities["15001"]) == "9"
    assert market_for(published, municipality_of(published, "25")) == "1"


def test_un_departamento_fuera_del_mapa_no_tiene_central(published):
    """Nunca se usa otra central por defecto (R1)."""
    outside = replace(published.municipalities["15001"], department_id="05")
    assert market_for(published, outside) is None


def test_una_region_sin_mapa_no_tiene_central(published):
    without_map = replace(published, region={k: v for k, v in published.region.items() if k != "department_markets"})
    assert market_for(without_map, published.municipalities["15001"]) is None


def test_papa_en_tunja_no_tiene_indice(published):
    """SIPSA no publica la papa negra en Tunja con 3 años completos: `market_month` no tiene esas filas (R1)."""
    market = market_for(published, published.municipalities["15001"])
    assert all(seasonal_index(published, "papa", market, month) == (None, None) for month in range(1, 13))


def test_papa_en_corabastos_trae_el_indice_y_los_anos_publicados(published):
    market = market_for(published, municipality_of(published, "25"))
    expected = (
        published.market_month.filter(
            (published.market_month["crop_id"] == "papa")
            & (published.market_month["market_id"] == "1")
            & (published.market_month["month"] == 4)
        )
        .select("seasonal_index", "years")
        .row(0)
    )
    assert seasonal_index(published, "papa", market, 4) == expected
    index, years = seasonal_index(published, "papa", market, 4)
    assert isinstance(index, float) and isinstance(years, int) and years >= 3


@pytest.mark.parametrize("crop_id", ["haba", "maiz"])
def test_un_cultivo_sin_producto_en_sipsa_no_tiene_indice(published, crop_id):
    assert seasonal_index(published, crop_id, "1", 4) == (None, None)


def test_sin_central_o_sin_market_month_no_hay_indice(published):
    assert seasonal_index(published, "papa", None, 4) == (None, None)
    assert seasonal_index(replace(published, market_month=None), "papa", "1", 4) == (None, None)


# ---------- La central por cultivo y la historia del precio (HU-073, decisión 17) ----------

OVERRIDES = {"15": {"papa": {"market_id": "1", "reason": "Tunja no publica papa negra desde el 27 de julio de 2021"}}}


def with_overrides(dataset):
    return replace(dataset, region={**dataset.region, "crop_market_overrides": OVERRIDES})


def test_la_papa_de_boyaca_va_a_corabastos_solo_con_la_central_por_cultivo(published):
    boyaca = published.municipalities["15001"]
    without = replace(published, region={k: v for k, v in published.region.items() if k != "crop_market_overrides"})
    assert crop_market(without, boyaca, "papa") is None
    assert crop_market(with_overrides(published), boyaca, "papa") == ("1", "crop_override", OVERRIDES["15"]["papa"]["reason"])


def test_la_arveja_de_boyaca_va_a_tunja(published):
    assert crop_market(with_overrides(published), published.municipalities["15001"], "arveja") == ("9", "department", None)


def test_la_historia_del_precio_sale_de_market_month(published):
    history = price_history(with_overrides(published), published.municipalities["15001"], "papa", published.crops["papa"], 9)
    assert (history.market_id, history.market, history.market_basis, history.product_id) == (
        "1", "Corabastos (Bogotá)", "crop_override", "papa-negra"
    )  # fmt: skip
    assert history.seasonal_index == pytest.approx(0.774)
    assert history.product_name == "la papa negra"
    if "years_above" in published.market_month.columns:
        assert (history.years_above, history.years_below, history.years) == (0, 5, 5)
    else:
        # El dataset publicado es anterior a HU-073: los años contados llegan nulos y el motor no los inventa (R1).
        assert (history.years_above, history.years_below) == (None, None)


def test_sin_central_no_hay_historia(published):
    outside = replace(published.municipalities["15001"], department_id="05")
    assert price_history(published, outside, "papa", published.crops["papa"], 9) is None
    assert price_history(published, published.municipalities["15001"], "haba", published.crops["haba"], 9) is None
