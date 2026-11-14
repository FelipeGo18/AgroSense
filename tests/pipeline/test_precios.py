"""Precios mayoristas de SIPSA del DANE (HU-221): lectura, temporada y publicación (R1, R4, R8)."""

import io
import json
from datetime import date

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, SAMPLE_SIPSA_ROWS, sipsa_row, sipsa_xml


def read(rows: list[str], markets: dict[str, str] = SAMPLE_MARKETS) -> pl.DataFrame:
    return sipsa.prices(io.BytesIO(sipsa_xml(rows).encode()), markets)


@pytest.mark.parametrize(
    ("name", "key"),
    [("Papa negra", "papa-negra"), ("Fríjol verde", "frijol-verde"), ("Limón Tahití", "limon-tahiti"), ("Piña", "pina")],
)
def test_la_llave_del_producto_es_estable_y_sin_tildes(name, key):
    assert sipsa.product_id(name) == key


def test_solo_entran_las_centrales_de_la_region_ordenadas_por_su_llave():
    table = read(SAMPLE_SIPSA_ROWS)
    assert sorted(set(table["market_id"].to_list())) == ["1", "9"]
    keys = table.select("product_id", "market_id", "date").rows()
    assert keys == sorted(keys)


def test_el_asterisco_del_dane_dice_que_junta_variedades():
    papa = read(SAMPLE_SIPSA_ROWS).filter(pl.col("product_id") == "papa-negra").row(0, named=True)
    assert (papa["product"], papa["several_varieties"], papa["group"]) == ("Papa negra", True, "Tubérculos, raíces y plátanos")
    assert papa["market"] == "Corabastos (Bogotá)" and papa["source_id"] == "dane_sipsa"
    # Sin municipio: Corabastos está en Bogotá, que no es de la región, y toda columna `municipality_id` publicada se une
    # con `municipalities` (R7).
    assert "municipality_id" not in papa


def test_los_precios_van_en_pesos_enteros_y_un_cero_es_sin_dato():
    criolla = read(SAMPLE_SIPSA_ROWS).filter(pl.col("product_id") == "papa-criolla").row(0, named=True)
    assert (criolla["min_cop_kg"], criolla["avg_cop_kg"], criolla["max_cop_kg"]) == (None, 4972, 5111)


def test_un_dia_sin_precio_medio_no_se_publica():
    zanahoria = read(SAMPLE_SIPSA_ROWS).filter(pl.col("product_id") == "zanahoria")
    assert zanahoria["date"].to_list() == [date(2026, 10, 17)]


def monthly(years: range, price) -> list[str]:
    """Un precio por mes en cada año, con `price(año, mes)`."""
    return [sipsa_row("1", "Papa negra*", f"{y}-{m:02d}-15", price(y, m), price(y, m), price(y, m)) for y in years for m in range(1, 13)]


def test_la_temporada_compara_cada_mes_con_su_propio_ano():
    # Octubre siempre a la mitad que el resto del año, y cada año al doble que el anterior (inflación): el índice no la ve.
    rows = monthly(range(2021, 2024), lambda y, m: (2 ** (y - 2021)) * (500 if m == 10 else 1000))
    season = sipsa.seasonal(read(rows))
    year_mean = (11 * 1000 + 500) / 12
    october, march = (season.filter(pl.col("month") == m)["seasonal_index"][0] for m in (10, 3))
    assert october == pytest.approx(500 / year_mean, abs=0.001)
    assert march == pytest.approx(1000 / year_mean, abs=0.001)
    first = season.row(0, named=True)
    assert (first["years"], first["first_year"], first["last_year"], first["source_id"]) == (3, 2021, 2023, "dane_sipsa")
    assert season.height == 12


def test_sin_anos_completos_suficientes_no_hay_temporada():
    # Dos años completos y uno al que le falta diciembre: no alcanza.
    rows = monthly(range(2021, 2023), lambda y, m: 1000) + monthly(range(2023, 2024), lambda y, m: 1000)[:-1]
    assert sipsa.seasonal(read(rows)).is_empty()


def publish(folder, prices):
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    return build.publish(SAMPLE_REGION, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, folder, prices=prices)


def test_publica_los_precios_su_temporada_y_su_fuente(tmp_path):
    manifest = publish(tmp_path, read(SAMPLE_SIPSA_ROWS))
    assert {"market_price_day.parquet", "market_price_season.parquet"} <= {path.name for path in tmp_path.iterdir()}
    assert manifest["tables"]["market_price_day"]["rows"] == 7
    assert "del 2026-10-05 al 2026-10-19" in manifest["tables"]["market_price_day"]["coverage"]
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert pl.read_parquet(tmp_path / "sources.parquet")["source_id"].to_list() == ["dane_divipola", "dane_sipsa"]


def test_mismos_precios_dan_las_mismas_tablas(tmp_path):
    publish(tmp_path / "a", read(SAMPLE_SIPSA_ROWS))
    publish(tmp_path / "b", read(SAMPLE_SIPSA_ROWS))
    for table in ("market_price_day.parquet", "market_price_season.parquet"):
        assert (tmp_path / "a" / table).read_bytes() == (tmp_path / "b" / table).read_bytes()


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([sipsa_row("1", "Papa negra*", "2026-10-19", 3000, 2000, 3100)], "fuera del mínimo y el máximo"),
        ([sipsa_row("1", "Papa negra*", "2026-10-19", 1, 2, 3)] * 2, "repetidos"),
        ([sipsa_row("2", "Papa negra*", "2026-10-19", 1, 2, 3)], "vacía"),
    ],
)
def test_unos_precios_que_no_cumplen_el_contrato_no_se_publican(tmp_path, rows, message):
    with pytest.raises(build.ValidationError, match=message):
        publish(tmp_path, read(rows))
    assert not (tmp_path / "manifest.json").exists()


