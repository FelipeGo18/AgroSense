"""`GET /catalogs/municipalities` y `/version` leen el dataset publicado; sin él no inventan nada (HU-078, HU-122)."""

from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from backend.api.main import app


def test_los_municipios_de_la_region_por_departamento_y_nombre(dataset):
    response = TestClient(app).get("/api/v1/catalogs/municipalities")
    assert response.status_code == 200
    assert response.json() == [
        {"municipality_id": "15646", "name": "Samacá", "department": "Boyacá", "lat": 5.4925, "lon": -73.4856},
        {"municipality_id": "15407", "name": "Villa de Leyva", "department": "Boyacá", "lat": 5.6339, "lon": -73.5249},
        {"municipality_id": "25899", "name": "Zipaquirá", "department": "Cundinamarca", "lat": 5.0221, "lon": -74.0048},
    ]


def test_sin_dataset_el_catalogo_responde_503_y_el_log_dice_por_que():
    with capture_logs() as logs:
        response = TestClient(app).get("/api/v1/catalogs/municipalities")
    assert response.status_code == 503 and response.json()["error"]["code"] == "dataset_unavailable"
    reason = next(entry for entry in logs if entry["event"] == "dataset_unavailable")
    assert "manifest.json" in reason["detail"]


def test_version_dice_el_dataset_la_region_y_sus_fuentes(dataset):
    body = TestClient(app).get("/api/v1/version").json()
    assert body["dataset_version"] == "0.0.0-pruebas"
    assert body["region"] == "Región de ejemplo de las pruebas"
    assert body["created_at"] is not None
    # La versión del catálogo agronómico (catalog/crops.yaml).
    assert body["rules_version"] == "0.1.0"
    assert {"dane_divipola", "dane_mgn_2025", "fao_ecocrop", "fao_56", "upra_papa_diacol"} <= {s["source_id"] for s in body["sources"]}


def test_el_limite_del_municipio_en_geojson(dataset):
    body = TestClient(app).get("/api/v1/catalogs/municipalities/15646/boundary").json()
    assert body["type"] == "Feature" and body["geometry"]["type"] == "Polygon"
    assert body["properties"] == {"municipality_id": "15646", "name": "Samacá", "source_id": "dane_mgn_2025"}


def test_el_limite_de_un_municipio_fuera_de_la_region_responde_404(dataset):
    assert TestClient(app).get("/api/v1/catalogs/municipalities/05001/boundary").status_code == 404


def test_los_cultivos_del_catalogo(dataset):
    body = TestClient(app).get("/api/v1/catalogs/crops").json()
    assert [crop["crop_id"] for crop in body] == ["arveja", "avena_vicia", "cebolla_bulbo", "descanso", "haba", "maiz", "papa", "zanahoria"]
    papa = next(crop for crop in body if crop["crop_id"] == "papa")
    assert papa == {"crop_id": "papa", "name_es": "Papa", "kind": "crop", "archetype": "tuber", "family": "Solanaceae", "cycle_months": 5.4}


def test_sin_dataset_los_cultivos_responden_503():
    assert TestClient(app).get("/api/v1/catalogs/crops").status_code == 503
