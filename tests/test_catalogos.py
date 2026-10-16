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
    # Las reglas agronómicas todavía no existen: no se inventa una versión.
    assert body["rules_version"] is None
    assert [source["source_id"] for source in body["sources"]] == ["dane_divipola", "dane_mgn_2025"]


def test_el_limite_del_municipio_en_geojson(dataset):
    body = TestClient(app).get("/api/v1/catalogs/municipalities/15646/boundary").json()
    assert body["type"] == "Feature" and body["geometry"]["type"] == "Polygon"
    assert body["properties"] == {"municipality_id": "15646", "name": "Samacá", "source_id": "dane_mgn_2025"}


def test_el_limite_de_un_municipio_fuera_de_la_region_responde_404(dataset):
    assert TestClient(app).get("/api/v1/catalogs/municipalities/05001/boundary").status_code == 404
