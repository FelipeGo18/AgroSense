"""Los números, las listas y los meses en texto de `common/text.py` y `common/months.py` (HU-077): los comparten la razón de
la aptitud, la de heladas y los boletines de SIPSA, sin importarse (R6)."""

import pytest

from common.months import MONTH_NAMES, month_name
from common.text import format_decimal, format_number, join, of


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (30, "30"),
        (30.0, "30"),
        (0, "0"),
        (22.4, "22,4"),
        (22.45, "22,4"),
        (29.96, "30,0"),
        (-3.5, "-3,5"),
    ],
)
def test_format_number_sin_decimales_si_es_entero_y_con_coma_si_no(value, expected):
    assert format_number(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(5, "5,0"), (5.0, "5,0"), (5.75, "5,8"), (4.13, "4,1"), (7.88, "7,9")])
def test_format_decimal_siempre_con_un_decimal_y_coma(value, expected):
    """El pH de la señal de suelo (HU-183) y del descarte `soil_ph` de las estrategias."""
    assert format_decimal(value) == expected


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        (["a"], "a"),
        (["a", "b"], "a y b"),
        (["a", "b", "c"], "a, b y c"),
        (iter(["a", "b", "c", "d"]), "a, b, c y d"),
    ],
)
def test_join_une_con_comas_y_una_y_al_final(items, expected):
    assert join(items) == expected


def test_los_meses_estan_en_orden_y_en_minuscula():
    assert len(MONTH_NAMES) == 12
    assert MONTH_NAMES[0] == "enero"
    assert MONTH_NAMES[-1] == "diciembre"
    assert all(name == name.lower() for name in MONTH_NAMES)


@pytest.mark.parametrize(("month", "expected"), [(1, "enero"), (9, "septiembre"), (12, "diciembre")])
def test_month_name_cuenta_desde_uno(month, expected):
    assert month_name(month) == expected


@pytest.mark.parametrize(
    ("name", "expected"), [("la papa", "de la papa"), ("el maíz", "del maíz"), ("la cebolla de bulbo", "de la cebolla de bulbo")]
)
def test_of_contrae_de_el_en_del(name, expected):
    assert of(name) == expected
