"""La señal de mercado: la historia del precio en el mes en que saldría la cosecha, sin calificar (HU-073, decisión 17;
specs/01-reglas.md, «Señales de una ventana»).

Función pura (R6): recibe la historia del precio ya resuelta por la API (`backend/api/market_signal.py`, de
`market_month`: la central, el producto y los años por encima y por debajo del promedio de su año) y el nombre del
cultivo. No importa la API, el dataset ni FastAPI, y no abre archivos.

**No califica.** Ninguna fuente publica qué es un precio bajo en el mercado mayorista (la propuesta de curva quedó en
`docs/investigacion-decisiones.md`, 5e, y la evidencia de la decisión en 5f). Con historia, la señal es `available` con
nivel y calificación nulos y `critical` falso: se muestra, pero nunca cambia la luz, la acción, el factor limitante ni el
promedio ponderado, porque el semáforo y el orden solo leen señales con calificación (`rated_signals`). Va a las
limitaciones con `UNRATED_LIMITATION`, la misma frase que la oferta (HU-072). Sin historia: `insufficient_data` (R1).

Es historia de precios mayoristas, nunca un pronóstico (decisión 4): la razón cuenta en cuántos años el mes estuvo por
encima o por debajo del promedio de su año, en qué central y en qué periodo, y nunca dice «precio bajo» ni «precio alto»
como veredicto (R5).

No trae `counts`: si la señal cuenta para la luz lo deciden los pesos en el semáforo (HU-074), no esta señal.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, round_half_up
from common.months import month_name
from common.text import of

INDICATORS = ("seasonal_index", "years_above", "years_below")
NO_DATA_REASON = "Sin datos de mercado para la zona"
UNRATED_REASON = "Precio sin calificar: ninguna fuente publica qué es un precio bajo en el mercado mayorista"
UNRATED_LIMITATION = "La oferta y el mercado se muestran sin calificar: no cambian la luz"
HISTORY_LABEL = "Así fue en la historia: no es un pronóstico del precio. Fuente: DANE"
# Un `market_month` publicado antes de HU-073 no trae los años contados: el motor no los inventa (R1, R5).
NO_COUNT_REASON = (
    "Los precios publicados no dicen en cuántos años el mes de la cosecha estuvo por encima o por debajo del promedio "
    "de su año: el mercado no se muestra hasta que se actualicen los datos"
)

# De dónde sale la central (`price_history.market_basis`): la del departamento (`region.department_markets`) o la del
# cultivo cuando la del departamento no lo publica (`region.crop_market_overrides`).
DEPARTMENT = "department"
CROP_OVERRIDE = "crop_override"


@dataclass(frozen=True)
class PriceHistory:
    """`signals.market.price_history` del contrato (specs/02-contratos.md), con los nombres de campo del contrato."""

    market_id: str
    market: str
    market_basis: str
    product_id: str
    month: int
    seasonal_index: float
    years: int
    # Nulos en un `market_month` anterior a HU-073: entonces la señal es `insufficient_data` (`NO_COUNT_REASON`).
    years_above: int | None
    years_below: int | None
    first_year: int | None
    last_year: int | None
    source_id: str


@dataclass(frozen=True)
class MarketSignalResult:
    """La señal `market` de una ventana, con los nombres de campo del contrato (specs/02-contratos.md)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    price_history: PriceHistory | None = None


def market_signal(
    history: PriceHistory | None,
    crop_name: str,
    product_name: str | None = None,
    override_reason: str | None = None,
) -> MarketSignalResult:
    """La señal sin calificar del mes de cosecha.

    `history` es la fila de `market_month` del cultivo en su central y en el mes de la cosecha estimada, o None (cultivo
    sin producto en SIPSA, departamento sin central o central sin fila del cultivo): entonces `insufficient_data`, nivel
    y calificación nulos y la razón del contrato, `NO_DATA_REASON` (R1). `crop_name` es el nombre con artículo («la
    papa»); `product_name`, el del producto de SIPSA con el mismo artículo («la papa negra»), si se conoce: la razón usa
    ese y, sin él, el del cultivo. `override_reason` es el porqué de usar otra central (`crop_market_overrides`): con
    `market_basis = crop_override` la razón lo dice, antes de la historia. Con historia sin los años contados (dataset
    anterior a HU-073): `insufficient_data` con `NO_COUNT_REASON`, también en las limitaciones.
    """
    if history is None:
        return MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))
    if history.years_above is None or history.years_below is None:
        return MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_COUNT_REASON,), (NO_COUNT_REASON,))
    reasons = [UNRATED_REASON]
    if history.market_basis == CROP_OVERRIDE and override_reason:
        reasons.append(f"Se usa {_short(history.market)}: {override_reason}")
    reasons.append(_history_reason(history, crop_name, product_name))
    return MarketSignalResult(AVAILABLE, None, False, None, INDICATORS, tuple(reasons), (UNRATED_LIMITATION,), history)


def _history_reason(history: PriceHistory, crop_name: str, product_name: str | None) -> str:
    """«En Corabastos, en septiembre (el mes en que saldría su cosecha), el precio de la papa negra estuvo por encima
    del promedio de su año en 0 de 5 años (2021–2025) y por debajo en 5; en promedio, 23 % por debajo. Así fue en la
    historia: no es un pronóstico del precio. Fuente: DANE»."""
    period = f" ({history.first_year}–{history.last_year})" if history.first_year and history.last_year else ""
    # round(…, 9) quita el ruido de flotante (0,4999999999) para que el half-up sea simétrico en 0,995 y 1,005.
    pct = round_half_up(round(abs(history.seasonal_index - 1.0) * 100, 9))
    # Un año en que el mes quedó justo en el promedio de su año no cuenta en ninguno de los dos (contrato): se dice,
    # para que los años cuadren (revisión de Felipe del PR #158).
    equal = history.years - (history.years_above or 0) - (history.years_below or 0)
    tie = f", y en {equal} quedó igual" if equal > 0 else ""
    if pct == 0:
        average = "en promedio, igual al de su año"
    else:
        average = f"en promedio, {pct} % por {'encima' if history.seasonal_index > 1.0 else 'debajo'}"
    return (
        f"En {_short(history.market)}, en {month_name(history.month)} (el mes en que saldría su cosecha), el precio "
        f"{of(product_name or crop_name)} estuvo por encima del promedio de su año en {history.years_above} de {history.years} "
        f"años{period} y por debajo en {history.years_below}{tie}; {average}. {HISTORY_LABEL}"
    )


def _short(market: str) -> str:
    """El nombre corto de la central, como en los botones de la web: «Corabastos (Bogotá)» → «Corabastos»."""
    return market.split(" (", 1)[0]
