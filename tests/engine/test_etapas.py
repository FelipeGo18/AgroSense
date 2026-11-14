"""La etapa por calendario (HU-220) y que el motor no conozca la web (R6)."""

import ast
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.engine.stages import StageSpan, stage_today

# Papa: FAO-56, fila «Idaho, USA» (catalog/crops.yaml).
PAPA = [StageSpan("initial", 45), StageSpan("development", 30), StageSpan("mid", 70), StageSpan("late", 20)]
SOWN = date(2026, 8, 2)


def test_el_dia_de_la_siembra_es_el_comienzo_de_la_etapa_inicial():
    state = stage_today(PAPA, SOWN, SOWN)
    assert (state.stage, state.stage_progress_pct, state.days_since_sowing) == ("initial", 0.0, 0)
    assert state.harvest_estimate == SOWN + timedelta(days=165)
    assert state.stage_method == "calendar" and not state.harvest_due


def test_cada_etapa_empieza_el_dia_que_termina_la_anterior():
    assert stage_today(PAPA, SOWN, SOWN + timedelta(days=44)).stage == "initial"
    assert stage_today(PAPA, SOWN, SOWN + timedelta(days=45)).stage == "development"
    middle = stage_today(PAPA, SOWN, SOWN + timedelta(days=75 + 35))
    assert (middle.stage, middle.stage_progress_pct) == ("mid", 50.0)


def test_pasada_la_cosecha_estimada_queda_en_la_ultima_etapa_y_lo_dice():
    state = stage_today(PAPA, SOWN, SOWN + timedelta(days=200))
    assert (state.stage, state.stage_progress_pct, state.harvest_due) == ("late", 100.0, True)


def test_sin_etapas_no_hay_etapa_ni_cosecha_estimada():
    state = stage_today([], SOWN, SOWN + timedelta(days=10))
    assert (state.stage, state.harvest_estimate, state.days_since_sowing) == (None, None, 10)


def test_mismos_datos_mismo_resultado():
    assert stage_today(PAPA, SOWN, date(2026, 10, 1)) == stage_today(PAPA, SOWN, date(2026, 10, 1))


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
