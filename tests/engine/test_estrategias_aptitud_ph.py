"""HU-081, PR C, fase 1: motivos `not_suitable` y `soil_ph` y su unión en `phase1` (R1, R3, R8). Escritas antes del
código (HU-121).

Los rangos de temperatura y de pH son los reales de `catalog/crops.yaml`: papa 8, 12, 15 y 16 °C y pH 4,2 a 8,5;
zanahoria pH 4,2 a 8,7. Las temperaturas anuales y los suelos son DE EJEMPLO (R5): con datos reales SoilGrids va de 4,1
a 7,3 y nunca excluye por pH, así que se usa un suelo angosto armado. `explain` es un doble de prueba.
Supuestos por confirmar: (S1) un cultivo sin dato da una sola limitación aunque aparezca en dos ciclos; (S2) el texto
de la limitación nombra al cultivo por `name_es` en minúscula o por `crop_id`; (S3) en `phase1` las limitaciones van
por primera aparición, con las de aptitud antes que las de pH.
"""

from pathlib import Path

import yaml

from backend.engine.rotations.candidates import CropInfo
from backend.engine.rotations.exclusions import SoilPh, ph_motives, phase1, suitability_motives
from backend.engine.rotations.rules import FilterRule
from backend.engine.suitability import Suitability

RAIZ = Path(__file__).resolve().parents[2] / "catalog"


