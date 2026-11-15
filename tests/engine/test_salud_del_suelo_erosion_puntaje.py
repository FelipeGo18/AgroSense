"""HU-224 y HU-212, PR D: `erosion` y el puntaje `soil` de `soil_health`. Escritas antes del código (HU-121); fallan por
ImportError (`SlopeInfo`, `soil_score`) hasta que `motor-api` amplíe `backend/engine/rotations/soil_health.py`.

Lo marcado «EJEMPLO» está armado para la prueba (R5): las pendientes y las duraciones no son de ninguna zona. Los meses
descubiertos son (días de descanso + huecos) / 30,4; con días enteros no se cae exacto en 1,0 ni en 3,0 meses, así que
los bordes se prueban con el día de cada lado (30 y 31 días; 91 y 92). Supuestos por confirmar: (S1) `slope` y razón con
coma decimal y un decimal (`{slope}` «20,0», `{months}` «1,0»); (S2) con pendiente menor que 12, `{months}` de la razón no
se prueba: la spec no dice qué muestra; (S3) `slope_pct` nulo y `slope` nulo dan lo mismo; (S4) un descanso sin duración
con pendiente menor que 12 no se prueba (la spec dice `favorable` sin duraciones, y `cycle_days=None` sí se prueba).
"""

import re
from pathlib import Path

import polars as pl
import pytest
import yaml

