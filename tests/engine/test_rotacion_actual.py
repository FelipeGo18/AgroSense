"""HU-223 (motor): la rotación actual como referencia. Valores esperados escritos a mano, antes del código."""

import pytest

import backend.engine.rotations.current as current
import backend.engine.rotations.ranking as ranking
from backend.engine.rotations.current import (
    NO_CURRENT_LIMITATION,
    current_sequence,
    drop_current,
    truncation_limitation,
    vs_current,
)
from backend.engine.rotations.ranking import CycleScores, score_strategy
from backend.engine.rotations.soil_health import Criterion
from backend.engine.signal_score import SignalScore

CRITERIOS = ("water", "soil", "income", "risk")


# --- current_sequence ---


@pytest.mark.parametrize(
    ("cultivos", "ciclos", "esperado"),
    [
        (["papa", "arveja"], 3, ("papa", "arveja", "papa")),
        (["papa", "avena_vicia", "arveja"], 3, ("papa", "avena_vicia", "arveja")),
        (["papa", "avena_vicia", "arveja"], 2, ("papa", "avena_vicia")),
        (["papa", "arveja"], 2, ("papa", "arveja")),
        # El contrato responde 422 con menos de 2 cultivos (`current_crop_ids`); el motor lo trata igual por si lo llama otra ruta.
        (["papa"], 3, ("papa", "papa", "papa")),
    ],
)
def test_la_secuencia_actual_tiene_exactamente_los_ciclos_pedidos(cultivos, ciclos, esperado):
    assert current_sequence(cultivos, ciclos).crop_ids == esperado


@pytest.mark.parametrize("vacia", [None, []])
@pytest.mark.parametrize("ciclos", [2, 3])
def test_sin_cultivos_no_hay_referencia(vacia, ciclos):
    assert current_sequence(vacia, ciclos) is None


@pytest.mark.parametrize("ciclos", [1, 4])
def test_ciclos_distintos_de_2_o_3_lanzan_value_error(ciclos):
    with pytest.raises(ValueError):
        current_sequence(["papa", "arveja"], ciclos)


def test_la_secuencia_actual_no_muta_la_entrada_y_devuelve_tupla():
    entrada = ["papa", "arveja"]
    resultado = current_sequence(entrada, 3)
    assert entrada == ["papa", "arveja"]
    assert isinstance(resultado.crop_ids, tuple)


def test_truncated_es_true_solo_si_hay_mas_cultivos_que_ciclos():
    recortada = current_sequence(["papa", "avena_vicia", "arveja"], 2)
    assert recortada.crop_ids == ("papa", "avena_vicia")
    assert recortada.truncated is True
    repetida = current_sequence(["papa", "arveja"], 3)
    assert repetida.crop_ids == ("papa", "arveja", "papa")
    assert repetida.truncated is False
    assert current_sequence(["papa", "avena_vicia", "arveja"], 3).truncated is False


NOMBRES = {"papa": "papa", "avena_vicia": "avena con vicia", "arveja": "arveja"}


def test_el_aviso_del_recorte_nombra_los_cultivos_comparados():
    texto = truncation_limitation(["papa", "avena_vicia", "arveja"], 2, NOMBRES)
    assert texto == "Su rotación tiene 3 cultivos; con 2 ciclos se compararon papa y avena con vicia"


# El contrato admite hasta 3 cultivos en `current_crop_ids`: este caso de 4 solo prueba cómo se unen tres nombres.
def test_el_aviso_del_recorte_con_tres_ciclos_une_con_coma_y_y():
    texto = truncation_limitation(["papa", "avena_vicia", "arveja", "maiz"], 3, NOMBRES)
    assert texto == "Su rotación tiene 4 cultivos; con 3 ciclos se compararon papa, avena con vicia y arveja"


@pytest.mark.parametrize("entrada", [["papa", "arveja"], ["papa", "avena_vicia", "arveja"], [], None])
def test_sin_recorte_o_sin_cultivos_no_hay_aviso(entrada):
    assert truncation_limitation(entrada, 3, NOMBRES) is None


