"""HU-223 (motor): la rotación actual como referencia. Valores esperados escritos a mano, antes del código."""

import ast
import inspect

import pytest

import backend.engine.rotations.current as current
from backend.engine.rotations.current import NO_CURRENT_LIMITATION, current_sequence, drop_current, vs_current

CRITERIOS = ("water", "soil", "income", "risk")


# --- current_sequence ---


@pytest.mark.parametrize(
    ("cultivos", "ciclos", "esperado"),
    [
        (["papa", "arveja"], 3, ("papa", "arveja", "papa")),
        (["papa", "avena_vicia", "arveja"], 3, ("papa", "avena_vicia", "arveja")),
        (["papa", "avena_vicia", "arveja"], 2, ("papa", "avena_vicia")),
        (["papa", "arveja"], 2, ("papa", "arveja")),
        (["papa"], 3, ("papa", "papa", "papa")),
    ],
)
def test_la_secuencia_actual_tiene_exactamente_los_ciclos_pedidos(cultivos, ciclos, esperado):
    assert current_sequence(cultivos, ciclos) == esperado


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
    assert isinstance(resultado, tuple)


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


# --- R6 ---


def test_r6_current_no_importa_la_web_la_base_ni_polars_ni_abre_archivos():
    arbol = ast.parse(inspect.getsource(current))
    prohibidos = {"fastapi", "starlette", "sqlalchemy", "polars", "yaml", "backend.api", "backend.db", "backend.dataset", "backend.config"}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            nombres = [nodo.module or ""]
        else:
            nombres = []
        for nombre in nombres:
            assert not any(nombre == p or nombre.startswith(p + ".") for p in prohibidos), f"importa {nombre}"
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
            assert nodo.func.id != "open", "abre un archivo"
