# ruff: noqa: F401, F811  (los fixtures se importan de datos_reales.py y se piden por nombre)
"""Casos de referencia del diagnóstico de una ventana (HU-121, PR 2). Todos son de EJEMPLO (R5), salvo la curva, que usa la
ficha real de la papa. Cada resultado esperado sale de `specs/01-reglas.md` («Agregación del semáforo», «Las prioridades del
agricultor», «Orden de las ventanas») y del contrato de `/diagnostics`.

Hoy `/diagnostics` responde 501 si el cultivo es apto: los casos van con `xfail(strict=True)` y fallan primero en
`assert status_code == 200`. Armar una señal con un nivel dado exige tablas que `publish()` todavía no escribe (heladas y calor
por mes: HU-045; suelo: HU-181; oferta: HU-031): no se inventan Parquet. Cada caso dice qué falta; la entrada es la más honesta
posible y la aserción, solo lo que la spec deduce. Lo que no, queda como «supuesto por confirmar».
"""

from fastapi.testclient import TestClient

from backend.engine.curve import crop_curve, score_from_curve
from tests.engine.casos.datos_reales import (
    EJEMPLO_CON_IMERG,
    EJEMPLO_FRIO,
    SENALES,
    VERSION_CASOS_REALES,
    cliente,
    datos_reales,
    diagnostico,
    ejemplo_dos_lluvias,
    pendiente,
    valor,
    version_fijada,
)

# Pesos para una señal con la que se juega y las demás en importancia normal (3); `supply` y `market` no tienen curva
# (thresholds.yaml): siempre `insufficient_data`, así que su peso no importa para la luz.
NORMALES = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
VENTANAS = pendiente(*SENALES, "HU-045", "HU-192", extra="y tablas de heladas por mes")


def con(**pesos) -> dict:
    return {**NORMALES, **pesos}


def luz(cuerpo: dict, clave: str = "overall") -> tuple[str, str]:
    return cuerpo[clave]["light"], cuerpo[clave]["action"]


# ---------- Luces: verde, rojo, no evaluable ----------


@pendiente(*SENALES, "HU-045", "HU-181", extra="y tablas de lluvia, heladas y suelo del ejemplo")
def test_ejemplo_luz_verde(cliente):
    # Entrada a armar: agua, heladas, calor y suelo `favorable`. Regla 3: ninguna señal que cuenta es desfavorable y `water` es
    # favorable: verde y `sow`. `supply` y `market` sin curva son `insufficient_data`: no cambian la luz y van a `limitations`.
    cuerpo = diagnostico(cliente)
    assert luz(cuerpo) == ("green", "sow")
    assert {n: cuerpo["signals"][n]["level"] for n in ("water", "frost", "heat", "soil")} == dict.fromkeys(
        ("water", "frost", "heat", "soil"), "favorable"
    )
    for nombre in ("supply", "market"):
        assert cuerpo["signals"][nombre]["status"] == "insufficient_data" and cuerpo["signals"][nombre]["level"] is None
    assert cuerpo["limitations"]


@pendiente(*SENALES, "HU-045", extra="y tablas de heladas")
def test_ejemplo_luz_roja_por_helada_critica_con_agua_favorable(cliente):
    # Entrada a armar: `frost` desfavorable y crítica (calificación < 40: `critical_below`); agua favorable. Regla 2: roja aunque
    # lo demás sea bueno (R2). Todas las desfavorables son de clima: acción `other_window`, y trae `best_windows` (puede ser vacío).
    cuerpo = diagnostico(cliente)
    frost = cuerpo["signals"]["frost"]
    assert (frost["level"], frost["critical"]) == ("unfavorable", True) and frost["score"] < 40
    assert cuerpo["signals"]["water"]["level"] == "favorable"
    assert luz(cuerpo) == ("red", "other_window") and luz(cuerpo, "overall_default") == ("red", "other_window")
    assert cuerpo["best_windows"] is not None


@pendiente(*SENALES, "HU-045", extra="y tablas de heladas, PR #61")
def test_ejemplo_helada_critica_con_peso_cero_sigue_en_rojo_y_cuenta(cliente):
    # Un peso 0 no esconde un riesgo grave de clima (R2): `frost` crítica con peso 0 da rojo y trae `counts = true`.
    cuerpo = diagnostico(cliente, priorities=con(frost=0))
    assert cuerpo["signals"]["frost"]["critical"] is True and cuerpo["signals"]["frost"]["counts"] is True
    assert luz(cuerpo)[0] == "red"
    assert cuerpo["overall"]["weights_basis"] == "farmer" and cuerpo["weights"]["frost"] == 0


