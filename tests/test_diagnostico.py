"""HU-076: `POST /api/v1/diagnostics` con el motor (HU-074, HU-077, HU-190, HU-073, HU-191, HU-192).

Usa el dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá (12,8 °C) con heladas y
calor de ejemplo. «Hoy» queda fijo en el 14 de noviembre de 2026 en la región, para que las ventanas no dependan del día
en que corre la prueba (R4). En esos datos, la papa sembrada en noviembre tiene helada crítica (7 de 100) y la de abril
no tiene heladas (100); el calor da 100 en todo el año.

El agua (HU-071), el suelo (HU-183) y la oferta (HU-072) todavía no tienen motor: son `insufficient_data`. Con los pesos
por defecto el agua pesa 3, así que la luz de AgroSense es `not_evaluable` (regla 1): es lo honesto (R1). Para ver una
luz roja o verde, las pruebas ponen el agua en 0 con `priorities`.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from structlog.testing import capture_logs

from backend.api import calc_models as m
from backend.api import calculations
from backend.api.calculations import IRRIGATION_UNKNOWN
from backend.api.climate_signals import frost_caveat
from backend.api.main import app
from backend.api.window_signals import pending_reason
from backend.config.settings import get_settings
from backend.config.weights import get_default_weights
from backend.dataset import get_dataset
from backend.db.models import Base
from common import region

EXAMPLES = Path("data/examples")
SAMACA = "15646"
SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
# 14 de noviembre de 2026 al mediodía en Bogotá.
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
NOVEMBER, APRIL = "2026-11-01", "2027-04-01"
# El agua en 0: sin su motor, con peso la luz sería siempre `not_evaluable`.
NO_WATER = {"water": 0, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
PENDING = {name: pending_reason(name) for name in ("water", "soil", "supply")}


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
    """Una copia de los ejemplos para cambiar una tabla sin tocar el repositorio."""
    folder = tmp_path / "ejemplos"
    shutil.copytree(EXAMPLES, folder)
    use(monkeypatch, folder)
    return folder


def diagnose(client, sowing_date: str = APRIL, **extra):
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": sowing_date, **extra}
    response = client.post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    m.DiagnosisResponse.model_validate(response.json())
    return response.json()


# ---------- forma completa y pesos por defecto ----------


def test_un_diagnostico_con_datos_trae_la_forma_completa(examples):
    body = diagnose(TestClient(app))
    assert body["request"] == {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL, "irrigated": None, "lot_id": None}
    assert body["suitability"]["level"] == "suitable"
    # La papa de la ficha dura 45 + 30 + 70 + 20 = 165 días (HU-220).
    assert body["window"] == {"sowing_start": APRIL, "harvest_estimate": "2027-09-13", "harvest_basis": "calendar", "supply_semester": None}
    assert tuple(body["signals"]) == SIGNALS
    frost, heat = body["signals"]["frost"], body["signals"]["heat"]
    assert (frost["status"], frost["score"], frost["level"], frost["critical"], frost["indicators"]) == (
        "available", 100, "favorable", False, ["frost_freq_pct"]
    )  # fmt: skip
    assert (heat["status"], heat["score"], heat["level"], heat["indicators"]) == ("available", 100, "favorable", ["tmax_p90_c"])
    # Sin central de precios para el departamento en los ejemplos: el texto del contrato (HU-073).
    assert body["signals"]["market"]["reasons"] == ["Sin datos de mercado para la zona"]
    for name, reason in PENDING.items():
        signal = body["signals"][name]
        assert (signal["status"], signal["level"], signal["score"], signal["critical"], signal["reasons"]) == (
            "insufficient_data", None, None, False, [reason]
        )  # fmt: skip
    assert body["versions"] == {"dataset": "ejemplo", "rules": "0.1.0"}


def test_sin_prioridades_las_dos_luces_coinciden_con_los_pesos_por_defecto(examples):
    body = diagnose(TestClient(app))
    defaults = get_default_weights().weights
    assert body["weights"] == defaults
    assert body["overall"] == body["overall_default"]
    assert body["overall"]["weights_basis"] == "default"
    # Con el agua sin datos y con peso, la luz no se puede evaluar (regla 1): no se inventa un verde (R1).
    assert (body["overall"]["light"], body["overall"]["action"], body["overall"]["limiting_signal"]) == (
        "not_evaluable",
        "review_data",
        None,
    )
    # Ninguna acción es `other_window`: `best_windows` no viene (no viene nulo), como `DIAGNOSIS_OK` del contrato.
    assert "best_windows" not in body
    # Con los pesos por defecto (todos de 1 a 5) cuentan todas, también las que no tienen datos.
    assert all(body["signals"][name]["counts"] for name in SIGNALS)


def test_las_limitaciones_dicen_cada_senal_sin_datos_y_el_aviso_de_heladas_sin_repetir(examples):
    body = diagnose(TestClient(app))
    limitations = body["limitations"]
    assert len(limitations) == len(set(limitations))
    for name in ("el agua", "el suelo", "la oferta", "el mercado"):
        assert f"Sin datos para la zona: {name} no se evaluó." in limitations
    assert not any("la helada no se evaluó" in text or "el calor no se evaluó" in text for text in limitations)
    # El `frost_caveat` de la región va siempre que se evalúa la ventana (HU-077).
    assert frost_caveat(get_dataset()) in limitations


# ---------- prioridades del agricultor y las dos luces ----------


def test_con_prioridades_overall_usa_las_del_agricultor_y_counts_sigue_sus_pesos(examples):
    body = diagnose(TestClient(app), priorities=NO_WATER)
    assert body["weights"] == NO_WATER
    assert body["overall"]["weights_basis"] == "farmer" and body["overall_default"]["weights_basis"] == "default"
    # Peso 0 y sin dato (no es crítica): no cuenta (HU-074).
    assert body["signals"]["water"]["counts"] is False
    assert all(body["signals"][name]["counts"] for name in SIGNALS if name != "water")
    # Abril: heladas y calor en 100, lo demás sin datos. Con sus prioridades es verde; con las de AgroSense, no evaluable.
    assert (body["overall"]["light"], body["overall"]["action"]) == ("green", "sow")
    assert body["overall_default"]["light"] == "not_evaluable"
    assert "best_windows" not in body


def test_caso_de_referencia_helada_critica_da_rojo_y_busca_otra_ventana(examples):
    """HU-077: una helada crítica da rojo y la acción es `other_window`. Trae las mejores ventanas, ninguna de alto riesgo
    (R2). El agua y la oferta no se pueden poner favorables (no tienen motor): el agua no cuenta y la oferta no tiene datos."""
    body = diagnose(TestClient(app), NOVEMBER, priorities=NO_WATER)
    frost = body["signals"]["frost"]
    assert (frost["score"], frost["level"], frost["critical"]) == (7, "unfavorable", True)
    overall = body["overall"]
    assert (overall["light"], overall["action"], overall["high_risk"], overall["limiting_signal"]) == ("red", "other_window", True, "frost")
    # La luz de AgroSense no se puede evaluar sin el agua, pero no esconde la helada crítica.
    assert body["overall_default"]["light"] == "not_evaluable" and body["overall_default"]["high_risk"] is True
    best = body["best_windows"]
    assert [window["sowing_start"] for window in best] == ["2027-04-01", "2027-05-01", "2027-03-01"]
    assert not any(window["high_risk"] for window in best)
    assert best[0] == {
        "sowing_start": "2027-04-01",
        "harvest_estimate": "2027-09-13",
        "limiting_signal": "frost",
        "limiting_score": 100,
        "weighted_score": 100,
        "high_risk": False,
    }


def test_una_helada_critica_con_peso_0_sigue_contando(examples):
    body = diagnose(TestClient(app), NOVEMBER, priorities={**NO_WATER, "frost": 0})
    assert body["signals"]["frost"]["counts"] is True
    assert (body["overall"]["light"], body["overall"]["action"]) == ("red", "other_window")


def test_caso_de_referencia_calor_critico_da_rojo_y_ninguna_ventana_de_alto_riesgo(examples_copy):
    """HU-190: un calor crítico da rojo y `other_window`. Aquí hace 45 °C todo el año en Samacá (datos cambiados a
    propósito, R5): las doce ventanas son de alto riesgo y `best_windows` viene vacío (puede pasar: no siempre hay un buen
    mes)."""
    table = examples_copy / "climate_risk_month.parquet"
    rows = pl.read_parquet(table)
    hot = pl.when(pl.col("municipality_id") == SAMACA).then(pl.lit(45.0)).otherwise(pl.col("tmax_p90_c"))
    rows.with_columns(hot.cast(rows.schema["tmax_p90_c"]).alias("tmax_p90_c")).write_parquet(table)

    body = diagnose(TestClient(app), APRIL, priorities=NO_WATER)
    heat = body["signals"]["heat"]
    assert (heat["score"], heat["level"], heat["critical"]) == (0, "unfavorable", True)
    assert (body["overall"]["light"], body["overall"]["action"], body["overall"]["limiting_signal"]) == ("red", "other_window", "heat")
    assert body["best_windows"] == []
    # Un calor crítico cuenta aunque el agricultor le ponga peso 0 (R2).
    ignored = diagnose(TestClient(app), APRIL, priorities={**NO_WATER, "heat": 0})
    assert ignored["signals"]["heat"]["counts"] is True and ignored["overall"]["light"] == "red"


def test_con_otra_ventana_solo_en_la_luz_de_agrosense_tambien_trae_las_mejores_ventanas(examples, monkeypatch):
    """HU-074: `best_windows` viene cuando la acción de `overall` **o** de `overall_default` es `other_window`. Con los
    pesos reales de `weights.yaml` el agua pesa y, sin su motor (HU-071), la luz de AgroSense es siempre `not_evaluable`;
    para ver la rama de `overall_default`, la prueba cambia los pesos por defecto por unos con el agua en 0. Quien
    consulta pone el agua en 3: su luz es `not_evaluable`. Las ventanas se ordenan entonces con los pesos de AgroSense,
    y salen iguales a las de quien consulta con esos mismos pesos."""
    monkeypatch.setattr(calculations, "get_default_weights", lambda: SimpleNamespace(weights=NO_WATER))
    all_3 = dict.fromkeys(SIGNALS, 3)
    body = diagnose(TestClient(app), NOVEMBER, priorities=all_3)
    assert (body["overall"]["light"], body["overall"]["action"]) == ("not_evaluable", "review_data")
    assert (body["overall_default"]["light"], body["overall_default"]["action"]) == ("red", "other_window")
    same = diagnose(TestClient(app), NOVEMBER, priorities=NO_WATER)
    assert body["best_windows"] == same["best_windows"]
    assert [window["sowing_start"] for window in body["best_windows"]] == ["2027-04-01", "2027-05-01", "2027-03-01"]


# ---------- riego sin dato ----------


def test_riego_nulo_sin_lote_se_evalua_como_sin_riego_y_lo_dicen_las_limitaciones(examples):
    """Contrato (cuerpo de `/diagnostics`): `irrigated` nulo se trata como sin riego y se agrega a las limitaciones."""
    client = TestClient(app)
    assert diagnose(client)["limitations"].count(IRRIGATION_UNKNOWN) == 1
    assert diagnose(client, irrigated=None)["limitations"].count(IRRIGATION_UNKNOWN) == 1
    for value in (True, False):
        assert IRRIGATION_UNKNOWN not in diagnose(client, irrigated=value)["limitations"]


def test_riego_nulo_del_lote_lo_dicen_las_limitaciones_aunque_la_consulta_lo_diga(examples, client):
    """EP-16: con `lot_id`, el riego es el del lote; si el lote no lo dice, se evalúa como sin riego y se dice."""
    register(client, "rosa.samaca")
    unknown = create_lot(client)
    assert IRRIGATION_UNKNOWN in diagnose(client, lot_id=unknown, irrigated=True)["limitations"]
    known = create_lot(client, name="El Bajo", irrigated=False)
    assert IRRIGATION_UNKNOWN not in diagnose(client, lot_id=known)["limitations"]


# ---------- HU-192: el orden de las ventanas y el diagnóstico salen del mismo cálculo ----------


def test_una_ventana_del_orden_y_el_diagnostico_de_esa_fecha_dan_lo_mismo(examples):
    client = TestClient(app)
    best = diagnose(client, NOVEMBER, priorities=NO_WATER)["best_windows"]
    assert best
    for window in best:
        body = diagnose(client, window["sowing_start"], priorities=NO_WATER)
        overall = body["overall"]
        assert body["window"]["harvest_estimate"] == window["harvest_estimate"]
        assert (overall["limiting_signal"], overall["high_risk"]) == (window["limiting_signal"], window["high_risk"])
        assert body["signals"][window["limiting_signal"]]["score"] == window["limiting_score"]
        rated = [name for name in ("frost", "heat") if body["signals"][name]["score"] is not None]
        assert min(body["signals"][name]["score"] for name in rated) == window["limiting_score"]


# ---------- sin datos: 200, nunca un riesgo inventado ----------


def test_una_entrada_valida_sin_datos_responde_200_con_insufficient_data(dataset):
    """El dataset de las pruebas no tiene clima: ninguna señal se evalúa y la luz es `not_evaluable` (R1)."""
    body = diagnose(TestClient(app))
    for signal in body["signals"].values():
        assert (signal["status"], signal["level"], signal["score"], signal["critical"]) == ("insufficient_data", None, None, False)
    assert (body["overall"]["light"], body["overall"]["action"]) == ("not_evaluable", "review_data")
    for name in ("el agua", "la helada", "el calor", "el suelo", "la oferta", "el mercado"):
        assert f"Sin datos para la zona: {name} no se evaluó." in body["limitations"]


def test_sin_las_etapas_del_cultivo_no_hay_ventana_y_nada_se_inventa(examples_copy):
    """Un dataset sin `crop_stages`: no hay ventana (`window` nulo), ninguna señal se califica y, con el agua en 0, la luz
    es amarilla sin evidencia (regla 3) y no hay ventanas que recomendar."""
    (examples_copy / "crop_stages.parquet").unlink()
    body = diagnose(TestClient(app), priorities=NO_WATER)
    assert body["window"] is None
    assert all(signal["status"] == "insufficient_data" for signal in body["signals"].values())
    assert body["signals"]["frost"]["reasons"] == ["Sin las etapas de la papa: la señal no se evalúa"]
    assert (body["overall"]["light"], body["overall"]["action"]) == ("yellow", "other_window")
    assert body["best_windows"] == []


# ---------- entradas inválidas ----------


@pytest.mark.parametrize(
    "change",
    [
        {"sowing_date": "2026-13-01"},
        {"sowing_date": "mañana"},
        {"priorities": {**NO_WATER, "frost": 6}},
        {"priorities": {**NO_WATER, "frost": -1}},
        {"priorities": {"water": 3}},
        {"irrigated": "a veces"},
    ],
)
def test_una_entrada_mal_formada_responde_422(examples, change):
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL, **change}
    response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 422, response.json()
    assert response.json()["error"]["code"] == "invalid_input"


# ---------- R4 y R9 ----------


def test_dos_consultas_iguales_dan_lo_mismo(examples):
    client = TestClient(app)
    first = client.post(
        "/api/v1/diagnostics", json={"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": NOVEMBER, "priorities": NO_WATER}
    )
    again = client.post(
        "/api/v1/diagnostics", json={"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": NOVEMBER, "priorities": NO_WATER}
    )
    assert first.content == again.content


def rows(db) -> dict[str, int]:
    return {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}


def register(client, username: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "papaya-criolla-2026",
            "display_name": "Rosa",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    assert response.status_code == 201, response.json()


def create_lot(client, **extra) -> str:
    response = client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": SAMACA, "area_ha": 1.0, **extra})
    assert response.status_code == 201, response.json()
    return response.json()["lot_id"]


def test_el_diagnostico_no_escribe_en_la_base_ni_registra_la_consulta(examples, client, db):
    """R9: ninguna tabla de las cuentas cambia, con o sin lote; ni el cuerpo ni las prioridades van al log."""
    register(client, "rosa.samaca")
    lot_id = create_lot(client)
    before = rows(db)
    with capture_logs() as logs:
        diagnose(client, NOVEMBER, priorities=NO_WATER)
        diagnose(client, NOVEMBER, priorities=NO_WATER, lot_id=lot_id)
    assert rows(db) == before
    text = str([{key: value for key, value in entry.items() if key != "request_id"} for entry in logs])
    for value in (SAMACA, "papa", NOVEMBER, lot_id, "priorities", "weights_basis", "El Alto"):
        assert value not in text, value


# ---------- el lote ----------


def test_con_lote_el_riego_es_el_del_lote(examples, client):
    register(client, "rosa.samaca")
    with_irrigation = create_lot(client, irrigated=True)
    assert diagnose(client, lot_id=with_irrigation, irrigated=False)["request"]["irrigated"] is True
    # Si el lote no lo dice («todavía no sé»), sigue siendo el del lote: nulo, que se evalúa como sin riego (EP-16).
    unknown = create_lot(client, name="El Bajo")
    assert diagnose(client, lot_id=unknown, irrigated=True)["request"]["irrigated"] is None
    # Sin lote, el de la consulta.
    assert diagnose(client, irrigated=True)["request"]["irrigated"] is True


def test_con_lote_inexistente_o_ajeno_responde_404(examples, client):
    register(client, "rosa.samaca")
    lot_id = create_lot(client)
    assert client.post("/api/v1/auth/logout").status_code == 204
    register(client, "fabio.samaca")
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL}
    for other in (lot_id, "00000000-0000-4000-8000-000000000001"):
        response = client.post("/api/v1/diagnostics", json={**body, "lot_id": other})
        assert response.status_code == 404, response.json()
        assert response.json()["error"]["code"] == "not_found"
