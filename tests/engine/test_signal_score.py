"""Calificación de las señales con curvas por cultivo (HU-196; specs/01-reglas.md, «Cómo se califica cada señal»).

Cada señal se califica de 0 a 100 con la única curva del motor (`backend/engine/curve.py`): 100 en el óptimo, 0 en el
límite absoluto o fuera, recta entre medio. El nivel y el grado crítico salen de los umbrales ya validados (`Thresholds`,
HU-075): la forma de `thresholds.yaml` se prueba en tests/test_umbrales.py, no aquí. La prueba sí lee archivos (los
umbrales y el catálogo reales); el motor no (R6, cubierto en tests/engine/test_etapas.py).
"""

import copy
from dataclasses import replace

import pytest

from backend.config import thresholds as thresholds_config
from backend.config.thresholds import SignalThreshold, Thresholds, load_thresholds
from backend.engine import signal_score
from backend.engine.signal_score import (
    AVAILABLE,
    CROP_LIMITS,
    FAVORABLE,
    INSUFFICIENT_DATA,
    MODERATE,
    UNFAVORABLE,
    SignalScore,
    score_signal,
)
from pipeline import catalog

INSUFFICIENT = SignalScore(INSUFFICIENT_DATA, None, None, False)

HEAT_LIMITS = ("temp_opt_max_c", "heat_max_c")
SOIL_LIMITS = ("ph_min", "ph_opt_min", "ph_opt_max", "ph_max")


@pytest.fixture(scope="module")
def thresholds() -> Thresholds:
    """`thresholds.yaml` del repositorio, leído y validado por `load_thresholds` (el motor lo recibe así)."""
    return load_thresholds()


def with_signal(thresholds: Thresholds, signal: str, **changes) -> Thresholds:
    """Una copia de los umbrales con un campo de una señal cambiado (los originales no se tocan)."""
    changed: SignalThreshold = replace(thresholds.signals[signal], **changes)
    return replace(thresholds, signals={**thresholds.signals, signal: changed})


@pytest.fixture(scope="module")
def papa():
    """Los límites de la papa de catalog/crops.yaml, ya validados con fuente por el catálogo (R8)."""
    crops, _, _ = catalog.build(catalog.load())
    row = crops.filter(crops["crop_id"] == "papa").row(0, named=True)
    return {field: row[field] for field in HEAT_LIMITS + SOIL_LIMITS}


# ---------- Casos de referencia con los datos reales ----------


def test_los_limites_de_la_papa_son_los_esperados(papa):
    """Fija los números con que se escribieron los casos de abajo (FAO EcoCrop): si cambia la ficha, se revisan."""
    assert papa == {
        "temp_opt_max_c": 25,
        "heat_max_c": 30,
        "ph_min": 4.2,
        "ph_opt_min": 5.0,
        "ph_opt_max": 6.2,
        "ph_max": 8.5,
    }


def test_los_umbrales_son_los_esperados(thresholds):
    """Fija la versión de `thresholds.yaml` con que se escribieron los casos de abajo: si cambia, se revisan."""
    assert thresholds.version == "1.0.0"
    assert (thresholds.favorable, thresholds.moderate) == (70, 40)


# ---------- Sin desincronizarse de backend/config/thresholds.py ----------


def test_la_constante_crop_es_la_de_la_configuracion():
    """El motor no importa la configuración en tiempo de ejecución (R6): su constante tiene que valer lo mismo."""
    assert signal_score.FROM_CROP == thresholds_config.FROM_CROP


def test_las_senales_con_limites_de_la_ficha_son_las_de_la_configuracion():
    """Cada señal que la configuración permite con `curve: crop` tiene sus límites de la ficha, y ninguna más."""
    assert set(CROP_LIMITS) == thresholds_config.CROP_CURVES


# ---------- Dentro del óptimo: 100 ----------


