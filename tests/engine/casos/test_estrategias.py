"""Casos de referencia de estrategias de rotación (HU-121, PR 1). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Esperaban el motor con `xfail(strict=True)`; desde HU-084 `/rotations` responde y corren sin marca. Los resultados
salen de la HU-121, del contrato y de «Estrategias de rotación»; lo que la spec no deja deducir queda como «supuesto
por confirmar».

TODO(HU-121): casos reales sobre `data/published` con la `dataset_version` 2026.11.11 (llega con el PR #62).
"""

import os
from pathlib import Path

import polars as pl
import pytest

from backend.api import calc_examples
from backend.engine.rotations.ranking import NO_CRITERION
from common.region import region_today
from tests.engine.casos.conftest import CONTORNO_LOTE, EJEMPLO_CALIDO, EJEMPLO_FRIO, EJEMPLO_PRIORIDADES, rotacion
from tests.test_diagnostico import create_lot, register

# Sin sensibilidad a la helada en ninguna etapa de la ficha (catalog/crops.yaml): un ciclo con ellos no es de alto riesgo.
SIN_HELADA = {"zanahoria", "descanso"}
# Abono verde y descanso: no dejan cosecha, así que no cuentan como «cultivo» en `income`.
SIN_COSECHA = {"avena_vicia", "descanso"}
NO_INCOME = NO_CRITERION["income"]


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
    comprobadas = 0
    for item in respuesta["excluded"]:
        if item["kind"] != "rule" or not repite(item["crop_ids"], "haba"):
            continue
        assert item["rule_id"] == "familia_seguida"
        # Supuesto por confirmar: `cycle` es el ciclo (desde 1) del cultivo que repite la familia, como en el ejemplo del contrato.
        assert item["cycle"] == repite(item["crop_ids"], "haba")[0]
        # Plantilla de `familia_seguida` (`catalog/rotation_rules.yaml`) con la familia repetida, escrita a mano: arveja y
        # haba son Leguminosae; avena con vicia y maíz, Gramineae.
        familia_repetida = familias_de(item["crop_ids"][item["cycle"] - 1])
        assert familia_repetida in {"Leguminosae", "Gramineae"}
        assert item["reason"] == f"Repite la familia {familia_repetida} en dos ciclos seguidos"
        comprobadas += 1
    assert comprobadas > 0  # el caso no pasa en vacío: al menos una exclusión por familia se comprobó


def test_ejemplo_suelo_fuera_del_rango_de_un_cultivo_lo_excluye_de_las_estrategias(armar_ejemplo):
    # Suelo de EJEMPLO (R5) en Samacá con pH 8,7 y el intervalo p05 a p95 de 8,4 a 9,0 (`publicar_ejemplo`: pH ± 0,3). Rangos de
    # pH de `catalog/crops.yaml`: arveja 4,5 a 8,3, cebolla de bulbo 4,3 a 8,3 y avena con vicia 4,5 a 7,5 quedan fuera de todo el
    # intervalo (su máximo es menor que 8,4); papa 4,2 a 8,5, maíz, haba y zanahoria lo tocan o lo cruzan y no se excluyen.
    api = armar_ejemplo(ph=8.7)
    fuera = {
        "arveja": "la arveja (4,5 a 8,3)",
        "cebolla_bulbo": "la cebolla de bulbo (4,3 a 8,3)",
        "avena_vicia": "la avena con vicia (abono verde) (4,5 a 7,5)",
    }
    respuesta = rotacion(api, cycles=2)
    assert respuesta["excluded_counts"]["soil_ph"] > 0
    assert respuesta["strategies"]
    for estrategia in respuesta["strategies"]:
        assert not set(estrategia["crop_ids"]) & set(fuera), estrategia["crop_ids"]
    por_ph = [e for e in respuesta["excluded"] if e["kind"] == "soil_ph"]
    assert por_ph  # el caso no pasa en vacío: al menos una exclusión `soil_ph` se comprueba
    fuentes = set(pl.read_parquet(Path(os.environ["AGROSENSE_DATA_DIR"]) / "sources.parquet")["source_id"].to_list())
    for item in por_ph:
        assert item["crop_id"] in fuera, item
        assert item["cycle"] == item["crop_ids"].index(item["crop_id"]) + 1  # el primer ciclo donde aparece el cultivo
        assert item["reason"] == f"El pH del suelo de la zona (8,4 a 9,0) queda fuera del que tolera {fuera[item['crop_id']]}"
        assert item["source_ids"] and set(item["source_ids"]) <= fuentes
        assert {"fao_ecocrop", "soilgrids"} <= set(item["source_ids"])  # la fuente del pH de la ficha y la del suelo
    assert {e["crop_id"] for e in por_ph} <= set(fuera)


