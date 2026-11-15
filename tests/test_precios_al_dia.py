"""Precios de SIPSA al día (HU-222): las dos actualizaciones (boletín diario y servicio semanal), sus versiones y la API,
que solo las lee.

Ninguna prueba usa la red: las «descargas» escriben un anexo o una respuesta del servicio de ejemplo (R5).
"""

import http.client
import io
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

import polars as pl
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from backend.api.main import app
from backend.config.settings import get_settings
from backend.market import store, updates
from backend.market.updates import BOGOTA, UpdateError
from pipeline.build import publish
from pipeline.sources import dane, fetch, sipsa, sipsa_boletin
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, SAMPLE_SIPSA_ROWS, sipsa_row, sipsa_xml

REGION = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}
# Los precios publicados de ejemplo llegan hasta el lunes 19 de octubre de 2026.
THURSDAY_3PM = datetime(2026, 10, 22, 15, 0, tzinfo=BOGOTA)
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def bulletin(day: date, products: dict[str, tuple], columns=("Barranquilla", "Bogotá, Corabastos", "Tunja"), header="Precio $/Kg") -> bytes:
    """Un anexo de ejemplo (R5) con la forma del boletín diario del DANE: el día arriba, una fila de centrales con dos
    columnas cada una (precio y variación) y los productos por grupo. `products`: nombre → precio en cada central."""
    book = Workbook()
    sheet = book.active
    sheet.title = "Boletín diario"
    sheet.append([None])
    sheet.append([f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"])
    row = [header]
    for name in columns:
        row += [name, None]
    sheet.append(row)
    sheet.append([None] + ["Precio", "Var %"] * len(columns))
    sheet.append(["Tubérculos, raíces y plátanos"])
    for name, prices in products.items():
        row = [name]
        for price in prices:
            row += [price, 0.01]
        sheet.append(row)
    sheet.append(["*Variedad predominante en el mercado"])
    sheet.append(["n.d. : no disponible"])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def bulletins(by_day: dict[date, bytes]):
    """Una descarga del boletín de ejemplo: el anexo de ese día, o nada si ese día no hubo boletín (como un 404)."""
    asked = []

    def download(day, folder):
        asked.append(day)
        if day not in by_day:
            return None
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"boletin-{day:%Y%m%d}.xlsx"
        path.write_bytes(by_day[day])
        return path

    download.asked = asked
    return download


def service(rows):
    """Una descarga del servicio de ejemplo: escribe la respuesta donde la escribiría `sipsa.download`."""

    def download(cache):
        cache.mkdir(parents=True, exist_ok=True)
        (cache / sipsa.ROWS_FILE).write_text(sipsa_xml(rows), encoding="utf-8")
        (cache / sipsa.META_FILE).write_text("2026-10-25T20:00:00+00:00", encoding="utf-8")
        return cache / sipsa.ROWS_FILE

    return download


@pytest.fixture
def published(tmp_path, monkeypatch):
    """El dataset publicado de ejemplo, con sus precios hasta el 19 de octubre y las centrales en la región."""
    folder = tmp_path / "published"
    prices = sipsa.prices(io.BytesIO(sipsa_xml(SAMPLE_SIPSA_ROWS).encode()), SAMPLE_MARKETS)
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    publish(REGION, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, folder, prices=prices)
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()
    return folder


@pytest.fixture
def market(tmp_path, monkeypatch):
    folder = tmp_path / "market"
    monkeypatch.setenv("AGROSENSE_MARKET_DIR", str(folder))
    get_settings.cache_clear()
    return folder


PAPA = {"Papa negra*": (2400, 3010, 2700)}


# ---------- Boletín diario ----------


def test_el_boletin_suma_los_dias_habiles_que_faltan_sin_minimo_ni_maximo(published, market):
    download = bulletins({date(2026, 10, 20): bulletin(date(2026, 10, 20), PAPA), date(2026, 10, 22): bulletin(date(2026, 10, 22), PAPA)})
    data = updates.daily(market, published, now=THURSDAY_3PM, download=download)
    # Del martes 20 al jueves 22; el miércoles no hubo boletín (festivo, por ejemplo).
    assert download.asked == [date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22)]
    new = data.prices.filter(pl.col("source_id") == sipsa_boletin.SOURCE_ID).sort("market_id", "date")
    assert new.select("market_id", "date", "avg_cop_kg").rows() == [
        ("1", date(2026, 10, 20), 3010),
        ("1", date(2026, 10, 22), 3010),
        ("9", date(2026, 10, 20), 2700),
        ("9", date(2026, 10, 22), 2700),
    ]
    assert new["min_cop_kg"].null_count() == new["max_cop_kg"].null_count() == new.height
    assert data.version.endswith("-boletin") and json.loads((market / store.CURRENT).read_text())["version"] == data.version


def test_cada_fila_dice_de_donde_salio_y_las_dos_fuentes_quedan_citadas(published, market):
    data = updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), PAPA)}))
    assert set(data.prices["source_id"].unique().to_list()) == {sipsa.SOURCE_ID, sipsa_boletin.SOURCE_ID}
    cited = {row["source_id"]: row for row in data.sources}
    assert set(cited) == {sipsa.SOURCE_ID, sipsa_boletin.SOURCE_ID}
    assert cited[sipsa_boletin.SOURCE_ID]["period_covered"] == "Del 2026-10-22 al 2026-10-22"


