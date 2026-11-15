"""Restaurar lo borrado durante 30 días y borrarlo para siempre después (HU-204, R9; specs/02-contratos.md)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from backend.accounts import maintenance
from backend.accounts.farm_models import RESTORE_WINDOW, Lot, Season
from backend.accounts.trace_models import ActivityEvent
from common.region import region_today

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
OTRA = {**ROSA, "username": "ana.tunja", "display_name": "Ana"}
TODAY = region_today()


def ago(days: int) -> str:
    return (TODAY - timedelta(days=days)).isoformat()


@pytest.fixture
def lot(client, dataset):
    """Un lote de 1 ha de Rosa."""
    client.post("/api/v1/auth/register", json=ROSA)
    return client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": "15646", "area_ha": 1}).json()["lot_id"]


def sow(client, lot, **body):
    return client.post(f"/api/v1/lots/{lot}/seasons", json={"crop_id": "papa", "sowing_date": ago(60), **body}).json()["season_id"]


def age(db, model: type[Lot] | type[Season], object_id: str, days: float) -> None:
    """Hace que un lote o una temporada parezcan borrados hace `days` días."""
    key = Lot.lot_id if model is Lot else Season.season_id
    db.execute(update(model).where(key == uuid.UUID(object_id)).values(deleted_at=datetime.now(UTC) - timedelta(days=days)))
    db.commit()


def actions(db, name):
    return db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.action == name))


# ---------- Lotes ----------


def test_la_lista_trae_los_lotes_borrados_con_hasta_cuando(client, lot):
    other = client.post("/api/v1/lots", json={"name": "La Vega", "municipality_id": "15646", "area_ha": 2}).json()["lot_id"]
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204
    lots = {item["lot_id"]: item for item in client.get("/api/v1/lots").json()}
    assert lots[other]["deleted_at"] is None and lots[other]["restorable_until"] is None
    deleted = lots[lot]
    gone = datetime.fromisoformat(deleted["deleted_at"])
    assert datetime.fromisoformat(deleted["restorable_until"]) - gone == RESTORE_WINDOW == timedelta(days=30)
    # Un lote borrado no tiene cultivos en curso, ni se abre.
    assert deleted["current_crop_ids"] == []
    assert client.get(f"/api/v1/lots/{lot}").status_code == 404


def test_restaurar_el_lote_devuelve_las_temporadas_que_se_borraron_con_el(client, db, lot):
    alone = sow(client, lot, area_ha=0.3)
    assert client.delete(f"/api/v1/seasons/{alone}").status_code == 204
    kept = sow(client, lot, area_ha=0.5)
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204

    response = client.post(f"/api/v1/lots/{lot}/restore")
    assert response.status_code == 200 and response.json()["lot_id"] == lot
    detail = client.get(f"/api/v1/lots/{lot}").json()
    assert [s["season_id"] for s in detail["current_seasons"]] == [kept]
    # La que se había borrado sola, antes que el lote, sigue borrada y se puede restaurar aparte.
    history = {s["season_id"]: s for s in client.get(f"/api/v1/lots/{lot}/seasons").json()}
    assert history[kept]["deleted_at"] is None and history[alone]["deleted_at"] is not None
    assert actions(db, "lot.restored") == 1
    assert client.get("/api/v1/lots").json()[0]["current_crop_ids"] == ["papa"]


def test_restaurar_un_lote_sin_borrar_o_de_hace_30_dias_responde_404(client, db, lot):
    assert client.post(f"/api/v1/lots/{lot}/restore").status_code == 404
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204
    age(db, Lot, lot, 30)
    assert client.post(f"/api/v1/lots/{lot}/restore").status_code == 404
    # Pasado el plazo ya no sale en la lista.
    assert client.get("/api/v1/lots").json() == []
    assert client.post(f"/api/v1/lots/{uuid.uuid4()}/restore").status_code == 404


def test_nadie_restaura_un_lote_ajeno(client, lot):
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json=OTRA)
    assert client.post(f"/api/v1/lots/{lot}/restore").status_code == 404
    assert client.get("/api/v1/lots").json() == []


def test_sin_sesion_no_se_restaura(client, lot):
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204
    client.post("/api/v1/auth/logout")
    assert client.post(f"/api/v1/lots/{lot}/restore").status_code == 401


# ---------- Temporadas ----------


def test_restaurar_una_siembra_la_devuelve_y_queda_en_la_actividad(client, db, lot):
    season = sow(client, lot, area_ha=0.5)
    assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    deleted = client.get(f"/api/v1/lots/{lot}/seasons").json()[0]
    gone = datetime.fromisoformat(deleted["deleted_at"])
    assert datetime.fromisoformat(deleted["restorable_until"]) - gone == timedelta(days=30)
    # Mientras está borrada no cuenta en el área libre ni se ve en el lote.
    assert client.get(f"/api/v1/lots/{lot}").json()["current_seasons"] == []

    response = client.post(f"/api/v1/seasons/{season}/restore")
    assert response.status_code == 200
    assert (response.json()["deleted_at"], response.json()["restorable_until"]) == (None, None)
    assert [s["season_id"] for s in client.get(f"/api/v1/lots/{lot}").json()["current_seasons"]] == [season]
    assert actions(db, "season.restored") == 1


def test_si_ya_no_cabe_restaurar_responde_422_y_sigue_borrada(client, lot):
    season = sow(client, lot, area_ha=0.6)
    assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    # Mientras estaba borrada, su terreno se ocupó con otra siembra.
    sow(client, lot, area_ha=0.7, crop_id="arveja")
    response = client.post(f"/api/v1/seasons/{season}/restore")
    assert response.status_code == 422 and response.json()["error"]["code"] == "area_exceeds_free"
    assert "0,30 ha" in response.json()["error"]["message"]
    history = {s["season_id"]: s for s in client.get(f"/api/v1/lots/{lot}/seasons").json()}
    assert history[season]["deleted_at"] is not None


def test_una_siembra_cosechada_se_restaura_aunque_el_lote_este_lleno(client, lot):
    harvested = sow(client, lot, area_ha=0.5, sowing_date=ago(150))
    assert client.patch(f"/api/v1/seasons/{harvested}", json={"harvest_date": ago(20)}).status_code == 200
    assert client.delete(f"/api/v1/seasons/{harvested}").status_code == 204
    sow(client, lot, area_ha=1, crop_id="arveja", sowing_date=ago(10))
    # Lo cosechado no ocupa terreno: no hay área que revisar.
    assert client.post(f"/api/v1/seasons/{harvested}/restore").status_code == 200


def test_si_lo_de_antes_ya_no_existe_restaurar_responde_422(client, lot):
    before = sow(client, lot, area_ha=0.5, sowing_date=ago(150))
    assert client.patch(f"/api/v1/seasons/{before}", json={"harvest_date": ago(40)}).status_code == 200
    after = sow(client, lot, area_ha=0.5, crop_id="arveja", sowing_date=ago(30), follows_season_ids=[before])
    assert client.delete(f"/api/v1/seasons/{after}").status_code == 204
    assert client.delete(f"/api/v1/seasons/{before}").status_code == 204
    response = client.post(f"/api/v1/seasons/{after}/restore")
    assert response.status_code == 422 and "mismo lote" in response.json()["error"]["message"]
    # Restaurada la anterior, ya se puede.
    assert client.post(f"/api/v1/seasons/{before}/restore").status_code == 200
    assert client.post(f"/api/v1/seasons/{after}/restore").status_code == 200


def test_restaurar_una_siembra_sin_borrar_de_hace_30_dias_o_de_un_lote_borrado_responde_404(client, db, lot):
    season = sow(client, lot, area_ha=0.5)
    assert client.post(f"/api/v1/seasons/{season}/restore").status_code == 404
    assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    age(db, Season, season, 30)
    assert client.post(f"/api/v1/seasons/{season}/restore").status_code == 404
    assert client.get(f"/api/v1/lots/{lot}/seasons").json() == []

    other = sow(client, lot, area_ha=0.5)
    assert client.delete(f"/api/v1/lots/{lot}").status_code == 204
    # Con el lote borrado, se restaura el lote, no la siembra suelta.
    assert client.post(f"/api/v1/seasons/{other}/restore").status_code == 404
    assert client.post(f"/api/v1/seasons/{uuid.uuid4()}/restore").status_code == 404


def test_nadie_restaura_una_siembra_ajena(client, lot):
    season = sow(client, lot, area_ha=0.5)
    assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json=OTRA)
    assert client.post(f"/api/v1/seasons/{season}/restore").status_code == 404


# ---------- Borrar para siempre ----------


def test_el_mantenimiento_borra_para_siempre_lo_de_hace_30_dias_o_mas(client, db, lot):
    recent = sow(client, lot, area_ha=0.2)
    old = sow(client, lot, area_ha=0.2)
    for season in (recent, old):
        assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    age(db, Season, recent, 29.9)
    age(db, Season, old, 30)
    gone_lot = client.post("/api/v1/lots", json={"name": "La Vega", "municipality_id": "15646", "area_ha": 2}).json()["lot_id"]
    sow(client, gone_lot, area_ha=1)
    assert client.delete(f"/api/v1/lots/{gone_lot}").status_code == 204
    db.execute(update(Season).where(Season.lot_id == uuid.UUID(gone_lot)).values(deleted_at=datetime.now(UTC) - timedelta(days=31)))
    age(db, Lot, gone_lot, 31)

    cleaned = maintenance.run(db)
    db.commit()
    # Las temporadas cuentan también la del lote borrado.
    assert (cleaned.lots, cleaned.seasons) == (1, 2)
    db.expire_all()
    assert db.get(Lot, uuid.UUID(gone_lot)) is None
    assert db.get(Season, uuid.UUID(old)) is None
    assert db.get(Season, uuid.UUID(recent)) is not None
    # El lote activo y lo que se puede restaurar siguen.
    assert db.get(Lot, uuid.UUID(lot)) is not None
    assert client.post(f"/api/v1/seasons/{recent}/restore").status_code == 200
    assert maintenance.run(db) == maintenance.Cleaned(sessions=0, events=0)
