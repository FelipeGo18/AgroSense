"""Escribirle al responsable de los datos: reportar un problema o pedir algo sobre sus datos (HU-163, HU-170).

`POST /api/v1/me/tickets` y `GET /api/v1/me/tickets` (specs/02-contratos.md, «Endpoints de cuenta»). Es el canal de
contacto que nombra la política de tratamiento de datos (Ley 1581 de 2012): con cuenta, porque sin cuenta AgroSense no
guarda nada de la persona (R9). Un mensaje puede ir sobre uno de sus lotes.

Se guarda solo lo que se escribe y el lote, con su fecha. El mensaje nunca va a los logs de la terminal ni a
`activity_log`, que dice solo `ticket.opened` y el id (R9).

El responsable los lee y los contesta por consola (`python -m backend.accounts.tickets`, `backend/README.md`); la
respuesta (`reply`, `replied_at`) se ve en «Mis mensajes». Hasta 5 mensajes por día por persona: el sexto responde 429.
"""

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.farm_models import Lot
from backend.accounts.models import User
from backend.accounts.trace_models import SupportTicket
from backend.api import calc_examples
from backend.api.auth import current_user, require_accounts
from backend.api.errors import ApiError, explain, request_id_of
from backend.db.session import get_db
from common.region import region_timezone, region_today

router = APIRouter(
    prefix="/api/v1/me", tags=["cuenta"], dependencies=[Depends(require_accounts)], responses=calc_examples.responses(401, 422)
)

MAX_MESSAGE = 2000
# Hasta 5 mensajes por día por persona: alcanza para escribir lo que necesite sin llenar la tabla.
DAILY_LIMIT = 5
# La lista se corta en los 50 más recientes, como «Mi actividad».
LIST_LIMIT = 50
Message = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE)]


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message
    lot_id: uuid.UUID | None = None


class TicketOut(BaseModel):
    ticket_id: uuid.UUID
    lot_id: uuid.UUID | None
    message: str
    status: str
    created_at: datetime
    closed_at: datetime | None
    # La respuesta del responsable; nula mientras no conteste.
    reply: str | None
    replied_at: datetime | None


def _out(ticket: SupportTicket) -> TicketOut:
    return TicketOut(**{field: getattr(ticket, field) for field in TicketOut.model_fields})


@router.post("/tickets", status_code=201, responses=calc_examples.responses(404, 429))
def open_ticket(body: TicketCreate, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> TicketOut:
    """Abre un mensaje al responsable. Si nombra un lote, tiene que ser uno suyo y sin borrar (404 si no). Hasta
    `DAILY_LIMIT` por día (429 después)."""
    # «Hoy» es el día en la hora de la región, desde la medianoche, como el resto de la API.
    midnight = datetime.combine(region_today(), time(0), tzinfo=region_timezone())
    today = db.scalar(
        select(func.count()).select_from(SupportTicket).where(SupportTicket.user_id == user.user_id, SupportTicket.created_at >= midnight)
    )
    if today >= DAILY_LIMIT:
        raise ApiError(
            429,
            "too_many_requests",
            f"Ya nos escribió {DAILY_LIMIT} mensajes hoy. Espere nuestra respuesta o vuelva a escribir mañana.",
            log="Mensaje rechazado: llegó al límite de mensajes del día",
            # Lo que falta para la medianoche de la región, cuando se puede volver a escribir (contrato: todo 429 lo dice).
            headers={"Retry-After": str(max(1, int((midnight + timedelta(days=1) - datetime.now(UTC)).total_seconds())))},
        )
    if body.lot_id is not None:
        lot = db.scalar(select(Lot).where(Lot.lot_id == body.lot_id, Lot.user_id == user.user_id, Lot.deleted_at.is_(None)))
        if lot is None:
            raise ApiError(404, "not_found", "No encontramos ese lote.", log="Mensaje rechazado: el lote no existe o es de otro usuario")
    ticket = SupportTicket(user_id=user.user_id, lot_id=body.lot_id, message=body.message)
    db.add(ticket)
    db.flush()
    activity.record(db, "ticket.opened", request_id=request_id_of(request), actor=user, object_type="ticket", object_id=ticket.ticket_id)
    db.commit()
    db.refresh(ticket)
    explain(request, "Mensaje al responsable abierto" + (" sobre un lote" if body.lot_id else ""))
    return _out(ticket)


@router.get("/tickets")
def list_tickets(request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> list[TicketOut]:
    """Los mensajes del usuario, del más reciente al más antiguo, hasta los 50 últimos. Nunca los de otro usuario."""
    tickets = db.scalars(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.user_id)
        .order_by(SupportTicket.created_at.desc(), SupportTicket.ticket_id)
        .limit(LIST_LIMIT)
    ).all()
    explain(request, f"Mensajes consultados: {len(tickets)}")
    return [_out(ticket) for ticket in tickets]
