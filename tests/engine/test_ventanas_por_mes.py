"""Las ventanas de los próximos doce meses, una por mes de siembra (HU-192; specs/01-reglas.md, «La ventana de siembra»).

La fecha desde la que se cuentan los meses entra como parámetro: el motor no lee el reloj (R4, R6). Cada mes se calcula
desde esa fecha, no encadenado desde el mes anterior: el 31 de enero da el 28 (o 29) de febrero y vuelve al 31 en
marzo.
"""

from datetime import date

import pytest

from backend.engine.stages import StageSpan, crop_window, monthly_sowing_windows

# Papa: FAO-56, fila «Idaho, USA» (catalog/crops.yaml): 165 días.
PAPA = [
    StageSpan("initial", 45, kc=0.5, frost_sensitive=True),
    StageSpan("development", 30, frost_sensitive=True),
    StageSpan("mid", 70, kc=1.15, frost_sensitive=True),
    StageSpan("late", 20, kc=0.75, frost_sensitive=True),
]
START = date(2026, 11, 14)


def test_doce_ventanas_en_orden_con_meses_seguidos_que_cruzan_el_ano():
    windows = monthly_sowing_windows(PAPA, START)
    assert isinstance(windows, tuple)
    assert [w.sowing_date for w in windows] == [
        date(2026, 11, 14),
        date(2026, 12, 14),
        date(2027, 1, 14),
        date(2027, 2, 14),
        date(2027, 3, 14),
        date(2027, 4, 14),
        date(2027, 5, 14),
        date(2027, 6, 14),
        date(2027, 7, 14),
        date(2027, 8, 14),
        date(2027, 9, 14),
        date(2027, 10, 14),
    ]


def test_cada_ventana_es_la_de_crop_window_para_esa_fecha():
    for window in monthly_sowing_windows(PAPA, START):
        expected = crop_window(PAPA, window.sowing_date)
        assert window == expected
        assert window.harvest_estimate == expected.harvest_estimate


def test_el_31_de_enero_da_el_29_de_febrero_en_ano_bisiesto_y_vuelve_al_31():
    windows = monthly_sowing_windows(PAPA, date(2028, 1, 31))
    assert [w.sowing_date for w in windows] == [
        date(2028, 1, 31),
        date(2028, 2, 29),
        date(2028, 3, 31),
        date(2028, 4, 30),
        date(2028, 5, 31),
        date(2028, 6, 30),
        date(2028, 7, 31),
        date(2028, 8, 31),
        date(2028, 9, 30),
        date(2028, 10, 31),
        date(2028, 11, 30),
        date(2028, 12, 31),
    ]


def test_el_31_de_enero_da_el_28_de_febrero_en_ano_no_bisiesto():
    windows = monthly_sowing_windows(PAPA, date(2027, 1, 31), months=4)
    assert [w.sowing_date for w in windows] == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
    ]


def test_el_fin_de_mes_que_cruza_el_ano_se_ajusta_al_mes():
    windows = monthly_sowing_windows(PAPA, date(2026, 12, 31), months=3)
    assert [w.sowing_date for w in windows] == [date(2026, 12, 31), date(2027, 1, 31), date(2027, 2, 28)]


@pytest.mark.parametrize("months", [1, 3, 24])
def test_el_numero_de_meses_es_un_parametro(months):
    windows = monthly_sowing_windows(PAPA, START, months=months)
    assert len(windows) == months
    assert windows[0].sowing_date == START


def test_veinticuatro_meses_terminan_dos_anos_despues():
    assert monthly_sowing_windows(PAPA, START, months=24)[-1].sowing_date == date(2028, 10, 14)


def test_sin_etapas_no_hay_ventanas():
    assert monthly_sowing_windows([], START) == ()


def test_una_etapa_sin_dias_no_da_ventanas():
    assert monthly_sowing_windows([StageSpan("initial", 0), StageSpan("mid", 30)], START) == ()


def test_mismos_datos_mismas_ventanas():
    assert monthly_sowing_windows(PAPA, START) == monthly_sowing_windows(PAPA, START)
