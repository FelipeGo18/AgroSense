"""Lo que arregló la revisión de seguridad de las cuentas del 13 de octubre de 2026 (HU-162, HU-160, HU-178, HU-177)."""

import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import sessionmaker
from structlog.testing import capture_logs

from backend.accounts import maintenance, security
from backend.accounts.limits import FAILED_PER_IP_AND_USER, LIMITER, LOGIN_PER_IP, REGISTER_PER_IP, Limiter
from backend.accounts.models import LoginAttempt, Session, User
from backend.accounts.security import MAX_ATTEMPTS, clear_attempts, take_attempt
from backend.accounts.trace_models import ActivityEvent
from backend.api import main
from backend.api.auth import SESSION_COOKIE
from backend.config.logging import escape_control
from backend.config.settings import Settings, get_settings
from backend.db import migrate
from backend.db.session import get_engine
from tests.conftest import alembic_config

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
LOGIN = {"username": ROSA["username"], "password": ROSA["password"]}
WRONG = {**LOGIN, "password": "no-es-esta"}
# Contraseñas que no coinciden para un usuario desde una misma conexión antes del 429.
PER_CONNECTION = FAILED_PER_IP_AND_USER.limit


@contextmanager
def other_connection(ip: str = "198.51.100.20"):
    """La misma API (y la misma base de pruebas que `client`), vista desde otra IP."""
    with TestClient(main.app, base_url="https://testserver", client=(ip, 50000)) as other:
        yield other


def denied(db, action: str) -> int:
    db.expire_all()
    return db.scalar(
        select(func.count()).select_from(ActivityEvent).where(ActivityEvent.action == action, ActivityEvent.outcome == "denied")
    )


def attempts(db) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(LoginAttempt))


# ---------- Tope de intentos ----------


