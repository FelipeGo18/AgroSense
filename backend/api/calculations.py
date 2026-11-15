"""Endpoints de cálculo: diagnóstico, estrategias, plan de agua, «Qué cambió» y tendencias (HU-012).

Tienen su forma del contrato (`backend/api/calc_models.py`) y sus ejemplos de cada estado en el OpenAPI. Validan la
entrada como dice el contrato (422, 401 y 404). El diagnóstico (HU-076), las tendencias (HU-078, `backend/api/trends.py`)
y el plan de agua (HU-146) ya responden con el motor; los demás, mientras su motor no exista, responden `501`
`not_implemented` (decisión 15).
Cuando llegue cada HU del motor, la ruta deja de responder 501 y devuelve su modelo: la forma no cambia.

No guardan los datos de la finca ni quién consultó (R9): solo leen el dataset y, con `lot_id`, el lote.
"""

import uuid
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session as Db

from backend.accounts.farm_models import Lot
from backend.api import calc_examples as ex
from backend.api import monthly_climate
from backend.api.auth import current_session, require_accounts
from backend.api.calc_models import (
    ChangesResponse,
    CropId,
    DiagnosisRequest,
    DiagnosisRequestEcho,
    DiagnosisResponse,
    FarmWater,
    LightResult,
    MunicipalityId,
    RotationRequest,
    RotationResponse,
    Signal,
    SoilMoisture,
    SourceValue,
    SuitabilityResult,
    TrendsResponse,
    WaterPlanCropResult,
    WaterPlanRequest,
    WaterPlanResponse,
    WaterSources,
    Window,
    WindowSummary,
)
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.api.lot_terrain import ZoneTemperature, zone_temperature, zone_texture
from backend.api.lots import _own_lot
from backend.api.soil_signals import soil_for
from backend.api.trends import trends as build_trends
from backend.api.water_signals import zone_water
from backend.api.window_signals import (
    SignalResult,
    SignalZone,
    signal_sources,
    signal_zone,
    window_signals,
)
from backend.config.thresholds import Thresholds, get_thresholds
from backend.config.versions import rules_version
from backend.config.weights import get_default_weights
from backend.dataset import Dataset, Municipality
from backend.db.session import get_db
from backend.engine.changes import (
    Period,
    PeriodPair,
    compare_climate_months,
)
from backend.engine.diagnosis import diagnose, evaluates_windows, irrigation_used
from backend.engine.signal_score import counts, round_half_up, signal_scores, weight_of
from backend.engine.stages import crop_window, monthly_sowing_windows
from backend.engine.suitability import NOT_SUITABLE, Suitability, ZoneTemperatureUsed, crop_suitability, suitability_reason
from backend.engine.traffic_light import DEFAULT, FARMER, TrafficLight
from backend.engine.water_balance import root_zone
from backend.engine.water_plan import PlanCrop, water_plan
from backend.engine.window_order import WindowSignals, best_windows, order_windows
from common import signal_sources as source_config
from common.dates import add_months
from common.region import region_today
from common.signal_sources import get_signal_sources

router = APIRouter(prefix="/api/v1", tags=["cálculo"])

NOT_IMPLEMENTED = "Este cálculo todavía no está disponible."
# El dataset de ejemplo (`data/examples/`) se publica con esta versión, y la respuesta lo dice (R5).
EXAMPLE_VERSION = "ejemplo"
EXAMPLE_DATA = "Datos de ejemplo: no representan observaciones reales."
# `irrigated` nulo, en la consulta o en el lote: se evalúa como sin riego y se dice (contrato, cuerpo de `/diagnostics`).


def _examples(**values: tuple[str, Any]) -> dict[str, Any]:
    return {"application/json": {"examples": {name: {"summary": summary, "value": value} for name, (summary, value) in values.items()}}}


def _months_ahead(day: date, months: int) -> date:
    """El día 1 del mes que queda `months` meses después del de `day`."""
    return date(*add_months(day.year, day.month, months), 1)


