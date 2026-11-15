"""La señal de oferta: cuánto se sembró del cultivo en el municipio según la estadística oficial, sin calificar (HU-072,
decisión 17; specs/01-reglas.md, «Señales de una ventana»).

Función pura (R6): recibe el semestre de EVA ya leído por la API (`backend/api/supply_signal.py`, de `supply_semester`:
el área sembrada, la variación de HU-032, si es preliminar y si repite el valor del año anterior). No importa la API,
el dataset ni FastAPI, y no abre archivos.

**No califica.** Ninguna fuente publica desde qué aumento del área sembrada hay sobreoferta, y EVA no alcanza para
decirlo (`docs/investigacion-decisiones.md`, 5f). Con dato, la señal es `available` con nivel y calificación nulos y
`critical` falso: se muestra, pero nunca cambia la luz, la acción, el factor limitante ni el promedio ponderado, porque
el semáforo y el orden solo leen señales con calificación (`rated_signals`). Va a las limitaciones con
`UNRATED_LIMITATION`, la misma frase que el mercado (HU-073). Sin dato: `insufficient_data` (R1).

Las razones dicen el dato y de dónde sale; nunca «mucho», «poco» ni «sobreoferta» como veredicto (R5). Es estadística
del pasado, no un pronóstico del precio (decisión 4).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.engine.market_signal import UNRATED_LIMITATION
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, round_half_up
from common.text import format_number

NO_DATA_REASON = "Sin datos de oferta para la zona"
UNRATED_REASON = "Oferta sin calificar: ninguna fuente publica desde qué aumento del área sembrada hay sobreoferta"
INDICATORS = ("planted_ha", "planted_change_pct")


@dataclass(frozen=True)
class SupplySemester:
    """El semestre de EVA en que cae la siembra (`window.supply_semester` del contrato). `planted_change_pct` es el de
    HU-032, nulo sin semestres anteriores; `same_as_previous` es nulo sin el mismo semestre del año anterior.
    `complete_baseline` es falso cuando la variación se calculó con menos de tres semestres anteriores (`quality =
    partial`): la razón no dice «los tres»."""

    year: int
    semester: str
    preliminary: bool
    planted_ha: float
    planted_change_pct: float | None
    same_as_previous: bool | None
    complete_baseline: bool = True


@dataclass(frozen=True)
class SupplySignalResult:
    """La señal `supply` de una ventana, con los nombres de campo del contrato (specs/02-contratos.md)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    # El semestre que respalda la señal: la API lo pone en `window.supply_semester`. None sin dato.
    semester: SupplySemester | None = None


def supply_signal(semester: SupplySemester | None, crop_label: str) -> SupplySignalResult:
    """La señal sin calificar del semestre en que cae la siembra.

    `semester` es la fila de EVA del cultivo en el municipio (el último año con dato de ese semestre), o None: entonces
    `insufficient_data`, nivel y calificación nulos y `NO_DATA_REASON` (R1). `crop_label` es el nombre del cultivo sin
    artículo, como lo dice la razón («420 ha de papa»).
    """
    if semester is None:
        return SupplySignalResult(INSUFFICIENT_DATA, None, False, None, (), (NO_DATA_REASON,))
    indicators = INDICATORS if semester.planted_change_pct is not None else INDICATORS[:1]
    return SupplySignalResult(
        AVAILABLE,
        None,
        False,
        None,
        indicators,
        (UNRATED_REASON, _data_reason(semester, crop_label)),
        (UNRATED_LIMITATION,),
        semester,
    )


def _data_reason(semester: SupplySemester, crop_label: str) -> str:
    """«En 2025 B (último dato, preliminar) EVA registra 420 ha de papa en su municipio, 35 % más que el promedio de los
    tres semestres B anteriores». Con `same_as_previous`, suma «EVA trae el mismo valor que en 2024 B»."""
    label = "último dato, preliminar" if semester.preliminary else "último dato"
    text = (
        f"En {semester.year} {semester.semester} ({label}) EVA registra {_hectares(semester.planted_ha)} ha de {crop_label} en su municipio"
    )
    if semester.planted_change_pct is not None:
        text += f", {_change(semester)}"
    if semester.same_as_previous:
        text += f". EVA trae el mismo valor que en {semester.year - 1} {semester.semester}"
    return text


def _hectares(planted_ha: float) -> str:
    """El área con un decimal si no es entera: «420», «0,4». A entero, de 0,1 a 0,4 ha diría «0 ha» cuando sí hubo
    siembra (R5; revisión del PR #174). `round(…, 9)` quita el ruido de flotante antes del half-up."""
    return format_number(round_half_up(round(planted_ha * 10, 9)) / 10)


def _change(semester: SupplySemester) -> str:
    # round(…, 9) quita el ruido de flotante para que el half-up sea simétrico.
    pct = round_half_up(round(abs(semester.planted_change_pct or 0.0), 9))
    baseline = (
        f"el promedio de los tres semestres {semester.semester} anteriores"
        if semester.complete_baseline
        else f"el promedio de los semestres {semester.semester} anteriores con dato (menos de tres)"
    )
    if pct == 0:
        return f"igual que {baseline}"
    return f"{pct} % {'más' if (semester.planted_change_pct or 0.0) > 0 else 'menos'} que {baseline}"
