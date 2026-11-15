"""Escribirle al responsable de los datos: reportar un problema o pedir algo sobre sus datos (HU-163, HU-170).

`POST /api/v1/me/tickets` y `GET /api/v1/me/tickets` (specs/02-contratos.md, «Endpoints de cuenta»). Es el canal de
contacto que nombra la política de tratamiento de datos (Ley 1581 de 2012): con cuenta, porque sin cuenta AgroSense no
guarda nada de la persona (R9). Un mensaje puede ir sobre uno de sus lotes.

Se guarda solo lo que se escribe y el lote, con su fecha. El mensaje nunca va a los logs de la terminal ni a
`activity_log`, que dice solo `ticket.opened` y el id (R9).
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.farm_models import Lot
from backend.accounts.models import User
from backend.accounts.trace_models import SupportTicket
from backend.api import calc_examples
from backend.api.auth import current_user, require_accounts
from backend.api.errors import ApiError, explain, request_id_of
from backend.db.session import get_db

router = APIRouter(
    prefix="/api/v1/me", tags=["cuenta"], dependencies=[Depends(require_accounts)], responses=calc_examples.responses(401, 422)
)

MAX_MESSAGE = 2000
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


def _out(ticket: SupportTicket) -> TicketOut:
    return TicketOut(**{field: getattr(ticket, field) for field in TicketOut.model_fields})


@router.post("/tickets", status_code=201, responses=calc_examples.responses(404))
def open_ticket(body: TicketCreate, request: Request, user: User = Depends(current_user), db: Db = Depends(get_db)) -> TicketOut:
    """Abre un mensaje al responsable. Si nombra un lote, tiene que ser uno suyo y sin borrar (404 si no)."""
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
    """Los mensajes del usuario, del más reciente al más antiguo. Nunca los de otro usuario."""
    tickets = db.scalars(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.user_id)
        .order_by(SupportTicket.created_at.desc(), SupportTicket.ticket_id)
    ).all()
    explain(request, f"Mensajes consultados: {len(tickets)}")
    return [_out(ticket) for ticket in tickets]