def _check_sowing_date(sowing_date: date) -> None:
    """De este mes a doce meses: el mes en curso se acepta aunque su día 1 ya haya pasado (contrato, «Fechas»). «Hoy» es
    el día en la región, no el del servidor ni el de quien consulta (`common/region.py`)."""
    today = region_today()
    if not date(today.year, today.month, 1) <= sowing_date < _months_ahead(today, 13):
        raise ApiError(
            422,
            "invalid_input",
            "La fecha de siembra debe estar entre este mes y los próximos doce.",
            log="Cálculo rechazado: fecha de siembra fuera de los próximos doce meses",
        )


def _check_place(dataset: Dataset, municipality_id: str) -> None:
    if municipality_id not in dataset.municipalities:
        raise ApiError(
            422,
            "invalid_input",
            "Ese municipio no está entre los de la región de AgroSense.",
            log=f"Cálculo rechazado: municipio fuera del catálogo del dataset {dataset.version}",
        )


def _check_crops(dataset: Dataset, crop_ids: list[str], only_crops: bool = False) -> None:
    """Los cultivos existen en el catálogo; en el diagnóstico y en «Qué cambió», solo `kind = crop`."""
    for crop_id in crop_ids:
        crop = dataset.crops.get(crop_id)
        if crop is None or (only_crops and crop.get("kind") != "crop"):
            raise ApiError(
                422,
                "invalid_input",
                "Ese cultivo no está en el catálogo."
                if crop is None
                else "Ese cultivo no se puede diagnosticar: es un abono verde o un descanso.",
                log="Cálculo rechazado: cultivo fuera del catálogo o que no es `kind = crop`",
            )


def _check_lot(request: Request, db: Db, lot_id: uuid.UUID | None, municipality_id: str | None = None) -> Lot | None:
    """Con `lot_id` hace falta sesión (401), el lote debe ser propio (404) y, si se dice el municipio de la consulta, del
    mismo municipio (422): mezclar un municipio con el terreno de otro daría una temperatura de ningún lugar. Devuelve
    el lote. Solo se lee, no se guarda nada (R9)."""
    if lot_id is None:
        return None
    require_accounts(db)
    session = current_session(request, db)
    lot = _own_lot(db, session.user, lot_id)
    if municipality_id is not None and lot.municipality_id != municipality_id:
        raise ApiError(422, "invalid_input", "Ese lote es de otro municipio.", log="Cálculo rechazado: el lote es de otro municipio")
    return lot


def calc_dataset(request: Request) -> Dataset:
    """El dataset publicado (o 503, como `require_dataset`), y sus versiones para la línea del log de la petición: los
    endpoints de cálculo dicen con qué dataset y qué reglas respondieron (R4; contrato, «Logs de la terminal»). Solo
    las versiones: el cuerpo de la consulta nunca va al log (R9)."""
    dataset = require_dataset()
    request.state.versions = {"dataset": dataset.version, "rules": rules_version(dataset.rules_version)}
    return dataset


def _not_implemented(request: Request, what: str) -> None:
    explain(request, f"{what}: la entrada es válida, pero el motor todavía no está construido (501)")
    raise ApiError(501, "not_implemented", NOT_IMPLEMENTED)


def _get_article(crop: dict[str, Any]) -> str:
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


def _crop_name(crop: dict[str, Any]) -> str:
    """El nombre del cultivo con su artículo, como lo dicen las razones: «la papa», «el haba»."""
    return f"{_get_article(crop)} {crop.get('name_es', 'cultivo').lower()}"


def _suitability_result(crop: dict[str, Any], result: Suitability, zone: ZoneTemperature, municipality: Municipality) -> SuitabilityResult:
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
        reasons=[suitability_reason(result, crop, _crop_name(crop), used)],
    )


