"""HU-081, PR D: fase 2 (`high_risk`), armado de `excluded` y modo «actual» (R2, R3, R8). Escritas antes del código
(HU-121).

Los diagnósticos, razones, fuentes y descartadas de estas pruebas son DE EJEMPLO (R5): los arma la prueba, no salen del
motor ni de un dato real. La integración final usa los `phase1` y el catálogo reales con diagnósticos de ejemplo.
Supuestos por confirmar: (S1) los motivos de `current_issues` con el mismo ciclo y `kind` se ordenan por
`rule_id`, luego la señal en el orden del contrato (`P0_SIGNALS`), luego `crop_id`; (S2) con varios motivos del mismo
`kind` en `summarize_exclusions`, el mostrado es el de menor ciclo; (S3) `current_issues` no quita motivos repetidos.
"""

from pathlib import Path

import pytest
import yaml

from backend.engine.rotations.candidates import CropInfo, candidates
from backend.engine.rotations.exclusions import (
    CLIMATE_SIGNALS,
    Excluded,
    ExclusionSummary,
    Phase1Result,
    SignalReason,
    SoilPh,
    current_issues,
    filter_strategies,
    high_risk_motives,
    phase1,
    summarize_exclusions,
)
from backend.engine.rotations.rules import FilterRule, Motive
from backend.engine.signal_score import SignalScore

RAIZ = Path(__file__).resolve().parents[2] / "catalog"
KINDS = ("rule", "not_suitable", "soil_ph", "high_risk")

CRITICA = SignalScore("available", 20, "unfavorable", True)  # DE EJEMPLO: desfavorable y crítica
NO_CRITICA = SignalScore("available", 35, "unfavorable", False)  # DE EJEMPLO: desfavorable, sobre el corte crítico
MODERADA_CRITICA = SignalScore("available", 45, "moderate", True)  # DE EJEMPLO, incoherente a propósito: moderada
FAVORABLE = SignalScore("available", 90, "favorable", False)
SIN_DATOS = SignalScore("insufficient_data", None, None, False)


def _r(score: SignalScore, name: str = "x") -> SignalReason:
    return SignalReason(score, f"RAZON DE EJEMPLO {name}", (f"fuente_ejemplo_{name}", "fuente_ejemplo_b"))


def _ciclo(**signals) -> dict[str, SignalReason]:
    return {n: _r(s, n) for n, s in signals.items()}


def _bueno() -> dict[str, SignalReason]:
    return _ciclo(water=FAVORABLE, frost=FAVORABLE, heat=FAVORABLE, soil=FAVORABLE)


def _m(kind: str, cycle: int = 1, **kw) -> Motive:  # DE EJEMPLO
    return Motive(kind, cycle, f"RAZON DE EJEMPLO {kind}", ("fuente_ejemplo_a",), **kw)


# ---------- high_risk ----------


def test_las_senales_de_clima_son_water_frost_heat():
    assert CLIMATE_SIGNALS == ("water", "frost", "heat")


def test_helada_critica_en_el_ciclo_2_da_un_motivo_con_su_razon_y_sus_fuentes():
    d = [_bueno(), {**_bueno(), "frost": _r(CRITICA, "frost")}, _bueno()]
    motivos = high_risk_motives(("papa", "maiz", "arveja"), d)
    assert len(motivos) == 1
    m = motivos[0]
    assert (m.kind, m.cycle, m.signal) == ("high_risk", 2, "frost")
    assert m.reason == "RAZON DE EJEMPLO frost"
    assert m.source_ids == ("fuente_ejemplo_frost", "fuente_ejemplo_b")
    assert high_risk_motives(("papa", "maiz", "arveja"), [_bueno(), _bueno(), _bueno()]) == []  # el otro lado


def test_water_y_heat_criticos_tambien_dan_motivo_en_su_ciclo():
    for senal, ciclo in (("water", 1), ("heat", 2)):
        d = [_bueno(), _bueno()]
        assert high_risk_motives(("papa", "maiz"), d) == []
        d[ciclo - 1] = {**_bueno(), senal: _r(CRITICA, senal)}
        motivos = high_risk_motives(("papa", "maiz"), d)
        assert [(m.cycle, m.signal) for m in motivos] == [(ciclo, senal)]


