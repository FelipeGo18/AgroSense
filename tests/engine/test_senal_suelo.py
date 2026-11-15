"""Señal de suelo (HU-183; specs/01-reglas.md, «Señales de una ventana» y «Cómo se califica cada señal», R1, R10).
Escritas antes del código (HU-121).

Los umbrales y el rango de pH de la papa son los reales (`thresholds.yaml`; `catalog/crops.yaml`: tolera de 4,2 a 8,5 y
su óptimo va de 5,0 a 6,2, FAO EcoCrop). Los pH del suelo son DE PRUEBA (R5), no de ningún municipio.

- La calificación es la curva de HU-196 sobre el pH estimado (`ph` de `soil_municipality`, la mediana de las celdas) y
  el nivel sale de ella (70 y 40 de `thresholds.yaml`).
- Con el intervalo `ph_p05`–`ph_p95`: si todo queda fuera del tolerado, el nivel es `unfavorable`; si solo cruza un
  límite, la razón lo dice y el nivel sigue siendo el de la curva (decisión del 14 nov 2026). Tocar un borde no cuenta,
  igual que en las estrategias (`backend/engine/rotations/exclusions.py`).
- Nunca crítica (R10).
"""

import math

import pytest

from backend.config.thresholds import load_thresholds
from backend.engine.sensitive_signal import no_stages_reason
from backend.engine.signal_score import AVAILABLE, FAVORABLE, INSUFFICIENT_DATA, MODERATE, UNFAVORABLE, SignalScore
from backend.engine.soil_signal import (
    ESTIMATE_LABEL,
    NO_SOIL_REASON,
    ZoneSoilPh,
    crosses_tolerated,
    outside_tolerated,
    soil_signal,
    soil_without_stages,
)
from backend.engine.traffic_light import traffic_light
from common.text import format_decimal

CROP = "la papa"
PAPA = {"ph_min": 4.2, "ph_opt_min": 5.0, "ph_opt_max": 6.2, "ph_max": 8.5}


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


def signal(thresholds, ph, p05=None, p95=None, limits=PAPA):
    return soil_signal(ZoneSoilPh(ph, p05, p95), limits, thresholds, CROP)


def state(result):
    return (result.status, result.score, result.level, result.critical)


# ---------- la curva de HU-196 ----------


def test_en_el_optimo_da_100_y_favorable(thresholds):
    result = signal(thresholds, 5.7, 5.2, 6.1)
    assert state(result) == (AVAILABLE, 100, FAVORABLE, False)
    assert result.indicators == ("ph",)
    assert result.reasons == (
        "pH estimado de 5,7 (de 5,2 a 6,1), dentro del óptimo de la papa (5,0 a 6,2). "
        "Todo ese rango está dentro de lo que tolera (4,2 a 8,5). " + ESTIMATE_LABEL,
    )
    assert result.limitations == ()


def test_entre_el_optimo_y_el_tolerado_va_en_linea_recta(thresholds):
    """Del lado ácido: 100 · (4,6 − 4,2) / (5,0 − 4,2) = 50. Del alcalino: 100 · (8,5 − 7,35) / (8,5 − 6,2) = 50."""
    acid = signal(thresholds, 4.6, 4.4, 4.8)
    assert state(acid) == (AVAILABLE, 50, MODERATE, False)
    assert acid.reasons[0].startswith("pH estimado de 4,6 (de 4,4 a 4,8), más ácido que el óptimo de la papa (5,0 a 6,2). ")
    alkaline = signal(thresholds, 7.35, 7.0, 7.7)
    assert state(alkaline) == (AVAILABLE, 50, MODERATE, False)
    assert alkaline.reasons[0].startswith("pH estimado de 7,3 (de 7,0 a 7,7), más alcalino que el óptimo de la papa (5,0 a 6,2). ")
    # 100 · (4,8 − 4,2) / 0,8 = 75: favorable aunque no esté en el óptimo.
    assert state(signal(thresholds, 4.8, 4.6, 5.0)) == (AVAILABLE, 75, FAVORABLE, False)


def test_fuera_del_tolerado_da_0_y_desfavorable(thresholds):
    result = signal(thresholds, 4.0, 3.6, 4.1)
    assert state(result) == (AVAILABLE, 0, UNFAVORABLE, False)
    assert result.reasons == (
        "pH estimado de 4,0 (de 3,6 a 4,1), más ácido de lo que tolera la papa (4,2 a 8,5). "
        "Todo ese rango queda fuera de lo que tolera (4,2 a 8,5). " + ESTIMATE_LABEL,
    )
    assert state(signal(thresholds, 9.0, 8.7, 9.3)) == (AVAILABLE, 0, UNFAVORABLE, False)
    assert signal(thresholds, 9.0, 8.7, 9.3).reasons[0].startswith("pH estimado de 9,0 (de 8,7 a 9,3), más alcalino de lo que tolera")


