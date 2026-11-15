"""HU-076: `POST /api/v1/diagnostics` con el motor (HU-074, HU-077, HU-190, HU-073, HU-191, HU-192).

Usa el dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá (12,8 °C) con heladas y
calor de ejemplo. «Hoy» queda fijo en el 14 de noviembre de 2026 en la región, para que las ventanas no dependan del día
en que corre la prueba (R4). En esos datos, la papa sembrada en noviembre tiene helada crítica (7 de 100) y la de abril
no tiene heladas (100); el calor da 100 en todo el año.

La oferta (HU-072) todavía no tiene motor: es `insufficient_data`. El suelo (HU-183) sí: el del ejemplo (pH 5,5, de 5,1 a
5,9) le da 100 a la papa (sus pruebas están en `tests/test_senal_suelo_datos.py`). El agua (HU-071) también (sus
pruebas están en `tests/test_senal_agua_datos.py`), pero las filas de lluvia del ejemplo están rotuladas `ejemplo` y no
cuentan como de ninguna fuente (`monthly_climate.rain_rows`): aquí el agua es `insufficient_data`. Con los pesos por
defecto el agua pesa 3, así que la luz de AgroSense es `not_evaluable` (regla 1): es lo honesto (R1). Para ver una luz
roja o verde, las pruebas ponen el agua en 0 con `priorities`.
"""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from structlog.testing import capture_logs

from backend.accounts.models import Session as AccountSession
from backend.api import calc_models as m
from backend.api import calculations, window_signals
from backend.api.auth import SESSION_COOKIE
from backend.api.climate_signals import frost_caveat
from backend.api.main import app
from backend.api.window_signals import pending_reason
from backend.config.settings import get_settings
from backend.config.weights import get_default_weights
from backend.dataset import get_dataset
from backend.db.models import Base
from backend.engine.diagnosis import IRRIGATION_UNKNOWN
from backend.engine.water_signal import WaterBalanceSummary
from common import region
from tests.ejemplos_con_fuente import examples_with_sources

