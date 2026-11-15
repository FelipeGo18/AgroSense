"""Leer y contestar los mensajes de «Escribir al responsable» por consola (HU-163).

Mientras no exista la bandeja de soporte en la web (HU-170, P1), el responsable revisa los mensajes abiertos una vez
al día y los contesta desde aquí. La respuesta le llega a la persona en «Mis mensajes». Ver `backend/README.md`.

    python -m backend.accounts.tickets abiertos
    python -m backend.accounts.tickets responder <ticket_id> "La respuesta"

Responder cierra el mensaje y queda en `activity_log` como `admin.ticket_updated`, sin el texto (R9).
"""

import argparse
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as Db

from backend.accounts.trace_models import ActivityEvent, SupportTicket
from backend.config.settings import get_settings


def open_tickets(db: Db) -> list[SupportTicket]:
    """Los mensajes sin cerrar, del más antiguo al más reciente: primero el que lleva más tiempo esperando."""
    return list(db.scalars(select(SupportTicket).where(SupportTicket.status != "closed").order_by(SupportTicket.created_at)))


def answer(db: Db, ticket_id: uuid.UUID, reply: str, *, correct: bool = False) -> SupportTicket:
    """Guarda la respuesta, cierra el mensaje y deja la traza. Quien llama confirma la transacción.

    Un mensaje que ya tiene respuesta no se vuelve a contestar: la persona pudo haberla leído. Solo con `correct`
    (`--corregir` en la consola) se cambia, y la traza lo dice."""
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise LookupError(f"No hay un mensaje con el id {ticket_id}.")
    if not reply.strip():
        raise ValueError("La respuesta no puede ir vacía.")
    if ticket.reply is not None and not correct:
        raise ValueError("Ese mensaje ya tiene respuesta; use --corregir para cambiarla.")
    now = datetime.now(UTC)
    ticket.reply, ticket.replied_at, ticket.status, ticket.closed_at = reply.strip(), now, "closed", now
    db.add(
        ActivityEvent(
            actor_role="admin",
            subject_user_id=ticket.user_id,
            action="admin.ticket_updated",
            object_type="ticket",
            object_id=ticket.ticket_id,
            ticket_id=ticket.ticket_id,
            reason="Respuesta corregida por consola" if correct else "Respuesta por consola",
        )
    )
    return ticket


def main() -> None:
    parser = argparse.ArgumentParser(description="Mensajes de «Escribir al responsable»")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("abiertos", help="Lista los mensajes sin contestar")
    reply = sub.add_parser("responder", help="Contesta un mensaje y lo cierra")
    reply.add_argument("ticket_id", type=uuid.UUID)
    reply.add_argument("texto")
    reply.add_argument("--corregir", action="store_true", help="Cambia la respuesta de un mensaje que ya la tiene")
    args = parser.parse_args()
    engine = create_engine(get_settings().database_url, hide_parameters=True, connect_args={"connect_timeout": 3})
    with Db(engine) as db:
        if args.command == "abiertos":
            tickets = open_tickets(db)
            for t in tickets:
                waiting = (datetime.now(UTC) - t.created_at).days
                lot = f" · lote {t.lot_id}" if t.lot_id else ""
                print(f"{t.ticket_id} · hace {waiting} días{lot}\n  {t.message}\n")
            print(f"{len(tickets)} mensajes sin contestar.")
        else:
            answer(db, args.ticket_id, args.texto, correct=args.corregir)
            db.commit()
            print("Respuesta guardada; el mensaje quedó cerrado.")
    engine.dispose()


if __name__ == "__main__":
    main()
