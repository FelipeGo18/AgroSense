"""HU-081, decisión 6 de Felipe: una sola historia del terreno (R3, R4, R5, R6). Escritas antes del código (HU-121).

El catálogo real se lee aquí (el motor no lee archivos, R6). Supuestos por confirmar con Felipe: (S1) con
`current_crop_ids`, la historia son exactamente 3 cultivos (el máximo de `previous_crop_ids`), del más reciente al más
antiguo: se repite o se recorta; (S2) la frase de la historia supuesta va solo en los motivos cuyo par o cuya aparición anterior
cae en los cultivos anteriores del terreno, nunca en los de entre ciclos de la estrategia.
DE PRUEBA (R5): `FAMILIA_VUELVE` no es del catálogo (hoy `family_return_min_cycles` solo es `health`); cita la fuente
`criterio_equipo_2026`, que sí existe en `rotation_rules.yaml`.
"""

from pathlib import Path

import pytest
import yaml

from backend.engine.rotations.candidates import CropInfo
from backend.engine.rotations.exclusions import current_issues, filter_strategies, phase1
from backend.engine.rotations.history import HISTORY_BASES, HISTORY_TEXT, TerrainHistory, check_history, terrain_history
from backend.engine.rotations.rules import FilterRule, rule_motives
from backend.engine.rotations.soil_health import HealthRule, SoilCrop, soil_health

RAIZ = Path(__file__).resolve().parents[2] / "catalog"
FRASE = "Se supuso que antes del primer ciclo el terreno siguió su rotación actual"
SIN_ANTERIORES = "No hay cultivos anteriores del terreno: solo se revisan los ciclos de la estrategia"
# Texto literal de `familia_seguida` con la familia Leguminosae (arveja y haba son de esa familia en crops.yaml).
RAZON_LEGUMINOSAE = "Repite la familia Leguminosae en dos ciclos seguidos"


def _fichas() -> list[dict]:
    return yaml.safe_load((RAIZ / "crops.yaml").read_text(encoding="utf-8"))["crops"]


def _v(f, campo):
    return f[campo]["v"] if campo in f else None


