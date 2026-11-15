"""HU-182: cifras inventadas y rotuladas como ejemplo; medianas esperadas a mano."""

import uuid
from dataclasses import replace

import polars as pl
import pytest
from shapely.geometry import box, mapping
from sqlalchemy import func, select

from backend.accounts.farm_models import Lot
from backend.api.lot_soil import zone_soil, zone_terrain
from backend.api.soil_signals import LOT_SOIL_LIMITATION
from backend.dataset import SOIL_COLUMNS, load
from backend.db.models import Base
from common.grid import cell_id
from tests.test_senal_suelo_datos import diagnose, register


@pytest.fixture
def lot_dataset(dataset_con_clima):
    # Centros en (-73.48625, 5.49125) y (-73.48375, 5.49125).
    rows = []
    for lon, ph, altitude, slope in [(-73.48375, 4.0, 2800.0, 18.0), (-73.48625, 3.8, 2520.0, 2.0)]:
        rows.append(
            {
                "cell_id": cell_id(5.49125, lon),
                "altitude_m": altitude,
                "slope_pct": slope,
                **dict.fromkeys(SOIL_COLUMNS, 10.0),
                "ph": ph,
                "ph_p05": ph - 0.2,
                "ph_p95": ph + 0.2,
                "texture_class": "franco",
                "quality": "ok",
                "source_ids": ["ejemplo"],
            }
        )
    pl.DataFrame(rows).write_parquet(dataset_con_clima / "grid_cells.parquet")
    soil = {
        "municipality_id": "15646",
        **dict.fromkeys(SOIL_COLUMNS, 10.0),
        "ph": 5.5,
        "ph_p05": 5.1,
        "ph_p95": 5.9,
        "texture_class": "arcilloso",
        "cells": 30,
        "quality": "ok",
        "source_id": "ejemplo",
    }
    pl.DataFrame([soil]).write_parquet(dataset_con_clima / "soil_municipality.parquet")
    return load(dataset_con_clima)


def drawn():
    return Lot(municipality_id="15646", geometry=mapping(box(-73.487, 5.4905, -73.483, 5.492)))


def test_medianas_fuentes_y_orden_de_celdas(lot_dataset):
    municipality = lot_dataset.municipalities["15646"]
    soil = zone_soil(lot_dataset, municipality, drawn())
    assert soil["ph"] == pytest.approx(3.9)
    assert soil["ph_p05"] == pytest.approx(3.7)
    assert soil["ph_p95"] == pytest.approx(4.1)
    assert (soil["basis"], soil["cells"], soil["source_ids"], soil["quality"]) == ("lot", 2, ["ejemplo"], "ok")
    assert zone_terrain(lot_dataset, municipality, drawn()) == {"altitude_m": 2660.0, "slope_pct": 10.0, "basis": "lot", "cells": 2}


def test_lote_pequeno_usa_la_celda_de_su_centro(lot_dataset):
    lot = Lot(geometry=mapping(box(-73.486, 5.491, -73.4859, 5.4911)))
    soil = zone_soil(lot_dataset, lot_dataset.municipalities["15646"], lot)
    assert (soil["ph"], soil["cells"], soil["basis"]) == (3.8, 1, "lot")


def test_sin_dibujo_usa_municipio_y_sin_datos_no_sustituye(lot_dataset):
    municipality = lot_dataset.municipalities["15646"]
    soil = zone_soil(lot_dataset, municipality, Lot(geometry=None))
    assert (soil["ph"], soil["basis"], soil["cells"]) == (5.5, "municipality", 30)
    assert zone_soil(replace(lot_dataset, grid=None), municipality, drawn()) is None
    outside = Lot(geometry=mapping(box(-73.4, 5.4, -73.3999, 5.4001)))
    assert zone_soil(lot_dataset, municipality, outside) is None
    assert zone_terrain(replace(lot_dataset, grid=None), municipality, drawn()) is None


def test_nulos_no_se_rellenan_y_las_otras_propiedades_se_conservan(lot_dataset):
    grid = replace(lot_dataset.grid, properties=lot_dataset.grid.properties.with_columns(pl.lit(None, dtype=pl.Float64).alias("ph")))
    soil = zone_soil(replace(lot_dataset, grid=grid), lot_dataset.municipalities["15646"], drawn())
    assert soil["ph"] is None and soil["soc_g_kg"] == 10 and soil["quality"] == "partial"


def test_detalle_diagnostico_suelo_del_poligono_y_ninguna_escritura(lot_dataset, client, db):
    register(client)
    response = client.post("/api/v1/lots", json={"name": "Ejemplo", "municipality_id": "15646", "geometry": drawn().geometry})
    assert response.status_code == 201, response.json()
    lot_id = response.json()["lot_id"]

    def counts():
        return [db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]

    before = counts()
    detail = client.get(f"/api/v1/lots/{lot_id}").json()
    assert detail["soil"]["ph"] == pytest.approx(3.9)
    assert detail["terrain"]["slope_pct"] == 10
    assert detail["versions"]["dataset"] == lot_dataset.version
    body = diagnose(client, lot_id=lot_id)
    assert body["signals"]["soil"]["score"] == 0
    assert LOT_SOIL_LIMITATION not in body["limitations"]
    assert counts() == before
    assert not {"soil", "terrain", "ph", "slope_pct"} & set(Lot.__table__.columns.keys())
    # Cada lectura usa el contorno vigente, sin persistir el resultado anterior.
    lot = db.get(Lot, uuid.UUID(lot_id))
    lot.geometry = mapping(box(-73.484, 5.491, -73.4839, 5.4911))
    db.commit()
    assert client.get(f"/api/v1/lots/{lot_id}").json()["soil"]["ph"] == 4.0


def test_detalle_sin_dibujo_y_sin_dataset(lot_dataset, client, monkeypatch, tmp_path):
    from backend.config.settings import get_settings

    register(client)
    lot = client.post("/api/v1/lots", json={"name": "Ejemplo", "municipality_id": "15646", "area_ha": 1}).json()
    url = f"/api/v1/lots/{lot['lot_id']}"
    detail = client.get(url).json()
    assert detail["soil"]["basis"] == detail["terrain"]["basis"] == "municipality"
    assert detail["soil"]["ph"] == 5.5
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(tmp_path / "ausente"))
    get_settings.cache_clear()
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["soil"] is None and response.json()["terrain"] is None
    assert response.json()["versions"] == {"dataset": None, "rules": None}


@pytest.mark.parametrize("endpoint", ["diagnostics", "rotations"])
def test_sin_sesion_y_lote_ajeno(lot_dataset, client, endpoint):
    register(client)
    lot = client.post("/api/v1/lots", json={"name": "Ejemplo", "municipality_id": "15646", "area_ha": 1}).json()
    body = {"municipality_id": "15646", "sowing_date": "2027-04-01", "lot_id": lot["lot_id"]}
    body.update({"crop_id": "papa"} if endpoint == "diagnostics" else {"priorities": {"water": 3, "soil": 3, "income": 3, "risk": 3}})
    client.cookies.clear()
    assert client.post(f"/api/v1/{endpoint}", json=body).status_code == 401
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "otra.persona",
            "password": "papaya-criolla-2026",
            "display_name": "Otra",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    assert client.post(f"/api/v1/{endpoint}", json=body).status_code == 404
