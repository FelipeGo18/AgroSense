"""Casos de referencia del diagnóstico de una ventana (HU-121, PR 2). Todos son de EJEMPLO (R5), salvo la curva, que usa la
ficha real de la papa. Cada resultado esperado sale de `specs/01-reglas.md` («Agregación del semáforo», «Las prioridades del
agricultor», «Orden de las ventanas») y del contrato de `/diagnostics`.

Cada caso arma su entrada con `publicar_ejemplo` (`conftest.py`): la lluvia de GPM IMERG, las heladas por mes y el pH
del suelo son tablas de ejemplo publicadas con `publish()`; el cultivo es la papa real. Los casos de luz, pesos, ventanas, riego y
fuentes de agua corren hoy, también los del suelo (HU-183: con pH 5,5 la señal de suelo sale `favorable`). La oferta (HU-072) no
tiene tabla ni curva: nunca califica y no cambia la luz.
"""

from datetime import date

from fastapi.testclient import TestClient

from backend.engine.curve import crop_curve, score_from_curve
from common.dates import add_months
from common.region import region_today
from tests.engine.casos.conftest import EJEMPLO_CON_IMERG, EJEMPLO_FRIO, diagnostico, valor

# Pesos para una señal con la que se juega y las demás en importancia normal (3); `supply` y `market` no tienen curva
# (thresholds.yaml): siempre `insufficient_data`, así que su peso no importa para la luz.
NORMALES = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
# Lluvia de ejemplo de GPM IMERG que cubre de sobra lo que pide la papa (agua favorable) y la que no alcanza (agua crítica).
LLUVIA_SUFICIENTE_MM, LLUVIA_ESCASA_MM = 200.0, 20.0
# Años de 30 con helada en Samacá (EJEMPLO): 3 de 30 es 10 % (calificación 84, favorable), 9 es 30 % (53, moderada) y 24 es 80 %
# (11, crítica). Con la curva de `thresholds.yaml`: [[0,100],[20,70],[40,40],[100,0]] y crítica bajo 40.
SIN_HELADA, HELADA_MODERADA, HELADA_CRITICA = 3, 9, 24
# Heladas por mes (años de 30): críticas de junio a agosto, moderadas en abril, mayo y septiembre, favorables en el resto.
# Así unas ventanas de siembra son de alto riesgo, otras salen moderadas y otras favorables.
HELADAS_POR_MES = {
    1: SIN_HELADA, 2: SIN_HELADA, 3: SIN_HELADA, 4: HELADA_MODERADA, 5: HELADA_MODERADA, 6: HELADA_CRITICA,
    7: HELADA_CRITICA, 8: HELADA_CRITICA, 9: HELADA_MODERADA, 10: SIN_HELADA, 11: SIN_HELADA, 12: SIN_HELADA,
}  # fmt: skip


def armado(armar_ejemplo, **datos) -> TestClient:
    """La API sobre un dataset de EJEMPLO con agua favorable y sin heladas, más lo que se cambie."""
    base = {"imerg_en": (EJEMPLO_FRIO,), "lluvia_mm": LLUVIA_SUFICIENTE_MM, "helada_anios": SIN_HELADA, "ph": 5.5}
    return armar_ejemplo(**{**base, **datos})


def con(**pesos) -> dict:
    return {**NORMALES, **pesos}


def luz(cuerpo: dict, clave: str = "overall") -> tuple[str, str]:
    return cuerpo[clave]["light"], cuerpo[clave]["action"]


def fecha_en_mes(mes: int) -> str:
    """Una fecha de siembra del próximo `mes` que la API acepta (en el mes en curso, hoy)."""
    hoy = region_today()
    if mes == hoy.month:
        return hoy.isoformat()
    return date(hoy.year + (mes < hoy.month), mes, 3).isoformat()


# ---------- Luces: verde, rojo, no evaluable ----------


