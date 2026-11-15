"""Lee el contexto de /changes y llama al motor puro de HU-217 (HU-218)."""

from collections.abc import Mapping
from datetime import date
from typing import Any

import polars as pl

from backend.api.market_signal import market_for, seasonal_index
from backend.api.soil_signals import zone_soil_ph
from backend.api.window_diagnosis import crop_name
from backend.api.window_signals import pending_signal
from backend.config.changes import get_change_parameters
from backend.config.thresholds import get_thresholds
from backend.config.weights import get_default_weights
from backend.dataset import Dataset
from backend.engine.change_windows import ChangeConfig, compare_historical_changes
from backend.engine.changes import PeriodPair
from backend.engine.market_signal import market_signal
from backend.engine.stages import monthly_sowing_windows
from backend.engine.suitability import NOT_SUITABLE, ZoneTemperatureUsed, crop_suitability
from common.signal_sources import SignalSource


def historical_changes(
    dataset: Dataset,
    municipality_id: str,
    crop_id: str,
    irrigated: bool | None,
    periods: PeriodPair,
    precip_periods: PeriodPair | None,
    sources: Mapping[str, SignalSource],
) -> dict[str, Any]:
    municipality, crop = dataset.municipalities[municipality_id], dataset.crops[crop_id]
    parameters, thresholds = get_change_parameters(), get_thresholds()
    rain_source = sources["water"].used
    publishes_rain = dataset.precip_month is not None and not dataset.precip_month.filter(pl.col("source_id") == rain_source).is_empty()
    config = ChangeConfig(
        parameters.min_year_share,
        parameters.dry_quantile,
        sources["water"].et0,
        sources["frost"].used,
        thresholds,
        get_default_weights().weights,
        sources["frost"].caveat,
        sources["water"].caveat,
        rain_table="precip_month" if publishes_rain else "climate_month",
    )
    fixed = {}
    stages = dataset.stages.get(crop_id, [])
    # No preparar ventanas/mercado para un cultivo no apto.
    if crop_suitability(crop, municipality.tmean_annual_c).level != NOT_SUITABLE:
        market_id = market_for(dataset, municipality)
        for window in monthly_sowing_windows(stages, date(periods.before.start_year, 1, 1)):
            index, years = seasonal_index(dataset, crop_id, market_id, window.harvest_estimate.month)
            fixed[window.sowing_date.month] = {"supply": pending_signal("supply"), "market": market_signal(index, years, thresholds)}

    def rows(table: pl.DataFrame | None) -> list[dict[str, Any]]:
        return [] if table is None else table.filter(pl.col("municipality_id") == municipality_id).to_dicts()

    return compare_historical_changes(
        municipality_id=municipality_id,
        change_rows=rows(dataset.climate_change_month),
        climate_rows=rows(dataset.climate_month),
        precip_rows=rows(dataset.precip_month),
        frost_rows=rows(dataset.climate_frost_month),
        periods=periods,
        precip_periods=precip_periods,
        crop=crop,
        stages=stages,
        zone=ZoneTemperatureUsed(
            "municipality",
            municipality.tmean_annual_c,
            municipality.altitude_m,
            False,
            municipality.tmean_annual_c,
            municipality.altitude_m,
        ),
        soil=zone_soil_ph(dataset, municipality_id),
        texture_class=dataset.soil.get(municipality_id, {}).get("texture_class"),
        fixed_signals=fixed,
        config=config,
        crop_name=crop_name(crop),
        irrigated=irrigated,
    )
