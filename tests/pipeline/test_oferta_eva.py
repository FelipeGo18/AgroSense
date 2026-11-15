"""Oferta de EVA de la UPRA normalizada por DIVIPOLA, cultivo y semestre (HU-031; tabla `supply_semester`)."""

import csv
import io
import json
from collections import Counter

import polars as pl
import pytest

from pipeline import build, catalog, schema
from pipeline.sources import dane, dane_mgn, eva
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION
from tests.pipeline.test_municipios import feature_collection

TOWNS = {"15646", "15407", "25899"}
CODES = {1080701: "papa", 1010402: "maiz", 1010404: "maiz"}
EVA_META = {
    "name": "Evaluaciones Agropecuarias Municipales – EVA. 2019 - 2025. Base Agrícola (ejemplo de pruebas)",
    "license": "Creative Commons Attribution | Share Alike 4.0 International",
    "rows_updated_at": 1787936043,
    "downloaded_at": "2026-11-14T00:00:00+00:00",
}


def row(town="15646", code="1080701", period="2024A", planted="10", harvested="9", production="180", yield_="20", dept=None):
    """Una fila de la base agrícola de EVA, con los nombres de campo de datos.gov.co."""
    return {
        "c_digo_dane_departamento": dept or town[:2],
        "c_digo_dane_municipio": town,
        "c_digo_del_cultivo": code,
        "periodo": period,
        "rea_sembrada": planted,
        "rea_cosechada": harvested,
        "producci_n": production,
        "rendimiento": yield_,
    }


def raw(rows):
    return pl.DataFrame(rows, schema={col: pl.String for col in eva.COLUMNS.values()})


def normalize(rows, counts=None):
    return eva.normalize(raw(rows), CODES, ["15", "25"], TOWNS, counts if counts is not None else Counter())


def test_una_fila_por_municipio_cultivo_y_semestre_con_la_fuente():
    table = normalize([row(period="2024A"), row(period="2024B", planted="12")])
    assert table.columns == list(schema.TABLES["supply_semester"].columns)
    assert table.select("municipality_id", "crop_id", "year", "semester", "source_id", "planted_ha").rows() == [
        ("15646", "papa", 2024, "A", "eva", 10.0),
        ("15646", "papa", 2024, "B", "eva", 12.0),
    ]
    schema.check("supply_semester", table)


def test_la_variacion_y_la_participacion_quedan_para_hu_032():
    table = normalize([row()])
    assert table["planted_change_pct"].to_list() == [None] and table["dept_share_pct"].to_list() == [None]


def test_los_dos_ultimos_anos_de_la_descarga_son_preliminares():
    """La nota de EVA: «las cifras de los dos últimos años son susceptibles de modificación»."""
    table = normalize([row(period=f"{year}A") for year in (2022, 2023, 2024, 2025)])
    assert dict(table.select("year", "preliminary").rows()) == {2022: False, 2023: False, 2024: True, 2025: True}


def test_los_codigos_de_un_mismo_cultivo_se_suman_y_el_rendimiento_sale_de_los_totales():
    table = normalize(
        [
            row(code="1010402", planted="30", harvested="20", production="60", yield_="3"),
            row(code="1010404", planted="10", harvested="10", production="40", yield_="4"),
        ]
    )
    maize = table.row(0, named=True)
    assert (maize["crop_id"], maize["planted_ha"], maize["harvested_ha"], maize["production_t"]) == ("maiz", 40.0, 30.0, 100.0)
    assert maize["yield_t_ha"] == 3.33 and maize["quality"] == "ok"


def test_si_una_parte_no_trae_el_valor_el_total_queda_nulo_y_partial():
    """Sumar solo las partes con dato daría un total más bajo que el real: queda nulo (R1)."""
    table = normalize([row(code="1010402", production="60"), row(code="1010404", production="")])
    maize = table.row(0, named=True)
    assert maize["production_t"] is None and maize["yield_t_ha"] is None
    assert maize["planted_ha"] == 20.0 and maize["quality"] == "partial"