def test_ejemplo_toda_exclusion_y_todo_issue_cita_fuentes_que_existen(api, fuentes):
    respuesta = rotacion(api, previous_crop_ids=["haba"], current_crop_ids=["arveja", "haba"])
    elementos = [*respuesta["excluded"], *respuesta["current_strategy"]["issues"]]
    assert elementos
    for elemento in elementos:
        assert elemento["source_ids"], elemento
        assert set(elemento["source_ids"]) <= fuentes, elemento


def test_ejemplo_rotacion_actual_que_viola_regla_sale_con_issues_y_sin_rank(api):
    respuesta = rotacion(api, current_crop_ids=["arveja", "haba"])
    actual = respuesta["current_strategy"]
    assert actual["kind"] == "current"
    assert actual["rank"] is None
    # Con 3 ciclos (por defecto) la actual se completa repitiendo desde el primero (contrato, `current_crop_ids`).
    assert actual["crop_ids"] == ["arveja", "haba", "arveja"]
    reglas = [i for i in actual["issues"] if i["kind"] == "rule" and i["rule_id"] == "familia_seguida"]
    assert reglas and all(i["source_ids"] for i in reglas)
    # Nunca se excluye en silencio: no aparece en `excluded`.
    assert all(e["crop_ids"] != ["arveja", "haba", "arveja"] for e in respuesta["excluded"])


def test_ejemplo_sin_rotacion_actual_no_hay_referencia_y_las_limitaciones_lo_dicen(api):
    respuesta = rotacion(api)
    assert respuesta["current_strategy"] is None
    # Supuesto por confirmar: la limitación menciona la «rotación actual» (R1); el texto exacto no está fijado.
    assert any("actual" in texto.lower() for texto in respuesta["limitations"])
    assert all(s["kind"] == "suggested" for s in respuesta["strategies"])


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


def test_ejemplo_un_ciclo_con_helada_critica_excluye_la_estrategia(api, datos_con_heladas, fuentes):
    # Samacá con heladas del 80 % de los años en cada mes (ver `datos_con_heladas`): `frost` califica 13 y es crítica.
    # Con `cycles = 2` no hay tantas estrategias por regla y las excluidas por helada caben entre las 10 de `excluded`
    # (supuesto por confirmar: `excluded` trae primero las de un solo motivo; si no aparece ninguna, el caso falla).
    # `fuentes` se lee del dataset de `datos`: la fuente de la helada (`nasa_power`) se publica con `datos_con_heladas`.
    respuesta = rotacion(api, cycles=2)
    comprobar_exclusion_por_helada(respuesta, fuentes | {"nasa_power", "mapa_zarc_2025"})
    # El otro lado: zanahoria y descanso no tienen etapa sensible con dato, así que su helada no cambia la luz (R1).
    assert not any(e["kind"] == "high_risk" and set(e["crop_ids"]) <= SIN_HELADA for e in respuesta["excluded"])


def test_ejemplo_la_oferta_y_el_mercado_no_excluyen_y_sin_historia_el_ingreso_no_califica(api):
    # `supply` y `market` nunca se califican (decisión 17): no pueden ser críticos, así que no se puede escribir «con
    # `supply` crítico». Este dataset de ejemplo no publica precios, así que ningún cultivo tiene historia del precio.
    # Lo que sí se comprueba (HU-241, decidido por Felipe el 15 nov 2026): una estrategia solo de cultivos queda sin
    # `scores.income` y lo dice en sus limitaciones; una con abono verde o descanso tiene ingreso 0, porque que no deja
    # cosecha no depende de los precios.
    respuesta = rotacion(api, cycles=2, previous_crop_ids=["haba"])
    comprobar_sin_oferta_ni_mercado(respuesta)
    con_cultivo = [s for s in respuesta["strategies"] if set(s["crop_ids"]) - SIN_COSECHA]
    assert con_cultivo
    for estrategia in con_cultivo:
        for ciclo in estrategia["cycles"]:
            if ciclo["diagnosis"]:
                assert ciclo["diagnosis"]["signals"]["supply"]["status"] == "insufficient_data"
                assert ciclo["diagnosis"]["signals"]["market"]["status"] == "insufficient_data"
        # Lo dice en las limitaciones de su estrategia (R1): por ciclo si hay ingreso, o la limitación general si no.
        assert any("historia del precio" in t or "historia de precio" in t for t in estrategia["limitations"]), estrategia["limitations"]
        if set(estrategia["crop_ids"]) & SIN_COSECHA:
            assert estrategia["scores"]["income"] == 0
        else:
            assert estrategia["scores"]["income"] is None
            assert NO_INCOME in estrategia["limitations"]


