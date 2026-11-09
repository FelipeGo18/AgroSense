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


# ---------- El lote dibujado (entrega 2) ----------

# Samacá en el dataset de ejemplo: un cuadrado de 0,1° alrededor de (-73.4856, 5.4925).
LON, LAT = -73.4856, 5.4925
# Unos 100 m de lado a esta latitud: 1 ha.
SIDE_LAT = 100 / 110_574
SIDE_LON = 100 / (111_320 * 0.99541)


def square(lon=LON, lat=LAT, dlon=SIDE_LON, dlat=SIDE_LAT):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + dlon, lat], [lon + dlon, lat + dlat], [lon, lat + dlat], [lon, lat]]]}


def test_un_lote_dibujado_guarda_su_contorno_y_la_api_calcula_el_area(rosa, db):
    # El área que mande la web se ignora: la del lote es la de su dibujo.
    response = create(rosa, geometry=square(), area_ha=99)
    assert response.status_code == 201
    lot = response.json()
    assert lot["area_ha"] == pytest.approx(1.0, rel=0.01)
    assert lot["geometry"]["type"] == "Polygon" and len(lot["geometry"]["coordinates"][0]) == 5
    assert db.get(Lot, uuid.UUID(lot["lot_id"])).geometry == lot["geometry"]


def test_sin_dibujo_ni_area_no_se_crea(rosa):
    response = rosa.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": "15646"})
    assert response.status_code == 422 and "Dibuje" in response.json()["error"]["message"]


def test_un_lote_que_se_sale_de_su_municipio_responde_422_y_dice_cual(rosa):
    # Villa de Leyva queda a unos 15 km: fuera del límite de Samacá.
    response = create(rosa, geometry=square(lon=-73.5249, lat=5.6339))
    error = response.json()["error"]
    assert response.status_code == 422 and error["code"] == "geometry_outside_municipality"
    assert error["message"].startswith("Su lote se sale de Samacá")


@pytest.mark.parametrize(
    ("geometry", "why"),
    [
        # Un moño: las líneas se cruzan.
        (
            {
                "type": "Polygon",
                "coordinates": [[[LON, LAT], [LON + 0.001, LAT + 0.001], [LON + 0.001, LAT], [LON, LAT + 0.001], [LON, LAT]]],
            },
            "cruzan",
        ),
        ({"type": "Polygon", "coordinates": [square()["coordinates"][0], square(dlon=0.0001, dlat=0.0001)["coordinates"][0]]}, "huecos"),
        ({"type": "Polygon", "coordinates": [[[LON, LAT], [LON + 0.001, LAT], [LON, LAT]]]}, "puntos"),
        ({"type": "Point", "coordinates": [LON, LAT]}, "polígono"),
        ({"type": "Polygon", "coordinates": [[[LON, LAT], ["x", LAT], [LON, LAT + 0.001], [LON, LAT]]]}, "mal formado"),
    ],
)
def test_un_contorno_que_no_sirve_responde_422_y_dice_por_que(rosa, geometry, why):
    response = create(rosa, geometry=geometry)
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_geometry"
    assert why in response.json()["error"]["message"]


def test_un_lote_sin_dibujar_se_puede_dibujar_despues(rosa, db):
    lot = create(rosa, area_ha=7).json()
    response = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"geometry": square()})
    assert response.status_code == 200
    assert response.json()["area_ha"] == pytest.approx(1.0, rel=0.01)
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "lot.updated"))
    # Solo los nombres de los campos, nunca el polígono (HU-178).
    assert event.details == {"fields": ["area_ha", "geometry"]}


def test_un_lote_dibujado_tiene_el_area_de_su_dibujo_y_el_dibujo_no_se_quita(rosa):
    lot = create(rosa, geometry=square()).json()
    # Mandar un área no la cambia.
    assert rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"area_ha": 50}).json()["area_ha"] == lot["area_ha"]
    assert rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"geometry": None}).status_code == 422
    bigger = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"geometry": square(dlon=2 * SIDE_LON)})
    assert bigger.json()["area_ha"] == pytest.approx(2.0, rel=0.01)


def test_cambiar_de_municipio_un_lote_dibujado_valida_el_dibujo_en_el_nuevo(rosa):
    lot = create(rosa, geometry=square()).json()
    response = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"municipality_id": "15407"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "geometry_outside_municipality"


def test_el_contorno_dibujado_no_puede_quedar_mas_chico_que_lo_sembrado(rosa, db):
    lot = create(rosa, geometry=square(dlon=3 * SIDE_LON)).json()
    db.add(Season(lot_id=uuid.UUID(lot["lot_id"]), crop_id="papa", area_ha=Decimal("2"), sowing_date=date.today()))
    db.commit()
    response = rosa.patch(f"/api/v1/lots/{lot['lot_id']}", json={"geometry": square()})
    assert response.status_code == 422 and response.json()["error"]["code"] == "area_below_seasons"


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
    # Con las etapas del catálogo (FAO-56 «Idaho»: 45 días de etapa inicial), la papa del día 30 va en la inicial.
    papa = detail["current_seasons"][0]
    assert (papa["stage"], papa["stage_method"], papa["harvest_basis"]) == ("initial", "calendar", "calendar")
    assert papa["harvest_estimate"] == (sown + timedelta(days=165)).isoformat()
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


def test_sin_dataset_el_lote_y_su_historial_se_leen_igual_con_la_etapa_nula(rosa, db, monkeypatch, tmp_path):
    """Los GET solo leen lo guardado: sin datos publicados no fallan; la etapa de hoy va nula (R1), igual en los dos."""
    from backend.config.settings import get_settings

    lot = create(rosa).json()
    sown = date.today() - timedelta(days=30)
    db.add(Season(lot_id=uuid.UUID(lot["lot_id"]), crop_id="papa", area_ha=Decimal("1"), sowing_date=sown))
    db.commit()
    with_data = rosa.get(f"/api/v1/lots/{lot['lot_id']}").json()["current_seasons"][0]
    history = rosa.get(f"/api/v1/lots/{lot['lot_id']}/seasons").json()[0]
    # Con datos, el detalle y el historial dicen lo mismo de la etapa de hoy.
    shared = set(with_data) & set(history)
    assert shared >= {"stage", "stage_progress_pct", "days_since_sowing", "harvest_estimate", "harvest_due"}
    assert {k: history[k] for k in shared} == {k: with_data[k] for k in shared}

    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(tmp_path / "no-hay"))
    get_settings.cache_clear()
    detail = rosa.get(f"/api/v1/lots/{lot['lot_id']}")
    history = rosa.get(f"/api/v1/lots/{lot['lot_id']}/seasons")
    assert detail.status_code == 200 and history.status_code == 200
    for season in (detail.json()["current_seasons"][0], history.json()[0]):
        assert (season["stage"], season["harvest_estimate"], season["harvest_basis"], season["days_since_sowing"]) == (None, None, None, 30)
