"""Reglas de rotación como datos (EP-06: HU-062; R1, R3, R4, R5, R8).

Escritas antes de la implementación, contra la interfaz acordada de `pipeline/rotation_rules.py` y de
`pipeline/schema.CONDITION_TYPES`, con la forma del contrato aprobada en la decisión 16 (`docs/decisiones.md`, 9 de
noviembre de 2026; `specs/02-contratos.md`, «Reglas de rotación como datos»). Tres bloques:

1. Validación del build con un Test Data Builder (`valid_rule`, `valid_catalog`): cada caso de falla cambia lo mínimo para
   que quede una sola causa, y el mensaje debe nombrar la regla.
2. Casos válidos, inmutabilidad, publicación (JSON, orden, esquema, `pipeline.build.publish`) y determinismo (R4).
3. El catálogo real (`catalog/rotation_rules.yaml` con las familias de `catalog/crops.yaml`): reglas mínimas, la «Matriz
   esperada» 8 × 8 de la HU y la rotación de referencia de Agrosavia en Tibaitatá.

Todas las fuentes y reglas de los bloques 1 y 2 son de ejemplo (R5): no son datos agronómicos.
"""

import copy
import dataclasses
import json
import re
from collections.abc import Mapping
from pathlib import Path

import polars as pl
import pytest

from pipeline import build as pipeline_build
from pipeline import catalog, examples, rotation_rules, schema
from pipeline.sources import dane, dane_mgn
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION

RULE_ID = "regla_de_prueba"
VERSION = "0.1.0"
EPIC = Path("specs/epicas/EP-06-catalogo-agronomico.md")
CRITERIA = {
    "nitrogen": "legume_cycles",
    "organic_carbon": "organic_matter_cycles",
    "soil_cover": "covered_months_pct",
    "pest_break": "family_return_min_cycles",
    "erosion": "bare_months_on_slope",
}
# Las familias exactas de las fichas (criterio de HU-062: misma mayúscula).
FAMILIES = {"Solanaceae", "Leguminosae", "Gramineae", "Umbelliferae", "Alliaceae"}


def source(source_id: str, **changes) -> dict:
    """Una fuente de ejemplo con las columnas de `sources` (mismo formato que en `catalog/crops.yaml`)."""
    return {
        "source_id": source_id,
        "name": f"Fuente de ejemplo {source_id} (pruebas)",
        "institution": "AgroSense (pruebas)",
        "url": None,
        "downloaded_at": "2026-11-09",
        "period_covered": None,
        "coverage": "Pruebas",
        "license": None,
        "notes": "Inventada para las pruebas (R5): no es una fuente agronómica.",
        **changes,
    }


RULES_SOURCE = source("fuente_reglas")
CROP_SOURCE = source("fuente_fichas")
KNOWN_SOURCES = {RULES_SOURCE["source_id"], CROP_SOURCE["source_id"]}

# Una regla válida mínima por tipo de condición, con la forma de la tabla de «Reglas de rotación como datos».
# Los números son de ejemplo (R5).
VALID = {
    "same_family_consecutive": {
        "kind": "filter",
        "criterion": None,
        "params": {"families": None},
        "levels": None,
        "reason_template": "Repite la familia {family} en dos ciclos seguidos",
    },
    "family_return_min_cycles": {
        "kind": "health",
        "criterion": "pest_break",
        "params": {"family": "Solanaceae", "min_cycles": 2},
        "levels": {"favorable": 2, "moderate": 1},
        "reason_template": "La familia {family} vuelve después de {cycles} ciclos de otras familias",
    },
    "legume_cycles": {
        "kind": "health",
        "criterion": "nitrogen",
        "params": {},
        "levels": {"favorable": 2, "moderate": 1},
        "reason_template": "{count} de los ciclos tienen leguminosas, que fijan nitrógeno",
    },
    # Forma de `levels` de la decisión 16: `low` y `normal`, cada una con `favorable` y `moderate`. Sin marcadores en la
    # razón porque los de este tipo no están en el contrato (decisión pendiente).
    "organic_matter_cycles": {
        "kind": "health",
        "criterion": "organic_carbon",
        "params": {"soc_low_g_kg": 20},
        "levels": {"low": {"favorable": 2, "moderate": 1}, "normal": {"favorable": 1, "moderate": 0}},
        "reason_template": "Cuenta los ciclos de abono verde o descanso según el carbono orgánico del suelo",
    },
    "covered_months_pct": {
        "kind": "health",
        "criterion": "soil_cover",
        "params": {},
        "levels": {"favorable": 80, "moderate": 60},
        "reason_template": "El suelo queda cubierto {pct} % de los meses de la estrategia",
    },
    "bare_months_on_slope": {
        "kind": "health",
        "criterion": "erosion",
        "params": {"slope_pct_from": 8},
        "levels": {"favorable": 1, "moderate": 3},
        "reason_template": "Con pendiente de {slope} %, el suelo queda descubierto {months} meses",
    },
}


def valid_rule(base: str = "legume_cycles", **overrides) -> dict:
    """Test Data Builder: una regla válida mínima del tipo `base`, con los campos que cambie la prueba (`overrides`)."""
    rule = {"rule_id": RULE_ID, "condition_type": base, **copy.deepcopy(VALID[base]), "source_id": "fuente_reglas"}
    rule.update(overrides)
    return rule


def valid_catalog(rules: list[dict] | None = None, sources: list[dict] | None = None, version: str = VERSION) -> dict:
    """Test Data Builder: el contenido de un `catalog/rotation_rules.yaml` válido mínimo."""
    return {
        "version": version,
        "sources": copy.deepcopy([RULES_SOURCE] if sources is None else sources),
        "rules": [valid_rule()] if rules is None else rules,
    }


def organic(levels: object = None, **groups) -> dict:
    """Una regla `organic_matter_cycles` válida con `levels` entero cambiado, o con los grupos (`low`, `normal`, ...) dados."""
    rule = valid_rule("organic_matter_cycles")
    if levels is not None:
        rule["levels"] = levels
    if groups:
        rule["levels"].update(groups)
    return rule


def build(data: dict, *, crop_sources: list[dict] | None = None, expected_version: str = VERSION):
    return rotation_rules.build(
        data,
        crop_sources=copy.deepcopy([CROP_SOURCE] if crop_sources is None else crop_sources),
        known_families=set(FAMILIES),
        expected_version=expected_version,
    )


def parse(raw: dict, families: set[str] = FAMILIES, sources: set[str] = KNOWN_SOURCES):
    return rotation_rules.parse_rule(raw, known_sources=set(sources), known_families=set(families))


