"""`months_phrase` de la razón de las señales por etapas sensibles (HU-077): meses seguidos, meses salteados y meses que
repetirían un nombre por estar a doce meses o más del primero (R5)."""

from backend.engine.sensitive_signal import months_phrase
from backend.engine.stages import WindowMonth


def month(year: int, number: int) -> WindowMonth:
    return WindowMonth(year=year, month=number, days=30, stages=(), periods=())


def test_un_solo_mes_dice_su_nombre():
    assert months_phrase([month(2026, 12)]) == "diciembre"


def test_meses_seguidos_dicen_de_a():
    assert months_phrase([month(2026, 11), month(2026, 12), month(2027, 1)]) == "de noviembre a enero"


def test_meses_no_seguidos_se_enumeran():
    assert months_phrase([month(2026, 10), month(2026, 12)]) == "octubre y diciembre"


def test_un_mes_a_doce_meses_del_primero_dice_del_ano_siguiente():
    assert months_phrase([month(2026, 8), month(2026, 9), month(2027, 8)]) == "agosto, septiembre y agosto del año siguiente"


def test_un_mes_a_dos_anos_del_primero_dice_de_dos_anos_despues():
    assert months_phrase([month(2026, 8), month(2028, 9)]) == "agosto y septiembre de dos años después"
