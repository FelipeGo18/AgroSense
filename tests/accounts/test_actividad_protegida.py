"""HU-178: `activity_log` solo se agrega (migración 1.4) y los cálculos nunca escriben en él (R9)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import DBAPIError

from backend.accounts import activity, maintenance
from backend.accounts.trace_models import ActivityEvent
from tests.test_logs_de_calculo import CASES

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}


def events(db) -> int:
    return db.scalar(select(func.count()).select_from(ActivityEvent))


@pytest.mark.parametrize(("method", "path", "route", "body"), CASES)
def test_ningun_calculo_escribe_en_la_actividad(client, dataset, db, method, path, route, body):
    # Con sesión abierta: aun así, consultar no deja rastro de quién consultó ni de la finca (R9).
    client.post("/api/v1/auth/register", json=ROSA)
    before = events(db)
    getattr(client, method)(path, **({"json": body} if body else {}))
    db.expire_all()
    assert events(db) == before, route


def test_un_evento_no_se_modifica(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    with pytest.raises(DBAPIError, match="no se modifica"):
        db.execute(update(ActivityEvent).values(action="auth.login"))
    db.rollback()
    # Tampoco se puede poner otra persona como dueña de los datos: solo anonimizar (dejar en nulo).
    other = db.scalar(select(ActivityEvent.actor_user_id))
    with pytest.raises(DBAPIError, match="no se modifica"):
        db.execute(update(ActivityEvent).values(occurred_at=datetime.now(UTC) - timedelta(days=200)))
    db.rollback()
    assert other is not None


def test_un_evento_no_se_borra_sin_pedir_la_limpieza_o_el_olvido(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    with pytest.raises(DBAPIError, match="no se borra"):
        db.execute(delete(ActivityEvent))
    db.rollback()
    assert events(db) > 0


def test_anonimizar_si_se_puede(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    db.execute(update(ActivityEvent).values(subject_user_id=None, object_id=None))
    db.commit()
    assert db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.subject_user_id.is_not(None))) == 0


def age(db, action: str, days: int) -> None:
    """Envejece un evento para probar la limpieza. Solo en las pruebas: se apaga el disparador un momento."""
    db.execute(text("alter table activity_log disable trigger activity_log_guard"))
    db.execute(update(ActivityEvent).where(ActivityEvent.action == action).values(occurred_at=datetime.now(UTC) - timedelta(days=days)))
    db.execute(text("alter table activity_log enable trigger activity_log_guard"))
    db.commit()


def test_la_limpieza_borra_solo_lo_de_mas_de_180_dias(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    total = events(db)
    age(db, "auth.registered", 181)
    assert maintenance.run(db).events == 1
    db.commit()
    assert events(db) == total - 1
    # Aun pidiendo la limpieza, lo reciente no se borra.
    db.execute(text("select set_config('agrosense.activity_purge', 'on', true)"))
    with pytest.raises(DBAPIError, match="no se borra"):
        db.execute(delete(ActivityEvent))
    db.rollback()


def test_olvidar_a_una_persona_no_deja_borrar_los_eventos_de_otra(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    rosa = db.scalar(select(ActivityEvent.actor_user_id))
    db.execute(text("select set_config('agrosense.forget_user', :id, true)"), {"id": "00000000-0000-0000-0000-000000000000"})
    with pytest.raises(DBAPIError, match="no se borra"):
        db.execute(delete(ActivityEvent).where(ActivityEvent.actor_user_id == rosa))
    db.rollback()


def test_purge_old_y_forget_user_piden_su_permiso_en_la_misma_transaccion(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    assert activity.purge_old(db) == 0
    db.rollback()
    # El permiso no sobrevive a la transacción: borrar después falla.
    with pytest.raises(DBAPIError, match="no se borra"):
        db.execute(delete(ActivityEvent))
    db.rollback()
