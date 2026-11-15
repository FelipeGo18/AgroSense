"""HU-212, PR C: `organic_carbon` y `soil_cover` de `soil_health`. Escritas antes del código (HU-121); fallan por
ImportError (`SoilCarbon`) o por nivel hasta que `motor-api` amplíe `backend/engine/rotations/soil_health.py`.

Las fichas y las reglas reales se leen de `catalog/`. Lo marcado «EJEMPLO» está armado para la prueba (R5): el suelo y
las duraciones de los casos de borde no son datos de ninguna zona. Supuestos por confirmar: (S1) los números de la razón
llevan coma decimal y un decimal: `pct` «98,7» y `{soc_range}` «3,8 a 141,2» (el contrato dice coma decimal para el
rango; `pct` se asume igual); (S2) `cycle_days` y `gap_days` van en el orden de los ciclos; (S3) la razón de
`soil_cover` solo llena `{pct}`: los meses (días / 30,4) no se prueban porque el `reason_template` no los usa;
(S4) no se prueba `gap_days = None` con `cycle_days` dado: la spec no lo dice.
"""

from pathlib import Path

import polars as pl
import pytest
import yaml

from backend.engine.rotations.soil_health import (
    DAYS_PER_MONTH,
    TEAM_CRITERION,
    TEAM_NOTE,
    HealthRule,
    SoilCarbon,
    SoilCrop,
    soil_health,
)

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "catalog"
RANGO = {"unfavorable": 0, "moderate": 1, "favorable": 2}


