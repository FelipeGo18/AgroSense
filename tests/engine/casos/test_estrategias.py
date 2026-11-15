"""Casos de referencia de estrategias de rotación (HU-121, PR 1). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Todos esperan el motor (`/rotations` responde 501 hoy) y van con `xfail(strict=True)`: cuando la HU pase, la prueba falla
hasta quitar la marca. Los resultados salen de la HU-121, del contrato y de «Estrategias de rotación»; lo que la spec no
deja deducir queda como «supuesto por confirmar».

TODO(HU-121): casos reales sobre `data/published` con la `dataset_version` 2026.11.11 (llega con el PR #62).
"""

import pytest

from backend.api import calc_examples
from common.region import region_today
from tests.engine.casos.conftest import EJEMPLO_CALIDO, EJEMPLO_FRIO, EJEMPLO_PRIORIDADES, rotacion

ESPERA_REGLA = pytest.mark.xfail(strict=True, reason="espera HU-213, HU-082 y HU-084 (el endpoint responde 501)")
ESPERA_ESTRATEGIAS = pytest.mark.xfail(strict=True, reason="espera HU-213, HU-082 y HU-084 (el endpoint responde 501)")
ESPERA_CICLOS = pytest.mark.xfail(strict=True, reason="espera HU-213, HU-082 y HU-084 (el endpoint responde 501)")
ESPERA_HELADA = pytest.mark.xfail(strict=True, reason="espera HU-213, HU-082 y HU-084 (el endpoint responde 501)")
# Sin sensibilidad a la helada en ninguna etapa de la ficha (catalog/crops.yaml): un ciclo con ellos no es de alto riesgo.
SIN_HELADA = {"zanahoria", "descanso"}
# Abono verde y descanso: no dejan cosecha, así que no cuentan como «cultivo» en `income`.
SIN_COSECHA = {"avena_vicia", "descanso"}


@ESPERA_REGLA
def test_ejemplo_repetir_familia_en_ciclos_seguidos_se_excluye_por_regla(api, familias):
    # Arveja y haba son Leguminosae: seguidas violan `same_family_consecutive` (`familia_seguida`). Con `haba` antes en el
    # terreno, el primer ciclo tampoco puede ser de esa familia.
    respuesta = rotacion(api, previous_crop_ids=["haba"], cycles=2)
    assert respuesta["excluded_counts"]["rule"] > 0
    assert respuesta["excluded"]

    def repite(crop_ids, anterior):
        cadena = [anterior, *crop_ids]
        return [i for i in range(1, len(cadena)) if familias_de(cadena[i]) and familias_de(cadena[i]) == familias_de(cadena[i - 1])]

    familias_de = lambda crop_id: familias[crop_id][0] if crop_id in familias else None  # noqa: E731
    for estrategia in respuesta["strategies"]:
        assert not repite(estrategia["crop_ids"], "haba"), estrategia["crop_ids"]
    for item in respuesta["excluded"]:
        if item["kind"] != "rule" or not repite(item["crop_ids"], "haba"):
            continue
        assert item["rule_id"] == "familia_seguida"
        # Supuesto por confirmar: `cycle` es el ciclo (desde 1) del cultivo que repite la familia, como en el ejemplo del contrato.
        assert item["cycle"] == repite(item["crop_ids"], "haba")[0]
        assert item["reason"]


@ESPERA_REGLA
def test_ejemplo_toda_exclusion_y_todo_issue_cita_fuentes_que_existen(api, fuentes):
    respuesta = rotacion(api, previous_crop_ids=["haba"], current_crop_ids=["arveja", "haba"])
    elementos = [*respuesta["excluded"], *respuesta["current_strategy"]["issues"]]
    assert elementos
    for elemento in elementos:
        assert elemento["source_ids"], elemento
        assert set(elemento["source_ids"]) <= fuentes, elemento


@ESPERA_REGLA
def test_ejemplo_rotacion_actual_que_viola_regla_sale_con_issues_y_sin_rank(api):
    respuesta = rotacion(api, current_crop_ids=["arveja", "haba"])
    actual = respuesta["current_strategy"]
    assert actual["kind"] == "current"
    assert actual["rank"] is None
    assert actual["crop_ids"] == ["arveja", "haba"]
    reglas = [i for i in actual["issues"] if i["kind"] == "rule" and i["rule_id"] == "familia_seguida"]
    assert reglas and all(i["source_ids"] for i in reglas)
    # Nunca se excluye en silencio: no aparece en `excluded`.
    assert all(e["crop_ids"] != ["arveja", "haba"] for e in respuesta["excluded"])