# Pasa desde el endpoint de diagnóstico (HU-076, PR #102): se quitó la marca de pendiente.
def test_ejemplo_agua_sin_datos_es_no_evaluable_y_con_peso_cero_no(cliente):
    # `dataset_con_clima` no publica lluvia: `water` es `insufficient_data` (R1). Regla 1: si `water` cuenta, la luz es
    # `not_evaluable` con `review_data`; con peso 0 no cuenta y esa regla no aplica (las demás sin datos no cambian la luz).
    cuerpo = diagnostico(cliente)
    assert cuerpo["signals"]["water"]["status"] == "insufficient_data" and cuerpo["signals"]["water"]["level"] is None
    assert luz(cuerpo) == ("not_evaluable", "review_data") and luz(cuerpo, "overall_default") == ("not_evaluable", "review_data")
    sin_agua = diagnostico(cliente, priorities=con(water=0))
    assert luz(sin_agua)[0] != "not_evaluable"
    assert luz(sin_agua, "overall_default") == ("not_evaluable", "review_data")  # los pesos de AgroSense sí cuentan el agua


# ---------- Pesos ----------


@pendiente(*SENALES, "HU-045", extra="y tablas de heladas por mes")
def test_ejemplo_peso_5_cuenta_un_moderate_como_desfavorable(cliente):
    # Entrada a armar: `frost` moderada (calificación de 40 a 69, no crítica), el resto favorable. Con el peso por defecto (3), un
    # `moderate` no frena la luz: verde. Con peso 5, cuenta como `unfavorable`: regla 3 falla (hay una desfavorable) y regla 2 no
    # aplica (no es crítica ni hay dos): amarilla; acción `other_window` (la desfavorable es de clima).
    cuerpo = diagnostico(cliente, priorities=con(frost=5))
    assert cuerpo["signals"]["frost"]["level"] == "moderate" and cuerpo["signals"]["frost"]["counts"] is True
    assert luz(cuerpo, "overall_default") == ("green", "sow")
    assert luz(cuerpo) == ("yellow", "other_window")


@pendiente(*SENALES, "HU-181", extra="y suelo publicado")
def test_ejemplo_suelo_desfavorable_no_basta_para_rojo_y_con_peso_cero_cambia_la_luz(cliente):
    # Entrada a armar: `soil` desfavorable (pH fuera del rango de la papa), las demás favorables. El suelo nunca es crítico
    # (R10) y una sola desfavorable no da rojo: con el peso por defecto (2), amarilla y `rotate` (cambiar de fecha no arregla
    # el suelo). Con `soil` en 0 no cuenta: verde y `sow`. Reemplaza el caso de `supply`, que sin curva no tiene nivel.
    cuerpo = diagnostico(cliente, priorities=con(soil=0))
    suelo = cuerpo["signals"]["soil"]
    assert suelo["level"] == "unfavorable" and suelo["critical"] is False and suelo["counts"] is False
    assert luz(cuerpo, "overall_default") == ("yellow", "rotate")
    assert luz(cuerpo) == ("green", "sow")
    assert cuerpo["overall"]["weights_basis"] == "farmer" and cuerpo["overall_default"]["weights_basis"] == "default"


# ---------- Ventanas: factor limitante, alto riesgo, mejores ventanas ----------


