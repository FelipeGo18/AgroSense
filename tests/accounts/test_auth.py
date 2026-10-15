"""Crear cuenta, entrar, salir y borrar la cuenta (HU-162, HU-163; specs/02-contratos.md)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from backend.accounts.models import Session, User
from backend.accounts.security import hash_token
from backend.api.auth import SESSION_COOKIE

ROSA = {"username": "rosa.samaca", "password": "papa-criolla-2026", "display_name": "Rosa", "consent_version": 3, "consent_accepted": True}
LOGIN = {"username": ROSA["username"], "password": ROSA["password"]}


def register(client, **changes):
    return client.post("/api/v1/auth/register", json={**ROSA, **changes})


# ---------- Crear cuenta ----------


def test_crear_cuenta_deja_la_sesion_abierta(client, db):
    response = register(client)
    assert response.status_code == 201
    profile = response.json()
    assert profile["username"] == "rosa.samaca"
    assert profile["role"] == "farmer"
    assert profile["consent_version"] == 3 and profile["consent_at"]
    assert profile["priorities"] is None
    assert "password" not in str(profile).lower()
    assert client.get("/api/v1/me").json()["user_id"] == profile["user_id"]


def test_la_contrasena_se_guarda_solo_como_hash_argon2(client, db):
    register(client)
    user = db.scalar(select(User))
    assert user.password_hash.startswith("$argon2id$")
    assert ROSA["password"] not in user.password_hash


def test_la_cookie_es_httponly_secure_y_samesite_lax(client):
    cookie = register(client).headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie and "max-age=2592000" in cookie


def test_en_la_base_se_guarda_el_hash_del_token_no_el_token(client, db):
    register(client)
    token = client.cookies[SESSION_COOKIE]
    session = db.scalar(select(Session))
    assert session.token_hash == hash_token(token) != token
    assert timedelta(days=29) < session.expires_at - datetime.now(UTC) <= timedelta(days=30)


def test_sin_aceptar_el_consentimiento_no_se_crea_la_cuenta(client, db):
    response = register(client, consent_accepted=False)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "consent_required"
    assert db.scalar(select(User)) is None


def test_una_version_vieja_del_consentimiento_no_sirve(client, db):
    assert register(client, consent_version=2).status_code == 422
    assert db.scalar(select(User)) is None


def test_usuario_repetido_responde_409(client):
    register(client)
    client.cookies.clear()
    response = register(client, display_name="Otra Rosa")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "username_taken"


def test_datos_invalidos_responden_422_sin_repetir_lo_que_llego(client):
    for changes in (
        {"password": "corta"},
        {"username": "Rosa Samacá"},
        {"username": "ro"},
        {"display_name": "   "},
        {"display_name": "x" * 41},
    ):
        response = register(client, **changes)
        assert response.status_code == 422, changes
        assert response.json()["error"]["code"] == "invalid_input"
        assert "corta" not in response.text


# ---------- Entrar y salir ----------


def test_entrar_con_usuario_y_contrasena(client):
    register(client)
    client.cookies.clear()
    assert client.get("/api/v1/me").status_code == 401
    response = client.post("/api/v1/auth/login", json=LOGIN)
    assert response.status_code == 200
    assert response.json()["display_name"] == "Rosa"
    assert client.get("/api/v1/me").status_code == 200


def test_el_usuario_se_puede_escribir_con_mayusculas_y_espacios(client):
    register(client)
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={**LOGIN, "username": "  Rosa.Samaca "}).status_code == 200


def test_contrasena_mala_y_usuario_que_no_existe_responden_igual(client):
    register(client)
    client.cookies.clear()
    wrong = client.post("/api/v1/auth/login", json={**LOGIN, "password": "no-es-esta-clave"})
    unknown = client.post("/api/v1/auth/login", json={"username": "nadie", "password": "no-es-esta-clave"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert SESSION_COOKIE not in client.cookies


def test_tras_5_intentos_fallidos_responde_429_aunque_la_contrasena_sea_buena(client):
    register(client)
    client.cookies.clear()
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={**LOGIN, "password": "no-es-esta-clave"}).status_code == 401
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 429
    # Otro usuario no queda bloqueado por los intentos de este.
    assert client.post("/api/v1/auth/login", json={"username": "otro", "password": "no-es-esta-clave"}).status_code == 401


def test_cuenta_bloqueada_no_entra(client, db):
    register(client)
    client.cookies.clear()
    db.execute(update(User).values(blocked_at=datetime.now(UTC)))
    db.commit()
    response = client.post("/api/v1/auth/login", json=LOGIN)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_blocked"


def test_salir_invalida_la_sesion_en_la_base_de_datos(client, db):
    register(client)
    token = client.cookies[SESSION_COOKIE]
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert db.scalar(select(Session)) is None
    # Aunque alguien haya copiado el token, ya no sirve.
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/v1/me").status_code == 401


def test_una_sesion_vencida_no_sirve(client, db):
    register(client)
    db.execute(update(Session).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()
    assert client.get("/api/v1/me").status_code == 401
    assert db.scalar(select(Session)) is None


def test_sin_sesion_los_endpoints_de_cuenta_responden_401(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.delete("/api/v1/me").status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 401
    client.cookies.set(SESSION_COOKIE, "un-token-inventado")
    assert client.get("/api/v1/me").status_code == 401


# ---------- Borrar la cuenta ----------


def test_borrar_la_cuenta_borra_al_usuario_y_sus_sesiones(client, db):
    register(client)
    client.post("/api/v1/auth/login", json=LOGIN)  # una segunda sesión, como desde otro dispositivo
    assert client.request("DELETE", "/api/v1/me", json={"password": ROSA["password"]}).status_code == 204
    assert db.scalar(select(User)) is None
    assert db.scalar(select(Session)) is None
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 401


# ---------- Protección y errores ----------


def test_una_peticion_que_cambia_datos_desde_otro_sitio_se_rechaza(client):
    response = client.post("/api/v1/auth/register", json=ROSA, headers={"Origin": "https://sitio-malicioso.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert register(client, username="desde.la.web").status_code == 201
    ok = client.post("/api/v1/auth/login", json={**LOGIN, "username": "desde.la.web"}, headers={"Origin": "http://localhost:5173"})
    assert ok.status_code == 200


def test_toda_respuesta_lleva_su_identificador_de_peticion(client):
    given = "0b0e4f6e-58a5-4c0e-9d7a-2f1f3a5b7c9d"
    assert client.get("/api/v1/health", headers={"X-Request-ID": given}).headers["X-Request-ID"] == given
    error = client.get("/api/v1/me", headers={"X-Request-ID": "no-es-un-uuid"})
    request_id = error.headers["X-Request-ID"]
    assert len(request_id) == 36 and request_id != "no-es-un-uuid"
    assert error.json()["error"]["request_id"] == request_id
