"""La curva EcoCrop de calificación (HU-196): 0 en los límites absolutos, 100 en el tramo óptimo, recta entre medio
(specs/01-reglas.md, «Cómo se califica cada señal»)."""

import pytest

from backend.engine.curve import crop_curve, score_from_curve

# Papa: UPRA, zonificación Diacol Capiro (catalog/crops.yaml): tmean_min_c 8, tmean_opt_min_c 12, tmean_opt_max_c 15,
# tmean_max_c 16.
PAPA_TMEAN = (8.0, 12.0, 15.0, 16.0)
PAPA_CURVE = crop_curve(*PAPA_TMEAN)

# Heladas (thresholds.yaml, señal `frost`): curva descendente derivada del ZARC de Brasil.
FROST_CURVE = [(0, 100), (20, 70), (40, 40), (100, 0)]


def test_crop_curve_devuelve_los_cuatro_puntos_de_la_papa():
    assert PAPA_CURVE == ((8.0, 0.0), (12.0, 100.0), (15.0, 100.0), (16.0, 0.0))


@pytest.mark.parametrize("value", [12.0, 13.5, 15.0])
def test_dentro_del_tramo_optimo_califica_100(value):
    assert score_from_curve(PAPA_CURVE, value) == 100.0


@pytest.mark.parametrize("value", [8.0, 16.0])
def test_en_los_limites_absolutos_exactos_califica_0(value):
    assert score_from_curve(PAPA_CURVE, value) == 0.0


def test_a_medio_camino_entre_el_absoluto_inferior_y_el_optimo_califica_50():
    assert score_from_curve(PAPA_CURVE, 10.0) == 50.0


def test_a_medio_camino_entre_el_optimo_y_el_absoluto_superior_califica_50():
    assert score_from_curve(PAPA_CURVE, 15.5) == 50.0


@pytest.mark.parametrize("value", [2.0, 25.0])
def test_fuera_de_los_extremos_clampa_a_0(value):
    assert score_from_curve(PAPA_CURVE, value) == 0.0


def test_una_curva_descendente_de_varios_puntos_interpola_bien():
    """La de heladas de thresholds.yaml: HU-196 la reusa para HU-189."""
    assert score_from_curve(FROST_CURVE, 10) == 85
    assert score_from_curve(FROST_CURVE, 30) == 55


def test_un_tramo_degenerado_con_valores_repetidos_no_divide_por_cero():
    curve = crop_curve(8, 8, 15, 16)
    assert score_from_curve(curve, 8) == 100.0


def test_una_curva_vacia_es_un_error():
    with pytest.raises(ValueError):
        score_from_curve([], 10.0)


def test_una_curva_desordenada_es_un_error():
    with pytest.raises(ValueError):
        score_from_curve([(10, 0), (5, 100)], 7.0)
