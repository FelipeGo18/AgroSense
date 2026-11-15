"""HU-212, PR B: forma de los cinco criterios de `soil_health`, `nitrogen` y `pest_break`. Escritas antes del código
(HU-121); fallan por ImportError hasta que exista `backend/engine/rotations/soil_health.py`.

Las fichas y las reglas reales se leen aquí de `catalog/` (el motor no lee archivos, R6). Lo marcado «EJEMPLO» está
armado para la prueba (R5) y no es del catálogo. Supuestos por confirmar: (S1) `previous_crop_ids` va del más
reciente al más antiguo y la función lo invierte; (S2) con `min_cycles = 3` la función mira hasta 3 cultivos
anteriores: una papa anterior a 4 ciclos ya no cuenta y da `favorable` igual (supuesto 4); (S3) la razón contiene
`reason_template.format(...)` y termina con `TEAM_NOTE`; (S4) `sequence` es la tupla de `crop_id` de los ciclos.
"""

from pathlib import Path

import pytest
import yaml

from backend.engine.rotations.soil_health import (
    SOIL_CRITERIA,
    TEAM_CRITERION,
    TEAM_NOTE,
    Criterion,
    HealthRule,
    SoilCrop,
    level_from_cuts,
    soil_health,
)

RAIZ = Path(__file__).resolve().parents[2] / "catalog"


def _cultivos() -> dict[str, SoilCrop]:
    fichas = yaml.safe_load((RAIZ / "crops.yaml").read_text(encoding="utf-8"))["crops"]
    return {
        f["crop_id"]: SoilCrop(
            f["crop_id"],
            f["kind"]["v"],
            f["family"]["v"] if "family" in f else None,
            tuple(f.get("secondary_families", {}).get("v") or ()),
            f["fixes_nitrogen"]["v"] if "fixes_nitrogen" in f else None,
        )
        for f in fichas
    }


def _reglas_reales() -> list[HealthRule]:
    filas = yaml.safe_load((RAIZ / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
    return [
        HealthRule(
            r["rule_id"],
            r["criterion"],
            r["condition_type"],
            r["params"],
            r["levels"],
            r["reason_template"],
            r["source_id"],
        )
        for r in filas
        if r["kind"] == "health"
    ]


CULTIVOS = _cultivos()
REGLAS = _reglas_reales()
NITROGENO = next(r for r in REGLAS if r.rule_id == "leguminosa_en_rotacion")
PAPA_ESPERA = next(r for r in REGLAS if r.rule_id == "papa_espera")
# EJEMPLO (R5): cultivo sin el dato `fixes_nitrogen` y regla de plagas para Leguminosae. No son del catálogo.
SIN_DATO = SoilCrop("ejemplo_sin_dato", "crop", "Poaceae", (), None)
LEGUMINOSA_VUELVE = HealthRule(
    "ejemplo_leguminosa_vuelve",
    "pest_break",
    "family_return_min_cycles",
    {"family": "Leguminosae", "min_cycles": 2},
    {"favorable": 2, "moderate": 1},
    "La familia {family} vuelve al terreno después de {cycles} ciclos de otras familias",
    "ejemplo",
)


def _sh(sequence, previous=(), rules=REGLAS, crops=CULTIVOS):
    return soil_health(tuple(sequence), crops, list(previous), rules)


def test_el_catalogo_trae_las_reglas_health_que_usa_la_prueba():
    assert len(REGLAS) == 5
    assert (NITROGENO.levels, NITROGENO.source_id) == ({"favorable": 1, "moderate": 1}, TEAM_CRITERION)
    assert (PAPA_ESPERA.levels, PAPA_ESPERA.params["min_cycles"]) == ({"favorable": 3, "moderate": 2}, 3)
    assert CULTIVOS["avena_vicia"].fixes_nitrogen is True and CULTIVOS["avena_vicia"].kind == "cover"


# --- Forma ---


def test_devuelve_siempre_las_cinco_llaves_con_su_criterio():
    res = _sh(("papa", "arveja", "maiz"))
    assert set(res) == set(SOIL_CRITERIA) and len(SOIL_CRITERIA) == 5
    assert all(isinstance(c, Criterion) for c in res.values())


def test_insufficient_data_nunca_trae_nivel_y_available_siempre_lo_trae():
    res = _sh(("papa", "arveja", "maiz"))
    assert [c.status for c in res.values()].count("insufficient_data") >= 3
    assert all((c.level is None) == (c.status == "insufficient_data") for c in res.values())
    assert all(c.reasons for c in res.values())  # dice qué falta o qué evaluó


def test_sin_suelo_ni_pendiente_ni_duracion_organic_carbon_soil_cover_y_erosion_son_insufficient_data():
    res = _sh(("papa", "arveja", "maiz"))
    for criterio in ("organic_carbon", "soil_cover", "erosion"):
        assert (res[criterio].status, res[criterio].level) == ("insufficient_data", None), criterio


def test_nitrogen_sin_su_regla_es_insufficient_data_sin_inventar_corte():
    sin_regla = [r for r in REGLAS if r.rule_id != "leguminosa_en_rotacion"]
    assert len(sin_regla) == 4
    c = _sh(("papa", "arveja", "maiz"), rules=sin_regla)["nitrogen"]  # con una leguminosa
    assert (c.status, c.level, c.rule_ids, c.source_ids) == ("insufficient_data", None, (), ())
    assert c.reasons


def test_pest_break_sin_su_regla_es_insufficient_data_sin_inventar_corte():
    sin_regla = [r for r in REGLAS if r.rule_id != "papa_espera"]
    c = _sh(("papa", "arveja", "maiz"), ["papa"], rules=sin_regla)["pest_break"]
    assert (c.status, c.level, c.rule_ids, c.source_ids) == ("insufficient_data", None, (), ())


def test_sin_ninguna_regla_los_cinco_son_insufficient_data_con_ids_vacios():
    res = _sh(("papa", "arveja", "maiz"), rules=[])
    assert set(res) == set(SOIL_CRITERIA)
    assert all(c.level is None and c.rule_ids == () and c.source_ids == () for c in res.values())
    assert all(c.status == "insufficient_data" for c in res.values())


# --- level_from_cuts ---


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(4, "favorable"), (3, "favorable"), (2.9, "moderate"), (2, "moderate"), (1.9, "unfavorable"), (1, "unfavorable"), (0, "unfavorable")],
)
def test_cortes_de_papa_espera_3_y_2(valor, esperado):
    assert level_from_cuts(valor, PAPA_ESPERA.levels) == esperado