@ESPERA_ESTRATEGIAS
def test_ejemplo_sin_rotacion_actual_no_hay_referencia_y_las_limitaciones_lo_dicen(api):
    respuesta = rotacion(api)
    assert respuesta["current_strategy"] is None
    # Supuesto por confirmar: la limitación menciona la «rotación actual» (R1); el texto exacto no está fijado.
    assert any("actual" in texto.lower() for texto in respuesta["limitations"])
    assert all(s["kind"] == "suggested" for s in respuesta["strategies"])


@ESPERA_ESTRATEGIAS
def test_ejemplo_cultivo_no_apto_no_entra_a_ninguna_estrategia(api):
    # Papa en un municipio cálido de ejemplo (28,4 °C, sobre el máximo de su ficha) no es apta: ninguna estrategia la usa.
    respuesta = rotacion(api, municipality_id=EJEMPLO_CALIDO)
    assert respuesta["excluded_counts"]["not_suitable"] > 0
    assert all("papa" not in s["crop_ids"] for s in respuesta["strategies"])
    # Forma de `not_suitable` aprobada por Felipe el 14 nov 2026 (PR #70, contrato en el PR #73): `cycle` es el primer
    # ciclo donde aparece el cultivo, `crop_id` ese cultivo, `reason` la misma frase de `/diagnostics` y `source_ids` la
    # fuente del rango de la ficha (`upra_papa_diacol` en `catalog/crops.yaml`), `nasa_power` y `cenicafe_lapse_rate`.
    diagnostico = api.post(
        "/api/v1/diagnostics",
        json={"municipality_id": EJEMPLO_CALIDO, "crop_id": "papa", "sowing_date": region_today().isoformat()},
    )
    assert diagnostico.status_code == 200, diagnostico.text
    razon_diagnostico = diagnostico.json()["suitability"]["reasons"]
    # Que el caso no pase sin comprobar nada (revisión de Felipe, PR #70): toda exclusión `not_suitable` trae `crop_id`
    # y al menos una es de la papa; si el motor olvida `crop_id`, el caso falla aquí en vez de saltarse el `for`.
    no_aptas = [e for e in respuesta["excluded"] if e["kind"] == "not_suitable"]
    assert no_aptas and all(e.get("crop_id") for e in no_aptas)
    assert any(e["crop_id"] == "papa" for e in no_aptas)
    for item in no_aptas:
        if item["crop_id"] != "papa":
            continue
        assert item["cycle"] == item["crop_ids"].index("papa") + 1
        assert item["reason"] in razon_diagnostico
        assert {"upra_papa_diacol", "nasa_power", "cenicafe_lapse_rate"} <= set(item["source_ids"])


# ---------- Comprobaciones que corren hoy sobre el ejemplo del contrato y mañana sobre `/rotations` ----------


def comprobar_exclusion_por_helada(cuerpo: dict, fuentes: set[str] | None = None) -> None:
    """R2: la helada crítica excluye con `kind = high_risk`, `signal = frost` y el ciclo afectado; ninguna estrategia que
    queda trae un ciclo de alto riesgo."""
    altos = [e for e in cuerpo["excluded"] if e["kind"] == "high_risk"]
    assert altos and cuerpo["excluded_counts"]["high_risk"] >= len(altos)  # no pasa sin comprobar nada
    for item in altos:
        assert item["signal"] == "frost", item
        assert 1 <= item["cycle"] <= len(item["crop_ids"])
        assert item["crop_ids"][item["cycle"] - 1] not in SIN_HELADA, item  # el ciclo afectado es uno sensible
        assert item["source_ids"] and set(item["source_ids"]) <= (fuentes or set(item["source_ids"]))
    excluidas = [e["crop_ids"] for e in altos]
    for estrategia in cuerpo["strategies"]:
        assert estrategia["crop_ids"] not in excluidas
        assert estrategia["cycles"] and not any(c["high_risk"] for c in estrategia["cycles"])
        for ciclo in estrategia["cycles"]:
            frost = (ciclo["diagnosis"] or {}).get("signals", {}).get("frost")
            assert not (frost and frost["level"] == "unfavorable" and frost["critical"]), estrategia["crop_ids"]