def plain(value):
    """`params` o `levels` de una regla como dict y listas de Python, sea cual sea el contenedor inmutable que use."""
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [plain(item) for item in value]
    return value


# ---------- 1. El build falla, con un mensaje que nombra la regla ----------

FAILURES = [
    # `kind` no es `filter` ni `health`.
    ("kind_que_no_es_filter_ni_health", valid_rule(kind="consejo")),
    # `condition_type` fuera de la lista cerrada o que no admite ese `kind`.
    ("condition_type_fuera_de_la_lista_cerrada", valid_rule(condition_type="root_type_alternation")),
    ("legume_cycles_como_filter", valid_rule(kind="filter", criterion=None, levels=None)),
    ("bare_months_on_slope_como_filter", valid_rule("bare_months_on_slope", kind="filter", criterion=None, levels=None)),
    ("same_family_consecutive_como_health", valid_rule("same_family_consecutive", kind="health", criterion="pest_break")),
    # `criterion` no nulo en un `filter`, o distinto del que el contrato da a su `condition_type` en un `health`.
    ("criterion_en_un_filter", valid_rule("same_family_consecutive", criterion="pest_break")),
    ("criterion_de_otro_tipo_en_un_health", valid_rule(criterion="soil_cover")),
    ("criterion_nulo_en_un_health", valid_rule(criterion=None)),
    ("criterion_que_no_existe", valid_rule(criterion="fertilidad")),
    # `params` no es un objeto con las llaves de su tipo.
    ("params_nulo", valid_rule(params=None)),
    ("params_lista", valid_rule(params=[])),
    ("params_texto", valid_rule("same_family_consecutive", params="families")),
    ("params_sin_una_llave", valid_rule("family_return_min_cycles", params={"family": "Solanaceae"})),
    ("params_con_una_llave_de_mas", valid_rule(params={"min_cycles": 2})),
    ("params_sin_soc_low_g_kg", valid_rule("organic_matter_cycles", params={})),
    ("params_sin_slope_pct_from", valid_rule("bare_months_on_slope", params={})),
    # `levels` no es un objeto con las llaves de su tipo, falta en un `health` o sobra en un `filter`.
    ("levels_lista", valid_rule(levels=[2, 1])),
    ("levels_sin_moderate", valid_rule(levels={"favorable": 2})),
    ("levels_con_una_llave_de_mas", valid_rule(levels={"favorable": 2, "moderate": 1, "unfavorable": 0})),
    ("levels_falta_en_un_health", valid_rule(levels=None)),
    ("levels_sobra_en_un_filter", valid_rule("same_family_consecutive", levels={"favorable": 1, "moderate": 0})),
    ("levels_sobra_en_family_return_como_filter", valid_rule("family_return_min_cycles", kind="filter", criterion=None)),
    # `levels` de organic_matter_cycles (decisión 16): `low` y `normal` obligatorias, cada una con `favorable` y
    # `moderate` enteros ≥ 0, `moderate <= favorable` en cada grupo (sin franja intermedia, 9 de noviembre de 2026) y
    # `low.favorable >= 1`.
    ("organic_levels_vacio", organic(levels={})),
    ("organic_levels_no_objeto", organic(levels=1)),
    ("organic_levels_sin_low", organic(levels={"normal": {"favorable": 1, "moderate": 0}})),
    ("organic_levels_sin_normal", organic(levels={"low": {"favorable": 2, "moderate": 1}})),
    ("organic_levels_con_una_llave_de_mas", organic(high={"favorable": 1, "moderate": 0})),
    ("organic_levels_plano_como_los_demas", organic(levels={"favorable": 2, "moderate": 1})),
    ("organic_grupo_no_objeto", organic(low=2)),
    ("organic_grupo_sin_moderate", organic(low={"favorable": 2})),
    ("organic_grupo_con_una_llave_de_mas", organic(normal={"favorable": 1, "moderate": 0, "unfavorable": 0})),
    # Con `moderate <= favorable`, `{0, 0}` respeta el orden: la única causa es `low.favorable = 0`.
    ("organic_low_favorable_cero", organic(low={"favorable": 0, "moderate": 0})),
    ("organic_moderate_mayor_que_favorable_en_low", organic(low={"favorable": 1, "moderate": 2})),
    ("organic_moderate_mayor_que_favorable_en_normal", organic(normal={"favorable": 1, "moderate": 2})),
    ("organic_favorable_no_entero", organic(low={"favorable": 2.5, "moderate": 1})),
    ("organic_moderate_texto", organic(normal={"favorable": 1, "moderate": "0"})),
    ("organic_favorable_booleano", organic(low={"favorable": True, "moderate": 0})),
    ("organic_moderate_negativo", organic(normal={"favorable": 1, "moderate": -1})),
    ("organic_grupo_nulo", organic(normal=None)),
    # Cortes en orden invertido: con «higher_is_better», `moderate` no puede pasar de `favorable`; con «lower_is_better»
    # (`bare_months_on_slope`), `favorable` no puede pasar de `moderate`. La igualdad sí vale (sin franja intermedia).
    ("cortes_al_reves_en_legume_cycles", valid_rule(levels={"favorable": 1, "moderate": 2})),
    ("cortes_al_reves_en_covered_months_pct", valid_rule("covered_months_pct", levels={"favorable": 60, "moderate": 80})),
    (
        "cortes_al_reves_en_family_return_min_cycles",
        valid_rule("family_return_min_cycles", params={"family": "Solanaceae", "min_cycles": 1}, levels={"favorable": 1, "moderate": 2}),
    ),
    ("cortes_al_reves_en_bare_months_on_slope", valid_rule("bare_months_on_slope", levels={"favorable": 3, "moderate": 1})),
    # En un `family_return_min_cycles` de `kind = health`, `params.min_cycles` es igual a `levels.favorable`.
    ("min_cycles_distinto_de_favorable", valid_rule("family_return_min_cycles", params={"family": "Solanaceae", "min_cycles": 3})),
    (
        "min_cycles_distinto_de_favorable_sin_franja_intermedia",
        valid_rule("family_return_min_cycles", params={"family": "Solanaceae", "min_cycles": 2}, levels={"favorable": 4, "moderate": 4}),
    ),
    # `source_id` vacío o que no está en `sources` (R8).
    ("source_id_vacio", valid_rule(source_id="")),
    ("source_id_nulo", valid_rule(source_id=None)),
    ("source_id_que_no_esta_en_sources", valid_rule(source_id="inventada")),
    ("source_id_ejemplo_sin_definir", valid_rule(source_id="ejemplo")),
    # Una familia de `params` que no está en ninguna ficha (también con otra mayúscula).
    ("familia_en_minuscula", valid_rule("family_return_min_cycles", params={"family": "solanaceae", "min_cycles": 2})),
    ("familia_que_no_esta_en_ninguna_ficha", valid_rule("family_return_min_cycles", params={"family": "Rosaceae", "min_cycles": 2})),
    ("familias_con_una_que_no_esta", valid_rule("same_family_consecutive", params={"families": ["Solanaceae", "Rosaceae"]})),
    # Un `{marcador}` de la razón que no es de su tipo.
    ("marcador_que_no_es_de_su_tipo", valid_rule(reason_template="La familia {family} fija nitrógeno")),
]


