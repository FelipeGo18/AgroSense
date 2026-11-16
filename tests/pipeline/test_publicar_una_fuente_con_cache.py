"""`pipeline.build --solo ndvi|oferta|precios` (HU-238, parte 1): las fuentes que leen su caché de `data/raw/` y no
comparten tablas con otra. Sin red, con las cachés de ejemplo (R5), rotuladas así. Datos inventados.

Cada prueba construye el dataset completo con la caché `a`, apunta las cachés de los adaptadores a la `b` (las tres con un
valor distinto) y corre `--solo <fuente>`: solo deben cambiar las tablas de esa fuente.
"""

import json
import sys

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane_mgn, eva, modis_ndvi, sipsa
from tests.conftest import SAMPLE_SIPSA_ROWS, sipsa_row, sipsa_xml
from tests.pipeline.test_altitud import places_cache
from tests.pipeline.test_oferta_eva import row as eva_row
from tests.pipeline.test_oferta_eva import write_cache as write_eva
from tests.pipeline.test_publicar_una_fuente import (
    VERSION_NUEVA,
    manifiesto,
    sha_de_tablas,
    sha_de_todo,
)
from tests.pipeline.test_reconstruir import REGION, caches  # noqa: F401  (`caches` es un fixture)
from tests.pipeline.test_verdor import REGION_NDVI
from tests.pipeline.test_verdor import write_cache as write_ndvi

FUENTES = ("ndvi", "oferta", "precios")
CARPETA = {"ndvi": "modis_ndvi", "oferta": "eva", "precios": "sipsa"}
# Las tablas que reconstruye cada fuente (más `sources`, que siempre puede cambiar).
TABLAS = {
    "ndvi": {"ndvi_municipality", "ndvi_municipality_normal"},
    "oferta": {"supply_semester"},
    "precios": {"market_price_day", "market_price_latest", "market_price_season", "market_month"},
}
# La tabla que sí o sí cambia con el valor distinto de la caché `b`.
PRINCIPAL = {"ndvi": "ndvi_municipality", "oferta": "supply_semester", "precios": "market_price_day"}
COMPUESTOS = [(year, day) for year in (2023, 2024, 2025) for day in (1, 17)]


def region_con_verdor(version=None):
    region = {**REGION, "ndvi": REGION_NDVI}
    return {**region, "dataset_version": version} if version else region


class Mundo:
    """Las cachés de ejemplo en dos variantes: `a` (con la que se publica) y `b` (un valor distinto en cada fuente)."""

    def __init__(self, tmp_path, dane_cache, monkeypatch):
        self.tmp_path, self.dane_cache, self.monkeypatch = tmp_path, dane_cache, monkeypatch
        features, _ = dane_mgn.read_cache(REGION["region"]["departments"], dane_cache)
        self.area = modis_ndvi.window(dane_mgn.boundaries(features), 1)
        self.caches_de_ejemplo = {tag: self._escribir(tag) for tag in "ab"}

    def _escribir(self, tag):
        raiz = self.tmp_path / f"cache-{tag}"
        valor_ndvi, produccion, precio = (5000, "180", 2925) if tag == "a" else (6000, "200", 2999)
        sipsa_dir = raiz / "sipsa"
        sipsa_dir.mkdir(parents=True)
        filas = [*SAMPLE_SIPSA_ROWS[:2], sipsa_row("1", "Papa negra*", "2026-10-19", 2800, precio, 3000), *SAMPLE_SIPSA_ROWS[3:]]
        (sipsa_dir / sipsa.ROWS_FILE).write_text(sipsa_xml(filas), encoding="utf-8")
        (sipsa_dir / sipsa.META_FILE).write_text("2026-10-20T15:34:00+00:00", encoding="utf-8")
        write_eva(raiz / "eva", [eva_row(period="2024A", production=produccion), eva_row(town="25899", code="1010402", period="2025B")])
        write_ndvi(raiz / "modis_ndvi", self.area, COMPUESTOS, ndvi=lambda row, col: valor_ndvi)
        return {"ndvi": raiz / "modis_ndvi", "oferta": raiz / "eva", "precios": sipsa_dir}

    def construir(self, destino, caches_por_fuente, version=None):
        self.monkeypatch.setattr(build, "load_region", lambda: region_con_verdor(version))
        build.build(
            folder=destino,
            cache=self.dane_cache,
            market_cache=caches_por_fuente["precios"],
            power_cache=self.tmp_path / "sin-clima",
            supply_cache=caches_por_fuente["oferta"],
            ndvi_cache=caches_por_fuente["ndvi"],
        )
        return destino

    def apuntar_a(self, tag):
        """Las cachés por defecto de los adaptadores, las de la variante `tag`: lo que lee `--solo` sin `cache=`."""
        for modulo, fuente in ((modis_ndvi, "ndvi"), (eva, "oferta"), (sipsa, "precios")):
            self.monkeypatch.setattr(modulo, "CACHE", self.caches_de_ejemplo[tag][fuente])


