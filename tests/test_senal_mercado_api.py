"""HU-073 (decisión 17): la señal de mercado en `/diagnostics`, sin calificar, con `price_history` y la central por
cultivo; y HU-241: el ingreso de las estrategias en `/rotations` sale de esa misma historia.

Usa una copia del dataset de ejemplo (`data/examples/`, rotulado como ejemplo, R5): `market_month` solo trae Corabastos
(`1`) y el manifiesto manda Boyacá a Tunja (`9`) y la papa de Boyacá a Corabastos (`crop_market_overrides`). Samacá es de
Boyacá. Las cifras de precios son de ejemplo.
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api import calc_models as m
from backend.api.main import app
from backend.config.settings import get_settings
from backend.engine.market_signal import NO_COUNT_REASON, NO_DATA_REASON, UNRATED_LIMITATION, UNRATED_REASON
from common import region

EXAMPLES = Path("data/examples")
SAMACA = "15646"
APRIL = "2027-04-01"
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
NO_WATER = {"water": 0, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 5}
OVERRIDE_REASON = "Tunja no publica papa negra desde el 27 de julio de 2021; su temporada es casi la de Corabastos"


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return TODAY.astimezone(tz) if tz else TODAY

    monkeypatch.setattr(region, "datetime", Clock)


@pytest.fixture
def folder(tmp_path, monkeypatch):
    copy = tmp_path / "ejemplos"
    shutil.copytree(EXAMPLES, copy)
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(copy.resolve()))
    get_settings.cache_clear()
    return copy


def change_month(folder: Path, change) -> None:
    path = folder / "market_month.parquet"
    change(pl.read_parquet(path)).write_parquet(path)
    get_settings.cache_clear()


def change_manifest(folder: Path, change) -> None:
    path = folder / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    change(manifest)
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    get_settings.cache_clear()


def diagnose(crop_id: str = "papa", **extra) -> dict:
    body = {"municipality_id": SAMACA, "crop_id": crop_id, "sowing_date": APRIL, "priorities": NO_WATER, **extra}
    response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    m.DiagnosisResponse.model_validate(response.json())
    return response.json()


def month_row(folder: Path, crop_id: str, market_id: str, month: int) -> dict:
    table = pl.read_parquet(folder / "market_month.parquet")
    return table.filter((pl.col("crop_id") == crop_id) & (pl.col("market_id") == market_id) & (pl.col("month") == month)).row(0, named=True)


def test_la_papa_de_boyaca_usa_corabastos_sin_calificar_y_lo_dice(folder):
    body = diagnose()
    market = body["signals"]["market"]
    month = int(body["window"]["harvest_estimate"][5:7])
    row = month_row(folder, "papa", "1", month)
    assert (market["status"], market["level"], market["score"], market["critical"]) == ("available", None, None, False)
    assert market["indicators"] == ["seasonal_index", "years_above", "years_below"]
    assert market["price_history"] == {
        "market_id": "1",
        "market": "Corabastos (Bogotá)",
        "market_basis": "crop_override",
        "product_id": "papa-negra",
        "month": month,
        "seasonal_index": row["seasonal_index"],
        "years": row["years"],
        "years_above": row["years_above"],
        "years_below": row["years_below"],
        "first_year": row["first_year"],
        "last_year": row["last_year"],
        "source_id": row["source_id"],
    }
    unrated, override, history = market["reasons"]
    assert unrated == UNRATED_REASON
    assert override == f"Se usa la central de Corabastos (Bogotá): {OVERRIDE_REASON}"
    assert history.startswith("En Corabastos, en septiembre (el mes en que saldría su cosecha), el precio de la papa")
    assert f"en {row['years_above']} de {row['years']} años ({row['first_year']}–{row['last_year']})" in history
    assert history.endswith("Así fue en la historia: no es un pronóstico del precio. Fuente: DANE")
    assert UNRATED_LIMITATION in body["limitations"]
    # Las demás señales no traen historia del precio.
    assert all(body["signals"][name]["price_history"] is None for name in ("water", "frost", "heat", "soil", "supply"))


def test_la_arveja_de_boyaca_usa_tunja(folder):
    change_month(folder, lambda t: pl.concat([t, t.filter(pl.col("crop_id") == "arveja").with_columns(pl.lit("9").alias("market_id"))]))
    history = diagnose("arveja")["signals"]["market"]["price_history"]
    assert (history["market_id"], history["market"], history["market_basis"]) == (
        "9",
        "Tunja (Complejo de Servicios del Sur)",
        "department",
    )


def test_si_tunja_publica_la_papa_se_usa_tunja_y_no_corabastos(folder):
    """La central por cultivo solo vale cuando la del departamento no tiene filas del cultivo."""
    change_month(folder, lambda t: pl.concat([t, t.filter(pl.col("crop_id") == "papa").with_columns(pl.lit("9").alias("market_id"))]))
    market = diagnose()["signals"]["market"]
    assert (market["price_history"]["market_id"], market["price_history"]["market_basis"]) == ("9", "department")
    assert len(market["reasons"]) == 2


def test_sin_central_por_cultivo_la_papa_de_boyaca_no_tiene_mercado(folder):
    """Nunca otra central por defecto (R1)."""
    change_manifest(folder, lambda manifest: manifest["region"].pop("crop_market_overrides"))
    market = diagnose()["signals"]["market"]
    assert (market["status"], market["level"], market["price_history"], market["reasons"]) == (
        "insufficient_data",
        None,
        None,
        [NO_DATA_REASON],
    )


def test_un_cultivo_sin_producto_no_tiene_mercado(folder):
    market = diagnose("haba")["signals"]["market"]
    assert (market["status"], market["price_history"]) == ("insufficient_data", None)


def test_un_dataset_sin_los_anos_contados_no_inventa_y_lo_dice(folder):
    """Un `market_month` publicado antes de HU-073: la señal no se muestra y la limitación lo dice (R1)."""
    change_month(folder, lambda t: t.drop("years_above", "years_below", "first_year", "last_year"))
    body = diagnose()
    market = body["signals"]["market"]
    assert (market["status"], market["level"], market["score"], market["price_history"]) == ("insufficient_data", None, None, None)
    assert market["reasons"] == [NO_COUNT_REASON]
    assert NO_COUNT_REASON in body["limitations"]


@pytest.mark.parametrize("priorities", [NO_WATER, {**NO_WATER, "market": 0}, {**NO_WATER, "market": 1}, None])
@pytest.mark.parametrize("sowing_date", [APRIL, "2026-11-01"])
def test_con_mercado_la_luz_la_accion_y_el_factor_limitante_son_los_mismos_que_sin_el(folder, monkeypatch, priorities, sowing_date):
    extra = {"sowing_date": sowing_date, "priorities": priorities}
    with_market = diagnose(**extra)
    assert with_market["signals"]["market"]["status"] == "available"
    # Otra carpeta: el dataset se guarda en memoria por carpeta.
    other = folder.parent / "sin-mercado"
    shutil.copytree(folder, other)
    (other / "market_month.parquet").unlink()
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(other.resolve()))
    get_settings.cache_clear()
    without = diagnose(**extra)
    assert without["signals"]["market"]["status"] == "insufficient_data"
    for light in ("overall", "overall_default"):
        assert {k: v for k, v in with_market[light].items() if k != "reasons"} == {
            k: v for k, v in without[light].items() if k != "reasons"
        }
    assert with_market.get("best_windows") == without.get("best_windows")


def test_la_misma_consulta_da_la_misma_respuesta(folder):
    """R4."""
    assert diagnose() == diagnose()


# ---------- HU-241: el ingreso de las estrategias ----------


def rotations(**extra) -> dict:
    body = {
        "municipality_id": SAMACA,
        "sowing_date": APRIL,
        "previous_crop_ids": ["haba"],
        "current_crop_ids": ["papa", "papa"],
        "cycles": 2,
        "priorities": {"water": 3, "soil": 3, "income": 3, "risk": 3},
        "signal_priorities": {"water": 0, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3},
        **extra,
    }
    response = TestClient(app).post("/api/v1/rotations", json=body)
    assert response.status_code == 200, response.json()
    return response.json()


def cycle_share(cycle: dict) -> float | None:
    signals = (cycle["diagnosis"] or {}).get("signals") or {}
    history = (signals.get("market") or {}).get("price_history")
    return None if history is None else 100 * history["years_above"] / history["years"]


def expected_income(strategy: dict, kinds: dict[str, str]) -> int | None:
    # El descanso y el abono verde valen 0 siempre; un cultivo sin historia no cuenta (decidido por Felipe el 15 nov 2026).
    values = []
    for cycle in strategy["cycles"]:
        if kinds[cycle["crop_id"]] != "crop":
            values.append(0)
            continue
        share = cycle_share(cycle)
        if share is not None:
            values.append(share)
    if not values:
        return None
    mean = sum(values) / len(values)
    return int(mean + 0.5)


def test_el_ingreso_de_cada_estrategia_sale_de_la_historia_del_precio_de_sus_ciclos(folder):
    body = rotations()
    kinds = {row["crop_id"]: row["kind"] for row in pl.read_parquet(folder / "crops.parquet").select("crop_id", "kind").to_dicts()}
    strategies = [*body["strategies"], body["current_strategy"]]
    assert any(s["scores"]["income"] is not None for s in strategies)
    for strategy in strategies:
        assert strategy["scores"]["income"] == expected_income(strategy, kinds), strategy["crop_ids"]


def test_la_rotacion_actual_de_papa_tiene_ingreso_y_vs_current_lo_compara(folder):
    body = rotations()
    current = body["current_strategy"]
    assert current["scores"]["income"] is not None
    for strategy in body["strategies"]:
        if strategy["scores"]["income"] is not None:
            assert strategy["vs_current"]["income"] == strategy["scores"]["income"] - current["scores"]["income"]
