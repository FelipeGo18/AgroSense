"""La necesidad de agua (ETc, FAO-56) y la lluvia de una ventana, prorrateadas por día (HU-078; base de HU-144).

Las cifras de lluvia y ET0 son de ejemplo (R5); el Kc es el de la papa en FAO-56 (tabla 12, `catalog/crops.yaml`).
"""

from datetime import date

import pytest

from backend.engine.stages import StageSpan, crop_window
from backend.engine.water_need import daily_kc, window_deficit_mm, window_etc_mm, window_rain_mm

PAPA = [
    StageSpan("initial", 45, kc=0.5),
    StageSpan("development", 30, kc=None),
    StageSpan("mid", 70, kc=1.15),
    StageSpan("late", 20, kc=0.75),
]
# Σ Kc a mano: inicial 45 × 0,5 = 22,5; desarrollo Σ(0,5 + 0,65 j/30), j = 1..30 = 15 + 0,65 × 465/30 = 25,075;
# media 70 × 1,15 = 80,5; final Σ(1,15 − 0,4 j/20), j = 1..20 = 23 − 0,4 × 210/20 = 18,8. Total: 146,875.
PAPA_KC_SUM = 146.875


def test_la_curva_de_kc_es_la_de_fao56():
    kc = daily_kc(PAPA)
    assert len(kc) == 165
    assert kc[0] == kc[44] == 0.5
    # El desarrollo sube en línea recta y su último día llega al Kc de la media (ecuación 66).
    assert kc[45] == pytest.approx(0.5 + 0.65 / 30) and kc[74] == pytest.approx(1.15)
    assert kc[75] == kc[144] == 1.15
    # La final baja en línea recta hasta el Kc final.
    assert kc[145] == pytest.approx(1.15 - 0.4 / 20) and kc[164] == pytest.approx(0.75)
    assert sum(kc) == pytest.approx(PAPA_KC_SUM)


def test_sin_etapa_final_la_curva_termina_en_la_media():
    haba = [StageSpan("initial", 90, kc=0.5), StageSpan("development", 45), StageSpan("mid", 40, kc=1.15)]
    kc = daily_kc(haba)
    assert len(kc) == 175 and kc[-1] == 1.15


@pytest.mark.parametrize(
    "stages",
    [
        # Sin el Kc de la inicial, el desarrollo no tiene de dónde subir.
        [StageSpan("initial", 10), StageSpan("development", 10), StageSpan("mid", 10, kc=1.1)],
        # Sin el Kc de la media, el desarrollo no tiene a dónde llegar.
        [StageSpan("initial", 10, kc=0.5), StageSpan("development", 10), StageSpan("mid", 10)],
        # Sin el Kc final, la etapa final no tiene a dónde bajar.
        [StageSpan("initial", 10, kc=0.5), StageSpan("mid", 10, kc=1.1), StageSpan("late", 10)],
        # El desarrollo no sube hacia el Kc final: ese es el del final del ciclo, no el de la media.
        [StageSpan("initial", 10, kc=0.5), StageSpan("development", 10), StageSpan("late", 10, kc=0.7)],
    ],
)
def test_sin_kc_con_fuente_no_hay_curva(stages):
    assert daily_kc(stages) is None


def test_lluvia_y_necesidad_se_prorratean_igual_por_dia():
    # Papa sembrada el 2 de agosto: agosto 30 días, septiembre 30, octubre 31, noviembre 30, diciembre 31 y enero 13.
    window = crop_window(PAPA, date(2027, 8, 2))
    keys = [(2027, 8), (2027, 9), (2027, 10), (2027, 11), (2027, 12), (2028, 1)]
    month_days = {(2027, 8): 31, (2027, 9): 30, (2027, 10): 31, (2027, 11): 30, (2027, 12): 31, (2028, 1): 31}
    # Un total mensual de 2 mm y 3 mm por día: la ventana suma 2 × 165 de lluvia y 3 × Σ Kc de necesidad.
    rain = {key: 2.0 * month_days[key] for key in keys}
    et0 = {key: 3.0 * month_days[key] for key in keys}
    assert window_rain_mm(window, rain) == pytest.approx(330.0)
    assert window_etc_mm(window, et0) == pytest.approx(3 * PAPA_KC_SUM)


def test_un_mes_tocado_en_parte_aporta_la_fraccion_de_sus_dias():
    # Una etapa de 20 días con Kc 1, del 22 de enero al 10 de febrero de 2027: 10 días de enero y 10 de febrero.
    window = crop_window([StageSpan("mid", 20, kc=1.0)], date(2027, 1, 22))
    rain = {(2027, 1): 62.0, (2027, 2): 56.0}
    et0 = {(2027, 1): 93.0, (2027, 2): 84.0}
    # 62 × 10/31 + 56 × 10/28 = 20 + 20; 93/31 × 10 + 84/28 × 10 = 30 + 30.
    assert window_rain_mm(window, rain) == pytest.approx(40.0)
    assert window_etc_mm(window, et0) == pytest.approx(60.0)