CULTIVOS = {
    f["crop_id"]: CropInfo(f["crop_id"], _v(f, "kind"), _v(f, "family"), tuple(_v(f, "secondary_families") or ())) for f in _fichas()
}
SUELO_CULTIVOS = {
    f["crop_id"]: SoilCrop(f["crop_id"], _v(f, "kind"), _v(f, "family"), tuple(_v(f, "secondary_families") or ()), _v(f, "fixes_nitrogen"))
    for f in _fichas()
}
_FILAS = yaml.safe_load((RAIZ / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
FILTROS = [
    FilterRule(r["rule_id"], r["condition_type"], r["params"], r["reason_template"], r["source_id"])
    for r in _FILAS
    if r["kind"] == "filter"
]
SALUD = [
    HealthRule(r["rule_id"], r["criterion"], r["condition_type"], r["params"], r["levels"], r["reason_template"], r["source_id"])
    for r in _FILAS
    if r["kind"] == "health"
]
FAMILIA_VUELVE = FilterRule(  # DE PRUEBA (R5): filtro de retorno de familia; fuente existente del catálogo.
    "prueba_retorno_solanaceae",
    "family_return_min_cycles",
    {"family": "Solanaceae", "min_cycles": 3},
    "La familia {family} vuelve al terreno después de {cycles} ciclos de otras familias",
    "criterio_equipo_2026",
)
EXPLICA = lambda crop, apt: ("RAZON DE EJEMPLO", ("fuente_ejemplo_a",))  # noqa: E731  (DE EJEMPLO, no se usa: sin tmean)
SIN_RIESGO = lambda secuencia: [{} for _ in secuencia]  # noqa: E731  (DE PRUEBA: diagnósticos sin señales)


def _f1(sequence, previous, rules=FILTROS, **kw):
    """Fase 1 sin temperatura ni suelo: no hay motivos de aptitud ni de pH (solo limitaciones, R1)."""
    return phase1(tuple(sequence), previous, CULTIVOS, rules, None, None, EXPLICA, **kw)


def _reglas(m):
    return [(x.cycle, x.rule_id, x.reason) for x in m]


# ---------- terrain_history ----------


def test_las_constantes_de_la_historia_son_las_del_contrato():
    assert HISTORY_BASES == ("declared", "current_rotation", "none")
    assert HISTORY_TEXT == {"none": SIN_ANTERIORES, "current_rotation": FRASE}


def test_con_lista_declarada_la_rotacion_actual_no_se_usa():
    assert terrain_history(["papa"], ["maiz", "arveja"]) == TerrainHistory(("papa",), "declared")


def test_sin_lista_la_rotacion_actual_va_del_mas_reciente_al_mas_antiguo():
    h = terrain_history([], ["papa", "avena_vicia", "arveja"])
    assert h == TerrainHistory(("arveja", "avena_vicia", "papa"), "current_rotation")


def test_una_rotacion_actual_corta_se_repite_hasta_tres():
    assert terrain_history([], ["papa", "arveja"]) == TerrainHistory(("arveja", "papa", "arveja"), "current_rotation")


@pytest.mark.parametrize("actual", [None, []])
def test_sin_lista_ni_rotacion_actual_no_hay_cultivos_anteriores(actual):
    assert terrain_history([], actual) == TerrainHistory((), "none")


def test_la_rotacion_actual_son_siempre_exactamente_tres_cultivos():
    assert terrain_history([], ["papa"]) == TerrainHistory(("papa", "papa", "papa"), "current_rotation")
    assert terrain_history([], ["a", "b", "c", "d"]) == TerrainHistory(("d", "c", "b"), "current_rotation")


def test_la_lista_declarada_no_se_recorta():
    assert terrain_history(["a", "b", "c", "d"], ["x"]) == TerrainHistory(("a", "b", "c", "d"), "declared")


def test_terrain_history_es_determinista_y_no_muta_las_entradas():
    previous, actual = [], ["papa", "avena_vicia", "arveja"]
    a, b = terrain_history(previous, actual), terrain_history(previous, actual)
    assert a == b and a.crop_ids == b.crop_ids
    assert previous == [] and actual == ["papa", "avena_vicia", "arveja"]
    declarada = ["papa"]
    terrain_history(declarada, ["maiz"])
    assert declarada == ["papa"]


# ---------- check_history ----------


def test_check_history_acepta_las_combinaciones_validas():
    assert check_history([], "none") is None
    assert check_history(["papa"], "declared") is None
    assert check_history(["papa", "maiz"], "current_rotation") is None


@pytest.mark.parametrize(
    ("anteriores", "base"),
    [
        ([], "actual"),
        (["papa"], "actual"),
        (["papa"], "none"),
        ([], "declared"),
        ([], "current_rotation"),
    ],
)
def test_check_history_rechaza_una_base_invalida_o_que_contradice_la_lista(anteriores, base):
    with pytest.raises(ValueError):
        check_history(anteriores, base)


def test_rule_motives_y_phase1_exigen_history_basis_por_palabra_clave():
    with pytest.raises(TypeError):
        rule_motives(("arveja", "maiz", "papa"), [], CULTIVOS, FILTROS)
    with pytest.raises(TypeError):
        phase1(("arveja", "maiz", "papa"), [], CULTIVOS, FILTROS, None, None, EXPLICA)
    with pytest.raises(TypeError):
        filter_strategies([("arveja", "maiz", "papa")], [], CULTIVOS, FILTROS, None, None, EXPLICA, SIN_RIESGO)


@pytest.mark.parametrize("base", ["actual", "declared", "current_rotation"])
def test_history_basis_invalido_o_que_contradice_da_value_error_en_las_tres_funciones(base):
    # Con `[]` como anteriores, solo "none" es coherente: los tres valores de la lista rompen.
    with pytest.raises(ValueError):
        rule_motives(("arveja", "maiz", "papa"), [], CULTIVOS, FILTROS, history_basis=base)
    with pytest.raises(ValueError):
        _f1(("arveja", "maiz", "papa"), [], history_basis=base)
    with pytest.raises(ValueError):
        filter_strategies([("arveja", "maiz", "papa")], [], CULTIVOS, FILTROS, None, None, EXPLICA, SIN_RIESGO, history_basis=base)


def test_history_basis_none_con_cultivos_anteriores_da_value_error():
    with pytest.raises(ValueError):
        rule_motives(("arveja", "maiz", "papa"), ["haba"], CULTIVOS, FILTROS, history_basis="none")


# ---------- la razón del motivo `rule` ----------


def test_familia_seguida_con_historia_supuesta_lleva_la_frase_en_el_ciclo_1():
    h = terrain_history([], ["arveja", "maiz", "haba"])  # el más reciente es la haba (Leguminosae)
    assert h == TerrainHistory(("haba", "maiz", "arveja"), "current_rotation")
    m = rule_motives(("arveja", "maiz", "papa"), h.crop_ids, CULTIVOS, FILTROS, history_basis=h.basis)
    assert _reglas(m) == [
        (1, "familia_seguida", "Repite la familia Leguminosae en dos ciclos seguidos. "
         "Se supuso que antes del primer ciclo el terreno siguió su rotación actual"),
    ]  # fmt: skip
    assert m[0].source_ids == ("psu_rotacion_familias",)


def test_familia_seguida_con_la_misma_lista_declarada_no_lleva_la_frase():
    m = rule_motives(("arveja", "maiz", "papa"), ["haba", "maiz", "arveja"], CULTIVOS, FILTROS, history_basis="declared")
    assert _reglas(m) == [(1, "familia_seguida", RAZON_LEGUMINOSAE)]


def test_los_motivos_entre_ciclos_de_la_estrategia_nunca_llevan_la_frase():
    h = terrain_history([], ["arveja", "maiz", "haba"])
    m = rule_motives(("arveja", "haba", "maiz"), h.crop_ids, CULTIVOS, FILTROS, history_basis="current_rotation")
    assert [(x.cycle, x.reason) for x in m] == [
        (1, "Repite la familia Leguminosae en dos ciclos seguidos. "
            "Se supuso que antes del primer ciclo el terreno siguió su rotación actual"),
        (2, RAZON_LEGUMINOSAE),
    ]  # fmt: skip
    solo_dentro = rule_motives(("maiz", "arveja", "haba"), h.crop_ids, CULTIVOS, FILTROS, history_basis="current_rotation")
    assert [(x.cycle, x.reason) for x in solo_dentro] == [(3, RAZON_LEGUMINOSAE)]


def test_papa_tras_papa_supuesta_lleva_la_frase_en_las_dos_reglas_del_ciclo_1():
    h = terrain_history([], ["maiz", "zanahoria", "papa"])
    m = rule_motives(("papa", "maiz", "haba"), h.crop_ids, CULTIVOS, FILTROS, history_basis=h.basis)
    assert [(x.cycle, x.rule_id) for x in m] == [(1, "familia_seguida"), (1, "papa_seguida")]
    assert all(x.reason == f"Repite la familia Solanaceae en dos ciclos seguidos. {FRASE}" for x in m)


def test_family_return_filter_lleva_la_frase_si_la_aparicion_anterior_esta_en_los_anteriores_supuestos():
    # Papa en el ciclo 1; la papa anterior está 1 ciclo atrás (maiz) en los cultivos anteriores.
    reglas = [FAMILIA_VUELVE]
    m = rule_motives(("papa", "arveja", "maiz"), ["maiz", "papa"], CULTIVOS, reglas, history_basis="current_rotation")
    assert _reglas(m) == [
        (1, "prueba_retorno_solanaceae",
         "La familia Solanaceae vuelve al terreno después de 1 ciclos de otras familias. "
         "Se supuso que antes del primer ciclo el terreno siguió su rotación actual"),
    ]  # fmt: skip
    declarada = rule_motives(("papa", "arveja", "maiz"), ["maiz", "papa"], CULTIVOS, reglas, history_basis="declared")
    assert _reglas(declarada) == [
        (1, "prueba_retorno_solanaceae", "La familia Solanaceae vuelve al terreno después de 1 ciclos de otras familias"),
    ]


def test_family_return_filter_no_lleva_la_frase_si_las_dos_apariciones_son_de_la_estrategia():
    m = rule_motives(("papa", "maiz", "papa"), ["haba", "zanahoria", "maiz"], CULTIVOS, [FAMILIA_VUELVE], history_basis="current_rotation")
    assert _reglas(m) == [
        (3, "prueba_retorno_solanaceae", "La familia Solanaceae vuelve al terreno después de 1 ciclos de otras familias"),
    ]  # fmt: skip


# ---------- una sola historia (R4) ----------


def test_con_la_misma_historia_filtro_y_salud_del_suelo_dicen_lo_mismo():
    """Dada la misma historia, el filtro y `soil_health` cuentan los mismos ciclos. Que quien llama les pase la misma
    historia es de HU-213, no de esta prueba."""
    h = terrain_history([], ["papa", "avena_vicia", "arveja"])
    estrategia = ("papa", "avena_vicia", "arveja")
    pest = soil_health(estrategia, SUELO_CULTIVOS, list(h.crop_ids), SALUD, history_basis=h.basis)["pest_break"]
    assert (pest.status, pest.level) == ("available", "moderate")
    assert "después de 2 ciclos de otras familias" in pest.reasons[0]
    assert pest.reasons[-1] == FRASE
    motivos = rule_motives(estrategia, h.crop_ids, CULTIVOS, [FAMILIA_VUELVE], history_basis=h.basis)
    assert _reglas(motivos) == [
        (1, "prueba_retorno_solanaceae",
         "La familia Solanaceae vuelve al terreno después de 2 ciclos de otras familias. " + FRASE),
    ]  # fmt: skip


# ---------- filter_strategies y la estrategia actual ----------


def test_una_candidata_que_choca_con_la_rotacion_actual_queda_excluida_con_la_frase():
    h = terrain_history([], ["arveja", "maiz", "haba"])
    candidatas = [("arveja", "maiz", "papa"), ("maiz", "arveja", "papa")]
    r = filter_strategies(candidatas, h.crop_ids, CULTIVOS, FILTROS, None, None, EXPLICA, SIN_RIESGO, history_basis=h.basis)
    assert r.survivors == (("maiz", "arveja", "papa"),)
    assert [e.crop_ids for e in r.summary.excluded] == [("arveja", "maiz", "papa")]
    m = r.summary.excluded[0].motive
    assert (m.kind, m.cycle, m.rule_id) == ("rule", 1, "familia_seguida")
    assert m.reason == f"{RAZON_LEGUMINOSAE}. {FRASE}"
    assert r.summary.counts["rule"] == 1


def test_con_lista_declarada_la_exclusion_no_lleva_la_frase():
    r = filter_strategies(
        [("arveja", "maiz", "papa")], ["haba", "maiz", "arveja"], CULTIVOS, FILTROS, None, None, EXPLICA, SIN_RIESGO,
        history_basis="declared",
    )  # fmt: skip
    assert r.summary.excluded[0].motive.reason == RAZON_LEGUMINOSAE


def test_la_rotacion_actual_lleva_la_frase_en_su_issue_del_ciclo_1_y_nunca_se_excluye():
    actual = ("arveja", "maiz", "haba")
    h = terrain_history([], list(actual))
    fase1 = _f1(actual, h.crop_ids, history_basis=h.basis)
    issues = current_issues(fase1, [])
    assert [(i.cycle, i.kind, i.rule_id, i.reason) for i in issues] == [
        (1, "rule", "familia_seguida", f"{RAZON_LEGUMINOSAE}. {FRASE}"),
    ]  # fmt: skip
    assert issues[0].source_ids == ("psu_rotacion_familias",)


def test_family_return_del_ciclo_2_lleva_la_frase_solo_si_la_aparicion_anterior_es_un_cultivo_anterior():
    # Ciclo 2 (papa): la papa anterior está en los anteriores, 1 ciclo atrás tras el ciclo 1 (arveja) -> lleva la frase.
    m = rule_motives(("arveja", "papa", "maiz"), ["papa"], CULTIVOS, [FAMILIA_VUELVE], history_basis="current_rotation")
    assert _reglas(m) == [
        (2, "prueba_retorno_solanaceae",
         "La familia Solanaceae vuelve al terreno después de 1 ciclos de otras familias. " + FRASE),
    ]  # fmt: skip
    # Aparición anterior dentro de la estrategia (ciclo 1 papa, ciclo 2 arveja, ciclo 3 papa): sin frase.
    dentro = rule_motives(
        ("papa", "arveja", "papa"), ["haba", "maiz", "arveja"], CULTIVOS, [FAMILIA_VUELVE], history_basis="current_rotation"
    )
    assert _reglas(dentro) == [
        (3, "prueba_retorno_solanaceae", "La familia Solanaceae vuelve al terreno después de 1 ciclos de otras familias"),
    ]  # fmt: skip
