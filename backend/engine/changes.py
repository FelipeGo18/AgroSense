"""Comparación mensual de clima histórico (HU-217)"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

INDICATORS = {
    "frost_freq_pct": ("frecuencia de heladas", "%", "puntos porcentuales"),
    "precip_normal_mm": ("lluvia normal", "mm", "mm"),
    "tmax_p90_c": ("temperatura máxima p90", "°C", "°C"),
}


@dataclass(frozen=True)
class Period:
    """Un periodo recibido de la configuración, no definido por el motor."""

    period_id: str
    start_year: int
    end_year: int
    source_id: str

    def __post_init__(self) -> None:
        if not self.period_id or not self.source_id:
            raise ValueError("El periodo necesita period_id y source_id")
        if self.start_year > self.end_year:
            raise ValueError("El inicio del periodo no puede superar su final")


@dataclass(frozen=True)
class PeriodPair:
    before: Period
    after: Period

    def __post_init__(self) -> None:
        if self.before.source_id != self.after.source_id:
            raise ValueError("Los dos periodos deben usar la misma fuente")
        if self.before.end_year >= self.after.start_year:
            raise ValueError("El periodo anterior debe terminar antes del posterior")


def _number(value: Any) -> float | None:
    """Un nulo o un valor no finito nunca se convierte en cero."""
    if value is None:
        return None
    number = float(value)
    return number if isfinite(number) else None


def compare_climate_months(
    *,
    municipality_id: str,
    rows: Iterable[Mapping[str, Any]],
    periods: PeriodPair,
    precip_periods: PeriodPair | None = None,
) -> dict[str, Any]:
    """Devuelve los bloques months y reasons del contrato de /changes
    rows contiene las filas ya cargadas de climate_change_month.
    HU-216 es responsable de publicar solo meses con años suficientes.
    Una fila partial puede tener indicadores disponibles y otros nulos:
    se revisa cada indicador por separado.

    Si la lluvia tiene otra fuente y otros periodos, se reciben mediante
    precip_periods. Nunca se usa otra fuente para rellenar un dato ausente.
    """
    rain_periods = precip_periods if precip_periods is not None else periods

    selected_periods = {(period.source_id, period.period_id) for pair in (periods, rain_periods) for period in (pair.before, pair.after)}

    # Fuente, periodo y mes. No se unen datos por nombre
    index: dict[tuple[str, str, int], Mapping[str, Any]] = {}

    for row in rows:
        if row["municipality_id"] != municipality_id:
            continue
        source_id = row["source_id"]
        period_id = row["period_id"]
        if (source_id, period_id) not in selected_periods:
            continue

        month = row["month"]
        if isinstance(month, bool) or month not in range(1, 13):
            raise ValueError("El mes debe ser un entero entre 1 y 12")

        key = (source_id, period_id, month)
        if key in index:
            raise ValueError(f"Fila duplicada de climate_change_month: {key}")
        index[key] = row

    months = []
    reasons = []

    for month in range(1, 13):
        month_result: dict[str, Any] = {"month": month}
        month_name = MONTH_NAMES[month - 1]

        for indicator, (label, unit, change_unit) in INDICATORS.items():
            pair = rain_periods if indicator == "precip_normal_mm" else periods
            before_row = index.get((pair.before.source_id, pair.before.period_id, month))
            after_row = index.get((pair.after.source_id, pair.after.period_id, month))
            before = _number(before_row.get(indicator) if before_row is not None else None)
            after = _number(after_row.get(indicator) if after_row is not None else None)
            available = before is not None and after is not None
            difference = after - before if available else None

            month_result[indicator] = {
                "status": "available" if available else "insufficient_data",
                "before": before,
                "after": after,
                "change": difference,
            }

            before_years = f"{pair.before.start_year}–{pair.before.end_year}"
            after_years = f"{pair.after.start_year}–{pair.after.end_year}"

            if available:
                reasons.append(
                    f"En {month_name}, la {label} fue {before:g} {unit} "
                    f"en {before_years} y {after:g} {unit} en {after_years} "
                    f"según {pair.before.source_id}; "
                    f"la diferencia fue {difference:+g} {change_unit}."
                )
            else:
                reasons.append(
                    f"No hay datos suficientes para comparar la {label} "
                    f"de {month_name} entre {before_years} y {after_years} "
                    f"según {pair.before.source_id}."
                )
        months.append(month_result)
    return {"months": months, "reasons": reasons}
