"""Perfil, contraseña, actividad y borrado de la cuenta (HU-160, HU-178; specs/02-contratos.md)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, update

from backend.accounts.farm_models import Lot, Season
from backend.accounts.limits import LIMITER
from backend.accounts.models import LoginAttempt, Session, User
from backend.accounts.security import MAX_ATTEMPTS
from backend.accounts.trace_models import ActivityEvent, SupportTicket

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
LOGIN = {"username": ROSA["username"], "password": ROSA["password"]}


def register(client, **changes):
    return client.post("/api/v1/auth/register", json={**ROSA, **changes})


def actions(db, **where) -> list[tuple[str, str]]:
    db.expire_all()
    query = select(ActivityEvent.action, ActivityEvent.outcome).order_by(ActivityEvent.occurred_at, ActivityEvent.action)
    for column, value in where.items():
        query = query.where(getattr(ActivityEvent, column) == value)
    return [tuple(row) for row in db.execute(query)]


# ---------- Editar el perfil ----------


def test_editar_el_nombre_y_el_usuario_no_cierra_la_sesion(client):
    register(client)
    response = client.patch("/api/v1/me", json={"display_name": "  Rosa Elvira ", "username": "rosa.elvira"})
    assert response.status_code == 200
    assert response.json()["display_name"] == "Rosa Elvira"
    assert client.get("/api/v1/me").json()["username"] == "rosa.elvira"
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={**LOGIN, "username": "rosa.elvira"}).status_code == 200


def test_las_prioridades_se_guardan_y_nulo_vuelve_a_las_de_agrosense(client):
    register(client)
    weights = {"water": 5, "frost": 3, "heat": 2, "soil": 1, "supply": 0, "market": 1}
    assert client.patch("/api/v1/me", json={"priorities": weights}).json()["priorities"] == weights
    # Un campo que no viene no cambia.
    assert client.patch("/api/v1/me", json={"display_name": "Rosa E."}).json()["priorities"] == weights
    assert client.patch("/api/v1/me", json={"priorities": None}).json()["priorities"] is None


def test_prioridades_fuera_de_rango_o_todas_en_cero_responden_422(client):
    register(client)
    for bad in ({"water": 6}, {"water": -1}, {"water": 0, "frost": 0}, {"lluvia": 3}, {}):
        assert client.patch("/api/v1/me", json={"priorities": bad}).status_code == 422, bad
    assert client.get("/api/v1/me").json()["priorities"] is None


def test_un_usuario_ya_tomado_responde_409_y_no_cambia_nada(client):
    register(client)
    client.cookies.clear()
    register(client, username="otra.persona")
    response = client.patch("/api/v1/me", json={"username": "rosa.samaca", "display_name": "Impostora"})
    assert response.status_code == 409
    assert client.get("/api/v1/me").json()["display_name"] == "Rosa"


def test_el_nombre_y_el_usuario_no_se_pueden_vaciar(client):
    register(client)
    assert client.patch("/api/v1/me", json={"display_name": None}).status_code == 422
    assert client.patch("/api/v1/me", json={"username": "Con Espacios"}).status_code == 422
    assert client.patch("/api/v1/me", json={"role": "admin"}).status_code == 422  # nadie se sube el rol


# ---------- Cambiar la contraseña ----------


def test_cambiar_la_contrasena_cierra_las_demas_sesiones_y_deja_la_actual(client, db):
    register(client)
    client.post("/api/v1/auth/login", json=LOGIN)  # otra sesión, como desde otro dispositivo
    assert db.scalar(select(func.count()).select_from(Session)) == 2
    response = client.post("/api/v1/me/password", json={"current_password": ROSA["password"], "new_password": "arveja-verde-2027"})
    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Session)) == 1
    assert client.get("/api/v1/me").status_code == 200
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 401
    assert client.post("/api/v1/auth/login", json={**LOGIN, "password": "arveja-verde-2027"}).status_code == 200


def test_contrasena_actual_incorrecta_responde_403_y_la_sesion_sigue(client):
    register(client)
    response = client.post("/api/v1/me/password", json={"current_password": "no-es-esta", "new_password": "arveja-verde-2027"})
    assert response.status_code == 403
    assert client.get("/api/v1/me").status_code == 200


def test_contrasena_nueva_corta_o_igual_a_la_actual_responde_422(client):
    register(client)
    assert client.post("/api/v1/me/password", json={"current_password": ROSA["password"], "new_password": "corta"}).status_code == 422
    same = client.post("/api/v1/me/password", json={"current_password": ROSA["password"], "new_password": ROSA["password"]})
    assert same.status_code == 422


def test_los_intentos_fallidos_de_cambiar_la_contrasena_cuentan_como_los_de_entrar(client):
    register(client)
    for _ in range(5):
        client.post("/api/v1/me/password", json={"current_password": "no-es-esta", "new_password": "arveja-verde-2027"})
    good = client.post("/api/v1/me/password", json={"current_password": ROSA["password"], "new_password": "arveja-verde-2027"})
    assert good.status_code == 429


# ---------- Tope de intentos ----------


def test_el_tope_guarda_un_hash_y_no_lo_que_se_escribio(client, db):
    client.post("/api/v1/auth/login", json={"username": "mi-contraseña-secreta", "password": "xxxxxxxx"})
    attempt = db.scalar(select(LoginAttempt))
    assert len(attempt.username_hash) == 64 and "secreta" not in attempt.username_hash


def test_el_tope_general_sobrevive_a_un_reinicio_y_se_levanta_a_los_15_minutos(client, db):
    """20 fallidos desde cualquier conexión bloquean al usuario. Ese tope vive en la base de datos, no en la memoria."""
    register(client)
    client.cookies.clear()
    key = hashlib.sha256(f"intento:{ROSA['username']}".encode()).hexdigest()
    db.add_all(LoginAttempt(username_hash=key) for _ in range(MAX_ATTEMPTS))
    db.commit()
    LIMITER.reset()  # como un reinicio: los límites de memoria se pierden; este no
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 429
    db.execute(update(LoginAttempt).values(attempted_at=datetime.now(UTC) - timedelta(minutes=15, seconds=1)))
    db.commit()
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    assert db.scalar(select(func.count()).select_from(LoginAttempt)) == 0


# ---------- Trazabilidad ----------


def test_cada_cosa_que_pasa_con_la_cuenta_deja_su_evento(client, db):
    request_id = str(uuid.uuid4())
    register(client)
    client.patch("/api/v1/me", json={"display_name": "Rosa E."}, headers={"X-Request-ID": request_id})
    client.post("/api/v1/me/password", json={"current_password": "no-es-esta", "new_password": "arveja-verde-2027"})
    client.post("/api/v1/me/password", json={"current_password": ROSA["password"], "new_password": "arveja-verde-2027"})
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={**LOGIN, "password": "no-es-esta"})
    assert sorted(actions(db)) == sorted(
        [
            ("auth.registered", "ok"),
            ("consent.accepted", "ok"),
            ("auth.login", "ok"),
            ("profile.updated", "ok"),
            ("auth.password_changed", "failed"),
            ("auth.password_changed", "ok"),
            ("auth.logout", "ok"),
            ("auth.login_failed", "failed"),
        ]
    )
    edit = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "profile.updated"))
    # Solo los nombres de los campos que cambiaron, nunca sus valores; y el mismo identificador de la petición.
    assert edit.details == {"fields": ["display_name"]}
    assert str(edit.request_id) == request_id
    assert edit.actor_role == "farmer" and edit.subject_user_id == edit.actor_user_id


def test_un_intento_con_un_usuario_que_no_existe_no_guarda_lo_que_se_escribio(client, db):
    client.post("/api/v1/auth/login", json={"username": "mi-contraseña-secreta", "password": "xxxxxxxx"})
    event = db.scalar(select(ActivityEvent))
    assert (event.action, event.outcome, event.actor_user_id, event.details) == ("auth.login_failed", "failed", None, None)


def test_un_cambio_que_no_ocurrio_no_deja_evento(client, db):
    register(client)
    before = len(actions(db))
    client.patch("/api/v1/me", json={"display_name": "Rosa"})  # el mismo nombre: no cambió nada
    client.patch("/api/v1/me", json={"priorities": {"water": 9}})  # inválido
    assert len(actions(db)) == before


def test_mi_actividad_va_de_lo_mas_reciente_a_lo_mas_antiguo_y_por_paginas(client, db):
    register(client)
    for i in range(4):
        client.patch("/api/v1/me", json={"display_name": f"Rosa {i}"})
    first = client.get("/api/v1/me/activity", params={"limit": 3}).json()
    assert [item["action"] for item in first["items"]] == ["profile.updated"] * 3
    assert set(first["items"][0]) == {
        "event_id",
        "occurred_at",
        "action",
        "actor_role",
        "object_type",
        "object_id",
        "outcome",
        "ticket_id",
        "details",
    }
    rest = client.get("/api/v1/me/activity", params={"limit": 50, "before": first["next_before"]}).json()
    assert len(rest["items"]) == 4 and rest["next_before"] is None
    assert client.get("/api/v1/me/activity", params={"limit": 51}).status_code == 422


def test_cada_quien_ve_solo_su_actividad(client):
    register(client)
    client.cookies.clear()
    register(client, username="otra.persona")
    items = client.get("/api/v1/me/activity").json()["items"]
    assert len(items) == 3  # registro, consentimiento y entrada de esta cuenta; nada de la otra


# ---------- Borrar la cuenta ----------


def test_borrar_la_cuenta_se_lleva_todo_lo_suyo(client, db):
    register(client)
    user = db.scalar(select(User))
    lot = Lot(user_id=user.user_id, municipality_id="15646", name="El Alto", area_ha=Decimal("2.51"))
    db.add(lot)
    db.flush()
    db.add(Season(lot_id=lot.lot_id, crop_id="papa", area_ha=Decimal("1.2"), sowing_date=datetime(2026, 8, 2).date()))
    ticket = SupportTicket(user_id=user.user_id, lot_id=lot.lot_id, message="No me deja guardar la siembra")
    db.add(ticket)
    db.flush()
    # Lo que soporte hizo sobre sus datos se conserva, pero sin decir de quién eran.
    admin = User(
        username="soporte", password_hash="x", display_name="Soporte", role="admin", consent_version=3, consent_at=datetime.now(UTC)
    )
    db.add(admin)
    db.flush()
    db.add(
        ActivityEvent(
            actor_user_id=admin.user_id,
            actor_role="admin",
            subject_user_id=user.user_id,
            action="admin.lot_deleted",
            object_type="lot",
            object_id=lot.lot_id,
            ticket_id=ticket.ticket_id,
            reason="Lo pidió por el ticket",
        )
    )
    db.commit()

    assert client.request("DELETE", "/api/v1/me", json={"password": ROSA["password"]}).status_code == 204
    db.expire_all()
    assert db.scalars(select(User.username)).all() == ["soporte"]
    for table in (Session, Lot, Season, SupportTicket):
        assert db.scalar(select(func.count()).select_from(table)) == 0, table.__tablename__
    kept = db.scalars(select(ActivityEvent)).all()
    assert [event.action for event in kept] == ["admin.lot_deleted"]
    assert (kept[0].subject_user_id, kept[0].object_id, kept[0].reason, kept[0].ticket_id) == (None, None, None, None)
    assert kept[0].actor_user_id == admin.user_id