def test_el_redondeo_del_dane_no_es_un_error(tmp_path):
    """El DANE redondea el medio: 1563 con mínimo y máximo de 1562,5."""
    publish(tmp_path, read([sipsa_row("1", "Piña *", "2020-03-05", 1562.5, 1563, 1562.5, group="FRUTAS")]))


def test_sin_la_cache_de_sipsa_dice_como_bajarla(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        sipsa.read_cache(SAMPLE_MARKETS, tmp_path)


def test_lo_publicado_en_el_repositorio_cumple_el_contrato():
    """El dataset de la demo: precios de Corabastos y Tunja con su fuente."""
    folder = build.PUBLISHED
    if not (folder / "market_price_day.parquet").exists():
        pytest.skip("data/published no trae precios en esta imagen")
    prices = pl.read_parquet(folder / "market_price_day.parquet")
    build.validate_market(prices, pl.read_parquet(folder / "sources.parquet"))
    assert sorted(set(prices["market_id"].to_list())) == ["1", "9"]


# ---------- El último precio de cada producto (market_price_latest) ----------


def test_el_ultimo_precio_trae_el_de_hace_una_semana_y_el_cambio():
    """Lo calcula quien escribe los datos, no la API (revisión de Felipe del PR #12)."""
    latest = sipsa.latest(read(SAMPLE_SIPSA_ROWS))
    papa = latest.filter((pl.col("market_id") == "1") & (pl.col("product_id") == "papa-negra")).to_dicts()[0]
    assert (papa["date"], papa["avg_cop_kg"], papa["min_cop_kg"], papa["max_cop_kg"]) == (date(2026, 10, 19), 2925, 2800, 3000)
    assert (papa["week_ago_date"], papa["week_ago_avg_cop_kg"], papa["change_pct"]) == (date(2026, 10, 12), 2750, 6.4)
    assert papa["source_id"] == "dane_sipsa" and papa["several_varieties"] is True


def test_sin_precio_de_hace_una_semana_el_cambio_va_nulo():
    """La zanahoria solo tiene el 17 de octubre: no hay con qué compararla (R1)."""
    latest = sipsa.latest(read(SAMPLE_SIPSA_ROWS))
    zanahoria = latest.filter(pl.col("product_id") == "zanahoria").to_dicts()[0]
    assert zanahoria["week_ago_date"] is None and zanahoria["week_ago_avg_cop_kg"] is None and zanahoria["change_pct"] is None


def test_los_productos_van_en_el_orden_en_que_se_muestran_y_cada_central_dice_su_ultimo_dia():
    latest = sipsa.latest(read(SAMPLE_SIPSA_ROWS))
    corabastos = latest.filter(pl.col("market_id") == "1")
    # Primero tubérculos, raíces y plátanos; después verduras y hortalizas; las frutas al final. Dentro, por nombre.
    assert corabastos["product_id"].to_list() == ["papa-criolla", "papa-negra", "zanahoria", "aguacate"]
    assert corabastos["position"].to_list() == [1, 2, 3, 4]
    assert set(corabastos["market_date"].to_list()) == {date(2026, 10, 19)}
    assert set(corabastos["market_source_id"].to_list()) == {"dane_sipsa"}
    assert latest.select("market_id", "product_id").is_duplicated().sum() == 0


def test_el_ultimo_precio_se_publica_con_su_fila_en_el_manifiesto(tmp_path):
    manifest = publish(tmp_path, read(SAMPLE_SIPSA_ROWS))
    assert manifest["tables"]["market_price_latest"]["rows"] == 5
    assert pl.read_parquet(tmp_path / "market_price_latest.parquet").equals(sipsa.latest(read(SAMPLE_SIPSA_ROWS)))


def test_las_fuentes_del_dane_traen_su_cita():
    """La cita que piden los términos del DANE va en `sources.citation` (R8): la API la lee de ahí."""
    assert sipsa.source(read(SAMPLE_SIPSA_ROWS), "2026-10-20T15:34:00+00:00")["citation"] == dane.CITATION
    assert dane.source(SAMPLE_META)["citation"] == dane.CITATION
    assert dane.CITATION == "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co"


# ---------- Qué central da el precio de mercado en cada departamento (department_markets, HU-073) ----------

MARKET_REGION = {
    "dataset_version": "0.0.0-pruebas",
    "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS, "department_markets": {"15": "9", "25": "1"}},
}


def test_los_departamentos_y_centrales_que_existen_son_validos():
    build.validate_department_markets(MARKET_REGION)
    build.validate_department_markets(SAMPLE_REGION)


def test_la_region_del_repositorio_cumple_department_markets():
    build.validate_department_markets(build.load_region())


@pytest.mark.parametrize(
    ("department_markets", "message"),
    [
        ({"15": "99", "25": "1"}, "centrales que no están en `markets`.*99"),
        ({"15": 9, "25": "1"}, r"centrales que no están en `markets`: \[9\]"),
        ({15: "9", "25": "1"}, r"departamentos que no están en `departments`: \[15\]"),
        ({"15": "9", "52": "1"}, "departamentos que no están en `departments`.*52"),
    ],
)
def test_una_central_o_un_departamento_que_no_existen_hacen_fallar_el_build(tmp_path, department_markets, message):
    region = {**MARKET_REGION, "region": {**MARKET_REGION["region"], "department_markets": department_markets}}
    prices = read(SAMPLE_SIPSA_ROWS)
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    with pytest.raises(build.ValidationError, match=message):
        build.publish(region, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, tmp_path, prices=prices)
    assert not (tmp_path / "manifest.json").exists()
