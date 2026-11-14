"""Aptitud del cultivo en la zona por temperatura media anual (HU-191; specs/01-reglas.md, «Aptitud del cultivo en la zona»).

Es un filtro por rango absoluto de temperatura, no una señal (R3). El score es una nota informativa con la curva
de HU-196 y nunca cambia el semáforo ni el orden de las ventanas. Sin la aptitud con fuente, es insufficient_data.
"""

from dataclasses import dataclass

from backend.engine.curve import crop_curve, score_from_curve

SUITABLE = "suitable"
NOT_SUITABLE = "not_suitable"
INSUFFICIENT_DATA = "insufficient_data"

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