from backend.engine.rotations.soil_health import (
    DAYS_PER_MONTH,
    TEAM_CRITERION,
    TEAM_NOTE,
    Criterion,
    HealthRule,
    SlopeInfo,
    SoilCarbon,
    SoilCrop,
    soil_health,
    soil_score,
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
EROSION = next(r for r in REGLAS if r.rule_id == "erosion_pendiente")
# EJEMPLO (R5): ni la pendiente ni el suelo son de un municipio; SlopeInfo lleva la fuente real de la pendiente.
EMPINADO = SlopeInfo(20.0, "nasadem", "municipality")
BAJO = SoilCarbon(20.0, 3.84, 141.2, "soilgrids")
CON_DESCANSO = ("papa", "descanso", "maiz")


def _crit(slope, dias_descanso=30, secuencia=CON_DESCANSO, gaps=(0, 0)):
    """`erosion` de (papa, descanso, maiz) con papa 165 y maíz 180 días; el descanso dura `dias_descanso` (EJEMPLO)."""
    dias = [165, dias_descanso, 180]
    return soil_health(secuencia, CULTIVOS, [], REGLAS, slope=slope, cycle_days=dias, gap_days=[*gaps, None])["erosion"]


def _c(level):
    return Criterion("available" if level else "insufficient_data", level, (), (), ())


def test_el_catalogo_trae_la_regla_y_los_cortes_que_usa_la_prueba():
    assert EROSION.condition_type == "bare_months_on_slope" and EROSION.params == {"slope_pct_from": 12}
    assert EROSION.levels == {"favorable": 1, "moderate": 3}
    assert EROSION.source_id == TEAM_CRITERION and DAYS_PER_MONTH == 30.4


# --- erosion: la pendiente decide si cuenta ---


@pytest.mark.parametrize("dias", [30, 400])
def test_con_pendiente_menor_que_12_es_favorable_aunque_el_suelo_quede_descubierto_mucho(dias):
    c = _crit(SlopeInfo(11.9, "nasadem", "lot"), dias_descanso=dias)  # 400 días = 13,2 meses descubiertos
    assert (c.status, c.level) == ("available", "favorable")
    assert "11,9" in c.reasons[0]  # S1


def test_con_pendiente_menor_que_12_no_necesita_duraciones():
    c = soil_health(CON_DESCANSO, CULTIVOS, [], REGLAS, slope=SlopeInfo(11.9, "nasadem", "lot"), cycle_days=None)["erosion"]
    assert (c.status, c.level) == ("available", "favorable")


def test_la_pendiente_igual_a_12_ya_cuenta_porque_el_corte_es_mayor_o_igual():
    # 12,0 con 92 días descubiertos (3,03 meses): unfavorable. A 11,99 con los mismos días, favorable.
    assert _crit(SlopeInfo(12.0, "nasadem", "lot"), 92).level == "unfavorable"
    assert _crit(SlopeInfo(11.99, "nasadem", "lot"), 92).level == "favorable"


# --- erosion: los meses descubiertos pasan por los cortes máximos 1 y 3 ---


@pytest.mark.parametrize(
    ("dias", "meses", "nivel"),
    [
        (30, "1,0", "favorable"),  # 30 / 30,4 = 0,987: llega a favorable (<= 1) y se ve «1,0»
        (31, "1,0", "moderate"),  # 31 / 30,4 = 1,020: pasa de 1; se ve «1,0» y no se decide con el redondeo
        (34, "1,1", "moderate"),  # 34 / 30,4 = 1,118: 1,1 meses
        (91, "3,0", "moderate"),  # 91 / 30,4 = 2,993: llega a moderate (<= 3)
        (92, "3,0", "unfavorable"),  # 92 / 30,4 = 3,026: pasa de 3; se ve «3,0»
        (95, "3,1", "unfavorable"),  # 95 / 30,4 = 3,125: 3,1 meses
    ],
)
def test_los_cortes_de_1_y_3_meses_en_el_borde(dias, meses, nivel):
    c = _crit(EMPINADO, dias_descanso=dias)  # descanso `dias` y huecos 0
    assert (c.status, c.level) == ("available", nivel)
    assert EROSION.reason_template.format(slope="20,0", months=meses) in c.reasons[0]


def test_el_hueco_entre_ciclos_cuenta_como_descubierto():
    # EJEMPLO (R5): descanso 20 + huecos 5 y 6 = 31 días = 1,02 meses: moderate. Sin huecos, 20 días = 0,66: favorable.
    assert _crit(EMPINADO, 20, gaps=(0, 0)).level == "favorable"
    c = _crit(EMPINADO, 20, gaps=(5, 6))
    assert c.level == "moderate" and EROSION.reason_template.format(slope="20,0", months="1,0") in c.reasons[0]


def test_sin_descanso_solo_cuentan_los_huecos():
    # (papa, avena_vicia, maiz): el abono verde cubre. Huecos 5 y 6 = 11 días = 0,36 meses: favorable.
    c = _crit(EMPINADO, 30, secuencia=("papa", "avena_vicia", "maiz"), gaps=(5, 6))
    assert c.level == "favorable" and EROSION.reason_template.format(slope="20,0", months="0,4") in c.reasons[0]


def test_hu224_con_pendiente_el_abono_verde_da_erosion_mejor_que_el_descanso_desnudo():
    # EJEMPLO (R5): mismos 100 días en el ciclo del medio. Con descanso, 100 / 30,4 = 3,29 meses (unfavorable); con
    # abono verde, 0 meses descubiertos (favorable).
    con_abono = _crit(EMPINADO, 100, secuencia=("papa", "avena_vicia", "maiz"))
    con_descanso = _crit(EMPINADO, 100)
    assert (con_abono.level, con_descanso.level) == ("favorable", "unfavorable")
    assert RANGO[con_abono.level] > RANGO[con_descanso.level]


# --- erosion: sin datos (R1) ---


@pytest.mark.parametrize("slope", [None, SlopeInfo(None, "nasadem", "municipality")])
def test_sin_pendiente_es_insufficient_data_con_la_regla(slope):
    c = _crit(slope)
    assert (c.status, c.level) == ("insufficient_data", None)  # R1
    assert c.rule_ids == ("erosion_pendiente",) and len(c.reasons) >= 1


def test_con_pendiente_de_12_o_mas_y_un_ciclo_sin_duracion_es_insufficient_data():
    c = soil_health(CON_DESCANSO, CULTIVOS, [], REGLAS, slope=EMPINADO, cycle_days=[165, None, 180], gap_days=[0, 0, None])["erosion"]
    assert (c.status, c.level, c.rule_ids) == ("insufficient_data", None, ("erosion_pendiente",))
    sin = soil_health(CON_DESCANSO, CULTIVOS, [], REGLAS, slope=EMPINADO)["erosion"]  # cycle_days=None
    assert (sin.status, sin.level) == ("insufficient_data", None)


# --- erosion: la razón y las fuentes ---


def test_la_razon_termina_con_la_nota_y_cita_la_regla_y_las_dos_fuentes():
    c = _crit(SlopeInfo(20.0, "nasadem", "lot"))
    assert len(c.reasons) >= 1 and all(r.endswith(TEAM_NOTE) for r in c.reasons)
    assert c.rule_ids == ("erosion_pendiente",)
    assert TEAM_CRITERION in c.source_ids and "nasadem" in c.source_ids  # R8
    assert "no medido en su lote" in c.reasons[0]  # dato de la zona (R10)


def test_erosion_real_de_un_municipio_decide_el_nivel_comparando_su_pendiente_con_12():
    # Esperado calculado aquí desde data/published/municipalities.parquet (NASADEM, HU-206): la de menor y la de mayor
    # pendiente del dataset. Con 92 días descubiertos (3,03 meses): unfavorable si la pendiente es >= 12; si no, favorable.
    d = pl.read_parquet(RAIZ / "data" / "published" / "municipalities.parquet").filter(pl.col("slope_pct").is_not_null())
    assert d.height > 0
    filas = [d.sort("slope_pct").row(0, named=True), d.sort("slope_pct").row(-1, named=True)]
    for r in filas:
        esperado = "unfavorable" if r["slope_pct"] >= EROSION.params["slope_pct_from"] else "favorable"
        assert _crit(SlopeInfo(r["slope_pct"], "nasadem", "municipality"), 92).level == esperado


# --- Que no se rompa lo anterior, y determinismo (R4) ---


def test_con_slope_los_otros_cuatro_criterios_no_cambian():
    dias = [165, 120, 180]
    kw = {"soil": BAJO, "cycle_days": dias, "gap_days": [3, 4, None]}
    sin = soil_health(CON_DESCANSO, CULTIVOS, ["papa"], REGLAS, **kw)
    con = soil_health(CON_DESCANSO, CULTIVOS, ["papa"], REGLAS, slope=EMPINADO, **kw)
    otros = ("nitrogen", "organic_carbon", "soil_cover", "pest_break")
    assert all(con[n] == sin[n] for n in otros) and all(sin[n].status == "available" for n in otros)
    assert sin["erosion"].status == "insufficient_data" and con["erosion"].status == "available"


def test_misma_entrada_misma_salida_aunque_las_reglas_lleguen_en_otro_orden():
    base = _crit(EMPINADO, 100)
    assert base == _crit(EMPINADO, 100)
    invertidas = list(reversed(REGLAS))
    otro = soil_health(CON_DESCANSO, CULTIVOS, [], invertidas, slope=EMPINADO, cycle_days=[165, 100, 180], gap_days=[0, 0, None])["erosion"]
    assert base == otro and base.level == "unfavorable"


# --- soil_score (puntaje del criterio `soil` de HU-082) ---


def test_cinco_criterios_favorable_moderate_unfavorable_favorable_y_sin_datos_dan_63():
    niveles = ("favorable", "moderate", "unfavorable", "favorable", None)
    criterios = dict(zip(("nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion"), map(_c, niveles), strict=True))
    assert soil_score(criterios) == 63  # (100 + 50 + 0 + 100) / 4 = 62,5: mitad hacia arriba; el nulo no entra


def test_todos_sin_datos_o_ninguno_dan_none():
    assert soil_score({n: _c(None) for n in ("nitrogen", "erosion", "pest_break")}) is None  # R1
    assert soil_score({}) is None


@pytest.mark.parametrize(("nivel", "puntaje"), [("favorable", 100), ("moderate", 50), ("unfavorable", 0)])
def test_un_solo_criterio_con_nivel_vale_100_50_o_0(nivel, puntaje):
    assert soil_score({"nitrogen": _c(nivel), "erosion": _c(None)}) == puntaje


def _p(favorables=0, moderados=0, desfavorables=0):
    niveles = ["favorable"] * favorables + ["moderate"] * moderados + ["unfavorable"] * desfavorables
    return soil_score({f"c{i}": _c(n) for i, n in enumerate(niveles)})


def test_el_redondeo_es_mitad_hacia_arriba_y_x_coma_49_baja():
    # EJEMPLO (R5). x,5 sube: (50 + 0 + 0 + 0) / 4 = 12,5 -> 13; (100 + 50 + 0 + 0) / 4 = 37,5 -> 38.
    assert (_p(0, 1, 3), _p(1, 1, 2)) == (13, 38)
    # Casi x,5 baja: (100 + 50 + 0 * 5) / 7 = 21,43 -> 21; 100 / 41 = 2,44 -> 2.
    assert (_p(1, 1, 5), _p(1, 0, 40)) == (21, 2)
    # Y por encima de x,5 sube: (100 + 100 + 0) / 3 = 66,67 -> 67; (100 + 0 + 0) / 3 = 33,33 -> 33.
    assert (_p(2, 0, 1), _p(1, 0, 2)) == (67, 33)


def test_el_puntaje_no_depende_del_orden():
    niveles = ["favorable", "moderate", "unfavorable", "favorable", None]
    a = soil_score({f"c{i}": _c(n) for i, n in enumerate(niveles)})
    b = soil_score({f"c{i}": _c(n) for i, n in enumerate(reversed(niveles))})
    assert a == b == 63


# --- HU-224: huecos que faltan (R1), razón fija y prueba de 120 y 180 días ---

TEXTO_DURACION = "Falta la duración de algún ciclo de la estrategia"
TEXTO_HUECO = "Falta el hueco entre algún par de ciclos de la estrategia"


def _con(dias, gaps, secuencia=CON_DESCANSO, slope=EMPINADO):
    return soil_health(secuencia, CULTIVOS, [], REGLAS, slope=slope, cycle_days=dias, gap_days=gaps)["erosion"]


@pytest.mark.parametrize("gaps", [None, [0, None, None], [None, 0, None], [0, 0], [0, 0, 0], [0, 7, None], [0, -1, None]])
def test_un_hueco_que_falta_o_invalido_con_pendiente_es_insufficient_data_y_dice_el_hueco(gaps):
    # EJEMPLO (R5): papa -> descanso (90 días) -> maíz en 20 % de pendiente. Contado como 0, daría 2,96 meses: moderate.
    c = _con([165, 90, 180], gaps)
    assert (c.status, c.level) == ("insufficient_data", None)
    assert c.reasons == (f"{TEXTO_HUECO}. {TEAM_NOTE}",)
    assert c.rule_ids == ("erosion_pendiente",) and c.source_ids == (TEAM_CRITERION,)


def test_sin_duracion_la_razon_dice_la_duracion_aunque_tambien_falte_el_hueco():
    c = _con([165, None, 180], None)
    assert (c.status, c.reasons) == ("insufficient_data", (f"{TEXTO_DURACION}. {TEAM_NOTE}",))


def test_con_pendiente_menor_que_12_los_huecos_que_faltan_no_hacen_falta():
    c = _con([165, 90, 180], None, slope=SlopeInfo(11.9, "nasadem", "lot"))
    assert (c.status, c.level) == ("available", "favorable")


def test_el_texto_fijo_con_pendiente_menor_esta_como_lo_escribe_la_spec():
    c = _crit(SlopeInfo(11.9, "nasadem", "lot"))
    assert c.reasons == (
        "Pendiente estimada del terreno: 11,9 % (dato de la zona, no medido en su lote), por debajo de 12 %: "
        f"con esa pendiente el suelo descubierto no se cuenta para la erosión. {TEAM_NOTE}",
    )


def test_hu224_pendiente_20_descanso_de_120_dias_es_unfavorable_y_con_abono_verde_favorable():
    # EJEMPLO (R5): 120 / 30,4 = 3,9 meses descubiertos con el descanso; con abono verde, 0.
    descanso = _con([165, 120, 180], [0, 0, None])
    abono = _con([165, 120, 180], [0, 0, None], secuencia=("papa", "avena_vicia", "maiz"))
    assert descanso.level == "unfavorable" and "3,9 meses" in descanso.reasons[0]
    assert abono.level == "favorable" and "0,0 meses" in abono.reasons[0]
    sin_duracion = _con([165, None, 180], [0, 0, None])
    assert (sin_duracion.status, sin_duracion.level) == ("insufficient_data", None)


@pytest.mark.parametrize(("hueco_1", "hueco_2"), [(0, 0), (6, 6), (0, 6), (6, 0)])
def test_hu224_descanso_de_180_dias_es_unfavorable_con_cualquier_hueco_de_0_a_6(hueco_1, hueco_2):
    # EJEMPLO (R5): los 180 días del descanso todavía no están en el catálogo (HU-063); aquí son una entrada de la
    # prueba. 180 / 30,4 = 5,9 meses; con huecos de 6 y 6, 6,3.
    c = _con([165, 180, 180], [hueco_1, hueco_2, None])
    assert (c.status, c.level) == ("available", "unfavorable")


def test_hu212_las_razones_de_los_cinco_criterios_usan_coma_decimal_y_terminan_con_el_sufijo_del_equipo():
    # EJEMPLO (R5): una estrategia con los cinco criterios evaluados.
    cr = soil_health(CON_DESCANSO, CULTIVOS, ["papa"], REGLAS, soil=BAJO, slope=EMPINADO, cycle_days=[165, 120, 180], gap_days=[3, 4, None])
    assert all(c.status == "available" for c in cr.values())
    for nombre, c in cr.items():
        assert all(r.endswith(f". {TEAM_NOTE}") for r in c.reasons), nombre
        assert not any(re.search(r"\d\.\d", r) for r in c.reasons), nombre  # coma decimal, nunca punto
