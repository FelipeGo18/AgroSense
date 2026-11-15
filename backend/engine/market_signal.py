"""La señal de mercado: en cuántos años el precio del mes en que saldría la cosecha estuvo por encima o por debajo del
promedio de su año (HU-073; decisión 17; specs/01-reglas.md, «Señales de una ventana» y «Oferta y mercado sin
calificar»).

Función pura (R6): recibe la historia del precio del mes de cosecha ya resuelta por la API
(`backend/api/market_signal.py`, de `market_month` y de las centrales del manifiesto). No importa la API, el dataset ni
FastAPI, y no abre archivos.

**Sin calificar (decisión 17, aprobada por Felipe el 15 de noviembre de 2026).** Ninguna fuente externa dice qué es un
«precio bajo» en el mercado mayorista, así que la señal no tiene curva (`curve: null` en `thresholds.yaml`). Con la
historia, la señal es `available` con `level` y `score` nulos y `critical` falso: el dato existe, pero no se califica
(R1 separa disponibilidad y nivel). Así nunca cambia la luz, la acción, el factor limitante ni el promedio ponderado:
`rated_signals` (`signal_score.py`) solo deja entrar señales con calificación. Sin historia, `insufficient_data`.

**Cuenta años.** La razón dice en cuántos de los años completos el precio del mes quedó por encima y por debajo del
promedio de su año, de qué año a qué año y cuánto en promedio (el índice estacional). Un mes que quedó igual al
promedio (el cociente redondeado a 3 decimales da 1) no cuenta en ninguno de los dos, y si hubo alguno la razón lo dice.
Es historia de precios mayoristas, nunca un pronóstico (decisión 4), y nunca dice «precio bajo» ni «precio alto» (R5).

**Dataset anterior a HU-073.** Si la historia llega sin `years_above` o sin `years_below` (un `market_month` publicado
antes de la decisión 17), la señal no inventa el conteo: es `insufficient_data` y lo dice como razón y como limitación
(R1).

No trae `counts`: si la señal cuenta para la luz lo deciden los pesos en el semáforo (HU-074), no esta señal.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, round_half_up
from common.months import month_name

INDICATORS = ("seasonal_index", "years_above", "years_below")
DEPARTMENT = "department"
CROP_OVERRIDE = "crop_override"
MARKET_BASES = frozenset({DEPARTMENT, CROP_OVERRIDE})

NO_DATA_REASON = "Sin datos de mercado para la zona"
UNRATED_REASON = "Precio sin calificar: ninguna fuente publica qué es un precio bajo en el mercado mayorista"
UNRATED_LIMITATION = "La oferta y el mercado se muestran sin calificar: no cambian la luz"
NO_COUNT_REASON = (
    "Los precios publicados no dicen en cuántos años el mes de la cosecha estuvo por encima o por debajo del promedio de "
    "su año: el mercado no se muestra hasta que se actualicen los datos"
)
HISTORY_LABEL = "Así fue en la historia: no es un pronóstico del precio"
SOURCE_LABEL = "Fuente: DANE"


@dataclass(frozen=True)
class PriceHistory:
    """La historia del precio del mes de cosecha en la central de referencia, con los campos de
    `signals.market.price_history` del contrato. Además, para las razones: `product_name`, el producto como lo dice la
    razón («la papa negra»), y `override_reason`, por qué se usa la central de `crop_market_overrides` (solo con
    `market_basis = crop_override`). Ninguno de los dos va en la respuesta.

    `years_above` y `years_below` son nulos solo en un dataset publicado antes de HU-073."""

    market_id: str
    market: str
    market_basis: str
    product_id: str
    month: int
    seasonal_index: float
    years: int
    years_above: int | None
    years_below: int | None
    first_year: int | None
    last_year: int | None
    source_id: str
    product_name: str
    override_reason: str | None = None

    @property
    def counted(self) -> bool:
        """Si trae los años contados (un dataset publicado desde HU-073)."""
        return self.years_above is not None and self.years_below is not None and self.years > 0


@dataclass(frozen=True)
class MarketSignalResult:
    """La señal `market` de una ventana, con los nombres de campo del contrato (specs/02-contratos.md). `price_history`
    es nulo sin historia. `limitations` tiene la misma forma que en las demás señales de la ventana."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    price_history: PriceHistory | None = None


