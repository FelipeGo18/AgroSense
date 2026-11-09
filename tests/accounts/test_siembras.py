"""Siembras y cosechas de un lote: dividir y juntar terreno (HU-165; specs/02-contratos.md)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.accounts.farm_models import Season
from backend.accounts.trace_models import ActivityEvent

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
TODAY = datetime.now(UTC).date()


def ago(days: int) -> str:
    return (TODAY - timedelta(days=days)).isoformat()


@pytest.fixture
def lot(client, dataset):
    client.post("/api/v1/auth/register", json=ROSA)
    return client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": "15646", "area_ha": 2}).json()["lot_id"]


def sow(client, lot, **body):
    return client.post(f"/api/v1/lots/{lot}/seasons", json={"crop_id": "papa", "sowing_date": ago(60), **body})


def harvest(client, season, days_ago=10):
    return client.patch(f"/api/v1/seasons/{season}", json={"harvest_date": ago(days_ago)})


def test_registrar_una_siembra_y_ver_su_etapa(client, lot, db):
    response = sow(client, lot, area_ha=1.5)
    assert response.status_code == 201
    season = response.json()
    # Papa sembrada hace 60 días: FAO-56 «Idaho» da 45 de etapa inicial, así que va en desarrollo.
    assert (season["crop_id"], season["area_ha"], season["stage"], season["days_since_sowing"]) == ("papa", 1.5, "development", 60)
    assert season["harvest_basis"] == "calendar" and season["harvest_estimate"] == (TODAY + timedelta(days=105)).isoformat()
    detail = client.get(f"/api/v1/lots/{lot}").json()
    assert [(s["crop_id"], s["stage"], s["stage_method"]) for s in detail["current_seasons"]] == [("papa", "development", "calendar")]
    assert client.get("/api/v1/lots").json()[0]["current_crop_ids"] == ["papa"]
    assert db.scalar(select(ActivityEvent.action).where(ActivityEvent.action == "season.created")) == "season.created"


def test_sin_area_ocupa_lo_libre_y_no_cabe_mas_de_lo_libre(client, lot):
    assert sow(client, lot, area_ha=1.2).status_code == 201
    rest = sow(client, lot, crop_id="arveja")
    assert rest.status_code == 201 and rest.json()["area_ha"] == 0.8
    full = sow(client, lot, crop_id="haba", area_ha=0.1)
    assert full.status_code == 422 and full.json()["error"]["code"] == "area_exceeds_free"


def test_varios_cultivos_a_la_vez_sin_pasar_del_area(client, lot):
    assert sow(client, lot, area_ha=1).status_code == 201
    too_big = sow(client, lot, crop_id="arveja", area_ha=1.5)
    assert too_big.status_code == 422 and "quedan 1,00 ha libres" in too_big.json()["error"]["message"]


def test_dividir_una_papa_cosechada_en_dos_siembras(client, lot):
    papa = sow(client, lot, area_ha=1, sowing_date=ago(200)).json()["season_id"]
    assert harvest(client, papa, 30).status_code == 200
    for crop in ("arveja", "haba"):
        response = sow(client, lot, crop_id=crop, area_ha=0.5, sowing_date=ago(20), follows_season_ids=[papa])
        assert response.status_code == 201 and response.json()["follows_season_ids"] == [papa]


def test_juntar_dos_cosechadas_en_una_siembra(client, lot):
    a = sow(client, lot, crop_id="arveja", area_ha=1, sowing_date=ago(150)).json()["season_id"]
    b = sow(client, lot, crop_id="haba", area_ha=1, sowing_date=ago(150)).json()["season_id"]
    harvest(client, a, 20)
    harvest(client, b, 15)
    joined = sow(client, lot, crop_id="maiz", area_ha=2, sowing_date=ago(5), follows_season_ids=[a, b])
    assert joined.status_code == 201 and sorted(joined.json()["follows_season_ids"]) == sorted([a, b])


@pytest.mark.parametrize("case", ["en_curso", "cosechada_despues", "otro_lote", "repetida"])
def test_lo_de_antes_tiene_que_ser_una_cosecha_valida_del_mismo_lote(client, lot, case):
    previous = sow(client, lot, area_ha=1, sowing_date=ago(150)).json()["season_id"]
    if case == "cosechada_despues":
        harvest(client, previous, 5)
    elif case != "en_curso":
        harvest(client, previous, 30)
    follows = [previous]
    if case == "otro_lote":
        other = client.post("/api/v1/lots", json={"name": "El Bajo", "municipality_id": "15646", "area_ha": 1}).json()["lot_id"]
        response = sow(client, other, crop_id="arveja", sowing_date=ago(10), follows_season_ids=follows)
    else:
        if case == "repetida":
            follows = [previous, previous]
        response = sow(client, lot, crop_id="arveja", area_ha=0.5, sowing_date=ago(10), follows_season_ids=follows)
    assert response.status_code == 422, case


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"crop_id": "fresa"}, "catálogo"),
        ({"sowing_date": (TODAY + timedelta(days=3)).isoformat()}, "posterior a hoy"),
        ({"area_ha": 0}, "Hay datos"),
        ({"diagnosis_action": "regar"}, "diagnóstico"),
        ({"diagnosis_light": "azul"}, "diagnóstico"),
    ],
)
def test_datos_invalidos_responden_422(client, lot, body, message):
    response = sow(client, lot, **body)
    assert response.status_code == 422 and message in response.json()["error"]["message"]


def test_el_diagnostico_visto_al_sembrar_se_guarda(client, lot):
    seen = {
        "diagnosis_light": "yellow",
        "diagnosis_light_default": "green",
        "diagnosis_action": "other_window",
        "diagnosis_weights": {"water": 5, "frost": 3, "heat": 3, "soil": 2, "supply": 0, "market": 2},
        "diagnosis_irrigated": False,
        "dataset_version": "2026.10.3",
        "rules_version": "0.1.0",
    }
    season = sow(client, lot, **seen).json()
    assert {k: season[k] for k in seen} == seen


def test_registrar_la_cosecha_deja_libre_el_terreno(client, lot):
    papa = sow(client, lot, area_ha=2, sowing_date=ago(170)).json()["season_id"]
    assert sow(client, lot, crop_id="arveja", area_ha=0.5).status_code == 422
    done = harvest(client, papa, 1)
    assert done.status_code == 200 and done.json()["harvest_date"] == ago(1) and done.json()["stage"] is None
    assert client.get(f"/api/v1/lots/{lot}").json()["current_seasons"] == []
    assert sow(client, lot, crop_id="arveja", sowing_date=ago(0), follows_season_ids=[papa]).status_code == 201


@pytest.mark.parametrize(("days_ago", "message"), [(70, "antes de la siembra"), (-2, "posterior a hoy")])
def test_la_cosecha_va_entre_la_siembra_y_hoy(client, lot, days_ago, message):
    papa = sow(client, lot, sowing_date=ago(60)).json()["season_id"]
    response = harvest(client, papa, days_ago)
    assert response.status_code == 422 and message in response.json()["error"]["message"]


def test_no_se_deshace_una_cosecha_que_ya_tiene_siembra_despues(client, lot):
    papa = sow(client, lot, area_ha=1, sowing_date=ago(150)).json()["season_id"]
    harvest(client, papa, 30)
    sow(client, lot, crop_id="arveja", area_ha=1, sowing_date=ago(20), follows_season_ids=[papa])
    assert client.patch(f"/api/v1/seasons/{papa}", json={"harvest_date": None}).status_code == 422
    # Tampoco se mueve la cosecha a después de la siembra que vino luego.
    assert client.patch(f"/api/v1/seasons/{papa}", json={"harvest_date": ago(10)}).status_code == 422


def test_corregir_la_siembra_revisa_que_quepa(client, lot):
    a = sow(client, lot, area_ha=1).json()["season_id"]
    sow(client, lot, crop_id="arveja", area_ha=1)
    assert client.patch(f"/api/v1/seasons/{a}", json={"area_ha": 1.5}).status_code == 422
    fixed = client.patch(f"/api/v1/seasons/{a}", json={"crop_id": "haba", "area_ha": 0.8})
    assert fixed.status_code == 200 and (fixed.json()["crop_id"], fixed.json()["area_ha"]) == ("haba", 0.8)


def test_borrar_una_siembra_la_marca_y_deja_de_verse(client, lot, db):
    papa = sow(client, lot, area_ha=1).json()["season_id"]
    assert client.delete(f"/api/v1/seasons/{papa}").status_code == 204
    assert client.get(f"/api/v1/lots/{lot}/seasons").json() == []
    db.expire_all()
    assert db.scalar(select(Season.deleted_at).where(Season.crop_id == "papa")) is not None
    assert client.patch(f"/api/v1/seasons/{papa}", json={"harvest_date": ago(1)}).status_code == 404


def test_el_historial_va_de_lo_mas_reciente_a_lo_mas_antiguo(client, lot):
    old = sow(client, lot, area_ha=1, sowing_date=ago(300)).json()["season_id"]
    harvest(client, old, 100)
    sow(client, lot, crop_id="arveja", area_ha=1, sowing_date=ago(50), follows_season_ids=[old])
    history = client.get(f"/api/v1/lots/{lot}/seasons").json()
    assert [s["crop_id"] for s in history] == ["arveja", "papa"]
    assert history[1]["stage"] is None and history[0]["stage"] is not None


def test_una_siembra_ajena_responde_404(client, lot):
    papa = sow(client, lot, area_ha=1).json()["season_id"]
    client.cookies.clear()
    client.post("/api/v1/auth/register", json={**ROSA, "username": "otra.persona"})
    assert client.patch(f"/api/v1/seasons/{papa}", json={"harvest_date": ago(1)}).status_code == 404
    assert client.delete(f"/api/v1/seasons/{papa}").status_code == 404
    assert client.get(f"/api/v1/lots/{lot}/seasons").status_code == 404