# ---------- el intervalo p05–p95 ----------


def test_un_intervalo_que_cruza_un_limite_se_dice_pero_no_cambia_el_nivel(thresholds):
    """La mediana en el óptimo da 100 y `favorable`; el intervalo del mapa llega más allá de lo que tolera la papa: la
    razón lo dice, pero el nivel lo da el pH estimado (decisión del 14 nov 2026)."""
    result = signal(thresholds, 5.7, 4.1, 7.9)
    assert state(result) == (AVAILABLE, 100, FAVORABLE, False)
    assert result.reasons == (
        "pH estimado de 5,7 (de 4,1 a 7,9), dentro del óptimo de la papa (5,0 a 6,2). "
        "Es un rango amplio y parte de él queda fuera de lo que tolera (4,2 a 8,5). " + ESTIMATE_LABEL,
    )
    # Del lado alcalino también.
    assert state(signal(thresholds, 6.0, 5.5, 8.8)) == (AVAILABLE, 100, FAVORABLE, False)


def test_cruzar_un_limite_tampoco_cambia_un_nivel_bajo(thresholds):
    """Con la mediana en 4,4 (25, desfavorable) el intervalo que cruza no la mueve: sigue desfavorable."""
    result = signal(thresholds, 4.4, 3.9, 5.0)
    assert state(result) == (AVAILABLE, 25, UNFAVORABLE, False)
    assert "Es un rango amplio y parte de él queda fuera de lo que tolera (4,2 a 8,5). " in result.reasons[0]


def test_todo_el_intervalo_fuera_del_tolerado_es_desfavorable_aunque_la_curva_diga_otra_cosa(thresholds):
    """Un dato incoherente (la mediana fuera de su propio intervalo) no rescata el nivel: manda el intervalo."""
    result = signal(thresholds, 5.7, 3.5, 4.1)
    assert state(result) == (AVAILABLE, 100, UNFAVORABLE, False)
    assert "Todo ese rango queda fuera de lo que tolera (4,2 a 8,5)" in result.reasons[0]


def test_tocar_un_borde_del_tolerado_no_es_quedar_fuera(thresholds):
    """Igual que en las estrategias: `ph_max < p05` o `ph_min > p95` es estar todo fuera; un borde compartido no cuenta.
    Cruzar es que una parte del intervalo quede fuera y otra no: un intervalo que llega justo al borde desde adentro no
    cruza, y uno que llega desde afuera sí (solo el borde queda adentro)."""
    assert state(signal(thresholds, 5.7, 4.2, 8.5)) == (AVAILABLE, 100, FAVORABLE, False)
    # p95 justo en ph_min: no está todo fuera, pero cruza; la mediana (4,2) da 0 por la curva.
    assert state(signal(thresholds, 4.2, 3.9, 4.2)) == (AVAILABLE, 0, UNFAVORABLE, False)
    assert "Todo ese rango queda fuera" not in signal(thresholds, 4.2, 3.9, 4.2).reasons[0]
    assert "Es un rango amplio y parte de él queda fuera" in signal(thresholds, 4.2, 3.9, 4.2).reasons[0]


@pytest.mark.parametrize(
    ("p05", "p95", "outside", "crosses"),
    [
        (5.2, 6.1, False, False),
        (4.2, 8.5, False, False),  # los dos bordes, justos
        (4.1, 7.9, False, True),
        (5.0, 8.6, False, True),
        (4.0, 9.0, False, True),  # cruza los dos
        (3.6, 4.1, True, False),
        (3.6, 4.2, False, True),  # p95 en ph_min: no está todo fuera, pero casi todo sí
        (8.5, 9.0, False, True),  # p05 en ph_max: igual, del lado alcalino
        (4.2, 6.0, False, False),  # p05 en ph_min, desde adentro: nada queda fuera
        (8.6, 9.0, True, False),
    ],
)
def test_las_dos_lecturas_del_intervalo(p05, p95, outside, crosses):
    assert outside_tolerated(4.2, 8.5, p05, p95) is outside
    assert crosses_tolerated(4.2, 8.5, p05, p95) is crosses


# ---------- nunca crítica (R10) ----------


@pytest.mark.parametrize(("ph", "p05", "p95"), [(4.0, 3.6, 4.1), (9.5, 9.0, 9.9), (4.2, 3.9, 4.2), (5.7, 3.5, 4.1)])
def test_nunca_es_critica(thresholds, ph, p05, p95):
    assert signal(thresholds, ph, p05, p95).critical is False


