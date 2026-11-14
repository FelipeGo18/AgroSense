"""Endpoints de cálculo: diagnóstico, estrategias, plan de agua, «Qué cambió» y tendencias (HU-012).

Tienen su forma del contrato (`backend/api/calc_models.py`) y sus ejemplos de cada estado en el OpenAPI. Validan la
entrada como dice el contrato (422, 401 y 404). El diagnóstico (HU-076) ya responde con el motor; los demás, mientras su
motor no exista, responden `501` `not_implemented` (decisión 15). Cuando llegue cada HU del motor, la ruta deja de
responder 501 y devuelve su modelo: la forma no cambia.

No guardan los datos de la finca ni quién consultó (R9): solo leen el dataset y, con `lot_id`, el lote.
"""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session as Db

from backend.accounts.farm_models import Lot
from backend.api import calc_examples as ex
from backend.api.auth import current_session, require_accounts
from backend.api.calc_models import (
    ChangesResponse,
    CropId,
    DiagnosisRequest,
    DiagnosisRequestEcho,
    DiagnosisResponse,
    LightResult,
    MunicipalityId,
    RotationRequest,
    RotationResponse,
    Signal,
    SuitabilityResult,
    TrendsResponse,
    WaterPlanRequest,
    WaterPlanResponse,
    Window,
    WindowSummary,
)
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.api.lot_terrain import ZoneTemperature, zone_temperature
from backend.api.lots import _own_lot
from backend.api.window_signals import SignalResult, SignalZone, signal_scores, signal_zone, window_signals
from backend.config.thresholds import Thresholds, get_thresholds
from backend.config.weights import get_default_weights
from backend.dataset import Dataset, Municipality
from backend.db.session import get_db
from backend.engine.signal_score import counts, round_half_up, weight_of
from backend.engine.stages import crop_window, monthly_sowing_windows
from backend.engine.suitability import ABOVE_MAX, INSUFFICIENT_DATA, NOT_SUITABLE, SUITABLE, Suitability, suitability
from backend.engine.traffic_light import DEFAULT, FARMER, OTHER_WINDOW, TrafficLight, missing_data_limitations, traffic_light
from backend.engine.window_order import WindowSignals, best_windows, order_windows
from common.dates import add_months
from common.region import region_today
from common.text import format_number

router = APIRouter(prefix="/api/v1", tags=["cálculo"])

NOT_IMPLEMENTED = "Este cálculo todavía no está disponible."


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
    request.state.versions = {"dataset": dataset.version, "rules": dataset.rules_version}
    return dataset


def _not_implemented(request: Request, what: str) -> None:
    explain(request, f"{what}: la entrada es válida, pero el motor todavía no está construido (501)")
    raise ApiError(501, "not_implemented", NOT_IMPLEMENTED)


def _format_temperature(value: float) -> str:
    """Formatea temperatura con exactamente 1 decimal y coma separadora."""
    return f"{value:.1f}".replace(".", ",")


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


def _temperature_phrase(zone: ZoneTemperature, municipality: Municipality) -> str:
    """Dice qué temperatura se usó, con su altitud: la del municipio o la estimada para el lote, y de dónde se corrigió."""
    municipal = f"{_format_temperature(municipality.tmean_annual_c)} °C"
    has_altitude = municipality.altitude_m is not None
    if zone.basis == "municipality":
        municipal_at = f"{municipal}, a {municipality.altitude_m:.0f} m" if has_altitude else municipal
        return f"La temperatura media anual del municipio ({municipal_at})"
    municipal_at = f"{municipal} a {municipality.altitude_m:.0f} m" if has_altitude else municipal
    # Es un reanálisis corregido por altitud, no una medición del lote: por eso «estimada» (R10).
    origin = ", la altitud de la celda de 250 m que contiene su centro" if zone.by_center else ""
    return (
        f"La temperatura media anual estimada para su lote ({_format_temperature(zone.tmean_annual_c)} °C, "
        f"a {zone.altitude_m:.0f} m{origin}; corregida desde la del municipio, {municipal_at})"
    )