def comprobar_sin_oferta_ni_mercado(cuerpo: dict) -> None:
    """R3: la oferta y el mercado nunca excluyen; solo hay cuatro motivos y ninguno es `supply` ni `market`."""
    assert set(cuerpo["excluded_counts"]) == {"rule", "not_suitable", "soil_ph", "high_risk"}
    assert cuerpo["excluded"]
    for item in cuerpo["excluded"]:
        assert item["kind"] in cuerpo["excluded_counts"], item
        assert item.get("signal") not in ("supply", "market"), item


def comprobar_primer_ciclo(ciclo: dict, diagnostico: dict) -> int:
    """El primer ciclo y `/diagnostics` dan las mismas señales y calificaciones. Devuelve cuántas señales comparó."""
    propio = ciclo["diagnosis"]
    assert propio is not None and diagnostico["signals"]
    assert set(propio["signals"]) == set(diagnostico["signals"])
    for nombre, senal in diagnostico["signals"].items():
        for campo in ("status", "level", "score", "critical", "counts"):
            assert propio["signals"][nombre][campo] == senal[campo], (nombre, campo)
    assert propio["overall"]["light"] == diagnostico["overall"]["light"] == ciclo["light"]
    return len(diagnostico["signals"])


def rank_de(cuerpo: dict, crop_ids: list[str]) -> int | None:
    return next((s["rank"] for s in cuerpo["strategies"] if s["crop_ids"] == crop_ids), None)


def comprobar_abono_verde_gana(cuerpo: dict, con: list[str], sin: list[str]) -> None:
    """`rank` menor es mejor: con abono verde gana a la misma sin él, y no al revés."""
    rango_con, rango_sin = rank_de(cuerpo, con), rank_de(cuerpo, sin)
    assert rango_con is not None and rango_sin is not None, "las dos tienen que estar entre las 10 de `strategies`"
    assert rango_con < rango_sin


def test_ejemplo_del_contrato_cumple_las_comprobaciones_de_estrategias():
    """Corre hoy: valida la forma y las aserciones contra `calc_examples.ROTATIONS`."""
    cuerpo = calc_examples.ROTATIONS
    comprobar_exclusion_por_helada(cuerpo)
    comprobar_sin_oferta_ni_mercado(cuerpo)
    comprobar_abono_verde_gana(cuerpo, ["avena_vicia", "arveja", "papa"], ["descanso", "arveja", "papa"])
    # Los dos lados: al revés, o con una exclusión de otra señal, las comprobaciones fallan.
    with pytest.raises(AssertionError):
        comprobar_abono_verde_gana(cuerpo, ["descanso", "arveja", "papa"], ["avena_vicia", "arveja", "papa"])
    with pytest.raises(AssertionError):
        comprobar_exclusion_por_helada({**cuerpo, "excluded": [{**cuerpo["excluded"][1], "signal": "heat"}]})
    with pytest.raises(AssertionError):
        comprobar_sin_oferta_ni_mercado({**cuerpo, "excluded": [{**cuerpo["excluded"][1], "signal": "supply"}]})
    # Primer ciclo del ejemplo contra el diagnóstico del que sale: mismas señales y calificaciones (las luces del ejemplo
    # no coinciden entre sí en `light_default`: se anota en el informe, no se comprueba aquí).
    assert comprobar_primer_ciclo({**cuerpo["strategies"][0]["cycles"][0], "light": "green"}, calc_examples.DIAGNOSIS_OK) == 6
    with pytest.raises(AssertionError):
        comprobar_primer_ciclo(
            cuerpo["strategies"][0]["cycles"][0],
            {
                **calc_examples.DIAGNOSIS_OK,
                "signals": {
                    **calc_examples.DIAGNOSIS_OK["signals"],
                    "water": {**calc_examples.DIAGNOSIS_OK["signals"]["water"], "score": 1},
                },
            },
        )


@ESPERA_HELADA
def test_ejemplo_un_ciclo_con_helada_critica_excluye_la_estrategia(api, datos_con_heladas, fuentes):
    # Samacá con heladas del 80 % de los años en cada mes (ver `datos_con_heladas`): `frost` califica 13 y es crítica.
    # Con `cycles = 2` no hay tantas estrategias por regla y las excluidas por helada caben entre las 10 de `excluded`
    # (supuesto por confirmar: `excluded` trae primero las de un solo motivo; si no aparece ninguna, el caso falla).
    # `fuentes` se lee del dataset de `datos`: la fuente de la helada (`nasa_power`) se publica con `datos_con_heladas`.
    respuesta = rotacion(api, cycles=2)
    comprobar_exclusion_por_helada(respuesta, fuentes | {"nasa_power", "mapa_zarc_2025"})
    # El otro lado: zanahoria y descanso no tienen etapa sensible con dato, así que su helada no cambia la luz (R1).
    assert not any(e["kind"] == "high_risk" and set(e["crop_ids"]) <= SIN_HELADA for e in respuesta["excluded"])


