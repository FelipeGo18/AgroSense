"""Escribirle al responsable de los datos: `POST` y `GET /api/v1/me/tickets` (HU-163, HU-170; R9)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from structlog.testing import capture_logs

from backend.accounts import tickets
from backend.accounts.trace_models import ActivityEvent, SupportTicket
from common.region import region_timezone, region_today

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
LUIS = {**ROSA, "username": "luis.tunja", "display_name": "Luis"}
EL_ALTO = {"name": "El Alto", "municipality_id": "15646", "area_ha": 2.5, "irrigated": False}
MESSAGE = "Quiero saber qué datos de mi lote tienen guardados."


def test_escribir_un_mensaje_lo_guarda_y_deja_la_traza_sin_el_texto(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    with capture_logs() as logs:
        response = client.post("/api/v1/me/tickets", json={"message": f"  {MESSAGE} "})
    assert response.status_code == 201
    ticket = response.json()
    assert (ticket["message"], ticket["status"], ticket["lot_id"], ticket["closed_at"]) == (MESSAGE, "open", None, None)
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "ticket.opened"))
    assert (event.object_type, str(event.object_id), event.details) == ("ticket", ticket["ticket_id"], None)
    # El mensaje nunca va a los logs de la terminal (R9).
    assert MESSAGE not in str(logs)


def test_un_mensaje_puede_ir_sobre_un_lote_suyo(client, dataset):
    client.post("/api/v1/auth/register", json=ROSA)
    lot = client.post("/api/v1/lots", json=EL_ALTO).json()
    response = client.post("/api/v1/me/tickets", json={"message": MESSAGE, "lot_id": lot["lot_id"]})
    assert response.status_code == 201 and response.json()["lot_id"] == lot["lot_id"]


def test_un_lote_ajeno_responde_404_y_no_guarda_nada(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    lot = client.post("/api/v1/lots", json=EL_ALTO).json()
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json=LUIS)
    response = client.post("/api/v1/me/tickets", json={"message": MESSAGE, "lot_id": lot["lot_id"]})
    assert response.status_code == 404
    assert db.scalar(select(SupportTicket)) is None


def test_cada_uno_ve_solo_sus_mensajes_del_mas_reciente_al_mas_antiguo(client, dataset):
    client.post("/api/v1/auth/register", json=ROSA)
    client.post("/api/v1/me/tickets", json={"message": "Primero"})
    client.post("/api/v1/me/tickets", json={"message": "Segundo"})
    assert [t["message"] for t in client.get("/api/v1/me/tickets").json()] == ["Segundo", "Primero"]
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json=LUIS)
    assert client.get("/api/v1/me/tickets").json() == []


def test_un_mensaje_vacio_o_muy_largo_responde_422(client, dataset):
    client.post("/api/v1/auth/register", json=ROSA)
    for message in ("   ", "x" * 2001):
        assert client.post("/api/v1/me/tickets", json={"message": message}).status_code == 422


def test_sin_sesion_no_se_escribe_ni_se_lee(client, dataset, db):
    assert client.post("/api/v1/me/tickets", json={"message": MESSAGE}).status_code == 401
    assert client.get("/api/v1/me/tickets").status_code == 401
    assert db.scalar(select(SupportTicket)) is None


def test_hasta_5_mensajes_por_dia(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    for n in range(5):
        assert client.post("/api/v1/me/tickets", json={"message": f"Mensaje {n}"}).status_code == 201
    response = client.post("/api/v1/me/tickets", json={"message": "El sexto"})
    assert response.status_code == 429 and "mañana" in response.json()["error"]["message"]
    assert db.scalar(select(func.count()).select_from(SupportTicket)) == 5


def test_la_lista_trae_los_50_mas_recientes(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    user_id = db.scalar(select(ActivityEvent.actor_user_id))
    for n in range(55):
        db.add(SupportTicket(user_id=user_id, message=f"Mensaje {n}", created_at=datetime.now(UTC) - timedelta(days=60 - n)))
    db.commit()
    listed = client.get("/api/v1/me/tickets").json()
    assert len(listed) == 50 and listed[0]["message"] == "Mensaje 54"


def test_el_responsable_contesta_y_la_respuesta_se_ve_en_mis_mensajes(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    ticket_id = client.post("/api/v1/me/tickets", json={"message": MESSAGE}).json()["ticket_id"]
    assert [str(t.ticket_id) for t in tickets.open_tickets(db)] == [ticket_id]
    tickets.answer(db, uuid.UUID(ticket_id), "  Guardamos su usuario, su nombre y sus lotes.  ")
    db.commit()
    shown = client.get("/api/v1/me/tickets").json()[0]
    assert (shown["reply"], shown["status"]) == ("Guardamos su usuario, su nombre y sus lotes.", "closed")
    assert shown["replied_at"] and shown["closed_at"]
    assert tickets.open_tickets(db) == []
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "admin.ticket_updated"))
    assert (event.actor_role, str(event.object_id), event.details) == ("admin", ticket_id, None)


def test_contestar_un_mensaje_que_no_existe_o_vacio_falla(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    ticket_id = client.post("/api/v1/me/tickets", json={"message": MESSAGE}).json()["ticket_id"]
    with pytest.raises(LookupError):
        tickets.answer(db, uuid.uuid4(), "Hola")
    with pytest.raises(ValueError, match="vacía"):
        tickets.answer(db, uuid.UUID(ticket_id), "   ")


def test_un_mensaje_contestado_no_se_vuelve_a_contestar_sin_corregir(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    ticket_id = uuid.UUID(client.post("/api/v1/me/tickets", json={"message": MESSAGE}).json()["ticket_id"])
    tickets.answer(db, ticket_id, "Primera")
    db.commit()
    with pytest.raises(ValueError, match="--corregir"):
        tickets.answer(db, ticket_id, "Segunda")
    tickets.answer(db, ticket_id, "Segunda", correct=True)
    db.commit()
    assert client.get("/api/v1/me/tickets").json()[0]["reply"] == "Segunda"
    reasons = db.scalars(
        select(ActivityEvent.reason).where(ActivityEvent.action == "admin.ticket_updated").order_by(ActivityEvent.occurred_at)
    ).all()
    assert reasons == ["Respuesta por consola", "Respuesta corregida por consola"]


def test_el_limite_cuenta_desde_la_medianoche_de_la_region(client, dataset, db):
    client.post("/api/v1/auth/register", json=ROSA)
    user_id = db.scalar(select(ActivityEvent.actor_user_id))
    # Cinco mensajes de ayer (antes de la medianoche de la región) no cuentan para hoy.
    midnight = datetime.combine(region_today(), datetime.min.time(), tzinfo=region_timezone())
    for n in range(5):
        db.add(SupportTicket(user_id=user_id, message=f"Ayer {n}", created_at=midnight - timedelta(minutes=5)))
    db.commit()
    assert client.post("/api/v1/me/tickets", json={"message": "Hoy"}).status_code == 201
