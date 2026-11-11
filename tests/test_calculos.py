"""HU-012: los endpoints de cálculo ya tienen su forma del contrato, sus ejemplos y sus validaciones; responden 501."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import calc_examples as ex
from backend.api import calc_models as m
from backend.api.main import app
from backend.config.settings import get_settings

SOON = (date.today() + timedelta(days=40)).isoformat()
DIAGNOSIS = {"municipality_id": "15646", "crop_id": "papa", "sowing_date": SOON}
ROTATION = {"municipality_id": "15646", "sowing_date": SOON, "priorities": {"water": 3, "soil": 5, "income": 2, "risk": 4}}
WATER = {"municipality_id": "15646", "total_area_ha": 1.26, "crops": [{"crop_id": "papa", "area_pct": 100, "sowing_date": SOON}]}


@pytest.mark.parametrize(
    ("model", "example"),
    [
        (m.DiagnosisResponse, ex.DIAGNOSIS_OK),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_SUITABLE),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_EVALUABLE),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_APPLICABLE),
        (m.RotationResponse, ex.ROTATIONS),
        (m.RotationResponse, ex.ROTATIONS_EMPTY),
        (m.RotationResponse, ex.ROTATIONS_NO_CURRENT),
        (m.WaterPlanResponse, ex.WATER_PLAN),
        (m.ChangesResponse, ex.CHANGES),
        (m.TrendsResponse, ex.TRENDS),
        (m.MunicipalitySoil, ex.SOIL),
        *[(m.ErrorBody, body) for body in ex.ERRORS.values()],
    ],
)
def test_cada_ejemplo_cumple_su_modelo(model, example):
    model.model_validate(example)


def test_los_ejemplos_de_calculo_se_rotulan_como_ejemplo():
    """R5: ningún ejemplo pasa por un resultado real."""
    for example in (ex.DIAGNOSIS_OK, ex.ROTATIONS, ex.WATER_PLAN, ex.CHANGES, ex.TRENDS, ex.SOIL):
        assert example["versions"] == {"dataset": "ejemplo", "rules": "ejemplo"}


def test_los_ejemplos_cubren_cada_estado():
    statuses = {
        signal["status"]
        for example in (ex.DIAGNOSIS_OK, ex.DIAGNOSIS_NOT_EVALUABLE, ex.DIAGNOSIS_NOT_APPLICABLE)
        for signal in example["signals"].values()
    }
    assert statuses == {"available", "insufficient_data", "not_applicable"}
    assert ex.ROTATIONS["excluded"] and ex.ROTATIONS["current_strategy"]["issues"]
    assert any(month["tmax_p90_c"]["status"] == "insufficient_data" for month in ex.CHANGES["months"])


def test_el_openapi_trae_los_endpoints_de_calculo_con_sus_ejemplos():
    paths = app.openapi()["paths"]
    for path, method, codes in [
        ("/api/v1/diagnostics", "post", {"200", "401", "404", "422", "501", "503"}),
        ("/api/v1/rotations", "post", {"200", "401", "404", "422", "501", "503"}),
        ("/api/v1/water-plans", "post", {"200", "422", "501", "503"}),
        ("/api/v1/changes", "get", {"200", "422", "501", "503"}),
        ("/api/v1/trends", "get", {"200", "422", "501", "503"}),
        ("/api/v1/catalogs/municipalities/{municipality_id}/soil", "get", {"200", "404", "503"}),
    ]:
        responses = paths[path][method]["responses"]
        assert codes <= set(responses), path
        content = responses["200"]["content"]["application/json"]
        assert "examples" in content or "example" in content, path


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/diagnostics", DIAGNOSIS),
        ("post", "/api/v1/rotations", {**ROTATION, "previous_crop_ids": ["papa"], "current_crop_ids": ["papa", "arveja"]}),
        ("post", "/api/v1/water-plans", WATER),
        ("get", "/api/v1/changes?municipality_id=15646&crop_id=papa", None),
        ("get", f"/api/v1/trends?municipality_id=15646&crop_id=papa&sowing_date={SOON}", None),
    ],
)
def test_una_entrada_valida_responde_501_con_la_forma_de_los_errores(dataset, method, path, body):
    response = getattr(TestClient(app), method)(path, **({"json": body} if body else {}))
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"
    assert response.json()["error"]["request_id"]


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/diagnostics", {**DIAGNOSIS, "crop_id": "yuca"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "crop_id": "avena_vicia"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "municipality_id": "05001"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "sowing_date": (date.today() - timedelta(days=40)).isoformat()}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "sowing_date": (date.today() + timedelta(days=420)).isoformat()}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "priorities": {s: 0 for s in ("water", "frost", "heat", "soil", "supply", "market")}}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "otro_campo": 1}),
        ("/api/v1/rotations", {**ROTATION, "cycles": 4}),
        ("/api/v1/rotations", {**ROTATION, "current_crop_ids": ["papa"]}),
        ("/api/v1/rotations", {**ROTATION, "previous_crop_ids": ["papa", "arveja", "haba", "maiz"]}),
        ("/api/v1/rotations", {**ROTATION, "priorities": {"water": 0, "soil": 0, "income": 0, "risk": 0}}),
        (
            "/api/v1/water-plans",
            {
                **WATER,
                "crops": [
                    {"crop_id": "papa", "area_pct": 70, "sowing_date": SOON},
                    {"crop_id": "arveja", "area_pct": 40, "sowing_date": SOON},
                ],
            },
        ),
    ],
)
def test_una_entrada_invalida_responde_422(dataset, path, body):
    response = TestClient(app).post(path, json=body)
    assert response.status_code == 422, response.json()
    assert response.json()["error"]["code"] == "invalid_input"


def test_el_mes_en_curso_se_acepta_aunque_su_dia_1_ya_paso(dataset):
    first = date.today().replace(day=1).isoformat()
    assert TestClient(app).post("/api/v1/diagnostics", json={**DIAGNOSIS, "sowing_date": first}).status_code == 501


def test_con_lot_id_y_sin_sesion_responde_401(dataset, client):
    response = client.post("/api/v1/diagnostics", json={**DIAGNOSIS, "lot_id": "00000000-0000-4000-8000-000000000001"})
    assert response.status_code == 401


def test_sin_dataset_los_calculos_responden_503():
    assert TestClient(app).post("/api/v1/diagnostics", json=DIAGNOSIS).status_code == 503


def test_el_suelo_del_municipio_sin_suelo_publicado_responde_503(dataset):
    response = TestClient(app).get("/api/v1/catalogs/municipalities/15646/soil")
    assert response.status_code == 503 and response.json()["error"]["code"] == "dataset_unavailable"
    assert TestClient(app).get("/api/v1/catalogs/municipalities/99999/soil").status_code == 404


def test_el_suelo_del_municipio_con_los_datos_de_ejemplo(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(Path("data/examples").resolve()))
    get_settings.cache_clear()
    body = TestClient(app).get("/api/v1/catalogs/municipalities/15646/soil").json()
    m.MunicipalitySoil.model_validate(body)
    assert body["source_id"] == "ejemplo" and body["versions"]["dataset"] == "ejemplo"
    assert body["ph"]["p05"] <= body["ph"]["value"] <= body["ph"]["p95"]
    assert body["slope_pct"] == 9.0
