"""El semáforo de una ventana: luz, acción y razones con unos pesos (HU-074; specs/01-reglas.md, «Agregación del
semáforo», «Las prioridades del agricultor» y «Aptitud del cultivo en la zona»).

Casos con calificaciones fijas, sin endpoint ni dataset: la calificación de cada señal es de HU-196
(tests/engine/test_signal_score.py) y el orden de las ventanas de HU-192 (tests/engine/test_orden_ventanas.py). Los
pesos por defecto son los reales de `weights.yaml` 1.0.0 (agua 3, heladas 4, calor 2, suelo 2, oferta 1, mercado 1),
leídos con su cargador: la prueba sí lee archivos; el motor no (R6, cubierto en tests/engine/test_etapas.py, que
recorre todo `backend/engine/`).

Decisiones que fijan estas pruebas (docstring de `backend/engine/traffic_light.py`):
- Nivel efectivo: con peso 4 o más, un `moderate` cuenta como `unfavorable` para la luz y para la acción; el factor
  limitante y el alto riesgo usan la calificación y el nivel reales.
- La tabla de acciones mira las señales que cuentan con nivel efectivo `unfavorable` (specs/01-reglas.md, bajo la
  tabla de acciones; aprobado por Felipe el 14 de noviembre de 2026, docs/registro-de-decisiones.md).
- Regla 1: solo mira el peso de `water`, no `counts`; no hay factor limitante (como `DIAGNOSIS_NOT_EVALUABLE` del
  contrato), pero el alto riesgo sí se calcula y la razón nombra las críticas.
- Las razones se comprueban por las señales que nombran y por su comienzo, no por la frase exacta.
"""

from datetime import date

import pytest

from backend.config.thresholds import load_thresholds
from backend.config.weights import load_weights
from backend.engine.signal_score import CLIMATE_CRITICAL_SIGNALS, SignalScore, score_signal
from backend.engine.traffic_light import (
    DEFAULT,
    FARMER,
    GREEN,
    NOT_EVALUABLE,
    OTHER_WINDOW,
    RED,
    REVIEW_DATA,
    ROTATE,
    ROTATE_SIGNALS,
    SIGNAL_NAMES_ES,
    SOW,
    YELLOW,
    TrafficLight,
    missing_data_limitations,
    traffic_light,
)
from backend.engine.window_order import WindowSignals, rank_window
from common.signals import P0_SIGNALS

SIGNALS = P0_SIGNALS
ALL_3 = dict.fromkeys(SIGNALS, 3)
DEFAULTS = load_weights().weights

SUITABLE = "suitable"
NOT_SUITABLE = "not_suitable"
SUITABILITY_UNKNOWN = "insufficient_data"

INSUFFICIENT = SignalScore("insufficient_data", None, None, False)
NOT_APPLICABLE = SignalScore("not_applicable", None, None, False)

FARMER_PREFIX = "Con sus prioridades"
DEFAULT_PREFIX = "Con el criterio de AgroSense"


def sig(score: int, critical: bool = False) -> SignalScore:
    """Una señal calificada, con el nivel que corresponde a su calificación (70+, 40-69, <40)."""
    if score >= 70:
        level = "favorable"
    elif score >= 40:
        level = "moderate"
    else:
        level = "unfavorable"
    assert not critical or level == "unfavorable", "una señal crítica es desfavorable"
    return SignalScore("available", score, level, critical)


def ventana(**signals: SignalScore) -> dict[str, SignalScore]:
    """Las seis señales del P0: las que no se dan quedan favorables (85)."""
    return {name: signals.get(name, sig(85)) for name in SIGNALS}


def luz(signals, weights, suitability=SUITABLE, basis=FARMER) -> TrafficLight:
    return traffic_light(suitability, signals, weights, basis)


def light_action(result: TrafficLight) -> tuple[str, str]:
    return result.light, result.action


def core(result: TrafficLight) -> tuple:
    """Todo menos las razones: luz, acción, límite y alto riesgo."""
    return result.light, result.action, result.limiting_signal, result.high_risk


def text(result: TrafficLight) -> str:
    return " ".join(result.reasons)


def starts_with(result: TrafficLight, prefix: str) -> bool:
    return bool(result.reasons) and result.reasons[0].startswith(prefix)


# ------------------------------------------------------------------ configuración que fija los casos