@pytest.mark.parametrize("ph", [5.0, 5.6, 6.2])
def test_suelo_con_ph_dentro_del_optimo_de_la_papa_da_100(thresholds, papa, ph):
    assert score_signal("soil", ph, thresholds, papa) == SignalScore(AVAILABLE, 100.0, FAVORABLE, False)


@pytest.mark.parametrize("tmax", [20.0, 25.0])
def test_calor_en_o_bajo_el_optimo_de_la_papa_da_100(thresholds, papa, tmax):
    assert score_signal("heat", tmax, thresholds, papa) == SignalScore(AVAILABLE, 100.0, FAVORABLE, False)


def test_agua_con_la_necesidad_cubierta_da_100(thresholds):
    assert score_signal("water", 100.0, thresholds) == SignalScore(AVAILABLE, 100.0, FAVORABLE, False)


def test_heladas_que_nunca_ocurren_dan_100(thresholds):
    assert score_signal("frost", 0.0, thresholds) == SignalScore(AVAILABLE, 100.0, FAVORABLE, False)


# ---------- En el límite absoluto o fuera: 0 ----------


@pytest.mark.parametrize("ph", [4.2, 3.5, 8.5, 9.0])
def test_suelo_en_el_limite_absoluto_o_fuera_da_0_y_nunca_es_critico(thresholds, papa, ph):
    """R10: el suelo es una estimación de 250 m; aunque califique 0, no es crítico."""
    assert score_signal("soil", ph, thresholds, papa) == SignalScore(AVAILABLE, 0.0, UNFAVORABLE, False)


@pytest.mark.parametrize("tmax", [30.0, 34.0])
def test_calor_en_el_maximo_absoluto_o_encima_da_0_y_es_critico(thresholds, papa, tmax):
    """`critical_below: 1`: solo la calificación 0 es crítica (la máxima llega al máximo que aguanta el cultivo)."""
    assert score_signal("heat", tmax, thresholds, papa) == SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)


def test_agua_sin_lluvia_que_cubra_da_0_y_es_critica(thresholds):
    assert score_signal("water", 0.0, thresholds) == SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)


def test_heladas_todos_los_anos_dan_0_y_son_criticas(thresholds):
    assert score_signal("frost", 100.0, thresholds) == SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)


# ---------- Punto medio entre el óptimo y el límite: 50 ----------


@pytest.mark.parametrize("ph", [4.6, 7.35])
def test_suelo_en_el_punto_medio_entre_optimo_y_limite_da_50(thresholds, papa, ph):
    result = score_signal("soil", ph, thresholds, papa)
    assert result.status == AVAILABLE
    assert result.score == pytest.approx(50.0)
    assert (result.level, result.critical) == (MODERATE, False)


def test_calor_en_el_punto_medio_entre_optimo_y_maximo_da_50(thresholds, papa):
    assert score_signal("heat", 27.5, thresholds, papa) == SignalScore(AVAILABLE, 50.0, MODERATE, False)


# ---------- El calor tiene curva de 2 puntos: el frío no es calor ----------


@pytest.mark.parametrize("tmax", [-5.0, 0.0, 7.0, 15.0])
def test_calor_con_maxima_baja_da_100_no_0(thresholds, papa, tmax):
    """Sin límite inferior: una máxima fría (aun por debajo de `temp_min_c`) es 100 en calor, no 0."""
    assert score_signal("heat", tmax, thresholds, papa).score == 100.0


def test_calor_no_necesita_los_limites_de_frio_de_la_ficha(thresholds):
    """Solo pide `temp_opt_max_c` y `heat_max_c`: sin `temp_min_c` ni `temp_opt_min_c` califica igual."""
    limits = {"temp_opt_max_c": 25.0, "heat_max_c": 30.0}
    assert score_signal("heat", 27.5, thresholds, limits) == SignalScore(AVAILABLE, 50.0, MODERATE, False)


