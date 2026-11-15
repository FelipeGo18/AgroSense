"""Comprobación de HU-217 con la publicación real de HU-216, sin HTTP ni DB."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest
import yaml
from fastapi.testclient import TestClient

from backend.api import calculations
from backend.api.calc_models import ChangesResponse
from backend.api.main import app
from backend.api.market_signal import market_for, seasonal_index
from backend.api.soil_signals import zone_soil_ph
from backend.api.window_signals import pending_signal
from backend.config.thresholds import load_thresholds
from backend.config.weights import load_weights
from backend.dataset import load
from backend.engine.change_windows import ChangeConfig, compare_historical_changes
from backend.engine.changes import Period, PeriodPair
from backend.engine.market_signal import market_signal
from backend.engine.stages import monthly_sowing_windows
from backend.engine.suitability import ZoneTemperatureUsed
from common.signal_sources import get_signal_sources

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not (ROOT / "data/published/climate_change_month.parquet").exists(), reason="Sin publicación de HU-216 en este checkout"
)
def test_hu216_published_data_reaches_motor_and_http_endpoint(monkeypatch):
    dataset = load(ROOT / "data/published")
    municipality_id, crop_id = "15238", "papa"
    municipality, crop = dataset.municipalities[municipality_id], dataset.crops[crop_id]
    thresholds = load_thresholds()
    sources = get_signal_sources().for_region(dataset.region["id"])
    region = yaml.safe_load((ROOT / "pipeline/region.yaml").read_text(encoding="utf-8"))

    def pair(source_id):
        periods = sorted((Period(**p) for p in dataset.periods if p["source_id"] == source_id), key=lambda p: p.start_year)
        return PeriodPair(*periods)

    periods, rain = pair(sources["frost"].used), pair(sources["water"].used)
    config = ChangeConfig(
        region["change_periods"]["min_year_share"],
        region["climate_normal"]["dry_quantile"],
        sources["water"].et0,
        sources["frost"].used,
        thresholds,
        load_weights().weights,
        sources["frost"].caveat,
        sources["water"].caveat,
    )
    fixed = {}
    for window in monthly_sowing_windows(dataset.stages[crop_id], date(periods.before.start_year, 1, 1)):
        index, years = seasonal_index(dataset, crop_id, market_for(dataset, municipality), window.harvest_estimate.month)
        fixed[window.sowing_date.month] = {"supply": pending_signal("supply"), "market": market_signal(index, years, thresholds)}

    def rows(table):
        return [] if table is None else table.filter(pl.col("municipality_id") == municipality_id).to_dicts()

    result = compare_historical_changes(
        municipality_id=municipality_id,
        change_rows=rows(dataset.climate_change_month),
        climate_rows=rows(dataset.climate_month),
        precip_rows=rows(dataset.precip_month),
        frost_rows=rows(dataset.climate_frost_month),
        periods=periods,
        precip_periods=rain,
        crop=crop,
        stages=dataset.stages[crop_id],
        zone=ZoneTemperatureUsed(
            "municipality",
            municipality.tmean_annual_c,
            municipality.altitude_m,
            False,
            municipality.tmean_annual_c,
            municipality.altitude_m,
        ),
        soil=zone_soil_ph(dataset, municipality_id),
        texture_class=dataset.soil[municipality_id].get("texture_class"),
        fixed_signals=fixed,
        config=config,
        irrigated=False,
    )
    assert dataset.version != "ejemplo"
    assert result["suitability"].level == "suitable"
    assert len(result["months"]) == 12
    assert any(m["frost_freq_pct"]["status"] == "available" for m in result["months"])
    for side in ("before", "after"):
        assert len(result["window_evaluations"][side]) == 12
        assert any(e["water_balance"] is not None for e in result["window_evaluations"][side])
        assert len(result["best_windows"][side]) <= 3
        assert all(not w["high_risk"] for w in result["best_windows"][side])
    monkeypatch.setattr(calculations, "require_dataset", lambda: dataset)
    response = TestClient(app).get("/api/v1/changes", params={"municipality_id": municipality_id, "crop_id": crop_id, "irrigated": "false"})
    assert response.status_code == 200, response.text
    body = response.json()
    ChangesResponse.model_validate(body)
    assert body["months"] == result["months"]
    assert body["best_windows"] == result["best_windows"]
    assert body["suitability"]["level"] == "suitable"
    assert body["versions"]["dataset"] == dataset.version
    assert "window_evaluations" not in body
