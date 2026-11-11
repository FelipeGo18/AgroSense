"""Municipios de la región desde DIVIPOLA del DANE (HU-044) y su publicación (R4, R7, R8)."""

import json

import polars as pl
import pytest
import shapely
from shapely.geometry import box, mapping

from pipeline import build
from pipeline.sources import dane, dane_mgn, sipsa
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
    for department, ids in (("15", ["15407", "15646"]), ("25", ["25899"])):
        (cache / dane_mgn._file(department)).write_text(json.dumps(feature_collection(ids)), encoding="utf-8")

    def no_network(*args, **kwargs):
        raise AssertionError("no debe usar la red")

    monkeypatch.setattr(dane.urllib.request, "urlopen", no_network)
    region = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}
    monkeypatch.setattr(build, "load_region", lambda: region)
    # El mapeo de ejemplo, con productos que trae la caché de ejemplo (HU-003).
    crops = {"papa": {"product_id": "papa-negra"}, "haba": {"product_id": None, "reason": "Ejemplo: sin producto en SIPSA."}}
    monkeypatch.setattr(build, "load_crops", lambda: crops)
    manifest = build.build(folder=tmp_path / "published", cache=cache, market_cache=market_cache, power_cache=tmp_path / "sin-clima")
    assert manifest["tables"]["municipalities"]["rows"] == 3
    assert manifest["tables"]["municipality_boundaries"]["rows"] == 3
    assert manifest["tables"]["market_price_day"]["rows"] == 7


def test_lo_publicado_en_el_repositorio_cumple_el_contrato():
    """El dataset de la demo: 123 municipios de Boyacá y 116 de Cundinamarca, con su fuente."""
    folder = build.PUBLISHED
    if not (folder / "manifest.json").exists():
        pytest.skip("data/published no está en esta imagen")
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    sources = pl.read_parquet(folder / "sources.parquet")
    build.validate(municipalities, sources)
    assert dict(municipalities.group_by("department_id").len().iter_rows()) == {"15": 123, "25": 116}
    build.validate_boundaries(pl.read_parquet(folder / "municipality_boundaries.parquet"), municipalities, sources)


# ---------- Límites municipales (MGN del DANE) ----------


def feature_collection(ids):
    """Como lo devuelve el geoportal del DANE: propiedades en minúscula y un cuadrado por municipio (ejemplo, R5)."""
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"mpio_cdpmp": mid, "mpio_cnmbre": "X"}, "geometry": mapping(box(i, 0, i + 0.5, 0.5))}
            for i, mid in enumerate(ids)
        ],
    }


def test_los_limites_se_guardan_por_codigo_validos_y_con_su_fuente():
    table = dane_mgn.boundaries(feature_collection(["25899", "15646"])["features"])
    assert table["municipality_id"].to_list() == ["15646", "25899"]
    assert set(table["source_id"].to_list()) == {"dane_mgn_2025"}
    assert all(shapely.from_wkb(wkb).is_valid for wkb in table["geometry"].to_list())


def test_un_limite_que_se_cruza_se_corrige_al_leerlo():
    bow = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    table = dane_mgn.boundaries([{"type": "Feature", "properties": {"MPIO_CDPMP": "15646"}, "geometry": bow}])
    assert shapely.from_wkb(table["geometry"][0]).is_valid


def boundary_table(ids):
    return dane_mgn.boundaries(feature_collection(ids)["features"])


def publish_with(tmp_path, boundaries):
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    sources = pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)])
    return build.publish(SAMPLE_REGION, municipalities, sources, tmp_path, boundaries)


def test_publica_los_limites_y_los_cuenta_en_el_manifiesto(tmp_path):
    manifest = publish_with(tmp_path, boundary_table(["15407", "15646", "25899"]))
    assert manifest["tables"]["municipality_boundaries"]["rows"] == 3
    assert (tmp_path / "municipality_boundaries.parquet").exists()


@pytest.mark.parametrize(
    ("ids", "message"),
    [
        (["15407", "15646"], "faltan \\['25899'\\]"),
        (["15407", "15646", "25899", "99999"], "sobran \\['99999'\\]"),
        (["15407", "15646", "25899", "25899"], "repetidos"),
    ],
)
def test_limites_que_no_cuadran_con_los_municipios_no_se_publican(tmp_path, ids, message):
    with pytest.raises(build.ValidationError, match=message):
        publish_with(tmp_path, boundary_table(ids))
    assert not (tmp_path / "manifest.json").exists()
