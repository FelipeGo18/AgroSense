"""`market_month` (HU-051): el índice estacional y el precio de cada mes, por cultivo y central (R1, R4, R8)."""

import io

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, sipsa_row, sipsa_xml

CROPS = {
    "papa": {"product_id": "papa-negra"},
    "zanahoria": {"product_id": "zanahoria"},
    "haba": {"product_id": None, "reason": "Ejemplo: SIPSA no publica haba."},
}


def rows(market_id: str, product: str, years: range, price) -> list[str]:
    """Un precio el día 15 de cada mes de cada año, con `price(año, mes)`."""
    return [sipsa_row(market_id, product, f"{y}-{m:02d}-15", price(y, m), price(y, m), price(y, m)) for y in years for m in range(1, 13)]


def read(xml_rows: list[str]) -> pl.DataFrame:
    return sipsa.prices(io.BytesIO(sipsa_xml(xml_rows).encode()), SAMPLE_MARKETS)


def month_table(xml_rows: list[str], crops=CROPS) -> pl.DataFrame:
    prices = read(xml_rows)
    return sipsa.monthly(prices, sipsa.seasonal(prices), crops)


# Papa negra en Corabastos: 2021 a 2023 completos, con la inflación doblando el precio cada año y octubre a la mitad.
PAPA = rows("1", "Papa negra*", range(2021, 2024), lambda y, m: (2 ** (y - 2021)) * (500 if m == 10 else 1000))
# Enero de 2024: el año siguiente empezó, así que el último año completo (2023) es el esperado.
JANUARY_2024 = [sipsa_row("1", "Papa negra*", "2024-01-15", 4000, 4000, 4000)]


def test_cada_mes_trae_el_indice_y_el_precio_del_ultimo_ano_completo():
    table = month_table(PAPA + JANUARY_2024)
    assert table.height == 12
    assert set(table["crop_id"].to_list()) == {"papa"}
    october = table.filter(pl.col("month") == 10).row(0, named=True)
    year_mean = (11 * 1000 + 500) / 12
    assert october["seasonal_index"] == pytest.approx(500 / year_mean, abs=0.001)
    # El precio es el que se pagó en octubre de 2023, no un promedio entre años con inflación.
    assert (october["price_year"], october["price_cop_kg"]) == (2023, 2000)
    assert (october["product_id"], october["market_id"], october["years"], october["source_id"]) == ("papa-negra", "1", 3, "dane_sipsa")
    assert october["volume_t"] is None
    assert october["quality"] == "ok"


def test_el_indice_es_el_mismo_de_la_temporada_del_producto():
    prices = read(PAPA + JANUARY_2024)
    season = sipsa.seasonal(prices).select("month", "seasonal_index")
    table = sipsa.monthly(prices, sipsa.seasonal(prices), CROPS).select("month", "seasonal_index")
    assert table.sort("month").equals(season.sort("month"))


def test_un_cultivo_sin_producto_o_sin_anos_completos_no_tiene_filas():
    # Zanahoria con un solo año completo: no alcanza para el índice. Haba no tiene producto en SIPSA.
    zanahoria = rows("1", "Zanahoria", range(2023, 2024), lambda y, m: 1500)
    table = month_table(PAPA + JANUARY_2024 + zanahoria)
    assert set(table["crop_id"].to_list()) == {"papa"}


def test_un_producto_sin_cultivo_no_entra():
    criolla = rows("1", "Papa criolla", range(2021, 2024), lambda y, m: 3000)
    table = month_table(PAPA + JANUARY_2024 + criolla)
    assert set(table["product_id"].to_list()) == {"papa-negra"}


def test_cada_central_va_por_separado():
    tunja = rows("9", "Papa negra*", range(2021, 2024), lambda y, m: 900)
    table = month_table(PAPA + JANUARY_2024 + tunja)
    assert table.group_by("market_id").len().sort("market_id").rows() == [("1", 12), ("9", 12)]
    assert table.filter(pl.col("market_id") == "9")["price_cop_kg"].unique().to_list() == [900]