def test_desfavorable_no_critica_no_da_motivo_y_critica_pero_moderada_tampoco():
    for score in (NO_CRITICA, MODERADA_CRITICA):
        for senal in CLIMATE_SIGNALS:
            assert high_risk_motives(("papa",), [{**_bueno(), senal: _r(score, senal)}]) == []
    assert len(high_risk_motives(("papa",), [{**_bueno(), "frost": _r(CRITICA)}])) == 1  # control


def test_oferta_y_mercado_criticos_nunca_excluyen_y_suelo_tampoco():
    for senal in ("supply", "market", "soil"):  # supply y market hoy no tienen curva; el motor no depende de eso (R3)
        assert high_risk_motives(("papa",), [{**_bueno(), senal: _r(CRITICA, senal)}]) == []
    assert len(high_risk_motives(("papa",), [{**_bueno(), "heat": _r(CRITICA)}])) == 1  # control


def test_sin_datos_no_da_motivo_y_un_ciclo_none_no_se_revisa():
    assert high_risk_motives(("papa",), [{**_bueno(), "frost": _r(SIN_DATOS)}]) == []  # R1
    d = [None, {**_bueno(), "water": _r(CRITICA, "water")}]
    assert [(m.cycle, m.signal) for m in high_risk_motives(("descanso", "papa"), d)] == [(2, "water")]
    assert high_risk_motives(("descanso", "papa"), [None, _bueno()]) == []


def test_dos_senales_criticas_en_un_ciclo_dan_dos_motivos_en_orden_water_frost_heat():
    c = {"heat": _r(CRITICA, "heat"), "water": _r(CRITICA, "water"), "frost": _r(FAVORABLE, "frost")}
    assert [m.signal for m in high_risk_motives(("papa",), [c])] == ["water", "heat"]
    c["frost"] = _r(CRITICA, "frost")
    assert [m.signal for m in high_risk_motives(("papa",), [c])] == ["water", "frost", "heat"]


# ---------- summarize_exclusions ----------


def test_counts_cuenta_una_vez_por_el_primer_motivo_y_la_suma_es_el_total():
    descartadas = [  # DE EJEMPLO
        (("a", "b"), [_m("not_suitable"), _m("rule", rule_id="r1")]),  # cuenta como rule
        (("c", "d"), [_m("soil_ph", crop_id="c")]),
        (("e", "f"), [_m("high_risk", signal="frost"), _m("high_risk", 2, signal="heat")]),
    ]
    resumen = summarize_exclusions(descartadas)
    assert resumen.counts == {"rule": 1, "not_suitable": 0, "soil_ph": 1, "high_risk": 1}
    assert sum(resumen.counts.values()) == len(descartadas) == 3


def test_las_cuatro_llaves_estan_siempre_y_con_lista_vacia_todo_vale_cero():
    resumen = summarize_exclusions([])
    assert resumen.excluded == ()
    assert dict(resumen.counts) == dict.fromkeys(KINDS, 0)
    una = summarize_exclusions([(("a", "b"), [_m("soil_ph", crop_id="a")])])
    assert set(una.counts) == set(KINDS) and una.counts["soil_ph"] == 1


def test_el_motivo_mostrado_es_el_primero_del_orden_fijo_aunque_lleguen_desordenados():
    desordenados = [_m("high_risk", signal="water"), _m("soil_ph", crop_id="a"), _m("not_suitable", crop_id="b")]
    resumen = summarize_exclusions([(("a", "b"), desordenados)])
    (e,) = resumen.excluded
    assert isinstance(e, Excluded) and e.crop_ids == ("a", "b")
    assert e.motive.kind == "not_suitable" and e.motive_count == 3
    assert resumen.counts["not_suitable"] == 1 and resumen.counts["soil_ph"] == 0


