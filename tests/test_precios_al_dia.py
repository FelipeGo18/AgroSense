"""Precios de SIPSA al día (HU-222): la API los baja del DANE cada día, los valida y sirve la última versión buena.

Ninguna prueba usa la red: la «descarga» escribe una respuesta de ejemplo del servicio.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import market_updates
from backend.api.main import app
from backend.market_updates import BOGOTA
from pipeline.build import ValidationError
from pipeline.sources import sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_SIPSA_ROWS, sipsa_row, sipsa_xml

AT_3_05_PM = datetime(2026, 10, 21, 15, 5, tzinfo=BOGOTA)


def fake_download(rows):
    """Una descarga de ejemplo: escribe la respuesta del servicio donde la escribiría `sipsa.download`."""

    def download(cache):
        cache.mkdir(parents=True, exist_ok=True)
        (cache / sipsa.ROWS_FILE).write_text(sipsa_xml(rows), encoding="utf-8")
        (cache / sipsa.META_FILE).write_text("2026-10-21T20:05:00+00:00", encoding="utf-8")
        return cache / sipsa.ROWS_FILE

    return download


def failing_download(cache):
    raise OSError("el DANE no respondió")


TODAY = [*SAMPLE_SIPSA_ROWS, sipsa_row("1", "Papa negra*", "2026-10-21", 2900, 3010, 3100)]


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 10, 21, 10, 0, tzinfo=BOGOTA), datetime(2026, 10, 21, 15, 0, tzinfo=BOGOTA)),
        (datetime(2026, 10, 21, 15, 0, tzinfo=BOGOTA), datetime(2026, 10, 22, 15, 0, tzinfo=BOGOTA)),
        # A las 21:00 UTC ya son las 4:00 p. m. en Bogotá: la de hoy ya pasó.
        (datetime(2026, 10, 21, 21, 0, tzinfo=UTC), datetime(2026, 10, 22, 15, 0, tzinfo=BOGOTA)),
    ],
)
def test_se_baja_cada_dia_a_las_3_pm_de_bogota(now, expected):
    assert market_updates.next_run(now) == expected


def test_hace_falta_bajar_si_no_hay_version_o_si_es_de_antes_de_la_ultima_publicacion(tmp_path):
    data = market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM)
    assert market_updates.is_stale(None, AT_3_05_PM)
    assert not market_updates.is_stale(data, AT_3_05_PM + timedelta(hours=20))  # mañana a las 11:05 a. m.
    assert market_updates.is_stale(data, AT_3_05_PM + timedelta(days=1))  # mañana a las 3:05 p. m.


def test_una_actualizacion_buena_queda_como_version_nueva_y_borra_la_descarga(tmp_path):
    data = market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM)
    assert data.version == "sipsa-20261021T1505"
    assert market_updates.current() is data
    assert json.loads((tmp_path / "current.json").read_text(encoding="utf-8"))["version"] == data.version
    assert {p.name for p in (tmp_path / data.version).iterdir()} == {"market_price_day.parquet", "market_price_season.parquet"}
    assert not (tmp_path / "raw").exists()
    # Al reiniciar la API, se lee la misma versión.
    market_updates._serve(None)
    assert market_updates.load_latest(tmp_path).version == data.version


@pytest.mark.parametrize(
    ("download", "error"),
    [
        (failing_download, OSError),
        # Un precio medio fuera del mínimo y el máximo: no pasa la validación del pipeline.
        (fake_download([sipsa_row("1", "Papa negra*", "2026-10-22", 3000, 2000, 3100)]), ValidationError),
    ],
)
def test_si_falla_se_sigue_sirviendo_la_ultima_version_buena(tmp_path, download, error):
    good = market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM)
    with pytest.raises(error):
        market_updates.refresh(tmp_path, SAMPLE_MARKETS, download, now=AT_3_05_PM + timedelta(days=1))
    assert market_updates.current() is good
    assert json.loads((tmp_path / "current.json").read_text(encoding="utf-8"))["version"] == good.version
    assert not (tmp_path / "raw").exists()


def test_se_guardan_solo_las_dos_ultimas_versiones(tmp_path):
    for day in range(3):
        market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM + timedelta(days=day))
    assert sorted(p.name for p in tmp_path.glob("sipsa-*")) == ["sipsa-20261022T1505", "sipsa-20261023T1505"]


def test_la_api_sirve_los_precios_de_hoy_y_dice_su_version(market_dataset, tmp_path):
    published = TestClient(app).get("/api/v1/market/prices").json()
    assert (published["version"], published["updated_at"], published["date"]) == ("0.0.0-pruebas", None, "2026-10-19")

    market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM)
    body = TestClient(app).get("/api/v1/market/prices").json()
    assert body["version"] == "sipsa-20261021T1505" and body["updated_at"].startswith("2026-10-21T15:05")
    assert body["date"] == "2026-10-21"
    papa = next(p for p in body["products"] if p["product_id"] == "papa-negra")
    assert papa["latest"]["avg_cop_kg"] == 3010
    history = TestClient(app).get("/api/v1/market/prices/papa-negra").json()
    assert history["version"] == "sipsa-20261021T1505" and history["days"][-1]["date"] == "2026-10-21"


def test_una_version_bajada_mas_vieja_que_la_publicada_no_se_sirve(market_dataset, tmp_path):
    """Si alguien publica un dataset más nuevo que lo bajado, gana lo publicado: nunca se retrocede."""
    market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download([sipsa_row("1", "Papa negra*", "2026-10-01", 1, 2, 3)]), now=AT_3_05_PM)
    assert TestClient(app).get("/api/v1/market/prices").json()["version"] == "0.0.0-pruebas"


def test_sin_dataset_publicado_igual_sirve_lo_bajado(dataset, tmp_path):
    """El dataset de ejemplo no trae precios: con una versión bajada, la pantalla funciona igual."""
    market_updates.refresh(tmp_path, SAMPLE_MARKETS, fake_download(TODAY), now=AT_3_05_PM)
    response = TestClient(app).get("/api/v1/market/prices")
    assert response.status_code == 200 and response.json()["version"] == "sipsa-20261021T1505"


def test_apagada_la_actualizacion_diaria_no_arranca(monkeypatch):
    monkeypatch.setattr(market_updates, "run_daily", lambda *a: pytest.fail("no debe arrancar"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code in (200, 503)
