"""Endpoints de cálculo: diagnóstico, estrategias, plan de agua, «Qué cambió» y tendencias (HU-012).

Ya tienen su forma del contrato (`backend/api/calc_models.py`) y sus ejemplos de cada estado en el OpenAPI, para que la
web avance sin esperar al motor. Validan la entrada como dice el contrato (422, 401 y 404) y, mientras el motor no
exista, responden `501` `not_implemented` (decisión 15). Cuando llegue cada HU del motor, la ruta deja de responder 501
y devuelve su modelo: la forma no cambia.

No guardan los datos de la finca ni quién consultó (R9): solo leen el dataset y, con `lot_id`, el lote.
"""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session as Db

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
    SuitabilityResult,
    TrendsResponse,
    WaterPlanRequest,
    WaterPlanResponse,
)
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.api.lots import _own_lot
from backend.config.weights import get_default_weights
from backend.dataset import Dataset
from backend.db.session import get_db
from backend.engine.suitability import ABOVE_MAX, NOT_SUITABLE, Suitability, suitability
from common.region import region_today

router = APIRouter(prefix="/api/v1", tags=["cálculo"])

NOT_IMPLEMENTED = "Este cálculo todavía no está disponible."


def _examples(**values: tuple[str, Any]) -> dict[str, Any]:
    return {"application/json": {"examples": {name: {"summary": summary, "value": value} for name, (summary, value) in values.items()}}}


def _months_ahead(day: date, months: int) -> date:
    year, month = divmod(day.month - 1 + months, 12)
    return date(day.year + year, month + 1, 1)


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


def _check_lot(request: Request, db: Db, lot_id: uuid.UUID | None) -> None:
    """Con `lot_id` hace falta sesión (401) y el lote debe ser propio (404). Solo se lee el lote, no se guarda nada (R9)."""
    if lot_id is None:
        return
    require_accounts(db)
    session = current_session(request, db)
    _own_lot(db, session.user, lot_id)


def _not_implemented(request: Request, what: str) -> None:
    explain(request, f"{what}: la entrada es válida, pero el motor todavía no está construido (501)")
    raise ApiError(501, "not_implemented", NOT_IMPLEMENTED)


def _format_temperature(value: float) -> str:
    """Formatea temperatura con exactamente 1 decimal y coma separadora."""
    return f"{value:.1f}".replace(".", ",")


def _format_limit(value: float) -> str:
    """Formatea límite: sin decimales si es entero, con coma si tiene decimales."""
    if value == int(value):
        return str(int(value))
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