def test_ejemplo_el_primer_ciclo_coincide_con_el_diagnostico(api):
    hoy = region_today().isoformat()
    prioridades = {"water": 2, "frost": 4, "heat": 1, "soil": 5, "supply": 0, "market": 1}
    # La rotación actual (papa y maíz) entra con el mismo diagnóstico por ciclo: así se compara más de un cultivo aunque
    # las 10 sugeridas empiecen todas con el mismo.
    respuesta = rotacion(api, irrigated=True, signal_priorities=prioridades, current_crop_ids=["papa", "maiz"])
    comparadas, cultivos = 0, set()
    for estrategia in [*respuesta["strategies"], respuesta["current_strategy"]]:
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


def comparar_primeros_ciclos(cliente, respuesta: dict, prioridades: dict, **extra) -> tuple[int, set[str]]:
    """Cada primer ciclo con diagnóstico (sugeridas y actual) contra `/diagnostics` con la misma entrada: mismas señales,
    calificaciones y luces, y la señal `soil` califica en los dos lados. Devuelve cuántos ciclos y qué cultivos comparó."""
    hoy = region_today().isoformat()
    comparados, cultivos = 0, set()
    for estrategia in [*respuesta["strategies"], respuesta["current_strategy"]]:
        primero = estrategia["cycles"][0]
        if primero["diagnosis"] is None:  # descanso: sin diagnóstico
            continue
        diagnostico = cliente.post(
            "/api/v1/diagnostics",
            json={
                "municipality_id": EJEMPLO_FRIO,
                "crop_id": primero["crop_id"],
                "sowing_date": hoy,
                "irrigated": True,
                "priorities": prioridades,
                **extra,
            },
        )
        assert diagnostico.status_code == 200, diagnostico.text
        cuerpo = diagnostico.json()
        comprobar_primer_ciclo(primero, cuerpo)
        assert primero["light_default"] == cuerpo["overall_default"]["light"]
        # El suelo entra: `soil` califica (pH de ejemplo dentro del rango del cultivo); `comprobar_primer_ciclo` la compara.
        assert cuerpo["signals"]["soil"]["status"] == "available" and cuerpo["signals"]["soil"]["score"] is not None
        comparados += 1
        cultivos.add(primero["crop_id"])
    return comparados, cultivos


def test_ejemplo_el_primer_ciclo_coincide_con_el_diagnostico_con_el_suelo_del_municipio(datos_con_suelo, api):
    # El suelo del municipio (pH 6,0; `datos_con_suelo`, EJEMPLO) sale del dataset en las dos rutas. Con `irrigated` y los pesos
    # del agricultor, las dos luces y las seis señales coinciden, y `soil` califica.
    prioridades = {"water": 2, "frost": 4, "heat": 1, "soil": 5, "supply": 0, "market": 1}
    respuesta = rotacion(api, irrigated=True, signal_priorities=prioridades, current_crop_ids=["papa", "maiz"])
    assert respuesta["soil_basis"] == "municipality"
    comparados, cultivos = comparar_primeros_ciclos(api, respuesta, prioridades)
    assert comparados >= 2 and len(cultivos) >= 2


def test_ejemplo_el_primer_ciclo_coincide_con_el_diagnostico_con_el_suelo_del_lote(datos_con_suelo, client):
    # El mismo `lot_id` en las dos rutas (exige sesión): el suelo es el de las celdas bajo el contorno (pH de mediana 6,3), no el
    # del municipio (6,0). La rejilla es de EJEMPLO y el lote es riego (`irrigated` del lote, HU-164).
    prioridades = {"water": 2, "frost": 4, "heat": 1, "soil": 5, "supply": 0, "market": 1}
    register(client, "rosa.coherencia")
    lote = create_lot(client, geometry=CONTORNO_LOTE, irrigated=True)
    respuesta = rotacion(client, lot_id=lote, signal_priorities=prioridades, current_crop_ids=["papa", "maiz"])
    assert (respuesta["soil_basis"], respuesta["slope_basis"]) == ("lot", "lot")
    comparados, cultivos = comparar_primeros_ciclos(client, respuesta, prioridades, lot_id=lote)
    assert comparados >= 2 and len(cultivos) >= 2