def test_los_pesos_por_defecto_son_los_de_weights_yaml_1_1_0():
    """1.1.0 (decisión 17) solo cambió el porqué de la oferta y el mercado: los pesos son los de 1.0.0."""
    weights = load_weights()
    assert weights.version == "1.1.0"
    assert weights.weights == {"water": 3, "frost": 4, "heat": 2, "soil": 2, "supply": 1, "market": 1}


def test_las_senales_de_rotar_y_las_de_clima_parten_las_del_p0():
    """La tabla de acciones: «si no es de rotar, es de clima». Si se agrega una señal del P0, hay que decidir de qué
    lado va."""
    assert not ROTATE_SIGNALS & CLIMATE_CRITICAL_SIGNALS
    assert set(P0_SIGNALS) == ROTATE_SIGNALS | CLIMATE_CRITICAL_SIGNALS


def test_cada_senal_del_p0_tiene_su_nombre_en_espanol():
    assert set(SIGNAL_NAMES_ES) == set(P0_SIGNALS)


# ------------------------------------------------------------------ regla 0: aptitud


def test_regla_0_un_cultivo_no_apto_da_rojo_y_rotar_sin_mirar_las_senales():
    result = luz(ventana(), ALL_3, suitability=NOT_SUITABLE)

    assert core(result) == (RED, ROTATE, None, False)
    # El texto del contrato (`DIAGNOSIS_NOT_SUITABLE` de backend/api/calc_examples.py).
    assert result.reasons == ("Este cultivo no se da en su zona: elija otro",)


@pytest.mark.parametrize("signals", [ventana(water=INSUFFICIENT), ventana(frost=sig(10, critical=True)), {}])
def test_regla_0_va_antes_que_todo_lo_demas(signals):
    """Ni el agua sin datos (regla 1) ni una helada crítica (regla 2) cambian el rojo por no apto."""
    assert core(luz(signals, ALL_3, suitability=NOT_SUITABLE)) == (RED, ROTATE, None, False)


def test_regla_0_no_depende_de_los_pesos():
    assert light_action(luz(ventana(), dict.fromkeys(SIGNALS, 0), suitability=NOT_SUITABLE)) == (RED, ROTATE)


def test_aptitud_sin_datos_no_bloquea_y_se_evalua_normal():
    assert core(luz(ventana(), ALL_3, suitability=SUITABILITY_UNKNOWN)) == core(luz(ventana(), ALL_3))
    assert light_action(luz(ventana(), ALL_3, suitability=SUITABILITY_UNKNOWN)) == (GREEN, SOW)


# ------------------------------------------------------------------ regla 1: agua


@pytest.mark.parametrize(
    "water",
    [INSUFFICIENT, SignalScore("available", None, None, False), NOT_APPLICABLE],
    ids=["sin_datos", "available_sin_calificacion", "no_aplica"],
)
def test_si_el_agua_cuenta_y_no_esta_disponible_la_luz_es_no_evaluable(water):
    """Sin críticas no hay alto riesgo; sin agua no hay factor limitante (`DIAGNOSIS_NOT_EVALUABLE` del contrato)."""
    result = luz(ventana(water=water), ALL_3)

    assert core(result) == (NOT_EVALUABLE, REVIEW_DATA, None, False)
    assert "agua" in text(result)


def test_agua_ausente_del_mapa_con_peso_es_no_evaluable():
    signals = ventana()
    del signals["water"]

    assert core(luz(signals, ALL_3)) == (NOT_EVALUABLE, REVIEW_DATA, None, False)


def test_regla_1_sin_agua_no_hay_factor_limitante_aunque_otra_senal_sea_baja():
    """Un «factor limitante» sin el agua confundiría: la luz no se evaluó."""
    assert luz(ventana(water=INSUFFICIENT, soil=sig(45)), ALL_3).limiting_signal is None


def test_regla_1_va_antes_que_una_helada_critica_pero_no_la_esconde():
    """Las reglas se aplican en orden: sin agua que cuenta no hay luz que evaluar, aunque haya un riesgo grave. El
    alto riesgo sí se calcula y la razón nombra la helada; el factor limitante queda nulo."""
    result = luz(ventana(water=INSUFFICIENT, frost=sig(10, critical=True)), ALL_3)

    assert core(result) == (NOT_EVALUABLE, REVIEW_DATA, None, True)
    assert "agua" in text(result) and "la helada" in text(result)