@pytest.mark.parametrize("rule", [r for _, r in FAILURES], ids=[name for name, _ in FAILURES])
def test_el_build_falla_con_un_mensaje_que_nombra_la_regla(rule):
    # Preparar
    data = valid_catalog(rules=[rule])
    # Actuar y comprobar
    with pytest.raises(rotation_rules.RotationRulesError, match=re.escape(RULE_ID)):
        build(data)


@pytest.mark.parametrize("rule", [r for _, r in FAILURES], ids=[name for name, _ in FAILURES])
def test_parse_rule_rechaza_la_misma_regla(rule):
    # El build valida regla por regla con `parse_rule`: la misma causa falla ahí, nombrando la regla.
    with pytest.raises(rotation_rules.RotationRulesError, match=re.escape(RULE_ID)):
        parse(rule)


def test_el_build_falla_con_un_rule_id_repetido():
    # Preparar: dos reglas válidas con el mismo `rule_id`.
    data = valid_catalog(rules=[valid_rule(), valid_rule("covered_months_pct")])
    # Actuar y comprobar
    with pytest.raises(rotation_rules.RotationRulesError, match=re.escape(RULE_ID)):
        build(data)


def test_el_build_falla_si_un_source_id_esta_en_los_dos_catalogos_con_datos_distintos():
    # Preparar: `fuente_fichas` también en la sección de reglas, con otro nombre.
    data = valid_catalog(sources=[RULES_SOURCE, source("fuente_fichas", name="Otro nombre")])
    # Actuar y comprobar: el mensaje nombra la fuente en conflicto.
    with pytest.raises(rotation_rules.RotationRulesError, match="fuente_fichas"):
        build(data)


def test_el_build_falla_si_la_version_no_es_la_del_catalogo_de_fichas():
    # Supuesto de la nota 7 de HU-062: los dos catálogos llevan la misma `version` (`rules_version`).
    data = valid_catalog(version="0.2.0")
    with pytest.raises(rotation_rules.RotationRulesError, match=re.escape("0.2.0")):
        build(data, expected_version=VERSION)


def test_load_falla_con_un_mensaje_claro_si_no_existe_el_archivo(tmp_path):
    missing = tmp_path / "rotation_rules.yaml"
    with pytest.raises(FileNotFoundError, match="rotation_rules"):
        rotation_rules.load(missing)


def test_load_lee_params_y_levels_como_mapas_yaml(tmp_path):
    # Preparar: un YAML de ejemplo escrito en tmp_path (nada se escribe en data/ ni en catalog/).
    path = tmp_path / "rotation_rules.yaml"
    path.write_text(
        f'version: "{VERSION}"\n'
        "sources:\n  - source_id: fuente_reglas\n    name: Fuente de ejemplo (pruebas)\n"
        "rules:\n  - rule_id: regla_de_prueba\n    kind: health\n    criterion: nitrogen\n    condition_type: legume_cycles\n"
        "    params: {}\n    levels: {favorable: 2, moderate: 1}\n"
        '    reason_template: "{count} de los ciclos tienen leguminosas"\n    source_id: fuente_reglas\n',
        encoding="utf-8",
    )
    # Actuar
    data = rotation_rules.load(path)
    # Comprobar
    assert data["version"] == VERSION
    assert data["rules"][0]["levels"] == {"favorable": 2, "moderate": 1}


# ---------- 2. Casos válidos, publicación y determinismo ----------


@pytest.mark.parametrize("condition_type", list(VALID), ids=[f"{t}_valida" for t in VALID])
def test_cada_tipo_con_su_forma_correcta_pasa(condition_type):
    # Preparar
    raw = valid_rule(condition_type)
    # Actuar
    rule = parse(raw)
    # Comprobar
    assert isinstance(rule, rotation_rules.RotationRule)
    assert (rule.rule_id, rule.kind, rule.criterion, rule.condition_type) == (RULE_ID, raw["kind"], raw["criterion"], condition_type)
    assert (plain(rule.params), plain(rule.levels), rule.reason_template, rule.source_id) == (
        raw["params"],
        raw["levels"],
        raw["reason_template"],
        raw["source_id"],
    )


def test_family_return_min_cycles_tambien_vale_como_filter_sin_levels():
    rule = parse(valid_rule("family_return_min_cycles", kind="filter", criterion=None, levels=None))
    assert (rule.kind, rule.criterion, rule.levels) == ("filter", None, None)


def test_same_family_consecutive_acepta_una_lista_de_familias_de_las_fichas():
    rule = parse(valid_rule("same_family_consecutive", params={"families": ["Solanaceae", "Leguminosae"]}))
    assert sorted(plain(rule.params)["families"]) == ["Leguminosae", "Solanaceae"]


@pytest.mark.parametrize(
    "levels",
    [
        {"low": {"favorable": 2, "moderate": 1}, "normal": {"favorable": 1, "moderate": 0}},
        {"low": {"favorable": 1, "moderate": 0}, "normal": {"favorable": 1, "moderate": 0}},
        {"low": {"favorable": 3, "moderate": 1}, "normal": {"favorable": 2, "moderate": 1}},
        {"low": {"favorable": 2, "moderate": 2}, "normal": {"favorable": 1, "moderate": 0}},
        {"low": {"favorable": 2, "moderate": 1}, "normal": {"favorable": 1, "moderate": 1}},
        {"low": {"favorable": 1, "moderate": 1}, "normal": {"favorable": 0, "moderate": 0}},
    ],
    ids=[
        "ejemplo_del_contrato",
        "low_favorable_uno_el_minimo",
        "cortes_mas_altos",
        "sin_franja_intermedia_en_low",
        "sin_franja_intermedia_en_normal",
        "sin_franja_intermedia_en_los_dos_con_los_minimos",
    ],
)
def test_organic_matter_cycles_acepta_la_forma_de_la_decision_16(levels):
    # `low` y `normal`, cada una con `favorable` ≥ `moderate` ≥ 0 enteros (la igualdad es «sin franja intermedia», 9 de
    # noviembre de 2026), y `low.favorable` ≥ 1 (decisión 16).
    rule = parse(valid_rule("organic_matter_cycles", levels=levels))
    assert plain(rule.levels) == levels