def test_varias_peticiones_a_la_vez_no_se_saltan_el_tope_general(client, engine):
    """El intento se anota antes de verificar la contraseña: de 25 a la vez, a lo sumo 20 llegan a verificarla."""
    factory = sessionmaker(engine, expire_on_commit=False)
    start = threading.Barrier(25)
    taken: list[bool] = []

    def one() -> None:
        with factory() as db:
            start.wait()
            taken.append(take_attempt(db, "rosa.samaca") is not None)

    threads = [threading.Thread(target=one) for _ in range(25)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert taken.count(True) <= MAX_ATTEMPTS
    with factory() as db:
        # Los que no cupieron no quedan anotados: el bloqueo no se alarga.
        assert attempts(db) == taken.count(True)
        clear_attempts(db, "rosa.samaca")
        db.commit()


def test_varias_peticiones_a_la_vez_no_se_saltan_el_tope_de_la_conexion():
    limiter = Limiter()
    start = threading.Barrier(12)
    taken: list[bool] = []

    def one() -> None:
        start.wait()
        taken.append(not isinstance(limiter.take(FAILED_PER_IP_AND_USER, "10.0.0.1", "rosa.samaca"), float))

    threads = [threading.Thread(target=one) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert taken.count(True) == PER_CONNECTION


def test_un_intento_rechazado_por_el_tope_no_alarga_el_bloqueo(client, db, monkeypatch):
    client.post("/api/v1/auth/register", json=ROSA)
    client.cookies.clear()
    for _ in range(PER_CONNECTION):
        assert client.post("/api/v1/auth/login", json=WRONG).status_code == 401
    for _ in range(3):
        blocked = client.post("/api/v1/auth/login", json=LOGIN)
        assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "too_many_attempts"
        assert 0 < int(blocked.headers["Retry-After"]) <= 900
    assert attempts(db) == PER_CONNECTION
    # A los 15 minutos de los fallidos se levanta, aunque después haya seguido intentando.
    later = time.monotonic() + 15 * 60 + 1
    monkeypatch.setattr(LIMITER, "clock", lambda: later)
    db.execute(update(LoginAttempt).values(attempted_at=datetime.now(UTC) - timedelta(minutes=15, seconds=1)))
    db.commit()
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200


def test_equivocarse_desde_una_conexion_no_bloquea_la_cuenta_en_otra(client):
    """Quien escribe mal la contraseña de otra persona a propósito solo se bloquea a sí mismo."""
    client.post("/api/v1/auth/register", json=ROSA)
    client.cookies.clear()
    for _ in range(PER_CONNECTION):
        client.post("/api/v1/auth/login", json=WRONG)
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 429
    with other_connection() as home:
        assert home.post("/api/v1/auth/login", json=LOGIN).status_code == 200


def test_entrar_bien_no_cuenta_como_intento(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    client.cookies.clear()
    for _ in range(PER_CONNECTION + 2):
        assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    assert attempts(db) == 0


def test_una_contrasena_nueva_igual_a_la_actual_no_cuenta_como_intento(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    same = {"current_password": ROSA["password"], "new_password": ROSA["password"]}
    for _ in range(PER_CONNECTION + 1):
        assert client.post("/api/v1/me/password", json=same).status_code == 422
    assert attempts(db) == 0


# ---------- Un evento por bloqueo ----------


def test_un_bloqueo_deja_un_solo_evento_aunque_se_repita_la_peticion(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    client.cookies.clear()
    for _ in range(PER_CONNECTION):
        client.post("/api/v1/auth/login", json=WRONG)
    for _ in range(4):
        assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 429
    assert denied(db, "auth.login_failed") == 1


def test_el_bloqueo_de_un_usuario_que_no_existe_no_llena_el_registro(client, db):
    nobody = {"username": "nadie", "password": "xxxxxxxx"}
    for _ in range(PER_CONNECTION):
        client.post("/api/v1/auth/login", json=nobody)
    for _ in range(4):
        assert client.post("/api/v1/auth/login", json=nobody).status_code == 429
    db.expire_all()
    # Quedan los 5 fallidos, sin actor; los rechazos por el tope no agregan nada.
    assert db.scalar(select(func.count()).select_from(ActivityEvent)) == PER_CONNECTION
    assert denied(db, "auth.login_failed") == 0


def test_el_bloqueo_al_cambiar_la_contrasena_tambien_deja_un_solo_evento(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    bad = {"current_password": "no-es-esta", "new_password": "arveja-verde-2027"}
    for _ in range(PER_CONNECTION + 3):
        client.post("/api/v1/me/password", json=bad)
    assert denied(db, "auth.password_changed") == 1


# ---------- Límite por conexión ----------


def test_una_conexion_entra_hasta_30_veces_en_15_minutos(client):
    client.post("/api/v1/auth/register", json=ROSA)
    for _ in range(LOGIN_PER_IP.limit):
        assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    response = client.post("/api/v1/auth/login", json=LOGIN)
    assert response.status_code == 429 and response.json()["error"]["code"] == "too_many_requests"
    assert int(response.headers["Retry-After"]) > 0
    # Otra conexión sigue entrando.
    with other_connection() as home:
        assert home.post("/api/v1/auth/login", json=LOGIN).status_code == 200


def test_una_conexion_intenta_hasta_10_registros_por_hora(client, db):
    # Los rechazados (409) también cuentan: así no se prueba en masa qué usuarios existen.
    client.post("/api/v1/auth/register", json=ROSA)
    for _ in range(REGISTER_PER_IP.limit - 1):
        assert client.post("/api/v1/auth/register", json=ROSA).status_code == 409
    response = client.post("/api/v1/auth/register", json={**ROSA, "username": "otra.persona"})
    assert response.status_code == 429 and response.json()["error"]["code"] == "too_many_requests"
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_la_ip_no_queda_en_el_log_ni_en_la_base(client, db):
    with other_connection("203.0.113.77") as home, capture_logs() as logs:
        home.post("/api/v1/auth/register", json=ROSA)
        home.post("/api/v1/auth/login", json=WRONG)
    assert "203.0.113.77" not in str(logs)
    db.expire_all()
    rows = [str(row) for model in (LoginAttempt, ActivityEvent) for row in db.execute(select(model.__table__)).all()]
    assert rows and not any("203.0.113.77" in row for row in rows)


def test_con_todos_los_calculos_de_contrasena_ocupados_responde_503(client, monkeypatch):
    full = threading.BoundedSemaphore(1)
    full.acquire()
    monkeypatch.setattr(security, "_slots", full)
    monkeypatch.setattr(security, "ARGON2_WAIT_S", 0.05)
    response = client.post("/api/v1/auth/login", json=LOGIN)
    assert response.status_code == 503 and response.json()["error"]["code"] == "server_busy"
    assert response.headers["Retry-After"] == "5"


# ---------- Borrar la cuenta pide la contraseña ----------


def test_borrar_la_cuenta_sin_la_contrasena_o_con_otra_no_borra_nada(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    assert client.delete("/api/v1/me").status_code == 422
    wrong = client.request("DELETE", "/api/v1/me", json={"password": "no-es-esta"})
    assert wrong.status_code == 403 and wrong.json()["error"]["code"] == "wrong_password"
    # La cuenta y la sesión siguen.
    assert client.get("/api/v1/me").status_code == 200
    db.expire_all()
    failed = db.scalar(select(ActivityEvent).where(ActivityEvent.action == "account.deleted"))
    assert failed.outcome == "failed"


def test_las_contrasenas_malas_al_borrar_cuentan_para_el_tope(client):
    client.post("/api/v1/auth/register", json=ROSA)
    for _ in range(PER_CONNECTION):
        client.request("DELETE", "/api/v1/me", json={"password": "no-es-esta"})
    assert client.request("DELETE", "/api/v1/me", json={"password": ROSA["password"]}).status_code == 429
    assert client.get("/api/v1/me").status_code == 200


# ---------- Limpieza de los 180 días ----------


def test_al_arrancar_se_borra_la_actividad_de_mas_de_180_dias(client, db, engine, database_url):
    client.post("/api/v1/auth/register", json=ROSA)
    db.execute(
        update(ActivityEvent).where(ActivityEvent.action == "auth.registered").values(occurred_at=datetime.now(UTC) - timedelta(days=181))
    )
    db.commit()
    with capture_logs() as logs:
        migrate.on_startup(database_url, alembic_config(database_url))
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.action == "auth.registered")) == 0
    # Lo de menos de 180 días se queda.
    assert db.scalar(select(func.count()).select_from(ActivityEvent)) == 2
    assert [entry["purged"] for entry in logs if entry["event"] == "activity_purged"] == [1]


def test_al_arrancar_se_borran_las_sesiones_vencidas(client, db, database_url):
    client.post("/api/v1/auth/register", json=ROSA)
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json=LOGIN)
    # Dos sesiones (la de salir ya se borró; queda la de antes en otra conexión): vence la que no es la de ahora.
    current = security.hash_token(client.cookies[SESSION_COOKIE])
    db.add(Session(user_id=db.scalar(select(User.user_id)), token_hash="vieja", expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Session).where(Session.token_hash != current)) == 1
    with capture_logs() as logs:
        migrate.on_startup(database_url, alembic_config(database_url))
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Session)) == 1
    assert client.get("/api/v1/me").status_code == 200
    assert [entry["purged"] for entry in logs if entry["event"] == "sessions_purged"] == [1]


def test_entrar_solo_inicia_sesion_y_no_limpia(client, db):
    """Cada endpoint hace solo lo suyo: lo vencido lo borra el mantenimiento, no el inicio de sesión."""
    client.post("/api/v1/auth/register", json=ROSA)
    db.execute(update(Session).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.execute(
        update(ActivityEvent).where(ActivityEvent.action == "auth.registered").values(occurred_at=datetime.now(UTC) - timedelta(days=181))
    )
    db.commit()
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Session)) == 2
    assert db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.action == "auth.registered")) == 1