def test_regla_1_con_un_calor_critico_de_peso_0_tambien_es_alto_riesgo():
    result = luz(ventana(water=INSUFFICIENT, heat=sig(5, critical=True)), {**ALL_3, "heat": 0})

    assert core(result) == (NOT_EVALUABLE, REVIEW_DATA, None, True)
    assert "el calor" in text(result)


def test_regla_1_sin_criticas_la_razon_no_nombra_otras_senales():
    """R5: con agua sin datos y lo demás favorable, la razón solo habla del agua."""
    result = luz(ventana(water=INSUFFICIENT), ALL_3)

    assert not any(SIGNAL_NAMES_ES[name] in text(result) for name in SIGNALS if name != "water")


@pytest.mark.parametrize("weights", [{**ALL_3, "water": 0}, {**ALL_3, "water": -1}, {k: v for k, v in ALL_3.items() if k != "water"}])
def test_con_peso_0_en_el_agua_la_luz_no_queda_no_evaluable(weights):
    result = luz(ventana(water=INSUFFICIENT), weights)

    assert light_action(result) == (GREEN, SOW)
    assert result.limiting_signal != "water"


# ------------------------------------------------------------------ regla 2: rojo


@pytest.mark.parametrize("signal", ["water", "frost", "heat"])
@pytest.mark.parametrize("weight", [0, 1, 3, 5])
def test_una_senal_desfavorable_critica_nunca_da_verde(signal, weight):
    """R2: con todas las demás favorables, aunque el agricultor le ponga peso 0, un riesgo grave de clima da rojo."""
    result = luz(ventana(**{signal: sig(10, critical=True)}), {**ALL_3, signal: weight})

    assert core(result) == (RED, OTHER_WINDOW, signal, True)
    assert SIGNAL_NAMES_ES[signal] in text(result)


def test_una_helada_critica_con_peso_0_sigue_dando_rojo():
    result = luz(ventana(water=sig(95), supply=sig(95), frost=sig(15, critical=True)), {**DEFAULTS, "frost": 0})

    assert core(result) == (RED, OTHER_WINDOW, "frost", True)
    assert "la helada" in text(result)


@pytest.mark.parametrize("signal", ["soil", "supply", "market"])
def test_una_critica_que_no_es_de_clima_con_peso_da_rojo_y_rotar(signal):
    result = luz(ventana(**{signal: sig(5, critical=True)}), ALL_3)

    assert core(result) == (RED, ROTATE, signal, True)


@pytest.mark.parametrize("signal", ["soil", "supply", "market"])
def test_una_critica_que_no_es_de_clima_con_peso_0_no_cuenta(signal):
    result = luz(ventana(**{signal: sig(5, critical=True)}), {**ALL_3, signal: 0})

    assert core(result) == (GREEN, SOW, "water", False)


def test_dos_desfavorables_de_clima_no_criticas_dan_rojo_y_otra_ventana():
    result = luz(ventana(water=sig(25), heat=sig(30)), ALL_3)

    assert core(result) == (RED, OTHER_WINDOW, "water", False)
    assert "el agua" in text(result) and "el calor" in text(result)


def test_dos_desfavorables_y_una_es_de_rotar_dan_rojo_y_rotar():
    assert core(luz(ventana(soil=sig(30), market=sig(35)), ALL_3)) == (RED, ROTATE, "soil", False)
    assert core(luz(ventana(heat=sig(30), market=sig(35)), ALL_3)) == (RED, ROTATE, "heat", False)


# ------------------------------------------------------------------ reglas 3 y 4: verde y amarillo


def test_todas_favorables_dan_verde_y_sembrar():
    result = luz(ventana(water=sig(90), frost=sig(75)), ALL_3)

    assert core(result) == (GREEN, SOW, "frost", False)


def test_el_agua_que_cuenta_y_no_es_favorable_da_amarillo():
    result = luz(ventana(water=sig(50)), ALL_3)

    assert core(result) == (YELLOW, OTHER_WINDOW, "water", False)
    assert "el agua" in text(result)


def test_con_peso_0_en_el_agua_moderada_y_no_critica_la_regla_3_no_la_exige():
    result = luz(ventana(water=sig(50)), {**ALL_3, "water": 0})

    assert core(result) == (GREEN, SOW, "frost", False)


