"""HU-081, PR C: la matriz de 8 x 8 de HU-062 contra el motor (escrita antes del código, HU-121).

Para cada par (cultivo anterior, ciclo siguiente) se evalúan los filtros reales de `catalog/rotation_rules.yaml` con las
fichas reales de `catalog/crops.yaml`. Supuesto por confirmar: el descanso como ciclo anterior es un `previous_crop_ids`
de un solo elemento, y no excluye nada (nota 3 de HU-062).
"""

from pathlib import Path

import yaml

from backend.engine.rotations.candidates import CropInfo
from backend.engine.rotations.rules import FilterRule, rule_motives

RAIZ = Path(__file__).resolve().parents[2] / "catalog"

# Copiada de la «Matriz esperada» de HU-062 (specs/epicas/EP-06-catalogo-agronomico.md, catálogo 0.1.0):
# fila = ciclo anterior, columna = ciclo siguiente, X = excluye, . = pasa.
ORDEN = ("papa", "arveja", "haba", "maiz", "zanahoria", "cebolla_bulbo", "avena_vicia", "descanso")
MATRIZ = {
    "papa": "X.......",
    "arveja": ".XX.....",
    "haba": ".XX.....",
    "maiz": "...X..X.",
    "zanahoria": "....X...",
    "cebolla_bulbo": ".....X..",
    "avena_vicia": "...X..X.",
    "descanso": "........",
}


def _cultivos() -> dict[str, CropInfo]:
    fichas = yaml.safe_load((RAIZ / "crops.yaml").read_text(encoding="utf-8"))["crops"]
    return {
        f["crop_id"]: CropInfo(
            f["crop_id"],
            f["kind"]["v"],
            f["family"]["v"] if "family" in f else None,
            tuple(f.get("secondary_families", {}).get("v") or ()),
        )
        for f in fichas
    }


def _filtros() -> list[FilterRule]:
    filas = yaml.safe_load((RAIZ / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
    return [
        FilterRule(r["rule_id"], r["condition_type"], r["params"], r["reason_template"], r["source_id"])
        for r in filas
        if r["kind"] == "filter"
    ]


CULTIVOS = _cultivos()
FILTROS = _filtros()


def test_la_matriz_y_el_catalogo_tienen_los_mismos_8_cultivos():
    assert set(ORDEN) == set(CULTIVOS)
    assert len(ORDEN) == 8
    assert all(len(fila) == 8 for fila in MATRIZ.values())
    assert FILTROS  # sin filtros la matriz no probaría nada


def test_los_64_pares_excluyen_exactamente_donde_la_tabla_dice_x():
    pares = [(a, s) for a in ORDEN for s in ORDEN]
    assert len(pares) == 64
    for anterior, siguiente in pares:
        esperado = MATRIZ[anterior][ORDEN.index(siguiente)] == "X"
        motivos = rule_motives((siguiente,), [anterior], CULTIVOS, FILTROS)
        assert bool(motivos) == esperado, f"par {anterior} -> {siguiente}: la tabla dice {'X' if esperado else '.'}, el motor dio {motivos}"
        assert all(m.kind == "rule" and m.cycle == 1 for m in motivos), f"par {anterior} -> {siguiente}"


def test_la_matriz_tiene_las_x_que_se_esperan():
    """Control: sin esto, una tabla vacía de X haría pasar la prueba de arriba con un motor que nunca excluye."""
    assert sum(fila.count("X") for fila in MATRIZ.values()) == 11
    assert sum(len(rule_motives((s,), [a], CULTIVOS, FILTROS)) > 0 for a in ORDEN for s in ORDEN) == 11
