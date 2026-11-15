"""La API sirve el build de la web en el mismo origen (HU-023): archivos, páginas con HTML del build y el resto con
`index.html`. Lo que empieza por `/api/` sigue siendo de la API."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app, install_web


@pytest.fixture
def web(tmp_path):
    (tmp_path / "index.html").write_text("<p>inicio</p>")
    (tmp_path / "entrar").mkdir()
    (tmp_path / "entrar" / "index.html").write_text("<p>entrar</p>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secreto.txt").write_text("no")
    app = create_app()
    install_web(app, tmp_path)
    return TestClient(app, base_url="https://testserver")


def test_sirve_archivos_paginas_y_el_resto_con_index(web):
    assert web.get("/").text == "<p>inicio</p>"
    assert web.get("/entrar").text == "<p>entrar</p>"
    assert web.get("/assets/app.js").text == "console.log(1)"
    # Una ruta de React Router sin HTML propio: `index.html`.
    assert web.get("/mi-finca/lote/3").text == "<p>inicio</p>"


def test_la_api_no_cae_en_la_web(web):
    assert web.get("/api/v1/version").status_code == 200
    missing = web.get("/api/v1/no-existe")
    assert missing.status_code == 404 and missing.headers["content-type"].startswith("application/json")
    # La web no lleva la política de las respuestas JSON; la API sí.
    assert "Content-Security-Policy" not in web.get("/").headers
    assert web.get("/api/v1/version").headers["Content-Security-Policy"].startswith("default-src 'none'")


def test_nada_fuera_de_la_carpeta_del_build(web):
    assert web.get("/../secreto.txt").text != "no"
    assert web.get("/%2e%2e/secreto.txt").text != "no"


def test_sin_index_no_arranca(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        install_web(create_app(), tmp_path)