def _light(result: TrafficLight, weights_basis: str) -> LightResult:
    """La luz del motor con la forma del contrato. `weights_basis` lo pone la API: el motor solo lo usa en las razones."""
    return LightResult(
        light=result.light,
        action=result.action,
        high_risk=result.high_risk,
        weights_basis=weights_basis,
        limiting_signal=result.limiting_signal,
        reasons=list(result.reasons),
    )


def _signal(name: str, result: SignalResult, weights: dict[str, int]) -> Signal:
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


def _best_windows(
    dataset: Dataset,
    zone: SignalZone,
    crop_id: str,
    crop: dict[str, Any],
    crop_name: str,
    thresholds: Thresholds,
    weights: Mapping[str, int],
    irrigated: bool | None,
    texture_class: str | None,
    soil: SignalResult,
) -> list[WindowSummary]:
    """Hasta tres ventanas de los próximos doce meses, desde el mes en curso en la región, sin las de alto riesgo
    (HU-192). Cada una se califica con `window_signals`, el mismo cálculo de la ventana consultada (con el mismo riego
    y el mismo suelo: la textura del agua y la señal de suelo, que no cambia con la fecha)."""
    windows = [
        WindowSignals(
            window.sowing_date,
            window.harvest_estimate,
            signal_scores(window_signals(dataset, zone, crop_id, crop, crop_name, window, thresholds, irrigated, texture_class, soil)),
        )
        for window in monthly_sowing_windows(dataset.stages.get(crop_id, []), region_today())
    ]
    return [WindowSummary.model_validate(ranked, from_attributes=True) for ranked in best_windows(order_windows(windows, weights))]


