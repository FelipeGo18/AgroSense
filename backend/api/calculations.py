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
    DiagnosisResponse,
    MunicipalityId,
    RotationRequest,
    RotationResponse,
    TrendsResponse,
    WaterPlanRequest,
    WaterPlanResponse,
)
from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.api.lots import _own_lot
from backend.dataset import Dataset
from backend.db.session import get_db
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
        **ex.responses(401, 404, 422, 500, 501, 503),
    },
)
def diagnostics(body: DiagnosisRequest, request: Request, dataset: Dataset = Depends(require_dataset), db: Db = Depends(get_db)) -> Any:
    """Diagnóstico de una ventana de siembra (HU-076). Es historia de la zona, no un pronóstico."""
    _check_place(dataset, body.municipality_id)
    _check_crops(dataset, [body.crop_id], only_crops=True)
    _check_sowing_date(body.sowing_date)
    _check_lot(request, db, body.lot_id)
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