@pytest.mark.parametrize(
    "tmax,expected",
    [(24.0, SignalScore(AVAILABLE, 100.0, FAVORABLE, False))]
    + [(t, SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)) for t in (25.0, 26.0, 40.0)],
)
def test_calor_con_optimo_igual_al_maximo_es_un_escalon(thresholds, tmax, expected):
    """Ficha con `temp_opt_max_c == heat_max_c`: tramo vertical de curve.py, que da la calificación del último punto.
    Bajo el límite, 100; en el límite o encima, 0 y crítica. Fija el comportamiento actual."""
    limits = {"temp_opt_max_c": 25.0, "heat_max_c": 25.0}
    assert score_signal("heat", tmax, thresholds, limits) == expected


# ---------- Agua y heladas: la curva fija de thresholds.yaml, no la ficha ----------


@pytest.mark.parametrize(
    "value,score",
    [
        (0.0, 0.0),
        (50.0, 20.0),
        (55.0, 30.0),
        (60.0, 40.0),
        (70.0, 55.0),
        (80.0, 70.0),
        (90.0, 85.0),
        (100.0, 100.0),
        (130.0, 100.0),
    ],
)
def test_agua_sigue_los_puntos_de_thresholds(thresholds, value, score):
    assert score_signal("water", value, thresholds).score == pytest.approx(score)


@pytest.mark.parametrize(
    "value,score",
    [(0.0, 100.0), (10.0, 85.0), (20.0, 70.0), (30.0, 55.0), (40.0, 40.0), (70.0, 20.0), (100.0, 0.0)],
)
def test_heladas_siguen_los_puntos_de_thresholds(thresholds, value, score):
    assert score_signal("frost", value, thresholds).score == pytest.approx(score)


@pytest.mark.parametrize("signal,value", [("water", 70.0), ("frost", 30.0)])
def test_agua_y_heladas_ignoran_los_limites_de_la_ficha(thresholds, papa, signal, value):
    """Los límites de la ficha (ni los de la papa ni unos absurdos ni ninguno) no cambian una curva fija."""
    absurd = {field: 0.0 for field in papa}
    expected = score_signal(signal, value, thresholds)
    assert score_signal(signal, value, thresholds, papa) == expected
    assert score_signal(signal, value, thresholds, absurd) == expected
    assert score_signal(signal, value, thresholds, {}) == expected


def test_la_curva_fija_sale_de_la_configuracion_recibida(thresholds):
    """Si cambia la curva en los umbrales, cambia la calificación: el motor no tiene puntos propios."""
    changed = with_signal(thresholds, "water", curve=((0.0, 0.0), (100.0, 100.0)))
    assert score_signal("water", 55.0, changed).score == pytest.approx(55.0)
    assert score_signal("water", 55.0, thresholds).score == pytest.approx(30.0)


# ---------- Cortes de nivel: exactos, desde thresholds.yaml ----------


@pytest.mark.parametrize(
    "value,level",
    [
        (80.0, FAVORABLE),  # 70 exacto
        (79.0, MODERATE),  # 68,5 crudo, 69 ya redondeado: lejos del corte, para que el redondeo no lo cruce
        (60.0, MODERATE),  # 40 exacto
        (59.0, UNFAVORABLE),  # 38 crudo, lejos del corte por la misma razón
    ],
)
def test_cortes_de_nivel_exactos(thresholds, value, level):
    assert score_signal("water", value, thresholds).level == level


@pytest.mark.parametrize(
    "ph,level",
    [
        # Lejos de los cortes a propósito: 4,76 da 69,999… en coma flotante. Los cortes exactos se prueban con el agua.
        (4.8, FAVORABLE),  # 75
        (4.7, MODERATE),  # 62,5
        (4.55, MODERATE),  # 43,75
        (4.5, UNFAVORABLE),  # 37,5
    ],
)
def test_niveles_tambien_con_curva_de_la_ficha(thresholds, papa, ph, level):
    assert score_signal("soil", ph, thresholds, papa).level == level


