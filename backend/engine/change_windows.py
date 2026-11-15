"""Ventanas históricas de HU-217, con datos y configuración ya leídos (R6).

Reutiliza HU-144, HU-191, HU-192 y HU-196. No usa las normales repetidas
en las tablas anuales: vuelve a calcularlas exclusivamente dentro de cada periodo.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import ceil, isfinite
from statistics import fmean
from typing import TYPE_CHECKING, Any

from backend.engine.changes import SOURCE_NAMES, Period, PeriodPair, compare_climate_months
from backend.engine.diagnosis import IRRIGATION_UNKNOWN, SignalOutcome
from backend.engine.frost_signal import FrostMonth, frost_signal
from backend.engine.heat_signal import HeatMonth, heat_signal
from backend.engine.sensitive_signal import ClimateNormal, insufficient
from backend.engine.signal_score import INSUFFICIENT_DATA, signal_scores
from backend.engine.soil_signal import ZoneSoilPh, soil_signal
from backend.engine.stages import StageSpan, monthly_sowing_windows
from backend.engine.suitability import NOT_SUITABLE, ZoneTemperatureUsed, crop_suitability, suitability_reason
from backend.engine.water_balance import DRY, MonthClimate, root_zone, water_balance
from backend.engine.water_notes import RainSource, missing_data
from backend.engine.water_signal import WaterBalanceSummary, water_signal
from backend.engine.window_order import WindowSignals, best_windows, order_windows

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds


@dataclass(frozen=True)
class ChangeConfig:
    """Valores de configuración versionada; quien llama los lee, nunca el motor.

    min_year_share y dry_quantile son los de pipeline/region.yaml.
    frost_source_id identifica la fuente de la tabla anual de heladas.
    et0_source_id sale de sources.yaml.
    """

    min_year_share: float
    dry_quantile: float
    et0_source_id: str
    frost_source_id: str
    thresholds: Thresholds
    default_weights: Mapping[str, int]
    frost_caveat: str | None = None
    rain_caveat: str | None = None
    rain_table: str = "precip_month"

    def __post_init__(self) -> None:
        if not 0 < self.min_year_share <= 1 or not 0 <= self.dry_quantile <= 1:
            raise ValueError("Proporción mínima de años o percentil seco inválidos")
        if not self.et0_source_id or not self.frost_source_id:
            raise ValueError("Se necesitan las fuentes de ET0 y heladas")
        if self.rain_table not in {"climate_month", "precip_month"}:
            raise ValueError("Tabla de lluvia inválida")


def _value(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if isfinite(number) else None


def _annual(
    rows: Iterable[Mapping[str, Any]], municipality_id: str, period: Period, source_id: str | None
) -> dict[tuple[int, int], Mapping[str, Any]]:
    result = {}
    for row in rows:
        if row["municipality_id"] != municipality_id or (source_id is not None and row.get("source_id") != source_id):
            continue
        year, month = row["year"], row["month"]
        if not period.start_year <= year <= period.end_year:
            continue
        key = (year, month)
        if key in result:
            raise ValueError(f"Fila anual duplicada: {key}")
        result[key] = row
    return result


def _monthly_values(rows: Mapping[tuple[int, int], Mapping[str, Any]], month: int, column: str, minimum: int) -> list[float]:
    values = sorted(value for (_, m), row in rows.items() if m == month and (value := _value(row.get(column))) is not None)
    return values if len(values) >= minimum else []


def _quantile(values: Sequence[float], q: float) -> float | None:
    """Percentil lineal, como el del pipeline (HU-143), sin completar años."""
    if not values:
        return None
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 1)


def compare_historical_changes(
    *,
    municipality_id: str,
    change_rows: Iterable[Mapping[str, Any]],
    climate_rows: Iterable[Mapping[str, Any]],
    precip_rows: Iterable[Mapping[str, Any]],
    frost_rows: Iterable[Mapping[str, Any]],
    periods: PeriodPair,
    precip_periods: PeriodPair | None,
    crop: Mapping[str, Any],
    stages: list[StageSpan],
    zone: ZoneTemperatureUsed,
    soil: ZoneSoilPh | None,
    texture_class: str | None,
    fixed_signals: Mapping[int, Mapping[str, SignalOutcome]],
    config: ChangeConfig,
    irrigated: bool | None = None,
) -> dict[str, Any]:
    """Comparación completa del motor; no abre archivos ni conoce Dataset/FastAPI.

    fixed_signals contiene oferta y mercado por mes de SIEMBRA, calculados con
    el mismo contexto actual para ambos periodos (el mercado puede depender de
    la cosecha). Una señal ausente se declara sin datos, nunca se inventa.
    El año inicial del primer periodo es solo plantilla del calendario, igual
    en ambos lados: no se consulta el reloj ni se comparan fechas futuras.
    Las heladas usan años completos de su periodo; las ventanas que cruzan
    diciembre no leen heladas del año posterior al final del periodo.
    """
    change_rows = tuple(change_rows)
    comparison = compare_climate_months(municipality_id=municipality_id, rows=change_rows, periods=periods, precip_periods=precip_periods)
    aptitude = crop_suitability(crop, zone.tmean_annual_c)
    crop_name = f"{crop.get('article', '')} {crop.get('name_es', 'cultivo')}".strip()
    reason = suitability_reason(aptitude, crop, crop_name, zone)
    limitations = [
        "La oferta, el mercado y el suelo son los mismos en los dos periodos; solo cambia el clima.",
        "Es historia comparada, no es un pronóstico.",
    ]
    if periods.before.source_id == "nasa_power":
        limitations.append("NASA POWER es un reanálisis, no una observación directa.")
    if precip_periods is not None:
        limitations.append("La lluvia usa los periodos de su propia fuente, que pueden ser más cortos que los de heladas y calor.")
    result = {
        **comparison,
        "suitability": aptitude,
        "suitability_reasons": [reason],
        "best_windows": {"before": [], "after": []},
        "weights_basis": "default",
        "limitations": limitations,
        # Diagnósticos por mes para comprobar el cálculo; la API entrega solo
        # best_windows y months, sin ampliar el contrato.
        "window_evaluations": {"before": [], "after": []},
    }
    if aptitude.level == NOT_SUITABLE:
        result["reasons"] = ["No se calculan ventanas porque el cultivo no es apto para la zona.", reason, *comparison["reasons"]]
        return result
    if aptitude.level == INSUFFICIENT_DATA:
        limitations.append(reason)
    if irrigated is None:
        limitations.append(IRRIGATION_UNKNOWN)
    windows = monthly_sowing_windows(stages, date(periods.before.start_year, 1, 1))
    if not windows:
        limitations.append("Sin etapas publicadas del cultivo: no se pueden evaluar ventanas de siembra.")
        return result
    climate_rows, precip_rows, frost_rows = tuple(climate_rows), tuple(precip_rows), tuple(frost_rows)
    soil_result = soil_signal(soil, crop, config.thresholds, crop_name)
    rain_pair = precip_periods or periods
    for side in ("before", "after"):
        period, rain_period = getattr(periods, side), getattr(rain_pair, side)
        minimum = ceil(config.min_year_share * (period.end_year - period.start_year + 1))
        rain_minimum = ceil(config.min_year_share * (rain_period.end_year - rain_period.start_year + 1))
        normal = ClimateNormal(period.start_year, period.end_year, minimum)
        annual_frost = (
            _annual(frost_rows, municipality_id, period, config.frost_source_id) if period.source_id == config.frost_source_id else {}
        )
        frost = {
            key: FrostMonth(value, row["quality"])
            for key, row in annual_frost.items()
            if (value := _value(row.get("frost_days"))) is not None
        }
        heat = {
            row["month"]: HeatMonth(value, "ok")
            for row in change_rows
            if row["municipality_id"] == municipality_id
            and row["source_id"] == period.source_id
            and row["period_id"] == period.period_id
            and (value := _value(row.get("tmax_p90_c"))) is not None
        }
        # ET0 y lluvia abarcan los años del periodo de la fuente de LLUVIA.
        # No se usan las columnas normal/dry, que describen otro periodo.
        annual_et0 = _annual(climate_rows, municipality_id, rain_period, config.et0_source_id)
        # La API identifica la tabla publicada para la fuente antes de filtrar
        # por municipio, igual que HU-071. Sin filas, no se busca en la otra.
        rain_table = climate_rows if config.rain_table == "climate_month" else precip_rows
        annual_rain = _annual(rain_table, municipality_id, rain_period, rain_period.source_id)
        water_months = {}
        for month in range(1, 13):
            et0 = _monthly_values(annual_et0, month, "et0_mm", rain_minimum)
            rain = _monthly_values(annual_rain, month, "precip_mm", rain_minimum)
            water_months[month] = MonthClimate(
                round(fmean(et0), 1) if et0 else None,
                round(fmean(rain), 1) if rain else None,
                _quantile(rain, config.dry_quantile),
            )
        rain_source = RainSource(
            SOURCE_NAMES.get(rain_period.source_id, rain_period.source_id), rain_period.start_year, rain_period.end_year, config.rain_caveat
        )
        candidates = []
        for window in windows:
            touched = window.months()
            missing = missing_data(
                rain_source,
                [m for m in touched if water_months[m.month].rain_dry_mm is None],
                [m for m in touched if water_months[m.month].et0_mm is None],
            )
            balance = None if missing else water_balance(window, water_months, texture_class, root_zone(dict(crop)))
            summary = None if balance is None else WaterBalanceSummary(balance.need_mm, balance.deficit_mm[DRY], balance.retention)
            signals = {
                "water": water_signal(summary, irrigated, rain_source, window, config.thresholds, crop_name, missing),
                "frost": frost_signal(window, frost, normal, config.thresholds, crop_name, config.frost_caveat),
                "heat": heat_signal(window, heat, crop, normal, config.thresholds, crop_name),
                "soil": soil_result,
                **{
                    name: fixed_signals.get(window.sowing_date.month, {}).get(
                        name, insufficient(f"Sin señal de {'oferta' if name == 'supply' else 'mercado'} para la comparación histórica")
                    )
                    for name in ("supply", "market")
                },
            }
            candidates.append(WindowSignals(window.sowing_date, window.harvest_estimate, signal_scores(signals)))
            result["window_evaluations"][side].append({"month": window.sowing_date.month, "signals": signals, "water_balance": balance})
            for name, signal in signals.items():
                notes = (*signal.limitations, *(signal.reasons if signal.status == INSUFFICIENT_DATA else ()))
                signal_period = rain_period if name == "water" else period
                limitations.extend(f"{signal_period.start_year}–{signal_period.end_year}: {note}" for note in notes)
        result["best_windows"][side] = [
            {
                "month": ranked.sowing_start.month,
                "limiting_signal": ranked.limiting_signal,
                "limiting_score": ranked.limiting_score,
                "high_risk": ranked.high_risk,
            }
            for ranked in best_windows(order_windows(candidates, config.default_weights))
        ]
    result["limitations"] = list(dict.fromkeys(limitations))
    return result
