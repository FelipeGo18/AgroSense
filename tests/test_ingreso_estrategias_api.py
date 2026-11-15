"""HU-241 (decisión 17): el ingreso de las estrategias en `/rotations` sale de la historia del precio del mes de la cosecha
de cada ciclo, la misma de `signals.market.price_history` de su diagnóstico (HU-073).

Con el dataset publicado (`data/published/`, el de la demo) en Duitama, donde la haba y el maíz no tienen producto en
SIPSA y la papa, la cebolla y la zanahoria sí. Las decisiones de Felipe del 15 nov 2026: el abono verde y el descanso
valen 0 siempre; un cultivo sin historia no cuenta y se dice; una estrategia solo de cultivos sin historia queda sin
ingreso, se compara con los otros criterios y lo dice.
"""

from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.settings import get_settings
from backend.engine.rotations.ranking import NO_CRITERION

PUBLISHED = Path(__file__).resolve().parents[1] / "data" / "published"
DUITAMA = "15238"
NO_HISTORY = "historia del precio del mes de su cosecha"


@pytest.fixture
def published(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(PUBLISHED))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def kinds() -> dict[str, str]:
    rows = pl.read_parquet(PUBLISHED / "crops.parquet").select("crop_id", "kind").to_dicts()
    return {row["crop_id"]: row["kind"] for row in rows}


def rotations(**extra) -> dict:
    body = {
        "municipality_id": DUITAMA,
        "sowing_date": "2026-12-07",
        "previous_crop_ids": ["papa"],
        "current_crop_ids": ["papa", "papa"],
        "cycles": 3,
        "priorities": {"water": 3, "soil": 3, "income": 3, "risk": 3},
        **extra,
    }
    response = TestClient(app).post("/api/v1/rotations", json=body)
    assert response.status_code == 200, response.json()
    return response.json()


def cycle_share(cycle: dict) -> float | None:
    """100 × `years_above` / `years` del `price_history` del ciclo, sin redondear (los empates no cuentan)."""
    signals = (cycle["diagnosis"] or {}).get("signals") or {}
    history = (signals.get("market") or {}).get("price_history")
    return None if history is None else 100 * history["years_above"] / history["years"]


def expected_income(strategy: dict, kinds: dict[str, str]) -> int | None:
    values = []
    for cycle in strategy["cycles"]:
        if kinds[cycle["crop_id"]] != "crop":
            values.append(0)  # el abono verde y el descanso no dejan cosecha: 0 siempre
        elif (share := cycle_share(cycle)) is not None:
            values.append(share)
    return None if not values else int(sum(values) / len(values) + 0.5)


def test_el_ingreso_de_cada_estrategia_sale_de_la_historia_del_precio_de_sus_ciclos(published, kinds):
    body = rotations()
    strategies = [*body["strategies"], body["current_strategy"]]
    assert any(s["scores"]["income"] is not None for s in strategies)
    for strategy in strategies:
        assert strategy["scores"]["income"] == expected_income(strategy, kinds), strategy["crop_ids"]
        for number, cycle in enumerate(strategy["cycles"], start=1):
            if kinds[cycle["crop_id"]] == "crop" and cycle_share(cycle) is None:
                text = f"El ciclo {number} no tiene {NO_HISTORY}: no cuenta en ese criterio"
                # Con ingreso se dice qué ciclo no cuenta; sin ninguno, solo la limitación general (Felipe, 15 nov 2026).
                if strategy["scores"]["income"] is None:
                    assert text not in strategy["limitations"], strategy["crop_ids"]
                else:
                    assert text in strategy["limitations"], strategy["crop_ids"]


def test_una_estrategia_de_cultivos_sin_historia_queda_sin_ingreso_y_lo_dice(published):
    """Haba → maíz → haba: ningún cultivo tiene producto en SIPSA. Se acepta y se dice (Felipe, 15 nov 2026)."""
    body = rotations()
    found = {tuple(s["crop_ids"]): s for s in body["strategies"]}
    strategy = found[("haba", "maiz", "haba")]
    assert strategy["scores"]["income"] is None
    assert strategy["total_score"] is not None  # se compara con el agua, el suelo y el riesgo
    assert NO_CRITERION["income"] == "Sus cultivos no tienen historia de precio: el ingreso no cuenta en su total"
    assert NO_CRITERION["income"] in strategy["limitations"]
    assert strategy["vs_current"]["income"] is None
    assert 2 <= len(strategy["reasons"]) <= 4


def test_el_descanso_vale_cero_aunque_ningun_cultivo_tenga_historia(published):
    """Descanso → haba → descanso: la haba no tiene historia y no cuenta, pero el descanso vale 0 siempre (que no deja
    cosecha no depende de los precios): el ingreso es 0, no nulo. Se pide como rotación actual, que se evalúa igual."""
    current = rotations(current_crop_ids=["descanso", "haba"])["current_strategy"]
    assert current["crop_ids"] == ["descanso", "haba", "descanso"]
    assert current["scores"]["income"] == 0
    assert f"El ciclo 2 no tiene {NO_HISTORY}: no cuenta en ese criterio" in current["limitations"]
    assert NO_CRITERION["income"] not in current["limitations"]


def test_la_rotacion_actual_de_papa_tiene_ingreso_y_vs_current_lo_compara(published):
    body = rotations()
    current = body["current_strategy"]
    assert current["scores"]["income"] is not None
    for strategy in body["strategies"]:
        assert 2 <= len(strategy["reasons"]) <= 4
        if strategy["scores"]["income"] is not None:
            assert strategy["vs_current"]["income"] == strategy["scores"]["income"] - current["scores"]["income"]