def test_excluded_va_por_numero_de_motivos_y_luego_por_crop_ids_aunque_lleguen_al_reves():
    descartadas = [  # DE EJEMPLO
        (("z", "y"), [_m("rule", rule_id="r1"), _m("soil_ph", crop_id="z")]),  # 2 motivos
        (("b", "c"), [_m("rule", rule_id="r1")]),
        (("a", "c"), [_m("high_risk", signal="frost")]),
    ]
    esperado = [("a", "c"), ("b", "c"), ("z", "y")]
    assert [e.crop_ids for e in summarize_exclusions(descartadas).excluded] == esperado
    assert [e.crop_ids for e in summarize_exclusions(descartadas[::-1]).excluded] == esperado
    assert [e.motive_count for e in summarize_exclusions(descartadas).excluded] == [1, 1, 2]
    # El número de motivos manda antes que el nombre: con 2 motivos, ("a", "a") va después de ("z", "z") con 1, aunque
    # sea alfabéticamente menor. Si el orden fuera solo por crop_ids, este caso fallaría.
    contra = [(("a", "a"), [_m("rule", rule_id="r1"), _m("soil_ph", crop_id="a")]), (("z", "z"), [_m("rule", rule_id="r1")])]
    assert [e.crop_ids for e in summarize_exclusions(contra).excluded] == [("z", "z"), ("a", "a")]


def test_con_12_descartadas_excluded_trae_10_y_counts_suma_12():
    descartadas = [((f"ej{i:02d}", "x"), [_m(KINDS[i % 4], signal="frost" if i % 4 == 3 else None)]) for i in range(12)]
    resumen = summarize_exclusions(descartadas)
    assert isinstance(resumen, ExclusionSummary)
    assert len(resumen.excluded) == 10 and sum(resumen.counts.values()) == 12
    assert [e.crop_ids[0] for e in resumen.excluded] == [f"ej{i:02d}" for i in range(10)]  # las dos últimas quedan fuera
    assert len(summarize_exclusions(descartadas, limit=3).excluded) == 3
    assert len(summarize_exclusions(descartadas[:10]).excluded) == 10  # borde: justo 10


def test_summarize_exclusions_es_determinista_y_no_depende_del_orden_de_entrada():
    descartadas = [((f"ej{i:02d}", "x"), [_m(KINDS[i % 4], signal="water" if i % 4 == 3 else None)]) for i in range(12)]
    primero = summarize_exclusions(descartadas)
    assert primero.excluded
    assert summarize_exclusions(descartadas) == primero
    assert summarize_exclusions(descartadas[::-1]) == primero


def test_el_motivo_mostrado_no_depende_del_orden_de_los_motivos_de_la_estrategia():
    for orden in (("frost", "water"), ("water", "frost")):
        (e,) = summarize_exclusions([(("a", "b"), [_m("high_risk", signal=s) for s in orden])]).excluded
        assert e.motive.signal == "water" and e.motive_count == 2


def test_una_estrategia_sin_motivos_lanza_value_error_con_sus_crop_ids():
    with pytest.raises(ValueError, match="papa.*maiz"):
        summarize_exclusions([(("papa", "maiz"), [])])


# ---------- current_issues ----------


def test_current_issues_junta_las_dos_fases_sin_descartar_y_ordena_por_ciclo_y_kind():
    fase1 = Phase1Result((_m("rule", 1, rule_id="r1"), _m("soil_ph", 2, crop_id="a")), ("limitacion de ejemplo",))
    hr = [_m("high_risk", 2, signal="frost"), _m("high_risk", 1, signal="water")]
    issues = current_issues(fase1, hr)
    assert isinstance(issues, tuple) and len(issues) == 4
    assert [(m.cycle, m.kind) for m in issues] == [(1, "rule"), (1, "high_risk"), (2, "soil_ph"), (2, "high_risk")]
    assert issues[3].signal == "frost" and issues[1].signal == "water"