def test_con_peso_0_en_el_agua_desfavorable_no_critica_da_verde_y_lo_dice():
    result = luz(ventana(water=sig(25)), {**ALL_3, "water": 0})

    assert light_action(result) == (GREEN, SOW)
    assert "el agua" in text(result)


def test_una_desfavorable_no_critica_de_clima_da_amarillo_y_otra_ventana():
    result = luz(ventana(heat=sig(30)), ALL_3)

    assert core(result) == (YELLOW, OTHER_WINDOW, "heat", False)
    assert "el calor" in text(result)


def test_una_helada_moderada_con_peso_4_en_amarillo_dice_cuanto_pesa():
    result = luz(ventana(frost=sig(55)), {**ALL_3, "frost": 4})

    assert light_action(result) == (YELLOW, OTHER_WINDOW)
    assert "la helada" in text(result) and "(pesa 4)" in text(result)


@pytest.mark.parametrize("signal", ["soil", "supply", "market"])
def test_una_desfavorable_no_critica_de_rotar_da_amarillo_y_rotar(signal):
    result = luz(ventana(**{signal: sig(30)}), ALL_3)

    assert core(result) == (YELLOW, ROTATE, signal, False)
    assert SIGNAL_NAMES_ES[signal] in text(result)


def test_agua_moderada_y_oferta_desfavorable_dan_amarillo_y_rotar():
    """Una sola desfavorable (la oferta, peso 1) y el agua moderada (peso 3, no sube): amarillo; la oferta es de rotar."""
    result = luz(ventana(water=sig(55), supply=sig(30)), {**ALL_3, "water": 3, "supply": 1})

    assert core(result) == (YELLOW, ROTATE, "supply", False)
    assert "la oferta" in text(result)


# ------------------------------------------------------------------ prioridades: oferta y dos luces


def test_oferta_desfavorable_con_peso_0_da_verde_y_con_los_pesos_por_defecto_amarillo():
    """Criterio de HU-074: `overall` puede dar verde mientras `overall_default` da amarillo."""
    signals = ventana(supply=sig(30))

    overall = luz(signals, {**DEFAULTS, "supply": 0}, basis=FARMER)
    overall_default = luz(signals, DEFAULTS, basis=DEFAULT)

    assert light_action(overall) == (GREEN, SOW)
    assert "la oferta" in text(overall)
    assert light_action(overall_default) == (YELLOW, ROTATE)
    assert overall_default.limiting_signal == "supply"


