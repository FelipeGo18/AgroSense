"""Las ventanas de los próximos doce meses, una por mes de siembra (HU-192; specs/01-reglas.md, «La ventana de siembra»).

La fecha desde la que se cuentan los meses entra como parámetro: el motor no lee el reloj (R4, R6). Cada ventana empieza
el día 1 de su mes, desde el mes en curso de esa fecha, aunque su día 1 ya haya pasado (specs/02-contratos.md, «Fechas»).
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
        date(2026, 11, 1),
        date(2026, 12, 1),
        date(2027, 1, 1),
        date(2027, 2, 1),
        date(2027, 3, 1),
        date(2027, 4, 1),
        date(2027, 5, 1),
        date(2027, 6, 1),
        date(2027, 7, 1),
        date(2027, 8, 1),
        date(2027, 9, 1),
        date(2027, 10, 1),
    ]


@pytest.mark.parametrize("day", [1, 14, 30])
def test_el_mes_en_curso_empieza_el_dia_1_aunque_ya_haya_pasado(day):
    windows = monthly_sowing_windows(PAPA, date(2026, 11, day), months=2)
    assert [w.sowing_date for w in windows] == [date(2026, 11, 1), date(2026, 12, 1)]


def test_el_31_de_enero_empieza_en_el_1_de_enero_y_sigue_el_1_de_cada_mes():
    windows = monthly_sowing_windows(PAPA, date(2027, 1, 31), months=3)
    assert [w.sowing_date for w in windows] == [date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)]


def test_cada_ventana_es_la_de_crop_window_para_esa_fecha():
    for window in monthly_sowing_windows(PAPA, START):
        expected = crop_window(PAPA, window.sowing_date)
        assert window == expected
        assert window.harvest_estimate == expected.harvest_estimate


def test_la_ventana_de_un_mes_y_crop_window_con_el_dia_1_dan_las_mismas_etapas_y_meses():
    # Criterio de HU-192: la web pide el diagnóstico con el día 1 del mes, y el diagnóstico usa `crop_window`.
    for window in monthly_sowing_windows(PAPA, START):
        diagnosis = crop_window(PAPA, date(window.sowing_date.year, window.sowing_date.month, 1))
        assert window.periods == diagnosis.periods
        assert window.months() == diagnosis.months()
        assert window.harvest_estimate == diagnosis.harvest_estimate


@pytest.mark.parametrize("months", [1, 3, 24])
def test_el_numero_de_meses_es_un_parametro(months):
    windows = monthly_sowing_windows(PAPA, START, months=months)
    assert len(windows) == months
    assert windows[0].sowing_date == date(2026, 11, 1)


def test_veinticuatro_meses_terminan_dos_anos_despues():
    assert monthly_sowing_windows(PAPA, START, months=24)[-1].sowing_date == date(2028, 10, 1)


def test_sin_etapas_no_hay_ventanas():
    assert monthly_sowing_windows([], START) == ()


def test_una_etapa_sin_dias_no_da_ventanas():
    assert monthly_sowing_windows([StageSpan("initial", 0), StageSpan("mid", 30)], START) == ()


def test_mismos_datos_mismas_ventanas():
    assert monthly_sowing_windows(PAPA, START) == monthly_sowing_windows(PAPA, START)