# ---------- Inmutabilidad: una regla validada no se puede cambiar después (R4) ----------

MUTATION_ERRORS = (TypeError, AttributeError)


@pytest.mark.parametrize(
    ("condition_type", "mutate"),
    [
        ("family_return_min_cycles", lambda r: r.params.__setitem__("min_cycles", 5)),
        ("family_return_min_cycles", lambda r: r.params.__delitem__("family")),
        ("legume_cycles", lambda r: r.params.__setitem__("nueva", 1)),
        ("family_return_min_cycles", lambda r: r.levels.__setitem__("favorable", 9)),
        ("covered_months_pct", lambda r: r.levels.pop("moderate")),
        ("organic_matter_cycles", lambda r: r.levels.__setitem__("low", {"favorable": 9, "moderate": 0})),
        ("organic_matter_cycles", lambda r: r.levels["low"].__setitem__("favorable", 9)),
        ("organic_matter_cycles", lambda r: r.levels["normal"].update({"moderate": 9})),
    ],
    ids=[
        "params_cambiar_un_valor",
        "params_borrar_una_llave",
        "params_agregar_una_llave",
        "levels_cambiar_un_corte",
        "levels_quitar_un_corte",
        "organic_levels_cambiar_un_grupo",
        "organic_levels_cambiar_un_corte_de_low",
        "organic_levels_cambiar_un_corte_de_normal",
    ],
)
def test_params_y_levels_de_una_regla_validada_no_se_pueden_mutar(condition_type, mutate):
    # Preparar
    rule = parse(valid_rule(condition_type))
    before = (plain(rule.params), plain(rule.levels))
    # Actuar y comprobar: el intento falla y la regla queda igual.
    with pytest.raises(MUTATION_ERRORS):
        mutate(rule)
    assert (plain(rule.params), plain(rule.levels)) == before


def test_la_lista_de_familias_de_una_regla_validada_no_se_puede_mutar():
    rule = parse(valid_rule("same_family_consecutive", params={"families": ["Solanaceae", "Leguminosae"]}))
    with pytest.raises(MUTATION_ERRORS):
        rule.params["families"].append("Gramineae")
    assert sorted(plain(rule.params)["families"]) == ["Leguminosae", "Solanaceae"]


def test_cambiar_el_dato_de_entrada_despues_no_cambia_la_regla_validada():
    # Una vista de solo lectura sobre el mismo dict de entrada no basta: la regla guarda su propia copia.
    raw = valid_rule("organic_matter_cycles")
    rule = parse(raw)
    raw["params"]["soc_low_g_kg"] = 99
    raw["levels"]["low"]["favorable"] = 99
    assert plain(rule.params) == VALID["organic_matter_cycles"]["params"]
    assert plain(rule.levels) == VALID["organic_matter_cycles"]["levels"]


def test_una_regla_validada_no_deja_reasignar_sus_campos():
    rule = parse(valid_rule())
    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.params = {}


def test_condition_types_no_se_puede_mutar():
    spec = schema.CONDITION_TYPES["legume_cycles"]
    with pytest.raises(MUTATION_ERRORS):
        schema.CONDITION_TYPES["nuevo_tipo"] = spec
    with pytest.raises(MUTATION_ERRORS):
        del schema.CONDITION_TYPES["legume_cycles"]
    assert "nuevo_tipo" not in schema.CONDITION_TYPES
    assert "legume_cycles" in schema.CONDITION_TYPES


@pytest.mark.parametrize("condition_type", list(VALID))
def test_una_entrada_de_condition_types_no_se_puede_mutar(condition_type):
    spec = schema.CONDITION_TYPES[condition_type]
    # El tipo de condición es un dataclass congelado...
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.criterion = "otro"
    # ...y sus llaves de `params` y `levels` (también los grupos anidados) son de solo lectura.
    with pytest.raises(MUTATION_ERRORS):
        spec.params_keys["nueva"] = schema.Value("integer")
    if spec.levels_keys is not None:
        with pytest.raises(MUTATION_ERRORS):
            spec.levels_keys["nueva"] = schema.Value("integer")
        for group in spec.levels_keys.values():
            if group.keys is not None:
                with pytest.raises(MUTATION_ERRORS):
                    group.keys["nueva"] = schema.Value("integer")


@pytest.mark.parametrize(
    "levels",
    [{"favorable": 1, "moderate": 3}, {"favorable": 0, "moderate": 2}, {"favorable": 2, "moderate": 2}, {"favorable": 0, "moderate": 0}],
    ids=["un_mes_y_tres", "cero_meses_y_dos", "sin_franja_intermedia", "sin_franja_intermedia_en_cero"],
)
def test_bare_months_on_slope_acepta_cortes_maximos_con_favorable_menor_o_igual_que_moderate(levels):
    rule = parse(valid_rule("bare_months_on_slope", levels=levels))
    assert rule.levels == levels


@pytest.mark.parametrize(
    ("condition_type", "params", "levels"),
    [
        ("legume_cycles", {}, {"favorable": 2, "moderate": 1}),
        ("covered_months_pct", {}, {"favorable": 80, "moderate": 60}),
        ("family_return_min_cycles", {"family": "Solanaceae", "min_cycles": 3}, {"favorable": 3, "moderate": 1}),
        ("legume_cycles", {}, {"favorable": 2, "moderate": 2}),
        ("covered_months_pct", {}, {"favorable": 80, "moderate": 80}),
        ("family_return_min_cycles", {"family": "Solanaceae", "min_cycles": 4}, {"favorable": 4, "moderate": 4}),
    ],
    ids=[
        "legume_cycles",
        "covered_months_pct",
        "family_return_min_cycles",
        "legume_cycles_sin_franja_intermedia",
        "covered_months_pct_sin_franja_intermedia",
        "family_return_min_cycles_sin_franja_intermedia",
    ],
)
def test_las_demas_aceptan_cortes_minimos_con_moderate_menor_o_igual_que_favorable(condition_type, params, levels):
    # Sin franja intermedia (9 de noviembre de 2026): `moderate == favorable` vale; solo `moderate > favorable` falla.
    rule = parse(valid_rule(condition_type, params=params, levels=levels))
    assert rule.levels == levels


