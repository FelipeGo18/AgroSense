"""Casos de referencia de «Qué cambió» (HU-121, PR 3). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Todos esperan el endpoint (`GET /api/v1/changes` responde 501 hoy) y van con `xfail(strict=True)`: cuando las HU pasen,
la prueba falla hasta quitar la marca. Lo que la spec no deja deducir queda como «supuesto por confirmar».

TODO(HU-216): `pipeline.build.publish()` todavía no escribe `climate_change_month`. El dataset de ejemplo de estos casos
no tiene el clima de dos periodos y el caso del mes sin datos se completa con esa tabla (sin inventar el Parquet).
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

ESPERA = pytest.mark.xfail(strict=True, reason="espera HU-216 y HU-218")
EJEMPLO_FRIO = "15646"  # Samacá, de `SAMPLE_MUNICIPALITIES` (tests/conftest.py): municipio de ejemplo (R5)
VARIABLES = ("frost_freq_pct", "precip_normal_mm", "tmax_p90_c")


@pytest.fixture
def api(dataset_con_clima) -> TestClient:
    return TestClient(app)


def cambios(api: TestClient, **campos) -> dict:
    respuesta = api.get("/api/v1/changes", params={"municipality_id": EJEMPLO_FRIO, "crop_id": "papa", **campos})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@ESPERA
def test_ejemplo_un_mes_sin_datos_en_un_periodo_da_diferencia_insufficient_data(api):
    # Entrada pendiente de HU-216: un mes con un solo periodo en `climate_change_month`. Hoy no se puede armar.
    cuerpo = cambios(api)
    assert len(cuerpo["months"]) == 12
    for mes in cuerpo["months"]:
        for variable in VARIABLES:
            dato = mes[variable]
            if dato["status"] == "insufficient_data":
                # R1: sin datos en un periodo, el valor de ese periodo y la diferencia son nulos; nunca se compara con uno.
                assert dato["change"] is None, (mes["month"], variable)
                assert dato["before"] is None or dato["after"] is None, (mes["month"], variable)
            else:
                assert dato["before"] is not None and dato["after"] is not None
                # `change` es después menos antes (contrato).
                assert dato["change"] == pytest.approx(dato["after"] - dato["before"], abs=0.11)


@ESPERA
def test_ejemplo_misma_entrada_misma_salida(api):
    # R4
    assert cambios(api) == cambios(api)


@ESPERA
def test_ejemplo_los_dos_periodos_son_de_la_misma_fuente_y_el_primero_es_anterior(api):
    periodos = cambios(api)["periods"]
    assert periodos["before"]["source_id"] == periodos["after"]["source_id"]
    assert periodos["before"]["end_year"] < periodos["after"]["start_year"]
    assert periodos["before"]["period_id"] != periodos["after"]["period_id"]


@ESPERA
def test_ejemplo_la_respuesta_trae_versiones_y_limitaciones_sin_pronostico(api):
    cuerpo = cambios(api)
    assert cuerpo["versions"]["dataset"]
    assert cuerpo["versions"]["rules"]
    # Supuesto por confirmar: con `nasa_power` las limitaciones dicen que es un reanálisis (ejemplo del contrato).
    assert cuerpo["limitations"]
    if cuerpo["periods"]["before"]["source_id"] == "nasa_power":
        assert any("reanálisis" in texto for texto in cuerpo["limitations"])
    # Historia comparada: ninguna razón se presenta como pronóstico de lo que va a pasar.
    for razon in cuerpo["reasons"]:
        assert "pronóstico" not in razon.lower() or "no es" in razon.lower()
