"""Casos de referencia de «Qué cambió» (HU-121, PR 3). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Las comprobaciones viven en funciones que corren **hoy, sin marca**, sobre el ejemplo del contrato
(`backend/api/calc_examples.CHANGES`, que trae un mes sin datos: el `tmax_p90_c` de enero). Así, un campo mal escrito no
se esconde en el `xfail` (revisión de Haider del PR #86). Las mismas funciones corren sobre `GET /api/v1/changes`, que
responde 501 hoy: esos casos van con `xfail(strict=True)` y, cuando las HU pasen, la prueba falla hasta quitar la marca.

TODO(HU-216): `pipeline.build.publish()` todavía no escribe `climate_change_month`. El dataset de ejemplo no tiene el
clima de dos periodos, así que el caso del endpoint con un mes sin datos se completa con esa tabla (sin inventar el
Parquet).
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import calc_examples
from tests.engine.casos.conftest import EJEMPLO_FRIO
from tests.textos import speaks_as_forecast

ESPERA = pytest.mark.xfail(strict=True, reason="espera HU-216 y HU-218")
VARIABLES = ("frost_freq_pct", "precip_normal_mm", "tmax_p90_c")


def cambios(api: TestClient, **campos) -> dict:
    respuesta = api.get("/api/v1/changes", params={"municipality_id": EJEMPLO_FRIO, "crop_id": "papa", **campos})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def comprobar_meses(cuerpo: dict) -> int:
    """R1 en cada variable de cada mes. Devuelve cuántas salen `insufficient_data`, para que el caso exija al menos una."""
    assert cuerpo["months"]
    sin_datos = 0
    for mes in cuerpo["months"]:
        for variable in VARIABLES:
            dato = mes[variable]
            if dato["status"] == "insufficient_data":
                sin_datos += 1
                # Sin datos en un periodo, ese valor y la diferencia son nulos: nunca se compara con un solo periodo.
                assert dato["change"] is None, (mes["month"], variable)
                assert dato["before"] is None or dato["after"] is None, (mes["month"], variable)
            else:
                assert dato["status"] == "available", (mes["month"], variable)
                assert dato["before"] is not None and dato["after"] is not None
                # `change` es después menos antes (contrato). Supuesto por confirmar: redondeo a un decimal.
                assert dato["change"] == pytest.approx(dato["after"] - dato["before"], abs=0.11)
    return sin_datos


def comprobar_periodos(cuerpo: dict) -> None:
    """Los dos periodos son de la misma fuente y vienen en la respuesta («Qué cambió en la zona»)."""
    periodos = cuerpo["periods"]
    assert periodos["before"]["source_id"] == periodos["after"]["source_id"]
    assert periodos["before"]["period_id"] != periodos["after"]["period_id"]
    # Supuesto por confirmar: el primer periodo termina antes de que empiece el segundo (periodos por defecto).
    assert periodos["before"]["end_year"] < periodos["after"]["start_year"]


def comprobar_textos(cuerpo: dict) -> None:
    """R4 y «nunca pronóstico»: versiones, limitaciones y razones sin hablar del futuro."""
    assert cuerpo["versions"]["dataset"] and cuerpo["versions"]["rules"]
    assert cuerpo["limitations"]
    if cuerpo["periods"]["before"]["source_id"] == "nasa_power":
        # NASA POWER es un reanálisis y se dice (R8), como en el ejemplo del contrato.
        assert any("reanálisis" in texto for texto in cuerpo["limitations"])
    for texto in [*cuerpo["reasons"], *cuerpo["limitations"]]:
        assert not speaks_as_forecast(texto), texto


def test_ejemplo_del_contrato_cumple_las_comprobaciones_y_tiene_un_mes_sin_datos():
    """Corre hoy: valida las comprobaciones contra la forma del contrato."""
    cuerpo = calc_examples.CHANGES
    assert comprobar_meses(cuerpo) >= 1
    comprobar_periodos(cuerpo)
    comprobar_textos(cuerpo)


@ESPERA
def test_ejemplo_un_mes_sin_datos_en_un_periodo_da_diferencia_insufficient_data(api):
    cuerpo = cambios(api)
    assert len(cuerpo["months"]) == 12
    # La entrada con un mes en un solo periodo llega con HU-216; sin ella este caso no pasa (y debe ser así).
    assert comprobar_meses(cuerpo) >= 1


@ESPERA
def test_ejemplo_misma_entrada_misma_salida(api):
    # R4
    assert cambios(api) == cambios(api)


@ESPERA
def test_ejemplo_los_dos_periodos_son_de_la_misma_fuente_y_el_primero_es_anterior(api):
    comprobar_periodos(cambios(api))


@ESPERA
def test_ejemplo_la_respuesta_trae_versiones_y_limitaciones_sin_pronostico(api):
    comprobar_textos(cambios(api))
