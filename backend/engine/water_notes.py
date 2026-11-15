"""Los textos del agua que comparten la señal `water` (HU-071, `water_signal.py`) y el plan de agua (HU-146,
`water_plan.py`): la fuente de la lluvia, el aviso sin el agua que guarda el suelo y los meses sin datos.

Viven aparte para que el plan no importe la señal ni la señal el plan: los dos dicen lo mismo con las mismas palabras
(R5). Son funciones puras: no leen archivos ni el dataset (R6).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from backend.engine.sensitive_signal import months_phrase
from backend.engine.stages import WindowMonth

# Sin la textura del suelo o la raíz del cultivo, el balance de HU-144 va sin el agua que guarda el suelo
# (specs/01-reglas.md, «Cómo se califica cada señal»): se calcula igual y se dice. Sin el agua guardada, el déficit no
# es menor que con ella (el suelo solo guarda lo que sobra de un mes para los siguientes), así que el error va del lado
# prudente.
NO_RETENTION = (
    "El agua se calculó sin la que guarda el suelo: puede faltar menos agua de la que se dice. Verifique la humedad del suelo en campo."
)


@dataclass(frozen=True)
class RainSource:
    """La fuente de la lluvia que calcula el agua, como se dice en la razón («GPM IMERG»), los años de su periodo normal
    (del que sale el año seco) y su aviso fijo (`rain_caveat`), si lo tiene."""

    name: str
    first_year: int | None
    last_year: int | None
    caveat: str | None


def in_months(months: Sequence[WindowMonth]) -> str:
    """«en septiembre», «en octubre y diciembre» o «de agosto a noviembre» (sin «en» delante de un tramo)."""
    phrase = months_phrase(months)
    return phrase if phrase.startswith("de ") else f"en {phrase}"


def missing_data(rain: RainSource, no_rain: Sequence[WindowMonth], no_et0: Sequence[WindowMonth]) -> tuple[str, ...]:
    """Por qué no se puede pedir el balance: los meses sin la lluvia de la fuente que calcula el agua (`no_rain`) y los
    meses sin la ET0 (`no_et0`), en orden cronológico. Vacío si no falta nada. Nunca se usa la fuente de contraste en
    lugar de la que falta (R1)."""
    notes = []
    if no_rain:
        notes.append(
            f"Sin la lluvia de {rain.name} para la zona {in_months(no_rain)}: el agua no se evalúa, y no se usa otra fuente en su lugar"
        )
    if no_et0:
        notes.append(f"Sin la evapotranspiración de referencia de la zona {in_months(no_et0)}: el agua no se evalúa")
    return tuple(notes)