def test_el_mantenimiento_dice_cuanto_borro(client, db):
    client.post("/api/v1/auth/register", json=ROSA)
    db.execute(update(Session).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.execute(
        update(ActivityEvent).where(ActivityEvent.action == "auth.registered").values(occurred_at=datetime.now(UTC) - timedelta(days=181))
    )
    db.commit()
    assert maintenance.run(db) == maintenance.Cleaned(sessions=1, events=1)
    db.commit()
    assert maintenance.run(db) == maintenance.Cleaned(sessions=0, events=0)


# ---------- Mi actividad: páginas sin huecos ----------


def test_mi_actividad_no_pierde_eventos_que_comparten_la_hora(client):
    # El registro deja tres eventos con la misma hora (una sola petición); después, dos cambios.
    client.post("/api/v1/auth/register", json=ROSA)
    for name in ("Rosa E.", "Rosa Elvira"):
        client.patch("/api/v1/me", json={"display_name": name})
    seen: list[str] = []
    before = None
    for limit in (2, 1, 1, 1):
        params = {"limit": limit} | ({"before": before} if before else {})
        body = client.get("/api/v1/me/activity", params=params).json()
        seen += [item["event_id"] for item in body["items"]]
        before = body["next_before"]
        if before is None:
            break
    assert len(seen) == len(set(seen)) == 5


def test_una_pagina_que_corta_entre_eventos_de_la_misma_hora_los_trae_todos(client):
    client.post("/api/v1/auth/register", json=ROSA)
    body = client.get("/api/v1/me/activity", params={"limit": 1}).json()
    assert len(body["items"]) == 3 and body["next_before"] is None


# ---------- Cabeceras de seguridad ----------


def test_toda_respuesta_lleva_las_cabeceras_de_seguridad(client):
    for response in (
        client.get("/api/v1/me"),  # 401
        client.post("/api/v1/auth/register", json=ROSA, headers={"Origin": "https://sitio-malicioso.example"}),  # 403 CSRF
        client.get("/api/v1/version"),
        client.get("/api/v1/no-existe"),
    ):
        headers = response.headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
        # El cliente de pruebas va por HTTPS.
        assert headers["Strict-Transport-Security"].startswith("max-age=")


def test_lo_de_la_cuenta_no_se_guarda_en_cache(client):
    register = client.post("/api/v1/auth/register", json=ROSA)
    for response in (register, client.get("/api/v1/me"), client.get("/api/v1/me/activity")):
        assert response.headers["Cache-Control"] == "no-store"
    assert "no-store" not in client.get("/api/v1/version").headers.get("Cache-Control", "")


def test_por_http_no_se_manda_hsts():
    assert "Strict-Transport-Security" not in TestClient(main.app, base_url="http://testserver").get("/api/v1/version").headers


# ---------- La documentación de la API solo en desarrollo ----------


@pytest.mark.parametrize(("value", "status"), [(None, 404), ("false", 404), ("true", 200)])
def test_la_documentacion_de_la_api_solo_existe_si_se_enciende(monkeypatch, value, status):
    if value is None:
        monkeypatch.delenv("AGROSENSE_API_DOCS", raising=False)
    else:
        monkeypatch.setenv("AGROSENSE_API_DOCS", value)
    # Sin leer el .env de quien corre las pruebas: solo cuenta la variable.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    try:
        client = TestClient(main.create_app())
        assert client.get("/api/openapi.json").status_code == status
        assert client.get("/api/docs").status_code == status
    finally:
        get_settings.cache_clear()


# ---------- Logs ----------


def test_una_direccion_que_no_existe_no_se_escribe_en_el_log(client):
    with capture_logs() as logs:
        client.get("/api/v1/no-existe/%1b%5b31mrojo")
    line = next(entry for entry in logs if entry["event"] == "request")
    assert line["route"] == "[sin ruta]" and "rojo" not in str(line)


def test_los_caracteres_de_control_se_escriben_y_no_actuan():
    event = {"event": "request", "detail": "viene de https://x\x1b[31m\nfalso", "items": ["\x07"], "status": 403}
    clean = escape_control(None, "warning", event)
    assert clean["detail"] == "viene de https://x\\x1b[31m\\x0afalso"
    assert clean["items"] == ["\\x07"] and clean["status"] == 403


def test_las_trazas_de_errores_de_base_de_datos_no_llevan_los_valores_de_la_consulta():
    assert get_engine().hide_parameters is True
