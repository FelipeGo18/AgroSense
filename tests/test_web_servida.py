"""La API sirve el build de la web en el mismo origen (HU-023), como pide `web/README.md` al alojamiento: archivos,
páginas dibujadas en el build, `app.html` para las demás rutas, 404 para un archivo que no existe, caché larga para
`assets/`, compresión y su propia política de seguridad. Lo que empieza por `/api/` responde igual con la web que sin
ella."""

import gzip

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.api.auth import _client_ip
from backend.api.main import API_CSP, ASSETS_CACHE, HTML_CACHE, WEB_CSP, create_app, install_web
from backend.config.settings import get_settings

APP_JS = "console.log('agrosense');" * 100  # más de 1 kB: se comprime


@pytest.fixture
def build(tmp_path):
    """Un build de la web en `tmp_path/build` y, fuera de él, un archivo que nunca se debe servir."""
    root = tmp_path / "build"
    (root / "entrar").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "index.html").write_text("<p>inicio</p>")
    (root / "app.html").write_text("<p>cascarón</p>")
    (root / "entrar" / "index.html").write_text("<p>entrar</p>")
    (root / "assets" / "app-1a2b.js").write_text(APP_JS)
    (root / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secreto.txt").write_text("no")
    return root


@pytest.fixture
def web(build):
    app = create_app()
    install_web(app, build)
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def plain():
    """La API sin la web, como en las pruebas y en Docker Compose."""
    return TestClient(create_app(), base_url="https://testserver")


def test_sirve_archivos_y_paginas_del_build(web):
    assert web.get("/").text == "<p>inicio</p>"
    assert web.get("/entrar").text == "<p>entrar</p>"
    assert web.get("/entrar/").text == "<p>entrar</p>"
    assert web.get("/assets/app-1a2b.js").text == APP_JS
    assert web.get("/favicon.svg").text == "<svg/>"


def test_las_demas_rutas_reciben_el_cascaron(web):
    for path in ("/mi-finca", "/mi-finca/lote/3", "/estrategias?municipio=15238"):
        response = web.get(path)
        assert response.status_code == 200
        assert response.text == "<p>cascarón</p>"


def test_sin_cascaron_las_rutas_reciben_el_inicio(build):
    (build / "app.html").unlink()
    app = create_app()
    install_web(app, build)
    assert TestClient(app).get("/mi-finca").text == "<p>inicio</p>"


def test_un_archivo_que_no_existe_es_404(web):
    # Una pestaña abierta antes de un despliegue pide un trozo que ya no existe: un 404, nunca el HTML de la app.
    for path in ("/assets/app-viejo.js", "/assets/no-existe", "/logo-viejo.png"):
        response = web.get(path)
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")


def test_head_responde_como_get(web):
    response = web.head("/")
    assert response.status_code == 200
    assert response.content == b""
    assert web.head("/assets/app-1a2b.js").status_code == 200


def test_cache_del_html_y_de_assets(web):
    assert web.get("/").headers["Cache-Control"] == HTML_CACHE
    assert web.get("/mi-finca").headers["Cache-Control"] == HTML_CACHE
    assert web.get("/assets/app-1a2b.js").headers["Cache-Control"] == ASSETS_CACHE
    assert "Cache-Control" not in web.get("/favicon.svg").headers


def test_la_web_va_comprimida_y_la_api_no(web):
    response = web.get("/assets/app-1a2b.js", headers={"Accept-Encoding": "gzip"})
    assert response.headers["Content-Encoding"] == "gzip"
    assert response.text == APP_JS  # el cliente la descomprime
    with web.stream("GET", "/assets/app-1a2b.js", headers={"Accept-Encoding": "gzip"}) as stream:
        assert gzip.decompress(b"".join(stream.iter_raw())) == APP_JS.encode()
    assert "Content-Encoding" not in web.get("/api/v1/version", headers={"Accept-Encoding": "gzip"}).headers


def test_politicas_de_seguridad(web, plain):
    assert web.get("/").headers["Content-Security-Policy"] == WEB_CSP
    assert web.get("/assets/app-viejo.js").headers["Content-Security-Policy"] == WEB_CSP
    assert web.get("/api/v1/version").headers["Content-Security-Policy"] == API_CSP
    # Sin la web, todo lleva la de la API, como antes de HU-023.
    assert plain.get("/no-existe").headers["Content-Security-Policy"] == API_CSP
    assert "script-src 'self';" in WEB_CSP and "'unsafe-inline'" not in WEB_CSP.split("script-src")[1].split(";")[0]


def test_la_politica_deja_cargar_las_capas_de_gibs():
    """HU-211: el mapa del lote pide el catálogo WMTS y las teselas de GIBS con `fetch` (MapLibre) y la leyenda del NDVI
    como imagen. Sin el origen en `connect-src` e `img-src`, el navegador las bloquea y la capa sale «no disponible»."""
    directives = dict(part.strip().split(" ", 1) for part in WEB_CSP.split(";") if part.strip())
    assert "https://gibs.earthdata.nasa.gov" in directives["connect-src"].split()
    assert "https://gibs.earthdata.nasa.gov" in directives["img-src"].split()
    # Ningún comodín: solo se abre ese origen.
    assert "*" not in directives["connect-src"] and "*" not in directives["img-src"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/no-existe"),
        ("POST", "/api/v1/no-existe"),
        ("DELETE", "/api/v1/no-existe"),
        ("GET", "/api"),
        ("POST", "/api/v1/version"),  # existe, pero solo con GET
        ("GET", "/api/v1/version/"),  # la barra final redirige
    ],
)
def test_la_api_responde_igual_con_la_web_que_sin_ella(web, plain, method, path):
    with_web = web.request(method, path, follow_redirects=False)
    without = plain.request(method, path, follow_redirects=False)
    assert with_web.status_code == without.status_code
    assert with_web.headers.get("content-type") == without.headers.get("content-type")
    assert with_web.headers.get("location") == without.headers.get("location")
    assert "cascarón" not in with_web.text


def test_nada_fuera_de_la_carpeta_del_build(web):
    # httpx normaliza `/../` antes de enviar; con los puntos codificados la ruta llega al servidor con `..`.
    assert web.build_request("GET", "/%2e%2e/secreto.txt").url.raw_path == b"/%2e%2e/secreto.txt"
    for path in ("/%2e%2e/secreto.txt", "/assets/%2e%2e/%2e%2e/secreto.txt"):
        assert web.get(path).status_code == 404


def test_sin_index_no_arranca(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        install_web(create_app(), tmp_path)


def _request(headers: dict[str, str]) -> Request:
    raw = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "client": ("10.0.0.7", 1234)})


@pytest.fixture
def behind_proxy(monkeypatch):
    monkeypatch.setenv("AGROSENSE_BEHIND_PROXY", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_detras_del_proxy_la_ip_es_la_que_agrega_google(behind_proxy):
    # Quien llama puede escribir lo que quiera al principio; la última la agrega el frente de Google.
    assert _client_ip(_request({"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
    assert _client_ip(_request({"X-Forwarded-For": "203.0.113.9"})) == "203.0.113.9"
    assert _client_ip(_request({})) == "10.0.0.7"


def test_sin_proxy_la_ip_es_la_de_la_conexion():
    get_settings.cache_clear()
    assert _client_ip(_request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.7"
