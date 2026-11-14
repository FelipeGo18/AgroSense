"""La aritmética de meses de `common/dates.py` (HU-192): la comparten la API (fechas de siembra aceptadas) y el motor
(ventanas por mes y meses de una ventana), sin importarse (R6)."""

import pytest

from common.dates import add_months


@pytest.mark.parametrize(
    ("year", "month", "offset", "expected"),
    [
        (2026, 11, 0, (2026, 11)),
        (2026, 11, 1, (2026, 12)),
        (2026, 12, 1, (2027, 1)),
        (2026, 11, 13, (2027, 12)),
        (2026, 1, 24, (2028, 1)),
        (2026, 1, -1, (2025, 12)),
        (2026, 3, -14, (2025, 1)),
    ],
)
def test_avanza_meses_cruzando_el_ano_en_los_dos_sentidos(year, month, offset, expected):
    assert add_months(year, month, offset) == expected


def test_el_mes_siempre_queda_entre_1_y_12():
    assert {add_months(2026, 1, offset)[1] for offset in range(-30, 30)} == set(range(1, 13))