def _cultivos() -> dict[str, SoilCrop]:
    fichas = yaml.safe_load((CATALOGO / "crops.yaml").read_text(encoding="utf-8"))["crops"]
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
    filas = yaml.safe_load((CATALOGO / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
    return [
        HealthRule(r["rule_id"], r["criterion"], r["condition_type"], r["params"], r["levels"], r["reason_template"], r["source_id"])
        for r in filas
        if r["kind"] == "health"
    ]


CULTIVOS = _cultivos()
REGLAS = _reglas_reales()
CARBONO = next(r for r in REGLAS if r.rule_id == "materia_organica_ciclos")
COBERTURA = next(r for r in REGLAS if r.rule_id == "suelo_cubierto")
# Duración real de crop_stages (dataset 2026.11.18): papa 165, maíz 180, haba 175 días.
PAPA_MAIZ_HABA = (("papa", "maiz", "haba"), [165, 180, 175])
# EJEMPLO (R5): suelo de carbono bajo (20 < 29) con su rango p05 a p95; no es de ningún municipio.
BAJO = SoilCarbon(20.0, 3.84, 141.2, "soilgrids")
# EJEMPLO (R5): suelo de carbono normal (45 >= 29).
NORMAL = SoilCarbon(45.0, 30.0, 60.0, "soilgrids")


def _sh(sequence, soil=None, days=None, gaps=None, rules=REGLAS, crops=CULTIVOS):
    return soil_health(tuple(sequence), crops, [], rules, soil=soil, cycle_days=days, gap_days=gaps)


def _carbono(sequence, soil):
    return _sh(sequence, soil=soil)["organic_carbon"]


def _cobertura(sequence, days, gaps=(0, 0)):
    return _sh(sequence, days=list(days), gaps=list(gaps))["soil_cover"]


def test_el_catalogo_trae_las_reglas_y_los_cortes_que_usa_la_prueba():
    assert (CARBONO.params, CARBONO.source_id) == ({"soc_low_g_kg": 29}, TEAM_CRITERION)
    assert CARBONO.levels == {"low": {"favorable": 2, "moderate": 1}, "normal": {"favorable": 1, "moderate": 0}}
    assert (COBERTURA.levels, COBERTURA.source_id) == ({"favorable": 80, "moderate": 60}, TEAM_CRITERION)
    assert DAYS_PER_MONTH == 30.4
    assert [CULTIVOS[c].kind for c in ("papa", "avena_vicia", "descanso")] == ["crop", "cover", "fallow"]


# --- organic_carbon ---


@pytest.mark.parametrize(
    ("secuencia", "ciclos", "nivel"),
    [
        (("papa", "maiz", "haba"), 0, "unfavorable"),  # 0 < corte moderate 1
        (("papa", "avena_vicia", "maiz"), 1, "moderate"),  # 1: llega a moderate 1, no a favorable 2
        (("avena_vicia", "papa", "descanso"), 2, "favorable"),  # abono verde + descanso: llega a 2
        (("descanso", "papa", "descanso"), 2, "favorable"),  # dos descansos
        (("papa", "descanso", "maiz"), 1, "moderate"),  # el descanso solo cuenta como 1
    ],
)
def test_carbono_bajo_cuenta_abono_verde_y_descanso_contra_los_cortes_2_y_1(secuencia, ciclos, nivel):
    c = _carbono(secuencia, BAJO)
    assert (c.status, c.level) == ("available", nivel)
    assert CARBONO.reason_template.format(count=ciclos, soc_level="bajo", soc_range="3,8 a 141,2") in c.reasons[0]


@pytest.mark.parametrize(("secuencia", "nivel"), [(("papa", "maiz", "haba"), "moderate"), (("papa", "avena_vicia", "maiz"), "favorable")])
def test_carbono_normal_con_45_cero_ciclos_es_moderate_y_uno_es_favorable(secuencia, nivel):
    c = _carbono(secuencia, NORMAL)  # normal: favorable 1, moderate 0
    assert (c.status, c.level) == ("available", nivel)
    assert "normal" in c.reasons[0]


def test_el_mismo_numero_de_ciclos_da_otro_nivel_segun_el_carbono():
    sin_abono = ("papa", "maiz", "haba")
    assert _carbono(sin_abono, BAJO).level == "unfavorable"  # con carbono bajo, sin abono verde no es favorable
    assert _carbono(sin_abono, NORMAL).level == "moderate"


def test_borde_29_es_normal_y_justo_debajo_es_bajo():
    # Spec: «menor es low, si no normal». 29 no es menor que 29: normal (0 ciclos: moderate). 28,99: bajo (unfavorable).
    en_el_corte = _carbono(("papa", "maiz", "haba"), SoilCarbon(29.0, 20.0, 40.0, "soilgrids"))
    debajo = _carbono(("papa", "maiz", "haba"), SoilCarbon(28.99, 20.0, 40.0, "soilgrids"))
    assert (en_el_corte.level, debajo.level) == ("moderate", "unfavorable")
    assert "normal" in en_el_corte.reasons[0] and "bajo" in debajo.reasons[0]


def test_los_residuos_de_los_cultivos_no_cuentan():
    # Papa, maíz y haba: ningún abono verde ni descanso. Con carbono bajo, unfavorable y la razón dice 0 ciclos.
    c = _carbono(("papa", "maiz", "haba"), BAJO)
    assert c.level == "unfavorable"
    assert "Ciclos de abono verde o descanso: 0" in c.reasons[0]


def test_con_carbono_bajo_la_estrategia_con_abono_verde_da_organic_carbon_mejor_que_la_misma_sin_el():
    con = _carbono(("papa", "avena_vicia", "maiz"), BAJO)
    sin = _carbono(("papa", "zanahoria", "maiz"), BAJO)
    assert RANGO[con.level] > RANGO[sin.level]


def test_carbono_la_razon_termina_con_la_nota_y_cita_la_regla_y_las_dos_fuentes():
    c = _carbono(("papa", "avena_vicia", "maiz"), BAJO)
    assert len(c.reasons) >= 1 and all(r.endswith(TEAM_NOTE) for r in c.reasons)
    assert c.rule_ids == ("materia_organica_ciclos",)
    assert TEAM_CRITERION in c.source_ids and "soilgrids" in c.source_ids  # R8, R10
    assert "250 m" in c.reasons[0]  # estimación de 250 m (R10)


@pytest.mark.parametrize("suelo", [None, SoilCarbon(None, None, None, "soilgrids")])
def test_carbono_sin_suelo_o_sin_soc_es_insufficient_data_con_la_regla(suelo):
    c = _carbono(("papa", "avena_vicia", "maiz"), suelo)
    assert (c.status, c.level) == ("insufficient_data", None)  # R1
    assert c.rule_ids == ("materia_organica_ciclos",) and c.reasons


def test_carbono_real_de_duitama_decide_el_nivel_por_su_soc_contra_29():
    # Esperado calculado aquí desde data/published/soil_municipality.parquet (SoilGrids, municipio 15238).
    fila = pl.read_parquet(RAIZ / "data" / "published" / "soil_municipality.parquet").filter(pl.col("municipality_id") == "15238")
    assert fila.height == 1
    r = fila.row(0, named=True)
    assert r["soc_g_kg"] is not None and r["soc_p05"] is not None and r["soc_p95"] is not None
    suelo = SoilCarbon(r["soc_g_kg"], r["soc_p05"], r["soc_p95"], r["source_id"])
    bajo = r["soc_g_kg"] < CARBONO.params["soc_low_g_kg"]
    esperado = {"sin": "unfavorable" if bajo else "moderate", "con": "moderate" if bajo else "favorable"}
    sin = _carbono(("papa", "maiz", "haba"), suelo)
    con = _carbono(("papa", "avena_vicia", "maiz"), suelo)
    assert (sin.level, con.level) == (esperado["sin"], esperado["con"])
    rango = f"{r['soc_p05']:.1f} a {r['soc_p95']:.1f}".replace(".", ",")
    assert rango in sin.reasons[0] and ("bajo" if bajo else "normal") in sin.reasons[0]
    assert r["source_id"] == "soilgrids" and "soilgrids" in sin.source_ids


# --- soil_cover ---


def test_papa_maiz_haba_con_huecos_3_y_4_cubre_98_7_por_ciento_y_es_favorable():
    secuencia, dias = PAPA_MAIZ_HABA
    c = _cobertura(secuencia, dias, gaps=(3, 4))  # 520 cubiertos de 520 + 7 = 527: 98,67 %
    assert (c.status, c.level) == ("available", "favorable")
    assert COBERTURA.reason_template.format(pct="98,7") in c.reasons[0]


@pytest.mark.parametrize(
    ("dias", "pct", "nivel"),
    [
        # EJEMPLO (R5): (papa, descanso, maiz) con huecos 0: cubiertos = papa + maíz; el descanso es descubierto.
        ([50, 20, 30], "80,0", "favorable"),  # 80 / 100: justo en el corte
        ([49, 20, 30], "79,8", "moderate"),  # 79 / 99 = 79,79: apenas debajo
        ([30, 40, 30], "60,0", "moderate"),  # 60 / 100: justo en el corte
        ([29, 40, 30], "59,6", "unfavorable"),  # 59 / 99 = 59,60: debajo de 60
    ],
)
def test_los_cortes_80_y_60_en_el_borde(dias, pct, nivel):
    c = _cobertura(("papa", "descanso", "maiz"), dias)
    assert c.level == nivel
    assert COBERTURA.reason_template.format(pct=pct) in c.reasons[0]


def test_el_nivel_sale_del_valor_sin_redondear_79_96_se_muestra_80_0_y_es_moderate():
    # EJEMPLO (R5): 7.996 días cubiertos de 10.000 = 79,96 %, que con un decimal se ve «80,0». Si se decidiera con el
    # valor redondeado, llegaría al corte 80 y sería favorable.
    c = _cobertura(("papa", "descanso", "maiz"), [4000, 2004, 3996])
    assert c.level == "moderate"
    assert COBERTURA.reason_template.format(pct="80,0") in c.reasons[0]


def test_el_descanso_es_suelo_descubierto_y_se_ve_en_el_porcentaje():
    # EJEMPLO (R5): el descanso no tiene etapas hoy; aquí 120 días. 165 + 180 = 345 cubiertos de 465: 74,19 %.
    con_descanso = _cobertura(("papa", "descanso", "maiz"), [165, 120, 180])
    con_abono = _cobertura(("papa", "avena_vicia", "maiz"), [165, 120, 180])  # mismos días, pero cubre: 100 %
    assert (con_descanso.level, con_abono.level) == ("moderate", "favorable")
    assert COBERTURA.reason_template.format(pct="74,2") in con_descanso.reasons[0]
    assert COBERTURA.reason_template.format(pct="100,0") in con_abono.reasons[0]


def test_el_hueco_cuenta_como_descubierto_0_da_mas_porcentaje_que_6():
    # EJEMPLO (R5): (papa, descanso, maiz) [40, 20, 40]: 80 cubiertos. Con huecos 0: 80/100 = 80,0 (favorable);
    # con huecos 6 y 6: 80/112 = 71,43 (moderate).
    sin_hueco = _cobertura(("papa", "descanso", "maiz"), [40, 20, 40], gaps=(0, 0))
    con_hueco = _cobertura(("papa", "descanso", "maiz"), [40, 20, 40], gaps=(6, 6))
    assert (sin_hueco.level, con_hueco.level) == ("favorable", "moderate")
    assert COBERTURA.reason_template.format(pct="80,0") in sin_hueco.reasons[0]
    assert COBERTURA.reason_template.format(pct="71,4") in con_hueco.reasons[0]


def test_un_ciclo_sin_duracion_da_insufficient_data_con_la_regla():
    c = _cobertura(("papa", "descanso", "maiz"), [165, None, 180])  # el descanso sin etapas, como hoy (HU-063)
    assert (c.status, c.level) == ("insufficient_data", None)  # R1
    assert c.rule_ids == ("suelo_cubierto",) and c.source_ids == (TEAM_CRITERION,) and c.reasons


def test_sin_cycle_days_soil_cover_es_insufficient_data():
    c = _sh(("papa", "maiz", "haba"))["soil_cover"]
    assert (c.status, c.level, c.rule_ids) == ("insufficient_data", None, ("suelo_cubierto",))


def test_soil_cover_la_razon_termina_con_la_nota_y_cita_solo_la_regla_del_equipo():
    secuencia, dias = PAPA_MAIZ_HABA
    c = _cobertura(secuencia, dias, gaps=(3, 4))
    assert len(c.reasons) >= 1 and all(r.endswith(TEAM_NOTE) for r in c.reasons)
    assert c.rule_ids == ("suelo_cubierto",) and TEAM_CRITERION in c.source_ids


# --- Que no se rompa el PR B, y determinismo (R4) ---


def test_nitrogen_y_pest_break_no_cambian_con_el_suelo_y_las_duraciones_y_erosion_sigue_pendiente():
    secuencia, dias = PAPA_MAIZ_HABA
    base = soil_health(secuencia, CULTIVOS, ["papa"], REGLAS)
    con = soil_health(secuencia, CULTIVOS, ["papa"], REGLAS, soil=BAJO, cycle_days=dias, gap_days=[3, 4])
    assert con["nitrogen"] == base["nitrogen"] and con["pest_break"] == base["pest_break"]
    assert con["nitrogen"].level == "favorable"  # la haba fija nitrógeno
    assert (con["erosion"].status, con["erosion"].level) == ("insufficient_data", None)  # es del PR D


def test_misma_entrada_misma_salida_aunque_reglas_y_cultivos_lleguen_en_otro_orden():
    secuencia, dias = PAPA_MAIZ_HABA
    kw = {"soil": BAJO, "days": dias, "gaps": [3, 4]}
    base = _sh(secuencia, **kw)
    assert base == _sh(secuencia, **kw)
    otro = _sh(secuencia, rules=list(reversed(REGLAS)), crops=dict(reversed(list(CULTIVOS.items()))), **kw)
    assert base == otro
    assert base["organic_carbon"].level == "unfavorable" and base["soil_cover"].level == "favorable"