def test_ejemplo_luz_verde(armar_ejemplo):
    # Agua, heladas y calor `favorable`; `soil` es favorable (pH 5,5, dentro del óptimo de la papa, 5,0 a 6,2: 100, y cuenta con su
    # peso por defecto) y `supply` y `market` sin curva son `insufficient_data`. El contrapunto es el caso del suelo con pH 9,0.
    # Regla 3: ninguna señal que cuenta es desfavorable y `water` es favorable: verde y `sow`. Regla 5: lo que no tiene datos no
    # cambia la luz y va a `limitations`.
    cuerpo = diagnostico(armado(armar_ejemplo))
    assert luz(cuerpo) == ("green", "sow") and luz(cuerpo, "overall_default") == ("green", "sow")
    assert {n: cuerpo["signals"][n]["level"] for n in ("water", "frost", "heat")} == dict.fromkeys(("water", "frost", "heat"), "favorable")
    suelo = cuerpo["signals"]["soil"]
    assert (suelo["status"], suelo["level"], suelo["score"], suelo["counts"]) == ("available", "favorable", 100, True)
    for nombre in ("supply", "market"):
        assert cuerpo["signals"][nombre]["status"] == "insufficient_data" and cuerpo["signals"][nombre]["level"] is None
    assert cuerpo["limitations"]


def test_ejemplo_luz_roja_por_helada_critica_con_agua_favorable(armar_ejemplo):
    # `frost` desfavorable y crítica (calificación < 40: `critical_below`); agua favorable. Regla 2: roja aunque lo demás sea
    # bueno (R2). Todas las desfavorables son de clima: acción `other_window`; las heladas de todo el año hacen de alto riesgo
    # cada ventana, así que `best_windows` viene vacío, no ausente.
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=HELADA_CRITICA))
    frost = cuerpo["signals"]["frost"]
    assert (frost["level"], frost["critical"]) == ("unfavorable", True) and frost["score"] < 40
    assert cuerpo["signals"]["water"]["level"] == "favorable"
    assert luz(cuerpo) == ("red", "other_window") and luz(cuerpo, "overall_default") == ("red", "other_window")
    assert cuerpo["best_windows"] == []


def test_ejemplo_helada_critica_con_peso_cero_sigue_en_rojo_y_cuenta(armar_ejemplo):
    # Un peso 0 no esconde un riesgo grave de clima (R2): `frost` crítica con peso 0 da rojo y trae `counts = true`.
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=HELADA_CRITICA), priorities=con(frost=0))
    assert cuerpo["signals"]["frost"]["critical"] is True and cuerpo["signals"]["frost"]["counts"] is True
    assert luz(cuerpo) == ("red", "other_window")
    assert cuerpo["overall"]["weights_basis"] == "farmer" and cuerpo["weights"]["frost"] == 0


def test_ejemplo_agua_sin_datos_es_no_evaluable_y_con_peso_cero_no(cliente):
    # `dataset_con_clima` no publica lluvia ni heladas: `water` es `insufficient_data` (R1). Regla 1: si `water` cuenta, la luz es
    # `not_evaluable` con `review_data`. Con peso 0 no cuenta y esa regla no aplica; como ninguna otra señal tiene datos, no hay
    # ninguna que cuente y califique: regla 3, `yellow` con `other_window` (HU-074), sin riesgo ni evidencia de que la ventana sea buena.
    cuerpo = diagnostico(cliente)
    assert cuerpo["signals"]["water"]["status"] == "insufficient_data" and cuerpo["signals"]["water"]["level"] is None
    assert luz(cuerpo) == ("not_evaluable", "review_data") and luz(cuerpo, "overall_default") == ("not_evaluable", "review_data")
    sin_agua = diagnostico(cliente, priorities=con(water=0))
    assert sin_agua["signals"]["water"]["counts"] is False
    assert luz(sin_agua) == ("yellow", "other_window")
    assert luz(sin_agua, "overall_default") == ("not_evaluable", "review_data")  # los pesos de AgroSense sí cuentan el agua


# ---------- Pesos ----------