def test_con_un_solo_codigo_el_rendimiento_es_el_de_eva():
    table = normalize([row(harvested="14.55", production="261.90", yield_="18.00")])
    assert table["yield_t_ha"].to_list() == [18.0]


def test_desde_2022_lo_cosechado_puede_pasar_a_lo_sembrado_y_no_se_descarta():
    """Desde 2022 EVA da las cosechas efectivas de cada semestre: se cosecha lo sembrado en el anterior."""
    counts = Counter()
    table = normalize([row(period="2024B", planted="10", harvested="30", production="600")], counts)
    assert table.height == 1 and sum(counts[reason] for reason in eva.REASONS) == 0


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (row(town="05001"), "outside_region"),
        (row(town="5001", dept="05"), "outside_region"),
        (row(town="15999"), "unknown_municipality"),
        (row(period="2024"), "no_semester"),
        (row(planted="diez"), "bad_value"),
        (row(planted="-3"), "negative_value"),
        (row(planted="", harvested="", production="", yield_=""), "no_data"),
    ],
)
def test_cada_fila_descartada_tiene_su_motivo(bad, reason):
    counts = Counter()
    table = normalize([row(town="25899"), bad], counts)
    assert table["municipality_id"].to_list() == ["25899"]
    assert counts[reason] == 1 and sum(counts[r] for r in eva.REASONS) == 1


def test_ninguna_fila_se_pierde_sin_motivo():
    """Cada fila leída sale publicada, es de otro cultivo o se descarta con su motivo (R1)."""
    counts = Counter()
    rows = [row(), row(town="25899", production=""), row(town="15407", planted="", harvested="", production="", yield_="")]
    table = normalize(rows, counts)
    assert table.height + counts["other_crop"] + sum(counts[r] for r in eva.REASONS) == counts["read"] == 3


def test_una_fila_repetida_se_descarta_entera():
    """Dos filas del mismo municipio, código y semestre: no se sabe cuál vale, así que no entra ninguna (R1)."""
    counts = Counter()
    table = normalize([row(), row(planted="99"), row(town="25899")], counts)
    assert table["municipality_id"].to_list() == ["25899"] and counts["duplicate"] == 2


def test_los_cultivos_que_no_son_del_mvp_se_cuentan_aparte():
    counts = Counter()
    normalize([row(), row(code="2030300")], counts)
    assert counts["read"] == 2 and counts["other_crop"] == 1 and sum(counts[r] for r in eva.REASONS) == 0


def test_sale_ordenada_por_su_llave():
    table = normalize([row(town="25899", period="2024B"), row(town="15407"), row(town="25899", period="2024A")])
    key = ["municipality_id", "crop_id", "year", "semester"]
    assert table.select(key).rows() == table.sort(key).select(key).rows()


def test_el_mapeo_del_repositorio_cubre_el_catalogo_sin_repetir_codigos():
    mapping = build.load_eva_crops()
    ids = {crop["crop_id"] for crop in catalog.load()["crops"]}
    codes = eva.crop_codes(mapping, ids)
    assert set(mapping["crops"]) == ids
    assert {codes[1080701], codes[1010402], codes[1051100]} == {"papa", "maiz", "cebolla_bulbo"}
    assert 1080702 not in codes  # la papa criolla es otro cultivo


@pytest.mark.parametrize(
    ("crops", "message"),
    [
        ({}, "no trae cultivos"),
        ({"yuca": {"eva_codes": [1081001]}}, "no están en `catalog/crops.yaml`"),
        ({"papa": {"eva_codes": [1]}, "haba": {"eva_codes": [1]}}, "está en dos cultivos"),
        ({"papa": {"eva_codes": None}}, "tiene que decir por qué"),
        ({"papa": {"notes": "sin códigos"}}, "falta `eva_codes`"),
        ({"papa": {"eva_codes": ["1080701"]}}, "no es un número"),
        ({"papa": {"eva_codes": [1], "producto": "x"}}, "campos que no se conocen"),
    ],
)
def test_un_mapeo_que_no_sirve_hace_fallar(crops, message):
    with pytest.raises(eva.EvaError, match=message):
        eva.crop_codes({"crops": crops}, {"papa", "haba"})


