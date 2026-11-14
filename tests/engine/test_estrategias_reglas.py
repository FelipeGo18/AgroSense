"""HU-081, PR B, fase 1: motivos `rule` de las reglas `filter` (R3; specs/02-contratos.md, «Reglas de rotación como
datos»). Escritas antes del código (HU-121).

Las reglas reales se leen aquí de `catalog/rotation_rules.yaml` (el motor no lee archivos, R6). La regla
`ejemplo_retorno` es DE EJEMPLO (R5): el catálogo hoy solo usa `family_return_min_cycles` como `health`.
Supuestos por confirmar: (S1) `{cycles}` es el número de ciclos de otras familias entre las dos apariciones; (S2) los
`previous_crop_ids` van del más reciente al más antiguo y, para `family_return_min_cycles`, cuentan como ciclos
previos en ese orden; (S3) un descanso cuenta como un ciclo sin la familia.
"""

from pathlib import Path

import yaml

from backend.engine.rotations.candidates import CropInfo
from backend.engine.rotations.rules import FilterRule, rule_motives

RAIZ = Path(__file__).resolve().parents[2] / "catalog"


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


def _reglas_reales() -> list[FilterRule]:
    filas = yaml.safe_load((RAIZ / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
    return [
        FilterRule(r["rule_id"], r["condition_type"], r["params"], r["reason_template"], r["source_id"])
        for r in filas
        if r["kind"] == "filter"
    ]


EJEMPLO_RETORNO = FilterRule(  # DE EJEMPLO (R5): no es una regla del catálogo.
    "ejemplo_retorno",
    "family_return_min_cycles",
    {"family": "Leguminosae", "min_cycles": 2},
    "La familia {family} vuelve al terreno después de {cycles} ciclos de otras familias",
    "ejemplo",
)
CULTIVOS = _cultivos()
REALES = _reglas_reales()


def _ids(motivos):
    return [(m.cycle, m.rule_id) for m in motivos]


def test_las_reglas_filter_reales_son_familia_seguida_y_papa_seguida():
    assert sorted(r.rule_id for r in REALES) == ["familia_seguida", "papa_seguida"]


def test_familia_seguida_arveja_haba_da_motivo_en_el_ciclo_2():
    motivos = rule_motives(("arveja", "haba", "maiz"), [], CULTIVOS, REALES)
    assert _ids(motivos) == [(2, "familia_seguida")]
    m = motivos[0]
    assert m.kind == "rule"
    assert m.source_ids == ("psu_rotacion_familias",)
    assert m.reason == "Repite la familia Leguminosae en dos ciclos seguidos"


def test_sin_familia_repetida_no_hay_motivos():
    assert rule_motives(("arveja", "maiz", "papa"), [], CULTIVOS, REALES) == []


def test_papa_tras_papa_anterior_da_familia_seguida_y_papa_seguida_en_el_ciclo_1():
    motivos = rule_motives(("papa", "maiz", "zanahoria"), ["papa"], CULTIVOS, REALES)
    assert _ids(motivos) == [(1, "familia_seguida"), (1, "papa_seguida")]
    assert motivos[0].source_ids == ("psu_rotacion_familias",)
    assert motivos[1].source_ids == ("ica_punta_morada",)
    assert all("Solanaceae" in m.reason for m in motivos)


def test_papa_tras_papa_dentro_de_la_estrategia_da_las_dos_reglas_en_el_ciclo_2():
    motivos = rule_motives(("papa", "papa", "maiz"), [], CULTIVOS, REALES)
    assert _ids(motivos) == [(2, "familia_seguida"), (2, "papa_seguida")]


def test_solo_cuenta_el_anterior_mas_reciente_el_primero_de_la_lista():
    sin_motivo = rule_motives(("papa", "maiz", "haba"), ["maiz", "papa"], CULTIVOS, REALES)
    assert sin_motivo == []
    # Control: con papa de más reciente, la misma secuencia sí da motivo (el orden de la lista importa).
    con_motivo = rule_motives(("papa", "maiz", "haba"), ["papa", "maiz"], CULTIVOS, REALES)
    assert _ids(con_motivo) == [(1, "familia_seguida"), (1, "papa_seguida")]


def test_papa_seguida_solo_vale_para_solanaceae():
    motivos = rule_motives(("maiz", "avena_vicia", "papa"), [], CULTIVOS, REALES)
    assert _ids(motivos) == [(2, "familia_seguida")]
    assert "Gramineae" in motivos[0].reason


def test_secondary_families_no_cuenta_en_familia_seguida():
    assert rule_motives(("avena_vicia", "arveja", "maiz"), [], CULTIVOS, REALES) == []
    # La vicia de avena_vicia es Leguminosae, pero `familia_seguida` solo compara `family` (Gramineae): con la arveja no repite.
    assert rule_motives(("arveja", "avena_vicia", "papa"), [], CULTIVOS, REALES) == []


def test_retorno_antes_de_min_cycles_da_motivo_en_el_ciclo_3():
    motivos = rule_motives(("arveja", "maiz", "haba"), [], CULTIVOS, [EJEMPLO_RETORNO])
    assert _ids(motivos) == [(3, "ejemplo_retorno")]
    assert motivos[0].source_ids == ("ejemplo",)
    assert motivos[0].reason == EJEMPLO_RETORNO.reason_template.format(family="Leguminosae", cycles=1)  # S1


def test_sin_retorno_de_la_familia_no_hay_motivo():
    assert rule_motives(("arveja", "maiz", "zanahoria"), [], CULTIVOS, [EJEMPLO_RETORNO]) == []


def test_el_retorno_cuenta_secondary_families():
    motivos = rule_motives(("avena_vicia", "maiz", "arveja"), [], CULTIVOS, [EJEMPLO_RETORNO])
    assert _ids(motivos) == [(3, "ejemplo_retorno")]


def test_el_retorno_cuenta_los_cultivos_anteriores_como_ciclos_previos():
    """S2: más reciente primero. Zanahoria (reciente) y arveja (antigua): la arveja vuelve tras 1 ciclo."""
    motivos = rule_motives(("haba", "maiz", "papa"), ["zanahoria", "arveja"], CULTIVOS, [EJEMPLO_RETORNO])
    assert _ids(motivos) == [(1, "ejemplo_retorno")]
    assert motivos[0].reason == EJEMPLO_RETORNO.reason_template.format(family="Leguminosae", cycles=1)


def test_el_retorno_tras_min_cycles_de_otras_familias_no_da_motivo():
    """S2: arveja es la más antigua, con 2 ciclos de otras familias (zanahoria, maiz) antes de la haba."""
    previos = ["maiz", "zanahoria", "arveja"]
    assert rule_motives(("haba", "papa", "maiz"), previos, CULTIVOS, [EJEMPLO_RETORNO]) == []


def test_el_descanso_no_es_familia_seguida_y_corta_la_sucesion():
    assert rule_motives(("papa", "descanso", "papa"), [], CULTIVOS, REALES) == []
    assert rule_motives(("papa", "descanso", "papa"), ["maiz"], CULTIVOS, REALES) == []


def test_el_descanso_cuenta_como_un_ciclo_sin_la_familia_en_el_retorno():
    """S3."""
    motivos = rule_motives(("arveja", "descanso", "haba"), [], CULTIVOS, [EJEMPLO_RETORNO])
    assert _ids(motivos) == [(3, "ejemplo_retorno")]
    assert motivos[0].reason == EJEMPLO_RETORNO.reason_template.format(family="Leguminosae", cycles=1)


def test_sin_reglas_no_hay_motivos():
    assert rule_motives(("papa", "papa", "papa"), ["papa"], CULTIVOS, []) == []


def test_los_motivos_van_por_ciclo_y_luego_por_rule_id():
    motivos = rule_motives(("papa", "papa", "papa"), ["papa"], CULTIVOS, list(reversed(REALES)))
    assert _ids(motivos) == [
        (1, "familia_seguida"),
        (1, "papa_seguida"),
        (2, "familia_seguida"),
        (2, "papa_seguida"),
        (3, "familia_seguida"),
        (3, "papa_seguida"),
    ]


def test_es_determinista():
    args = (("papa", "arveja", "haba"), ["papa"], CULTIVOS, [*REALES, EJEMPLO_RETORNO])
    primero = rule_motives(*args)
    assert primero
    assert rule_motives(*args) == primero