@router.post(
    "/diagnostics",
    response_model=DiagnosisResponse,
    responses={
        200: {
            "content": _examples(
                favorable=("Luz verde con sus prioridades y amarilla con las de AgroSense; mercado sin datos", ex.DIAGNOSIS_OK),
                no_apto=("El cultivo no se da en la zona: sin ventanas", ex.DIAGNOSIS_NOT_SUITABLE),
                sin_agua=("Sin datos de lluvia: no evaluable", ex.DIAGNOSIS_NOT_EVALUABLE),
                no_aplica=("Una señal que no aplica", ex.DIAGNOSIS_NOT_APPLICABLE),
            )
        },
        **ex.responses(401, 404, 422, 500, 503),
    },
)
def diagnostics(body: DiagnosisRequest, request: Request, dataset: Dataset = Depends(calc_dataset), db: Db = Depends(get_db)) -> Any:
    """Diagnóstico de una ventana de siembra (HU-076). Es historia de la zona, no un pronóstico.

    Un solo camino para todos los casos: la aptitud (HU-191), las seis señales de la ventana si el cultivo es apto o no
    se sabe, y el semáforo dos veces (HU-074), con los pesos de quien consulta y con los de AgroSense. La regla 0 (cultivo
    no apto: `red` y `rotate`, sin ventana ni señales) la decide el motor, no esta ruta.
    """
    _check_place(dataset, body.municipality_id)
    _check_crops(dataset, [body.crop_id], only_crops=True)
    _check_sowing_date(body.sowing_date)
    lot = _check_lot(request, db, body.lot_id, body.municipality_id)

    # La temperatura es la del municipio o, con un lote dibujado, la corregida a su altitud (primer criterio de
    # HU-191). Al log solo va de dónde salió, no el lote (R9).
    crop = dataset.crops[body.crop_id]
    crop_name = _crop_name(crop)
    municipality = dataset.municipalities[body.municipality_id]
    zone = zone_temperature(dataset, municipality, lot)
    explain(request, f"Aptitud decidida con la temperatura de su {'lote' if zone.basis == 'lot' else 'municipio'}")
    fit = crop_suitability(crop, zone.tmean_annual_c)
    fit_result = _suitability_result(crop, fit, zone, municipality)

    # Sin `priorities`, los pesos de quien consulta son los de AgroSense (cacheados: `weights.yaml` no se vuelve a leer
    # en cada consulta), y las dos luces salen iguales. Las prioridades no van al log (R9).
    defaults = get_default_weights().weights
    weights, basis = (body.priorities.model_dump(), FARMER) if body.priorities is not None else (defaults, DEFAULT)
    # El eco dice el riego que se usó, que es el que la web guarda con la temporada (`diagnosis_irrigated`).
    irrigated = irrigation_used(lot is not None, lot.irrigated if lot is not None else None, body.irrigated)

    thresholds = get_thresholds()
    signal_place = signal_zone(dataset, municipality)
    # La textura del suelo para el agua: la del lote si tiene contorno, si no la del municipio. No va al log ni se guarda
    # (R9).
    texture = zone_texture(dataset, municipality, lot)
    window = signals = soil = None
    if evaluates_windows(fit.level):
        window = crop_window(dataset.stages.get(body.crop_id, []), body.sowing_date)
        # El suelo no cambia con la fecha: una sola vez por consulta (HU-183).
        soil = soil_for(dataset, municipality, lot is not None, crop, thresholds, crop_name)
        signals = window_signals(dataset, signal_place, body.crop_id, crop, crop_name, window, thresholds, irrigated, texture, soil)

    diagnosis = diagnose(fit.level, fit_result.reasons, zone.limitation, irrigated, signals, weights, basis, defaults)
    best = None
    if diagnosis.best_windows_weights is not None:
        best = _best_windows(
            dataset, signal_place, body.crop_id, crop, crop_name, thresholds, diagnosis.best_windows_weights, irrigated, texture, soil
        )

    return DiagnosisResponse(
        request=DiagnosisRequestEcho(
            municipality_id=body.municipality_id,
            crop_id=body.crop_id,
            sowing_date=body.sowing_date,
            irrigated=irrigated,
            lot_id=body.lot_id,
        ),
        suitability=fit_result,
        window=None
        if window is None
        else Window(
            sowing_start=window.sowing_date,
            harvest_estimate=window.harvest_estimate,
            harvest_basis=window.harvest_basis,
            supply_semester=None,
        ),
        signals=None if signals is None else {name: _signal(name, result, weights) for name, result in signals.items()},
        overall=_light(diagnosis.overall, basis),
        overall_default=_light(diagnosis.overall_default, DEFAULT),
        weights=weights,
        best_windows=best,
        limitations=list(diagnosis.limitations),
        versions={"dataset": dataset.version, "rules": rules_version(dataset.rules_version)},
    )


@router.post(
    "/rotations",
    response_model=RotationResponse,
    responses={
        200: {
            "content": _examples(
                estrategias=("Dos estrategias sugeridas (una con descanso), la rotación actual y dos descartadas", ex.ROTATIONS),
                sin_actual=("Sin rotación actual: no hay referencia", ex.ROTATIONS_NO_CURRENT),
                sin_opciones=("Ninguna estrategia cumple: todas descartadas", ex.ROTATIONS_EMPTY),
            )
        },
        **ex.responses(401, 404, 422, 501, 503),
    },
)
def rotations(body: RotationRequest, request: Request, dataset: Dataset = Depends(calc_dataset), db: Db = Depends(get_db)) -> Any:
    """Estrategias de rotación de hasta 3 ciclos, comparadas contra la rotación actual (HU-084, HU-223)."""
    _check_place(dataset, body.municipality_id)
    _check_crops(dataset, [*body.previous_crop_ids, *(body.current_crop_ids or [])])
    _check_sowing_date(body.sowing_date)
    _check_lot(request, db, body.lot_id, body.municipality_id)
    _not_implemented(request, "Estrategias de rotación")