def test_un_cultivo_sin_nombre_se_muestra_con_su_crop_id():
    texto = truncation_limitation(["papa", "cebolla_larga", "arveja"], 2, NOMBRES)
    assert texto == "Su rotación tiene 3 cultivos; con 2 ciclos se compararon papa y cebolla_larga"


# --- drop_current ---

CANDIDATAS = [("arveja", "papa", "maiz"), ("papa", "arveja", "papa"), ("papa", "arveja", "haba")]


def test_drop_current_quita_solo_la_igual_y_conserva_el_orden():
    resultado = drop_current(CANDIDATAS, ("papa", "arveja", "papa"))
    assert resultado == (("arveja", "papa", "maiz"), ("papa", "arveja", "haba"))


def test_drop_current_no_quita_los_mismos_cultivos_en_otro_orden():
    candidatas = [("arveja", "papa", "papa"), ("papa", "papa", "arveja")]
    assert drop_current(candidatas, ("papa", "arveja", "papa")) == tuple(candidatas)


def test_drop_current_sin_actual_devuelve_todas():
    assert drop_current(CANDIDATAS, None) == tuple(CANDIDATAS)


def test_drop_current_compara_listas_como_tuplas_y_devuelve_tuplas():
    candidatas = [["arveja", "papa", "maiz"], ["papa", "arveja", "papa"]]
    resultado = drop_current(candidatas, ["papa", "arveja", "papa"])
    assert resultado == (("arveja", "papa", "maiz"),)
    assert isinstance(resultado, tuple)
    assert all(isinstance(c, tuple) for c in resultado)


def test_drop_current_si_ninguna_es_igual_no_cambia_nada():
    assert drop_current(CANDIDATAS, ("maiz", "maiz", "maiz")) == tuple(CANDIDATAS)


def test_drop_current_no_muta_la_entrada():
    candidatas = [("arveja", "papa", "maiz"), ("papa", "arveja", "papa")]
    copia = list(candidatas)
    drop_current(candidatas, ("papa", "arveja", "papa"))
    assert candidatas == copia


# --- vs_current ---

SUGERIDA = {"water": 74, "soil": 88, "income": 60, "risk": 71}
ACTUAL = {"water": 68, "soil": 50, "income": 69, "risk": 59}


def test_vs_current_reproduce_el_ejemplo_del_contrato():
    assert vs_current(SUGERIDA, 76, ACTUAL, 61) == {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15}


def test_vs_current_positivo_es_mejor_y_negativo_es_peor():
    resultado = vs_current({"water": 50, "soil": 50, "income": 50, "risk": 50}, 50, {"water": 40, "soil": 60, "income": 50, "risk": 50}, 50)
    assert resultado == {"water": 10, "soil": -10, "income": 0, "risk": 0, "total": 0}


@pytest.mark.parametrize("criterio", CRITERIOS)
def test_un_criterio_nulo_en_la_sugerida_da_solo_esa_clave_nula(criterio):
    sugerida = {**SUGERIDA, criterio: None}
    resultado = vs_current(sugerida, 76, ACTUAL, 61)
    esperado = {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15}
    esperado[criterio] = None
    assert resultado == esperado


@pytest.mark.parametrize("criterio", CRITERIOS)
def test_un_criterio_nulo_en_la_actual_da_solo_esa_clave_nula(criterio):
    actual = {**ACTUAL, criterio: None}
    resultado = vs_current(SUGERIDA, 76, actual, 61)
    esperado = {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15}
    esperado[criterio] = None
    assert resultado == esperado


