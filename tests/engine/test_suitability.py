"""Aptitud del cultivo en la zona (HU-191; specs/01-reglas.md, «Aptitud del cultivo en la zona»).

Es un filtro por temperatura media anual, no una señal (R3): solo fuera del rango absoluto es `not_suitable`. El
`score` es una nota informativa con la curva de HU-196 y nunca cambia el semáforo ni el orden de las ventanas.
"""

import pytest

from backend.engine.suitability import ABOVE_MAX, BELOW_MIN, INSUFFICIENT_DATA, NOT_SUITABLE, SUITABLE, Suitability, suitability

# Papa: UPRA, zonificación Diacol Capiro (catalog/crops.yaml): tmean_min_c 8, tmean_opt_min_c 12, tmean_opt_max_c 15,
# tmean_max_c 16.
PAPA = (8.0, 12.0, 15.0, 16.0)


def test_dentro_del_rango_optimo_es_apto_con_nota_100():
    assert suitability(*PAPA, 13.0) == Suitability(SUITABLE, 100.0)


def test_dentro_del_absoluto_bajo_el_optimo_es_apto_con_nota_intermedia():
    assert suitability(*PAPA, 10.0) == Suitability(SUITABLE, 50.0)


def test_dentro_del_absoluto_sobre_el_optimo_es_apto_con_nota_intermedia():
    assert suitability(*PAPA, 15.5) == Suitability(SUITABLE, 50.0)


@pytest.mark.parametrize("tmean_annual_c", [8.0, 16.0])
def test_en_el_limite_absoluto_exacto_es_apto_aunque_la_nota_sea_0(tmean_annual_c):
    """Criterio de aceptación de la HU: «Dentro del rango, incluidos los dos límites: suitable»."""
    assert suitability(*PAPA, tmean_annual_c) == Suitability(SUITABLE, 0.0)


@pytest.mark.parametrize("tmean_annual_c", [7.9, 24.0])
def test_por_debajo_o_por_encima_del_absoluto_no_es_apto(tmean_annual_c):
    """24 °C es el caso de referencia de la HU: un cultivo de clima frío en un municipio a nivel del mar."""
    assert suitability(*PAPA, tmean_annual_c).level == NOT_SUITABLE


def test_fuera_del_absoluto_la_nota_queda_en_0():
    result = suitability(*PAPA, 16.1)
    assert (result.level, result.score) == (NOT_SUITABLE, 0.0)


@pytest.mark.parametrize(
    "tmean_min_c,tmean_opt_min_c,tmean_opt_max_c,tmean_max_c",
    [
        (None, 12.0, 15.0, 16.0),
        (8.0, None, 15.0, 16.0),
        (8.0, 12.0, None, 16.0),
        (8.0, 12.0, 15.0, None),
    ],
)
def test_sin_alguno_de_los_cuatro_limites_de_la_ficha_queda_sin_datos(tmean_min_c, tmean_opt_min_c, tmean_opt_max_c, tmean_max_c):
    """R1, R8: ninguna excepción, no bloquea, se agrega a las limitaciones."""
    result = suitability(tmean_min_c, tmean_opt_min_c, tmean_opt_max_c, tmean_max_c, 13.0)
    assert result == Suitability(INSUFFICIENT_DATA, None)


def test_sin_la_temperatura_media_del_municipio_queda_sin_datos():
    assert suitability(*PAPA, None) == Suitability(INSUFFICIENT_DATA, None)


def test_mismos_datos_mismo_resultado():
    assert suitability(*PAPA, 13.0) == suitability(*PAPA, 13.0)


def test_la_aptitud_se_decide_solo_por_el_rango_absoluto_no_por_la_nota():
    """Una nota de 0 en el borde sigue siendo `suitable`: no es una señal (R3)."""
    result = suitability(*PAPA, 8.0)
    assert result.score == 0.0
    assert result.level == SUITABLE


# ---------- `exceeded`: qué límite se cruzó, para que quien arme el texto no repita la comparación (R6) ----------


def test_exceeded_es_nulo_cuando_es_apto():
    assert suitability(*PAPA, 13.0).exceeded is None


def test_exceeded_es_nulo_cuando_faltan_datos():
    assert suitability(None, 12.0, 15.0, 16.0, 13.0).exceeded is None


def test_exceeded_dice_min_por_debajo_del_absoluto():
    assert suitability(*PAPA, 7.9).exceeded == BELOW_MIN


def test_exceeded_dice_max_por_encima_del_absoluto():
    assert suitability(*PAPA, 16.1).exceeded == ABOVE_MAX
