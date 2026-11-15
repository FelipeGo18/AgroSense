"""Casos de referencia de «Qué cambió» (HU-121): ejemplo del contrato y endpoint real.

Las filas son de EJEMPLO (R5), con enero sin calor en el primer periodo.
HU-218 ya responde: estos casos no llevan xfail.
"""

from dataclasses import replace

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api import calc_examples, calculations
from backend.dataset import get_dataset
from common.signal_sources import SignalSource, SignalSources
from tests.engine.casos.conftest import EJEMPLO_FRIO
from tests.textos import speaks_as_forecast

VARIABLES = ("frost_freq_pct", "precip_normal_mm", "tmax_p90_c")


@pytest.fixture
def api(api, monkeypatch):
    """Mismo servidor de los casos, con dos periodos y filas de ejemplo explícitas."""
    dataset = get_dataset()
    periods = (
        {"period_id": "old", "start_year": 1981, "end_year": 2000, "source_id": "nasa_power"},
        {"period_id": "new", "start_year": 2005, "end_year": 2024, "source_id": "nasa_power"},
        {"period_id": "rain_old", "start_year": 2001, "end_year": 2012, "source_id": "imerg"},
        {"period_id": "rain_new", "start_year": 2013, "end_year": 2024, "source_id": "imerg"},
    )
    rows = [
        {
            "municipality_id": EJEMPLO_FRIO,
            "period_id": p["period_id"],
            "source_id": p["source_id"],
            "month": 1,
            "frost_freq_pct": value if p["source_id"] == "nasa_power" else None,
            "tmax_p90_c": None if p["period_id"] != "new" else 21.4,
            "precip_normal_mm": value,
            "quality": "partial",
        }
        for p, value in zip(periods, (30.0, 18.0, 28.0, 35.0), strict=True)
    ]
    dataset = replace(dataset, periods=periods, climate_change_month=pl.DataFrame(rows))
    monkeypatch.setattr(calculations, "require_dataset", lambda: dataset)
    sources = SignalSources(
        "ejemplo",
        {
            dataset.region["id"]: {
                "frost": SignalSource("nasa_power"),
                "heat": SignalSource("nasa_power"),
                "water": SignalSource("imerg", et0="nasa_power"),
            }
        },
    )
    monkeypatch.setattr(calculations, "get_signal_sources", lambda: sources)
    return api


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


def test_ejemplo_un_mes_sin_datos_en_un_periodo_da_diferencia_insufficient_data(api):
    cuerpo = cambios(api)
    assert len(cuerpo["months"]) == 12
    assert comprobar_meses(cuerpo) >= 1
    assert cuerpo["months"][0]["frost_freq_pct"]["change"] == -12


def test_ejemplo_misma_entrada_misma_salida(api):
    # R4
    assert cambios(api) == cambios(api)


def test_ejemplo_los_dos_periodos_son_de_la_misma_fuente_y_el_primero_es_anterior(api):
    comprobar_periodos(cambios(api))


def test_ejemplo_la_respuesta_trae_versiones_y_limitaciones_sin_pronostico(api):
    comprobar_textos(cambios(api))