def test_ejemplo_peso_5_cuenta_un_moderate_como_desfavorable(armar_ejemplo):
    # `frost` moderada (53, no crítica), el resto favorable. Con peso 3 (importancia normal) un `moderate` no frena la luz: regla 3,
    # verde. Con peso 5 cuenta como `unfavorable`: la regla 3 falla (hay una desfavorable) y la 2 no aplica (no es crítica ni
    # hay dos): amarilla y `other_window` (la desfavorable es de clima). El peso por defecto de `frost` en `weights.yaml` 1.0.0 es 4:
    # también cuenta el `moderate` como desfavorable, así que `overall_default` es amarilla.
    api = armado(armar_ejemplo, helada_anios=HELADA_MODERADA)
    normal = diagnostico(api, priorities=con(frost=3))
    mucho = diagnostico(api, priorities=con(frost=5))
    assert normal["signals"]["frost"]["level"] == mucho["signals"]["frost"]["level"] == "moderate"
    assert mucho["signals"]["frost"]["counts"] is True
    assert luz(normal) == ("green", "sow")
    assert luz(mucho) == ("yellow", "other_window")
    assert luz(mucho, "overall_default") == ("yellow", "other_window")


def test_ejemplo_suelo_desfavorable_no_basta_para_rojo_y_con_peso_cero_cambia_la_luz(armar_ejemplo):
    # `soil` desfavorable (pH 9,0, sobre el máximo de la papa: 8,5), las demás favorables. El suelo nunca es crítico (R10) y una sola
    # desfavorable no da rojo: con el peso por defecto (2), amarilla y `rotate` (cambiar de fecha no arregla el suelo). Con `soil` en 0
    # no cuenta: verde y `sow`.
    cuerpo = diagnostico(armado(armar_ejemplo, ph=9.0), priorities=con(soil=0))
    suelo = cuerpo["signals"]["soil"]
    assert suelo["level"] == "unfavorable" and suelo["score"] < 40 and suelo["critical"] is False and suelo["counts"] is False
    assert {n: cuerpo["signals"][n]["level"] for n in ("water", "frost", "heat")} == dict.fromkeys(("water", "frost", "heat"), "favorable")
    assert luz(cuerpo, "overall_default") == ("yellow", "rotate")  # una desfavorable no crítica no da rojo (R2, R10)
    assert luz(cuerpo) == ("green", "sow")
    assert cuerpo["overall"]["weights_basis"] == "farmer" and cuerpo["overall_default"]["weights_basis"] == "default"


# ---------- Ventanas: factor limitante, alto riesgo, mejores ventanas ----------


# El orden de las señales de la spec («Orden de las ventanas»), escrito a mano: el desempate del factor limitante.
ORDEN_DE_SEÑALES = ("water", "frost", "heat", "soil", "supply", "market")


def decena(calificacion: int) -> int:
    """La decena del factor limitante escrita a mano desde la spec: de 0 a 9, y la alta (90 a 100) es una sola. No se importa
    del motor (`limiting_decade`) para que un error ahí no se repita aquí."""
    return min(calificacion // 10, 9)


def _ordenadas(ventanas: list[dict]) -> bool:
    """Orden de la spec: por decena del factor limitante (mayor primero, `decena`), luego por promedio ponderado (mayor
    primero, el nulo al final de su decena) y, en empate, la más temprana."""
    llave = [(-decena(v["limiting_score"]), v["weighted_score"] is None, -(v["weighted_score"] or 0), v["sowing_start"]) for v in ventanas]
    return llave == sorted(llave)


def test_ejemplo_el_factor_limitante_manda_sobre_el_promedio(armar_ejemplo):
    # Con las heladas por mes de `HELADAS_POR_MES` hay ventanas con `frost` favorable (84) y otras moderadas (53 a 59). Ley del
    # mínimo: la mejor es una de las favorables y ninguna de factor más bajo queda antes de una de factor más alto (decena a decena);
    # ninguna de las mejores ventanas tiene una señal crítica (las que la tienen son de alto riesgo y no entran).
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=HELADAS_POR_MES), sowing_date=fecha_en_mes(7))
    ventanas = cuerpo["best_windows"]
    assert len(ventanas) == 3 and _ordenadas(ventanas)
    assert decena(ventanas[0]["limiting_score"]) > decena(ventanas[-1]["limiting_score"])  # hay de dos decenas
    assert ventanas[0]["limiting_score"] >= 70
    assert all(v["limiting_score"] >= 40 for v in ventanas)  # ninguna con una señal crítica (bajo 40)