@router.post(
    "/water-plans",
    response_model=WaterPlanResponse,
    responses={
        200: {"content": _examples(plan=("Un ciclo de papa, con un mes sin datos de lluvia", ex.WATER_PLAN))},
        **ex.responses(422, 500, 503),
    },
)
def water_plans(body: WaterPlanRequest, request: Request, dataset: Dataset = Depends(calc_dataset)) -> Any:
    """Plan de agua de una finca o de un ciclo de una estrategia (HU-146). Es una estimación (R10).

    Solo lee el dataset y llama al motor (`backend/engine/water_plan.py`): no recibe `lot_id`, así que el suelo es
    siempre el del municipio, también con cuenta (contrato). La fecha de siembra no se limita a los próximos doce
    meses: el tercer ciclo de una estrategia puede caer más lejos. No guarda nada ni escribe en la base de datos (R9).
    """
    _check_place(dataset, body.municipality_id)
    # Un abono verde también crece y necesita agua: el ciclo de una estrategia puede serlo (HU-215). Como en el
    # contrato, solo el diagnóstico y «Qué cambió» piden `kind = crop`. Un descanso pasa: el motor dice que no tiene agua.
    _check_crops(dataset, [crop.crop_id for crop in body.crops])

    municipality = dataset.municipalities[body.municipality_id]
    zone = zone_water(dataset, body.municipality_id)
    texture = zone_texture(dataset, municipality, None)
    crops = []
    for item in body.crops:
        crop = dataset.crops[item.crop_id]
        crops.append(
            PlanCrop(
                crop_id=item.crop_id,
                name=_crop_name(crop),
                kind=crop.get("kind"),
                area_pct=item.area_pct,
                sowing_date=item.sowing_date,
                window=crop_window(dataset.stages.get(item.crop_id, []), item.sowing_date),
                root=root_zone(crop),
            )
        )
    plan = water_plan(crops, body.total_area_ha, zone.months(), texture, zone.source, zone.wetness)

    config = monthly_climate.water_sources(dataset)
    # El suelo se cita solo si su textura entró al cálculo (el agua que guarda); si no, no se usó ninguna fuente de suelo.
    # Se lee del módulo (`source_config`), no de una función importada: las pruebas la cambian en él (`tests/conftest.py`).
    soil = source_config.get_signal_sources().for_region(dataset.region["id"])["soil"].used if plan.soil_used else None
    limitations = [EXAMPLE_DATA] if dataset.version == EXAMPLE_VERSION else []
    limitations.extend(plan.limitations)
    # Al log, solo cuántos cultivos tuvieron agua: ni el municipio, ni los cultivos, ni las fechas, ni el área (R9).
    explain(request, f"Plan de agua calculado: {sum(1 for crop in plan.crops if crop.months)} de {len(plan.crops)} cultivos con agua")
    return WaterPlanResponse(
        request=body,
        crops=[WaterPlanCropResult.model_validate(asdict(crop)) for crop in plan.crops],
        farm=FarmWater.model_validate(asdict(plan.farm)),
        soil_moisture=[SoilMoisture.model_validate(asdict(reading)) for reading in plan.soil_moisture],
        sources=WaterSources(rain=config.used, et0=config.et0, soil=soil),
        soil_basis="municipality",
        limitations=list(dict.fromkeys(limitations)),
        versions={"dataset": dataset.version, "rules": rules_version(dataset.rules_version)},
    )


def _compare_changes(
    dataset: Dataset,
    municipality_id: str,
    periods: PeriodPair,
    precip_periods: PeriodPair | None = None,
) -> dict[str, Any]:
    """Conecta los datos cargados por la API con el motor de HU-217."""
    table = dataset.climate_change_month

    # Sin tabla, pasamos una lista vacía. El motor devolverá
    # insufficient_data para los indicadores de los doce meses.
    rows = table.filter(pl.col("municipality_id") == municipality_id).to_dicts() if table is not None else []

    return compare_climate_months(
        municipality_id=municipality_id,
        rows=rows,
        periods=periods,
        precip_periods=precip_periods,
    )


