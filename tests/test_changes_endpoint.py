from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api import calculations
from backend.api.calc_models import ChangesResponse
from backend.api.catalogs import require_dataset
from backend.api.main import app
from backend.dataset import load
from backend.db.session import get_db
from common.signal_sources import SignalSource, SignalSources

EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples"
URL = "/api/v1/changes"
PARAMS = {"municipality_id": "15001", "crop_id": "papa"}


@pytest.fixture
def changes_api(monkeypatch):
    """Dataset de ejemplo y temperatura ficticia para probar el caso no apto."""
    dataset = load(EXAMPLES)

    municipalities = dict(dataset.municipalities)
    municipalities["15001"] = replace(
        municipalities["15001"],
        tmean_annual_c=100.0,
    )
    dataset = replace(dataset, municipalities=municipalities)

    # El archivo de ejemplo utiliza source_id="ejemplo".
    # Esto solo configura la prueba; no sustituye fuentes en producción.
    configuration = SignalSources(
        version="ejemplo",
        regions={
            dataset.region["id"]: {
                "frost": SignalSource(used="ejemplo"),
                "heat": SignalSource(used="ejemplo"),
                "water": SignalSource(used="ejemplo"),
            }
        },
    )
    monkeypatch.setattr(
        calculations,
        "get_signal_sources",
        lambda: configuration,
    )

    holder = {"dataset": dataset}
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_dataset] = lambda: holder["dataset"]

    try:
        with TestClient(app) as client:
            yield client, holder
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def test_not_suitable_returns_complete_response(changes_api):
    client, holder = changes_api

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200, response.text
    body = response.json()
    ChangesResponse.model_validate(body)

    assert body["suitability"]["level"] == "not_suitable"
    assert body["suitability"]["reasons"]
    assert body["best_windows"] == {"before": [], "after": []}
    assert body["weights_basis"] == "default"
    assert body["versions"] == {
        "dataset": holder["dataset"].version,
        "rules": holder["dataset"].rules_version,
    }
    assert len(body["months"]) == 12
    assert body["months"][0]["frost_freq_pct"]["before"] == 60
    assert body["periods"]["before"]["source_id"] == "ejemplo"
    assert body["request"]["irrigated"] is None
    assert any("riego" in text for text in body["limitations"])
    assert any("Datos de ejemplo" in text for text in body["limitations"])


def test_missing_climate_returns_insufficient_data(changes_api):
    client, holder = changes_api
    holder["dataset"] = replace(
        holder["dataset"],
        climate_change_month=None,
    )

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200, response.text
    for month in response.json()["months"]:
        for indicator in (
            "frost_freq_pct",
            "precip_normal_mm",
            "tmax_p90_c",
        ):
            assert month[indicator] == {
                "status": "insufficient_data",
                "before": None,
                "after": None,
                "change": None,
            }


@pytest.mark.parametrize(
    "params",
    [
        {**PARAMS, "municipality_id": "99999"},
        {**PARAMS, "crop_id": "no_existe"},
        {**PARAMS, "irrigated": "valor_invalido"},
    ],
)
def test_invalid_input_returns_422(changes_api, params):
    client, _ = changes_api
    assert client.get(URL, params=params).status_code == 422


def test_non_crop_is_rejected(changes_api):
    client, holder = changes_api
    crops = {key: dict(value) for key, value in holder["dataset"].crops.items()}
    crops["papa"]["kind"] = "green_manure"
    holder["dataset"] = replace(holder["dataset"], crops=crops)

    assert client.get(URL, params=PARAMS).status_code == 422


def test_missing_periods_returns_503(changes_api):
    client, holder = changes_api
    holder["dataset"] = replace(holder["dataset"], periods=())

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dataset_unavailable"


def test_suitable_crop_remains_unimplemented(changes_api):
    client, holder = changes_api
    dataset = holder["dataset"]
    municipalities = dict(dataset.municipalities)
    municipalities["15001"] = replace(
        municipalities["15001"],
        tmean_annual_c=dataset.crops["papa"]["tmean_opt_min_c"],
    )
    holder["dataset"] = replace(dataset, municipalities=municipalities)

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


def test_unknown_suitability_remains_unimplemented(changes_api):
    client, holder = changes_api
    dataset = holder["dataset"]
    municipalities = dict(dataset.municipalities)
    municipalities["15001"] = replace(
        municipalities["15001"],
        tmean_annual_c=None,
    )
    holder["dataset"] = replace(dataset, municipalities=municipalities)

    assert client.get(URL, params=PARAMS).status_code == 501