# Lluvia y heladas por mes para separar la ley del mínimo del promedio (EJEMPLO, R5). Cada ventana de papa dura unos cinco meses y
# `best_windows` empieza siempre el día 1 de cada mes. Lluvia (año seco, mm/mes): 100 de enero a junio y 200 de julio a diciembre;
# heladas (años de 30): 5 en marzo, 9 de julio a diciembre y 0 en los demás meses. ET0 de 80 mm al mes en todos.
LLUVIA_LEY_DEL_MINIMO = {**dict.fromkeys(range(1, 7), 100.0), **dict.fromkeys(range(7, 13), 200.0)}
HELADAS_LEY_DEL_MINIMO = {3: 5, **dict.fromkeys(range(7, 13), 9)}


def test_ejemplo_la_ley_del_minimo_pone_antes_la_ventana_de_mejor_factor_aunque_su_promedio_sea_menor(armar_ejemplo):
    # Ventana A (siembra del 1 de enero, enero a junio) y B (1 de mayo, mayo a octubre), con los pesos por defecto (agua 3, heladas 4,
    # calor 2, suelo 2; oferta y mercado sin curva no entran) y calor 100 y suelo 100 en las dos.
    #   A: lluvia efectiva de 0,8 x 100 - 25 = 55 mm al mes; el balance hídrico (HU-144) da una cobertura de 77 a 78 % y la curva del
    #      agua [[60,40],[80,70]] da 66 (moderada). Heladas: 5 de 30 años = 16,7 %; curva [[0,100],[20,70]] da 75 (favorable).
    #      Factor limitante: agua, 66, decena 6. Promedio: (66x3 + 75x4 + 100x2 + 100x2) / 11 = 898 / 11 = 81,6, es decir 82.
    #   B: de julio a octubre llueve 200 mm y mayo y junio traen 100, la cobertura es 100 % y el agua da 100. Heladas: 9 de 30 años =
    #      30 %; curva [[20,70],[40,40]] da 55 (moderada). Factor limitante: heladas, 55, decena 5.
    #      Promedio: (100x3 + 55x4 + 100x2 + 100x2) / 11 = 920 / 11 = 83,6, es decir 84.
    # B tiene mejor promedio (84 contra 82) pero A tiene mejor factor limitante en una decena más alta (6 contra 5): la ley del mínimo
    # pone antes a A. Un orden solo por `weighted_score` pondría antes a B. Todas las ventanas dan 40 o más: ninguna es de alto riesgo.
    api = armado(armar_ejemplo, lluvia_mm=LLUVIA_LEY_DEL_MINIMO, helada_anios=HELADAS_LEY_DEL_MINIMO)
    ventanas = diagnostico(api, sowing_date=fecha_en_mes(1))["best_windows"]
    por_mes = {v["sowing_start"][5:7]: v for v in ventanas}
    assert {"01", "05"} <= por_mes.keys(), f"A y B deben estar entre las mejores ventanas, y están {sorted(por_mes)}"
    a, b = por_mes["01"], por_mes["05"]
    assert (a["limiting_signal"], a["limiting_score"], a["weighted_score"]) == ("water", 66, 82)
    assert (b["limiting_signal"], b["limiting_score"], b["weighted_score"]) == ("frost", 55, 84)
    assert b["weighted_score"] > a["weighted_score"]  # el caso solo tiene sentido si el promedio favorece a B
    assert decena(a["limiting_score"]) > decena(b["limiting_score"])
    assert ventanas.index(a) < ventanas.index(b) and ventanas[0] == a
    assert not a["high_risk"] and not b["high_risk"] and _ordenadas(ventanas)