def test_total_nulo_en_la_sugerida_o_en_la_actual_da_total_nulo():
    esperado = {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": None}
    assert vs_current(SUGERIDA, None, ACTUAL, 61) == esperado
    assert vs_current(SUGERIDA, 76, ACTUAL, None) == esperado


def test_sin_rotacion_actual_vs_current_es_nulo_entero():
    assert vs_current(SUGERIDA, 76, None, None) is None
    assert vs_current(SUGERIDA, 76, None, 61) is None


def test_una_clave_que_falta_cuenta_como_nula():
    resultado = vs_current({"water": 74, "soil": 88, "income": 60}, 76, {"water": 68, "income": 69, "risk": 59}, 61)
    assert resultado == {"water": 6, "soil": None, "income": -9, "risk": None, "total": 15}


def test_vs_current_es_determinista_y_trae_las_cinco_claves():
    primero = vs_current(SUGERIDA, 76, ACTUAL, 61)
    segundo = vs_current(SUGERIDA, 76, ACTUAL, 61)
    assert primero == segundo
    assert set(primero) == {*CRITERIOS, "total"}


def test_vs_current_no_muta_las_entradas():
    sugerida, actual = dict(SUGERIDA), dict(ACTUAL)
    vs_current(sugerida, 76, actual, 61)
    assert sugerida == SUGERIDA
    assert actual == ACTUAL


# --- la limitación ---


def test_la_limitacion_sin_rotacion_actual_tiene_el_texto_exacto():
    assert NO_CURRENT_LIMITATION == "Sin rotación actual: no hay una referencia para comparar las estrategias"


def test_la_limitacion_menciona_la_rotacion_actual():
    # tests/engine/casos/test_estrategias.py busca «actual» en las limitaciones.
    assert "actual" in NO_CURRENT_LIMITATION.lower()


# --- el puntaje de la actual sale de `score_strategy` (HU-082) ---


def test_los_criterios_de_la_actual_son_los_del_ranking():
    assert current.CRITERIA is ranking.CRITERIA


def test_vs_current_con_el_puntaje_de_score_strategy_de_las_dos():
    """Datos de EJEMPLO inventados para la prueba (R5), no salen de ningún dataset.

    Sugerida (papa, arveja, descanso), con suelo bueno: agua (80 + 71) / 2 = 75,5 -> 76; suelo 88; ingreso
    (60 + 59,5 + 0) / 3 -> 40; riesgo 55; total (76 + 88 + 40 + 55) / 4 = 64,75 -> 65.
    Actual (dos ciclos), con suelo pobre: agua 55; suelo 25; ingreso (50 + 40) / 2 = 45; riesgo 40; total
    (55 + 25 + 45 + 40) / 4 = 41,25 -> 41. El ingreso de cada ciclo (HU-241) es el porcentaje de años con mejor precio en
    el mes de su cosecha (`precio`); la oferta y el mercado siguen aquí solo para el riesgo.
    """

    def senales(water, supply, market=None, precio=None):
        def una(valor):
            nivel = "favorable" if valor >= 70 else "moderate" if valor >= 40 else "unfavorable"
            return SignalScore("available", valor, nivel, False)

        sin_dato = SignalScore("insufficient_data", None, None, False)
        valores = {"water": water, "frost": 90, "heat": 95, "soil": 70, "supply": supply, "market": market}
        return CycleScores("crop", {n: sin_dato if v is None else una(v) for n, v in valores.items()}, precio)

    def salud(*niveles):
        nombres = ("nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion")
        return {n: Criterion("available" if v else "insufficient_data", v, (), (), ()) for n, v in zip(nombres, niveles, strict=True)}

    pesos_senales = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
    prioridades = {"water": 3, "soil": 3, "income": 3, "risk": 3}
    sugerida = score_strategy(
        ("papa", "arveja", "descanso"),
        (senales(80, 60, precio=60), senales(71, 55, 64, precio=59.5), CycleScores("fallow", None)),
        salud("favorable", "favorable", "favorable", "moderate", None),
        pesos_senales,
        prioridades,
    )
    actual = score_strategy(
        ("papa", "papa"),
        (senales(60, 50, precio=50), senales(50, 40, 40, precio=40)),
        salud("unfavorable", "moderate", "unfavorable", "moderate", None),
        pesos_senales,
        prioridades,
    )
    assert dict(sugerida.scores) == {"water": 76, "soil": 88, "income": 40, "risk": 55}
    assert sugerida.total_score == 65
    assert dict(actual.scores) == {"water": 55, "soil": 25, "income": 45, "risk": 40}
    assert actual.total_score == 41
    resultado = vs_current(sugerida.scores, sugerida.total_score, actual.scores, actual.total_score)
    assert resultado == {"water": 21, "soil": 63, "income": -5, "risk": 15, "total": 24}
