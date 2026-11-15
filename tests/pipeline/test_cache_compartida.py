"""Caché de las fuentes compartida (HU-237, parte 1), sin red: GitHub y la descarga se reemplazan por dobles.

Los archivos de las cachés de estas pruebas son DE EJEMPLO (R5): bytes que arma la prueba, no datos de ninguna fuente.
"""

import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

import pytest

from pipeline import build, raw_cache
from pipeline.raw_cache import CacheError
from pipeline.settings import get_settings

TOKEN = "token-de-prueba-123"
LICENCIAS = "| `imerg` · GPM IMERG | NASA | Datos abiertos |\n| `soilgrids` · SoilGrids | ISRIC | CC BY 4.0 |\n"


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    for name in ("AGROSENSE_CACHE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "AGROSENSE_EARTHDATA_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGROSENSE_CACHE_TOKEN", TOKEN)
    monkeypatch.setenv("AGROSENSE_CACHE_REPO", "equipo/ejemplo")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    """Una copia de trabajo de ejemplo: data/raw, el lock y docs/licencias.md en una carpeta temporal."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "licencias.md").write_text(LICENCIAS, encoding="utf-8")
    (tmp_path / "pipeline").mkdir()
    return tmp_path


def _carpeta(base: Path, archivos: dict[str, bytes]) -> Path:
    for nombre, contenido in archivos.items():
        ruta = base / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
    return base


EJEMPLO = {"imerg.meta.json": b'{"ejemplo": true}', "meses/2001-01.csv": b"mes,lluvia\n1,10\n", "meses/2001-02.csv": b"mes,lluvia\n2,20\n"}


class GitHubFalso:
    """Un doble de la API de GitHub: guarda las llamadas, sin red."""

    def __init__(self, release_existe: bool = False, assets: tuple[str, ...] = ()):
        self.release_existe = release_existe
        self.assets = list(assets)
        self.llamadas: list[tuple[str, str, str | None]] = []

    def __call__(self, method, url, token, data, headers):
        self.llamadas.append((method, url, token))
        if method == "GET":
            if not self.release_existe:
                return 404, b"{}"
            return 200, json.dumps({"id": 7, "assets": [{"name": a} for a in self.assets]}).encode()
        if url.endswith("/releases"):
            self.release_existe = True
            return 201, json.dumps({"id": 7, "assets": []}).encode()
        name = url.split("name=")[1]
        self.assets.append(name)
        return 201, b"{}"


# ---------- huella y paquete ----------


def test_la_huella_ignora_las_descargas_a_medias_y_cambia_con_el_contenido(tmp_path):
    a = _carpeta(tmp_path / "a", EJEMPLO)
    antes = raw_cache.tree_digest(a)
    (a / "meses" / "2001-03.csv.part").write_bytes(b"a medias")
    assert raw_cache.tree_digest(a) == antes
    (a / "meses" / "2001-02.csv").write_bytes(b"mes,lluvia\n2,21\n")
    assert raw_cache.tree_digest(a) != antes
    assert raw_cache.tree_digest(tmp_path / "no-existe") is None


def test_el_paquete_es_el_mismo_byte_a_byte_aunque_los_archivos_se_escriban_en_otro_orden(tmp_path):
    a = _carpeta(tmp_path / "a" / "imerg", EJEMPLO)
    b = _carpeta(tmp_path / "b" / "imerg", dict(reversed(list(EJEMPLO.items()))))
    (tmp_path / "out_a").mkdir()
    (tmp_path / "out_b").mkdir()
    pa, huella = raw_cache.pack("imerg", a, tmp_path / "out_a")
    pb, _ = raw_cache.pack("imerg", b, tmp_path / "out_b")
    assert pa.read_bytes() == pb.read_bytes()
    assert pa.name == f"cache-imerg-{huella[:16]}.tar.gz"


# ---------- lo que no se sube ----------


def test_no_se_sube_una_carpeta_fuera_de_la_lista(raiz):
    _carpeta(raiz / "data" / "raw" / "otra", EJEMPLO)
    with pytest.raises(CacheError, match="lista de carpetas"):
        raw_cache.check_shareable("otra", raiz / "data" / "raw" / "otra")


def test_no_se_sube_una_fuente_sin_licencia_documentada(raiz):
    carpeta = _carpeta(raiz / "data" / "raw" / "nasadem", EJEMPLO)
    with pytest.raises(CacheError, match="falta la licencia de nasadem"):
        raw_cache.check_shareable("nasadem", carpeta)


def test_no_se_sube_un_env_ni_un_archivo_con_un_token(raiz):
    carpeta = _carpeta(raiz / "data" / "raw" / "imerg", EJEMPLO)
    raw_cache.check_shareable("imerg", carpeta)  # control: sin secretos pasa
    (carpeta / ".env").write_text("AGROSENSE_EARTHDATA_TOKEN=x", encoding="utf-8")
    with pytest.raises(CacheError, match="configuración"):
        raw_cache.check_shareable("imerg", carpeta)
    (carpeta / ".env").unlink()
    (carpeta / "imerg.meta.json").write_text(f'{{"auth": "{TOKEN}"}}', encoding="utf-8")
    with pytest.raises(CacheError, match="contiene un token") as error:
        raw_cache.check_shareable("imerg", carpeta)
    assert TOKEN not in str(error.value)


# ---------- subir ----------


def test_subir_crea_la_release_sube_y_anota_y_la_segunda_vez_no_vuelve_a_subir(raiz):
    _carpeta(raiz / "data" / "raw" / "imerg", EJEMPLO)
    github = GitHubFalso()
    entrada = raw_cache.push("imerg", request=github)
    metodos = [(m, u.split("/repos/")[1].split("?")[0]) for m, u, _ in github.llamadas]
    assert metodos == [
        ("GET", "equipo/ejemplo/releases/tags/cache-datos"),
        ("POST", "equipo/ejemplo/releases"),
        ("POST", "equipo/ejemplo/releases/7/assets"),
    ]
    assert all(token == TOKEN for _, _, token in github.llamadas)
    lock = json.loads((raiz / "pipeline" / "raw_cache.json").read_text(encoding="utf-8"))
    assert lock["release"] == "cache-datos"
    assert lock["folders"]["imerg"]["asset"] == entrada.asset and lock["folders"]["imerg"]["source_ids"] == ["imerg"]
    assert lock["folders"]["imerg"]["files"] == 3

    github.llamadas.clear()
    otra = raw_cache.push("imerg", request=github)
    assert [m for m, _, _ in github.llamadas] == ["GET"]  # ya estaba: no se sube otra vez
    assert otra == entrada  # ni cambia su entrada (R4)


def test_subir_sin_token_falla_sin_tocar_github(raiz, monkeypatch):
    monkeypatch.delenv("AGROSENSE_CACHE_TOKEN")
    get_settings.cache_clear()
    _carpeta(raiz / "data" / "raw" / "imerg", EJEMPLO)
    github = GitHubFalso()
    with pytest.raises(CacheError, match="token de GitHub"):
        raw_cache.push("imerg", request=github)
    assert github.llamadas == []


def test_un_error_de_github_no_dice_el_token(raiz):
    _carpeta(raiz / "data" / "raw" / "imerg", EJEMPLO)
    with pytest.raises(CacheError) as error:
        raw_cache.push("imerg", request=lambda *a: (500, b"error"))
    assert "500" in str(error.value) and TOKEN not in str(error.value)


# ---------- traer ----------


def _publicada(raiz: Path, nombre: str = "imerg", archivos: dict[str, bytes] = EJEMPLO) -> tuple[Path, raw_cache.Entry]:
    """Empaqueta una carpeta de ejemplo como si ya estuviera en la release, y la anota en el lock."""
    origen = _carpeta(raiz / "origen" / nombre, archivos)
    (raiz / "release").mkdir(exist_ok=True)
    paquete, huella = raw_cache.pack(nombre, origen, raiz / "release")
    entrada = raw_cache.Entry(
        nombre,
        paquete.name,
        raw_cache._sha256_file(paquete),
        huella,
        paquete.stat().st_size,
        len(archivos),
        (nombre,),
        "2026-11-15T00:00:00+00:00",
    )
    raw_cache.save_lock({nombre: entrada})
    return paquete, entrada


def _descarga_desde(paquete: Path):
    llamadas = []

    def bajar(url, dest):
        llamadas.append(url)
        shutil.copy(paquete, dest)
        return dest

    return bajar, llamadas


def test_traer_baja_verifica_y_deja_la_carpeta_y_la_segunda_vez_no_baja_nada(raiz):
    paquete, entrada = _publicada(raiz)
    bajar, llamadas = _descarga_desde(paquete)
    assert raw_cache.pull(download=bajar) == ["imerg"]
    assert llamadas == [f"https://github.com/equipo/ejemplo/releases/download/cache-datos/{entrada.asset}"]
    assert raw_cache.tree_digest(raiz / "data" / "raw" / "imerg") == entrada.tree
    assert (raiz / "data" / "raw" / "imerg" / "meses" / "2001-01.csv").read_bytes() == EJEMPLO["meses/2001-01.csv"]
    assert raw_cache.pull(download=bajar) == []  # al día
    assert len(llamadas) == 1


def test_traer_reemplaza_una_carpeta_distinta(raiz):
    paquete, entrada = _publicada(raiz)
    _carpeta(raiz / "data" / "raw" / "imerg", {"vieja.csv": b"de antes"})
    bajar, _ = _descarga_desde(paquete)
    raw_cache.pull(["imerg"], download=bajar)
    assert not (raiz / "data" / "raw" / "imerg" / "vieja.csv").exists()
    assert raw_cache.tree_digest(raiz / "data" / "raw" / "imerg") == entrada.tree


def test_si_el_sha256_no_coincide_falla_y_la_carpeta_queda_como_estaba(raiz):
    _, entrada = _publicada(raiz)
    otro, _ = _publicada(raiz, archivos={"x.csv": b"otro contenido"})
    raw_cache.save_lock({"imerg": entrada})  # el lock dice un archivo y llega otro
    local = _carpeta(raiz / "data" / "raw" / "imerg", {"vieja.csv": b"de antes"})
    antes = raw_cache.tree_digest(local)
    bajar, _ = _descarga_desde(otro)
    with pytest.raises(CacheError, match="sha256 no coincide"):
        raw_cache.pull(download=bajar)
    assert raw_cache.tree_digest(local) == antes


def test_si_la_descarga_falla_da_un_mensaje_claro_y_la_carpeta_queda_como_estaba(raiz):
    _publicada(raiz)
    local = _carpeta(raiz / "data" / "raw" / "imerg", {"vieja.csv": b"de antes"})
    antes = raw_cache.tree_digest(local)

    def sin_red(url, dest):
        raise OSError("sin conexión")

    with pytest.raises(CacheError, match="no se pudo bajar"):
        raw_cache.pull(download=sin_red)
    assert raw_cache.tree_digest(local) == antes


def test_la_extraccion_rechaza_un_archivo_que_sale_de_la_carpeta(raiz):
    malo = raiz / "malo.tar.gz"
    with tarfile.open(malo, "w:gz") as tar:
        info = tarfile.TarInfo("../fuera.txt")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"mal!"))
    entrada = raw_cache.Entry("imerg", malo.name, raw_cache._sha256_file(malo), "0" * 64, malo.stat().st_size, 1, ("imerg",), "x")
    raw_cache.save_lock({"imerg": entrada})
    bajar, _ = _descarga_desde(malo)
    with pytest.raises(CacheError, match="no se pudo extraer"):
        raw_cache.pull(download=bajar)
    assert not (raiz / "data" / "fuera.txt").exists() and not (raiz / "data" / "raw" / "fuera.txt").exists()


def test_traer_una_carpeta_sin_entrada_falla(raiz):
    _publicada(raiz)
    with pytest.raises(CacheError, match="no tiene entrada"):
        raw_cache.pull(["sipsa"], download=lambda url, dest: dest)


# ---------- estado ----------


def test_estado_al_dia_distinta_falta_y_sin_entrada(raiz):
    _, imerg = _publicada(raiz, "imerg")
    _, soil = _publicada(raiz, "soilgrids", {"a.tif": b"suelo de ejemplo"})
    raw_cache.save_lock({"imerg": imerg, "soilgrids": soil})
    _carpeta(raiz / "data" / "raw" / "imerg", EJEMPLO)
    _carpeta(raiz / "data" / "raw" / "nasadem", {"n.hgt": b"ejemplo"})
    assert raw_cache.status() == {"imerg": "al_dia", "nasadem": "sin_entrada", "soilgrids": "falta"}
    (raiz / "data" / "raw" / "imerg" / "otro.csv").write_bytes(b"x")
    assert raw_cache.status()["imerg"] == "distinta"


# ---------- pipeline.build --traer-cache ----------


def test_build_con_traer_cache_trae_antes_de_publicar(monkeypatch):
    orden = []
    monkeypatch.setattr(raw_cache, "pull", lambda *a, **k: orden.append("traer"))
    monkeypatch.setattr(build, "build", lambda download: orden.append("publicar"))
    monkeypatch.setattr(build, "verify", lambda *a: {"dataset_version": "ejemplo", "tables": {}})
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--traer-cache"])
    build.main()
    assert orden == ["traer", "publicar"]
    orden.clear()
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--traer-cache", "--verificar"])
    build.main()
    assert orden == []  # verificar no trae ni publica
