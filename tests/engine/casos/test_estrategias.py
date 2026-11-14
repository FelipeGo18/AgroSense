"""Casos de referencia de estrategias de rotación (HU-121, PR 1). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Todos esperan el motor (`/rotations` responde 501 hoy) y van con `xfail(strict=True)`: cuando la HU pase, la prueba falla
hasta quitar la marca. Los resultados salen de la HU-121, del contrato y de «Estrategias de rotación»; lo que la spec no
deja deducir queda como «supuesto por confirmar».

TODO(HU-121): casos reales sobre `data/published` con la `dataset_version` 2026.11.11 (llega con el PR #62).
"""

import pytest

from common.region import region_today
from tests.engine.casos.conftest import EJEMPLO_CALIDO, rotacion

ESPERA_REGLA = pytest.mark.xfail(strict=True, reason="espera HU-081, HU-084 y HU-062 (PR #62)")
ESPERA_ESTRATEGIAS = pytest.mark.xfail(strict=True, reason="espera HU-081 y HU-084")

# Criterios de HU-121 sin caso en este PR: ver el informe de T2 (hace falta publicar tablas de heladas, oferta y suelo).


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