def test_los_cortes_de_nivel_salen_de_la_configuracion_recibida(thresholds):
    changed = replace(thresholds, favorable=90.0, moderate=60.0)
    # water 80 % → 70: con los cortes del repositorio es favorable; con 90/60, moderada.
    assert score_signal("water", 80.0, thresholds).level == FAVORABLE
    assert score_signal("water", 80.0, changed).level == MODERATE
    # water 55 % → 30: unfavorable con 90/60.
    assert score_signal("water", 55.0, changed).level == UNFAVORABLE


# ---------- `score` se redondea antes de decidir el nivel: el agricultor ve un entero (revisión de Felipe, PR #65) ----------


@pytest.fixture
def identidad(thresholds) -> Thresholds:
    """Los umbrales reales, pero con la curva de `water` cambiada por la identidad (0→0, 100→100): la calificación
    cruda es el mismo valor que se pide, así que un valor como 69,5 no depende de ningún redondeo de la curva."""
    water = replace(thresholds.signals["water"], curve=((0.0, 0.0), (100.0, 100.0)))
    return replace(thresholds, signals={**thresholds.signals, "water": water})


def test_69_5_redondea_a_70_y_es_favorable_no_moderada(identidad):
    """69,5 tiene que dar 70 (favorable, el corte real es 70), no quedarse en 69 (moderada) por decimales que el
    agricultor nunca ve. Es `floor(x + 0,5)`, no `round()`: `round(69.5)` también da 70, pero por la regla
    contraria (al par); esta prueba no distingue las dos reglas, la de abajo sí."""
    result = score_signal("water", 69.5, identidad)
    assert (result.score, result.level) == (70, FAVORABLE)


def test_69_4_redondea_a_69_y_sigue_moderada(identidad):
    result = score_signal("water", 69.4, identidad)
    assert (result.score, result.level) == (69, MODERATE)


def test_el_redondeo_es_hacia_arriba_desde_la_mitad_no_al_par(identidad):
    """`round()` redondea 68,5 a 68 (al par) y 69,5 a 70 (también al par, por casualidad). Aquí las dos suben:
    68,5 → 69, no 68. Si se usara `round()`, esta prueba fallaría para 68,5 aunque la de 69,5 pasara igual."""
    assert score_signal("water", 68.5, identidad).score == 69


def test_critica_tambien_se_decide_con_el_entero_redondeado(thresholds):
    """`frost` es crítica bajo 40: 39,5 redondea a 40 (no crítica) aunque el decimal crudo esté bajo el corte."""
    identidad = replace(thresholds.signals["frost"], curve=((0.0, 0.0), (100.0, 100.0)))
    changed = replace(thresholds, signals={**thresholds.signals, "frost": identidad})
    assert score_signal("frost", 39.5, changed).critical is False


def test_agua_con_calificacion_20_no_es_critica(thresholds):
    result = score_signal("water", 50.0, thresholds)
    assert (result.score, result.level, result.critical) == (20.0, UNFAVORABLE, False)


def test_agua_bajo_20_es_critica(thresholds):
    # 47,0 → 19 ya redondeado: lejos del corte a propósito, para que el redondeo no lo cruce (revisión de Felipe).
    result = score_signal("water", 47.0, thresholds)
    assert result.score < 20
    assert (result.level, result.critical) == (UNFAVORABLE, True)


def test_heladas_con_calificacion_40_no_son_criticas(thresholds):
    result = score_signal("frost", 40.0, thresholds)
    assert (result.score, result.level, result.critical) == (40.0, MODERATE, False)


def test_heladas_bajo_40_son_criticas(thresholds):
    # 45,0 → 37 ya redondeado: lejos del corte a propósito, para que el redondeo no lo cruce (revisión de Felipe).
    result = score_signal("frost", 45.0, thresholds)
    assert result.score < 40
    assert (result.level, result.critical) == (UNFAVORABLE, True)


