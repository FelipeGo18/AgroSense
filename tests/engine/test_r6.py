"""R6: el motor no conoce la web, ni la base, ni los archivos, ni los DataFrames (specs/01-reglas.md)."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest


def test_el_motor_no_importa_la_web_ni_la_base_ni_abre_archivos():
    """R6: backend/engine/ no importa fastapi ni sqlalchemy, no llama a open() y no lee rutas."""
    forbidden = {"fastapi", "sqlalchemy", "starlette", "polars", "backend.api", "backend.db", "backend.dataset", "backend.accounts"}
    for path in Path("backend/engine").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            for name in names:
                assert not any(name == f or name.startswith(f + ".") for f in forbidden), f"{path}: importa {name}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "open", f"{path}: abre un archivo"


ENGINE_MODULES = sorted(
    "backend.engine." + path.stem
    for path in Path(__file__).resolve().parents[2].joinpath("backend/engine").glob("*.py")
    if path.stem != "__init__"
)


@pytest.mark.parametrize("module", ENGINE_MODULES)
def test_importar_el_motor_no_carga_la_web_el_dataset_ni_la_configuracion(module):
    """R6 en ejecución, para cada módulo del motor: en un intérprete limpio, importarlo no carga (ni de forma transitiva)
    la API, el dataset, FastAPI, SQLAlchemy, Polars, la configuración (`backend.config.thresholds` lee archivos; los
    umbrales se importan solo para el tipado) ni yaml."""
    forbidden = ("backend.api", "backend.dataset", "backend.config", "fastapi", "sqlalchemy", "polars", "yaml")
    code = (
        f"import sys; import {module}; "
        f"print(','.join(m for m in {forbidden!r} if any(k == m or k.startswith(m + '.') for k in sys.modules)))"
    )
    root = Path(__file__).resolve().parents[2]
    # El código es una constante de esta prueba (el módulo sale de backend/engine/), no una entrada externa.
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=True)  # noqa: S603
    assert result.stdout.strip() == "", f"{module} carga {result.stdout.strip()}"