def _ordenadas(ventanas: list[dict]) -> bool:
    """Orden de la spec: por decena del factor limitante (mayor primero), luego por promedio ponderado, luego la más temprana."""
    llave = [(-(v["limiting_score"] // 10), -v["weighted_score"], v["sowing_start"]) for v in ventanas]
    return llave == sorted(llave)


@VENTANAS
def test_ejemplo_factor_limitante_una_ventana_con_una_senal_en_15_no_queda_arriba(cliente):
    # Entrada a armar: una ventana con una señal no crítica en 15 (por ejemplo `soil`) y buen promedio, y otra con todas en 60 o
    # más. Ley del mínimo: la de 15 nunca queda por encima ni entra primera en `best_windows`.
    cuerpo = diagnostico(cliente)
    ventanas = cuerpo["best_windows"]
    assert ventanas and _ordenadas(ventanas)
    assert ventanas[0]["limiting_score"] >= max(v["limiting_score"] for v in ventanas)
    assert ventanas[0]["limiting_score"] != 15
    assert all(v["limiting_score"] >= 60 for v in ventanas[:1])


@VENTANAS
def test_ejemplo_ventana_de_alto_riesgo_nunca_entra_en_las_mejores(cliente):
    # Entrada a armar: un mes con `frost` crítica y el balance más alto. R2: queda marcada `high_risk` y fuera de `best_windows`,
    # aunque el promedio sea el mejor; el diagnóstico de esa fecha dice `high_risk = true`.
    pedida = diagnostico(cliente)
    assert pedida["overall"]["high_risk"] is True
    inicios = {v["sowing_start"] for v in pedida["best_windows"]}
    assert pedida["window"]["sowing_start"] not in inicios
    assert all(v["high_risk"] is False for v in pedida["best_windows"])


@VENTANAS
def test_ejemplo_other_window_trae_mejores_ventanas_de_los_proximos_doce_meses(cliente):
    cuerpo = diagnostico(cliente)
    assert "other_window" in (cuerpo["overall"]["action"], cuerpo["overall_default"]["action"])
    assert 1 <= len(cuerpo["best_windows"]) <= 3
    assert all(v["sowing_start"] >= cuerpo["window"]["sowing_start"][:7] for v in cuerpo["best_windows"])


@VENTANAS
def test_ejemplo_other_window_con_todas_las_ventanas_de_alto_riesgo_trae_best_windows_vacio(cliente):
    # Entrada a armar: heladas críticas todo el año. La acción sigue en `other_window`, pero ninguna ventana es candidata:
    # `best_windows` viene como lista vacía (no ausente) y la web no inventa una fecha.
    cuerpo = diagnostico(cliente)
    assert "other_window" in (cuerpo["overall"]["action"], cuerpo["overall_default"]["action"])
    assert cuerpo["best_windows"] == []


@VENTANAS
def test_ejemplo_una_de_las_mejores_ventanas_coincide_con_el_diagnostico_de_esa_fecha(cliente):
    # Coherencia: el diagnóstico de la fecha de una mejor ventana da el mismo factor limitante y el mismo promedio ponderado.
    # Supuesto por confirmar: `weighted_score` se redondea a entero, así que se compara con tolerancia de 1.
    base = diagnostico(cliente)
    mejor = base["best_windows"][0]
    otra = diagnostico(cliente, sowing_date=mejor["sowing_start"])
    cuentan = {n: s for n, s in otra["signals"].items() if s["counts"] and s["score"] is not None}
    limitante = min(cuentan, key=lambda n: (cuentan[n]["score"], n))
    assert mejor["limiting_score"] == cuentan[limitante]["score"]
    assert mejor["limiting_signal"] == otra["overall"]["limiting_signal"]
    pesos = otra["weights"]
    ponderado = sum(cuentan[n]["score"] * pesos[n] for n in cuentan) / sum(pesos[n] for n in cuentan)
    assert abs(mejor["weighted_score"] - ponderado) <= 1
    assert mejor["high_risk"] is otra["overall"]["high_risk"] is False


# ---------- Riego ----------


@pendiente(*SENALES, extra="y una lluvia de ejemplo con déficit para la papa en Samacá")
def test_ejemplo_con_y_sin_riego_y_riego_nulo(cliente):
    # Entrada a armar: la misma ventana con déficit de agua. Sin riego, `water` es `unfavorable`; con riego no lo es (es
    # `favorable` y la razón dice cuánto riego haría falta). Con `irrigated` nulo se evalúa como sin riego y lo dice.
    sin_riego = diagnostico(cliente, irrigated=False)["signals"]["water"]
    con_riego = diagnostico(cliente, irrigated=True)["signals"]["water"]
    nulo = diagnostico(cliente, irrigated=None)
    assert sin_riego["level"] == "unfavorable" and con_riego["level"] != "unfavorable"
    assert nulo["signals"]["water"] == sin_riego
    # Supuesto por confirmar: el texto de la limitación; la spec pide que diga que se evaluó sin riego.
    assert any("riego" in texto.lower() for texto in nulo["limitations"])


# ---------- Dos fuentes de lluvia ----------


@pendiente(*SENALES, extra="y que `Dataset` lea `precip_month` y `climate_month`")
def test_ejemplo_sin_dato_de_la_fuente_de_agua_es_insufficient_data_aunque_la_otra_tenga(ejemplo_dos_lluvias):
    # `catalog/sources.yaml`: `water` usa `imerg` y contrasta con `nasa_power`. Samacá (EJEMPLO) trae lluvia de NASA POWER
    # (`climate_month`) pero no de IMERG (`precip_month`): R1, nunca se cambia de fuente en silencio. `sources` trae las dos.
    agua = diagnostico(ejemplo_dos_lluvias, municipality_id=EJEMPLO_FRIO)["signals"]["water"]
    assert agua["status"] == "insufficient_data" and agua["level"] is None
    usadas = {fuente["source_id"]: fuente["used"] for fuente in agua["sources"]}
    assert usadas["imerg"] is True and usadas["nasa_power"] is False
    # Control: el otro municipio sí tiene IMERG y su agua se calcula.
    assert EJEMPLO_CON_IMERG != EJEMPLO_FRIO


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
    assert VERSION_CASOS_REALES  # la versión fijada ya la comprobó `datos_reales`
