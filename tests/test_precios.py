"""`GET /market/prices` y `/market/prices/{product_id}` leen los precios publicados de SIPSA (HU-221).

Es lo que pasó en la central: nada de pronóstico. Sin precios publicados, no se inventan (R1, R5).
"""

from fastapi.testclient import TestClient

from backend.api.main import app


def test_el_ultimo_precio_de_cada_producto_en_corabastos(market_dataset):
    response = TestClient(app).get("/api/v1/market/prices")
    assert response.status_code == 200
    body = response.json()
    assert body["market"] == {"market_id": "1", "name": "Corabastos (Bogotá)"}
    assert body["markets"] == [
        {"market_id": "1", "name": "Corabastos (Bogotá)"},
        {"market_id": "9", "name": "Tunja (Complejo de Servicios del Sur)"},
    ]
    assert body["date"] == "2026-10-19" and body["source_id"] == "dane_sipsa"
    # Por grupo (tubérculos, verduras y al final frutas) y por nombre.
    assert [p["product_id"] for p in body["products"]] == ["papa-criolla", "papa-negra", "zanahoria", "aguacate"]


def test_el_cambio_se_mide_contra_el_precio_de_hace_una_semana(market_dataset):
    products = {p["product_id"]: p for p in TestClient(app).get("/api/v1/market/prices").json()["products"]}
    papa = products["papa-negra"]
    assert papa["latest"] == {"date": "2026-10-19", "min_cop_kg": 2800, "avg_cop_kg": 2925, "max_cop_kg": 3000}
    assert papa["week_ago"]["date"] == "2026-10-12" and papa["change_pct"] == 6.4
    assert papa["several_varieties"] is True
    # Sin un precio de hace una semana no hay con qué comparar: nulo, no cero (R1).
    assert products["papa-criolla"]["week_ago"] is None and products["papa-criolla"]["change_pct"] is None
    assert products["papa-criolla"]["latest"]["min_cop_kg"] is None


def test_otra_central(market_dataset):
    body = TestClient(app).get("/api/v1/market/prices", params={"market_id": "9"}).json()
    assert body["market"]["name"] == "Tunja (Complejo de Servicios del Sur)"
    assert [p["product_id"] for p in body["products"]] == ["papa-negra"]


def test_una_central_que_no_esta_responde_404(market_dataset):
    response = TestClient(app).get("/api/v1/market/prices", params={"market_id": "2"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "unknown_market"


def test_la_historia_de_un_producto(market_dataset):
    body = TestClient(app).get("/api/v1/market/prices/papa-negra").json()
    assert (body["product"], body["market"]["market_id"], body["group"]) == ("Papa negra", "1", "Tubérculos, raíces y plátanos")
    assert [d["date"] for d in body["days"]] == ["2026-10-05", "2026-10-12", "2026-10-19"]
    assert body["latest"]["avg_cop_kg"] == 2925
    # Tres semanas de precios no dicen en qué meses suele subir o bajar: sin temporada, no se inventa.
    assert body["season"] is None


def test_un_producto_sin_precios_en_esa_central_responde_404(market_dataset):
    response = TestClient(app).get("/api/v1/market/prices/zanahoria", params={"market_id": "9"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "unknown_product"


def test_sin_precios_publicados_responde_503(dataset):
    response = TestClient(app).get("/api/v1/market/prices")
    assert response.status_code == 503 and response.json()["error"]["code"] == "market_unavailable"


def test_sin_dataset_responde_503():
    response = TestClient(app).get("/api/v1/market/prices")
    assert response.status_code == 503 and response.json()["error"]["code"] == "dataset_unavailable"