def test_la_fuente_dice_lo_que_cubre_y_su_licencia():
    source = eva.source(EVA_META, normalize([row(period="2023B"), row(town="25899", period="2025A")]))
    assert source["source_id"] == "eva" and source["url"] == "https://www.datos.gov.co/d/uejq-wxrr"
    assert source["license"] == "CC BY-SA 4.0" and source["institution"].endswith("(UPRA)")
    assert source["period_covered"].startswith("Siembras de 2023B a 2025A")
    assert "2 municipios" in source["coverage"] and "A = enero a junio" in source["notes"]


def test_sin_la_cache_dice_como_bajarla(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        eva.read_cache(tmp_path)


def write_cache(folder, rows):
    folder.mkdir(parents=True, exist_ok=True)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["municipio", *eva.COLUMNS.values()], lineterminator="\n")
    writer.writeheader()
    writer.writerows({"municipio": "Ejemplo", **r} for r in rows)
    (folder / eva.ROWS_FILE).write_text(out.getvalue(), encoding="utf-8")
    (folder / eva.META_FILE).write_text(json.dumps(EVA_META), encoding="utf-8")


REGION = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}


def write_dane_cache(cache):
    """Los municipios y sus límites de ejemplo, para reconstruir sin la red."""
    cache.mkdir(parents=True, exist_ok=True)
    (cache / dane.ROWS_FILE).write_text(json.dumps(SAMPLE_MUNICIPALITIES), encoding="utf-8")
    (cache / dane.META_FILE).write_text(json.dumps(SAMPLE_META), encoding="utf-8")
    for department, ids in (("15", ["15407", "15646"]), ("25", ["25899"])):
        (cache / dane_mgn._file(department)).write_text(json.dumps(feature_collection(ids)), encoding="utf-8")


def test_publica_supply_semester_desde_la_cache_sin_usar_la_red(tmp_path, monkeypatch):
    cache, supply_cache = tmp_path / "raw", tmp_path / "raw-eva"
    write_dane_cache(cache)
    write_cache(supply_cache, [row(period="2024A"), row(town="25899", code="1010402", period="2025B"), row(code="2030300")])

    def no_network(*args, **kwargs):
        raise AssertionError("no debe usar la red")

    monkeypatch.setattr(eva.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(build, "load_region", lambda: REGION)
    manifest = build.build(folder=tmp_path / "published", cache=cache, power_cache=tmp_path / "sin-clima", supply_cache=supply_cache)
    assert manifest["tables"]["supply_semester"]["rows"] == 2
    assert "siembras de 2024A a 2025B" in manifest["tables"]["supply_semester"]["coverage"]
    published = pl.read_parquet(tmp_path / "published" / "supply_semester.parquet")
    schema.check("supply_semester", published)
    sources = pl.read_parquet(tmp_path / "published" / "sources.parquet")
    assert "eva" in sources["source_id"].to_list()


def test_sin_la_cache_de_eva_se_publica_lo_demas(tmp_path, monkeypatch):
    cache = tmp_path / "raw"
    write_dane_cache(cache)
    monkeypatch.setattr(build, "load_region", lambda: REGION)
    folder, power, supply = tmp_path / "published", tmp_path / "sin-clima", tmp_path / "sin-eva"
    manifest = build.build(folder=folder, cache=cache, power_cache=power, supply_cache=supply)
    assert "supply_semester" not in manifest["tables"] and manifest["tables"]["municipalities"]["rows"] == 3


def test_un_supply_semester_con_un_municipio_que_no_se_publica_no_pasa():
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15"])
    sources = pl.DataFrame([dane.source(SAMPLE_META), eva.source(EVA_META, pl.DataFrame())])
    supply = normalize([row(town="25899")])
    with pytest.raises(build.ValidationError, match="no están en `municipalities`"):
        build.validate_supply(supply, municipalities, sources, None)