def test_un_producto_conocido_conserva_su_nombre_aunque_el_boletin_lo_escriba_distinto(published, market):
    data = updates.daily(
        market,
        published,
        now=THURSDAY_3PM,
        download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), {"Papa Negra *": (1, 3010, 2700)})}),
    )
    names = data.prices.filter(pl.col("product_id") == "papa-negra")["product"].unique().to_list()
    assert names == ["Papa negra"]


def test_n_d_no_es_precio(published, market):
    data = updates.daily(
        market,
        published,
        now=THURSDAY_3PM,
        download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), {"Arracacha*": (1, "n.d.", 1800)})}),
    )
    new = data.prices.filter(pl.col("product_id") == "arracacha")
    assert new.select("market_id", "avg_cop_kg", "group", "several_varieties").rows() == [
        ("9", 1800, "Tubérculos, raíces y plátanos", True)
    ]


def test_sin_dias_nuevos_no_escribe_nada(published, market):
    assert updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({})) is None
    assert not (market / store.CURRENT).exists()


def test_un_fin_de_semana_no_se_pide_boletin(published, market):
    sunday = datetime(2026, 10, 25, 15, 0, tzinfo=BOGOTA)
    download = bulletins({})
    updates.daily(market, published, now=sunday, download=download)
    assert all(day.weekday() < 5 for day in download.asked) and date(2026, 10, 24) not in download.asked


def test_un_anexo_de_otro_dia_no_cambia_lo_que_se_sirve(published, market):
    with pytest.raises(UpdateError, match="dice ser del 2026-10-21"):
        updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 21), PAPA)}))
    assert not (market / store.CURRENT).exists() and not (market / "raw").exists()


def test_un_anexo_sin_su_fila_de_centrales_no_se_lee(published, market):
    """Si el DANE cambia el formato, falla en vez de leer mal (R1)."""
    broken = bulletin(date(2026, 10, 22), PAPA, header="Precios en $/Kg")
    with pytest.raises(UpdateError):
        updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): broken}))
    assert not (market / store.CURRENT).exists()


