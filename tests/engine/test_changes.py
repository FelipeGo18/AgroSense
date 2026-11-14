import pytest

from backend.api.calc_models import MonthChange
from backend.engine.changes import Period, PeriodPair, compare_climate_months


@pytest.fixture
def periods():
    return PeriodPair(
        before=Period("before", 1981, 2000, "nasa_power"),
        after=Period("after", 2005, 2024, "nasa_power"),
    )


def row(period_id, **values):
    return {
        "municipality_id": "15238",
        "source_id": "nasa_power",
        "period_id": period_id,
        "month": 1,
        "frost_freq_pct": None,
        "precip_normal_mm": None,
        "tmax_p90_c": None,
        "years": 20,
        "quality": "partial",
        **values,
    }


def test_comparison_matches_contract_and_preserves_missing_values(periods):
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        rows=[
            row("before", frost_freq_pct=30, precip_normal_mm=0),
            row(
                "after",
                frost_freq_pct=18,
                precip_normal_mm=7,
                tmax_p90_c=21.4,
            ),
        ],
    )

    assert [month["month"] for month in result["months"]] == list(range(1, 13))
    for month in result["months"]:
        MonthChange.model_validate(month)

    january = result["months"][0]
    assert january["frost_freq_pct"]["change"] == -12
    assert january["precip_normal_mm"]["before"] == 0
    assert january["precip_normal_mm"]["change"] == 7
    assert january["tmax_p90_c"] == {
        "status": "insufficient_data",
        "before": None,
        "after": 21.4,
        "change": None,
    }
    assert result["months"][1]["frost_freq_pct"]["status"] == "insufficient_data"
    assert "1981–2000" in result["reasons"][0]
    assert "2005–2024" in result["reasons"][0]


def test_rain_uses_its_own_source_without_fallback(periods):
    rain_periods = PeriodPair(
        before=Period("rain_before", 2001, 2012, "gpm_imerg"),
        after=Period("rain_after", 2013, 2024, "gpm_imerg"),
    )
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        precip_periods=rain_periods,
        rows=[
            row("before", precip_normal_mm=100),
            row("after", precip_normal_mm=200),
            row(
                "rain_after",
                source_id="gpm_imerg",
                precip_normal_mm=35,
            ),
        ],
    )

    # No usa POWER para rellenar el periodo ausente de IMERG.
    assert result["months"][0]["precip_normal_mm"] == {
        "status": "insufficient_data",
        "before": None,
        "after": 35.0,
        "change": None,
    }


def test_duplicate_rows_are_rejected(periods):
    with pytest.raises(ValueError, match="duplicada"):
        compare_climate_months(
            municipality_id="15238",
            periods=periods,
            rows=[row("before"), row("before")],
        )


def test_different_sources_cannot_be_compared():
    with pytest.raises(ValueError, match="misma fuente"):
        PeriodPair(
            before=Period("before", 1981, 2000, "nasa_power"),
            after=Period("after", 2005, 2024, "gpm_imerg"),
        )


def test_input_order_does_not_change_result(periods):
    rows = [
        row("before", frost_freq_pct=30),
        row("after", frost_freq_pct=18),
    ]
    first = compare_climate_months(municipality_id="15238", periods=periods, rows=rows)
    second = compare_climate_months(municipality_id="15238", periods=periods, rows=reversed(rows))
    assert first == second


def test_difference_is_rounded_to_one_decimal(periods):
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        rows=[row("before", tmax_p90_c=20.1), row("after", tmax_p90_c=21.4)],
    )
    assert result["months"][0]["tmax_p90_c"]["change"] == 1.3
    assert "+1,3 °C" in result["reasons"][2]


def test_missing_january_before_keeps_after_values(periods):
    """Caso que antes se comprobaba a mano con scripts/simular_cambios.py."""
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        rows=[row("after", frost_freq_pct=18, precip_normal_mm=35, tmax_p90_c=21.4)],
    )
    january = result["months"][0]
    for indicator, expected in (("frost_freq_pct", 18), ("precip_normal_mm", 35), ("tmax_p90_c", 21.4)):
        assert january[indicator] == {"status": "insufficient_data", "before": None, "after": expected, "change": None}
    assert len(result["months"]) == 12
    assert all("No hay datos suficientes" in reason for reason in result["reasons"])


def test_reasons_summarize_largest_difference_without_technical_source_ids(periods):
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        rows=[
            row("before", frost_freq_pct=30),
            row("after", frost_freq_pct=18),
            row("before", month=2, frost_freq_pct=50),
            row("after", month=2, frost_freq_pct=70),
        ],
    )
    assert len(result["reasons"]) == 3
    frost = result["reasons"][0]
    assert "febrero" in frost
    assert "50 %" in frost and "70 %" in frost
    assert "+20 puntos porcentuales" in frost
    assert "2 de los 12 meses" in frost
    assert "NASA POWER" in frost
    assert all("nasa_power" not in text and "p90" not in text for text in result["reasons"])
    assert result["months"][0]["frost_freq_pct"]["change"] == -12


def test_tied_summaries_choose_first_month_deterministically(periods):
    rows = [
        row("before", month=2, frost_freq_pct=50),
        row("after", month=2, frost_freq_pct=60),
        row("before", frost_freq_pct=30),
        row("after", frost_freq_pct=20),
    ]
    result = compare_climate_months(municipality_id="15238", periods=periods, rows=rows)
    assert "enero" in result["reasons"][0]
    assert "-10 puntos porcentuales" in result["reasons"][0]


def test_zero_change_summary_is_distinct_from_missing_data(periods):
    result = compare_climate_months(
        municipality_id="15238",
        periods=periods,
        rows=[row("before", frost_freq_pct=0), row("after", frost_freq_pct=0)],
    )
    assert "no presentó diferencias a un decimal" in result["reasons"][0]
    assert "1 de los 12 meses" in result["reasons"][0]
    assert "No hay datos suficientes" in result["reasons"][1]