def test_ejemplo_con_prioridad_de_suelo_en_5_el_abono_verde_queda_mejor(api):
    # Dos estrategias de 2 ciclos que solo difieren en el primero: avena con vicia (abono verde, fija nitrógeno) o cebolla,
    # que dura lo mismo (150 días), así que el segundo ciclo cae en la misma fecha. Con la regla `leguminosa_en_rotacion`
    # (favorable desde 1 ciclo con leguminosa), `nitrogen` es favorable con la avena con vicia y unfavorable con la cebolla.
    # Supuestos por confirmar: el agua y el riesgo de la avena y de la cebolla en Samacá no se comparan aquí; se espera que
    # el peso de `soil` en 5 baste para que la avena con vicia gane. `income` va en 0: con HU-241 el abono verde vale 0 en ingreso
    # y con peso 3 perdería por eso; con 0 el caso vale antes y después de esa regla. Sin datos de agua en el ejemplo, muchas estrategias
    # empatan arriba y la de cebolla no entra entre las 10: se pide como rotación actual, que se evalúa igual (decisión 14).
    # Con el ingreso en 0 (HU-241): el abono verde vale 0 en el ingreso siempre, porque no deja cosecha (decidido por
    # Felipe el 15 nov 2026), y la cebolla sin historia de precio no cuenta; este caso compara solo el suelo.
    con, sin = ["avena_vicia", "zanahoria"], ["cebolla_bulbo", "zanahoria"]
    respuesta = rotacion(api, cycles=2, priorities={**EJEMPLO_PRIORIDADES, "income": 0, "soil": 5}, current_crop_ids=sin)
    assert respuesta["weights"]["soil"] == 5
    por_crop_ids = {tuple(s["crop_ids"]): s for s in respuesta["strategies"]}
    actual = respuesta["current_strategy"]
    assert actual["crop_ids"] == sin
    assert por_crop_ids[tuple(con)]["soil_health"]["nitrogen"]["level"] == "favorable"
    assert actual["soil_health"]["nitrogen"]["level"] == "unfavorable"
    assert por_crop_ids[tuple(con)]["total_score"] > actual["total_score"]
    assert por_crop_ids[tuple(con)]["vs_current"]["soil"] > 0


