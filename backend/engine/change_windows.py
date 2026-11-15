"""Ventanas históricas de HU-217, con datos y configuración ya leídos (R6).

Reutiliza HU-144, HU-191, HU-192 y HU-196. No usa las normales repetidas
en las tablas anuales: vuelve a calcularlas exclusivamente dentro de cada periodo.
"""

from __future__ import annotations

import re
from collections import Counter
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
from backend.engine.signal_score import INSUFFICIENT_DATA, is_grave, rated_signals, signal_scores
from backend.engine.soil_signal import ZoneSoilPh, soil_signal
from backend.engine.stages import StageSpan, monthly_sowing_windows
from backend.engine.suitability import NOT_SUITABLE, ZoneTemperatureUsed, crop_suitability, suitability_reason
from backend.engine.traffic_light import SIGNAL_NAMES_ES
from backend.engine.water_balance import DRY, MonthClimate, root_zone, water_balance
from backend.engine.water_notes import RainSource, missing_data
from backend.engine.water_signal import WaterBalanceSummary, water_signal
from backend.engine.window_order import RankedWindow, WindowSignals, best_windows, order_windows
from common.months import MONTH_NAMES

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds


class HistoricalChangesError(ValueError):
    """Datos históricos o configuración que no sirven para comparar (periodos, fuentes o filas repetidas). La API lo
    responde como 503; cualquier otro error es de programación y sale como 500."""


# Las señales que dependen del clima del periodo. Las demás (oferta, mercado y suelo) son las mismas en los dos.
CLIMATE_SIGNALS = ("water", "frost", "heat")


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
            raise HistoricalChangesError("Proporción mínima de años o percentil seco inválidos")
        if not self.et0_source_id or not self.frost_source_id:
            raise HistoricalChangesError("Se necesitan las fuentes de ET0 y heladas")
        if self.rain_table not in {"climate_month", "precip_month"}:
            raise HistoricalChangesError("Tabla de lluvia inválida")


# Un aviso que termina en una lista de meses entre paréntesis, «… (marzo y agosto): esos meses no se evaluaron».
_MONTHS_IN_PARENS = re.compile(r"^(?P<head>.*) \((?P<months>[^()]*)\)(?P<tail>[^()]*)$")


def _month_list(text: str) -> list[str] | None:
    """Los meses de «marzo, abril y agosto», o None si alguna parte no es un mes."""
    names = [name.strip() for part in text.split(",") for name in part.split(" y ")]
    return names if names and all(name in MONTH_NAMES for name in names) else None


def _join_months(names: Iterable[str]) -> str:
    ordered = sorted(set(names), key=MONTH_NAMES.index)
    return ordered[0] if len(ordered) == 1 else f"{', '.join(ordered[:-1])} y {ordered[-1]}"


def merge_month_notes(notes: Iterable[str]) -> list[str]:
    """Junta los avisos que solo cambian en la lista de meses entre paréntesis: uno solo, con todos los meses en orden
    del calendario, en el lugar del primero. Los demás avisos quedan iguales y sin repetir."""
    merged: dict[tuple[str, str] | str, list[str] | None] = {}
    for note in notes:
        match = _MONTHS_IN_PARENS.match(note)
        months = _month_list(match["months"]) if match else None
        if match is None or months is None:
            merged.setdefault(note, None)
            continue
        merged.setdefault((match["head"], match["tail"]), []).extend(months)
    return [
        key if months is None else f"{key[0]} ({_join_months(months)}){key[1]}"  # type: ignore[index]
        for key, months in merged.items()
    ]


