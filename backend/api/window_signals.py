"""Las seis señales del P0 de una ventana de siembra: un solo cálculo para la ventana del diagnóstico y para las doce del
orden de las ventanas (HU-076, HU-192: «una ventana del orden y el diagnóstico de esa misma fecha dan las mismas señales
y calificaciones»), y después para cada ciclo de `/rotations` (HU-213).

Es la capa delgada de la API (R6): lee del dataset lo de la zona una sola vez (`signal_zone`) y, por ventana, llama al
motor con todo ya leído. No escribe nada ni guarda la consulta (R9).

Hoy hay cinco señales con motor (`water`, HU-071; `frost`, HU-077; `heat`, HU-190; `soil`, HU-183; `market`, HU-073)
y una sin él (`supply`, HU-072). La que falta sale de `pending_signal`: `insufficient_data`, con nivel y calificación
nulos, sin críticas, y una razón que dice que todavía no se evalúa (R1, R5). Pasa por el mismo camino que las demás: el
semáforo, el orden y las limitaciones no saben que es provisional.

**El suelo** no cambia con la fecha: quien llama calcula la señal una vez por consulta (`soil_signals.soil_for`, con el
suelo del municipio) y la pasa ya hecha (`soil`); todas las ventanas llevan la misma. Sin ventana (un cultivo sin
etapas) no se califica, como las demás señales (HU-076).

**El balance hídrico del agua** se pide en un solo punto, `balance_for`, que se busca como global de este módulo en
cada llamada (las pruebas lo cambian con `monkeypatch`). Es el de HU-144 (`backend/engine/water_balance.py`), que usa la
necesidad de `backend/engine/water_need.py`: una sola cuenta del agua. Recibe la ventana, el clima normal de cada mes de
la fuente que calcula la señal (`ZoneWater.months`, ya con el tipo del motor, `MonthClimate`), la textura y la ficha del
cultivo, de la que sale `root_zone`. Si a algún mes de la ventana le falta la lluvia del año seco de la fuente que calcula la señal o
la ET0, `balance_for` no se llama: sin esos datos no hay balance y nunca se usa la fuente de contraste en su lugar (R1).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from backend.api.climate_signals import ZoneClimate, frost_in, heat_in, zone_climate
from backend.api.market_signal import market_in
from backend.api.water_signals import SourceReading, ZoneWater, water_in, zone_water
from backend.config.thresholds import Thresholds
from backend.dataset import Dataset, Municipality
from backend.engine.diagnosis import SignalOutcome
from backend.engine.signal_score import INSUFFICIENT_DATA
from backend.engine.soil_signal import soil_without_stages
from backend.engine.stages import CropWindow
from backend.engine.traffic_light import SIGNAL_NAMES_ES
from backend.engine.water_balance import DRY, MonthClimate, root_zone, water_balance
from backend.engine.water_signal import WaterBalanceSummary


class SignalResult(SignalOutcome, Protocol):
    """Lo que trae cada señal de una ventana, con los nombres de campo del contrato (sin `counts`, que dependen de los
    pesos y los pone el diagnóstico). Lo cumplen `ClimateSignalResult`, `MarketSignalResult`, `WaterSignal`,
    `SoilSignalResult` y `PendingSignal`.

    `sources` (las fuentes para contrastar, opcional en el contrato) no está aquí: un miembro de un `Protocol` no puede
    ser opcional, y declararlo obligaría a `ClimateSignalResult` y `MarketSignalResult`, que son del motor, a llevar un
    campo de la API que nunca llenan. La señal que trae fuentes cumple además `ContrastedSignal`, y `signal_sources`
    las lee con el tipo (sin `getattr`). Extiende `SignalOutcome` del motor (calificación, razones y limitaciones) con
    `indicators`."""

    indicators: tuple[str, ...]


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


PENDING_SIGNALS = ("supply",)


def pending_reason(name: str) -> str:
    """La razón de una señal del P0 sin motor todavía: dice que esta versión no la evalúa (R5)."""
    return f"Esta versión de AgroSense todavía no evalúa {SIGNAL_NAMES_ES[name]}."


def pending_signal(name: str) -> PendingSignal:
    """Provisional: la señal `name` mientras no exista su motor. Hoy solo `supply`, que se reemplaza cuando llegue
    HU-072. No inventa un nivel ni una calificación (R1): la razón dice que esta versión no la evalúa (R5).
    La limitación es esa misma frase y no «sin datos para la zona»: no faltan datos, falta el motor."""
    return PendingSignal(INSUFFICIENT_DATA, None, False, None, (), (pending_reason(name),))


def balance_for(
    window: CropWindow, climate: Mapping[int, MonthClimate], texture_class: str | None, crop: Mapping[str, Any]
) -> WaterBalanceSummary | None:
    """El balance hídrico de la ventana (HU-144, `backend/engine/water_balance.py`): lo que pide el cultivo y el déficit
    del año seco como rango, con el agua que guarda el suelo según su textura y la raíz del cultivo. Sin textura o sin
    raíz va sin el agua guardada (`retention` falso) y la señal lo dice. None si el balance no se pudo armar (R1)."""
    balance = water_balance(window, dict(climate), texture_class, root_zone(dict(crop)))
    if balance.need_mm is None or balance.deficit_mm.get(DRY) is None:
        return None
    return WaterBalanceSummary(balance.need_mm, balance.deficit_mm[DRY], balance.retention)


@dataclass(frozen=True)
class SignalZone:
    """Lo que las señales leen del dataset para un municipio, una vez por consulta: el clima de heladas y calor, el del
    agua y el municipio, del que sale la central de precios de cada cultivo (`market_signal.market_choice`)."""

    climate: ZoneClimate
    municipality: Municipality
    water: ZoneWater


def signal_zone(dataset: Dataset, municipality: Municipality) -> SignalZone:
    municipality_id = municipality.municipality_id
    return SignalZone(zone_climate(dataset, municipality_id), municipality, zone_water(dataset, municipality_id))


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
    soil: SignalResult,
) -> dict[str, SignalResult]:
    """Las seis señales de la ventana, en el orden del contrato (`water`, `frost`, `heat`, `soil`, `supply`, `market`).

    `crop` es la ficha (`dataset.crops[crop_id]`) y `crop_name` su nombre con artículo («la papa»). `window` nula (un
    cultivo sin etapas publicadas) deja sin datos las que la necesitan (R1). El mercado mira el mes de la cosecha
    estimada (HU-073); sin ventana no hay mes y no hay índice. `irrigated` (nulo: se evalúa como sin riego) y
    `texture_class` (la del lote o la del municipio, `lot_terrain.zone_texture`; nula: sin retención) son del agua.
    `soil` es la señal de suelo ya calculada para la consulta (`soil_signals.soil_for`): no depende de la fecha, pero sin
    ventana no se usa y el suelo es `insufficient_data`, como las demás (`soil_without_stages`).
    """
    balance = _balance(zone.water, window, texture_class, crop)
    return {
        "water": water_in(zone.water, window, balance, irrigated, thresholds, crop_name),
        "frost": frost_in(zone.climate, window, thresholds, crop_name),
        "heat": heat_in(zone.climate, window, crop, thresholds, crop_name),
        # Sin ventana tampoco se califica el suelo, como las demás (HU-076): no hay ventana que diagnosticar.
        "soil": soil if window is not None else soil_without_stages(crop_name),
        "supply": pending_signal("supply"),
        "market": market_in(dataset, zone.municipality, crop_id, crop_name, window.harvest_estimate.month if window else None),
    }