def _suitability_reason(crop: dict[str, Any], result: Suitability, tmean_annual_c: float, tmean_min_c: float, tmean_max_c: float) -> str:
    """Arma la frase que explica por qué el cultivo no es apto. Solo da formato: qué límite se cruzó ya lo decidió
    el motor (`result.exceeded`), no se repite la comparación aquí (R6: la API es una capa delgada)."""
    article = _get_article(crop)
    name_lower = crop.get("name_es", "cultivo").lower()
    temperature = _format_temperature(tmean_annual_c)

    if result.exceeded == ABOVE_MAX:
        return (
            f"La temperatura media anual del municipio ({temperature} °C) "
            f"pasa de la que aguanta {article} {name_lower} (hasta {_format_limit(tmean_max_c)} °C)"
        )
    return (
        f"La temperatura media anual del municipio ({temperature} °C) "
        f"no alcanza la que necesita {article} {name_lower} (desde {_format_limit(tmean_min_c)} °C)"
    )


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
        **ex.responses(401, 404, 422, 501, 503),
    },
)
def diagnostics(body: DiagnosisRequest, request: Request, dataset: Dataset = Depends(require_dataset), db: Db = Depends(get_db)) -> Any:
    """Diagnóstico de una ventana de siembra (HU-076). Es historia de la zona, no un pronóstico."""
    _check_place(dataset, body.municipality_id)
    _check_crops(dataset, [body.crop_id], only_crops=True)
    _check_sowing_date(body.sowing_date)
    _check_lot(request, db, body.lot_id)

    # Regla 0 de la agregación del semáforo (specs/01-reglas.md, «Agregación del semáforo»): si el cultivo no es
    # apto para la zona, la luz es roja y no se evalúa nada más. `basis="municipality"` es fijo hasta HU-206, que
    # corrija la temperatura media a la altitud del lote.
    crop = dataset.crops[body.crop_id]
    municipality = dataset.municipalities[body.municipality_id]

    result = suitability(
        crop.get("tmean_min_c"),
        crop.get("tmean_opt_min_c"),
        crop.get("tmean_opt_max_c"),
        crop.get("tmean_max_c"),
        municipality.tmean_annual_c,
    )

    if result.level == NOT_SUITABLE:
        # Cultivo no es apto para la zona: devolver 200 con la forma completa
        reason = _suitability_reason(crop, result, municipality.tmean_annual_c, crop["tmean_min_c"], crop["tmean_max_c"])

        # Regla 0 ignora los pesos (la luz es roja de todas formas), pero `weights` y `weights_basis` siguen
        # diciendo cuáles se habrían usado (specs/epicas/EP-07-diagnostico.md, HU-074): los del agricultor si
        # mandó `priorities`, si no los de AgroSense (cacheados: `weights.yaml` no se vuelve a leer en cada consulta).
        weights_used = body.priorities if body.priorities is not None else get_default_weights().weights
        basis_used = "farmer" if body.priorities is not None else "default"

        reasons = ["Este cultivo no se da en su zona: elija otro"]
        limitations = []
        if body.lot_id is not None:
            # La aptitud usa la temperatura del municipio también con lote: la corrección a su altitud espera
            # HU-206, que calcula la mediana de `grid_cells` en el polígono del lote (R1).
            limitations.append("Temperatura media anual del municipio, no corregida a la altitud del lote.")

        return DiagnosisResponse(
            request=DiagnosisRequestEcho(
                municipality_id=body.municipality_id,
                crop_id=body.crop_id,
                sowing_date=body.sowing_date,
                irrigated=body.irrigated,
                lot_id=body.lot_id,
            ),
            suitability=SuitabilityResult(
                level="not_suitable",
                score=int(round(result.score)),
                basis="municipality",
                tmean_annual_c=municipality.tmean_annual_c,
                altitude_m=municipality.altitude_m,
                reasons=[reason],
            ),
            window=None,
            signals=None,
            overall=LightResult(
                light="red", action="rotate", high_risk=False, weights_basis=basis_used, limiting_signal=None, reasons=reasons
            ),
            overall_default=LightResult(
                light="red", action="rotate", high_risk=False, weights_basis="default", limiting_signal=None, reasons=reasons
            ),
            weights=weights_used,
            limitations=limitations,
            versions={"dataset": dataset.version, "rules": dataset.rules_version},
        )

    # Si es suitable o insufficient_data, sigue como antes: no se puede diagnosticar sin las señales
    _not_implemented(request, "Diagnóstico")


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
def rotations(body: RotationRequest, request: Request, dataset: Dataset = Depends(require_dataset), db: Db = Depends(get_db)) -> Any:
    """Estrategias de rotación de hasta 3 ciclos, comparadas contra la rotación actual (HU-084, HU-223)."""
    _check_place(dataset, body.municipality_id)
    _check_crops(dataset, [*body.previous_crop_ids, *(body.current_crop_ids or [])])
    _check_sowing_date(body.sowing_date)
    _check_lot(request, db, body.lot_id)
    _not_implemented(request, "Estrategias de rotación")


@router.post(
    "/water-plans",
    response_model=WaterPlanResponse,
    responses={
        200: {"content": _examples(plan=("Un ciclo de papa, con un mes sin datos de lluvia", ex.WATER_PLAN))},
        **ex.responses(422, 501, 503),
    },
)
def water_plans(body: WaterPlanRequest, request: Request, dataset: Dataset = Depends(require_dataset)) -> Any:
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
    dataset: Dataset = Depends(require_dataset),
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
    dataset: Dataset = Depends(require_dataset),
) -> Any:
    """Series para las gráficas: agua, área sembrada y verdor (HU-078). Cada una en su unidad."""
    _check_place(dataset, municipality_id)
    _check_crops(dataset, [crop_id], only_crops=True)
    _not_implemented(request, "Tendencias")