@pytest.mark.parametrize(
    ("condition_type", "block", "key", "bad"),
    [
        ("bare_months_on_slope", "params", "slope_pct_from", float("inf")),
        ("legume_cycles", "levels", "favorable", float("nan")),
    ],
    ids=["inf_en_un_param", "nan_en_un_level"],
)
def test_rechaza_nan_e_infinito_con_el_nombre_de_la_regla_y_el_campo(condition_type, block, key, bad):
    rule = valid_rule(condition_type)
    rule[block][key] = bad
    with pytest.raises(rotation_rules.RotationRulesError, match=re.escape(RULE_ID)) as error:
        parse(rule)
    assert f"{block}.{key}" in str(error.value)


def test_una_regla_puede_citar_una_fuente_del_catalogo_de_fichas_sin_repetirla():
    # Nota 7 de HU-062.
    rules, new_sources = build(valid_catalog(rules=[valid_rule(source_id="fuente_fichas")]))
    assert rules["source_id"].to_list() == ["fuente_fichas"]
    assert "fuente_fichas" not in new_sources["source_id"].to_list()


def test_una_fuente_repetida_con_los_mismos_datos_no_se_duplica():
    rules, new_sources = build(valid_catalog(sources=[RULES_SOURCE, CROP_SOURCE]))
    assert new_sources["source_id"].to_list() == ["fuente_reglas"]
    assert rules.height == 1


def all_types_catalog() -> dict:
    rules = [valid_rule(t, rule_id=f"regla_{i}_{t}") for i, t in enumerate(VALID)]
    return valid_catalog(rules=list(reversed(rules)))


def test_la_tabla_publicada_cumple_el_esquema_de_rotation_rules():
    # Actuar
    rules, _ = build(all_types_catalog())
    # Comprobar: columnas, orden, tipos, nulos y llave del contrato.
    schema.check("rotation_rules", rules)
    assert rules.height == len(VALID)


def test_la_tabla_va_ordenada_por_rule_id():
    rules, _ = build(all_types_catalog())
    assert rules["rule_id"].to_list() == sorted(rules["rule_id"].to_list())


def test_params_y_levels_se_publican_como_json_valido_con_llaves_ordenadas():
    # Preparar
    data = all_types_catalog()
    expected = {r["rule_id"]: r for r in data["rules"]}
    # Actuar
    rules, _ = build(data)
    # Comprobar
    for row in rules.iter_rows(named=True):
        raw = expected[row["rule_id"]]
        assert json.loads(row["params"]) == raw["params"]
        assert row["params"] == json.dumps(raw["params"], sort_keys=True)
        if raw["levels"] is None:
            assert row["levels"] is None
        else:
            assert json.loads(row["levels"]) == raw["levels"]
            assert row["levels"] == json.dumps(raw["levels"], sort_keys=True)


def test_un_filter_se_publica_con_criterion_y_levels_nulos():
    rules, _ = build(all_types_catalog())
    filters = rules.filter(pl.col("kind") == "filter")
    assert filters.height == 1
    assert filters["criterion"].to_list() == [None]
    assert filters["levels"].to_list() == [None]


def test_construir_dos_veces_el_mismo_dato_da_lo_mismo():
    # R4: misma entrada, mismo resultado, aunque las reglas lleguen en otro orden.
    first_rules, first_sources = build(all_types_catalog())
    second_rules, second_sources = build(all_types_catalog())
    data = all_types_catalog()
    data["rules"].reverse()
    third_rules, _ = build(data)
    assert first_rules.equals(second_rules)
    assert first_sources.equals(second_sources)
    assert first_rules.equals(third_rules)


def test_families_en_distinto_orden_publica_el_mismo_json():
    # R4: `params.families` se publica ordenada; el orden en que se escriba en el YAML no cambia la tabla.
    one = valid_rule("same_family_consecutive", params={"families": ["Solanaceae", "Leguminosae", "Gramineae"]})
    other = valid_rule("same_family_consecutive", params={"families": ["Gramineae", "Solanaceae", "Leguminosae"]})
    first, _ = build(valid_catalog(rules=[one]))
    second, _ = build(valid_catalog(rules=[other]))
    assert first.equals(second)
    assert json.loads(first["params"][0]) == {"families": ["Gramineae", "Leguminosae", "Solanaceae"]}


# ---------- Publicación con `pipeline.build` (HU-062: rotation_rules.parquet, sources y manifest.json) ----------


def real_rules_and_sources() -> tuple[str, pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """El catálogo real como lo arma `pipeline.build.build`: fichas, etapas, sus fuentes, reglas y fuentes nuevas."""
    crops_data = catalog.load()
    crops, stages, crop_sources = catalog.build(crops_data)
    rules, rules_sources = rotation_rules.build(
        rotation_rules.load(),
        crop_sources=crops_data["sources"],
        known_families=set(crops["family"].drop_nulls().to_list()),
        expected_version=crops_data["version"],
    )
    return crops_data["version"], crops, stages, crop_sources, rules, rules_sources


def test_publish_escribe_rotation_rules_con_su_esquema_sus_filas_en_el_manifiesto_y_sus_fuentes(tmp_path):
    # Preparar: los municipios de ejemplo de tests/conftest.py (R5) y el catálogo real, unidos como en `build`.
    version, crops, stages, crop_sources, rules, rules_sources = real_rules_and_sources()
    assert rules_sources.height > 0, "Las reglas reales no traen fuentes propias: la prueba no comprueba la unión."
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, SAMPLE_REGION["region"]["departments"])
    sources = pl.concat(
        [pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)]), crop_sources, rules_sources],
        how="diagonal_relaxed",
    )
    folder = tmp_path / "published"
    # Actuar
    manifest = pipeline_build.publish(SAMPLE_REGION, municipalities, sources, folder, crops=(version, crops, stages), rules=rules)
    # Comprobar: la tabla con el esquema del contrato, sus filas en el manifiesto y sus fuentes en `sources` (R8).
    published = pl.read_parquet(folder / "rotation_rules.parquet")
    schema.check("rotation_rules", published)
    assert published.equals(rules)
    written = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert written == manifest
    assert written["tables"]["rotation_rules"]["rows"] == rules.height
    assert written["rules_version"] == version
    published_sources = set(pl.read_parquet(folder / "sources.parquet")["source_id"].to_list())
    assert set(rules_sources["source_id"].to_list()) <= published_sources
    assert set(published["source_id"].to_list()) <= published_sources


