"""Integración pura de HU-217: años, fuentes, aptitud, agua y orden reales."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta

import pytest

from backend.config.thresholds import load_thresholds
from backend.config.weights import load_weights
from backend.engine.change_windows import ChangeConfig, compare_historical_changes
from backend.engine.changes import Period, PeriodPair
from backend.engine.signal_score import signal_scores
from backend.engine.soil_signal import ZoneSoilPh
from backend.engine.stages import StageSpan
from backend.engine.suitability import ZoneTemperatureUsed
from backend.engine.window_order import WindowSignals, best_windows, order_windows


@pytest.fixture
def inputs():
    periods = PeriodPair(Period("old", 1981, 2000, "nasa_power"), Period("new", 2005, 2024, "nasa_power"))
    rain = PeriodPair(Period("rain_old", 2001, 2012, "imerg"), Period("rain_new", 2013, 2024, "imerg"))
    return dict(
        municipality_id="15238",
        change_rows=[
            dict(
                municipality_id="15238",
                source_id="nasa_power",
                period_id=p.period_id,
                month=m,
                frost_freq_pct=30 if p == periods.before else 18,
                tmax_p90_c=20,
                precip_normal_mm=9999,
                quality="ok",
            )
            for p in (periods.before, periods.after)
            for m in range(1, 13)
        ],
        climate_rows=[
            dict(municipality_id="15238", source_id="nasa_power", year=y, month=m, et0_mm=100, precip_mm=9999, et0_normal_mm=9999)
            for y in range(1981, 2026)
            for m in range(1, 13)
        ],
        precip_rows=[
            dict(
                municipality_id="15238",
                source_id="imerg",
                year=y,
                month=m,
                precip_mm=200 if y <= 2012 else 10,
                precip_normal_mm=9999,
                precip_dry_mm=9999,
            )
            for y in range(2001, 2025)
            for m in range(1, 13)
        ],
        frost_rows=[
            dict(municipality_id="15238", source_id="nasa_power", year=y, month=m, frost_days=0, quality="ok")
            for y in range(1981, 2026)
            for m in range(1, 13)
        ],
        periods=periods,
        precip_periods=rain,
        crop=dict(
            name_es="papa",
            article="la",
            tmean_min_c=4,
            tmean_opt_min_c=8,
            tmean_opt_max_c=18,
            tmean_max_c=30,
            temp_opt_max_c=25,
            heat_max_c=35,
            ph_min=4,
            ph_opt_min=5,
            ph_opt_max=6,
            ph_max=8,
        ),
        stages=[StageSpan("initial", 40, 1, True, True)],
        zone=ZoneTemperatureUsed("municipality", 12, 2500, False, 12, 2500),
        soil=ZoneSoilPh(5.5, 5, 6),
        texture_class=None,
        fixed_signals={},
        config=ChangeConfig(0.8, 0.2, "nasa_power", "nasa_power", load_thresholds(), load_weights().weights),
        crop_name="la papa",
        irrigated=False,
    )


def test_real_balance_uses_own_rain_years_not_published_normal(inputs):
    result = compare_historical_changes(**inputs)
    before = result["window_evaluations"]["before"][0]
    after = result["window_evaluations"]["after"][0]
    assert before["water_balance"].need_mm < 200  # ET0 anual, no la normal 9999.
    assert before["signals"]["water"].score > after["signals"]["water"].score
    assert before["water_balance"].deficit_mm["dry"][1] == 0
    assert after["water_balance"].deficit_mm["dry"][1] > 0
    assert result["months"][0]["frost_freq_pct"]["change"] == -12
    assert "1981–2000" in result["reasons"][0] and "2005–2024" in result["reasons"][0]
    assert "2001 a 2012" in before["signals"]["water"].reasons[0]
    assert "2013 a 2024" in after["signals"]["water"].reasons[0]


def test_no_rain_source_fallback_and_no_years_outside_period(inputs):
    inputs["precip_rows"] = [r for r in inputs["precip_rows"] if r["year"] >= 2013]
    result = compare_historical_changes(**inputs)
    before = result["window_evaluations"]["before"][0]
    assert before["signals"]["water"].status == "insufficient_data"
    assert before["water_balance"] is None
    assert result["window_evaluations"]["after"][0]["signals"]["water"].status == "available"


def test_not_suitable_short_circuits_before_reading_annual_data(inputs):
    inputs["zone"] = replace(inputs["zone"], tmean_annual_c=50)

    def must_not_read():
        raise AssertionError("No debe evaluar ventanas")
        yield

    inputs["climate_rows"] = must_not_read()
    result = compare_historical_changes(**inputs)
    assert result["suitability"].level == "not_suitable"
    assert result["best_windows"] == {"before": [], "after": []}
    assert len(result["months"]) == 12
    assert "no es apto" in result["reasons"][0]


def test_unknown_suitability_still_evaluates_with_limitation(inputs):
    inputs["zone"] = replace(inputs["zone"], tmean_annual_c=None)
    result = compare_historical_changes(**inputs)
    assert result["suitability"].level == "insufficient_data"
    assert len(result["window_evaluations"]["before"]) == 12
    assert any("Sin la temperatura" in text for text in result["limitations"])


def test_missing_stages_never_recommends_windows(inputs):
    inputs["stages"] = []
    result = compare_historical_changes(**inputs)
    assert result["best_windows"] == {"before": [], "after": []}
    assert any("Sin etapas" in text for text in result["limitations"])


def test_default_order_is_exactly_hu192_and_excludes_critical_windows(inputs):
    result = compare_historical_changes(**inputs)
    for side in ("before", "after"):
        evaluated = result["window_evaluations"][side]
        candidates = [
            WindowSignals(date(1981, row["month"], 1), date(1981, row["month"], 1) + timedelta(days=40), signal_scores(row["signals"]))
            for row in evaluated
        ]
        expected = best_windows(order_windows(candidates, inputs["config"].default_weights))
        assert [r["month"] for r in result["best_windows"][side]] == [r.sowing_start.month for r in expected]
        assert all(not r["high_risk"] for r in result["best_windows"][side])
    assert result["best_windows"]["after"] == []  # Lluvia escasa: agua crítica.


def test_frost_uses_union_of_sensitive_months_and_own_period(inputs):
    # 10 años heló en enero y los otros 10 en febrero: unión 100 %, no promedio 50 %.
    for row in inputs["frost_rows"]:
        if row["year"] <= 2000:
            row["frost_days"] = int((row["month"] == 1 and row["year"] <= 1990) or (row["month"] == 2 and row["year"] > 1990))
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["frost"].critical
    assert not result["window_evaluations"]["after"][0]["signals"]["frost"].critical
    assert 1 not in [r["month"] for r in result["best_windows"]["before"]]


def test_minimum_years_is_per_period_and_per_indicator(inputs):
    inputs["precip_rows"] = [r for r in inputs["precip_rows"] if not (r["month"] == 1 and r["year"] in (2001, 2002, 2003))]
    result = compare_historical_changes(**inputs)
    january = result["window_evaluations"]["before"][0]["signals"]
    assert january["water"].status == "insufficient_data"  # 9 < ceil(12 * .8).
    assert january["frost"].status == "available"
    assert january["heat"].status == "available"


def test_no_cross_boundary_frost_and_no_other_municipality(inputs):
    inputs["config"] = replace(inputs["config"], min_year_share=1)
    inputs["frost_rows"].append(dict(municipality_id="99999", source_id="nasa_power", year=1981, month=1, frost_days=30, quality="ok"))
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["frost"].score == 100
    assert result["window_evaluations"]["before"][11]["signals"]["frost"].status == "insufficient_data"


def test_same_inputs_no_mutation_deterministic_without_clock(inputs):
    saved = deepcopy(inputs)
    first = compare_historical_changes(**inputs)
    assert inputs == saved
    for key in ("change_rows", "climate_rows", "precip_rows", "frost_rows"):
        inputs[key] = list(reversed(inputs[key]))
    assert first == compare_historical_changes(**inputs)


@pytest.mark.parametrize("irrigated", [True, None])
def test_irrigation_is_used_and_unknown_is_declared(inputs, irrigated):
    inputs["irrigated"] = irrigated
    result = compare_historical_changes(**inputs)
    water = result["window_evaluations"]["after"][0]["signals"]["water"]
    assert water.score == (100 if irrigated else 0)
    assert any("Sin dato de riego" in t for t in result["limitations"]) == (irrigated is None)


def test_offer_market_and_soil_are_identical_in_both_periods(inputs):
    from backend.engine.sensitive_signal import insufficient

    offer = insufficient("Esta versión todavía no evalúa la oferta")
    market = insufficient("Sin curva con fuente para mercado")
    inputs["fixed_signals"] = {m: {"supply": offer, "market": market} for m in range(1, 13)}
    result = compare_historical_changes(**inputs)
    for before, after in zip(result["window_evaluations"]["before"], result["window_evaluations"]["after"], strict=True):
        assert before["signals"]["supply"] is after["signals"]["supply"] is offer
        assert before["signals"]["market"] is after["signals"]["market"] is market
        assert before["signals"]["soil"] is after["signals"]["soil"]
    # Los avisos generales (historia comparada, lo que no cambia) los pone la API una sola vez, no el motor.
    assert not any("solo cambia el clima" in text or "pronóstico" in text for text in result["limitations"])


def test_heat_uses_period_rows_even_if_another_indicator_is_missing(inputs):
    for row in inputs["change_rows"]:
        if row["period_id"] == "new":
            row.update(tmax_p90_c=40, frost_freq_pct=None, quality="partial")
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["heat"].score == 100
    assert result["window_evaluations"]["after"][0]["signals"]["heat"].critical
    assert result["best_windows"]["after"] == []


def test_dry_percentile_is_linear_and_recomputed_from_annual_rain(inputs):
    for row in inputs["precip_rows"]:
        if row["year"] <= 2012:
            row["precip_mm"] = (row["year"] - 2001) * 10
    result = compare_historical_changes(**inputs)
    # p20([0,10,...,110]) = 22: enero completo conserva esos 22 mm.
    assert result["window_evaluations"]["before"][0]["water_balance"].months[0].rain_mm["dry"] == 22


def test_nonfinite_values_are_missing_even_with_irrigation(inputs):
    inputs["irrigated"] = True
    for row in inputs["precip_rows"]:
        if row["month"] == 1:
            row["precip_mm"] = float("nan")
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["water"].status == "insufficient_data"


def test_duplicate_annual_rows_are_rejected(inputs):
    inputs["precip_rows"].append(dict(inputs["precip_rows"][0]))
    with pytest.raises(ValueError, match="duplicada"):
        compare_historical_changes(**inputs)


def test_power_rain_uses_climate_month_when_no_separate_rain_periods(inputs):
    inputs["precip_periods"] = None
    inputs["config"] = replace(inputs["config"], rain_table="climate_month")
    inputs["precip_rows"] = []
    for row in inputs["climate_rows"]:
        row["precip_mm"] = 200 if row["year"] <= 2000 else 10
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["water"].score == 100
    assert result["window_evaluations"]["after"][0]["signals"]["water"].score == 0


def test_wrong_frost_source_is_not_used(inputs):
    for row in inputs["frost_rows"]:
        row["source_id"] = "otra_fuente"
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["frost"].status == "insufficient_data"


def test_period_lengths_and_minimum_come_from_received_configuration(inputs):
    inputs["precip_periods"] = PeriodPair(Period("r1", 2001, 2002, "imerg"), Period("r2", 2013, 2014, "imerg"))
    inputs["precip_rows"] = [r for r in inputs["precip_rows"] if r["year"] != 2001]
    inputs["config"] = replace(inputs["config"], min_year_share=0.5)
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["water"].status == "available"
    inputs["config"] = replace(inputs["config"], min_year_share=1)
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["water"].status == "insufficient_data"


def test_declared_rain_table_never_falls_back_to_another_table(inputs):
    inputs["climate_rows"].extend(inputs["precip_rows"])
    inputs["precip_rows"] = []
    result = compare_historical_changes(**inputs)
    assert result["window_evaluations"]["before"][0]["signals"]["water"].status == "insufficient_data"
