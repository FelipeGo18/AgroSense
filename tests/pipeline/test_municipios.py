"""Municipios de la región desde DIVIPOLA del DANE (HU-044) y su publicación (R4, R7, R8)."""

import json

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, SAMPLE_SIPSA_ROWS, sipsa_xml


@pytest.mark.parametrize(
    ("official", "shown"),
    [
        ("SAMACÁ", "Samacá"),
        ("VILLA DE LEYVA", "Villa de Leyva"),
        ("SAN ANTONIO DEL TEQUENDAMA", "San Antonio del Tequendama"),
        ("BOGOTÁ, D.C.", "Bogotá, D.C."),
        ("EL PEÑÓN", "El Peñón"),
        ("GÜICÁN DE LA SIERRA", "Güicán de la Sierra"),
    ],
)
def test_el_nombre_oficial_se_escribe_como_se_lee(official, shown):
    assert dane.display_name(official) == shown


def test_solo_entran_los_departamentos_de_la_region_ordenados_por_codigo():
    table = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    assert table["municipality_id"].to_list() == ["15407", "15646", "25899"]
    samaca = table.filter(pl.col("municipality_id") == "15646").to_dicts()[0]
    assert (samaca["name"], samaca["department"], samaca["lat"], samaca["lon"]) == ("Samacá", "Boyacá", 5.4925, -73.4856)
    assert samaca["source_ids"] == ["dane_divipola"]


def test_lo_que_todavia_no_tiene_fuente_va_nulo():
    """La altitud llega con NASADEM y la de la celda con NASA POWER: hasta entonces, nula (R1)."""
    table = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15"])
    assert table["altitude_m"].null_count() == table.height
    assert table["climate_cell_elevation_m"].null_count() == table.height


def test_una_coordenada_vacia_queda_nula_no_en_cero():
    rows = [{**SAMPLE_MUNICIPALITIES[0], "latitud": ""}]
    assert dane.municipalities(rows, ["15"])["lat"].to_list() == [None]


def test_la_fuente_dice_de_donde_viene_y_su_licencia():
    row = dane.source(SAMPLE_META)
    assert row["source_id"] == "dane_divipola" and row["url"].startswith("https://www.datos.gov.co/")
    assert row["license"] == "CC BY-SA 4.0" and row["coverage"] == "Colombia"


def publish(folder, municipalities=None):
    table = municipalities if municipalities is not None else dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    return build.publish(SAMPLE_REGION, table, pl.DataFrame([dane.source(SAMPLE_META)]), folder)


def test_publica_las_tablas_y_el_manifiesto(tmp_path):
    manifest = publish(tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["manifest.json", "municipalities.parquet", "sources.parquet"]
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert manifest["dataset_version"] == "0.0.0-pruebas" and manifest["rules_version"] is None
    assert manifest["tables"]["municipalities"]["rows"] == 3


def test_mismos_datos_dan_las_mismas_tablas(tmp_path):
    publish(tmp_path / "a")
    publish(tmp_path / "b")
    for table in ("municipalities.parquet", "sources.parquet"):
        assert (tmp_path / "a" / table).read_bytes() == (tmp_path / "b" / table).read_bytes()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"cod_mpio": "1564"}, "no son DIVIPOLA de 5 dígitos"),
        ({"cod_mpio": "15407"}, "repetidos"),
        ({"nom_mpio": "  "}, "sin nombre"),
        ({"latitud": "95,0"}, "fuera de rango"),
    ],
)
def test_una_tabla_que_no_cumple_el_contrato_no_se_publica(tmp_path, change, message):
    rows = [{**SAMPLE_MUNICIPALITIES[0], **change}, SAMPLE_MUNICIPALITIES[1]]
    with pytest.raises(build.ValidationError, match=message):
        publish(tmp_path, dane.municipalities(rows, ["15"]))
    assert not (tmp_path / "manifest.json").exists()


def test_una_fila_con_una_fuente_que_no_existe_no_se_publica(tmp_path):
    table = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15"]).with_columns(pl.lit(["inventada"]).alias("source_ids"))
    with pytest.raises(build.ValidationError, match="inventada"):
        publish(tmp_path, table)


def test_sin_la_cache_dice_como_bajarla(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        dane.read_cache(tmp_path)


def test_reconstruye_desde_la_cache_sin_usar_la_red(tmp_path, monkeypatch):
    cache, market_cache = tmp_path / "raw", tmp_path / "raw-sipsa"
    cache.mkdir()
    market_cache.mkdir()
    (cache / dane.ROWS_FILE).write_text(json.dumps(SAMPLE_MUNICIPALITIES), encoding="utf-8")
    (cache / dane.META_FILE).write_text(json.dumps(SAMPLE_META), encoding="utf-8")
    (market_cache / sipsa.ROWS_FILE).write_text(sipsa_xml(SAMPLE_SIPSA_ROWS), encoding="utf-8")
    (market_cache / sipsa.META_FILE).write_text("2026-10-20T15:34:00+00:00", encoding="utf-8")

    def no_network(*args, **kwargs):
        raise AssertionError("no debe usar la red")

    monkeypatch.setattr(dane.urllib.request, "urlopen", no_network)
    region = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}
    monkeypatch.setattr(build, "load_region", lambda: region)
    manifest = build.build(folder=tmp_path / "published", cache=cache, market_cache=market_cache)
    assert manifest["tables"]["municipalities"]["rows"] == 3
    assert manifest["tables"]["market_price_day"]["rows"] == 7


def test_lo_publicado_en_el_repositorio_cumple_el_contrato():
    """El dataset de la demo: 123 municipios de Boyacá y 116 de Cundinamarca, con su fuente."""
    folder = build.PUBLISHED
    if not (folder / "manifest.json").exists():
        pytest.skip("data/published no está en esta imagen")
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    build.validate(municipalities, pl.read_parquet(folder / "sources.parquet"))
    assert dict(municipalities.group_by("department_id").len().iter_rows()) == {"15": 123, "25": 116}
