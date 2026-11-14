"""La aptitud del cultivo con la altitud del lote (HU-191, primer criterio): `zone_temperature` y `/diagnostics`.

Las celdas de la rejilla y las cifras de clima son de ejemplo (R5). Samacá: 12,8 °C a 2660 m; Villa de Leyva: 6,0 °C a
2900 m; la papa se da entre 8 y 16 °C. El gradiente es el de Cenicafé: (0,0058 + 0,0059) / 2 = 0,00585 °C por metro.
"""

from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from structlog.testing import capture_logs

from backend import dataset as dataset_module
from backend.accounts.farm_models import Lot, Season
from backend.api.lot_terrain import zone_temperature
from backend.api.main import app
from common.grid import GRID_STEP_DEG, cell_id

SOON = (date.today() + timedelta(days=40)).isoformat()
SAMACA = {"municipality_id": "15646", "lat": 5.4925, "lon": -73.4856}
LEYVA = {"municipality_id": "15407", "lat": 5.6339, "lon": -73.5249}


def write_grid(folder, boxes: list[tuple[dict, float | None]]) -> None:
    """Una `grid_cells.parquet` de ejemplo con las dos columnas que lee la API: cada caja de ±0,03° alrededor de un
    municipio, con una altitud pareja (o nula)."""
    cells = {}
    for place, altitude in boxes:
        for dlat in np.arange(-0.03, 0.03, GRID_STEP_DEG):
            for dlon in np.arange(-0.03, 0.03, GRID_STEP_DEG):
                cells[cell_id(place["lat"] + dlat, place["lon"] + dlon)] = altitude
    pl.DataFrame(
        {"cell_id": list(cells), "altitude_m": list(cells.values())}, schema={"cell_id": pl.String, "altitude_m": pl.Float64}
    ).write_parquet(folder / "grid_cells.parquet")


