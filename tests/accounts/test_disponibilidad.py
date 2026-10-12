"""La API sube siempre. Las cuentas solo se atienden con la base de datos arriba y el esquema al día; si no, responden
503 y el log dice por qué. También: la línea de log de cada petición y lo que nunca se escribe (HU-177)."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from structlog.testing import capture_logs

from backend.api.main import app
from backend.config.logging import REDACTED, redact
from backend.db import migrate, state
from backend.db.session import get_db
from tests.conftest import alembic_config

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
LOGIN = {"username": ROSA["username"], "password": ROSA["password"]}


def offline_client(database_url) -> TestClient:
    """La API apuntando a un puerto donde no hay ninguna base de datos."""
    factory = sessionmaker(create_engine(database_url.set(port=9), connect_args={"connect_timeout": 1}))

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app, base_url="https://testserver")


# ---------- Con la base de datos apagada ----------


def test_con_la_base_apagada_las_cuentas_responden_503_y_el_log_dice_por_que(database_url):
    try:
        with offline_client(database_url) as client, capture_logs() as logs:
            for response in (
                client.post("/api/v1/auth/login", json=LOGIN),
                client.post("/api/v1/auth/register", json=ROSA),
                client.get("/api/v1/me"),
            ):
                assert response.status_code == 503
                error = response.json()["error"]
                assert error["code"] == "accounts_database_down"
                # A la persona no se le cuentan detalles internos: solo qué puede hacer.
                assert error["message"] == "Las cuentas no están disponibles en este momento. Puede seguir consultando sin cuenta."
        reasons = [entry for entry in logs if entry["event"] == "accounts_unavailable"]
        assert len(reasons) == 3
        assert reasons[0]["log_level"] == "warning" and reasons[0]["reason"] == "database_down"
        assert reasons[0]["detail"] == "Cuentas no disponibles (503) porque la base de datos está apagada o no responde"
    finally:
        app.dependency_overrides.clear()
        state.forget_down()


def test_con_la_base_apagada_la_api_sigue_respondiendo(database_url):
    try:
        with offline_client(database_url) as client:
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["accounts"] == {
            "available": False,
            "reason": "database_down",
            "current_migration": None,
            "expected_migration": "1.3",
        }
    finally:
        app.dependency_overrides.clear()
        state.forget_down()


def test_con_la_base_apagada_no_se_la_espera_en_cada_peticion(monkeypatch):
    """La primera petición descubre que la base no responde (y espera). Las siguientes responden de inmediato,
    sin volver a intentar conectarse, durante unos segundos. Pasado ese tiempo se intenta de nuevo."""
    from sqlalchemy.exc import OperationalError

    class Db:
        attempts = 0
        answer: str | None = None

        def scalar(self, _query):
            Db.attempts += 1
            if Db.answer is None:
                raise OperationalError("select", {}, Exception("sin conexión"))
            return Db.answer

        def rollback(self):
            pass

    now = [1000.0]
    monkeypatch.setattr(state.time, "monotonic", lambda: now[0])
    state.forget_down()
    try:
        assert state.accounts_state(Db()).reason == "database_down"
        assert Db.attempts == 1
        for _ in range(20):
            assert state.accounts_state(Db()).reason == "database_down"
        assert Db.attempts == 1  # veinte peticiones más y ni un intento de conexión
        # Aunque la base ya haya vuelto, se sigue diciendo «apagada» hasta que pase la espera.
        Db.answer = "1.3"
        now[0] += state.DOWN_MEMORY_SECONDS - 0.1
        assert state.accounts_state(Db()).reason == "database_down"
        now[0] += 0.2
        assert state.accounts_state(Db()).reason == "ok"
        assert Db.attempts == 2
    finally:
        state.forget_down()


# ---------- Con una migración sin aplicar ----------


def test_con_una_migracion_pendiente_las_cuentas_se_apagan_y_el_log_dice_cual(client, monkeypatch):
    assert client.post("/api/v1/auth/register", json=ROSA).status_code == 201
    # El código trae una migración que la base de datos todavía no tiene.
    monkeypatch.setattr(state, "expected_revision", lambda: "2.1")
    with capture_logs() as logs:
        response = client.get("/api/v1/me")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "accounts_migration_pending"
    entry = next(entry for entry in logs if entry["event"] == "accounts_unavailable")
    assert (entry["reason"], entry["current_migration"], entry["expected_migration"]) == ("migration_pending", "1.3", "2.1")
    assert entry["detail"] == "Cuentas no disponibles (503) porque la migración 2.1 no se completó; la base de datos está en la 1.3"
    health = client.get("/api/v1/health").json()
    assert health["status"] == "ok"
    assert health["accounts"] == {
        "available": False,
        "reason": "migration_pending",
        "current_migration": "1.3",
        "expected_migration": "2.1",
    }


def test_con_todo_al_dia_las_cuentas_estan_disponibles(client):
    assert client.get("/api/v1/health").json()["accounts"] == {
        "available": True,
        "reason": "ok",
        "current_migration": "1.3",
        "expected_migration": "1.3",
    }


# ---------- Al arrancar ----------


def test_al_arrancar_con_la_base_apagada_lo_registra_y_deja_subir_la_api(database_url):
    with capture_logs() as logs:
        migrate.on_startup(database_url.set(port=9), alembic_config(database_url))  # termina bien
    assert [(entry["event"], entry["log_level"], entry["reason"]) for entry in logs] == [("migration_skipped", "warning", "database_down")]


def test_al_arrancar_si_la_migracion_falla_lo_registra_con_las_dos_versiones_y_deja_subir_la_api(engine, database_url, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("columna duplicada")

    monkeypatch.setattr(migrate, "migrate", broken)
    with capture_logs() as logs:
        migrate.on_startup(database_url, alembic_config(database_url))  # termina bien
    assert len(logs) == 1
    entry = logs[0]
    assert (entry["event"], entry["log_level"]) == ("migration_failed", "error")
    assert (entry["current_migration"], entry["expected_migration"]) == ("1.3", "1.3")
    assert "no se completó: columna duplicada" in entry["detail"]


def test_al_arrancar_con_todo_al_dia_no_hace_nada(engine, database_url):
    with capture_logs() as logs:
        migrate.on_startup(database_url, alembic_config(database_url))
    assert [(entry["event"], entry["current_migration"]) for entry in logs] == [("migration_up_to_date", "1.3")]


# ---------- Logs de la terminal ----------


def test_cada_peticion_deja_una_linea_con_los_campos_del_contrato(client):
    client.post("/api/v1/auth/register", json=ROSA)
    with capture_logs() as logs:
        response = client.patch(
            "/api/v1/me", json={"display_name": "Rosa E."}, headers={"X-Request-ID": "0b0e4f6e-58a5-4c0e-9d7a-2f1f3a5b7c9d"}
        )
    line = next(entry for entry in logs if entry["event"] == "request")
    assert (line["method"], line["route"], line["status"], line["log_level"]) == ("PATCH", "/api/v1/me", 200, "info")
    assert isinstance(line["duration_ms"], int)
    # Quién fue: su identificador y su rol. Nunca su usuario, su nombre ni lo que envió.
    assert line["user_id"] == response.json()["user_id"] and line["role"] == "farmer"
    assert "rosa" not in str(line).lower()


def request_line(logs) -> dict:
    return next(entry for entry in logs if entry["event"] == "request")


def test_el_log_dice_por_que_fallo_un_inicio_de_sesion_aunque_a_la_persona_se_le_diga_lo_mismo(client):
    client.post("/api/v1/auth/register", json=ROSA)
    client.cookies.clear()
    with capture_logs() as logs:
        unknown = client.post("/api/v1/auth/login", json={"username": "nadie", "password": "xxxxxxxx"})
    assert request_line(logs)["detail"] == "Inicio de sesión rechazado: usuario no registrado"
    assert request_line(logs)["endpoint"] == "auth.login"
    with capture_logs() as logs:
        wrong = client.post("/api/v1/auth/login", json={**LOGIN, "password": "no-es-esta"})
    assert request_line(logs)["detail"] == "Inicio de sesión rechazado: contraseña incorrecta"
    # La respuesta no distingue los dos casos, y el log no repite ni el usuario ni la contraseña que se escribieron.
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]
    assert "nadie" not in str(logs) and "no-es-esta" not in str(logs)


def test_cada_respuesta_se_explica_en_el_log(client):
    cases = [
        (
            lambda: client.post("/api/v1/auth/register", json={**ROSA, "consent_accepted": False}),
            "Registro rechazado: no aceptó el consentimiento vigente (versión 3)",
        ),
        (
            lambda: client.post("/api/v1/auth/register", json={**ROSA, "password": "corta"}),
            "Petición rechazada: datos inválidos en password",
        ),
        (lambda: client.get("/api/v1/me"), "Petición rechazada: no trae cookie de sesión"),
        (lambda: client.post("/api/v1/auth/register", json=ROSA), "Cuenta creada y sesión abierta"),
        (lambda: client.get("/api/v1/me"), "Perfil consultado"),
        (lambda: client.patch("/api/v1/me", json={"display_name": "Rosa E."}), "Perfil actualizado: display_name"),
        (lambda: client.patch("/api/v1/me", json={"display_name": "Rosa E."}), "Perfil sin cambios: llegó lo mismo que ya tenía"),
        (
            lambda: client.post("/api/v1/me/password", json={"current_password": "no-es-esta", "new_password": "arveja-verde-2027"}),
            "Cambio de contraseña rechazado: la contraseña actual es incorrecta",
        ),
        (lambda: client.get("/api/v1/health"), "Estado de la API consultado: cuentas disponibles"),
        (lambda: client.post("/api/v1/auth/logout"), "Sesión cerrada"),
        (lambda: client.get("/api/v1/no-existe"), "No existe esa dirección en la API"),
    ]
    for call, expected in cases:
        with capture_logs() as logs:
            call()
        assert request_line(logs)["detail"] == expected


def test_una_sesion_cerrada_o_vencida_lo_dice_en_el_log(client):
    client.post("/api/v1/auth/register", json=ROSA)
    token = client.cookies["agrosense_session"]
    client.post("/api/v1/auth/logout")
    client.cookies.set("agrosense_session", token)
    with capture_logs() as logs:
        client.get("/api/v1/me")
    assert request_line(logs)["detail"] == "Petición rechazada: la sesión no existe o ya fue cerrada"


def test_lo_rechazado_sale_como_aviso(client):
    with capture_logs() as logs:
        client.post("/api/v1/auth/register", json=ROSA, headers={"Origin": "https://sitio-malicioso.example"})
    line = next(entry for entry in logs if entry["event"] == "request")
    assert (line["status"], line["log_level"]) == (403, "warning")
    assert (
        line["detail"]
        == "Petición rechazada: viene de https://sitio-malicioso.example, que no es la web de AgroSense (protección contra CSRF)"
    )
    assert "user_id" not in line


def test_el_log_nunca_lleva_contrasenas_tokens_ni_poligonos():
    event = {
        "event": "x",
        "password": "papa-criolla-2026",
        "Token": "abc",
        "body": {"new_password": "otra", "geometry": {"type": "Polygon"}, "name": "El Alto"},
        "items": [{"cookie": "c", "authorization": "Bearer x"}],
    }
    clean = redact(None, "info", event)
    assert clean["password"] == clean["Token"] == REDACTED
    assert clean["body"] == {"new_password": REDACTED, "geometry": REDACTED, "name": "El Alto"}
    assert clean["items"] == [{"cookie": REDACTED, "authorization": REDACTED}]
    assert "papa-criolla" not in str(clean)