@pytest.mark.parametrize(("valor", "esperado"), [(2, "favorable"), (1, "favorable"), (0.9, "unfavorable"), (0, "unfavorable")])
def test_cortes_de_leguminosa_1_y_1_no_tienen_franja_intermedia(valor, esperado):
    assert level_from_cuts(valor, NITROGENO.levels) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(0, "favorable"), (1, "favorable"), (1.1, "moderate"), (3, "moderate"), (3.1, "unfavorable"), (8, "unfavorable")],
)
def test_cortes_maximos_1_y_3_con_more_is_better_false(valor, esperado):
    assert level_from_cuts(valor, {"favorable": 1, "moderate": 3}, more_is_better=False) == esperado


# --- nitrogen ---


def test_nitrogen_dos_secuencias_iguales_salvo_una_leguminosa():
    con = _sh(("papa", "arveja", "maiz"))["nitrogen"]
    sin = _sh(("papa", "zanahoria", "maiz"))["nitrogen"]
    assert (con.status, con.level) == ("available", "favorable")  # 1 ciclo de arveja llega al corte 1
    assert (sin.status, sin.level) == ("available", "unfavorable")  # 0 ciclos: no llega a 1


def test_nitrogen_avena_vicia_cuenta_como_leguminosa_por_la_vicia():
    assert _sh(("papa", "avena_vicia", "maiz"))["nitrogen"].level == "favorable"


def test_nitrogen_cultivo_sin_dato_sin_otra_leguminosa_es_insufficient_data():
    crops = {**CULTIVOS, SIN_DATO.crop_id: SIN_DATO}
    c = _sh(("papa", SIN_DATO.crop_id, "maiz"), crops=crops)["nitrogen"]  # conteo 0 y un ciclo sin dato (supuesto 5)
    assert (c.status, c.level) == ("insufficient_data", None)
    assert c.rule_ids == ("leguminosa_en_rotacion",)  # tiene regla; falta el dato


def test_nitrogen_cultivo_sin_dato_con_otra_leguminosa_que_alcanza_el_corte_es_favorable():
    crops = {**CULTIVOS, SIN_DATO.crop_id: SIN_DATO}
    c = _sh(("arveja", SIN_DATO.crop_id, "maiz"), crops=crops)["nitrogen"]  # conteo 1 llega a 1
    assert (c.status, c.level) == ("available", "favorable")


def test_nitrogen_cita_la_regla_la_fuente_del_equipo_y_la_nota():
    c = _sh(("papa", "arveja", "maiz"))["nitrogen"]
    assert c.rule_ids == ("leguminosa_en_rotacion",)
    assert TEAM_CRITERION in c.source_ids
    assert len(c.reasons) >= 1
    assert NITROGENO.reason_template.format(count=1) in c.reasons[0]
    assert all(r.endswith(TEAM_NOTE) for r in c.reasons)


def test_nitrogen_la_razon_cuenta_dos_ciclos_con_leguminosa():
    c = _sh(("arveja", "haba", "maiz"))["nitrogen"]  # arveja y haba: 2 ciclos
    assert NITROGENO.reason_template.format(count=2) in c.reasons[0]


# --- pest_break ---


def test_pest_break_papa_avena_vicia_arveja_sin_anteriores_no_es_unfavorable_es_favorable():
    c = _sh(("papa", "avena_vicia", "arveja"))["pest_break"]  # la papa no vuelve (supuesto 4)
    assert (c.status, c.level) == ("available", "favorable")
    assert c.rule_ids == ("papa_espera",)
    assert TEAM_CRITERION in c.source_ids
    assert all(r.endswith(TEAM_NOTE) for r in c.reasons) and c.reasons