def test_una_central_que_no_reporto_ese_dia_no_tiene_precios_y_no_es_un_error(published, market):
    """Cada boletín trae solo las centrales que reportaron ese día: Tunja sale unos tres días por semana."""
    day = date(2026, 10, 22)
    data = updates.daily(
        market, published, now=THURSDAY_3PM, download=bulletins({day: bulletin(day, PAPA, columns=("Barranquilla", "Bogotá, Corabastos"))})
    )
    new = data.prices.filter(pl.col("source_id") == sipsa_boletin.SOURCE_ID)
    assert new.select("market_id", "date", "avg_cop_kg").rows() == [("1", day, 3010)]


def test_la_direccion_del_anexo_lleva_el_dia_y_el_mes_como_los_escribe_el_dane():
    assert sipsa_boletin.url(date(2026, 9, 15)).endswith("/anex-SIPSADiario-15sep2026.xlsx")
    assert sipsa_boletin.url(date(2026, 11, 6)).endswith("/anex-SIPSADiario-06nov2026.xlsx")


def test_un_404_del_dane_es_un_dia_sin_boletin(tmp_path, monkeypatch):
    def not_found(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", not_found)
    assert sipsa_boletin.download(date(2026, 11, 2), tmp_path) is None


# ---------- Servicio semanal ----------


def test_el_servicio_reemplaza_los_dias_del_boletin_y_conserva_los_posteriores(published, market):
    updates.daily(
        market,
        published,
        now=THURSDAY_3PM,
        download=bulletins({day: bulletin(day, PAPA) for day in (date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22))}),
    )
    # El servicio llega hasta el miércoles 21 en Corabastos y hasta el martes 20 en Tunja.
    rows = [
        *SAMPLE_SIPSA_ROWS,
        sipsa_row("1", "Papa negra*", "2026-10-21", 2900, 3000, 3100),
        sipsa_row("9", "Papa negra*", "2026-10-20", 2600, 2650, 2700),
    ]
    data = updates.weekly(market, published, now=THURSDAY_3PM + timedelta(days=3), download=service(rows), pause=0)
    papa = data.prices.filter(pl.col("product_id") == "papa-negra").sort("market_id", "date")
    after = papa.filter(pl.col("date") >= date(2026, 10, 20)).select("market_id", "date", "avg_cop_kg", "source_id").rows()
    assert after == [
        ("1", date(2026, 10, 21), 3000, sipsa.SOURCE_ID),
        ("1", date(2026, 10, 22), 3010, sipsa_boletin.SOURCE_ID),
        ("9", date(2026, 10, 20), 2650, sipsa.SOURCE_ID),
        ("9", date(2026, 10, 21), 2700, sipsa_boletin.SOURCE_ID),
        ("9", date(2026, 10, 22), 2700, sipsa_boletin.SOURCE_ID),
    ]
    assert data.version.endswith("-servicio") and {row["source_id"] for row in data.sources} == {sipsa.SOURCE_ID, sipsa_boletin.SOURCE_ID}
    assert not (market / "raw").exists()


def test_una_descarga_cortada_se_reintenta(published, market):
    calls = []

    def flaky(cache):
        calls.append(1)
        if len(calls) < 3:
            raise fetch.DownloadError("la descarga pasó de 900 s")
        return service(SAMPLE_SIPSA_ROWS)(cache)

    updates.weekly(market, published, now=THURSDAY_3PM, download=flaky, pause=0)
    assert len(calls) == 3


def test_tres_fallos_no_cambian_lo_que_se_sirve(published, market):
    updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), PAPA)}))
    before = json.loads((market / store.CURRENT).read_text())

    def failing(cache):
        raise OSError("el DANE no respondió")

    with pytest.raises(UpdateError, match="falló 3 veces"):
        updates.weekly(market, published, now=THURSDAY_3PM, download=failing, pause=0)
    assert json.loads((market / store.CURRENT).read_text()) == before and not (market / "raw").exists()


def test_dos_actualizaciones_a_la_vez_no_se_pisan(published, market):
    market.mkdir()
    (market / ".lock").write_text("")
    with pytest.raises(UpdateError, match="otra actualización"):
        updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({}))