def test_ejemplo_la_decena_alta_es_una_sola_y_un_factor_de_95_va_antes_que_uno_de_100_si_gana_en_fecha(armar_ejemplo, hoy_fijo):
    # La decena alta es de 90 a 100 (un factor limitante de 100 no forma una decena propia). Hoy es el 16 nov 2026 (`hoy_fijo`:
    # las mejores ventanas parten del mes en curso). Heladas de ejemplo: críticas en noviembre (la ventana pedida, del 20 nov,
    # es roja y trae `best_windows`) y 1 año de 30 en enero (3,3 %: la curva [[0,100],[20,70]] da 95).
    # Pesos: agua 5, calor 5, suelo 5 y heladas 1 (oferta y mercado, sin curva, no entran). Todo lo demás da 100.
    #   Sembrar el 1 dic y el 1 feb: heladas 100, factor limitante 100 (agua, la primera del empate), promedio 100.
    #   Sembrar el 1 ene: heladas 95, factor limitante 95 (heladas), promedio (5x100 + 1x95 + 5x100 + 5x100) / 16 = 1595 / 16 =
    #   99,7, es decir 100. Mismo promedio y la misma decena (90 a 100): gana la más temprana, así que el 1 ene (95) va antes que el
    #   1 feb (100). Con `limiting_score // 10` sin tope, el 100 es la decena 10 y el 1 feb pasaría antes.
    api = armado(armar_ejemplo, helada_anios={11: HELADA_CRITICA, 1: 1})
    prioridades = {"water": 5, "frost": 1, "heat": 5, "soil": 5, "supply": 3, "market": 3}
    cuerpo = diagnostico(api, sowing_date="2026-11-20", priorities=prioridades)
    assert hoy_fijo.isoformat() == "2026-11-16" and cuerpo["overall"]["light"] == "red"
    ventanas = [(v["sowing_start"], v["limiting_score"], v["weighted_score"]) for v in cuerpo["best_windows"]]
    assert ventanas == [("2026-12-01", 100, 100), ("2027-01-01", 95, 100), ("2027-02-01", 100, 100)]
    assert [decena(v["limiting_score"]) for v in cuerpo["best_windows"]] == [9, 9, 9]
    assert _ordenadas(cuerpo["best_windows"])


def test_ejemplo_ventana_de_alto_riesgo_nunca_entra_en_las_mejores(armar_ejemplo):
    # En julio las heladas son críticas: la ventana pedida es de alto riesgo (R2), aunque agua y calor den 100. Queda marcada
    # `high_risk` y ninguna mejor ventana lo es ni empieza ese mes.
    api = armado(armar_ejemplo, helada_anios=HELADAS_POR_MES)
    pedida = diagnostico(api, sowing_date=fecha_en_mes(7))
    assert pedida["overall"]["high_risk"] is True and luz(pedida) == ("red", "other_window")
    assert pedida["best_windows"]
    assert all(v["high_risk"] is False for v in pedida["best_windows"])
    assert pedida["window"]["sowing_start"][:7] not in {v["sowing_start"][:7] for v in pedida["best_windows"]}


def test_ejemplo_other_window_trae_mejores_ventanas_de_los_proximos_doce_meses(armar_ejemplo):
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=HELADAS_POR_MES), sowing_date=fecha_en_mes(7))
    assert "other_window" in (cuerpo["overall"]["action"], cuerpo["overall_default"]["action"])
    assert 1 <= len(cuerpo["best_windows"]) <= 3
    hoy = region_today()
    mes_en_curso = date(hoy.year, hoy.month, 1)
    dentro_de_doce_meses = date(*add_months(hoy.year, hoy.month, 12), 1)
    inicios = [date.fromisoformat(v["sowing_start"]) for v in cuerpo["best_windows"]]
    assert all(mes_en_curso <= inicio < dentro_de_doce_meses for inicio in inicios)


def test_ejemplo_other_window_con_todas_las_ventanas_de_alto_riesgo_trae_best_windows_vacio(armar_ejemplo):
    # Heladas críticas todo el año. La acción sigue en `other_window`, pero ninguna ventana es candidata: `best_windows` viene
    # como lista vacía (no ausente) y la web no inventa una fecha.
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=HELADA_CRITICA))
    assert "other_window" in (cuerpo["overall"]["action"], cuerpo["overall_default"]["action"])
    assert cuerpo["best_windows"] == []