def _no_best_windows_reason(
    ranked: Sequence[RankedWindow],
    candidates: Sequence[WindowSignals],
    weights: Mapping[str, int],
    period: Period,
    rain_period: Period,
) -> str:
    """Por qué un periodo no deja ninguna ventana entre las mejores (cultivo apto): cuántos meses de siembra son de alto
    riesgo y qué señales críticas los descartan, o cuántos no tienen señales para calificar (R2, R5)."""
    total = len(ranked)
    high = sum(window.high_risk for window in ranked)
    unrated = sum(window.limiting_score is None for window in ranked)
    causes: Counter[str] = Counter()
    for window in candidates:
        causes.update({name for name, signal, _ in rated_signals(window.signals, weights) if is_grave(signal)})
    label = rain_period if set(causes) == {"water"} else period
    where = f"En {label.start_year}–{label.end_year}"
    parts = []
    for index, (name, count) in enumerate(sorted(causes.items(), key=lambda item: (-item[1], CLIMATE_ORDER.get(item[0], 9), item[0]))):
        verb = (" es crítica" if name in _FEMININE else " es crítico") if index == 0 else ""
        times = "en todos" if count == total else f"en {count}"
        parts.append(f"{SIGNAL_NAMES_ES.get(name, name)}{verb} {times}")
    cause_text = " y ".join([", ".join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts)
    if high == total:
        sentence = f"{where} los {total} meses de siembra son de alto riesgo: {cause_text}."
    elif high:
        sentence = (
            f"{where} ninguna ventana queda entre las mejores: {high} de los {total} meses de siembra son de alto riesgo "
            f"({cause_text}) y {unrated} no tienen señales con datos para calificar."
        )
    else:
        sentence = f"{where} ninguna ventana queda entre las mejores: ningún mes de siembra tiene señales con datos para calificar."
    if "heat" in causes and period.source_id == "nasa_power":
        sentence += " El calor de NASA POWER puede salir más alto que el real en tierra caliente: vea las limitaciones."
    return sentence


CLIMATE_ORDER = {name: index for index, name in enumerate(CLIMATE_SIGNALS)}
# Las señales que se nombran en femenino en `SIGNAL_NAMES_ES` («el agua es crítica», «la helada es crítica»).
_FEMININE = frozenset({"water", "frost", "supply"})


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
            raise HistoricalChangesError(f"Fila anual duplicada: {key}")
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
    crop_name: str,
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
    `crop_name` llega de quien llama, con su artículo («la papa»), igual que en el diagnóstico.

    Los avisos generales (historia comparada, reanálisis, periodos de cada fuente) los pone la API una sola vez. Aquí
    solo van los de las señales: los del clima, de las ventanas que salen en `best_windows`, con su periodo delante;
    los de oferta, mercado y suelo, una vez y sin periodo, porque son los mismos en los dos.
    """
    change_rows = tuple(change_rows)
    comparison = compare_climate_months(municipality_id=municipality_id, rows=change_rows, periods=periods, precip_periods=precip_periods)
    aptitude = crop_suitability(crop, zone.tmean_annual_c)
    reason = suitability_reason(aptitude, crop, crop_name, zone)
    limitations: list[str] = []
    fixed_notes: list[str] = []
    caveats = {note for note in (config.rain_caveat, config.frost_caveat) if note}
    result = {
        **comparison,
        "suitability": aptitude,
        "suitability_reasons": [reason],
        "best_windows": {"before": [], "after": []},
        "weights_basis": "default",
        "limitations": limitations,
        "reasons": list(comparison["reasons"]),
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
            # La `quality` de la fila es de toda la fila: sale `partial` si falta otro indicador (por ejemplo, las
            # heladas). El calor del mes vale si su p90 está; si no, la fila no entra.
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
        by_month: dict[int, Mapping[str, SignalOutcome]] = {}
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
            by_month[window.sowing_date.month] = signals
            for name in ("soil", "supply", "market"):
                signal = signals[name]
                fixed_notes.extend((*signal.limitations, *(signal.reasons if signal.status == INSUFFICIENT_DATA else ())))
        ranked = order_windows(candidates, config.default_weights)
        ranked_best = best_windows(ranked)
        if not ranked_best and ranked:
            # Revisión del PR #142: sin ninguna ventana buena, la respuesta dice por qué (alto riesgo o sin datos).
            result["reasons"].append(_no_best_windows_reason(ranked, candidates, config.default_weights, period, rain_period))
        for ranked in ranked_best:
            signals = by_month[ranked.sowing_start.month]
            for name in CLIMATE_SIGNALS:
                signal = signals[name]
                signal_period = rain_period if name == "water" else period
                for note in (*signal.limitations, *(signal.reasons if signal.status == INSUFFICIENT_DATA else ())):
                    # El aviso fijo de una fuente no depende del periodo: va una vez y sin él.
                    limitations.append(note if note in caveats else f"{signal_period.start_year}–{signal_period.end_year}: {note}")
        result["best_windows"][side] = [
            {
                "month": ranked.sowing_start.month,
                "limiting_signal": ranked.limiting_signal,
                "limiting_score": ranked.limiting_score,
                "high_risk": ranked.high_risk,
            }
            for ranked in ranked_best
        ]
    # Los avisos del clima que solo cambian en los meses (uno por cada mejor ventana) van juntos, uno por periodo.
    result["limitations"] = merge_month_notes([*limitations, *fixed_notes])
    return result
