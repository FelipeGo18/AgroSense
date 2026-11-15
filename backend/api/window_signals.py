"""Las seis señales del P0 de una ventana de siembra: un solo cálculo para la ventana del diagnóstico y para las doce del
orden de las ventanas (HU-076, HU-192: «una ventana del orden y el diagnóstico de esa misma fecha dan las mismas señales
y calificaciones»), y después para cada ciclo de `/rotations` (HU-213).

Es la capa delgada de la API (R6): lee del dataset lo de la zona una sola vez (`signal_zone`) y, por ventana, llama al
motor con todo ya leído. No escribe nada ni guarda la consulta (R9).

Hoy hay cuatro señales con motor (`water`, HU-071; `frost`, HU-077; `heat`, HU-190; `market`, HU-073) y dos sin él
(`soil`, HU-183; `supply`, HU-072). Las que faltan salen de `pending_signal`: `insufficient_data`, con nivel y
calificación nulos, sin críticas, y una razón que dice que todavía no se evalúan (R1, R5). Pasan por el mismo camino
que las demás: el semáforo, el orden y las limitaciones no saben que son provisionales.

**El balance hídrico del agua** se pide en un solo punto, `balance_for`, que se busca como global de este módulo en
cada llamada (las pruebas lo cambian con `monkeypatch`). Es el de HU-144 (`backend/engine/water_balance.py`), que usa la
necesidad de `backend/engine/water_need.py`: una sola cuenta del agua. Recibe la ventana, el clima normal de cada mes de
la fuente que calcula la señal (`WaterMonth`, con la forma de `MonthClimate`), la textura y la ficha del cultivo, de la
que sale `root_zone`. Si a algún mes de la ventana le falta la lluvia del año seco de la fuente que calcula la señal o
la ET0, `balance_for` no se llama: sin esos datos no hay balance y nunca se usa la fuente de contraste en su lugar (R1).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from backend.api.climate_signals import ZoneClimate, frost_in, heat_in, zone_climate
from backend.api.market_signal import market_for, seasonal_index
from backend.api.water_signals import SourceReading, WaterMonth, ZoneWater, water_in, zone_water
from backend.config.thresholds import Thresholds
from backend.dataset import Dataset, Municipality
from backend.engine.market_signal import market_signal
from backend.engine.signal_score import INSUFFICIENT_DATA, SignalScore
from backend.engine.stages import CropWindow
from backend.engine.traffic_light import SIGNAL_NAMES_ES
from backend.engine.water_balance import DRY, MonthClimate, root_zone, water_balance
from backend.engine.water_signal import WaterBalanceSummary


class SignalResult(Protocol):
    """Lo que trae cada señal de una ventana, con los nombres de campo del contrato (sin `counts`, que dependen de los
    pesos y los pone el diagnóstico). Lo cumplen `ClimateSignalResult`, `MarketSignalResult`, `WaterSignal` y
    `PendingSignal`.

    `sources` (las fuentes para contrastar, opcional en el contrato) no está aquí: un miembro de un `Protocol` no puede
    ser opcional, y declararlo obligaría a `ClimateSignalResult` y `MarketSignalResult`, que son del motor, a llevar un
    campo de la API que nunca llenan. La señal que trae fuentes cumple además `ContrastedSignal`, y `signal_sources`
    las lee con el tipo (sin `getattr`)."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]


@runtime_checkable
class ContrastedSignal(SignalResult, Protocol):
    """Una señal que además trae `sources`, las fuentes del indicador para contrastar (contrato, «Respuesta de
    diagnóstico»): en el MVP, solo el agua (`WaterSignal`); la oferta, cuando las tenga (HU-072)."""

    sources: tuple[SourceReading, ...]


def signal_sources(result: SignalResult) -> tuple[SourceReading, ...] | None:
    """Las fuentes para contrastar de una señal, o nulo si no las trae (el contrato omite `sources` en esas)."""
    return result.sources if isinstance(result, ContrastedSignal) else None


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


PENDING_SIGNALS = ("soil", "supply")


def pending_reason(name: str) -> str:
    """La razón de una señal del P0 sin motor todavía: dice que esta versión no la evalúa (R5)."""
    return f"Esta versión de AgroSense todavía no evalúa {SIGNAL_NAMES_ES[name]}."