def _change_period_pair(dataset: Dataset, source_id: str) -> PeriodPair:
    """Selecciona exactamente dos periodos de la fuente solicitada.

    Nunca utiliza periodos de otra fuente ni inventa años.
    """
    selected = []

    for item in dataset.periods:
        if not isinstance(item, dict):
            raise ValueError("El manifiesto contiene un periodo inválido")

        if item.get("source_id") != source_id:
            continue

        # Validar antes de construir Period: el motor compara los años
        # en __post_init__ y no debe recibir tipos inválidos del manifiesto.
        for field in ("period_id", "source_id"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{field} debe ser un texto no vacío")
        for field in ("start_year", "end_year"):
            if isinstance(item.get(field), bool) or not isinstance(item.get(field), int):
                raise ValueError("Los años de los periodos deben ser enteros")

        period = Period(**item)
        selected.append(period)

    if len(selected) != 2:
        raise ValueError(f"Se necesitan exactamente dos periodos para {source_id}")

    selected.sort(key=lambda period: period.start_year)

    if selected[0].period_id == selected[1].period_id:
        raise ValueError("Los periodos deben tener identificadores distintos")

    return PeriodPair(before=selected[0], after=selected[1])


def _change_configuration(
    dataset: Dataset,
) -> tuple[PeriodPair, PeriodPair | None, list[str]]:
    """Obtiene fuentes y periodos sin sustituir fuentes ausentes."""
    try:
        sources = get_signal_sources().for_region(dataset.region["id"])

        climate_source = sources["frost"].used
        if sources["heat"].used != climate_source:
            raise ValueError("La comparación de heladas y calor necesita los mismos periodos")

        rain_source = sources["water"].used

        periods = _change_period_pair(dataset, climate_source)
        precip_periods = _change_period_pair(dataset, rain_source) if rain_source != climate_source else None

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ApiError(
            503,
            "dataset_unavailable",
            "La comparación histórica no está disponible en este momento.",
            log=(f"Qué cambió: faltan periodos o la configuración de fuentes no es compatible: {error}"),
        ) from error

    limitations = [
        "Así fue en la historia de su zona. No es un pronóstico.",
        "La oferta, el mercado y el suelo son los mismos en los dos periodos.",
    ]

    if "nasa_power" in {climate_source, rain_source}:
        limitations.append("NASA POWER es un reanálisis, no una observación directa.")
        # HU-216, comprobación del PR #79: hasta +7,3 °C en tierra caliente.
        limitations.append(
            "En tierra caliente, NASA POWER muestra aumentos de temperatura de hasta 7,3 °C "
            "que pueden ser un artefacto del reanálisis. No deben interpretarse como un calentamiento local confirmado."
        )

    if rain_source in {"nasa_power", "imerg"}:
        # HU-216, PR #79: la revisión inicial midió 68 %; la repetición con
        # los mismos años y sin el 2021 defectuoso midió 69 %. No es una
        # incertidumbre por municipio: es el resultado regional de esa comparación.
        limitations.append(
            "Al comparar los registros de la región, NASA POWER y GPM IMERG indicaron cambios de lluvia opuestos "
            "en cerca de 7 de cada 10 comparaciones. El cambio mensual de lluvia depende de la fuente "
            "y no confirma por sí solo que su municipio se haya vuelto más seco o más lluvioso."
        )

    if "imerg" in {climate_source, rain_source}:
        limitations.append("GPM IMERG tiene datos desde 2000; sus periodos de comparación son más cortos.")

    rain_caveat = sources["water"].caveat
    if rain_caveat:
        limitations.append(rain_caveat)

    return periods, precip_periods, limitations


@router.get(
    "/changes",
    response_model=ChangesResponse,
    responses={
        200: {"content": _examples(cambios=("Dos periodos de NASA POWER; un mes sin datos de calor en el primero", ex.CHANGES))},
        **ex.responses(422, 501, 503),
    },
)
def changes(
    request: Request,
    municipality_id: MunicipalityId = Query(),
    crop_id: CropId = Query(),
    irrigated: bool | None = Query(None),
    dataset: Dataset = Depends(calc_dataset),
) -> Any:
    """«Qué cambió en su zona» (HU-218): historia comparada, nunca pronóstico."""
    _check_place(dataset, municipality_id)
    _check_crops(dataset, [crop_id], only_crops=True)

    crop = dataset.crops[crop_id]
    municipality = dataset.municipalities[municipality_id]
    # /changes no recibe lot_id: la aptitud usa siempre el municipio.
    zone = zone_temperature(dataset, municipality, None)

    aptitude = crop_suitability(crop, zone.tmean_annual_c)

    # Todavía no tenemos la evaluación completa de ventanas.
    # No representamos esa implementación pendiente como una lista vacía.
    if aptitude.level != NOT_SUITABLE:
        _not_implemented(request, "Qué cambió")

    periods, precip_periods, limitations = _change_configuration(dataset)

    comparison = _compare_changes(
        dataset=dataset,
        municipality_id=municipality_id,
        periods=periods,
        precip_periods=precip_periods,
    )

    aptitude_reason = _suitability_result(crop, aptitude, zone, municipality).reasons[0]

    if irrigated is None:
        limitations.append("No se indicó si hay riego; se asume sin riego.")

    if dataset.version == EXAMPLE_VERSION:
        limitations.append(EXAMPLE_DATA)

    if dataset.climate_change_month is None:
        limitations.append("La tabla de comparación histórica no está publicada; los indicadores se muestran sin datos suficientes.")

    explain(request, "Qué cambió: el cultivo no es apto en su municipio; clima de dos periodos comparado")
    return ChangesResponse(
        request={
            "municipality_id": municipality_id,
            "crop_id": crop_id,
            "irrigated": irrigated,
        },
        periods={
            "before": asdict(periods.before),
            "after": asdict(periods.after),
        },
        precip_periods=(
            {
                "before": asdict(precip_periods.before),
                "after": asdict(precip_periods.after),
            }
            if precip_periods is not None
            else None
        ),
        suitability=SuitabilityResult(
            level="not_suitable",
            score=int(round(aptitude.score)),
            basis=zone.basis,
            tmean_annual_c=zone.tmean_annual_c,
            altitude_m=zone.altitude_m,
            reasons=[aptitude_reason],
        ),
        months=comparison["months"],
        best_windows={"before": [], "after": []},
        weights_basis="default",
        reasons=[
            "No se calculan ventanas porque el cultivo no es apto para la zona.",
            aptitude_reason,
            *comparison["reasons"],
        ],
        limitations=limitations,
        versions={
            "dataset": dataset.version,
            "rules": rules_version(dataset.rules_version),
        },
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    responses={
        200: {"content": _examples(series=("Agua y verdor con datos; la oferta sin datos", ex.TRENDS))},
        **ex.responses(422, 500, 503),
    },
)
def trends(
    request: Request,
    municipality_id: MunicipalityId = Query(),
    crop_id: CropId = Query(),
    sowing_date: date = Query(),
    dataset: Dataset = Depends(calc_dataset),
) -> Any:
    """Series para las gráficas: agua, área sembrada y verdor (HU-078). Cada una en su unidad. Es historia de la zona,
    no un pronóstico; solo lee el dataset publicado y no guarda nada (R9)."""
    _check_place(dataset, municipality_id)
    _check_crops(dataset, [crop_id], only_crops=True)
    result = build_trends(dataset, municipality_id, crop_id, sowing_date)
    # Al log, solo qué series tuvieron datos: ni el municipio, ni el cultivo, ni la fecha (R9).
    explain(
        request,
        f"Tendencias calculadas: agua {result.water.status} ({len(result.water.points)} años), "
        f"oferta {result.supply.status}, verdor {result.ndvi.status}",
    )
    return result
