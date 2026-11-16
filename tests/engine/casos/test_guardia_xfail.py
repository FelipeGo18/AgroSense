"""Guardia de los casos que esperan otra HU (HU-121). Recorre con `ast` los casos de referencia y falla si alguno usa `skip`,
`skipif` o un `xfail` que no sea `strict=True` con un `reason` que empiece por «espera HU-»: un caso pendiente nunca se salta ni se
olvida en silencio (con `strict`, cuando su HU lo hace pasar, la prueba falla hasta que se quite la marca)."""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
ARCHIVOS = sorted((RAIZ / "tests" / "engine" / "casos").glob("*.py")) + [RAIZ / "tests" / "accounts" / "test_casos_referencia.py"]


def marcas_prohibidas(codigo: str, nombre: str = "<codigo>") -> list[str]:
    """Los problemas de `codigo` (texto de un módulo): `skip`, `skipif`, y `xfail` sin `strict=True` o sin `reason` «espera HU-…»."""
    problemas = []
    arbol = ast.parse(codigo)
    llamados = {id(n.func) for n in ast.walk(arbol) if isinstance(n, ast.Call)}  # los `func` de una llamada se revisan en la llamada
    for nodo in ast.walk(arbol):
        # `xfail` sin llamada: `@pytest.mark.xfail`, `pytestmark = pytest.mark.xfail`, `pytest.param(..., marks=pytest.mark.xfail)`.
        if isinstance(nodo, ast.Attribute) and nodo.attr == "xfail" and id(nodo) not in llamados:
            problemas.append(f"{nombre}:{nodo.lineno}: `xfail` sin llamada: no puede llevar `strict=True` ni `reason`")
        if isinstance(nodo, ast.Name) and nodo.id == "xfail" and id(nodo) not in llamados:
            problemas.append(f"{nombre}:{nodo.lineno}: `xfail` sin llamada: no puede llevar `strict=True` ni `reason`")
        # `pytest.skip(...)`, `pytest.mark.skip`, `pytest.mark.skipif(...)`, `@mark.xfail(...)`, `pytest.xfail(...)`, `pytest.importorskip`.
        if isinstance(nodo, ast.Attribute) and nodo.attr in ("skip", "skipif", "importorskip"):
            problemas.append(f"{nombre}:{nodo.lineno}: `{nodo.attr}` no se usa en los casos de referencia")
        if isinstance(nodo, ast.Name) and nodo.id in ("skip", "skipif"):
            problemas.append(f"{nombre}:{nodo.lineno}: `{nodo.id}` no se usa en los casos de referencia")
        if isinstance(nodo, ast.Call) and getattr(nodo.func, "attr", getattr(nodo.func, "id", None)) == "xfail":
            palabras = {k.arg: k.value for k in nodo.keywords}
            estricto = palabras.get("strict")
            if not (isinstance(estricto, ast.Constant) and estricto.value is True):
                problemas.append(f"{nombre}:{nodo.lineno}: `xfail` sin `strict=True`")
            razon = palabras.get("reason")
            if not (isinstance(razon, ast.Constant) and isinstance(razon.value, str) and razon.value.startswith("espera HU-")):
                problemas.append(f"{nombre}:{nodo.lineno}: el `reason` de `xfail` tiene que empezar por «espera HU-»")
    return problemas


def test_los_casos_de_referencia_existen_y_se_recorren():
    assert len(ARCHIVOS) >= 7 and all(a.exists() for a in ARCHIVOS)  # no pasa recorriendo nada


def test_ningun_caso_de_referencia_usa_skip_ni_xfail_sin_strict_ni_sin_espera_hu():
    problemas = [
        problema
        for archivo in ARCHIVOS
        for problema in marcas_prohibidas(archivo.read_text(encoding="utf-8"), archivo.relative_to(RAIZ).as_posix())
    ]
    assert not problemas, "\n".join(problemas)


def test_los_xfail_de_las_cuentas_esperan_hu_167_y_son_estrictos():
    # Los dos casos pendientes de hoy (progreso de las temporadas, P1): se cuentan para que quitar uno no pase sin que se vea.
    codigo = (RAIZ / "tests" / "accounts" / "test_casos_referencia.py").read_text(encoding="utf-8")
    marcas = [n for n in ast.walk(ast.parse(codigo)) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "xfail"]
    assert [{k.arg: k.value for k in m.keywords}["reason"].value for m in marcas if len(m.keywords) == 2] == ["espera HU-167 (P1)"] * 2
    assert marcas_prohibidas(codigo) == []


def test_la_guardia_detecta_cada_marca_prohibida():
    malos = [
        "import pytest\n@pytest.mark.skip(reason='x')\ndef test_a(): ...",
        "import pytest\n@pytest.mark.skipif(True, reason='x')\ndef test_a(): ...",
        "import pytest\ndef test_a():\n    pytest.skip('x')",
        "import pytest\n@pytest.mark.xfail(reason='espera HU-1')\ndef test_a(): ...",
        "import pytest\n@pytest.mark.xfail(strict=False, reason='espera HU-1')\ndef test_a(): ...",
        "import pytest\n@pytest.mark.xfail(strict=True, reason='pendiente')\ndef test_a(): ...",
        "import pytest\n@pytest.mark.xfail(strict=True)\ndef test_a(): ...",
        "import pytest\n@pytest.mark.xfail\ndef test_a(): ...",
        "import pytest\npytestmark = pytest.mark.xfail",
        "import pytest\n@pytest.mark.parametrize('x', [pytest.param(1, marks=pytest.mark.xfail)])\ndef test_a(x): ...",
        "from pytest import xfail\n@xfail\ndef test_a(): ...",
    ]
    for codigo in malos:
        assert marcas_prohibidas(codigo), codigo
    bueno = "import pytest\n@pytest.mark.xfail(strict=True, reason='espera HU-167 (P1)')\ndef test_a(): ..."
    assert marcas_prohibidas(bueno) == []