def test_calor_apenas_bajo_el_maximo_no_es_critico(thresholds, papa):
    """29,9 °C da 2: desfavorable, pero `critical_below: 1` solo marca la calificación 0."""
    result = score_signal("heat", 29.9, thresholds, papa)
    assert result.score == pytest.approx(2.0)
    assert (result.level, result.critical) == (UNFAVORABLE, False)


def test_el_umbral_critico_sale_de_la_configuracion_recibida(thresholds):
    # water 70 % → 55: con el repositorio no es crítica; con 50, tampoco; con 55, tampoco (estricto); con 60, sí.
    assert not score_signal("water", 70.0, thresholds).critical
    assert not score_signal("water", 70.0, with_signal(thresholds, "water", critical_below=50.0)).critical
    assert not score_signal("water", 70.0, with_signal(thresholds, "water", critical_below=55.0)).critical
    assert score_signal("water", 70.0, with_signal(thresholds, "water", critical_below=60.0)).critical


def test_sin_umbral_critico_nunca_es_critica(thresholds):
    """`critical_below` nulo: ni la calificación 0 es crítica."""
    assert score_signal("water", 0.0, with_signal(thresholds, "water", critical_below=None)) == SignalScore(
        AVAILABLE, 0.0, UNFAVORABLE, False
    )


def test_el_suelo_nunca_es_critico_en_ningun_valor(thresholds, papa):
    """R10: recorre todo el rango de pH; ninguna calificación lo vuelve crítico (que `soil` no tenga `critical_below`
    lo prueba tests/test_umbrales.py)."""
    for tenth in range(0, 141):
        assert score_signal("soil", tenth / 10, thresholds, papa).critical is False


# ---------- Sin datos: insufficient_data, nunca un límite «típico» (R1, R8) ----------


@pytest.mark.parametrize("signal", ["supply", "market"])
@pytest.mark.parametrize("value", [None, -50.0, 0.0, 1.0, 35.0, 120.0])
def test_oferta_y_mercado_sin_curva_son_siempre_sin_datos(thresholds, papa, signal, value):
    """`curve: null` en thresholds.yaml 1.0.0: sin fuente para los cortes, aunque haya valor medido."""
    assert score_signal(signal, value, thresholds, papa) == INSUFFICIENT


@pytest.mark.parametrize("signal", ["water", "frost", "heat", "soil"])
def test_sin_valor_medido_es_sin_datos(thresholds, papa, signal):
    assert score_signal(signal, None, thresholds, papa) == INSUFFICIENT


@pytest.mark.parametrize("signal", ["water", "frost", "heat", "soil"])
def test_valor_nan_es_sin_datos(thresholds, papa, signal):
    """R1: un NaN no es un valor medido; no llega a la curva ni lanza error."""
    assert score_signal(signal, float("nan"), thresholds, papa) == INSUFFICIENT


@pytest.mark.parametrize("missing", HEAT_LIMITS + SOIL_LIMITS)
def test_limite_de_la_ficha_en_nan_es_sin_datos(thresholds, papa, missing):
    """Un límite NaN (como lo deja un nulo de Polars convertido a float) vale lo mismo que uno ausente."""
    signal, value = ("heat", 27.5) if missing in HEAT_LIMITS else ("soil", 5.6)
    assert score_signal(signal, value, thresholds, {**papa, missing: float("nan")}) == INSUFFICIENT


@pytest.mark.parametrize("missing", HEAT_LIMITS)
def test_calor_sin_un_limite_de_la_ficha_es_sin_datos(thresholds, papa, missing):
    as_none = {**papa, missing: None}
    absent = {k: v for k, v in papa.items() if k != missing}
    assert score_signal("heat", 27.5, thresholds, as_none) == INSUFFICIENT
    assert score_signal("heat", 27.5, thresholds, absent) == INSUFFICIENT


@pytest.mark.parametrize("missing", SOIL_LIMITS)
def test_suelo_sin_un_limite_de_la_ficha_es_sin_datos(thresholds, papa, missing):
    as_none = {**papa, missing: None}
    absent = {k: v for k, v in papa.items() if k != missing}
    assert score_signal("soil", 5.6, thresholds, as_none) == INSUFFICIENT
    assert score_signal("soil", 5.6, thresholds, absent) == INSUFFICIENT


