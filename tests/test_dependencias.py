"""Quién importa a quién (revisión de Felipe del PR #12): la API no importa el pipeline, el pipeline no importa el
backend y lo común (`common/`) no importa ninguno de los dos. Así ninguno queda amarrado al otro."""

import ast
from pathlib import Path

import pytest


def imported_packages(folder: str) -> dict[str, set[str]]:
    """Por archivo, los paquetes de primer nivel que importa (`backend`, `pipeline`, `common`...)."""
    found = {}
    for path in Path(folder).rglob("*.py"):
        packages = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                packages |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                packages.add(node.module.split(".")[0])
        found[str(path)] = packages
    return found


@pytest.mark.parametrize(
    ("folder", "forbidden"),
    [("backend/api", "pipeline"), ("pipeline", "backend"), ("common", "backend"), ("common", "pipeline")],
)
def test_nadie_importa_lo_que_no_le_toca(folder, forbidden):
    offenders = sorted(path for path, packages in imported_packages(folder).items() if forbidden in packages)
    assert not offenders, f"{folder} importa {forbidden}: {offenders}"


def test_las_actualizaciones_de_precios_no_leen_la_configuracion_de_la_api():
    """El servicio `market` no usa la base de datos: su configuración sale de `pipeline/settings.py`, que no la pide."""
    tree = ast.parse(Path("backend/market/updates.py").read_text(encoding="utf-8"))
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "backend.config.settings" not in modules and "pipeline.settings" in modules
