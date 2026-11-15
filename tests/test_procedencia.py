"""HU-122: de dónde sale cada dato. El manifiesto, las fuentes de la NASA y `GET /api/v1/version` (R4, R8).

Lo de la NASA se comprueba sobre el dataset publicado de verdad (`data/published/`), el de la demo.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.settings import get_settings
from backend.dataset import load

PUBLISHED = Path(__file__).resolve().parents[1] / "data" / "published"
CONTRACT_SOURCE_FIELDS = {"source_id", "name", "institution", "url", "coverage", "license"}
# Los productos de la NASA que ya tienen adaptador y entran al núcleo (decisión 12). MODIS NDVI desde HU-208 y GIBS desde
# HU-211; SMAP se suma con HU-210, que publica su entrada en `sources`.
NASA_IN_USE = ("nasa_power", "nasadem", "imerg", "modis_ndvi", "nasa_gibs")


def test_version_con_dataset_responde_lo_que_pide_el_contrato(dataset):
    body = TestClient(app).get("/api/v1/version").json()
    assert body["dataset_version"] and body["rules_version"] and body["created_at"] and body["region"]
    assert body["default_weights"] and body["weights_version"] and body["weights_reasons"]
    assert body["sources"], "sin fuentes"
    for source in body["sources"]:
        assert set(source) >= CONTRACT_SOURCE_FIELDS, source.get("source_id")
        assert source["source_id"] and source["name"] and source["coverage"], source["source_id"]


def test_el_manifiesto_publicado_trae_version_y_filas_y_cobertura_de_cada_tabla():
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] and manifest["rules_version"] and manifest["created_at"]
    assert manifest["region"]["id"] and manifest["region"]["name"]
    assert "sources" in manifest["tables"]
    for name, table in manifest["tables"].items():
        assert isinstance(table["rows"], int) and table["rows"] >= 0, name
        assert table["coverage"], name


@pytest.fixture
def published(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(PUBLISHED))
    get_settings.cache_clear()
    yield load(PUBLISHED)
    get_settings.cache_clear()


@pytest.mark.parametrize("source_id", NASA_IN_USE)
def test_cada_producto_de_la_nasa_dice_mision_resolucion_periodo_acceso_y_licencia(published, source_id):
    sources = {s["source_id"]: s for s in published.sources}
    assert source_id in sources, f"{source_id} no está en `sources`"
    s = sources[source_id]
    # Misión o proyecto y quién lo distribuye.
    assert "NASA" in s["institution"], s["institution"]
    # Acceso: el enlace (DOI o página del producto) y periodo.
    assert s["url"].startswith("https://"), s["url"]
    assert s["period_covered"], "sin periodo"
    # Licencia o condición de uso.
    assert s["license"], "sin licencia"
    # Resolución: en grados o en metros, en el nombre, la cobertura o las notas.
    text = " ".join(str(s.get(k) or "") for k in ("name", "coverage", "notes"))
    assert "°" in text or " m" in text, f"{source_id}: no dice su resolución"


def test_version_publica_las_fuentes_de_la_nasa_del_dataset_de_la_demo(published):
    body = TestClient(app).get("/api/v1/version").json()
    ids = {s["source_id"] for s in body["sources"]}
    assert set(NASA_IN_USE) <= ids
    assert body["dataset_version"] == published.version