@pytest.mark.parametrize("signal", ["water", "frost", "heat", "soil"])
def test_senal_sin_curva_es_siempre_sin_datos(thresholds, papa, signal):
    """`curve: null` (sin fuente para los cortes) da `insufficient_data` en cualquier señal, aunque haya valor."""
    without_curve = with_signal(thresholds, signal, curve=None, critical_below=None)
    assert score_signal(signal, 50.0, without_curve, papa) == INSUFFICIENT


@pytest.mark.parametrize("signal", ["heat", "soil"])
def test_curva_de_la_ficha_sin_ficha_es_sin_datos(thresholds, signal):
    assert score_signal(signal, 5.6, thresholds) == INSUFFICIENT
    assert score_signal(signal, 5.6, thresholds, None) == INSUFFICIENT
    assert score_signal(signal, 5.6, thresholds, {}) == INSUFFICIENT


# ---------- Infinitos: el extremo de la curva, no «sin dato» ----------


@pytest.mark.parametrize(
    "signal,value,expected",
    [
        ("water", float("inf"), SignalScore(AVAILABLE, 100.0, FAVORABLE, False)),
        ("water", float("-inf"), SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)),
        ("frost", float("inf"), SignalScore(AVAILABLE, 0.0, UNFAVORABLE, True)),
        ("frost", float("-inf"), SignalScore(AVAILABLE, 100.0, FAVORABLE, False)),
    ],
)
def test_infinito_se_califica_con_el_extremo_de_la_curva(thresholds, signal, value, expected):
    """A diferencia del NaN, `inf` y `-inf` tienen lado en la curva: toman la calificación del punto extremo."""
    assert score_signal(signal, value, thresholds) == expected


# ---------- Determinismo (R4) ----------


@pytest.mark.parametrize(
    "signal,value",
    [("water", 73.3), ("frost", 12.5), ("heat", 26.1), ("soil", 4.9), ("supply", 10.0), ("market", 0.95)],
)
def test_mismo_dato_misma_calificacion(thresholds, papa, signal, value):
    first = score_signal(signal, value, thresholds, papa)
    assert all(score_signal(signal, value, thresholds, papa) == first for _ in range(5))


def test_no_modifica_lo_que_recibe(thresholds, papa):
    before_thresholds, before_papa = copy.deepcopy(thresholds), dict(papa)
    for signal in ("water", "frost", "heat", "soil", "supply", "market"):
        score_signal(signal, 50.0, thresholds, papa)
    assert thresholds == before_thresholds
    assert papa == before_papa


def test_el_resultado_es_inmutable(thresholds):
    result = score_signal("water", 80.0, thresholds)
    with pytest.raises(AttributeError):
        result.score = 0.0  # type: ignore[misc]


# ---------- Errores: de programación o de catálogo, nunca «sin datos» ----------


@pytest.mark.parametrize("value", [10.0, None])
def test_senal_desconocida_da_key_error(thresholds, value):
    """Una señal que no está en los umbrales es un error de programación, también sin valor."""
    with pytest.raises(KeyError):
        score_signal("excess_rain", value, thresholds)


@pytest.mark.parametrize(
    "signal,value,broken",
    [
        ("heat", 27.0, {"temp_opt_max_c": 30.0, "heat_max_c": 25.0}),
        ("soil", 5.6, {"ph_min": 5.0, "ph_opt_min": 4.2, "ph_opt_max": 6.2, "ph_max": 8.5}),
    ],
)
def test_ficha_incoherente_deja_pasar_el_value_error(thresholds, signal, value, broken):
    """Una ficha con los límites desordenados es un error del catálogo: falla ruidoso, no da calificación."""
    with pytest.raises(ValueError):
        score_signal(signal, value, thresholds, broken)