def test_el_build_completo_une_las_fuentes_de_las_reglas_y_anota_la_tabla(tmp_path, monkeypatch):
    # Preparar: `pipeline.build.build` con la caché del DANE reemplazada por los municipios de ejemplo (R5) y un
    # cuadrado por municipio como límite; el catálogo y las reglas son los reales. Nada se escribe fuera de tmp_path.
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, SAMPLE_REGION["region"]["departments"])
    features = [
        {
            "type": "Feature",
            "properties": {"MPIO_CDPMP": m["municipality_id"]},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [m["lon"] - 0.05, m["lat"] - 0.05],
                        [m["lon"] + 0.05, m["lat"] - 0.05],
                        [m["lon"] + 0.05, m["lat"] + 0.05],
                        [m["lon"] - 0.05, m["lat"] + 0.05],
                        [m["lon"] - 0.05, m["lat"] - 0.05],
                    ]
                ],
            },
        }
        for m in municipalities.iter_rows(named=True)
    ]
    region = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}
    monkeypatch.setattr(pipeline_build, "load_region", lambda: copy.deepcopy(region))
    monkeypatch.setattr(dane, "read_cache", lambda cache: (copy.deepcopy(SAMPLE_MUNICIPALITIES), dict(SAMPLE_META)))
    monkeypatch.setattr(dane_mgn, "read_cache", lambda departments, cache: (copy.deepcopy(features), dict(SAMPLE_META)))
    folder = tmp_path / "published"
    # Actuar
    manifest = pipeline_build.build(folder=folder, cache=tmp_path / "raw")
    # Comprobar
    _, _, _, _, rules, rules_sources = real_rules_and_sources()
    published = pl.read_parquet(folder / "rotation_rules.parquet")
    schema.check("rotation_rules", published)
    assert published.equals(rules)
    assert manifest["tables"]["rotation_rules"]["rows"] == rules.height
    published_sources = set(pl.read_parquet(folder / "sources.parquet")["source_id"].to_list())
    assert set(rules_sources["source_id"].to_list()) <= published_sources
    assert set(published["source_id"].to_list()) <= published_sources


# ---------- La lista cerrada en código es la del contrato ----------

# Los tipos de valor que admite `schema.Value`: los cuatro de los valores de `params` y `levels` del contrato, más
# `object`, el grupo anidado de cortes de `organic_matter_cycles` (decisión 16). Cualquier otro es un error de la spec.
KNOWN_VALUE_TYPES = {"family", "families", "integer", "number", "object"}


def test_la_lista_cerrada_de_schema_es_la_del_contrato():
    # La tabla de «Reglas de rotación como datos» de specs/02-contratos.md (decisión 16), en código: tipos, `kind`,
    # `criterion`, llaves de `params` y de `levels` y el sentido de los cortes. Los marcadores no son del contrato
    # (prueba aparte, más abajo).
    flat = {"favorable", "moderate"}
    expected = {
        "same_family_consecutive": ({"filter"}, None, {"families"}, None, None),
        "family_return_min_cycles": ({"filter", "health"}, "pest_break", {"family", "min_cycles"}, flat, "higher_is_better"),
        "legume_cycles": ({"health"}, "nitrogen", set(), flat, "higher_is_better"),
        "organic_matter_cycles": ({"health"}, "organic_carbon", {"soc_low_g_kg"}, {"low", "normal"}, "higher_is_better"),
        "covered_months_pct": ({"health"}, "soil_cover", set(), flat, "higher_is_better"),
        "bare_months_on_slope": ({"health"}, "erosion", {"slope_pct_from"}, flat, "lower_is_better"),
    }
    assert set(schema.CONDITION_TYPES) == set(expected)
    assert set(schema.RULE_KINDS) == {"filter", "health"}
    for name, (kinds, criterion, params_keys, levels_keys, order) in expected.items():
        spec = schema.CONDITION_TYPES[name]
        assert set(spec.kinds) == kinds, name
        assert spec.criterion == criterion, name
        assert set(spec.params_keys) == params_keys, name
        assert (None if spec.levels_keys is None else set(spec.levels_keys)) == levels_keys, name
        assert spec.levels_order == order, name
    # organic_matter_cycles (decisión 16): `low` y `normal` son grupos con `favorable` y `moderate`. Su validación se
    # prueba por comportamiento en `parse_rule` (bloque 1 y `test_organic_matter_cycles_acepta_la_forma_de_la_decision_16`).
    for group in ("low", "normal"):
        value = schema.CONDITION_TYPES["organic_matter_cycles"].levels_keys[group]
        assert (value.type, set(value.keys or {})) == ("object", flat), group


def test_los_marcadores_de_reason_template_son_los_que_llena_el_motor():
    # La lista de marcadores de specs/02-contratos.md («Reglas de rotación como datos»), aprobada por Felipe el 11 nov
    # 2026. Esta prueba fija la de `pipeline/schema.py` para que no cambie sin cambiar el contrato.
    expected = {
        "same_family_consecutive": {"family"},
        "family_return_min_cycles": {"family", "cycles"},
        "legume_cycles": {"count"},
        "organic_matter_cycles": {"count", "soc_level", "soc_range"},
        "covered_months_pct": {"pct"},
        "bare_months_on_slope": {"slope", "months"},
    }
    for name, placeholders in expected.items():
        assert set(schema.CONDITION_TYPES[name].placeholders) == placeholders, name


def spec_values(keys: Mapping | None):
    """Cada `schema.Value` de unas llaves de `params` o `levels`, también los de grupos anidados (organic_matter_cycles)."""
    for key, value in (keys or {}).items():
        yield key, value
        if isinstance(value, schema.Value) and value.keys is not None:
            yield from ((f"{key}.{inner}", item) for inner, item in spec_values(value.keys))


@pytest.mark.parametrize("condition_type", sorted(schema.CONDITION_TYPES))
def test_la_spec_en_codigo_es_coherente(condition_type):
    # Autocomprobación de `CONDITION_TYPES`: que el validador no pueda saltarse un caso por un hueco de la spec en código.
    spec = schema.CONDITION_TYPES[condition_type]
    # Todo tipo que admite `health` tiene la forma de `levels` fijada (decisión 16: ya no hay «solo objeto no vacío»).
    if "health" in spec.kinds:
        assert spec.levels_keys is not None, f"{condition_type}: admite `health` y no fija la forma de `levels`."
    # Donde hay `levels_keys` hay un sentido de los cortes de LEVELS_ORDERS; donde no, ninguno.
    if spec.levels_keys is not None:
        assert spec.levels_order in schema.LEVELS_ORDERS, f"{condition_type}: `levels_order` {spec.levels_order!r}."
    else:
        assert spec.levels_order is None, f"{condition_type}: `levels_order` sin `levels_keys`."
    # Todos los `Value` tienen un `type` conocido; un `object` trae sus llaves y ningún otro tipo las trae.
    assert set(schema.VALUE_TYPES) == KNOWN_VALUE_TYPES
    for where, value in [*spec_values(spec.params_keys), *spec_values(spec.levels_keys)]:
        assert isinstance(value, schema.Value), f"{condition_type}.{where}: {value!r} no es un `schema.Value`."
        assert value.type in KNOWN_VALUE_TYPES, f"{condition_type}.{where}: `type` desconocido {value.type!r}."
        assert (value.type == "object") == bool(value.keys), f"{condition_type}.{where}: `keys` solo y siempre en `object`."
    # Los pares `params` = `levels` apuntan a llaves que existen.
    for param, level in spec.params_equal_levels:
        assert param in spec.params_keys and level in (spec.levels_keys or {}), (condition_type, param, level)