def _suitability_reason(
    crop: dict[str, Any], result: Suitability, zone: ZoneTemperature, municipality: Municipality, tmean_min_c: float, tmean_max_c: float
) -> str:
    """Arma la frase de un cultivo `suitable` o `not_suitable`: la temperatura de la zona y el rango del cultivo. Solo da
    formato: si es apto y qué límite se cruzó ya lo decidió el motor (`result.level`, `result.exceeded`), no se repite
    la comparación aquí (R6: la API es una capa delgada)."""
    name = _crop_name(crop)
    temperature = _temperature_phrase(zone, municipality)

    if result.level == SUITABLE:
        return f"{temperature} está dentro del rango de {name} ({format_number(tmean_min_c)} a {format_number(tmean_max_c)} °C)"
    if result.exceeded == ABOVE_MAX:
        return f"{temperature} pasa de la que aguanta {name} (hasta {format_number(tmean_max_c)} °C)"
    return f"{temperature} no alcanza la que necesita {name} (desde {format_number(tmean_min_c)} °C)"


# Lo que la ficha del cultivo debe traer con fuente para decidir la aptitud (`suitability` del motor).
SUITABILITY_LIMITS = ("tmean_min_c", "tmean_opt_min_c", "tmean_opt_max_c", "tmean_max_c")


def _missing_suitability_reason(crop: dict[str, Any], zone: ZoneTemperature) -> str:
    """Por qué la aptitud es `insufficient_data`: le falta el rango a la ficha, o la temperatura a la zona (R1, R8). Si es
    la del lote, `zone.limitation` dice además por qué no se pudo estimar."""
    name = _crop_name(crop)
    if any(crop.get(field) is None for field in SUITABILITY_LIMITS):
        return f"La ficha de {name} no tiene con fuente su rango de temperatura media anual: no se sabe si se da en su zona"
    place = "de su lote" if zone.basis == "lot" else "del municipio"
    return f"Sin la temperatura media anual {place}: no se sabe si {name} se da en su zona"