@pytest.fixture
def mundo(tmp_path, caches, monkeypatch):  # noqa: F811
    return Mundo(tmp_path, places_cache(tmp_path / "raw-lugares"), monkeypatch)


@pytest.fixture
def publicado_a(mundo):
    folder = mundo.construir(mundo.tmp_path / "publicado", mundo.caches_de_ejemplo["a"])
    mundo.apuntar_a("b")
    mundo.monkeypatch.setattr(build, "load_region", lambda: region_con_verdor(VERSION_NUEVA))
    return folder


def test_la_construccion_de_ejemplo_trae_las_tablas_de_las_tres_fuentes(mundo, publicado_a):
    tablas = set(manifiesto(publicado_a)["tables"])
    assert set().union(*TABLAS.values()) <= tablas


@pytest.mark.parametrize("fuente", FUENTES)
def test_solo_cambia_las_tablas_de_su_fuente_sus_sources_y_el_manifiesto(publicado_a, fuente):
    antes_tablas, antes = sha_de_tablas(publicado_a), manifiesto(publicado_a)

    build.publish_one(fuente, published=publicado_a)

    despues_tablas, despues = sha_de_tablas(publicado_a), manifiesto(publicado_a)
    cambiaron = {nombre.removesuffix(".parquet") for nombre in despues_tablas if despues_tablas[nombre] != antes_tablas[nombre]}
    assert PRINCIPAL[fuente] in cambiaron
    assert cambiaron <= TABLAS[fuente] | {"sources"}, cambiaron
    # El resto, byte a byte; y las entradas del manifiesto de lo que no cambió, iguales.
    assert {n: h for n, h in despues_tablas.items() if n.removesuffix(".parquet") not in cambiaron} == {
        n: h for n, h in antes_tablas.items() if n.removesuffix(".parquet") not in cambiaron
    }
    for nombre in antes["tables"]:
        if nombre not in cambiaron:
            assert despues["tables"][nombre] == antes["tables"][nombre], nombre
    assert despues["dataset_version"] == VERSION_NUEVA and despues["rules_version"] == antes["rules_version"]
    build.verify(publicado_a, VERSION_NUEVA)


@pytest.mark.parametrize("fuente", FUENTES)
def test_la_fuente_de_sources_se_reemplaza_y_las_demas_se_conservan(publicado_a, fuente):
    antes = {r["source_id"]: r for r in pl.read_parquet(publicado_a / "sources.parquet").to_dicts()}

    build.publish_one(fuente, published=publicado_a)

    despues = {r["source_id"]: r for r in pl.read_parquet(publicado_a / "sources.parquet").to_dicts()}
    propias = {"ndvi": {"modis_ndvi"}, "oferta": {"eva"}, "precios": {"dane_sipsa"}}[fuente]
    assert set(despues) == set(antes)  # ninguna se pierde ni se duplica
    assert {k: v for k, v in despues.items() if k not in propias} == {k: v for k, v in antes.items() if k not in propias}


@pytest.mark.parametrize("fuente", FUENTES)
def test_solo_da_lo_mismo_que_la_construccion_completa(mundo, publicado_a, fuente):
    """Lo publicado sale de un solo camino (R4): `--solo` y `build()` con las mismas cachés dan las mismas tablas."""
    mixto = {otra: mundo.caches_de_ejemplo["a"][otra] for otra in FUENTES} | {fuente: mundo.caches_de_ejemplo["b"][fuente]}
    completo = mundo.construir(mundo.tmp_path / "completo", mixto, VERSION_NUEVA)

    build.publish_one(fuente, published=publicado_a)

    assert sha_de_tablas(publicado_a) == sha_de_tablas(completo)
    assert manifiesto(publicado_a)["tables"] == manifiesto(completo)["tables"]
    for campo in ("dataset_version", "rules_version", "periods", "region"):
        assert manifiesto(publicado_a)[campo] == manifiesto(completo)[campo], campo


