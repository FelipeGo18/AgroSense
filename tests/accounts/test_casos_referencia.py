"""Casos de referencia de las cuentas (HU-121, «Casos de las cuentas»): dividir, juntar y área de un lote de 1 ha.

Los casos 5 (`follows_season_ids` inválido) ya los prueba `test_siembras.py` con los mismos números y código 422.
Lo que depende del progreso (HU-167) es P1: va con `xfail(strict=True)`. Restaurar el historial (HU-204) ya está.
"""

from datetime import timedelta

import pytest

from common.region import region_today

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
TODAY = region_today()


def ago(days: int) -> str:
    return (TODAY - timedelta(days=days)).isoformat()


@pytest.fixture
def lot(client, dataset):
    """Un lote de 1 ha, el de los casos de referencia."""
    client.post("/api/v1/auth/register", json=ROSA)
    return client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": "15646", "area_ha": 1}).json()["lot_id"]


def sow(client, lot, **body):
    return client.post(f"/api/v1/lots/{lot}/seasons", json={"crop_id": "papa", "sowing_date": ago(60), **body})


def harvested(client, lot, area, crop="papa", sowed=200, harvest=30):
    season = sow(client, lot, crop_id=crop, area_ha=area, sowing_date=ago(sowed)).json()["season_id"]
    assert client.patch(f"/api/v1/seasons/{season}", json={"harvest_date": ago(harvest)}).status_code == 200
    return season


def progress(client, lot):
    return client.get(f"/api/v1/lots/{lot}/progress")


def test_dividir_1_ha_en_dos_sucesoras_de_media_ha(client, lot):
    papa = harvested(client, lot, 1)
    for crop in ("arveja", "haba"):
        response = sow(client, lot, crop_id=crop, area_ha=0.5, sowing_date=ago(20), follows_season_ids=[papa])
        assert response.status_code == 201 and response.json()["follows_season_ids"] == [papa]


def test_juntar_dos_de_media_ha_en_una_de_1_ha(client, lot):
    a = harvested(client, lot, 0.5, "arveja", 150, 20)
    b = harvested(client, lot, 0.5, "haba", 150, 15)
    joined = sow(client, lot, crop_id="maiz", area_ha=1, sowing_date=ago(5), follows_season_ids=[a, b])
    assert joined.status_code == 201 and sorted(joined.json()["follows_season_ids"]) == sorted([a, b])


def test_sucesoras_que_suman_1_2_ha_en_un_lote_de_1_ha_responden_422(client, lot):
    papa = harvested(client, lot, 1)
    assert sow(client, lot, crop_id="arveja", area_ha=0.6, sowing_date=ago(20), follows_season_ids=[papa]).status_code == 201
    over = sow(client, lot, crop_id="haba", area_ha=0.6, sowing_date=ago(20), follows_season_ids=[papa])
    assert over.status_code == 422 and over.json()["error"]["code"] == "area_exceeds_free"


def test_terreno_anterior_mas_terreno_libre(client, dataset):
    # El área libre es la del lote menos las temporadas en curso (`_sown` en backend/api/seasons.py): una cosechada ya
    # no ocupa nada. Para que la prueba dependa de «anterior más libre» (revisión de Haider, PR #86, punto 9), otra
    # siembra en curso ocupa parte del lote. Lote de 2 ha: 0,5 ha en curso y la papa de 1 ha cosechada dejan 1,5 ha
    # libres. Se prueba el límite por los dos lados: 1,5 ha cabe y 1,6 ha no.
    client.post("/api/v1/auth/register", json=ROSA)
    big = client.post("/api/v1/lots", json={"name": "El Bajo", "municipality_id": "15646", "area_ha": 2}).json()["lot_id"]
    assert sow(client, big, crop_id="haba", area_ha=0.5, sowing_date=ago(30)).status_code == 201
    papa = harvested(client, big, 1)
    over = sow(client, big, crop_id="arveja", area_ha=1.6, sowing_date=ago(20), follows_season_ids=[papa])
    assert over.status_code == 422 and over.json()["error"]["code"] == "area_exceeds_free"
    fits = sow(client, big, crop_id="arveja", area_ha=1.5, sowing_date=ago(20), follows_season_ids=[papa])
    assert fits.status_code == 201 and fits.json()["area_ha"] == 1.5


@pytest.mark.xfail(strict=True, reason="espera HU-167 (P1)")
def test_dividir_da_dos_relaciones_en_el_progreso(client, lot):
    papa = harvested(client, lot, 1)
    sons = []
    for crop in ("arveja", "haba"):
        son = sow(client, lot, crop_id=crop, area_ha=0.5, sowing_date=ago(20), follows_season_ids=[papa])
        sons.append(son.json()["season_id"])
    response = progress(client, lot)
    assert response.status_code == 200
    assert sorted((r["from_season_id"], r["to_season_id"]) for r in response.json()["rotations"]) == sorted((papa, s) for s in sons)


@pytest.mark.xfail(strict=True, reason="espera HU-167 (P1)")
def test_juntar_da_dos_relaciones_hacia_la_misma_en_el_progreso(client, lot):
    a = harvested(client, lot, 0.5, "arveja", 150, 20)
    b = harvested(client, lot, 0.5, "haba", 150, 15)
    joined = sow(client, lot, crop_id="maiz", area_ha=1, sowing_date=ago(5), follows_season_ids=[a, b]).json()["season_id"]
    response = progress(client, lot)
    assert response.status_code == 200
    assert sorted((r["from_season_id"], r["to_season_id"]) for r in response.json()["rotations"]) == sorted([(a, joined), (b, joined)])


def test_una_temporada_borrada_aparece_con_restorable_until_y_vuelve(client, lot):
    season = sow(client, lot, area_ha=0.5).json()["season_id"]
    # Borrar responde exactamente 204 (backend/api/seasons.py).
    assert client.delete(f"/api/v1/seasons/{season}").status_code == 204
    history = {s["season_id"]: s for s in client.get(f"/api/v1/lots/{lot}/seasons").json()}
    assert history[season]["deleted_at"] is not None and history[season]["restorable_until"] is not None
    # El contrato no dice qué responde `restore`: se comprueba volviendo a leer el historial, no su cuerpo.
    assert client.post(f"/api/v1/seasons/{season}/restore").status_code < 300
    history = {s["season_id"]: s for s in client.get(f"/api/v1/lots/{lot}/seasons").json()}
    assert history[season]["deleted_at"] is None