def _suitability_result(crop: dict[str, Any], result: Suitability, zone: ZoneTemperature, municipality: Municipality) -> SuitabilityResult:
    if result.level == INSUFFICIENT_DATA:
        reason = _missing_suitability_reason(crop, zone)
    else:
        reason = _suitability_reason(crop, result, zone, municipality, crop["tmean_min_c"], crop["tmean_max_c"])
    return SuitabilityResult(
        level=result.level,
        score=None if result.score is None else round_half_up(result.score),
        basis=zone.basis,
        tmean_annual_c=zone.tmean_annual_c,
        altitude_m=zone.altitude_m,
        reasons=[reason],
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
    «Respuesta de diagnóstico»), con la misma definición que el semáforo y el orden (`counts` del motor)."""
    return Signal(
        status=result.status,
        level=result.level,
        critical=result.critical,
        score=result.score,
        counts=counts(name, weight_of(weights, name), result.critical),
        indicators=list(result.indicators),
        reasons=list(result.reasons),
    )


def _best_windows(
    dataset: Dataset, zone: SignalZone, crop_id: str, crop: dict[str, Any], crop_name: str, thresholds: Thresholds, weights: dict[str, int]
) -> list[WindowSummary]:
    """Hasta tres ventanas de los próximos doce meses, desde el mes en curso en la región, sin las de alto riesgo
    (HU-192). Cada una se califica con `window_signals`, el mismo cálculo de la ventana consultada."""
    windows = [
        WindowSignals(
            window.sowing_date,
            window.harvest_estimate,
            signal_scores(window_signals(dataset, zone, crop_id, crop, crop_name, window, thresholds)),
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
    fit = suitability(*(crop.get(field) for field in SUITABILITY_LIMITS), zone.tmean_annual_c)
    fit_result = _suitability_result(crop, fit, zone, municipality)

    # Sin `priorities`, los pesos de quien consulta son los de AgroSense (cacheados: `weights.yaml` no se vuelve a leer
    # en cada consulta), y las dos luces salen iguales. Las prioridades no van al log (R9).
    defaults = get_default_weights().weights
    weights, basis = (body.priorities.model_dump(), FARMER) if body.priorities is not None else (defaults, DEFAULT)
    # Con `lot_id`, el riego es el del lote, también cuando el lote no lo dice (nulo: se evalúa como sin riego; contrato y
    # EP-16). El eco dice el que se usó, que es el que la web guarda con la temporada (`diagnosis_irrigated`). Hoy ninguna
    # señal lo usa: el agua, y su limitación de «riego sin dato», son de HU-071.
    irrigated = lot.irrigated if lot is not None else body.irrigated

    limitations = [zone.limitation] if zone.limitation else []
    if fit.level == INSUFFICIENT_DATA:
        limitations.extend(fit_result.reasons)
    thresholds = get_thresholds()
    signal_place = signal_zone(dataset, municipality)
    window = signals = None
    scores = {}
    if fit.level != NOT_SUITABLE:
        window = crop_window(dataset.stages.get(body.crop_id, []), body.sowing_date)
        signals = window_signals(dataset, signal_place, body.crop_id, crop, crop_name, window, thresholds)
        scores = signal_scores(signals)
        limitations.extend(text for signal in signals.values() for text in signal.limitations)
        limitations.extend(missing_data_limitations(scores))

    overall = traffic_light(fit.level, scores, weights, basis)
    overall_default = traffic_light(fit.level, scores, defaults, DEFAULT)
    best = None
    # Con `other_window` en las dos luces, las ventanas se ordenan con los pesos de quien consulta: es la luz principal
    # (docs/registro-de-decisiones.md, 14 de noviembre de 2026). La regla 0 nunca da `other_window`.
    if OTHER_WINDOW in (overall.action, overall_default.action):
        best = _best_windows(
            dataset, signal_place, body.crop_id, crop, crop_name, thresholds, weights if overall.action == OTHER_WINDOW else defaults
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
        overall=_light(overall, basis),
        overall_default=_light(overall_default, DEFAULT),
        weights=weights,
        best_windows=best,
        # Sin repetir y en un orden fijo (R4): la zona, la aptitud, lo que dice cada señal y las señales sin datos.
        limitations=list(dict.fromkeys(limitations)),
        versions={"dataset": dataset.version, "rules": dataset.rules_version},
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
        **ex.responses(422, 501, 503),
    },
)
def water_plans(body: WaterPlanRequest, request: Request, dataset: Dataset = Depends(calc_dataset)) -> Any:
    """Plan de agua de una finca o de un ciclo de una estrategia (HU-146). Es una estimación (R10)."""
    _check_place(dataset, body.municipality_id)
    # Un abono verde también crece y necesita agua: el ciclo de una estrategia puede serlo (HU-215). Como en el
    # contrato, solo el diagnóstico y «Qué cambió» piden `kind = crop`.
    _check_crops(dataset, [crop.crop_id for crop in body.crops])
    _not_implemented(request, "Plan de agua")


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
    _not_implemented(request, "Qué cambió")


@router.get(
    "/trends",
    response_model=TrendsResponse,
    responses={
        200: {"content": _examples(series=("Agua y verdor con datos; la oferta sin datos", ex.TRENDS))},
        **ex.responses(422, 501, 503),
    },
)
def trends(
    request: Request,
    municipality_id: MunicipalityId = Query(),
    crop_id: CropId = Query(),
    sowing_date: date = Query(),
    dataset: Dataset = Depends(calc_dataset),
) -> Any:
    """Series para las gráficas: agua, área sembrada y verdor (HU-078). Cada una en su unidad."""
    _check_place(dataset, municipality_id)
    _check_crops(dataset, [crop_id], only_crops=True)
    _not_implemented(request, "Tendencias")