def test_current_issues_ordena_las_senales_como_el_contrato_y_no_por_nombre():
    hr = [_m("high_risk", signal="frost"), _m("high_risk", signal="water")]
    assert [m.signal for m in current_issues(Phase1Result((), ()), hr)] == ["water", "frost"]  # por nombre: frost, water


def test_current_issues_sin_motivos_es_la_tupla_vacia_y_con_solo_una_fase_devuelve_esa():
    assert current_issues(Phase1Result((), ()), []) == ()
    assert [m.kind for m in current_issues(Phase1Result((), ()), [_m("high_risk", signal="heat")])] == ["high_risk"]
    solo1 = Phase1Result((_m("not_suitable", crop_id="a"),), ())
    assert [m.kind for m in current_issues(solo1, [])] == ["not_suitable"]


# ---------- integración corta con el catálogo real y diagnósticos de ejemplo ----------


def _catalogo() -> dict[str, CropInfo]:
    fichas = yaml.safe_load((RAIZ / "crops.yaml").read_text(encoding="utf-8"))["crops"]

    def v(f, campo):
        return f[campo]["v"] if campo in f else None

    return {
        f["crop_id"]: CropInfo(
            f["crop_id"], f["kind"]["v"], v(f, "family"), tuple(f.get("secondary_families", {}).get("v") or ()),
            v(f, "name_es"), v(f, "article"), v(f, "tmean_min_c"), v(f, "tmean_opt_min_c"), v(f, "tmean_opt_max_c"),
            v(f, "tmean_max_c"), v(f, "ph_min"), v(f, "ph_max"), f["ph_min"]["s"] if "ph_min" in f else None,
        )
        for f in fichas
    }  # fmt: skip


def _filtros() -> list[FilterRule]:
    filas = yaml.safe_load((RAIZ / "rotation_rules.yaml").read_text(encoding="utf-8"))["rules"]
    campos = ("rule_id", "condition_type", "params", "reason_template", "source_id")
    return [FilterRule(*(r[k] for k in campos)) for r in filas if r["kind"] == "filter"]


def test_integracion_cycles_2_solo_diagnostica_las_que_pasaron_la_fase_1():
    cultivos, filtros = _catalogo(), _filtros()
    explica = lambda crop, apt: (f"RAZON DE EJEMPLO {crop.crop_id}", ("fuente_ejemplo_a",))  # noqa: E731
    suelo = SoilPh(4.5, 6.5, "ejemplo")  # DE EJEMPLO (R5)
    todas = candidates(list(cultivos.values()), 2)
    fase1 = {c: phase1(c, [], cultivos, filtros, 14.4, suelo, explica) for c in todas}
    fuera1 = {c for c, r in fase1.items() if r.motives}
    assert len(todas) == 56 and fuera1 and len(fuera1) < 56  # hay de las dos clases: si no, la prueba no prueba nada

    def diagnostica(secuencia):  # DOBLE DE PRUEBA (R5): helada crítica en todo ciclo de arveja; el resto, bueno
        assert tuple(secuencia) not in fuera1, f"se diagnosticó {secuencia}, descartada en la fase 1"
        helada = {"frost": _r(CRITICA, "frost")}
        return [None if cultivos[c].kind == "fallow" else {**_bueno(), **(helada if c == "arveja" else {})} for c in secuencia]

    r = filter_strategies(todas, [], cultivos, filtros, 14.4, suelo, explica, diagnostica, limit=1000)
    vivas = [c for c in todas if c not in fuera1]
    assert r.survivors == tuple(c for c in vivas if "arveja" not in c) and r.survivors  # en el orden recibido
    n_hr = len([c for c in vivas if "arveja" in c])
    assert n_hr and r.summary.counts["high_risk"] == n_hr  # precisión de Felipe en el #90: solo las vivas
    assert sum(r.summary.counts.values()) == len(fuera1) + n_hr == len(todas) - len(r.survivors)
    assert len(r.limitations) == len(set(r.limitations))
    assert filter_strategies(todas, [], cultivos, filtros, 14.4, suelo, explica, diagnostica, limit=1000) == r  # R4