def test_los_totales_de_otro_anio_se_reparten_entre_los_dias_de_su_mes():
    # La ventana es de 2027 (febrero de 28 días), pero los totales son de febrero de 2016, que tuvo 29: la lluvia y la
    # ET0 por día salen de 29 días, y la ventana suma sus 10 días de febrero.
    window = crop_window([StageSpan("mid", 20, kc=1.0)], date(2027, 1, 22))
    days = {(2027, 1): 31, (2027, 2): 29}
    totals = {(2027, 1): 62.0, (2027, 2): 58.0}
    assert window_rain_mm(window, totals, days) == pytest.approx(20 + 20)
    assert window_etc_mm(window, totals, days) == pytest.approx(20 + 20)


def test_un_febrero_bisiesto_sobre_uno_de_28_dias_nunca_pasa_de_su_total():
    # Ventana de 2028 con febrero entero (29 días) y totales de un febrero de 28: el 29 no existe en el mes histórico,
    # así que la fracción es 28/28, no 29/28. La ETc deja fuera el Kc de ese día (aquí 2, para que se note).
    window = crop_window([StageSpan("mid", 28, kc=1.0), StageSpan("late", 1, kc=2.0)], date(2028, 2, 1))
    days = {(2028, 2): 28}
    totals = {(2028, 2): 56.0}
    assert window_rain_mm(window, totals, days) == pytest.approx(56.0)
    assert window_etc_mm(window, totals, days) == pytest.approx(56.0)
    # Con los días del calendario de la ventana (29), el 29 sí cuenta.
    assert window_rain_mm(window, {(2028, 2): 58.0}) == pytest.approx(58.0)


def test_una_siembra_el_29_de_febrero_sobre_un_febrero_de_28_empieza_en_marzo():
    window = crop_window([StageSpan("mid", 3, kc=1.0)], date(2028, 2, 29))
    days = {(2028, 2): 28, (2028, 3): 31}
    totals = {(2028, 2): 280.0, (2028, 3): 31.0}
    # Febrero no aporta (su único día, el 29, no existe en el mes histórico); marzo aporta 2 días de 31.
    assert window_rain_mm(window, totals, days) == pytest.approx(2.0)
    assert window_etc_mm(window, totals, days) == pytest.approx(2.0)


def test_sin_un_mes_no_hay_total_nunca_cero():
    window = crop_window(PAPA, date(2027, 8, 2))
    full = {(2027, m): 100.0 for m in range(8, 13)} | {(2028, 1): 100.0}
    for missing in (None, "falta"):
        partial = dict(full)
        if missing is None:
            partial[(2027, 10)] = None
        else:
            del partial[(2027, 10)]
        assert window_rain_mm(window, partial) is None
        assert window_etc_mm(window, partial) is None


def test_sin_kc_no_hay_necesidad():
    window = crop_window([StageSpan("initial", 10), StageSpan("mid", 10, kc=1.0)], date(2027, 3, 1))
    assert window_etc_mm(window, {(2027, 3): 100.0}) is None


def test_mismos_datos_mismo_resultado():
    window = crop_window(PAPA, date(2027, 8, 2))
    et0 = {(2027, m): 90.0 + m for m in range(8, 13)} | {(2028, 1): 95.0}
    assert window_etc_mm(window, et0) == window_etc_mm(window, dict(reversed(list(et0.items()))))


# ---------- el déficit mes a mes, sin el agua guardada (HU-071, hasta el balance de HU-144) ----------


def test_sin_lluvia_el_deficit_es_toda_la_necesidad():
    window = crop_window(PAPA, date(2027, 8, 2))
    keys = [(2027, m) for m in range(8, 13)] + [(2028, 1)]
    et0 = {key: 90.0 for key in keys}
    rain = {key: 0.0 for key in keys}
    assert window_deficit_mm(window, rain, et0) == pytest.approx(window_etc_mm(window, et0))


def test_con_lluvia_de_sobra_no_hay_deficit():
    window = crop_window(PAPA, date(2027, 8, 2))
    keys = [(2027, m) for m in range(8, 13)] + [(2028, 1)]
    assert window_deficit_mm(window, {key: 500.0 for key in keys}, {key: 90.0 for key in keys}) == 0.0


def test_lo_que_sobra_un_mes_no_tapa_lo_que_falta_en_otro():
    """Sin el agua guardada, un mes lluvioso no compensa uno seco: el déficit es el de los meses secos, aunque la lluvia
    de toda la ventana alcance para la necesidad de toda la ventana."""
    window = crop_window([StageSpan("initial", 31, kc=1.0), StageSpan("mid", 30, kc=1.0)], date(2027, 3, 1))
    et0 = {(2027, 3): 100.0, (2027, 4): 100.0}
    rain = {(2027, 3): 200.0, (2027, 4): 0.0}
    assert window_rain_mm(window, rain) >= window_etc_mm(window, et0)
    assert window_deficit_mm(window, rain, et0) == pytest.approx(100.0)


def test_sin_un_mes_de_lluvia_o_de_et0_no_hay_deficit():
    window = crop_window(PAPA, date(2027, 8, 2))
    full = {(2027, m): 100.0 for m in range(8, 13)} | {(2028, 1): 100.0}
    partial = full | {(2027, 10): None}
    assert window_deficit_mm(window, partial, full) is None
    assert window_deficit_mm(window, full, partial) is None
    no_kc = crop_window([StageSpan("initial", 10), StageSpan("mid", 10, kc=1.0)], date(2027, 3, 1))
    assert window_deficit_mm(no_kc, {(2027, 3): 0.0}, {(2027, 3): 100.0}) is None