@pytest.mark.parametrize("fuente", FUENTES)
def test_sin_cambios_no_escribe_y_con_la_misma_version_y_cambios_falla(mundo, publicado_a, fuente):
    mundo.apuntar_a("a")  # la misma caché con la que se publicó
    antes = sha_de_todo(publicado_a)
    build.publish_one(fuente, published=publicado_a)
    assert sha_de_todo(publicado_a) == antes

    mundo.apuntar_a("b")
    mundo.monkeypatch.setattr(build, "load_region", lambda: region_con_verdor())  # la versión ya publicada
    with pytest.raises(build.ValidationError, match="dataset_version"):
        build.publish_one(fuente, published=publicado_a)
    assert sha_de_todo(publicado_a) == antes


@pytest.mark.parametrize("fuente", FUENTES)
@pytest.mark.parametrize("estado", ["no_existe", "vacia"])
def test_sin_la_carpeta_de_su_fuente_en_raw_falla_con_el_mensaje_y_no_escribe(mundo, publicado_a, fuente, estado):
    carpeta = mundo.tmp_path / "raw-sin-esta-fuente"
    if estado == "vacia":
        carpeta.mkdir()
    antes = sha_de_todo(publicado_a)

    with pytest.raises(build.ValidationError) as error:
        build.publish_one(fuente, published=publicado_a, cache=carpeta)

    mensaje = str(error.value)
    assert CARPETA[fuente] in mensaje and f"raw_cache traer {CARPETA[fuente]}" in mensaje and "--descargar" in mensaje
    assert sha_de_todo(publicado_a) == antes  # ni a medias, ni borra la tabla publicada (R1)
    assert PRINCIPAL[fuente] in manifiesto(publicado_a)["tables"]


@pytest.mark.parametrize("fuente", FUENTES)
def test_nunca_usa_la_red(mundo, publicado_a, fuente, monkeypatch):
    def sin_red(*_args, **_kwargs):
        raise AssertionError("`--solo` no debe usar la red")

    for modulo in (eva, modis_ndvi, sipsa):
        if hasattr(modulo, "download"):
            monkeypatch.setattr(modulo, "download", sin_red)
    monkeypatch.setattr(eva.urllib.request, "urlopen", sin_red)

    build.publish_one(fuente, published=publicado_a)


def test_por_la_linea_de_comandos_solo_oferta_sin_su_carpeta_sale_con_error_y_no_escribe(mundo, publicado_a, monkeypatch):
    from structlog.testing import capture_logs

    monkeypatch.setattr(eva, "CACHE", mundo.tmp_path / "no-hay-eva")
    monkeypatch.setattr(build, "PUBLISHED", publicado_a)
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--solo", "oferta"])
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    antes = sha_de_todo(publicado_a)

    with capture_logs() as logs, pytest.raises(SystemExit) as salida:
        build.main()

    assert salida.value.code not in (0, None)
    assert "raw_cache traer eva" in " ".join(line.get("detail", "") for line in logs)
    assert sha_de_todo(publicado_a) == antes


def test_por_la_linea_de_comandos_solo_precios_publica_y_revisa(mundo, publicado_a, monkeypatch):
    monkeypatch.setattr(build, "PUBLISHED", publicado_a)
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--solo", "precios"])
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    build.main()
    assert manifiesto(publicado_a)["dataset_version"] == VERSION_NUEVA
    assert json.loads((publicado_a / "manifest.json").read_text(encoding="utf-8"))["tables"]["market_price_day"]["rows"] > 0


@pytest.mark.parametrize("fuente", FUENTES)
def test_con_la_region_cambiada_solo_falla_y_no_escribe(mundo, publicado_a, fuente):
    """El `region.yaml` actual difiere del publicado (R4): `--solo` pide la construcción completa, aunque la caché cambie."""
    region = region_con_verdor(VERSION_NUEVA)
    cambiada = {**region, "region": {**region["region"], "name": "otra región"}}
    mundo.monkeypatch.setattr(build, "load_region", lambda: cambiada)
    antes = sha_de_todo(publicado_a)

    with pytest.raises(build.ValidationError, match="region"):
        build.publish_one(fuente, published=publicado_a)

    assert sha_de_todo(publicado_a) == antes