def market_signal(history: PriceHistory | None) -> MarketSignalResult:
    """La señal de mercado del mes de cosecha.

    - Sin historia (cultivo sin producto en SIPSA, central sin temporada, departamento sin central o sin ventana):
      `insufficient_data`, nivel y calificación nulos y la razón del contrato, `NO_DATA_REASON` (R1).
    - Con historia sin los años contados (dataset anterior a HU-073): `insufficient_data`, con `NO_COUNT_REASON` como
      razón y como limitación. No se inventa el conteo (R1).
    - Con historia: `available`, sin calificar (`level` y `score` nulos, `critical` falso), con `price_history`, la razón
      de que no se califica, la de la central por cultivo si aplica y la de los años.
    """
    if history is None:
        return MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))
    if history.market_basis not in MARKET_BASES:
        raise ValueError(f"base de la central desconocida: {history.market_basis!r}")
    if not history.counted:
        return MarketSignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_COUNT_REASON,), (NO_COUNT_REASON,))
    reasons = [UNRATED_REASON]
    if history.market_basis == CROP_OVERRIDE and history.override_reason:
        reasons.append(f"Se usa la central de {history.market}: {history.override_reason}")
    reasons.append(history_reason(history))
    return MarketSignalResult(AVAILABLE, None, False, None, INDICATORS, tuple(reasons), (UNRATED_LIMITATION,), history)


def short_market(name: str) -> str:
    """El nombre corto de la central, sin el detalle entre paréntesis: «Corabastos (Bogotá)» → «Corabastos»."""
    return name.split(" (", 1)[0]


def history_reason(history: PriceHistory) -> str:
    """«En Corabastos, en diciembre (el mes en que saldría su cosecha), el precio de la papa negra estuvo por encima del
    promedio de su año en 3 de 5 años (2021–2025) y por debajo en 2; en promedio, 7 % por encima. Así fue en la
    historia: no es un pronóstico del precio. Fuente: DANE». Historia, no pronóstico: nunca «va a estar» ni «subirá»."""
    above, below = history.years_above or 0, history.years_below or 0
    period = f" ({history.first_year}–{history.last_year})" if history.first_year and history.last_year else ""
    ties = history.years - above - below
    tie_text = f", y en {ties} quedó en el promedio de su año" if ties > 0 else ""
    return (
        f"En {short_market(history.market)}, en {month_name(history.month)} (el mes en que saldría su cosecha), el precio de "
        f"{history.product_name} estuvo por encima del promedio de su año en {above} de {history.years} años{period} y por "
        f"debajo en {below}{tie_text}; en promedio, {_average(history.seasonal_index)}. {HISTORY_LABEL}. {SOURCE_LABEL}"
    )


def _average(seasonal_index: float) -> str:
    # round(…, 9) quita el ruido de flotante (0,4999999999) para que el half-up sea simétrico en 0,995 y 1,005.
    pct = round_half_up(round(abs(seasonal_index - 1.0) * 100, 9))
    if pct == 0:
        return "como el promedio de su año"
    return f"{pct} % {'por encima' if seasonal_index > 1.0 else 'por debajo'}"


def harvest_years_share(history: PriceHistory | None) -> float | None:
    """El porcentaje de años en que el mes de cosecha tuvo mejor precio que el resto de su año: 100 × `years_above` /
    `years` (HU-241, decisión 17). Nulo sin historia o sin los años contados (R1). Es una frecuencia, como la de las
    heladas: no usa ningún corte y no dice cuánto se va a ganar."""
    if history is None or not history.counted or history.years_above is None:
        return None
    return 100 * history.years_above / history.years