def test_el_comando_sin_dataset_publicado_termina_con_error(market, monkeypatch, tmp_path):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(tmp_path / "nada"))
    get_settings.cache_clear()
    with pytest.raises(SystemExit) as exit_info:
        updates.main(["diario"])
    assert exit_info.value.code == 1


# ---------- Versiones ----------


def test_se_guardan_solo_las_dos_ultimas_versiones(published, market):
    for days in range(3):
        updates.weekly(market, published, now=THURSDAY_3PM + timedelta(days=days), download=service(SAMPLE_SIPSA_ROWS), pause=0)
    assert len([p for p in market.glob("sipsa-*") if p.is_dir()]) == store.KEEP


def test_la_api_mira_si_hay_version_nueva_como_mucho_cada_minuto(published, market):
    served = store.Served()
    assert served.get(market, now=0) is None
    data = updates.weekly(market, published, now=THURSDAY_3PM, download=service(SAMPLE_SIPSA_ROWS), pause=0)
    assert served.get(market, now=30) is None
    assert served.get(market, now=61).version == data.version


# ---------- La API ----------


def test_la_api_sirve_la_ultima_version_con_su_fuente_y_la_cita(published, market):
    data = updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), PAPA)}))
    body = TestClient(app).get("/api/v1/market/prices").json()
    assert (body["version"], body["date"], body["source_id"]) == (data.version, "2026-10-22", sipsa_boletin.SOURCE_ID)
    assert body["citation"] == sipsa.CITATION and body["updated_at"].startswith("2026-10-22T15:00")
    papa = next(p for p in body["products"] if p["product_id"] == "papa-negra")
    assert papa["latest"] == {"date": "2026-10-22", "min_cop_kg": None, "avg_cop_kg": 3010, "max_cop_kg": None}


def test_la_temporada_sale_siempre_del_dataset_publicado(published, market):
    updates.daily(market, published, now=THURSDAY_3PM, download=bulletins({date(2026, 10, 22): bulletin(date(2026, 10, 22), PAPA)}))
    body = TestClient(app).get("/api/v1/market/prices/papa-negra").json()
    assert body["citation"] == sipsa.CITATION and body["source_id"] == sipsa_boletin.SOURCE_ID
    # Los precios de ejemplo no tienen 3 años completos: sin temporada, no se inventa (R1).
    assert body["season"] is None


def test_una_version_mas_vieja_que_la_publicada_no_se_sirve(published, market):
    old = sipsa.prices(io.BytesIO(sipsa_xml(SAMPLE_SIPSA_ROWS[:1]).encode()), SAMPLE_MARKETS)
    store.write_version(market, "servicio", old, sipsa.latest(old), [], THURSDAY_3PM)
    body = TestClient(app).get("/api/v1/market/prices").json()
    assert body["version"] == REGION["dataset_version"] and body["updated_at"] is None


# ---------- Descargas ----------


class CutResponse(io.BytesIO):
    """Una respuesta que el servidor corta a mitad, como hace a veces el DANE con los 300 MB."""

    def read(self, size=-1):
        raise http.client.IncompleteRead(b"x" * 10, 100)


def test_un_corte_a_mitad_de_la_respuesta_es_un_error_de_red_y_no_deja_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda request, timeout: CutResponse())
    with pytest.raises(OSError, match="se cortó a mitad"):
        fetch.fetch(urllib.request.Request("https://example.org"), tmp_path / "x.xml", 10, 2**20)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("size", "seconds", "message"), [(4096, 0, "pasó de 0 MB"), (10, -1, "pasó de -1 s")])
def test_una_descarga_corta_por_tamano_o_por_tiempo_total(tmp_path, monkeypatch, size, seconds, message):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(b"x" * size))
    with pytest.raises(fetch.DownloadError, match=message):
        fetch.fetch(urllib.request.Request("https://example.org"), tmp_path / "x.xml", seconds, 1024)
    assert list(tmp_path.iterdir()) == []