def test_las_reglas_de_ejemplo_pasan_parse_rule_con_las_familias_de_las_fichas():
    # Las reglas de pipeline/examples.py citan la fuente `ejemplo` (R5) y usan las familias de las fichas, que el
    # dataset de ejemplo copia del catálogo real.
    crops, _, _ = catalog.build(catalog.load())
    families = real_families()
    table = examples.rotation_rules(crops)
    schema.check("rotation_rules", table)
    for row in table.iter_rows(named=True):
        raw = {**row, "params": json.loads(row["params"]), "levels": json.loads(row["levels"]) if row["levels"] else None}
        rule = parse(raw, families=set(families.values()) - {None}, sources={examples.SOURCE_ID})
        assert rule.source_id == examples.SOURCE_ID


# ---------- 3. El catálogo real ----------


def real_families() -> dict[str, str | None]:
    """`crop_id` → `family` de `catalog/crops.yaml` (el descanso no tiene familia)."""
    crops, _, _ = catalog.build(catalog.load())
    return dict(zip(crops["crop_id"].to_list(), crops["family"].to_list(), strict=True))


@pytest.fixture(scope="module")
def real_catalog():
    """Las reglas reales, construidas con las fuentes, la versión y las familias de `catalog/crops.yaml`.

    Si `catalog/rotation_rules.yaml` todavía no existe, falla con un mensaje claro: no se salta en silencio.
    """
    path = Path(rotation_rules.RULES_FILE)
    if not path.exists():
        pytest.fail(f"No existe {path}: HU-062 pide el catálogo de reglas de rotación con fuente.")
    crops_data = catalog.load()
    families = {f for f in real_families().values() if f is not None}
    rules, new_sources = rotation_rules.build(
        rotation_rules.load(path),
        crop_sources=crops_data["sources"],
        known_families=families,
        expected_version=crops_data["version"],
    )
    all_sources = {s["source_id"] for s in crops_data["sources"]} | set(new_sources["source_id"].to_list())
    return rules, all_sources


def rows(rules: pl.DataFrame) -> list[dict]:
    return [
        {**r, "params": json.loads(r["params"]), "levels": json.loads(r["levels"]) if r["levels"] is not None else None}
        for r in rules.iter_rows(named=True)
    ]


def test_el_catalogo_real_cumple_el_esquema_y_cita_fuentes_reales(real_catalog):
    rules, sources = real_catalog
    schema.check("rotation_rules", rules)
    # R8: toda regla cita una fuente de `sources`; R5: ninguna regla real cita la fuente `ejemplo`.
    assert set(rules["source_id"].to_list()) <= sources
    assert examples.SOURCE_ID not in set(rules["source_id"].to_list())


def test_el_catalogo_real_tiene_el_filtro_de_familia_en_ciclos_seguidos(real_catalog):
    rules, _ = real_catalog
    kinds = {(r["kind"], r["condition_type"]) for r in rows(rules)}
    assert ("filter", "same_family_consecutive") in kinds


# Cada criterio de `soil_health` tiene su regla `health` (criterio «como mínimo, una regla por criterio» de HU-062).
# Hasta el 10 de noviembre de 2026 cuatro criterios no tenían regla (nota 9 de HU-062); ese día el equipo fijó sus cortes
# como criterio propio registrado (`criterio_equipo_2026`). También `papa_espera`
# (pest_break) cita esa fuente desde ese día: sus cortes de 3 y 2 ciclos son criterio del equipo (con la FAO 2008 y
# Agrosavia como referencia), decididos por Felipe el 11 nov 2026. Si un criterio pierde su
# regla, la nota de HU-062 debe decirlo y esta prueba se ajusta en el mismo cambio (R1, R8).
TEAM_CRITERION_SOURCE = "criterio_equipo_2026"
TEAM_CRITERION_RULES = {
    "papa_espera": "pest_break",
    "leguminosa_en_rotacion": "nitrogen",
    "materia_organica_ciclos": "organic_carbon",
    "suelo_cubierto": "soil_cover",
    "erosion_pendiente": "erosion",
}


def test_cada_criterio_de_soil_health_tiene_al_menos_una_regla_health(real_catalog):
    # Preparar
    rules, _ = real_catalog
    health = {(r["criterion"], r["condition_type"]) for r in rows(rules) if r["kind"] == "health"}
    # Comprobar
    for criterion, condition_type in CRITERIA.items():
        assert (criterion, condition_type) in health, (
            f"`{criterion}` no tiene una regla `health` `{condition_type}`: si no hay fuente ni criterio del equipo, la "
            f"nota de HU-062 debe decirlo ({EPIC}) y esta prueba se ajusta (R1, R8)."
        )


def test_las_cinco_reglas_del_criterio_del_equipo_citan_su_fuente_propia(real_catalog):
    # Preparar
    rules, sources = real_catalog
    by_id = {r["rule_id"]: r for r in rows(rules)}
    # Comprobar: la fuente existe (R8) y cada regla es `health` de su criterio y la cita.
    assert TEAM_CRITERION_SOURCE in sources
    for rule_id, criterion in TEAM_CRITERION_RULES.items():
        assert rule_id in by_id, f"Falta la regla `{rule_id}` ({criterion})."
        rule = by_id[rule_id]
        assert (rule["kind"], rule["criterion"], rule["source_id"]) == ("health", criterion, TEAM_CRITERION_SOURCE), rule_id


def test_papa_espera_publica_3_ciclos_favorable_y_2_moderate(real_catalog):
    # Felipe, 11 nov 2026 (PR #46): FAO 2008 (3 o más) y Agrosavia en Tibaitatá (2: papa - avena - arveja).
    rules, _ = real_catalog
    rule = next(r for r in rows(rules) if r["rule_id"] == "papa_espera")
    assert rule["params"]["min_cycles"] == rule["levels"]["favorable"] == 3
    assert rule["levels"]["moderate"] == 2
    assert rule["source_id"] == TEAM_CRITERION_SOURCE


