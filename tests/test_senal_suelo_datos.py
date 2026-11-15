"""La señal de suelo en `/diagnostics` (HU-183): la API lee el suelo del municipio de `soil_municipality` (HU-181) una vez
por consulta y se lo pasa al motor ya leído (R6). Escritas antes del código (HU-121).

Usa el dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): en los tres municipios del
ejemplo el suelo es de pH 5,5 (de 5,1 a 5,9). La ficha de la papa es la real (tolera de 4,2 a 8,5; óptimo de 5,0 a 6,2).
«Hoy» queda fijo en el 14 de noviembre de 2026 en la región (R4).
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api import calc_models as m
from backend.api.main import app
from backend.api.soil_signals import LOT_SOIL_LIMITATION, soil_for, zone_soil_ph
from backend.config.settings import get_settings
from backend.config.thresholds import load_thresholds
from backend.dataset import load
from backend.engine.soil_signal import ESTIMATE_LABEL, NO_SOIL_REASON, ZoneSoilPh
from common import region

EXAMPLES = Path("data/examples")
SAMACA = "15646"
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
APRIL = "2027-04-01"
NO_WATER = {"water": 0, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
SAMACA_REASON = (
    "pH estimado de 5,5 (de 5,1 a 5,9), dentro del óptimo de la papa (5,0 a 6,2). "
    "Todo ese rango está dentro de lo que tolera (4,2 a 8,5). " + ESTIMATE_LABEL
)


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return TODAY.astimezone(tz) if tz else TODAY

    monkeypatch.setattr(region, "datetime", Clock)


def use(monkeypatch, folder: Path) -> None:
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder.resolve()))
    get_settings.cache_clear()


@pytest.fixture
def examples(monkeypatch):
    use(monkeypatch, EXAMPLES)


@pytest.fixture
def examples_copy(tmp_path, monkeypatch):
    folder = tmp_path / "ejemplos"
    shutil.copytree(EXAMPLES, folder)
    use(monkeypatch, folder)
    return folder


def diagnose(client, **extra) -> dict:
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL, **extra}
    response = client.post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    m.DiagnosisResponse.model_validate(response.json())
    return response.json()


# ---------- la lectura del dataset ----------


def test_el_suelo_del_municipio_sale_de_soil_municipality():
    dataset = load(EXAMPLES)
    assert zone_soil_ph(dataset, SAMACA) == ZoneSoilPh(5.5, 5.1, 5.9)
    assert zone_soil_ph(dataset, "99999") is None


def test_soil_for_califica_con_la_ficha_y_con_lote_dice_que_el_suelo_es_del_municipio():
    dataset = load(EXAMPLES)
    municipality = dataset.municipalities[SAMACA]
    thresholds = load_thresholds()
    without = soil_for(dataset, municipality, False, dataset.crops["papa"], thresholds, "la papa")
    assert (without.status, without.score, without.level, without.critical) == ("available", 100, "favorable", False)
    assert without.reasons == (SAMACA_REASON,)
    assert LOT_SOIL_LIMITATION not in without.limitations
    with_lot = soil_for(dataset, municipality, True, dataset.crops["papa"], thresholds, "la papa")
    assert (with_lot.score, with_lot.level, with_lot.reasons) == (100, "favorable", (SAMACA_REASON,))
    assert with_lot.limitations == (LOT_SOIL_LIMITATION,)


# ---------- en el diagnóstico ----------


def test_el_diagnostico_trae_la_senal_de_suelo_calificada(examples):
    body = diagnose(TestClient(app))
    soil = body["signals"]["soil"]
    assert (soil["status"], soil["level"], soil["score"], soil["critical"], soil["counts"]) == ("available", "favorable", 100, False, True)
    assert soil["indicators"] == ["ph"]
    assert soil["reasons"] == [SAMACA_REASON]
    assert "sources" not in soil or soil["sources"] is None
    # Sin lote, la limitación del suelo del lote no aparece; sin datos que falten, tampoco la del suelo.
    assert LOT_SOIL_LIMITATION not in body["limitations"]
    assert NO_SOIL_REASON not in body["limitations"]
    assert not any("el suelo" in text for text in body["limitations"])


def test_el_suelo_es_el_mismo_en_todas_las_ventanas(examples):
    """El suelo no cambia con la fecha: la misma señal en cualquier mes de siembra (HU-183, notas)."""
    client = TestClient(app)
    soils = [
        diagnose(client, sowing_date=day, priorities=NO_WATER)["signals"]["soil"] for day in ("2026-11-01", "2027-04-01", "2027-08-02")
    ]
    assert soils[0] == soils[1] == soils[2]


def test_sin_suelo_para_el_municipio_es_insufficient_data_y_va_a_las_limitaciones(examples_copy):
    (examples_copy / "soil_municipality.parquet").unlink()
    body = diagnose(TestClient(app))
    soil = body["signals"]["soil"]
    assert (soil["status"], soil["level"], soil["score"], soil["critical"]) == ("insufficient_data", None, None, False)
    assert soil["reasons"] == [NO_SOIL_REASON]
    # Una sola vez, con su propia frase (no la genérica de «Sin datos para la zona»).
    assert body["limitations"].count(NO_SOIL_REASON) == 1
    assert "Sin datos para la zona: el suelo no se evaluó." not in body["limitations"]


def test_un_ph_nulo_en_la_fila_del_municipio_es_sin_suelo(examples_copy):
    path = examples_copy / "soil_municipality.parquet"
    table = pl.read_parquet(path)
    table.with_columns(pl.when(pl.col("municipality_id") == SAMACA).then(None).otherwise(pl.col("ph")).alias("ph")).write_parquet(path)
    soil = diagnose(TestClient(app))["signals"]["soil"]
    assert (soil["status"], soil["score"], soil["reasons"]) == ("insufficient_data", None, [NO_SOIL_REASON])


def test_un_intervalo_que_cruza_un_limite_lleva_la_senal_a_moderate_con_la_calificacion_de_la_curva(examples_copy):
    """Los percentiles DE EJEMPLO de Samacá se abren hasta 4,1 y 7,9 (como en los datos reales del altiplano)."""
    path = examples_copy / "soil_municipality.parquet"
    table = pl.read_parquet(path)
    samaca = pl.col("municipality_id") == SAMACA
    table.with_columns(
        pl.when(samaca).then(4.1).otherwise(pl.col("ph_p05")).alias("ph_p05"),
        pl.when(samaca).then(7.9).otherwise(pl.col("ph_p95")).alias("ph_p95"),
    ).write_parquet(path)
    soil = diagnose(TestClient(app))["signals"]["soil"]
    assert (soil["status"], soil["score"], soil["level"], soil["critical"]) == ("available", 100, "moderate", False)
    assert "Parte de ese rango queda fuera de lo que tolera (4,2 a 8,5): por eso no sale favorable" in soil["reasons"][0]


def test_suelo_desfavorable_da_amarillo_y_rotar_no_rojo(examples_copy):
    """R2 y R10: el suelo nunca es crítico; solo, desfavorable, deja la luz en amarillo y la acción en rotar (cambiar de
    fecha no lo arregla). Un suelo DE EJEMPLO más ácido que lo que tolera la papa."""
    path = examples_copy / "soil_municipality.parquet"
    table = pl.read_parquet(path)
    samaca = pl.col("municipality_id") == SAMACA
    table.with_columns(
        pl.when(samaca).then(3.9).otherwise(pl.col("ph")).alias("ph"),
        pl.when(samaca).then(3.6).otherwise(pl.col("ph_p05")).alias("ph_p05"),
        pl.when(samaca).then(4.1).otherwise(pl.col("ph_p95")).alias("ph_p95"),
    ).write_parquet(path)
    body = diagnose(TestClient(app), priorities=NO_WATER)
    soil = body["signals"]["soil"]
    assert (soil["score"], soil["level"], soil["critical"]) == (0, "unfavorable", False)
    # En abril, la helada y el calor del ejemplo dan 100: el suelo es la única desfavorable.
    assert (body["overall"]["light"], body["overall"]["action"], body["overall"]["high_risk"]) == ("yellow", "rotate", False)
    assert body["overall"]["limiting_signal"] == "soil"


# ---------- con lote: el suelo sigue siendo el del municipio (HU-182 aparte) ----------


def register(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "rosa.suelo",
            "password": "papaya-criolla-2026",
            "display_name": "Rosa",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    assert response.status_code == 201, response.json()


def test_con_lote_el_suelo_es_el_del_municipio_y_lo_dicen_las_limitaciones(examples, client):
    register(client)
    response = client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": SAMACA, "area_ha": 1.0})
    assert response.status_code == 201, response.json()
    body = diagnose(client, lot_id=response.json()["lot_id"])
    soil = body["signals"]["soil"]
    assert (soil["score"], soil["level"], soil["reasons"]) == (100, "favorable", [SAMACA_REASON])
    assert body["limitations"].count(LOT_SOIL_LIMITATION) == 1