EXAMPLES = Path("data/examples")
SAMACA = "15646"
SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
# 14 de noviembre de 2026 al mediodía en Bogotá.
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
NOVEMBER, APRIL = "2026-11-01", "2027-04-01"
# El agua en 0: con la lluvia del ejemplo sin fuente, con peso la luz sería siempre `not_evaluable`.
NO_WATER = {"water": 0, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
# Un balance hídrico DE EJEMPLO (R5): el cultivo pide 400 mm y la lluvia del año seco los cubre.
NO_DEFICIT = WaterBalanceSummary(need_mm=400.0, dry_deficit_mm=(0.0, 0.0), retention=True)
# Las señales que todavía no tienen motor (el agua ya lo tiene desde HU-071 y el suelo desde HU-183).
PENDING = {name: pending_reason(name) for name in ("supply",)}


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
    # El agua tiene motor (HU-071), pero la lluvia del ejemplo está rotulada `ejemplo` y no es de ninguna fuente: no se
    # califica, y no es la razón de una señal sin motor.
    water = body["signals"]["water"]
    assert (water["status"], water["level"], water["score"], water["critical"]) == ("insufficient_data", None, None, False)
    assert water["reasons"] != [pending_reason("water")]
    assert body["versions"] == {"dataset": "ejemplo", "rules": "0.1.0+umbrales.1.0.0+pesos.1.0.0"}


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
    assert "Sin datos para la zona: el mercado no se evaluó." in limitations
    # Las que no tienen motor dicen lo verdadero: no faltan datos, falta el motor (R5).
    for reason in PENDING.values():
        assert limitations.count(reason) == 1
    assert pending_reason("water") not in limitations
    # El agua dice qué le falta (la lluvia rotulada con su fuente o el balance hídrico), no la frase genérica (R5).
    assert "Sin datos para la zona: el agua no se evaluó." not in limitations
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
    (R2). Usa `NO_WATER` y los datos de ejemplo, sin dobles: el agua no cuenta y la oferta no tiene datos. El caso con el
    agua y la oferta favorables va más abajo."""
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


def with_favorable_water_and_supply(monkeypatch, folder: Path) -> None:
    """El agua y la oferta favorables, para los casos de referencia de HU-077 y HU-190. El agua pasa por el motor real
    (el balance hídrico de HU-144 y la señal de HU-071): en Samacá la lluvia del ejemplo se cambia a 200 mm al mes, en
    el año normal y en el seco (cifras DE EJEMPLO, R5), y la lluvia efectiva cubre lo que pide el cultivo. La oferta sale
    de una señal DE EJEMPLO, porque todavía no tiene curva ni motor (HU-072). Las heladas y el calor son los del dataset."""
    table = folder / "precip_month.parquet"
    rows = pl.read_parquet(table)
    rainy = pl.when(pl.col("municipality_id") == SAMACA).then(pl.lit(200.0))
    rows.with_columns(rainy.otherwise(pl.col(name)).alias(name) for name in ("precip_normal_mm", "precip_dry_mm")).write_parquet(table)
    use(monkeypatch, folder)
    favorable_supply = window_signals.PendingSignal("available", "favorable", False, 90, (), ("Oferta DE EJEMPLO, favorable",))
    real = window_signals.pending_signal
    monkeypatch.setattr(window_signals, "pending_signal", lambda name: favorable_supply if name == "supply" else real(name))


def test_caso_de_referencia_helada_critica_con_agua_y_oferta_favorables_da_rojo_y_otra_ventana(tmp_path, monkeypatch):
    """HU-077, caso de referencia: con el agua y la oferta favorables y los pesos de AgroSense, la helada crítica de
    noviembre (los datos de ejemplo) da rojo y `other_window` en el diagnóstico completo (R2)."""
    with_favorable_water_and_supply(monkeypatch, examples_with_sources(tmp_path / "ejemplos"))
    body = diagnose(TestClient(app), NOVEMBER)
    signals = body["signals"]
    assert (signals["water"]["level"], signals["supply"]["level"]) == ("favorable", "favorable")
    assert (signals["frost"]["level"], signals["frost"]["critical"]) == ("unfavorable", True)
    light = body["overall_default"]
    assert (light["light"], light["action"], light["limiting_signal"], light["high_risk"]) == ("red", "other_window", "frost", True)
    assert body["best_windows"] and not any(window["high_risk"] for window in body["best_windows"])


def test_caso_de_referencia_calor_critico_con_agua_y_oferta_favorables_da_rojo_y_otra_ventana(tmp_path, monkeypatch):
    """HU-190, caso de referencia: con el agua y la oferta favorables y los pesos de AgroSense, un calor crítico (45 °C
    todo el año en Samacá, datos cambiados a propósito, R5) da rojo y `other_window` en el diagnóstico completo (R2). Se
    siembra en abril, cuando la helada del ejemplo es favorable, para que el calor sea el único riesgo."""
    folder = examples_with_sources(tmp_path / "ejemplos")
    table = folder / "climate_risk_month.parquet"
    rows = pl.read_parquet(table)
    hot = pl.when(pl.col("municipality_id") == SAMACA).then(pl.lit(45.0)).otherwise(pl.col("tmax_p90_c"))
    rows.with_columns(hot.cast(rows.schema["tmax_p90_c"]).alias("tmax_p90_c")).write_parquet(table)
    with_favorable_water_and_supply(monkeypatch, folder)
    body = diagnose(TestClient(app), APRIL)
    signals = body["signals"]
    assert (signals["water"]["level"], signals["supply"]["level"], signals["frost"]["level"]) == ("favorable", "favorable", "favorable")
    assert (signals["heat"]["level"], signals["heat"]["critical"]) == ("unfavorable", True)
    light = body["overall_default"]
    assert (light["light"], light["action"], light["limiting_signal"], light["high_risk"]) == ("red", "other_window", "heat", True)
    # Con 45 °C todo el año, todas las ventanas son de alto riesgo: ninguna entra entre las mejores (R2).
    assert body["best_windows"] == []


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
    """HU-074: `best_windows` viene cuando la acción de `overall` **o** de `overall_default` es `other_window`. Con la
    lluvia del ejemplo sin fuente el agua es `insufficient_data`, y con los pesos reales de `weights.yaml` el agua pesa:
    la luz de AgroSense sería `not_evaluable`. Para ver la rama de `overall_default`, la prueba cambia los pesos por
    defecto por unos con el agua en 0. Quien consulta pone el agua en 3: su luz es `not_evaluable`. Las ventanas se
    ordenan entonces con los pesos de AgroSense, y salen iguales a las de quien consulta con esos mismos pesos."""
    monkeypatch.setattr(calculations, "get_default_weights", lambda: SimpleNamespace(weights=NO_WATER))
    all_3 = dict.fromkeys(SIGNALS, 3)
    body = diagnose(TestClient(app), NOVEMBER, priorities=all_3)
    assert (body["overall"]["light"], body["overall"]["action"]) == ("not_evaluable", "review_data")
    assert (body["overall_default"]["light"], body["overall_default"]["action"]) == ("red", "other_window")
    same = diagnose(TestClient(app), NOVEMBER, priorities=NO_WATER)
    assert body["best_windows"] == same["best_windows"]
    assert [window["sowing_start"] for window in body["best_windows"]] == ["2027-04-01", "2027-05-01", "2027-03-01"]


def test_sin_prioridades_las_mejores_ventanas_se_ordenan_con_los_pesos_por_defecto(tmp_path, monkeypatch):
    """HU-192: sin `priorities`, el orden de las ventanas usa los pesos de `weights.yaml`, y los pesos sí cambian el
    orden. Con la lluvia del ejemplo rotulada con su fuente y un balance DE EJEMPLO fijo (R5), el agua es favorable en
    todas las ventanas: el orden lo deciden las heladas, críticas en noviembre en los datos de ejemplo."""
    use(monkeypatch, examples_with_sources(tmp_path / "ejemplos"))
    monkeypatch.setattr(window_signals, "balance_for", lambda *args, **kwargs: NO_DEFICIT)
    client = TestClient(app)
    defaults = get_default_weights().weights

    body = diagnose(client, NOVEMBER)
    assert (body["weights"], body["overall_default"]["weights_basis"]) == (defaults, "default")
    assert body["overall_default"]["action"] == "other_window"
    # Lo mismo que si quien consulta mandara esos mismos pesos: el orden es el de los pesos por defecto.
    assert body["best_windows"] == diagnose(client, NOVEMBER, priorities=defaults)["best_windows"]
    assert [window["sowing_start"] for window in body["best_windows"]] == ["2027-04-01", "2027-05-01", "2027-03-01"]
    # Sin peso en la helada (que solo cuenta donde es crítica), las tres ventanas empatan y gana la más temprana (R4).
    no_frost = diagnose(client, NOVEMBER, priorities={**defaults, "frost": 0})
    assert [window["sowing_start"] for window in no_frost["best_windows"]] == ["2027-03-01", "2027-04-01", "2027-05-01"]


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
        rated = [name for name in ("frost", "heat", "soil") if body["signals"][name]["score"] is not None]
        assert min(body["signals"][name]["score"] for name in rated) == window["limiting_score"]


# ---------- sin datos: 200, nunca un riesgo inventado ----------


def test_una_entrada_valida_sin_datos_responde_200_con_insufficient_data(dataset):
    """El dataset de las pruebas no tiene clima: ninguna señal se evalúa y la luz es `not_evaluable` (R1)."""
    body = diagnose(TestClient(app))
    for signal in body["signals"].values():
        assert (signal["status"], signal["level"], signal["score"], signal["critical"]) == ("insufficient_data", None, None, False)
    assert (body["overall"]["light"], body["overall"]["action"]) == ("not_evaluable", "review_data")
    for name in ("la helada", "el calor", "el mercado"):
        assert f"Sin datos para la zona: {name} no se evaluó." in body["limitations"]
    for name in ("el suelo", "la oferta"):
        assert f"Sin datos para la zona: {name} no se evaluó." not in body["limitations"]
    assert pending_reason("water") not in body["limitations"]
    for reason in PENDING.values():
        assert body["limitations"].count(reason) == 1


def test_sin_las_etapas_del_cultivo_no_hay_ventana_y_nada_se_inventa(examples_copy):
    """Un dataset sin `crop_stages`: no hay ventana (`window` nulo), ninguna señal se califica y, con el agua en 0, la luz
    es amarilla sin evidencia (regla 3) y no hay ventanas que recomendar."""
    (examples_copy / "crop_stages.parquet").unlink()
    body = diagnose(TestClient(app), priorities=NO_WATER)
    assert body["window"] is None
    assert all(signal["status"] == "insufficient_data" for signal in body["signals"].values())
    assert body["signals"]["frost"]["reasons"] == ["Sin las etapas de la papa: la señal no se evalúa"]
    # El suelo no cambia con la fecha, pero sin ventana tampoco se califica (HU-076; HU-183): la misma razón.
    assert body["signals"]["soil"]["reasons"] == ["Sin las etapas de la papa: la señal no se evalúa"]
    assert (body["signals"]["soil"]["level"], body["signals"]["soil"]["score"]) == (None, None)
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


def dump(db) -> dict[str, list[tuple]]:
    """Todo el contenido de cada tabla, con las filas ordenadas por clave primaria: un UPDATE también cambia el volcado."""
    db.rollback()
    return {
        table.name: [tuple(row) for row in db.execute(select(table).order_by(*table.primary_key.columns)).all()]
        for table in Base.metadata.sorted_tables
    }


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
    before, content_before = rows(db), dump(db)
    with capture_logs() as logs:
        diagnose(client, NOVEMBER, priorities=NO_WATER)
        assert dump(db) == content_before
        diagnose(client, NOVEMBER, priorities=NO_WATER, lot_id=lot_id)
    assert rows(db) == before
    assert dump(db) == content_before
    text = str([{key: value for key, value in entry.items() if key != "request_id"} for entry in logs])
    for value in (SAMACA, "papa", NOVEMBER, lot_id, "priorities", "weights_basis", "El Alto"):
        assert value not in text, value


def test_el_log_del_diagnostico_no_dice_quien_consulto_aunque_haya_sesion(examples, client):
    """R9: con sesión y lote, la línea del diagnóstico lleva las versiones (R4), pero no `user_id` ni `role`."""
    register(client, "rosa.samaca")
    with capture_logs() as logs:
        lot_id = create_lot(client)
        diagnose(client, NOVEMBER, lot_id=lot_id)
    requests = {entry["route"]: entry for entry in logs if entry.get("event") == "request"}
    # La sesión existe: la línea de crear el lote sí dice quién fue.
    assert "user_id" in requests["/api/v1/lots"]
    line = requests["/api/v1/diagnostics"]
    assert {"dataset", "rules"} <= line.keys()
    assert "user_id" not in line and "role" not in line


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


def without_request_id(response) -> dict:
    body = response.json()
    body["error"] = {key: value for key, value in body["error"].items() if key != "request_id"}
    return body


def diagnose_lot(client, lot_id: str):
    return client.post("/api/v1/diagnostics", json={"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL, "lot_id": lot_id})


def test_el_404_de_un_lote_ajeno_es_igual_al_de_uno_inexistente(examples, client):
    register(client, "rosa.samaca")
    lot_id = create_lot(client)
    assert client.post("/api/v1/auth/logout").status_code == 204
    register(client, "fabio.samaca")
    foreign = diagnose_lot(client, lot_id)
    missing = diagnose_lot(client, "00000000-0000-4000-8000-000000000001")
    assert foreign.status_code == missing.status_code == 404
    assert without_request_id(foreign) == without_request_id(missing)
    assert lot_id not in foreign.text and "El Alto" not in foreign.text


def test_un_lote_borrado_responde_el_mismo_404_que_uno_inexistente(examples, client):
    register(client, "rosa.samaca")
    lot_id = create_lot(client)
    assert diagnose_lot(client, lot_id).status_code == 200
    assert client.delete(f"/api/v1/lots/{lot_id}").status_code == 204
    deleted = diagnose_lot(client, lot_id)
    missing = diagnose_lot(client, "00000000-0000-4000-8000-000000000001")
    assert deleted.status_code == missing.status_code == 404
    assert without_request_id(deleted) == without_request_id(missing)
    assert lot_id not in deleted.text


def test_con_cookie_inventada_o_sesion_vencida_responde_401_sin_nada_del_lote(examples, client, db):
    register(client, "rosa.samaca")
    lot_id = create_lot(client)
    real_cookie = client.cookies.get(SESSION_COOKIE)
    assert real_cookie
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, "token-inventado-que-no-existe")
    forged = diagnose_lot(client, lot_id)
    assert forged.status_code == 401
    assert lot_id not in forged.text and "El Alto" not in forged.text

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, real_cookie)
    assert diagnose_lot(client, lot_id).status_code == 200
    db.execute(update(AccountSession).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
    db.commit()
    expired = diagnose_lot(client, lot_id)
    assert expired.status_code == 401
    assert lot_id not in expired.text and "El Alto" not in expired.text
    assert without_request_id(expired)["error"]["code"] == without_request_id(forged)["error"]["code"]
