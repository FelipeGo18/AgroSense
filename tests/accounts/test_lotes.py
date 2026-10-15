"""Lotes del agricultor, entrega 1: sin dibujar (HU-164, HU-169; specs/02-contratos.md)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.accounts.farm_models import Lot, Season
from backend.accounts.trace_models import ActivityEvent

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
EL_ALTO = {"name": "El Alto", "municipality_id": "15646", "area_ha": 2.5, "irrigated": False}


@pytest.fixture
def rosa(client, dataset):
    client.post("/api/v1/auth/register", json=ROSA)
    return client


def create(client, **changes):
    return client.post("/api/v1/lots", json={**EL_ALTO, **changes})


def test_crear_un_lote_sin_dibujar(rosa, db):
    response = create(rosa, name="  El Alto ")
    assert response.status_code == 201
    lot = response.json()
    assert (lot["name"], lot["municipality_id"], lot["area_ha"], lot["irrigated"], lot["geometry"]) == (
        "El Alto",
        "15646",
        2.5,
        False,
        None,
    )
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "lot.created"))
    assert (event.object_type, str(event.object_id)) == ("lot", lot["lot_id"])


def test_el_riego_se_puede_dejar_sin_decir(rosa):
    lot = rosa.post("/api/v1/lots", json={"name": "La Esperanza", "municipality_id": "15407", "area_ha": 1}).json()
    assert lot["irrigated"] is None


@pytest.mark.parametrize(
    "bad",
    [{"area_ha": 0}, {"area_ha": -1}, {"area_ha": 100_001}, {"name": "  "}, {"name": "x" * 61}, {"user_id": str(uuid.uuid4())}],
)
def test_datos_invalidos_responden_422(rosa, bad):
    assert create(rosa, **bad).status_code == 422


def test_un_municipio_que_no_esta_en_la_region_responde_422(rosa):
    # Medellín existe en DIVIPOLA, pero no es de la región publicada.
    response = create(rosa, municipality_id="05001")
    assert response.status_code == 422 and "región" in response.json()["error"]["message"]


def test_dibujar_el_lote_todavia_no_se_puede_y_lo_dice(rosa):
    polygon = {"type": "Polygon", "coordinates": [[[-73.49, 5.49], [-73.48, 5.49], [-73.48, 5.50], [-73.49, 5.49]]]}
    response = create(rosa, geometry=polygon)
    assert response.status_code == 422 and response.json()["error"]["code"] == "geometry_not_available"


def test_la_lista_trae_solo_los_lotes_propios_y_sin_borrar(rosa, client):
    alto = create(rosa).json()
    create(rosa, name="La Esperanza")
    rosa.delete(f"/api/v1/lots/{alto['lot_id']}")
    client.cookies.clear()
    client.post("/api/v1/auth/register", json={**ROSA, "username": "otra.persona"})
    create(client, name="Lo de otra persona")
    assert [lot["name"] for lot in client.get("/api/v1/lots").json()] == ["Lo de otra persona"]


def test_un_lote_ajeno_responde_404_como_uno_que_no_existe(rosa, client):
    alto = create(rosa).json()
    client.cookies.clear()
    client.post("/api/v1/auth/register", json={**ROSA, "username": "otra.persona"})
    for method in ("GET", "PATCH", "DELETE"):
        ajeno = client.request(method, f"/api/v1/lots/{alto['lot_id']}", json={"name": "Mío"} if method == "PATCH" else None)
        assert ajeno.status_code == 404, method
    assert client.get(f"/api/v1/lots/{uuid.uuid4()}").status_code == 404


def test_sin_sesion_los_lotes_responden_401(client, dataset):
    assert client.get("/api/v1/lots").status_code == 401
    assert create(client).status_code == 401


def test_el_detalle_trae_las_temporadas_en_curso_y_el_suelo_nulo(rosa, db):
    lot = create(rosa).json()
    lot_id = uuid.UUID(lot["lot_id"])
    sown = date.today() - timedelta(days=30)
    db.add_all(
        [
            Season(lot_id=lot_id, crop_id="papa", area_ha=Decimal("1.5"), sowing_date=sown),
            Season(lot_id=lot_id, crop_id="arveja", area_ha=Decimal("0.5"), sowing_date=sown),
            Season(lot_id=lot_id, crop_id="haba", area_ha=Decimal("0.5"), sowing_date=sown - timedelta(days=200), harvest_date=sown),
        ]
    )
    db.commit()
    detail = rosa.get(f"/api/v1/lots/{lot_id}").json()
    # Sin el suelo publicado no se inventa (R1).
    assert detail["soil"] is None
    assert [(s["crop_id"], s["area_ha"], s["days_since_sowing"]) for s in detail["current_seasons"]] == [
        ("papa", 1.5, 30),
        ("arveja", 0.5, 30),
    ]
    # Sin las etapas del cultivo con fuente, la etapa es nula.
    assert detail["current_seasons"][0]["stage"] is None
    assert rosa.get("/api/v1/lots").json()[0]["current_crop_ids"] == ["papa", "arveja"]


def test_editar_el_nombre_el_area_y_el_riego(rosa, db):
    lot = create(rosa).json()
    response = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"name": "El Alto de abajo", "area_ha": 3.25, "irrigated": None})
    assert response.status_code == 200
    assert (response.json()["name"], response.json()["area_ha"], response.json()["irrigated"]) == ("El Alto de abajo", 3.25, None)
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "lot.updated"))
    assert event.details == {"fields": ["area_ha", "irrigated", "name"]}


def test_el_lote_no_puede_quedar_mas_chico_que_lo_sembrado(rosa, db):
    lot = create(rosa).json()
    db.add(Season(lot_id=uuid.UUID(lot["lot_id"]), crop_id="papa", area_ha=Decimal("2"), sowing_date=date.today()))
    db.commit()
    response = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"area_ha": 1.5})
    assert response.status_code == 422 and response.json()["error"]["code"] == "area_below_seasons"
    assert "2,00 ha" in response.json()["error"]["message"]
    assert rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"area_ha": 2}).status_code == 200


def test_el_nombre_y_el_area_no_se_pueden_vaciar(rosa):
    lot = create(rosa).json()
    for empty in ({"name": None}, {"area_ha": None}, {"municipality_id": None}):
        assert rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json=empty).status_code == 422, empty


def test_borrar_el_lote_lo_marca_con_sus_temporadas(rosa, db):
    lot = create(rosa).json()
    lot_id = uuid.UUID(lot["lot_id"])
    db.add(Season(lot_id=lot_id, crop_id="papa", area_ha=Decimal("1"), sowing_date=date.today()))
    db.commit()
    assert rosa.delete(f"/api/v1/lots/{lot_id}").status_code == 204
    db.expire_all()
    stored = db.get(Lot, lot_id)
    season = db.scalar(select(Season).where(Season.lot_id == lot_id))
    # Se puede restaurar después (HU-204): se marca, no se borra, y con la misma hora.
    assert stored.deleted_at is not None and season.deleted_at == stored.deleted_at
    assert rosa.get(f"/api/v1/lots/{lot_id}").status_code == 404


def test_sin_dataset_no_se_puede_crear_un_lote(client):
    client.post("/api/v1/auth/register", json=ROSA)
    response = create(client)
    assert response.status_code == 503 and response.json()["error"]["code"] == "dataset_unavailable"