def test_si_sipsa_dejo_de_publicar_el_producto_la_calidad_es_parcial():
    # La zanahoria llega hasta 2025: el año esperado es 2024, y la papa se quedó en 2023.
    zanahoria = rows("1", "Zanahoria", range(2022, 2026), lambda y, m: 1500)
    table = month_table(PAPA + zanahoria)
    assert table.filter(pl.col("crop_id") == "papa")["quality"].unique().to_list() == ["partial"]
    assert table.filter(pl.col("crop_id") == "zanahoria")["quality"].unique().to_list() == ["ok"]


def test_sin_precios_la_tabla_sale_vacia_con_sus_columnas():
    table = month_table([sipsa_row("1", "Papa negra*", "2026-10-19", 2800, 2925, 3000)])
    assert table.is_empty()
    assert table.schema == pl.Schema(sipsa.MONTH_SCHEMA)


def publish(folder, xml_rows, crops=None):
    # Al publicar, el mapeo se valida contra los precios: el de ejemplo solo nombra la papa, que es lo que traen.
    crops = crops or {"papa": CROPS["papa"], "haba": CROPS["haba"]}
    prices = read(xml_rows)
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    return build.publish(SAMPLE_REGION, municipalities, sources, folder, prices=prices, crop_products=crops)


def test_publica_market_month_con_su_cobertura(tmp_path):
    manifest = publish(tmp_path, PAPA + JANUARY_2024)
    assert pl.read_parquet(tmp_path / "market_month.parquet").height == 12
    assert manifest["tables"]["market_month"]["rows"] == 12
    assert manifest["tables"]["market_month"]["coverage"].startswith("papa:")


def test_mismos_precios_dan_la_misma_tabla(tmp_path):
    publish(tmp_path / "a", PAPA + JANUARY_2024)
    publish(tmp_path / "b", PAPA + JANUARY_2024)
    assert (tmp_path / "a" / "market_month.parquet").read_bytes() == (tmp_path / "b" / "market_month.parquet").read_bytes()


def test_sin_mapeo_no_se_publica_market_month(tmp_path):
    prices = read(PAPA + JANUARY_2024)
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    manifest = build.publish(SAMPLE_REGION, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, tmp_path, prices=prices)
    assert "market_month" not in manifest["tables"]
    assert not (tmp_path / "market_month.parquet").exists()


def valid_month() -> pl.DataFrame:
    return month_table(PAPA + JANUARY_2024)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda t: pl.concat([t, t.head(1)]), "repite"),
        (lambda t: t.with_columns(pl.lit(None, dtype=pl.Int64).alias("price_cop_kg")), "fuera de lo permitido"),
        (lambda t: t.with_columns(pl.lit(0.0).alias("seasonal_index")), "fuera de lo permitido"),
        (lambda t: t.with_columns(pl.col("month").replace(12, 13)), "fuera de lo permitido"),
        (lambda t: t.with_columns(pl.lit("buena").alias("quality")), "fuera de lo permitido"),
        (lambda t: t.with_columns(pl.lit("papa-criolla").alias("product_id")), "no es el de `sipsa_crops.yaml`"),
        (lambda t: t.with_columns(pl.lit("otra_fuente").alias("source_id")), "no está en `sources`"),
    ],
)
def test_un_market_month_que_no_cumple_no_se_acepta(change, message):
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(read(PAPA), "2026-10-20T15:34:00+00:00")])
    with pytest.raises(build.ValidationError, match=message):
        build.validate_market_month(change(valid_month()), CROPS, sources)


def test_un_market_month_vacio_es_valido():
    sources = pl.DataFrame([dane.source(SAMPLE_META)])
    build.validate_market_month(pl.DataFrame(schema=sipsa.MONTH_SCHEMA), CROPS, sources)