def test_en_el_catalogo_real_min_cycles_es_igual_a_favorable_en_pest_break(real_catalog):
    rules, _ = real_catalog
    for r in rows(rules):
        if r["condition_type"] == "family_return_min_cycles" and r["kind"] == "health":
            assert r["params"]["min_cycles"] == r["levels"]["favorable"], r["rule_id"]


# «Matriz esperada» de HU-062, transcrita tal cual: familias de `catalog/crops.yaml` 0.1.0 y solo el filtro
# `same_family_consecutive` por `family`; X = excluye, · = pasa; filas = ciclo anterior, columnas = ciclo siguiente.
MATRIX_ORDER = ["papa", "arveja", "haba", "maiz", "zanahoria", "cebolla_bulbo", "avena_vicia", "descanso"]
MATRIX_FAMILIES = {
    "papa": "Solanaceae",
    "arveja": "Leguminosae",
    "haba": "Leguminosae",
    "maiz": "Gramineae",
    "zanahoria": "Umbelliferae",
    "cebolla_bulbo": "Alliaceae",
    "avena_vicia": "Gramineae",
    "descanso": None,
}
EXPECTED_MATRIX = """
papa           X · · · · · · ·
arveja         · X X · · · · ·
haba           · X X · · · · ·
maiz           · · · X · · X ·
zanahoria      · · · · X · · ·
cebolla_bulbo  · · · · · X · ·
avena_vicia    · · · X · · X ·
descanso       · · · · · · · ·
"""


def expected_matrix() -> dict[tuple[str, str], bool]:
    matrix = {}
    for line in EXPECTED_MATRIX.strip().splitlines():
        previous, *cells = line.split()
        assert len(cells) == len(MATRIX_ORDER), line
        for following, cell in zip(MATRIX_ORDER, cells, strict=True):
            matrix[(previous, following)] = cell == "X"
    return matrix


def violates_same_family(rule: dict, previous: str, following: str, families: dict[str, str | None]) -> bool:
    """`same_family_consecutive` mínimo (el motor, HU-081, aún no existe): misma `family` en dos ciclos seguidos.

    Un ciclo sin familia (el descanso) nunca viola el filtro. `params.families` nulo: todas las familias.
    """
    family = families[previous]
    if family is None or family != families[following]:
        return False
    scope = rule["params"]["families"]
    return scope is None or family in scope


def filters_of(rules: pl.DataFrame) -> list[dict]:
    filters = [r for r in rows(rules) if r["kind"] == "filter"]
    unknown = sorted({r["condition_type"] for r in filters} - {"same_family_consecutive"})
    assert not unknown, (
        f"Hay filtros que la «Matriz esperada» de HU-062 no considera ({unknown}): actualice la matriz en la HU y en esta prueba."
    )
    return filters


def test_las_familias_de_las_fichas_son_las_de_la_matriz_esperada():
    # Si cambian las familias, la «Matriz esperada» se actualiza en HU-062 y aquí, en el mismo cambio.
    assert real_families() == MATRIX_FAMILIES


def test_la_matriz_esperada_es_la_del_filtro_de_familia_con_las_fichas_reales():
    # Comprueba la transcripción de la matriz y la función auxiliar sin depender de catalog/rotation_rules.yaml.
    rule = {"rule_id": "familia_seguida", "params": {"families": None}}
    families = real_families()
    actual = {(p, f): violates_same_family(rule, p, f, families) for p in MATRIX_ORDER for f in MATRIX_ORDER}
    assert actual == expected_matrix()


def test_un_segundo_filtro_de_familia_solo_para_solanaceae_no_cambia_la_matriz_esperada():
    # El catálogo puede tener varias reglas `same_family_consecutive` (una general y otra para Solanaceae con fuente
    # del ICA): un par queda excluido si alguna lo excluye, y la segunda no excluye nada que la primera deje pasar.
    general = {"rule_id": "familia_seguida", "params": {"families": None}}
    solanaceae = {"rule_id": "papa_seguida", "params": {"families": ["Solanaceae"]}}
    families = real_families()
    actual = {
        (p, f): any(violates_same_family(r, p, f, families) for r in (general, solanaceae)) for p in MATRIX_ORDER for f in MATRIX_ORDER
    }
    assert actual == expected_matrix()
    # Y la de Solanaceae sola excluye solo papa → papa.
    only = {(p, f) for p in MATRIX_ORDER for f in MATRIX_ORDER if violates_same_family(solanaceae, p, f, families)}
    assert only == {("papa", "papa")}


def test_la_matriz_de_pares_coincide_con_la_matriz_esperada(real_catalog):
    # Preparar
    rules, _ = real_catalog
    families = real_families()
    filters = filters_of(rules)
    assert filters, "No hay reglas `filter`: la matriz no evalúa nada."
    expected = expected_matrix()
    # Actuar: para cada par, las reglas `filter` que se evalúan y las que lo excluyen.
    actual = {}
    for previous in MATRIX_ORDER:
        for following in MATRIX_ORDER:
            violated = [r["rule_id"] for r in filters if violates_same_family(r, previous, following, families)]
            actual[(previous, following)] = violated
    # Comprobar
    differences = [
        f"{previous} → {following}: esperado {'X' if expected[(previous, following)] else '·'}, reglas que excluyen {violated}"
        for (previous, following), violated in actual.items()
        if bool(violated) != expected[(previous, following)]
    ]
    assert not differences, "\n".join(differences)


def test_la_rotacion_de_referencia_de_agrosavia_no_viola_ningun_filtro(real_catalog):
    """Papa → avena → arveja (tratamiento T2 de Agrosavia en Tibaitatá, `agrosavia_tibaitata_2022`) no viola ningún filtro.

    En Tibaitatá se sembró avena sola (*Avena sativa* Cayuse, sin vicia): la secuencia se mapea a `papa` → `avena_vicia`
    → `arveja` porque `avena_vicia` es lo más cercano del catálogo (nota 2 de HU-062). El ensayo respalda la secuencia, no
    el aporte de la vicia; para el filtro da igual, porque `same_family_consecutive` compara solo `family` (Gramineae).
    """
    rules, _ = real_catalog
    families = real_families()
    sequence = ["papa", "avena_vicia", "arveja"]
    violated = [
        (previous, following, r["rule_id"])
        for previous, following in zip(sequence, sequence[1:], strict=False)
        for r in filters_of(rules)
        if violates_same_family(r, previous, following, families)
    ]
    assert violated == [], (
        f"La rotación de referencia (en Tibaitatá, avena sola, mapeada a `avena_vicia`; nota 2 de HU-062) viola: {violated}"
    )