@pytest.mark.parametrize(
    ("anteriores", "nivel", "entre"),
    [
        # Del más reciente al más antiguo; la papa anterior es la última. Entre las dos papas: ciclos de otras familias.
        (["maiz", "zanahoria", "haba", "papa"], "favorable", 3),
        (["zanahoria", "haba", "papa"], "moderate", 2),
        (["haba", "papa"], "unfavorable", 1),
        (["papa"], "unfavorable", 0),
    ],
)
def test_pest_break_cuenta_los_ciclos_entre_las_dos_papas(anteriores, nivel, entre):
    c = _sh(("papa", "arveja", "maiz"), anteriores)["pest_break"]
    assert (c.status, c.level) == ("available", nivel)
    if entre:
        assert PAPA_ESPERA.reason_template.format(family="Solanaceae", cycles=entre) in c.reasons[0]
    assert all(r.endswith(TEAM_NOTE) for r in c.reasons) and c.reasons


def test_pest_break_rotacion_actual_de_agrosavia_repetida_hacia_atras_da_moderate():
    # Papa, avena_vicia y arveja; los anteriores son sus propios cultivos repetidos hacia atrás: dos ciclos entre papas.
    c = _sh(("papa", "avena_vicia", "arveja"), ["arveja", "avena_vicia", "papa"])["pest_break"]
    assert c.level == "moderate"
    assert PAPA_ESPERA.reason_template.format(family="Solanaceae", cycles=2) in c.reasons[0]


def test_pest_break_el_descanso_cuenta_como_un_ciclo_sin_la_familia():
    # papa, descanso, maiz, [papa]: 2 ciclos entre las papas (con el descanso). Sin contarlo serían 1: unfavorable.
    c = _sh(("papa", "arveja", "maiz"), ["maiz", "descanso", "papa"])["pest_break"]
    assert c.level == "moderate"


def test_pest_break_cuenta_secondary_families():
    # EJEMPLO: regla de Leguminosae con min 2. avena_vicia (Gramineae + Leguminosae) y arveja, con maiz entre las dos:
    # 1 ciclo entre apariciones: moderate. Sin contar la familia secundaria, la leguminosa no volvería (favorable).
    c = _sh(("avena_vicia", "maiz", "arveja"), rules=[LEGUMINOSA_VUELVE])["pest_break"]
    assert (c.status, c.level) == ("available", "moderate")
    assert c.rule_ids == ("ejemplo_leguminosa_vuelve",)
    assert LEGUMINOSA_VUELVE.reason_template.format(family="Leguminosae", cycles=1) in c.reasons[0]


def test_pest_break_con_varias_vueltas_el_nivel_es_el_de_la_peor():
    # Anteriores [maiz, zanahoria, papa]: papa(previa) y papa del ciclo 1 con 2 ciclos entre ellas (moderate); luego
    # papa del ciclo 3 con 1 ciclo entre las dos del plan (unfavorable). Gana la peor.
    c = _sh(("papa", "maiz", "papa"), ["maiz", "zanahoria", "papa"])["pest_break"]
    assert c.level == "unfavorable"
    assert any(PAPA_ESPERA.reason_template.format(family="Solanaceae", cycles=1) in r for r in c.reasons)


def test_pest_break_una_papa_anterior_mas_lejos_que_min_cycles_ya_no_cuenta_y_da_favorable():
    c = _sh(("papa", "arveja", "maiz"), ["maiz", "zanahoria", "haba", "cebolla_bulbo", "papa"])["pest_break"]
    assert c.level == "favorable"  # 4 ciclos de otras familias entre las dos papas (supuesto S2)


# --- Determinismo (R4) ---


def test_misma_entrada_misma_salida_aunque_reglas_y_cultivos_lleguen_en_otro_orden():
    secuencia, anteriores = ("papa", "avena_vicia", "arveja"), ["arveja", "avena_vicia", "papa"]
    base = _sh(secuencia, anteriores)
    assert base == _sh(secuencia, anteriores)
    otro = _sh(secuencia, anteriores, rules=list(reversed(REGLAS)), crops=dict(reversed(list(CULTIVOS.items()))))
    assert base == otro
    assert base["pest_break"].level == "moderate" and base["nitrogen"].level == "favorable"


def test_pest_break_la_peor_vuelta_gana_aunque_sea_la_primera():
    # EJEMPLO: regla de Leguminosae con {favorable: 2, moderate: 1}. Anterior [arveja] y la arveja en el ciclo 1: vuelve
    # con 0 ciclos (unfavorable). La haba del ciclo 3 vuelve con 1 ciclo (maiz) tras la arveja: moderate. La peor es la
    # primera: si el motor tomara la última vuelta, daría moderate y este caso fallaría.
    c = _sh(("arveja", "maiz", "haba"), ["arveja"], rules=[LEGUMINOSA_VUELVE])["pest_break"]
    assert (c.status, c.level) == ("available", "unfavorable")
    assert LEGUMINOSA_VUELVE.reason_template.format(family="Leguminosae", cycles=0) in c.reasons[0]
