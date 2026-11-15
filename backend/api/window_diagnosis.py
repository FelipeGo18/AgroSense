"""El diagnóstico de una ventana de siembra con la forma del contrato: un solo camino para `/diagnostics` (HU-076) y
para cada ciclo de una estrategia (HU-213: «el diagnóstico de un ciclo sale de la misma función del motor que
`/diagnostics`»).

Es la capa delgada de la API (R6): `window_query` lee del dataset una sola vez lo que no cambia entre ventanas de una
misma consulta (la temperatura y la textura de la zona o del lote, el clima de las señales, el riego y los pesos), y
`diagnose_window` llama al motor para un cultivo y una fecha (la aptitud, las seis señales y las dos luces, HU-074,
HU-191) y arma el `DiagnosisCore`. No lee el reloj, no escribe nada ni guarda la consulta (R4, R9). Las mejores ventanas
(`best_windows`) son solo de `/diagnostics`: un ciclo no las trae.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.accounts.farm_models import Lot
from backend.api.calc_models import DiagnosisCore, LightResult, Signal, SourceValue, SuitabilityResult, Window
from backend.api.errors import ApiError
from backend.api.lot_terrain import ZoneTemperature, zone_temperature, zone_texture
from backend.api.soil_signals import soil_for
from backend.api.window_signals import SignalResult, SignalZone, signal_sources, signal_zone, window_signals
from backend.config.thresholds import Thresholds, get_thresholds
from backend.config.versions import rules_version
from backend.dataset import Dataset, Municipality
from backend.engine.diagnosis import Diagnosis, diagnose, evaluates_windows, irrigation_used
from backend.engine.signal_score import counts, round_half_up, weight_of
from backend.engine.stages import CropWindow, crop_window
from backend.engine.suitability import Suitability, ZoneTemperatureUsed, crop_suitability, suitability_reason
from backend.engine.traffic_light import DEFAULT, TrafficLight


def get_article(crop: Mapping[str, Any]) -> str:
    """El artículo ('el' o 'la') del nombre del cultivo, tal como lo trae el catálogo (`article`).

    Es un dato de diseño del catálogo (`catalog/crops.yaml`, fuente `agrosense_diseno`), no una heurística: un
    cultivo que no lo trae es un dataset sin reconstruir o una ficha incompleta, no algo para adivinar en silencio.
    """
    article = crop.get("article")
    if not article:
        crop_id = crop.get("crop_id", "?")
        raise ApiError(
            500,
            "internal_error",
            "Algo falló de nuestro lado. Intente de nuevo en un momento.",
            log=f"Al cultivo {crop_id!r} le falta `article` en el catálogo: reconstruya el dataset.",
        )
    return article


def crop_name(crop: Mapping[str, Any]) -> str:
    """El nombre del cultivo con su artículo, como lo dicen las razones: «la papa», «el haba»."""
    return f"{get_article(crop)} {crop.get('name_es', 'cultivo').lower()}"


def suitability_result(
    crop: Mapping[str, Any], result: Suitability, zone: ZoneTemperature, municipality: Municipality
) -> SuitabilityResult:
    """La aptitud con la forma del contrato; la razón la escribe el motor (`suitability_reason`)."""
    used = ZoneTemperatureUsed(
        zone.basis, zone.tmean_annual_c, zone.altitude_m, zone.by_center, municipality.tmean_annual_c, municipality.altitude_m
    )
    return SuitabilityResult(
        level=result.level,
        score=None if result.score is None else round_half_up(result.score),
        basis=zone.basis,
        tmean_annual_c=zone.tmean_annual_c,
        altitude_m=zone.altitude_m,
        reasons=[suitability_reason(result, dict(crop), crop_name(crop), used)],
    )


def light_result(result: TrafficLight, weights_basis: str) -> LightResult:
    """La luz del motor con la forma del contrato. `weights_basis` lo pone la API: el motor solo lo usa en las razones."""
    return LightResult(
        light=result.light,
        action=result.action,
        high_risk=result.high_risk,
        weights_basis=weights_basis,
        limiting_signal=result.limiting_signal,
        reasons=list(result.reasons),
    )


def signal_result(name: str, result: SignalResult, weights: Mapping[str, int]) -> Signal:
    """Una señal con la forma del contrato. `counts` es si cuenta para la luz con los pesos de `overall` (contrato,
    «Respuesta de diagnóstico»), con la misma definición que el semáforo y el orden (`counts` del motor). `sources` solo
    viene en la señal que trae varias fuentes para contrastar (en el MVP, el agua); en las demás es nulo."""
    sources = signal_sources(result)
    return Signal(
        status=result.status,
        level=result.level,
        critical=result.critical,
        score=result.score,
        counts=counts(name, weight_of(weights, name), result.critical),
        indicators=list(result.indicators),
        reasons=list(result.reasons),
        sources=None if sources is None else [SourceValue.model_validate(source, from_attributes=True) for source in sources],
    )


@dataclass(frozen=True)
class WindowQuery:
    """Lo que no cambia entre las ventanas de una consulta: la zona (o el lote), el riego con que se evalúa, los pesos de
    quien consulta y los de AgroSense. Ni el lote ni las prioridades van al log (R9)."""

    dataset: Dataset
    municipality: Municipality
    has_lot: bool
    # El lote, para el suelo del polígono (HU-182). Nulo sin lote.
    lot: Lot | None
    zone: ZoneTemperature
    place: SignalZone
    texture: str | None
    irrigated: bool | None
    thresholds: Thresholds
    weights: dict[str, int]
    weights_basis: str
    default_weights: dict[str, int]


def window_query(
    dataset: Dataset,
    municipality: Municipality,
    lot: Lot | None,
    weights: Mapping[str, int],
    weights_basis: str,
    default_weights: Mapping[str, int],
    requested_irrigated: bool | None,
) -> WindowQuery:
    """La consulta ya leída. La temperatura es la del municipio o, con un lote dibujado, la corregida a su altitud
    (HU-191); la textura del agua, la del lote si tiene contorno, si no la del municipio; el riego, con lote, siempre el
    del lote (EP-16)."""
    return WindowQuery(
        dataset=dataset,
        municipality=municipality,
        has_lot=lot is not None,
        lot=lot,
        zone=zone_temperature(dataset, municipality, lot),
        place=signal_zone(dataset, municipality),
        texture=zone_texture(dataset, municipality, lot),
        irrigated=irrigation_used(lot is not None, lot.irrigated if lot is not None else None, requested_irrigated),
        thresholds=get_thresholds(),
        weights=dict(weights),
        weights_basis=weights_basis,
        default_weights=dict(default_weights),
    )


@dataclass(frozen=True)
class WindowDiagnosis:
    """El diagnóstico de una ventana: `core` con la forma del contrato y, para quien siga calculando (las mejores
    ventanas de `/diagnostics`, el alto riesgo de las estrategias), la ventana, las señales del motor y la de suelo.
    `window`, `signals` y `soil` son nulos con un cultivo no apto: no hay ventana que evaluar (regla 0)."""

    core: DiagnosisCore
    window: CropWindow | None
    signals: dict[str, SignalResult] | None
    soil: SignalResult | None
    diagnosis: Diagnosis


def diagnose_window(query: WindowQuery, crop_id: str, sowing_date: date) -> WindowDiagnosis:
    """El diagnóstico de `crop_id` sembrado en `sowing_date`: la aptitud (HU-191), las seis señales de la ventana si el
    cultivo es apto o no se sabe, y el semáforo dos veces (HU-074), con los pesos de quien consulta y con los de
    AgroSense. La regla 0 (cultivo no apto: `red` y `rotate`, sin ventana ni señales) la decide el motor."""
    dataset = query.dataset
    crop = dataset.crops[crop_id]
    name = crop_name(crop)
    fit = crop_suitability(crop, query.zone.tmean_annual_c)
    fit_result = suitability_result(crop, fit, query.zone, query.municipality)

    window = signals = soil = None
    if evaluates_windows(fit.level):
        window = crop_window(dataset.stages.get(crop_id, []), sowing_date)
        # El suelo no cambia con la fecha (HU-183); con un lote sigue siendo el del municipio.
        soil = soil_for(dataset, query.municipality, query.lot, crop, query.thresholds, name)
        signals = window_signals(dataset, query.place, crop_id, crop, name, window, query.thresholds, query.irrigated, query.texture, soil)

    diagnosis = diagnose(
        fit.level,
        fit_result.reasons,
        query.zone.limitation,
        query.irrigated,
        signals,
        query.weights,
        query.weights_basis,
        query.default_weights,
    )
    core = DiagnosisCore(
        suitability=fit_result,
        window=None
        if window is None
        else Window(
            sowing_start=window.sowing_date,
            harvest_estimate=window.harvest_estimate,
            harvest_basis=window.harvest_basis,
            supply_semester=None,
        ),
        signals=None if signals is None else {n: signal_result(n, result, query.weights) for n, result in signals.items()},
        overall=light_result(diagnosis.overall, query.weights_basis),
        overall_default=light_result(diagnosis.overall_default, DEFAULT),
        weights=query.weights,
        limitations=list(diagnosis.limitations),
        versions={"dataset": dataset.version, "rules": rules_version(dataset.rules_version)},
    )
    return WindowDiagnosis(core, window, signals, soil, diagnosis)