def test_ejemplo_empate_del_factor_limitante_lo_gana_el_agua_luego_heladas_y_calor(armar_ejemplo):
    # Sin heladas, con lluvia de sobra y calor bajo, `water`, `frost` y `heat` califican 100: un empate de la señal más baja. R4: gana
    # la primera en el orden `water`, `frost`, `heat`, `soil`, `supply`, `market`. El valor esperado va escrito aquí y no sale de
    # el motor, para que un orden distinto (por ejemplo el alfabético, que daría `frost`) falle la prueba.
    cuerpo = diagnostico(armado(armar_ejemplo, helada_anios=0))
    assert [cuerpo["signals"][n]["score"] for n in ("water", "frost", "heat")] == [100, 100, 100]
    assert cuerpo["overall"]["limiting_signal"] == "water"
    # Con el agua en 0 no cuenta (peso 0, favorable): el empate queda entre `frost` y `heat`, y gana `frost`.
    sin_agua = diagnostico(armado(armar_ejemplo, helada_anios=0), priorities=con(water=0))
    assert sin_agua["signals"]["water"]["counts"] is False
    assert sin_agua["overall"]["limiting_signal"] == "frost"


def test_ejemplo_una_de_las_mejores_ventanas_coincide_con_el_diagnostico_de_esa_fecha(armar_ejemplo):
    # Coherencia: el diagnóstico de la fecha de una mejor ventana da el mismo factor limitante y el mismo promedio ponderado.
    # Supuesto por confirmar: `weighted_score` se redondea a entero, así que se compara con tolerancia de 1.
    api = armado(armar_ejemplo, helada_anios=HELADAS_POR_MES)
    mejor = diagnostico(api, sowing_date=fecha_en_mes(7))["best_windows"][0]
    otra = diagnostico(api, sowing_date=mejor["sowing_start"])
    cuentan = {n: s for n, s in otra["signals"].items() if s["counts"] and s["score"] is not None}
    limitante = min(cuentan, key=lambda n: (cuentan[n]["score"], ORDEN_DE_SEÑALES.index(n)))
    assert mejor["limiting_score"] == cuentan[limitante]["score"]
    assert mejor["limiting_signal"] == otra["overall"]["limiting_signal"] == limitante
    pesos = otra["weights"]
    ponderado = sum(cuentan[n]["score"] * pesos[n] for n in cuentan) / sum(pesos[n] for n in cuentan)
    assert abs(mejor["weighted_score"] - ponderado) <= 1
    assert mejor["high_risk"] is otra["overall"]["high_risk"] is False


def test_ejemplo_la_frecuencia_de_heladas_cuenta_los_anios_con_helada_en_cualquier_mes_sensible_no_el_peor_mes(armar_ejemplo):
    # Siembra en marzo: los meses sensibles de la papa van de marzo a agosto. Heladas de ejemplo en años distintos: abril en 1991 a
    # 1995 (5 años) y mayo en 1996 a 2000 (5 años); ningún otro mes. Spec («Cómo se califica cada señal»): el porcentaje de años
    # con al menos una helada en CUALQUIERA de los meses sensibles. Hay helada en 10 de 30 años: 33,3 %, y la curva
    # [[20,70],[40,40]] da 70 - 30 x (33,3 - 20) / 20 = 50 (moderada). El peor mes (5 de 30, 16,7 %) daría 75 (favorable).
    api = armado(armar_ejemplo, helada_anios={4: range(1991, 1996), 5: range(1996, 2001)})
    frost = diagnostico(api, sowing_date=fecha_en_mes(3))["signals"]["frost"]
    assert (frost["score"], frost["level"]) == (50, "moderate")
    assert any("en 10 de los 30 años" in razon for razon in frost["reasons"])


# ---------- Riego ----------


