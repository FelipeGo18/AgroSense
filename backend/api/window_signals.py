"""Las seis señales del P0 de una ventana de siembra: un solo cálculo para la ventana del diagnóstico y para las doce del
orden de las ventanas (HU-076, HU-192: «una ventana del orden y el diagnóstico de esa misma fecha dan las mismas señales
y calificaciones»), y después para cada ciclo de `/rotations` (HU-213).

Es la capa delgada de la API (R6): lee del dataset lo de la zona una sola vez (`signal_zone`) y, por ventana, llama al
motor con todo ya leído. No escribe nada ni guarda la consulta (R9).

Hoy hay tres señales con motor (`frost`, HU-077; `heat`, HU-190; `market`, HU-073) y tres sin él (`water`, HU-071;
`soil`, HU-183; `supply`, HU-072). Las que faltan salen de `pending_signal`: `insufficient_data`, con nivel y
calificación nulos, sin críticas, y una razón que dice que todavía no se evalúan (R1, R5). Pasan por el mismo camino
que las demás: el semáforo, el orden y las limitaciones no saben que son provisionales.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from backend.api.climate_signals import ZoneClimate, frost_in, heat_in, zone_climate
from backend.api.market_signal import market_for, seasonal_index
from backend.config.thresholds import Thresholds
from backend.dataset import Dataset, Municipality
from backend.engine.market_signal import market_signal
from backend.engine.signal_score import INSUFFICIENT_DATA, SignalScore
from backend.engine.stages import CropWindow
from backend.engine.traffic_light import SIGNAL_NAMES_ES


class SignalResult(Protocol):
    """Lo que trae cada señal de una ventana, con los nombres de campo del contrato (sin `counts`, que dependen de los
    pesos y los pone el diagnóstico). Lo cumplen `ClimateSignalResult`, `MarketSignalResult` y `PendingSignal`."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class PendingSignal:
    """Una señal del P0 que todavía no tiene motor: siempre `insufficient_data` (R1)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()


def pending_reason(name: str) -> str:
    """La razón de una señal del P0 sin motor todavía: dice que esta versión no la evalúa (R5)."""
    return f"Esta versión de AgroSense todavía no evalúa {SIGNAL_NAMES_ES[name]}."


def pending_signal(name: str) -> PendingSignal:
    """Provisional: la señal `name` mientras no exista su motor. Se reemplaza, una por una, cuando lleguen `water`
    (HU-071, con el balance hídrico de HU-144), `soil` (HU-183) y `supply` (HU-072). No inventa un nivel ni una
    calificación (R1): la razón dice que esta versión no la evalúa (R5), y la limitación de «sin datos» la agrega el
    diagnóstico como a cualquier otra señal sin datos (`missing_data_limitations`)."""
    return PendingSignal(INSUFFICIENT_DATA, None, False, None, (), (pending_reason(name),))


@dataclass(frozen=True)
class SignalZone:
    """Lo que las señales leen del dataset para un municipio, una vez por consulta: el clima de heladas y calor y la
    central de precios de su departamento."""

    climate: ZoneClimate
    market_id: str | None


def signal_zone(dataset: Dataset, municipality: Municipality) -> SignalZone:
    return SignalZone(zone_climate(dataset, municipality.municipality_id), market_for(dataset, municipality))


def window_signals(
    dataset: Dataset,
    zone: SignalZone,
    crop_id: str,
    crop: dict[str, Any],
    crop_name: str,
    window: CropWindow | None,
    thresholds: Thresholds,
) -> dict[str, SignalResult]:
    """Las seis señales de la ventana, en el orden del contrato (`water`, `frost`, `heat`, `soil`, `supply`, `market`).

    `crop` es la ficha (`dataset.crops[crop_id]`) y `crop_name` su nombre con artículo («la papa»). `window` nula (un
    cultivo sin etapas publicadas) deja sin datos las que la necesitan (R1). El mercado mira el mes de la cosecha
    estimada (HU-073); sin ventana no hay mes y no hay índice.

    Cuando llegue `water` (HU-071), esta función recibe también `irrigated` y el suelo de la zona o del lote; hoy no los
    usa ninguna señal y por eso no los pide.
    """
    index, years = seasonal_index(dataset, crop_id, zone.market_id, window.harvest_estimate.month) if window else (None, None)
    return {
        "water": pending_signal("water"),
        "frost": frost_in(zone.climate, window, thresholds, crop_name),
        "heat": heat_in(zone.climate, window, crop, thresholds, crop_name),
        "soil": pending_signal("soil"),
        "supply": pending_signal("supply"),
        "market": market_signal(index, years, thresholds),
    }


def signal_scores(signals: Mapping[str, SignalResult]) -> dict[str, SignalScore]:
    """Las calificaciones que leen el semáforo y el orden de las ventanas (`backend/engine/signal_score.py`)."""
    return {name: SignalScore(signal.status, signal.score, signal.level, signal.critical) for name, signal in signals.items()}
