"""Escribirle al responsable de los datos: `POST` y `GET /api/v1/me/tickets` (HU-163, HU-170; R9)."""

from sqlalchemy import select
from structlog.testing import capture_logs

from backend.accounts.trace_models import ActivityEvent, SupportTicket

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