def square(place: dict, half: float = 0.01) -> dict:
    lat, lon = place["lat"], place["lon"]
    ring = [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture
def farmer(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "rosa.samaca",
            "password": "papaya-criolla-2026",
            "display_name": "Rosa",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    return client


def create_lot(client, place: dict, geometry: dict | None = None, name: str = "El Alto") -> str:
    body = {"name": name, "municipality_id": place["municipality_id"]}
    body.update({"geometry": geometry} if geometry else {"area_ha": 1.0})
    response = client.post("/api/v1/lots", json=body)
    assert response.status_code == 201, response.json()
    return response.json()["lot_id"]


def diagnose(client, place: dict, lot_id: str | None, crop: str = "papa"):
    body = {"municipality_id": place["municipality_id"], "crop_id": crop, "sowing_date": SOON}
    if lot_id:
        body["lot_id"] = lot_id
    return client.post("/api/v1/diagnostics", json=body)


def test_lote_en_el_paramo_de_un_municipio_apto_da_no_apto_con_la_temperatura_del_lote(dataset_con_clima, farmer):
    """Samacá es apto para la papa (12,8 °C). Un lote a 3500 m queda 840 m más arriba: 12,8 - 4,914 = 7,9 °C, por debajo de 8."""
    write_grid(dataset_con_clima, [(SAMACA, 3500.0)])
    assert diagnose(farmer, SAMACA, None).status_code == 501
    response = diagnose(farmer, SAMACA, create_lot(farmer, SAMACA, square(SAMACA)))
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["suitability"] | {"reasons": None} == {
        "level": "not_suitable",
        "score": 0,
        "basis": "lot",
        "tmean_annual_c": 7.9,
        "altitude_m": 3500,
        "reasons": None,
    }
    assert body["suitability"]["reasons"] == [
        "La temperatura media anual estimada para su lote (7,9 °C, a 3500 m; corregida desde la del municipio, 12,8 °C a 2660 m) "
        "no alcanza la que necesita la papa (desde 8 °C)"
    ]
    assert body["limitations"] == []
    assert body["overall"]["light"] == "red" and body["overall"]["action"] == "rotate"


def test_lote_en_un_valle_de_un_municipio_frio_pasa_a_apto(dataset_con_clima, farmer):
    """Villa de Leyva (6,0 °C) no es apta para la papa; un lote a 2400 m queda 500 m más abajo: 6,0 + 2,925 = 8,9 °C. Apta
    sigue en 501 (todavía no hay señales), donde sin lote da 200."""
    write_grid(dataset_con_clima, [(LEYVA, 2400.0)])
    assert diagnose(farmer, LEYVA, None).status_code == 200
    assert diagnose(farmer, LEYVA, create_lot(farmer, LEYVA, square(LEYVA))).status_code == 501


def test_el_limite_exacto_del_rango_es_apto(dataset_con_clima, farmer):
    """3480 m: 12,8 - 0,00585 × 820 = 8,003, que redondeado a 1 decimal es 8,0, el mínimo de la papa (incluido)."""
    write_grid(dataset_con_clima, [(SAMACA, 3480.0)])
    assert diagnose(farmer, SAMACA, create_lot(farmer, SAMACA, square(SAMACA))).status_code == 501


def test_lote_sin_contorno_usa_el_municipio_con_su_altitud_y_lo_dice(dataset_con_clima, farmer):
    response = diagnose(farmer, {"municipality_id": "25307"}, create_lot(farmer, {"municipality_id": "25307"}))
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["suitability"]["basis"] == "municipality"
    assert (body["suitability"]["tmean_annual_c"], body["suitability"]["altitude_m"]) == (28.4, 289.0)
    assert body["suitability"]["reasons"] == [
        "La temperatura media anual del municipio (28,4 °C, a 289 m) pasa de la que aguanta la papa (hasta 16 °C)"
    ]
    assert body["limitations"] == [
        "Su lote no tiene contorno dibujado: la aptitud usa la temperatura media del municipio, a 289 m. "
        "Dibuje el lote para corregirla a su altitud."
    ]


def test_lote_mas_chico_que_una_celda_usa_la_celda_de_su_centro_y_lo_dice(dataset_con_clima, farmer):
    write_grid(dataset_con_clima, [(SAMACA, 3500.0)])
    tiny = square(SAMACA, half=0.0001)
    response = diagnose(farmer, SAMACA, create_lot(farmer, SAMACA, tiny))
    assert response.status_code == 200, response.json()
    reason = response.json()["suitability"]["reasons"][0]
    assert reason.startswith(
        "La temperatura media anual estimada para su lote (7,9 °C, a 3500 m, la altitud de la celda de 250 m que contiene su centro;"
    )


def test_lote_con_contorno_y_dataset_sin_rejilla_no_se_puede_decidir(dataset_con_clima, farmer):
    """R1: sin la altitud del lote no se usa la del municipio. Aptitud `insufficient_data`: no bloquea, y sin señales sigue en 501."""
    lot_id = create_lot(farmer, SAMACA, square(SAMACA))
    assert not (dataset_con_clima / "grid_cells.parquet").exists()
    assert diagnose(farmer, SAMACA, lot_id).status_code == 501


def zone_of(folder, municipality_id: str, geometry: dict | None):
    loaded = dataset_module.load(folder)
    lot = SimpleNamespace(geometry=geometry)
    return zone_temperature(loaded, loaded.municipalities[municipality_id], lot)


def test_zone_temperature_sin_rejilla_es_insuficiente_y_lo_dice(dataset_con_clima):
    zone = zone_of(dataset_con_clima, "15646", square(SAMACA))
    assert (zone.basis, zone.tmean_annual_c, zone.altitude_m) == ("lot", None, None)
    assert zone.limitation == "La altitud de los lotes no está publicada en esta versión del dataset."


def test_zone_temperature_con_celdas_sin_altitud_es_insuficiente_y_no_rellena(dataset_con_clima):
    write_grid(dataset_con_clima, [(SAMACA, None)])
    zone = zone_of(dataset_con_clima, "15646", square(SAMACA))
    assert (zone.basis, zone.tmean_annual_c, zone.altitude_m) == ("lot", None, None)
    assert zone.limitation == "No hay altitud de NASADEM para su lote: no se pudo saber si el cultivo se da a esa altura."


def test_zone_temperature_sin_gradiente_en_el_manifiesto_no_inventa_tasas(dataset_con_clima):
    """Un dataset publicado antes de HU-191 no trae el gradiente: la aptitud del lote es `insufficient_data` (R1/R4)."""
    import json

    write_grid(dataset_con_clima, [(SAMACA, 3500.0)])
    manifest_path = dataset_con_clima / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["region"]["temperature_lapse_rate"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    zone = zone_of(dataset_con_clima, "15646", square(SAMACA))
    assert zone.tmean_annual_c is None and "gradiente" in zone.limitation


def test_zone_temperature_municipio_sin_temperatura_no_corrige_nada(dataset_con_clima):
    write_grid(dataset_con_clima, [({"lat": 5.0221, "lon": -74.0048}, 2500.0)])
    zone = zone_of(dataset_con_clima, "25899", square({"lat": 5.0221, "lon": -74.0048}))
    assert zone.tmean_annual_c is None and zone.limitation is None


def test_un_lote_de_otro_municipio_responde_422(dataset_con_clima, farmer):
    lot_id = create_lot(farmer, SAMACA, square(SAMACA))
    response = diagnose(farmer, LEYVA, lot_id)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert response.json()["error"]["message"] == "Ese lote es de otro municipio."


def test_un_lote_de_otro_municipio_responde_422_tambien_en_rotaciones(dataset_con_clima, farmer):
    lot_id = create_lot(farmer, SAMACA, square(SAMACA))
    body = {"municipality_id": LEYVA["municipality_id"], "sowing_date": SOON, "lot_id": lot_id}
    response = farmer.post("/api/v1/rotations", json={**body, "priorities": {"water": 3, "soil": 5, "income": 2, "risk": 4}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert response.json()["error"]["message"] == "Ese lote es de otro municipio."


def test_zone_temperature_municipio_sin_altitud_no_rellena_con_su_temperatura(dataset_con_clima):
    write_grid(dataset_con_clima, [(SAMACA, 3500.0)])
    loaded = dataset_module.load(dataset_con_clima)
    municipality = replace(loaded.municipalities["15646"], altitude_m=None)
    assert municipality.tmean_annual_c is not None
    zone = zone_temperature(loaded, municipality, SimpleNamespace(geometry=square(SAMACA)))
    assert (zone.basis, zone.tmean_annual_c, zone.altitude_m) == ("lot", None, None)
    assert "altitud del municipio" in zone.limitation


def test_un_diagnostico_con_lote_no_guarda_nada_ni_registra_el_contorno_ni_la_altitud(dataset_con_clima, farmer, db):
    """R9: ni filas nuevas en la base ni el polígono o la altitud del lote en los logs."""
    write_grid(dataset_con_clima, [(SAMACA, 3500.0)])
    geometry = square(SAMACA)
    lot_id = create_lot(farmer, SAMACA, geometry)
    counts = (db.scalar(select(func.count()).select_from(Lot)), db.scalar(select(func.count()).select_from(Season)))
    with capture_logs() as logs:
        assert diagnose(farmer, SAMACA, lot_id).status_code == 200
    assert (db.scalar(select(func.count()).select_from(Lot)), db.scalar(select(func.count()).select_from(Season))) == counts
    text = str(logs)
    assert "3500" not in text and str(SAMACA["lat"] - 0.01) not in text and "coordinates" not in text


def test_sin_lote_la_temperatura_es_la_del_municipio_y_trae_su_altitud(dataset_con_clima):
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "25307", "crop_id": "papa", "sowing_date": SOON})
    assert response.json()["suitability"]["reasons"] == [
        "La temperatura media anual del municipio (28,4 °C, a 289 m) pasa de la que aguanta la papa (hasta 16 °C)"
    ]