def _cultivos() -> dict[str, CropInfo]:
    fichas = yaml.safe_load((RAIZ / "crops.yaml").read_text(encoding="utf-8"))["crops"]

    def v(f, campo):
        return f[campo]["v"] if campo in f else None

    return {
        f["crop_id"]: CropInfo(
            f["crop_id"],
            f["kind"]["v"],
            v(f, "family"),
            tuple(f.get("secondary_families", {}).get("v") or ()),
            v(f, "name_es"),
            v(f, "article"),
            v(f, "tmean_min_c"),
            v(f, "tmean_opt_min_c"),
            v(f, "tmean_opt_max_c"),
            v(f, "tmean_max_c"),
            v(f, "ph_min"),
            v(f, "ph_max"),
            f["ph_min"]["s"] if "ph_min" in f else None,
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


def _explica(crop: CropInfo, aptitud: Suitability):  # DOBLE DE PRUEBA (R5): no es la razón real de /diagnostics.
    return f"RAZON DE EJEMPLO {crop.crop_id} {aptitud.level} {aptitud.exceeded}", ("fuente_ejemplo_a", f"fuente_ejemplo_{crop.crop_id}")


def _apt(secuencia, temp):
    return suitability_motives(secuencia, CULTIVOS, temp, _explica)


def _menciona(texto: str, crop_id: str) -> bool:
    return crop_id in texto.lower() or (CULTIVOS[crop_id].name_es or "").lower() in texto.lower()


# ---------- not_suitable ----------


def test_la_ficha_real_de_la_papa_trae_los_cuatro_limites_y_su_fuente_de_ph():
    papa = CULTIVOS["papa"]
    assert (papa.tmean_min_c, papa.tmean_opt_min_c, papa.tmean_opt_max_c, papa.tmean_max_c) == (8, 12, 15, 16)
    assert (papa.ph_min, papa.ph_max, papa.ph_source_id) == (4.2, 8.5, "fao_ecocrop")


def test_papa_con_28_4_grados_no_es_apta_y_el_motivo_lleva_lo_que_dio_explain():
    motivos, limitaciones = _apt(("papa", "maiz"), 28.4)
    assert limitaciones == []
    assert len(motivos) == 1
    m = motivos[0]
    assert (m.kind, m.cycle, m.crop_id) == ("not_suitable", 1, "papa")
    assert m.reason == "RAZON DE EJEMPLO papa not_suitable max"
    assert m.source_ids == ("fuente_ejemplo_a", "fuente_ejemplo_papa")


def test_papa_con_14_4_grados_es_apta():
    assert _apt(("papa", "maiz"), 14.4) == ([], [])


def test_borde_papa_apta_justo_en_16_0_y_en_8_0_y_no_apta_un_poco_mas_alla():
    assert _apt(("papa",), 16.0) == ([], [])
    assert _apt(("papa",), 8.0) == ([], [])
    assert [m.crop_id for m in _apt(("papa",), 16.1)[0]] == ["papa"]
    assert _apt(("papa",), 7.9)[0][0].reason == "RAZON DE EJEMPLO papa not_suitable min"


def test_el_cultivo_no_apto_en_los_ciclos_1_y_3_da_un_solo_motivo_en_el_ciclo_1():
    motivos, _ = _apt(("papa", "maiz", "papa"), 28.4)
    assert [(m.cycle, m.crop_id) for m in motivos] == [(1, "papa")]


def test_cada_cultivo_no_apto_da_su_propio_motivo_en_su_primer_ciclo():
    motivos, _ = _apt(("maiz", "papa", "arveja"), 3.5)  # maíz 10-47, arveja 4-30 y papa 8-16: los tres quedan fuera
    assert [(m.cycle, m.crop_id) for m in motivos] == [(1, "maiz"), (2, "papa"), (3, "arveja")]


def test_el_descanso_no_se_excluye_ni_es_limitacion_con_28_4_ni_sin_temperatura():
    assert _apt(("descanso", "maiz"), 28.4) == ([], [])
    assert _apt(("descanso", "maiz"), None)[1] != []  # control: maíz sin temperatura sí da limitación
    _, limitaciones = _apt(("descanso", "descanso"), None)
    assert limitaciones == []
    assert [m.crop_id for m in _apt(("descanso", "papa"), 28.4)[0]] == ["papa"]


def test_sin_temperatura_anual_no_excluye_y_da_una_limitacion_por_cultivo():
    motivos, limitaciones = _apt(("papa", "maiz", "papa"), None)
    assert motivos == []
    assert len(limitaciones) == 2  # S1
    assert _menciona(limitaciones[0], "papa") and _menciona(limitaciones[1], "maiz")


def test_sin_un_limite_de_temperatura_en_la_ficha_no_excluye_y_nombra_el_cultivo():
    cebolla = CULTIVOS["cebolla_bulbo"]
    assert cebolla.tmean_max_c is None  # real: la UPRA no pone límite superior
    motivos, limitaciones = suitability_motives(("cebolla_bulbo",), CULTIVOS, 40.0, _explica)
    assert motivos == []
    assert len(limitaciones) == 1 and _menciona(limitaciones[0], "cebolla_bulbo")


# ---------- soil_ph ----------

SUELO_ACIDO = SoilPh(3.6, 4.0, "ejemplo")  # DE EJEMPLO (R5): más ácido que cualquier dato real de SoilGrids.


def test_zanahoria_con_suelo_3_6_a_4_0_se_excluye_con_la_razon_del_contrato():
    motivos, limitaciones = ph_motives(("maiz", "zanahoria"), CULTIVOS, SUELO_ACIDO)
    assert limitaciones == []
    zan = [m for m in motivos if m.crop_id == "zanahoria"]
    assert len(zan) == 1
    m = zan[0]
    assert (m.kind, m.cycle) == ("soil_ph", 2)
    assert m.reason == "El pH del suelo de la zona (3,6 a 4,0) queda fuera del que tolera la zanahoria (4,2 a 8,7)"
    assert m.source_ids == ("fao_ecocrop", "ejemplo")


def test_con_suelo_4_0_a_4_5_zanahoria_no_se_excluye():
    assert ph_motives(("zanahoria",), CULTIVOS, SoilPh(4.0, 4.5, "ejemplo")) == ([], [])


def test_bordes_del_ph_tocar_el_intervalo_no_excluye_y_pasarse_por_poco_si():
    assert ph_motives(("zanahoria",), CULTIVOS, SoilPh(3.9, 4.2, "ejemplo"))[0] == []  # ph_min 4,2 == p95
    assert ph_motives(("zanahoria",), CULTIVOS, SoilPh(8.7, 9.0, "ejemplo"))[0] == []  # ph_max 8,7 == p05
    assert len(ph_motives(("zanahoria",), CULTIVOS, SoilPh(3.9, 4.1, "ejemplo"))[0]) == 1  # ph_min > p95
    assert len(ph_motives(("zanahoria",), CULTIVOS, SoilPh(8.8, 9.2, "ejemplo"))[0]) == 1  # ph_max < p05


def test_el_cultivo_en_dos_ciclos_da_un_solo_motivo_de_ph_en_el_primero():
    motivos, _ = ph_motives(("zanahoria", "maiz", "zanahoria"), CULTIVOS, SUELO_ACIDO)
    assert [(m.cycle, m.crop_id) for m in motivos if m.crop_id == "zanahoria"] == [(1, "zanahoria")]


def test_el_descanso_no_se_excluye_por_ph_ni_es_limitacion():
    assert ph_motives(("descanso", "papa"), CULTIVOS, SoilPh(4.5, 6.0, "ejemplo")) == ([], [])
    assert ph_motives(("descanso", "descanso"), CULTIVOS, None) == ([], [])
    assert ph_motives(("descanso", "papa"), CULTIVOS, None)[1] != []  # control: papa sin suelo sí da limitación


def test_sin_suelo_no_excluye_y_agrega_una_limitacion():
    motivos, limitaciones = ph_motives(("papa", "zanahoria"), CULTIVOS, None)
    assert motivos == []
    assert limitaciones != []


def test_sin_rango_de_ph_con_fuente_no_excluye_y_nombra_el_cultivo():
    sin_rango = CropInfo("sin_ph", "crop", "Ejemplo", name_es="Sin pH", article="el")  # DE EJEMPLO (R5)
    motivos, limitaciones = ph_motives(("sin_ph",), {"sin_ph": sin_rango}, SUELO_ACIDO)
    assert motivos == []
    assert len(limitaciones) == 1 and ("sin ph" in limitaciones[0].lower() or "sin_ph" in limitaciones[0].lower())


# ---------- phase1 ----------


def _fase1(secuencia, previos, temp, suelo, reglas=None, cultivos=None):
    return phase1(secuencia, previos, cultivos or CULTIVOS, FILTROS if reglas is None else reglas, temp, suelo, _explica)


def test_phase1_junta_y_ordena_por_kind_luego_ciclo_y_luego_rule_id():
    # Orden del contrato («Varios motivos»): primero el `kind` (rule, not_suitable, soil_ph), después el ciclo; así el
    # primero es el que muestra `excluded` (revisión de Felipe, PR #105).
    r = _fase1(("papa", "papa", "zanahoria"), ["papa"], 28.4, SUELO_ACIDO, reglas=list(reversed(FILTROS)))
    orden = [(m.cycle, m.kind, m.rule_id or m.crop_id) for m in r.motives]
    assert orden == [
        (1, "rule", "familia_seguida"),
        (1, "rule", "papa_seguida"),
        (2, "rule", "familia_seguida"),
        (2, "rule", "papa_seguida"),
        (1, "not_suitable", "papa"),
        (1, "soil_ph", "papa"),
        (3, "soil_ph", "zanahoria"),
    ]
    assert isinstance(r.motives, tuple)


def test_phase1_una_regla_en_el_ciclo_2_va_antes_que_el_ph_del_ciclo_1():
    # Caso de la revisión de Felipe (PR #105): pH fuera en el ciclo 1 y regla violada en el ciclo 2 dan `rule` primero.
    # Con el suelo ácido DE EJEMPLO (3,6 a 4,0), la arveja (pH 4,5-8,3) queda fuera en el ciclo 1; arveja -> haba repite
    # Leguminosae en el ciclo 2 (`familia_seguida`). Sin temperatura, la aptitud no da `not_suitable` (solo limitación).
    r = _fase1(("arveja", "haba", "maiz"), [], None, SUELO_ACIDO)
    assert r.motives
    assert (r.motives[0].kind, r.motives[0].cycle, r.motives[0].rule_id) == ("rule", 2, "familia_seguida")
    # El pH del ciclo 1 sí está, pero después de la regla.
    assert any(m.kind == "soil_ph" and m.cycle == 1 for m in r.motives[1:])


def test_phase1_con_suelo_y_temperatura_buenos_y_sin_violaciones_no_tiene_motivos():
    r = _fase1(("papa", "maiz", "descanso"), [], 14.4, SoilPh(4.5, 6.5, "ejemplo"))
    assert r.motives == () and r.limitations == ()


def test_phase1_sin_datos_no_excluye_y_las_limitaciones_no_se_repiten():
    r = _fase1(("papa", "zanahoria", "papa"), [], None, None)
    assert r.motives == ()
    assert r.limitations
    assert len(set(r.limitations)) == len(r.limitations)
    primera_ph = next(i for i, t in enumerate(r.limitations) if "ph" in t.lower())
    assert _menciona(r.limitations[0], "papa")  # S3: la aptitud va antes que el pH
    assert primera_ph > 0


def test_phase1_es_determinista_y_no_depende_del_orden_de_las_reglas_ni_de_los_cultivos():
    args = (("papa", "papa", "zanahoria"), ["papa"])
    primero = _fase1(*args, 28.4, SUELO_ACIDO)
    assert primero.motives
    assert _fase1(*args, 28.4, SUELO_ACIDO) == primero
    invertidos = dict(reversed(list(CULTIVOS.items())))
    assert _fase1(*args, 28.4, SUELO_ACIDO, reglas=list(reversed(FILTROS)), cultivos=invertidos) == primero
