"""Aptitud del cultivo en la zona por temperatura media anual (HU-191; specs/01-reglas.md, «Aptitud del cultivo en la zona»).

Es un filtro por rango absoluto de temperatura, no una señal (R3). El score es una nota informativa con la curva
de HU-196 y nunca cambia el semáforo ni el orden de las ventanas. Sin la aptitud con fuente, es insufficient_data.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.engine.curve import crop_curve, score_from_curve

# `insufficient_data` es también un valor de la aptitud: el mismo de `status`, definido una vez en el motor.
from backend.engine.signal_score import INSUFFICIENT_DATA
from common.text import format_decimal, format_number, of

SUITABLE = "suitable"
NOT_SUITABLE = "not_suitable"

# Qué límite absoluto cruzó un `not_suitable`: lo decide el motor, no quien arma el texto de la API (R6, «la API
# es una capa delgada»). `None` cuando es `suitable` o `insufficient_data`.
BELOW_MIN = "min"
ABOVE_MAX = "max"


@dataclass(frozen=True)
class Suitability:
    """Resultado de la aptitud de un cultivo en una zona: `level` es 'suitable', 'not_suitable' o
    'insufficient_data' (nunca una señal con 'favorable', 'moderate', 'unfavorable'); `score` es la calificación
    informativa de 0 a 100 con la curva EcoCrop, o None si faltan datos. El score no entra al semáforo ni al orden
    de las ventanas (R3). `exceeded` ('min', 'max' o None) dice qué límite absoluto se cruzó cuando no es apto, para
    que quien arme el texto no tenga que repetir la comparación."""

    level: str
    score: float | None
    exceeded: str | None = None


def suitability(
    tmean_min_c: float | None,
    tmean_opt_min_c: float | None,
    tmean_opt_max_c: float | None,
    tmean_max_c: float | None,
    tmean_annual_c: float | None,
) -> Suitability:
    """Decide si un cultivo es apto para una zona solo por si la temperatura media anual cae dentro del rango
    absoluto [tmean_min_c, tmean_max_c], inclusivo en los dos límites. El score es informativo, con la curva
    EcoCrop de HU-196, incluso cuando no es apto.

    Sin alguno de los cinco datos, el level es insufficient_data y el score es None: nunca lanza excepción (R1, R8).
    """
    # Si falta alguno de los cinco: insufficient_data sin score
    if tmean_min_c is None or tmean_opt_min_c is None or tmean_opt_max_c is None or tmean_max_c is None or tmean_annual_c is None:
        return Suitability(INSUFFICIENT_DATA, None)

    # Calcula el score con la curva EcoCrop
    curve = crop_curve(tmean_min_c, tmean_opt_min_c, tmean_opt_max_c, tmean_max_c)
    score = score_from_curve(curve, tmean_annual_c)

    # Rango inclusivo en los dos límites: en el límite exacto, apto (criterio de aceptación de la HU). Esta es la
    # única comparación de los límites en todo el motor: `exceeded` evita que quien arme el texto la repita.
    if tmean_annual_c < tmean_min_c:
        return Suitability(NOT_SUITABLE, score, BELOW_MIN)
    if tmean_annual_c > tmean_max_c:
        return Suitability(NOT_SUITABLE, score, ABOVE_MAX)
    return Suitability(SUITABLE, score)


# Lo que la ficha del cultivo debe traer con fuente para decidir la aptitud.
SUITABILITY_LIMITS = ("tmean_min_c", "tmean_opt_min_c", "tmean_opt_max_c", "tmean_max_c")


@dataclass(frozen=True)
class ZoneTemperatureUsed:
    """La temperatura con que se decidió la aptitud y de dónde salió, ya leída por la API (`lot_terrain`): la del
    municipio (`basis = municipality`) o la del lote corregida por altitud (`basis = lot`). `by_center`: la altitud del
    lote es la de la celda que contiene su centro (un lote más chico que una celda)."""

    basis: str
    tmean_annual_c: float | None
    altitude_m: float | None
    by_center: bool
    municipality_tmean_c: float
    municipality_altitude_m: float | None


def crop_suitability(crop: Mapping[str, Any], tmean_annual_c: float | None) -> Suitability:
    """La aptitud con los límites de la ficha (`SUITABILITY_LIMITS`)."""
    return suitability(*(crop.get(field) for field in SUITABILITY_LIMITS), tmean_annual_c)


def temperature_phrase(zone: ZoneTemperatureUsed) -> str:
    """Qué temperatura se usó, con su altitud: la del municipio o la estimada para el lote, y de dónde se corrigió."""
    municipal = f"{format_decimal(zone.municipality_tmean_c)} °C"
    has_altitude = zone.municipality_altitude_m is not None
    if zone.basis == "municipality":
        municipal_at = f"{municipal}, a {zone.municipality_altitude_m:.0f} m" if has_altitude else municipal
        return f"La temperatura media anual del municipio ({municipal_at})"
    municipal_at = f"{municipal} a {zone.municipality_altitude_m:.0f} m" if has_altitude else municipal
    # Es un reanálisis corregido por altitud, no una medición del lote: por eso «estimada» (R10).
    origin = ", la altitud de la celda de 250 m que contiene su centro" if zone.by_center else ""
    return (
        f"La temperatura media anual estimada para su lote ({format_decimal(zone.tmean_annual_c)} °C, "
        f"a {zone.altitude_m:.0f} m{origin}; corregida desde la del municipio, {municipal_at})"
    )


def suitability_reason(result: Suitability, crop: Mapping[str, Any], crop_name: str, zone: ZoneTemperatureUsed) -> str:
    """La razón de la aptitud (R5). Con `suitable` o `not_suitable`: la temperatura de la zona frente al rango del
    cultivo, sin repetir la comparación (qué límite se cruzó ya lo dice `result.exceeded`). Con `insufficient_data`: qué
    falta, el rango de la ficha o la temperatura de la zona (R1, R8). `crop_name` lleva su artículo («la papa»)."""
    if result.level == INSUFFICIENT_DATA:
        if any(crop.get(field) is None for field in SUITABILITY_LIMITS):
            return f"La ficha {of(crop_name)} no tiene con fuente su rango de temperatura media anual: no se sabe si se da en su zona"
        place = "de su lote" if zone.basis == "lot" else "del municipio"
        return f"Sin la temperatura media anual {place}: no se sabe si {crop_name} se da en su zona"
    temperature = temperature_phrase(zone)
    tmean_min_c, tmean_max_c = crop["tmean_min_c"], crop["tmean_max_c"]
    if result.level == SUITABLE:
        return f"{temperature} está dentro del rango {of(crop_name)} ({format_number(tmean_min_c)} a {format_number(tmean_max_c)} °C)"
    if result.exceeded == ABOVE_MAX:
        return f"{temperature} pasa de la que aguanta {crop_name} (hasta {format_number(tmean_max_c)} °C)"
    return f"{temperature} no alcanza la que necesita {crop_name} (desde {format_number(tmean_min_c)} °C)"
