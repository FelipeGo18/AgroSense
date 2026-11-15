"""HU-177: la línea del log de un endpoint de cálculo trae la ruta, el estado, la duración y las versiones del dataset y
de las reglas, y nunca el cuerpo ni los parámetros de la consulta (R4, R9; contrato, «Logs de la terminal»)."""

import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from backend.api import calculations
from backend.api.main import app
from backend.config.versions import rules_version
from backend.dataset import get_dataset, load
from common.signal_sources import SignalSource, SignalSources

SOON = (date.today() + timedelta(days=40)).isoformat()
WATER_CROP = {"crop_id": "arveja", "area_pct": 100, "sowing_date": SOON}
CASES = [
    ("post", "/api/v1/diagnostics", "/api/v1/diagnostics", {"municipality_id": "15646", "crop_id": "papa", "sowing_date": SOON}),
    (
        "post",
        "/api/v1/rotations",
        "/api/v1/rotations",
        {"municipality_id": "15646", "sowing_date": SOON, "previous_crop_ids": ["papa"], "current_crop_ids": ["papa", "arveja"]},
    ),
    ("post", "/api/v1/water-plans", "/api/v1/water-plans", {"municipality_id": "15646", "total_area_ha": 1.26, "crops": [WATER_CROP]}),
    ("get", "/api/v1/changes?municipality_id=15646&crop_id=papa", "/api/v1/changes", None),
    ("get", f"/api/v1/trends?municipality_id=15646&crop_id=papa&sowing_date={SOON}", "/api/v1/trends", None),
]


def written(logs: list[dict]) -> str:
    """Todo lo que se escribió, sin el `request_id` (un UUID al azar podría traer por casualidad unos dígitos)."""
    return json.dumps([{k: v for k, v in entry.items() if k != "request_id"} for entry in logs], default=str)


def request_line(logs: list[dict]) -> dict:
    lines = [entry for entry in logs if entry["event"] == "request"]
    assert len(lines) == 1, logs
    return lines[0]


@pytest.mark.parametrize(("method", "path", "route", "body"), CASES)
def test_el_log_de_un_calculo_trae_las_versiones_y_nunca_la_consulta(dataset, method, path, route, body):
    with capture_logs() as logs:
        response = getattr(TestClient(app), method)(path, **({"json": body} if body else {}))
    line = request_line(logs)
    published = get_dataset()
    assert (line["route"], line["status"], line["dataset"], line["rules"]) == (
        route, response.status_code, published.version, rules_version(published.rules_version)
    )  # fmt: skip
    assert isinstance(line["duration_ms"], int)
    # Ni el municipio, ni el cultivo, ni la fecha, ni el área de la consulta (R9): ninguna parte de lo que llegó.
    text = written(logs)
    for value in ("15646", "papa", "arveja", SOON, "1.26"):
        assert value not in text, value


def test_el_diagnostico_que_si_responde_tambien_dice_sus_versiones(dataset_con_clima):
    # Un cultivo que no se da en la zona: el diagnóstico responde 200 con la regla 0 (HU-191).
    body = {"municipality_id": "25307", "crop_id": "papa", "sowing_date": SOON}
    with capture_logs() as logs:
        response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200
    line = request_line(logs)
    assert (line["dataset"], line["rules"]) == (response.json()["versions"]["dataset"], response.json()["versions"]["rules"])
    assert "25307" not in written(logs)


def test_sin_dataset_el_log_no_inventa_versiones():
    with capture_logs() as logs:
        response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "15646", "crop_id": "papa", "sowing_date": SOON})
    assert response.status_code == 503
    line = request_line(logs)
    assert "dataset" not in line and "rules" not in line


def test_una_ruta_que_no_es_de_calculo_no_lleva_versiones(dataset):
    with capture_logs() as logs:
        TestClient(app).get("/api/v1/catalogs/crops")
    assert "dataset" not in request_line(logs)


def test_cambios_no_apto_registra_versiones_y_detalle_sin_la_consulta(monkeypatch):
    """El 200 real recorre calc_dataset; las cifras de esta prueba son de ejemplo."""
    dataset = load(Path(__file__).resolve().parents[1] / "data" / "examples")
    municipalities = dict(dataset.municipalities)
    municipalities["15001"] = replace(municipalities["15001"], tmean_annual_c=100.0)
    dataset = replace(dataset, municipalities=municipalities)
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
    monkeypatch.setattr(calculations, "require_dataset", lambda: dataset)
    monkeypatch.setattr(calculations, "get_signal_sources", lambda: configuration)

    with capture_logs() as logs:
        response = TestClient(app).get("/api/v1/changes", params={"municipality_id": "15001", "crop_id": "papa"})

    assert response.status_code == 200, response.text
    line = request_line(logs)
    assert line["route"] == "/api/v1/changes"
    assert line["status"] == 200
    assert line["dataset"] == response.json()["versions"]["dataset"]
    assert line["rules"] == response.json()["versions"]["rules"]
    assert line["detail"] == "Qué cambió: el cultivo no es apto en su municipio; clima de dos periodos comparado"
    text = written(logs)
    assert "15001" not in text and "papa" not in text
    assert "municipality_id" not in text and "crop_id" not in text