def test_irrigated_parameter_is_preserved(changes_api):
    client, _ = changes_api

    response = client.get(
        URL,
        params={**PARAMS, "irrigated": "true"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["request"]["irrigated"] is True


@pytest.fixture
def split_sources_api(changes_api, monkeypatch):
    """Cifras ficticias: POWER para heladas/calor e IMERG para lluvia."""
    client, holder = changes_api
    dataset = holder["dataset"]
    periods = (
        {"period_id": "power_before", "start_year": 1981, "end_year": 2000, "source_id": "nasa_power"},
        {"period_id": "power_after", "start_year": 2005, "end_year": 2024, "source_id": "nasa_power"},
        {"period_id": "rain_before", "start_year": 2001, "end_year": 2012, "source_id": "imerg"},
        {"period_id": "rain_after", "start_year": 2013, "end_year": 2024, "source_id": "imerg"},
    )
    rows = [
        {
            "municipality_id": "15001",
            "period_id": period["period_id"],
            "source_id": period["source_id"],
            "month": 1,
            "frost_freq_pct": frost,
            "tmax_p90_c": heat,
            "precip_normal_mm": rain,
            "years": period["end_year"] - period["start_year"] + 1,
            "quality": "ok",
        }
        for period, frost, heat, rain in (
            (periods[0], 30.0, 20.0, 999.0),
            (periods[1], 18.0, 22.0, 999.0),
            (periods[2], None, None, 28.0),
            (periods[3], None, None, 35.0),
        )
    ]
    holder["dataset"] = replace(
        dataset,
        # Desorden deliberado: el endpoint debe ordenar por años y fuente.
        periods=tuple(reversed(periods)),
        climate_change_month=pl.DataFrame(rows),
    )
    configuration = SignalSources(
        version="ejemplo",
        regions={
            dataset.region["id"]: {
                "frost": SignalSource(used="nasa_power"),
                "heat": SignalSource(used="nasa_power"),
                "water": SignalSource(used="imerg", caveat="Aviso de lluvia de ejemplo."),
            }
        },
    )
    monkeypatch.setattr(calculations, "get_signal_sources", lambda: configuration)
    return client, holder


def test_power_and_imerg_use_their_own_periods(split_sources_api):
    client, _ = split_sources_api
    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200, response.text
    body = response.json()
    ChangesResponse.model_validate(body)
    assert body["periods"]["before"]["source_id"] == "nasa_power"
    assert body["periods"]["before"]["start_year"] == 1981
    assert body["precip_periods"]["before"]["source_id"] == "imerg"
    assert body["precip_periods"]["before"]["start_year"] == 2001
    january = body["months"][0]
    assert january["frost_freq_pct"]["change"] == -12
    assert january["tmax_p90_c"]["change"] == 2
    assert january["precip_normal_mm"] == {"status": "available", "before": 28, "after": 35, "change": 7}
    assert any("reanálisis" in text for text in body["limitations"])
    assert any("desde 2000" in text for text in body["limitations"])
    assert "Aviso de lluvia de ejemplo." in body["limitations"]
    assert any("2001–2012" in text and "2013–2024" in text for text in body["reasons"])


@pytest.mark.parametrize("missing_source, indicator", [("imerg", "precip_normal_mm"), ("nasa_power", "frost_freq_pct")])
def test_missing_source_values_are_not_replaced(split_sources_api, missing_source, indicator):
    client, holder = split_sources_api
    dataset = holder["dataset"]
    holder["dataset"] = replace(
        dataset,
        climate_change_month=dataset.climate_change_month.filter(pl.col("source_id") != missing_source),
    )

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200, response.text
    january = response.json()["months"][0]
    assert january[indicator] == {"status": "insufficient_data", "before": None, "after": None, "change": None}
    other_indicator = "frost_freq_pct" if missing_source == "imerg" else "precip_normal_mm"
    assert january[other_indicator]["status"] == "available"


def test_missing_rain_period_does_not_fall_back_to_power(split_sources_api):
    client, holder = split_sources_api
    dataset = holder["dataset"]
    holder["dataset"] = replace(dataset, periods=tuple(item for item in dataset.periods if item["source_id"] != "imerg"))

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dataset_unavailable"


@pytest.mark.parametrize(
    "field, value",
    [
        ("period_id", ""),
        ("period_id", 1),
        ("period_id", "p2005_2024"),  # Identificador duplicado.
        ("start_year", True),
        ("start_year", "1981"),
        ("start_year", 1981.5),
        ("end_year", 2005),  # Se solapa con el periodo posterior.
        ("end_year", 1980),  # Fin anterior al inicio.
    ],
)
def test_invalid_period_metadata_returns_503(changes_api, field, value):
    client, holder = changes_api
    dataset = holder["dataset"]
    periods = [dict(item) for item in dataset.periods]
    periods[0][field] = value
    holder["dataset"] = replace(dataset, periods=tuple(periods))

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 503, response.text
    assert response.json()["error"]["request_id"]


def test_more_than_two_periods_of_same_source_are_rejected(changes_api):
    client, holder = changes_api
    dataset = holder["dataset"]
    extra = {"period_id": "extra", "start_year": 2025, "end_year": 2026, "source_id": "ejemplo"}
    holder["dataset"] = replace(dataset, periods=(*dataset.periods, extra))

    assert client.get(URL, params=PARAMS).status_code == 503


def test_missing_one_period_keeps_other_value(changes_api):
    client, holder = changes_api
    dataset = holder["dataset"]
    holder["dataset"] = replace(
        dataset,
        climate_change_month=dataset.climate_change_month.filter(pl.col("period_id") != dataset.periods[0]["period_id"]),
    )

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200, response.text
    january = response.json()["months"][0]["frost_freq_pct"]
    assert january["status"] == "insufficient_data"
    assert january["before"] is None
    assert january["after"] is not None
    assert january["change"] is None


@pytest.mark.parametrize("irrigated", ["true", "false"])
def test_explicit_irrigation_does_not_claim_it_was_omitted(changes_api, irrigated):
    client, _ = changes_api
    response = client.get(URL, params={**PARAMS, "irrigated": irrigated})

    assert response.status_code == 200, response.text
    assert response.json()["request"]["irrigated"] is (irrigated == "true")
    assert not any("No se indicó" in text for text in response.json()["limitations"])


def test_endpoint_does_not_access_database_or_modify_dataset(changes_api):
    client, holder = changes_api
    dataset = holder["dataset"]
    original = dataset.climate_change_month.clone()

    def forbidden_database():
        pytest.fail("El endpoint de cálculo no debe acceder a la base de datos")

    app.dependency_overrides[get_db] = forbidden_database
    first = client.get(URL, params=PARAMS)
    second = client.get(URL, params=PARAMS)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert dataset.climate_change_month.equals(original)