def pending_signal(name: str) -> PendingSignal:
    """Provisional: la señal `name` mientras no exista su motor. Se reemplaza, una por una, cuando lleguen `soil`
    (HU-183) y `supply` (HU-072). No inventa un nivel ni una
    calificación (R1): la razón dice que esta versión no la evalúa (R5).
    La limitación es esa misma frase y no «sin datos para la zona»: no faltan datos, falta el motor."""
    return PendingSignal(INSUFFICIENT_DATA, None, False, None, (), (pending_reason(name),))


def balance_for(
    window: CropWindow, climate: Mapping[int, WaterMonth], texture_class: str | None, crop: Mapping[str, Any]
) -> WaterBalanceSummary | None:
    """El balance hídrico de la ventana (HU-144, `backend/engine/water_balance.py`): lo que pide el cultivo y el déficit
    del año seco como rango, con el agua que guarda el suelo según su textura y la raíz del cultivo. Sin textura o sin
    raíz va sin el agua guardada (`retention` falso) y la señal lo dice. None si el balance no se pudo armar (R1)."""
    months = {month: MonthClimate(c.et0_mm, c.rain_normal_mm, c.rain_dry_mm) for month, c in climate.items()}
    balance = water_balance(window, months, texture_class, root_zone(dict(crop)))
    if balance.need_mm is None or balance.deficit_mm.get(DRY) is None:
        return None
    return WaterBalanceSummary(balance.need_mm, balance.deficit_mm[DRY], balance.retention)


@dataclass(frozen=True)
class SignalZone:
    """Lo que las señales leen del dataset para un municipio, una vez por consulta: el clima de heladas y calor, el del
    agua y la central de precios de su departamento."""

    climate: ZoneClimate
    market_id: str | None
    water: ZoneWater


def signal_zone(dataset: Dataset, municipality: Municipality) -> SignalZone:
    municipality_id = municipality.municipality_id
    return SignalZone(zone_climate(dataset, municipality_id), market_for(dataset, municipality), zone_water(dataset, municipality_id))


def _balance(zone: ZoneWater, window: CropWindow | None, texture_class: str | None, crop: Mapping[str, Any]) -> WaterBalanceSummary | None:
    """El balance de la ventana, solo si hay ventana y no le falta ningún dato a la fuente que calcula la señal (R1).
    `balance_for` se busca en el módulo en cada llamada (ver el módulo)."""
    if window is None or zone.missing(window):
        return None
    return balance_for(window, zone.months(), texture_class, crop)


def window_signals(
    dataset: Dataset,
    zone: SignalZone,
    crop_id: str,
    crop: dict[str, Any],
    crop_name: str,
    window: CropWindow | None,
    thresholds: Thresholds,
    irrigated: bool | None,
    texture_class: str | None,
) -> dict[str, SignalResult]:
    """Las seis señales de la ventana, en el orden del contrato (`water`, `frost`, `heat`, `soil`, `supply`, `market`).

    `crop` es la ficha (`dataset.crops[crop_id]`) y `crop_name` su nombre con artículo («la papa»). `window` nula (un
    cultivo sin etapas publicadas) deja sin datos las que la necesitan (R1). El mercado mira el mes de la cosecha
    estimada (HU-073); sin ventana no hay mes y no hay índice. `irrigated` (nulo: se evalúa como sin riego) y
    `texture_class` (la del lote o la del municipio, `lot_terrain.zone_texture`; nula: sin retención) son del agua.
    """
    index, years = seasonal_index(dataset, crop_id, zone.market_id, window.harvest_estimate.month) if window else (None, None)
    balance = _balance(zone.water, window, texture_class, crop)
    return {
        "water": water_in(zone.water, window, balance, irrigated, thresholds, crop_name),
        "frost": frost_in(zone.climate, window, thresholds, crop_name),
        "heat": heat_in(zone.climate, window, crop, thresholds, crop_name),
        "soil": pending_signal("soil"),
        "supply": pending_signal("supply"),
        "market": market_signal(index, years, thresholds),
    }


def signal_scores(signals: Mapping[str, SignalResult]) -> dict[str, SignalScore]:
    """Las calificaciones que leen el semáforo y el orden de las ventanas (`backend/engine/signal_score.py`)."""
    return {name: SignalScore(signal.status, signal.score, signal.level, signal.critical) for name, signal in signals.items()}