def test_ejemplo_el_peso_del_suelo_cambia_el_orden_de_las_estrategias(api, datos_con_heladas_moderadas, hoy_fijo):
    # Samacá con heladas moderadas en el 30 % de los años (`datos_con_heladas_moderadas`, EJEMPLO): ningún ciclo es de alto
    # riesgo, `frost` califica 55 o 59 en los cultivos sensibles y 100 en el descanso. Con 2 ciclos, sin agua que califique y
    # con el ingreso en prioridad 0 (el descanso vale 0 en el ingreso desde HU-241, así que se aparta para que solo cambie el
    # peso del suelo), `total_score` es el promedio de `soil` y `risk` ponderado (decisión 15):
    #   A = arveja y zanahoria: soil 100 (leguminosa), risk 59.   B = descanso y zanahoria: soil 33, risk 100.
    # `income` va en 0 en las dos corridas a propósito: con HU-241 el descanso y el abono verde valen 0 en `income` siempre y, con
    # peso 3, B (con descanso) perdería por ingreso frente a A. Con peso 0 el ingreso no cuenta y el caso vale antes y después de
    # esa regla: lo único que cambia entre las dos corridas es el peso de `soil`.
    # Los números exactos son del 16 de noviembre de 2026 (`hoy_fijo`), no de otra fecha: con la siembra a mediados de
    # noviembre la etapa media y la final de la arveja (110 días) caen de enero a marzo del año siguiente, así que la serie por
    # año de siembra pierde el último año (8 de 29 años = 28 %, `frost` 59). Sembrando desde enero la ventana cabe en un solo año
    # (9 de 30 = 30 %, `frost` 55) y `risk` baja a 55. Las relaciones valen en cualquier fecha;
    # los números y el primer puesto de A, solo en esta.
    # Con `soil` en 5 (agua y riesgo en 3, ingreso en 0): A = (100*5 + 59*3) / 8 = 85 y B = (33*5 + 100*3) / 8 = 58.
    # Con `soil` en 0, B = 100 y A = 59.
    assert hoy_fijo.isoformat() == "2026-11-16"
    a, b = ["arveja", "zanahoria"], ["descanso", "zanahoria"]
    base = {**EJEMPLO_PRIORIDADES, "income": 0}
    con_peso = rotacion(api, cycles=2, priorities={**base, "soil": 5})
    sin_peso = rotacion(api, cycles=2, priorities={**base, "soil": 0})
    assert con_peso["weights"] == {**base, "soil": 5}
    assert sin_peso["weights"] == {**base, "soil": 0}
    assert con_peso["excluded_counts"] == sin_peso["excluded_counts"]  # lo único que cambia es el peso
    # Relaciones, que valen en cualquier fecha (comprobadas con el «hoy» simulado en 2026-11-16, 2027-01-01, 2027-03-15,
    # 2027-05-10 y 2027-12-31). Con el suelo en 5 la de suelo flojo no entra entre las 10 y la de mejor suelo sí, y sube
    # frente a su puesto con el suelo en 0. Ser la primera NO vale siempre (con otra fecha es la 2.ª o la 5.ª): va abajo.
    assert rank_de(con_peso, b) is None
    assert rank_de(con_peso, a) is not None
    assert rank_de(sin_peso, a) is None or rank_de(con_peso, a) < rank_de(sin_peso, a)
    # Con el suelo en 0 no cuenta: la de menor riesgo (B) es la primera y la de mejor suelo (A) queda detrás.
    assert rank_de(sin_peso, b) == 1
    assert rank_de(sin_peso, a) is None or rank_de(sin_peso, a) > rank_de(sin_peso, b)
    # Los números exactos y el primer puesto, con la fecha fija.
    assert rank_de(con_peso, a) == 1
    por_a = next(s for s in con_peso["strategies"] if s["crop_ids"] == a)
    assert (por_a["scores"]["soil"], por_a["scores"]["risk"], por_a["total_score"]) == (100, 59, 85)
    por_b = next(s for s in sin_peso["strategies"] if s["crop_ids"] == b)
    assert (por_b["scores"]["soil"], por_b["scores"]["risk"], por_b["total_score"]) == (33, 100, 100)
    por_a0 = next(s for s in sin_peso["strategies"] if s["crop_ids"] == a)
    assert por_a0["total_score"] == 59
    # El rango de A con el suelo en 0 es 4: `descanso+zanahoria` y `zanahoria+descanso` tienen 100 (sin ciclo sensible) y van
    # antes; A, con 59, queda tras ellas (y gana el desempate por `crop_ids` a otras de 59). Se asierta el orden relativo.
    ciento = [s for s in sin_peso["strategies"] if s["total_score"] == 100]
    assert {tuple(s["crop_ids"]) for s in ciento} >= {tuple(b), ("zanahoria", "descanso")}
    assert all(s["rank"] < por_a0["rank"] for s in ciento)
    assert por_a0["rank"] == 4


def test_ejemplo_un_suelo_que_toca_el_borde_del_ph_de_un_cultivo_no_lo_excluye(armar_ejemplo):
    # Suelo de EJEMPLO (R5) con pH 8,8: el intervalo p05 a p95 es de 8,5 a 9,1 (`publicar_ejemplo`: pH ± 0,3; `8.8 - 0.3` es
    # exactamente 8.5 en coma flotante). El máximo de la papa y del maíz es 8,5 (`catalog/crops.yaml`): tocan el borde y no se
    # excluyen (`outside_tolerated` usa `<`, no `<=`). Quedan fuera de todo el intervalo la arveja y la cebolla de bulbo (máximo
    # 8,3) y la avena con vicia (7,5); la haba (8,6) y la zanahoria (8,7) lo cruzan y tampoco se excluyen.
    assert 8.8 - 0.3 == 8.5
    api = armar_ejemplo(ph=8.8)
    respuesta = rotacion(api, cycles=2)
    por_ph = {e["crop_id"] for e in respuesta["excluded"] if e["kind"] == "soil_ph"}
    # `excluded` trae solo las primeras 10 de `excluded_counts["soil_ph"]`: se ven la arveja y la avena con vicia; la cebolla se
    # comprueba por su ausencia en `strategies`.
    assert respuesta["excluded_counts"]["soil_ph"] > len(respuesta["excluded"])
    assert {"arveja", "avena_vicia"} <= por_ph  # el caso no pasa en vacío
    assert not {"papa", "maiz", "haba", "zanahoria"} & por_ph
    en_estrategias = {c for e in respuesta["strategies"] for c in e["crop_ids"]}
    assert {"papa", "maiz"} <= en_estrategias
    assert not {"arveja", "cebolla_bulbo", "avena_vicia"} & en_estrategias


