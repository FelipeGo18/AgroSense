"""HU-146: `POST /api/v1/water-plans` con el motor del plan de agua (`backend/engine/water_plan.py`, sobre el balance de
HU-144).

Usa tres datasets:

- una copia del de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5) con la lluvia rotulada con la
  fuente de su tabla (`tests/ejemplos_con_fuente.py`): Samacá con lluvia de GPM IMERG, ET0 y humedad de NASA POWER y la
  textura del municipio;
- el de las pruebas (`dataset`, de `tests/conftest.py`), sin clima ni suelo: todo es sin datos (R1);
- el publicado de verdad (`data/published/`, el de la demo): papa en Samacá y en Duitama.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from structlog.testing import capture_logs

from backend.api import calc_models as m
from backend.api.main import app
from backend.config.settings import get_settings
from backend.config.versions import rules_version
from backend.dataset import get_dataset
from backend.db.models import Base
from backend.engine.water_notes import NO_RETENTION
from backend.engine.water_plan import ESTIMATE, fallow_note
from common.signal_sources import get_signal_sources
from tests.ejemplos_con_fuente import examples_with_sources

PUBLISHED = Path(__file__).resolve().parents[1] / "data" / "published"
SAMACA, DUITAMA = "15646", "15238"
APRIL = "2027-04-01"
PLAN = {"municipality_id": SAMACA, "total_area_ha": 1.26, "crops": [{"crop_id": "papa", "area_pct": 100, "sowing_date": APRIL}]}
NULL_RANGE = {"normal": None, "dry": None}


@pytest.fixture
def examples(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(examples_with_sources(tmp_path / "ejemplos")))
    get_settings.cache_clear()


@pytest.fixture
def published(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(PUBLISHED))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def post(body: dict, client: TestClient | None = None):
    return (client or TestClient(app)).post("/api/v1/water-plans", json=body)


def plan_of(body: dict) -> dict:
    response = post(body)
    assert response.status_code == 200, response.json()
    return response.json()


def rain_caveat() -> str:
    return get_signal_sources().for_region(get_dataset().region["id"])["water"].caveat


# ---------- la forma del contrato ----------


def test_responde_200_con_la_forma_del_contrato(examples):
    body = plan_of(PLAN)
    m.WaterPlanResponse.model_validate(body)
    assert body["request"] == PLAN
    (papa,) = body["crops"]
    assert (papa["crop_id"], papa["area_ha"], papa["sowing_date"], papa["harvest_basis"]) == ("papa", 1.26, APRIL, "calendar")
    assert papa["harvest_estimate"] > APRIL
    # La etapa que ocupa la mayor parte del mes: en mayo, 16 días de desarrollo contra 15 de inicial; en junio, 16 de
    # media contra 14 de desarrollo; en agosto, 23 de media contra 8 finales.
    stages = [(4, "initial"), (5, "development"), (6, "mid"), (7, "mid"), (8, "mid"), (9, "late")]
    assert [(month["month"], month["stage"]) for month in papa["months"]] == stages
    for month in papa["months"]:
        assert month["status"] == "available"
        for year in ("normal", "dry"):
            low, high = month["deficit_mm"][year]
            assert 0 <= low <= high
            assert month["volume_m3"][year] == pytest.approx([low * 12.6, high * 12.6], abs=0.06)
    assert [(f["year"], f["month"]) for f in body["farm"]["months"]] == [(m_["year"], m_["month"]) for m_ in papa["months"]]
    assert body["farm"]["total_volume_m3"] == papa["total_volume_m3"]
    assert body["sources"] == {"rain": "imerg", "et0": "nasa_power", "soil": "soilgrids"}
    assert body["soil_basis"] == "municipality"
    dataset = get_dataset()
    assert body["versions"] == {"dataset": dataset.version, "rules": rules_version(dataset.rules_version)}


def test_las_limitaciones_dicen_que_es_una_estimacion_el_aviso_de_la_lluvia_y_que_son_datos_de_ejemplo(examples):
    limitations = plan_of(PLAN)["limitations"]
    assert ESTIMATE in limitations
    assert rain_caveat() in limitations
    assert any("ejemplo" in text for text in limitations)
    assert len(limitations) == len(set(limitations))
    # Con la textura del municipio el agua guardada sí entra.
    assert NO_RETENTION not in limitations


def test_la_humedad_del_suelo_es_la_de_power_por_mes_de_la_ventana_y_no_la_de_smap(examples):
    body = plan_of(PLAN)
    months = [month["month"] for month in body["crops"][0]["months"]]
    readings = body["soil_moisture"]
    assert [reading["month"] for reading in readings] == months
    assert {(r["source_id"], r["indicator"], r["unit"]) for r in readings} == {("nasa_power", "soil_wetness_root", "fracción")}
    assert all(r["value"] is None or 0 <= r["value"] <= 1 for r in readings)
    # SMAP está en `planned` (HU-210): no se muestra.
    assert all(r["source_id"] != "smap" for r in readings)


def test_el_area_de_cada_cultivo_es_su_parte_del_total(examples):
    body = plan_of(
        {
            "municipality_id": SAMACA,
            "total_area_ha": 5.0,
            "crops": [
                {"crop_id": "papa", "area_pct": 60, "sowing_date": "2027-03-15"},
                {"crop_id": "arveja", "area_pct": 30, "sowing_date": APRIL},
            ],
        }
    )
    assert [c["area_ha"] for c in body["crops"]] == [3.0, 1.5]
    keys = sorted({(month["year"], month["month"]) for c in body["crops"] for month in c["months"]})
    assert [(f["year"], f["month"]) for f in body["farm"]["months"]] == keys


def test_un_abono_verde_es_un_ciclo_valido_con_su_agua(examples):
    body = plan_of({**PLAN, "crops": [{"crop_id": "avena_vicia", "area_pct": 100, "sowing_date": APRIL}]})
    assert body["crops"][0]["months"]
    assert body["crops"][0]["total_volume_m3"]["dry"] is not None


def test_un_descanso_no_tiene_agua_y_lo_dice(examples):
    body = plan_of(
        {
            **PLAN,
            "crops": [
                {"crop_id": "papa", "area_pct": 70, "sowing_date": APRIL},
                {"crop_id": "descanso", "area_pct": 30, "sowing_date": APRIL},
            ],
        }
    )
    rest = body["crops"][1]
    assert (rest["months"], rest["harvest_estimate"], rest["harvest_basis"]) == ([], None, None)
    assert rest["total_volume_m3"] == NULL_RANGE
    assert fallow_note("el descanso") in body["limitations"]
    # La finca es la de la papa: el descanso no es un dato que falta.
    assert body["farm"]["total_volume_m3"] == body["crops"][0]["total_volume_m3"]


def test_la_fecha_no_se_limita_a_doce_meses(examples):
    later = (date.today() + timedelta(days=500)).isoformat()
    assert post({**PLAN, "crops": [{"crop_id": "papa", "area_pct": 100, "sowing_date": later}]}).status_code == 200


# ---------- 422 ----------


@pytest.mark.parametrize(
    "crops",
    [
        [{"crop_id": "papa", "area_pct": 120, "sowing_date": APRIL}],
        [{"crop_id": "papa", "area_pct": 70, "sowing_date": APRIL}, {"crop_id": "arveja", "area_pct": 40, "sowing_date": APRIL}],
        [{"crop_id": "yuca", "area_pct": 100, "sowing_date": APRIL}],
        [{"crop_id": "papa", "area_pct": 0, "sowing_date": APRIL}],
    ],
)
def test_porcentajes_de_mas_de_100_o_un_cultivo_que_no_existe_responden_422(examples, crops):
    response = post({**PLAN, "crops": crops})
    assert response.status_code == 422, response.json()
    assert response.json()["error"]["code"] == "invalid_input"


def test_un_municipio_fuera_de_la_region_responde_422(examples):
    assert post({**PLAN, "municipality_id": "05001"}).status_code == 422


# ---------- sin datos (R1) ----------


def test_sin_clima_ni_suelo_todo_es_sin_datos_y_lo_dice(dataset):
    body = plan_of(PLAN)
    m.WaterPlanResponse.model_validate(body)
    (papa,) = body["crops"]
    assert papa["months"]
    for month in papa["months"]:
        assert month["status"] == "insufficient_data"
        assert month["rain_mm"] == NULL_RANGE and month["deficit_mm"] == NULL_RANGE and month["volume_m3"] == NULL_RANGE
    assert papa["total_volume_m3"] == NULL_RANGE
    assert body["farm"]["total_volume_m3"] == NULL_RANGE
    assert all(f["volume_m3"] == NULL_RANGE for f in body["farm"]["months"])
    # Sin la textura del municipio, el suelo no se usó: no se cita SoilGrids.
    assert body["sources"]["soil"] is None
    assert NO_RETENTION in body["limitations"]
    assert any(text.startswith("Sin la lluvia de ") for text in body["limitations"])


# ---------- R4 y R9 ----------


def test_dos_consultas_iguales_dan_lo_mismo(examples):
    client = TestClient(app)
    assert post(PLAN, client).content == post(PLAN, client).content


def rows(db) -> dict[str, list[tuple]]:
    db.rollback()
    return {
        table.name: [tuple(row) for row in db.execute(select(table).order_by(*table.primary_key.columns)).all()]
        for table in Base.metadata.sorted_tables
    }


def test_no_escribe_en_la_base_ni_registra_la_consulta(examples, client, db):
    """R9: ninguna tabla cambia, y ni el municipio, ni el cultivo, ni la fecha, ni el área van al log."""
    counts = {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}
    before = rows(db)
    with capture_logs() as logs:
        response = post(PLAN, client)
    assert response.status_code == 200
    assert rows(db) == before
    assert {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables} == counts
    text = str([{key: value for key, value in entry.items() if key != "request_id"} for entry in logs])
    for value in (SAMACA, "papa", APRIL, "1.26"):
        assert value not in text, value


# ---------- el dataset publicado (el de la demo) ----------


@pytest.mark.parametrize("municipality_id", [SAMACA, DUITAMA])
def test_papa_con_el_dataset_publicado(published, municipality_id):
    papa = {"crop_id": "papa", "area_pct": 100, "sowing_date": "2026-12-01"}
    body = plan_of({"municipality_id": municipality_id, "total_area_ha": 1.0, "crops": [papa]})
    m.WaterPlanResponse.model_validate(body)
    assert body["sources"]["rain"] == "imerg" and body["sources"]["et0"] == "nasa_power"
    assert rain_caveat() in body["limitations"]
    assert ESTIMATE in body["limitations"]
    assert body["versions"]["dataset"] == get_dataset().version
    (papa,) = body["crops"]
    assert papa["months"] and all(month["stage"] for month in papa["months"])
    assert {reading["source_id"] for reading in body["soil_moisture"]} == {"nasa_power"}
    assert any(reading["value"] is not None for reading in body["soil_moisture"])
    # Con el dataset publicado todos los meses vienen completos: el total y la finca tienen dato (PR #135).
    assert all(month["status"] == "available" for month in papa["months"])
    assert papa["total_volume_m3"]["dry"] is not None
    assert body["farm"]["total_volume_m3"] == papa["total_volume_m3"]


def test_con_el_dataset_publicado_los_meses_dan_exacto_el_total(published):
    """Revisión del PR #135: papa en Samacá, 2 ha, sembrada el 4 ene 2027. En el año seco los meses sumaban 3936 m³ y
    el total decía 3934, porque salía del déficit total del balance, redondeado aparte."""
    papa = {"crop_id": "papa", "area_pct": 100, "sowing_date": "2027-01-04"}
    body = plan_of({"municipality_id": SAMACA, "total_area_ha": 2.0, "crops": [papa]})
    (papa,) = body["crops"]
    for year in ("normal", "dry"):
        volumes = [month["volume_m3"][year] for month in papa["months"]]
        assert all(volumes), "algún mes sin volumen"
        months_sum = [round(sum(volume[0] for volume in volumes), 1), round(sum(volume[1] for volume in volumes), 1)]
        assert papa["total_volume_m3"][year] == months_sum
        assert body["farm"]["total_volume_m3"][year] == months_sum