def test_suelo_desfavorable_solo_no_da_rojo_y_con_otra_desfavorable_si(thresholds):
    """R2 y R10: el suelo nunca es crítico, así que solo da rojo junto con otra señal que cuente y sea desfavorable."""
    soil = signal(thresholds, 4.0, 3.6, 4.1)
    soil_score = SignalScore(soil.status, soil.score, soil.level, soil.critical)
    good = SignalScore(AVAILABLE, 100, FAVORABLE, False)
    bad = SignalScore(AVAILABLE, 20, UNFAVORABLE, False)
    weights = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
    alone = traffic_light("suitable", {"water": good, "frost": good, "heat": good, "soil": soil_score}, weights, "default")
    assert alone.light == "yellow"
    # El suelo no se arregla cambiando de fecha: la acción es rotar.
    assert alone.action == "rotate"
    with_other = traffic_light("suitable", {"water": good, "frost": good, "heat": bad, "soil": soil_score}, weights, "default")
    assert with_other.light == "red"


# ---------- sin datos (R1, R8) ----------


@pytest.mark.parametrize("soil", [None, ZoneSoilPh(None, 5.1, 5.9), ZoneSoilPh(math.nan, 5.1, 5.9)])
def test_sin_suelo_es_insufficient_data_y_va_a_las_limitaciones(thresholds, soil):
    result = soil_signal(soil, PAPA, thresholds, CROP)
    assert state(result) == (INSUFFICIENT_DATA, None, None, False)
    assert result.indicators == ()
    assert result.reasons == (NO_SOIL_REASON,)
    assert NO_SOIL_REASON in result.limitations


@pytest.mark.parametrize("missing", ["ph_min", "ph_opt_min", "ph_opt_max", "ph_max"])
def test_una_ficha_sin_rango_de_ph_con_fuente_es_insufficient_data(thresholds, missing):
    """El pipeline deja nulo todo valor sin fuente (R8), así que un límite nulo es un límite sin fuente; NaN, igual."""
    for value in (None, math.nan):
        result = signal(thresholds, 5.7, 5.2, 6.1, limits={**PAPA, missing: value})
        assert state(result) == (INSUFFICIENT_DATA, None, None, False)
        assert result.reasons == (
            "La ficha de la papa no trae con fuente su rango de pH (ph_min, ph_opt_min, ph_opt_max y ph_max): el suelo no se califica",
        )
        assert result.reasons[0] in result.limitations


def test_sin_etapas_no_hay_ventana_y_el_suelo_no_se_califica_con_la_razon_de_las_demas():
    """HU-076 (`docs/registro-de-decisiones.md`): sin etapas del cultivo no hay ventana y ninguna señal se califica. El
    suelo no cambia con la fecha, pero tampoco se califica, con la misma razón que las heladas y el calor."""
    result = soil_without_stages(CROP)
    assert state(result) == (INSUFFICIENT_DATA, None, None, False)
    assert result.reasons == (no_stages_reason(CROP),) == ("Sin las etapas de la papa: la señal no se evalúa",)
    assert result.limitations == result.reasons


@pytest.mark.parametrize(("p05", "p95"), [(None, None), (5.1, None), (None, 5.9), (math.nan, 5.9)])
def test_sin_el_intervalo_la_curva_califica_y_la_lectura_del_intervalo_va_a_las_limitaciones(thresholds, p05, p95):
    result = signal(thresholds, 5.7, p05, p95)
    assert state(result) == (AVAILABLE, 100, FAVORABLE, False)
    assert result.reasons == (
        "pH estimado de 5,7, dentro del óptimo de la papa (5,0 a 6,2). La papa tolera de 4,2 a 8,5. " + ESTIMATE_LABEL,
    )
    assert result.limitations == (
        "Sin el rango del pH estimado de la zona (percentiles 5 y 95): no se revisó si parte del suelo queda fuera de lo que "
        "tolera la papa",
    )


# ---------- la razón (R5, R10) ----------


def test_la_razon_dice_que_es_una_estimacion_de_250_m_y_pide_un_analisis_de_suelo_del_lote(thresholds):
    assert "250 m" in ESTIMATE_LABEL
    assert "análisis de suelo de su lote" in ESTIMATE_LABEL
    for ph, p05, p95 in [(5.7, 5.2, 6.1), (4.6, 4.4, 4.8), (4.0, 3.6, 4.1), (5.7, 4.1, 7.9), (5.7, None, None)]:
        reason = signal(thresholds, ph, p05, p95).reasons[0]
        assert reason.endswith(ESTIMATE_LABEL)
        assert format_decimal(ph) in reason


def test_dos_ejecuciones_iguales_dan_lo_mismo(thresholds):
    """R4."""
    assert signal(thresholds, 5.7, 4.1, 7.9) == signal(thresholds, 5.7, 4.1, 7.9)