def test_ejemplo_con_y_sin_riego_y_riego_nulo(armar_ejemplo):
    # La misma ventana con déficit de agua (lluvia de 20 mm al mes). Sin riego, `water` es `unfavorable`; con riego es
    # `favorable` y la razón dice cuánto riego haría falta. Con `irrigated` nulo se evalúa como sin riego y lo dice.
    api = armado(armar_ejemplo, lluvia_mm=LLUVIA_ESCASA_MM)
    sin_riego = diagnostico(api, irrigated=False)["signals"]["water"]
    con_riego = diagnostico(api, irrigated=True)["signals"]["water"]
    nulo = diagnostico(api, irrigated=None)
    assert sin_riego["level"] == "unfavorable"
    assert con_riego["level"] == "favorable"
    assert nulo["signals"]["water"] == sin_riego
    # Supuesto por confirmar: el texto de la limitación; la spec pide que diga que se evaluó sin riego.
    assert any("riego" in texto.lower() for texto in nulo["limitations"])


# ---------- Dos fuentes de lluvia ----------


def test_ejemplo_sin_dato_de_la_fuente_de_agua_es_insufficient_data_aunque_la_otra_tenga(ejemplo_dos_lluvias):
    # `catalog/sources.yaml`: `water` usa `imerg` y contrasta con `nasa_power`. Samacá (EJEMPLO) trae lluvia de NASA POWER
    # (`climate_month`) pero no de IMERG (`precip_month`): R1, nunca se cambia de fuente en silencio. `sources` trae las dos.
    agua = diagnostico(ejemplo_dos_lluvias, municipality_id=EJEMPLO_FRIO)["signals"]["water"]
    assert agua["status"] == "insufficient_data" and agua["level"] is None
    seca = {fuente["source_id"]: fuente for fuente in agua["sources"] if fuente["indicator"] == "precip_dry_mm"}
    assert (seca["imerg"]["used"], seca["imerg"]["value"]) == (True, None)  # la fuente elegida, sin dato
    assert seca["nasa_power"]["used"] is False and seca["nasa_power"]["value"] > 0  # solo para contrastar
    power_samaca = seca["nasa_power"]["value"]
    # Control: Villa de Leyva sí tiene IMERG y su agua se calcula con ella. Los dos municipios tienen la misma lluvia de ejemplo
    # (60 mm al mes en las dos fuentes), así que la IMERG de Villa de Leyva da lo mismo que la POWER de Samacá. Se comparan entre
    # sí y no con un número: la lluvia de la ventana se reparte por los días de cada mes y cambia con la fecha de siembra (R4).
    control = diagnostico(ejemplo_dos_lluvias, municipality_id=EJEMPLO_CON_IMERG)["signals"]["water"]
    assert control["status"] == "available" and control["level"] is not None
    seca = {fuente["source_id"]: fuente for fuente in control["sources"] if fuente["indicator"] == "precip_dry_mm"}
    assert seca["imerg"]["used"] is True and seca["imerg"]["value"] == power_samaca
    assert seca["nasa_power"]["used"] is False


# ---------- Curva (HU-196): pasa hoy ----------


def test_real_curva_optimo_100_limite_absoluto_0_y_punto_medio_50(datos_reales):
    # Papa, `crops.parquet` (UPRA): tmean_min_c 8, tmean_opt_min_c 12, tmean_opt_max_c 15, tmean_max_c 16. Dentro del óptimo
    # califica 100; en el límite absoluto, 0; a medio camino entre el absoluto y el óptimo, 50.
    punto = [
        valor(datos_reales, "crops", "crop_id", "papa", c) for c in ("tmean_min_c", "tmean_opt_min_c", "tmean_opt_max_c", "tmean_max_c")
    ]
    curva = crop_curve(*punto)
    assert punto == [8.0, 12.0, 15.0, 16.0]
    assert score_from_curve(curva, 13.5) == 100
    assert score_from_curve(curva, 8.0) == 0 and score_from_curve(curva, 16.0) == 0
    assert score_from_curve(curva, 10.0) == 50 and score_from_curve(curva, 15.5) == 50
