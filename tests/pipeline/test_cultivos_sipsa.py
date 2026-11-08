"""Qué producto de SIPSA da el precio de cada cultivo del MVP (HU-003): el mapeo de `sipsa_crops.yaml` y su validación.

Un cultivo sin producto lleva su porqué (R1); un producto no da el precio de dos cultivos ni dos productos se promedian
(decisión 11); los productos son los que SIPSA publica en la región (R7).
"""

import io

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, SAMPLE_SIPSA_ROWS, sipsa_xml

# Los 7 cultivos del MVP (EP-06, HU-061).
MVP_CROPS = {"papa", "arveja", "haba", "maiz", "cebolla_bulbo", "zanahoria", "avena_vicia"}


def sample_prices() -> pl.DataFrame:
    """Los precios de ejemplo: papa negra, papa criolla, zanahoria y aguacate."""
    return sipsa.prices(io.BytesIO(sipsa_xml(SAMPLE_SIPSA_ROWS).encode()), SAMPLE_MARKETS)


def publish(folder, crops):
    prices = sample_prices()
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    return build.publish(SAMPLE_REGION, municipalities, sources, folder, prices, crops)


def test_el_mapeo_trae_cada_cultivo_del_mvp():
    assert set(build.load_crops()) == MVP_CROPS


def test_el_mapeo_del_repositorio_tiene_la_forma_que_se_pide():
    """Contra unos precios con justo sus productos: revisa la forma sin depender del dataset publicado."""
    crops = build.load_crops()
    products = [entry["product_id"] for entry in crops.values() if entry["product_id"]]
    build.validate_crops(crops, pl.DataFrame({"product_id": products}))


def test_el_mapeo_del_repositorio_cumple_con_los_precios_publicados():
    """Cada producto del mapeo está en los precios de la demo: si SIPSA deja de publicar uno, esta prueba lo dice."""
    folder = build.PUBLISHED
    if not (folder / "market_price_day.parquet").exists():
        pytest.skip("data/published no trae precios en esta imagen")
    build.validate_crops(build.load_crops(), pl.read_parquet(folder / "market_price_day.parquet"))


@pytest.mark.parametrize(
    ("crops", "message"),
    [
        ({"papa": {"product_id": "papa-pastusa"}}, "no está en los precios"),
        ({"papa": {"product_id": "papa-negra"}, "papa_dos": {"product_id": "papa-negra"}}, "dos cultivos"),
        ({"haba": {"product_id": None}}, "por qué"),
        ({"haba": {"product_id": None, "reason": "  "}}, "por qué"),
        ({"Cebolla de bulbo": {"product_id": "zanahoria"}}, "snake_case"),
        ({"papa": {"product": "papa-negra"}}, "falta `product_id`"),
        ({"papa": {"product_id": "papa-negra", "nota": "sin acento"}}, "no se conocen"),
        ({"papa": {"product_id": ["papa-negra", "papa-criolla"]}}, "no está en los precios"),
        ({}, "no trae cultivos"),
    ],
)
def test_un_mapeo_que_no_cumple_no_se_acepta(crops, message):
    with pytest.raises(build.ValidationError, match=message):
        build.validate_crops(crops, sample_prices())


def test_un_cultivo_sin_producto_con_su_porque_es_valido():
    build.validate_crops({"haba": {"product_id": None, "reason": "SIPSA no publica haba."}}, sample_prices())


def test_con_un_mapeo_bueno_se_publica(tmp_path):
    crops = {"papa": {"product_id": "papa-negra"}, "haba": {"product_id": None, "reason": "SIPSA no publica haba."}}
    manifest = publish(tmp_path, crops)
    assert "market_price_day" in manifest["tables"]


def test_con_un_mapeo_malo_no_se_publica_nada(tmp_path):
    # Los precios de ejemplo no traen arveja.
    with pytest.raises(build.ValidationError, match="no está en los precios"):
        publish(tmp_path / "published", {"arveja": {"product_id": "arveja-verde-en-vaina"}})
    assert not (tmp_path / "published").exists()


def test_el_mapeo_sin_precios_no_se_puede_validar(tmp_path):
    sources = pl.DataFrame([dane.source(SAMPLE_META)])
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    with pytest.raises(build.ValidationError, match="no hay precios"):
        build.publish(SAMPLE_REGION, municipalities, sources, tmp_path, None, {"papa": {"product_id": "papa-negra"}})