def test_ejemplo_con_prioridad_de_suelo_en_5_una_estrategia_con_abono_verde_queda_mejor_que_la_misma_sin_el(datos_con_suelo, api, hoy_fijo):
    # Suelo de EJEMPLO (R5, `datos_con_suelo`): pH 6,0 (el óptimo de la avena con vicia) y carbono orgánico bajo (20 g/kg, bajo los
    # 29 de `materia_organica_ciclos`), que es donde el abono verde cuenta en `organic_carbon`: 1 ciclo = `moderate` y sin él
    # `unfavorable`. Sin datos de heladas ni de agua, `risk` vale 100 en todas y no decide.
    # Par: con = avena con vicia (abono verde, `kind = cover`) y zanahoria; sin = arveja y zanahoria. (Con papa no sirve: como rotación
    # actual haría de la papa un cultivo anterior y `papa_seguida` la sacaría de las sugeridas.) Las dos fijan nitrógeno (`nitrogen`
    # favorable) y cubren el suelo, así que solo difieren en el abono verde:
    #   con: soil 88 (75 + el carbono `moderate`) y sin: soil 75 (carbono `unfavorable`).
    # `income` va en 0 (con HU-241 el abono verde vale 0 en `income`; con peso 0 no cuenta y la comparación es solo de suelo).
    # Con `soil` en 5 (water y risk en 3): con = (88*5 + 100*3) / 8 = 93 y sin = (75*5 + 100*3) / 8 = 84. Con `soil` en 0 las dos
    # valen 100 y el desempate es `crop_ids`: arveja va antes que avena_vicia. Los puestos son del 16 de nov de 2026 (`hoy_fijo`).
    assert hoy_fijo.isoformat() == "2026-11-16"
    con, sin = ["avena_vicia", "zanahoria"], ["arveja", "zanahoria"]
    base = {**EJEMPLO_PRIORIDADES, "income": 0}
    con_peso = rotacion(api, cycles=2, priorities={**base, "soil": 5}, current_crop_ids=sin)
    # Con `soil` en 0 no se pide la actual: así la igual sin abono verde también se sugiere y tiene `rank`.
    sin_peso = rotacion(api, cycles=2, priorities={**base, "soil": 0})
    assert con_peso["weights"]["soil"] == 5 and sin_peso["weights"]["soil"] == 0
    por_con = next(s for s in con_peso["strategies"] if s["crop_ids"] == con)
    # La misma sin abono verde se evalúa como rotación actual (decisión 14): no entra entre las 10 pero se compara con ella.
    actual = con_peso["current_strategy"]
    assert actual["crop_ids"] == sin and actual["rank"] is None
    assert por_con["soil_health"]["organic_carbon"]["level"] == "moderate"
    assert actual["soil_health"]["organic_carbon"]["level"] == "unfavorable"
    assert por_con["soil_health"]["nitrogen"]["level"] == actual["soil_health"]["nitrogen"]["level"] == "favorable"
    assert (por_con["scores"]["soil"], por_con["scores"]["risk"], por_con["total_score"]) == (88, 100, 93)
    assert (actual["scores"]["soil"], actual["scores"]["risk"], actual["total_score"]) == (75, 100, 84)
    # Con `soil` en 5 el que tiene abono verde queda 6.º y el igual sin él no entra entre las 10 (aquí es la
    # actual); con `soil` en 0 se invierte: la igual sin él queda 6.ª y la que tiene abono verde no entra entre las 10.
    assert rank_de(con_peso, con) == 6
    assert rank_de(con_peso, sin) is None  # es la rotación actual: no se repite entre las sugeridas
    assert rank_de(sin_peso, sin) == 6
    assert rank_de(sin_peso, con) is None
