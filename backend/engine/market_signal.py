"""La señal de mercado: si el precio suele estar bajo en el mes en que saldría la cosecha (HU-073;
specs/01-reglas.md, «Señales de una ventana» y «Cómo se califica cada señal»).

Función pura (R6): recibe el índice estacional de precio del mes de cosecha ya resuelto por la API
(`backend/api/market_signal.py`, de `market_month`) y los umbrales ya leídos y validados (`Thresholds`, HU-075). No
importa la API, el dataset ni FastAPI, y no abre archivos: la curva de `market` vive en `thresholds.yaml`.

Hoy la curva de `market` es nula (`curve: null`): ninguna fuente externa dice qué índice estacional es «precio bajo» y
la regla del equipo del 11 de noviembre de 2026 no deja usar un criterio propio para una señal que no es central. Por
eso la señal siempre da `insufficient_data`, con o sin índice. La rama con índice (nivel, calificación y razón) queda
lista para cuando exista una fuente y se escriba la curva; la propuesta está en `docs/investigacion-decisiones.md` (5e).

Es historia de precios mayoristas, nunca un pronóstico (decisión 4): la razón solo dice cómo ha sido el precio de ese
mes frente al promedio del año del propio producto, en los años que respaldan el índice.

No trae `counts`: si la señal cuenta para la luz lo deciden los pesos en el semáforo (HU-074), no esta señal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.engine.signal_score import AVAILABLE, round_half_up, score_signal

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

INDICATOR = "seasonal_index"
NO_DATA_REASON = "Sin datos de mercado para la zona"
HISTORY_LABEL = "Es historia de precios, no un pronóstico"


@dataclass(frozen=True)
class MarketSignalResult:
    """La señal `market` de una ventana, con los nombres de campo del contrato (specs/02-contratos.md)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]


def market_signal(seasonal_index: float | None, years: int | None, thresholds: Thresholds) -> MarketSignalResult:
    """Califica el índice estacional del mes de cosecha con la curva de `market` de `thresholds`.

    Sin índice (cultivo sin producto en SIPSA, central sin temporada o departamento sin central) o con la curva nula
    (la de hoy): `insufficient_data`, nivel y calificación nulos y la razón del contrato (R1). Con curva e índice, la
    razón dice cuánto por encima o por debajo del promedio de su año ha estado el precio de ese mes, y en cuántos años.
    """
    result = score_signal("market", seasonal_index, thresholds)
    # Nivel, calificación y crítica los decide `score_signal` (también los nulos de `insufficient_data`); aquí solo se
    # suman indicadores y razón. `seasonal_index is None` ya da `insufficient_data`: la comprobación es para el tipado.
    if result.status != AVAILABLE or seasonal_index is None:
        return MarketSignalResult(result.status, result.level, result.critical, result.score, (), (NO_DATA_REASON,))
    return MarketSignalResult(
        result.status,
        result.level,
        result.critical,
        result.score,
        (INDICATOR,),
        (_reason(seasonal_index, years),),
    )


def _reason(seasonal_index: float, years: int | None) -> str:
    """Historia, no pronóstico: «ha estado» y «suele estar», nunca «va a estar» ni «subirá»."""
    # round(…, 9) quita el ruido de flotante (0,4999999999) para que el half-up sea simétrico en 0,995 y 1,005.
    pct = round_half_up(round(abs(seasonal_index - 1.0) * 100, 9))
    period = f"En {years} años de precios publicados" if years else "En los años con precios publicados"
    if pct == 0:
        comparison = "ha estado en el promedio de su año"
    else:
        side = "por encima" if seasonal_index >= 1.0 else "por debajo"
        comparison = f"ha estado un {pct} % {side} del promedio de su año"
    return f"{period}, el precio mayorista de este producto en el mes de cosecha {comparison}. {HISTORY_LABEL}"