def test_ejemplo_diagnosis_ok_del_contrato():
    """`DIAGNOSIS_OK` (backend/api/calc_examples.py; specs/02-contratos.md, «Respuesta de diagnóstico»)."""
    signals = {
        "water": sig(86),
        "frost": sig(58),
        "heat": sig(94),
        "soil": sig(80),
        "supply": sig(30),
        "market": INSUFFICIENT,
    }
    farmer = {"water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3}

    overall = luz(signals, farmer, basis=FARMER)
    overall_default = luz(signals, DEFAULTS, basis=DEFAULT)

    assert core(overall) == (GREEN, SOW, "frost", False)
    assert starts_with(overall, FARMER_PREFIX)
    assert "la oferta" in text(overall)
    assert core(overall_default) == (RED, ROTATE, "supply", False)
    assert starts_with(overall_default, DEFAULT_PREFIX)
    assert "la helada" in text(overall_default) and "(pesa 4)" in text(overall_default) and "la oferta" in text(overall_default)
    # R5: el mercado no se evaluó (sin datos): ninguna razón lo cita.
    assert "el mercado" not in text(overall) and "el mercado" not in text(overall_default)


def test_con_los_pesos_por_defecto_una_helada_moderada_sola_da_amarillo_y_otra_ventana():
    result = luz(ventana(frost=sig(55)), DEFAULTS, basis=DEFAULT)

    assert core(result) == (YELLOW, OTHER_WINDOW, "frost", False)
    assert "la helada" in text(result)


def test_con_los_pesos_por_defecto_helada_moderada_y_oferta_desfavorable_dan_rojo_y_rotar():
    result = luz(ventana(frost=sig(55), supply=sig(30)), DEFAULTS, basis=DEFAULT)

    assert core(result) == (RED, ROTATE, "supply", False)
    assert "la helada" in text(result) and "(pesa 4)" in text(result) and "la oferta" in text(result)


@pytest.mark.parametrize("weight", [4, 5, 7])
def test_con_peso_4_o_mas_una_moderada_cuenta_como_desfavorable(weight):
    """Un peso mayor que 5 se trata como alto: el motor no valida el rango (la API sí, con 422)."""
    assert light_action(luz(ventana(heat=sig(60)), {**ALL_3, "heat": weight})) == (YELLOW, OTHER_WINDOW)


def test_con_peso_3_una_moderada_que_no_es_el_agua_no_impide_el_verde():
    assert light_action(luz(ventana(heat=sig(60)), ALL_3)) == (GREEN, SOW)


def test_los_pesos_del_agricultor_y_los_de_agrosense_iguales_dan_la_misma_luz_y_cambia_solo_el_comienzo():
    signals = ventana(frost=sig(55), supply=sig(30))

    farmer = luz(signals, DEFAULTS, basis=FARMER)
    default = luz(signals, DEFAULTS, basis=DEFAULT)

    assert core(farmer) == core(default)
    assert starts_with(farmer, FARMER_PREFIX)
    assert starts_with(default, DEFAULT_PREFIX)


# ------------------------------------------------------------------ nivel efectivo: solo luz y acción


def test_el_factor_limitante_es_la_calificacion_mas_baja_no_la_desfavorable_efectiva():
    # La helada (60, peso 4) es desfavorable efectiva; el suelo (45, peso 3) es más bajo y es el limitante.
    result = luz(ventana(frost=sig(60), soil=sig(45)), {**ALL_3, "frost": 4})

    assert core(result) == (YELLOW, OTHER_WINDOW, "soil", False)


def test_dos_moderadas_con_peso_4_dan_rojo_sin_alto_riesgo_y_otra_ventana():
    result = luz(ventana(water=sig(50), frost=sig(55)), {**ALL_3, "water": 4, "frost": 4})

    assert core(result) == (RED, OTHER_WINDOW, "water", False)
    assert text(result).count("(pesa 4)") == 2


def test_una_oferta_moderada_con_peso_5_sola_da_amarillo_y_rotar():
    result = luz(ventana(supply=sig(60)), {**ALL_3, "supply": 5})

    assert core(result) == (YELLOW, ROTATE, "supply", False)
    assert "la oferta" in text(result) and "(pesa 5)" in text(result)


def test_helada_y_oferta_moderadas_con_peso_4_dan_rojo_y_rotar():
    result = luz(ventana(frost=sig(55), supply=sig(60)), {**ALL_3, "frost": 4, "supply": 4})

    assert core(result) == (RED, ROTATE, "frost", False)


# ------------------------------------------------------------------ regla 5: sin datos y no aplica


def test_sin_datos_de_la_oferta_sale_igual_que_con_peso_0_en_la_oferta_y_la_limitacion_lo_dice():
    without = ventana(water=sig(50), supply=INSUFFICIENT)
    zero = ventana(water=sig(50), supply=sig(30))
    zero_weights = {**ALL_3, "supply": 0}

    assert core(luz(without, ALL_3)) == core(luz(zero, zero_weights)) == (YELLOW, OTHER_WINDOW, "water", False)
    # El orden de las ventanas (HU-192) también sale igual.
    start, end = date(2027, 1, 4), date(2027, 6, 21)
    ranked_without = rank_window(WindowSignals(start, end, without), ALL_3)
    ranked_zero = rank_window(WindowSignals(start, end, zero), zero_weights)
    assert ranked_without == ranked_zero

    limitations = missing_data_limitations(without)
    assert len(limitations) == 1
    assert "la oferta" in limitations[0]


@pytest.mark.parametrize("signal", ["frost", "heat", "soil", "market"])
def test_sin_datos_frost_heat_soil_o_market_no_cambian_la_luz_y_van_a_las_limitaciones(signal):
    for base in (ventana(), ventana(water=sig(50))):  # verde y amarillo
        expected = light_action(luz(base, ALL_3))
        changed = {**base, signal: INSUFFICIENT}

        assert light_action(luz(changed, ALL_3)) == expected
        assert light_action(luz(changed, DEFAULTS, basis=DEFAULT)) == light_action(luz(base, DEFAULTS, basis=DEFAULT))
        assert missing_data_limitations(changed) == missing_data_limitations(ventana(**{signal: INSUFFICIENT}))
        (limitation,) = missing_data_limitations(changed)
        assert SIGNAL_NAMES_ES[signal] in limitation


@pytest.mark.parametrize("signal", ["frost", "heat"])
def test_no_aplica_no_cambia_la_luz_ni_va_a_las_limitaciones(signal):
    for base in (ventana(), ventana(water=sig(50))):
        changed = {**base, signal: NOT_APPLICABLE}

        assert light_action(luz(changed, ALL_3)) == light_action(luz(base, ALL_3))
        assert missing_data_limitations(changed) == ()


def test_sin_senales_sin_datos_no_hay_limitaciones():
    assert missing_data_limitations(ventana()) == ()


def test_las_limitaciones_van_en_el_orden_de_las_senales_no_del_mapa():
    signals = {**ventana(), "market": INSUFFICIENT, "heat": NOT_APPLICABLE, "frost": INSUFFICIENT}
    signals = dict(reversed(list(signals.items())))

    limitations = missing_data_limitations(signals)

    assert len(limitations) == 2
    assert SIGNAL_NAMES_ES["frost"] in limitations[0]
    assert SIGNAL_NAMES_ES["market"] in limitations[1]


def test_el_agua_sin_datos_va_a_las_limitaciones_sin_decir_que_no_cambia_la_luz():
    """Sin el agua, con peso, la luz es `not_evaluable`: la limitación no puede decir que no cambia la luz."""
    (limitation,) = missing_data_limitations(ventana(water=INSUFFICIENT))

    assert "el agua" in limitation
    assert "luz" not in limitation


def test_una_senal_del_p0_ausente_del_mapa_es_como_sin_datos_y_va_a_las_limitaciones():
    """R1: una señal que falta del mapa no desaparece en silencio."""
    absent = ventana(water=sig(50))
    del absent["frost"]
    insufficient = ventana(water=sig(50), frost=INSUFFICIENT)

    for weights, basis in ((ALL_3, FARMER), (DEFAULTS, DEFAULT)):
        assert luz(absent, weights, basis=basis) == luz(insufficient, weights, basis=basis)
    assert missing_data_limitations(absent) == missing_data_limitations(insufficient)
    (limitation,) = missing_data_limitations(absent)
    assert "la helada" in limitation


def test_las_senales_del_p0_ausentes_y_las_de_mas_salen_en_orden():
    """Un mapa parcial: las del P0 que faltan y una señal sin datos fuera del P0, todas en el orden de las señales."""
    limitations = missing_data_limitations({"water": sig(80), "otra": INSUFFICIENT})

    assert [next(name for name in (*SIGNAL_NAMES_ES.values(), "otra") if name in item) for item in limitations] == [
        "la helada",
        "el calor",
        "el suelo",
        "la oferta",
        "el mercado",
        "otra",
    ]


def test_una_senal_sin_datos_no_se_cita_en_las_razones():
    """R5: las razones solo citan señales evaluadas."""
    result = luz(ventana(heat=sig(30), soil=INSUFFICIENT, market=INSUFFICIENT), ALL_3)

    assert light_action(result) == (YELLOW, OTHER_WINDOW)
    assert "el suelo" not in text(result) and "el mercado" not in text(result)


# ------------------------------------------------------------------ pesos que faltan o son negativos


def test_un_peso_negativo_vale_0():
    assert light_action(luz(ventana(supply=sig(30)), {**ALL_3, "supply": -2})) == (GREEN, SOW)
    assert core(luz(ventana(frost=sig(10, critical=True)), {**ALL_3, "frost": -4})) == (RED, OTHER_WINDOW, "frost", True)


def test_un_peso_que_falta_vale_0():
    result = luz(ventana(water=sig(80), frost=sig(50), supply=sig(20)), {"water": 3})

    assert core(result) == (GREEN, SOW, "water", False)
    # La oferta desfavorable sin peso se dice, pero no cuenta para la luz.
    assert any("la oferta" in reason and "no cuenta" in reason for reason in result.reasons)


@pytest.mark.parametrize("weight", [4, 5])
def test_una_critica_con_peso_alto_dice_que_es_critica_una_sola_vez_y_no_cuanto_pesa(weight):
    """Una crítica ya es desfavorable: el peso alto no la sube, y la razón no repite «(pesa N)»."""
    result = luz(ventana(frost=sig(10, critical=True)), {**ALL_3, "frost": weight})

    assert core(result) == (RED, OTHER_WINDOW, "frost", True)
    assert text(result).count("es crítica") == 1
    assert "(pesa" not in text(result)


def test_con_todos_los_pesos_en_0_solo_cuentan_los_riesgos_graves_de_clima():
    """La API rechaza con 422 las prioridades todas en 0, pero el motor no valida rangos y puede recibirlas. El caso
    que sí llega desde la API está en la prueba siguiente."""
    zero = dict.fromkeys(SIGNALS, 0)

    nothing_counts = luz(ventana(water=sig(30), frost=sig(50), soil=sig(5)), zero)
    # Sin ninguna señal que cuente no hay evidencia de nada, ni a favor ni en contra: nunca `green` (sería afirmar
    # que está bien sin haber evaluado nada, e inconsistente con HU-192, donde este mismo caso tampoco se
    # recomienda). Queda `yellow`/`other_window`, sin factor limitante ni alto riesgo.
    assert core(nothing_counts) == (YELLOW, OTHER_WINDOW, None, False)
    assert "ninguna señal que cuenta tiene calificación" in text(nothing_counts)
    assert core(luz(ventana(heat=sig(10, critical=True), soil=sig(5)), zero)) == (RED, OTHER_WINDOW, "heat", True)


def test_con_peso_solo_en_oferta_y_mercado_sin_datos_la_luz_es_amarilla_y_no_verde():
    """El caso real de «ninguna señal que cuente y califique» (revisión de Felipe, PR #94): quien solo le pone peso a
    la oferta y al mercado, que hoy son siempre `insufficient_data`. La oferta sin datos va como peso 0 (regla 1) y el
    mercado sin datos no cambia la luz (regla 5). Agua, heladas, calor y suelo tienen peso 0 y ninguna es crítica, así
    que tampoco cuentan por riesgo grave. Nunca `green`: es `yellow`/`other_window`, sin factor limitante ni alto
    riesgo, y la razón lo explica (R5)."""
    weights = {**dict.fromkeys(SIGNALS, 0), "supply": 3, "market": 3}
    signals = ventana(water=sig(30), frost=sig(50), heat=sig(85), soil=sig(20), supply=INSUFFICIENT, market=INSUFFICIENT)

    result = luz(signals, weights)

    assert core(result) == (YELLOW, OTHER_WINDOW, None, False)
    assert result.reasons[0] == (
        "Con sus prioridades, la luz es amarilla: con esas prioridades ninguna señal que cuenta tiene calificación; "
        "no hay evidencia de riesgo ni de que sea buena."
    )
    limitations = " ".join(missing_data_limitations(signals))
    assert "la oferta no se evaluó" in limitations
    assert "el mercado no se evaluó" in limitations


# ------------------------------------------------------------------ determinismo (R4) y errores


def test_misma_entrada_mismo_resultado():
    signals = ventana(frost=sig(55), supply=sig(30), market=INSUFFICIENT)
    first = luz(signals, DEFAULTS, basis=DEFAULT)

    for _ in range(5):
        assert luz(signals, DEFAULTS, basis=DEFAULT) == first
        assert missing_data_limitations(signals) == missing_data_limitations(signals)


@pytest.mark.parametrize(
    "signals",
    [
        ventana(frost=sig(55), supply=sig(30), market=INSUFFICIENT),
        ventana(water=sig(50), frost=sig(50)),
        ventana(heat=sig(10, critical=True), water=sig(10, critical=True)),
    ],
)
def test_el_orden_del_mapa_no_cambia_nada(signals):
    reversed_signals = dict(reversed(list(signals.items())))
    reversed_weights = dict(reversed(list(DEFAULTS.items())))

    assert luz(reversed_signals, reversed_weights, basis=DEFAULT) == luz(signals, DEFAULTS, basis=DEFAULT)
    assert missing_data_limitations(reversed_signals) == missing_data_limitations(signals)


def test_en_empate_del_minimo_el_limitante_es_el_primero_del_p0():
    assert luz(ventana(heat=sig(10, critical=True), water=sig(10, critical=True)), ALL_3).limiting_signal == "water"


def test_no_modifica_lo_que_recibe():
    signals, weights = ventana(frost=sig(55)), dict(DEFAULTS)
    before_signals, before_weights = dict(signals), dict(weights)

    luz(signals, weights, basis=DEFAULT)

    assert signals == before_signals and weights == before_weights


def test_el_resultado_es_inmutable():
    result = luz(ventana(), ALL_3)
    assert isinstance(result.reasons, tuple)
    with pytest.raises(AttributeError):
        result.light = RED  # type: ignore[misc]


@pytest.mark.parametrize("suitability", ["apto", "", "SUITABLE", None])
def test_una_aptitud_desconocida_da_value_error(suitability):
    with pytest.raises(ValueError):
        luz(ventana(), ALL_3, suitability=suitability)


@pytest.mark.parametrize("suitability", [SUITABLE, NOT_SUITABLE])
@pytest.mark.parametrize("basis", ["agricultor", "", "FARMER", None])
def test_una_base_de_pesos_desconocida_da_value_error(suitability, basis):
    with pytest.raises(ValueError):
        luz(ventana(), ALL_3, suitability=suitability, basis=basis)


# ------------------------------------------------------------------ integrado: curva real (HU-196) y semáforo


@pytest.fixture(scope="module")
def umbrales():
    """`thresholds.yaml` 1.1.0, leído con su cargador: los cortes reales, no calificaciones a mano (1.1.0 solo cambió la
    nota del mercado, decisión 17: los cortes son los de 1.0.0)."""
    thresholds = load_thresholds()
    assert thresholds.version == "1.1.0"
    return thresholds


def ventana_real(umbrales, water_pct: float, frost_pct: float) -> dict[str, SignalScore]:
    """El agua y la helada calificadas con su curva real; calor y suelo sin ficha y oferta y mercado sin curva:
    `insufficient_data`, como los da `score_signal` (no cambian la luz)."""
    signals = {"water": score_signal("water", water_pct, umbrales), "frost": score_signal("frost", frost_pct, umbrales)}
    signals |= {name: score_signal(name, None, umbrales) for name in ("heat", "soil")}
    signals |= {name: score_signal(name, 10.0, umbrales) for name in ("supply", "market")}
    return signals


def test_integrado_helada_justo_en_el_corte_critico_da_amarillo_sin_alto_riesgo(umbrales):
    """Helada en el 40 % de los años: la curva da 40 (`moderate`), justo en `critical_below = 40`, no crítica. Con el
    peso por defecto (4) cuenta como desfavorable: amarillo y otra ventana. Agua al 100 %: 100."""
    signals = ventana_real(umbrales, water_pct=100, frost_pct=40)
    assert (signals["frost"].score, signals["frost"].level, signals["frost"].critical) == (40, "moderate", False)

    result = luz(signals, DEFAULTS, basis=DEFAULT)

    assert core(result) == (YELLOW, OTHER_WINDOW, "frost", False)


def test_integrado_helada_justo_debajo_del_corte_critico_da_rojo_y_alto_riesgo(umbrales):
    """Helada en el 41 % de los años: la curva da 39,3, que se muestra 39: crítica. Rojo, otra ventana, alto riesgo."""
    signals = ventana_real(umbrales, water_pct=100, frost_pct=41)
    assert (signals["frost"].score, signals["frost"].level, signals["frost"].critical) == (39, "unfavorable", True)

    result = luz(signals, DEFAULTS, basis=DEFAULT)

    assert core(result) == (RED, OTHER_WINDOW, "frost", True)
    assert "la helada" in text(result) and "es crítica" in text(result)


@pytest.mark.parametrize(
    ("water_pct", "score", "expected"),
    [
        # 50 % de cobertura: 20, justo en `critical_below = 20`: desfavorable sin ser crítica, una sola: amarillo.
        (50, 20, (YELLOW, OTHER_WINDOW, "water", False)),
        # 48 %: 19,2, que se muestra 19: crítica. Rojo y alto riesgo.
        (48, 19, (RED, OTHER_WINDOW, "water", True)),
    ],
)
def test_integrado_agua_en_su_corte_critico(umbrales, water_pct, score, expected):
    signals = ventana_real(umbrales, water_pct=water_pct, frost_pct=0)
    assert (signals["water"].score, signals["water"].critical) == (score, score < 20)
    assert signals["frost"].score == 100

    assert core(luz(signals, DEFAULTS, basis=DEFAULT)) == expected


def test_una_frase_ya_escrita_reemplaza_la_de_sin_datos_sin_repetirse():
    signals = ventana(water=INSUFFICIENT, frost=INSUFFICIENT)
    phrase = "Esta versión todavía no evalúa el agua."
    limitations = missing_data_limitations(signals, {"water": phrase})
    assert limitations == (phrase, "Sin datos para la zona: la helada no se evaluó.")