@ESPERA_CICLOS
def test_ejemplo_la_oferta_y_el_mercado_no_excluyen_y_sin_ellos_el_ingreso_no_califica(api):
    # Hoy `supply` y `market` no tienen curva (`thresholds.yaml`, decisión de Felipe del 11 nov 2026): siempre salen
    # `insufficient_data`. Por eso no se puede escribir «con `supply` crítico»: es imposible con las reglas de hoy. Lo que
    # sí se comprueba es que, sin oferta ni mercado, `scores.income` no califica (decisión 15) y las limitaciones lo dicen.
    respuesta = rotacion(api, cycles=2, previous_crop_ids=["haba"])
    comprobar_sin_oferta_ni_mercado(respuesta)
    con_cultivo = [s for s in respuesta["strategies"] if set(s["crop_ids"]) - SIN_COSECHA]
    assert con_cultivo
    for estrategia in con_cultivo:
        for ciclo in estrategia["cycles"]:
            if ciclo["diagnosis"]:
                assert ciclo["diagnosis"]["signals"]["supply"]["status"] == "insufficient_data"
                assert ciclo["diagnosis"]["signals"]["market"]["status"] == "insufficient_data"
        assert estrategia["scores"]["income"] is None
    # Supuesto por confirmar: la limitación nombra el ingreso, la oferta o el mercado; el texto exacto no está fijado.
    assert any(palabra in t.lower() for t in respuesta["limitations"] for palabra in ("ingreso", "oferta", "mercado"))


@ESPERA_CICLOS
def test_ejemplo_el_primer_ciclo_coincide_con_el_diagnostico(api):
    hoy = region_today().isoformat()
    prioridades = {"water": 2, "frost": 4, "heat": 1, "soil": 5, "supply": 0, "market": 1}
    respuesta = rotacion(api, irrigated=True, signal_priorities=prioridades)
    comparadas, cultivos = 0, set()
    for estrategia in respuesta["strategies"]:
        primero = estrategia["cycles"][0]
        if primero["diagnosis"] is None:  # descanso: sin diagnóstico
            continue
        assert primero["sowing_date"] == hoy
        diagnostico = api.post(
            "/api/v1/diagnostics",
            json={
                "municipality_id": EJEMPLO_FRIO,
                "crop_id": primero["crop_id"],
                "sowing_date": hoy,
                "irrigated": True,
                "priorities": prioridades,
            },
        )
        assert diagnostico.status_code == 200, diagnostico.text
        comparadas += comprobar_primer_ciclo(primero, diagnostico.json())
        assert primero["light_default"] == diagnostico.json()["overall_default"]["light"]
        cultivos.add(primero["crop_id"])
    assert comparadas and len(cultivos) >= 2  # más de un cultivo comparado


@ESPERA_CICLOS
def test_ejemplo_con_prioridad_de_suelo_en_5_el_abono_verde_queda_mejor(api):
    # Dos estrategias de 2 ciclos que solo difieren en el primero: avena con vicia (abono verde, fija nitrógeno) o cebolla,
    # que dura lo mismo (150 días), así que el segundo ciclo cae en la misma fecha. Con la regla `leguminosa_en_rotacion`
    # (favorable desde 1 ciclo con leguminosa), `nitrogen` es favorable con la avena con vicia y unfavorable con la cebolla.
    # Supuestos por confirmar: el agua y el riesgo de la avena y de la cebolla en Samacá no se comparan aquí; se espera que
    # el peso de `soil` en 5 baste para que la avena con vicia gane, y que las dos queden entre las 10 de `strategies`.
    con, sin = ["avena_vicia", "zanahoria"], ["cebolla_bulbo", "zanahoria"]
    respuesta = rotacion(api, cycles=2, priorities={**EJEMPLO_PRIORIDADES, "soil": 5})
    assert respuesta["weights"]["soil"] == 5
    por_crop_ids = {tuple(s["crop_ids"]): s for s in respuesta["strategies"]}
    assert por_crop_ids[tuple(con)]["soil_health"]["nitrogen"]["level"] == "favorable"
    assert por_crop_ids[tuple(sin)]["soil_health"]["nitrogen"]["level"] == "unfavorable"
    comprobar_abono_verde_gana(respuesta, con, sin)
