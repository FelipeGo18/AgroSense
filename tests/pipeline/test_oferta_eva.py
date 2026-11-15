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


def test_maiz_sumado_sin_cosecha_tiene_rendimiento_0_y_sale_ok():
    """Dos códigos de maíz con cosecha 0: el rendimiento es 0, como el que publica EVA con un solo código, y la fila es
    `ok` porque EVA trae los cuatro valores (revisión de Haider del PR #117; antes salía nulo y `partial`)."""
    table = normalize(
        [
            row(code="1010402", planted="5", harvested="0", production="0", yield_="0"),
            row(code="1010404", planted="3", harvested="0", production="0", yield_="0"),
        ]
    )
    maize = table.row(0, named=True)
    assert (maize["planted_ha"], maize["harvested_ha"], maize["yield_t_ha"], maize["quality"]) == (8.0, 0.0, 0.0, "ok")


def test_la_cobertura_dice_que_sin_fila_es_sin_dato():
    """Lo aprobado para HU-032: un municipio sin fila de un cultivo en un semestre es «sin dato», no «no se sembró»."""
    coverage = eva.source(EVA_META, normalize([row()]))["coverage"]
    assert "sin dato" in coverage and "no siembra" not in coverage


def supply_inputs():
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    sources = pl.DataFrame([dane.source(SAMPLE_META), eva.source(EVA_META, pl.DataFrame())])
    return municipalities, sources


@pytest.mark.parametrize(
    ("change", "catalog_ids", "message"),
    [
        ({"crop_id": "yuca"}, {"papa"}, "no están en el catálogo"),
        ({"semester": "C"}, None, "un semestre o un valor"),
        ({"planted_ha": -1.0}, None, "un semestre o un valor"),
        ({"source_id": "otra"}, None, "no está en `sources`"),
    ],
)
def test_un_supply_semester_imposible_no_pasa(change, catalog_ids, message):
    municipalities, sources = supply_inputs()
    supply = normalize([row()]).with_columns(pl.lit(value).alias(column) for column, value in change.items())
    with pytest.raises(build.ValidationError, match=message):
        build.validate_supply(supply, municipalities, sources, catalog_ids)


def fake_fetch(pages, calls):
    """Un `fetch` de ejemplo: cada página de datos.gov.co es un CSV (R5); los metadatos, un JSON."""

    def fetch(request, dest, timeout_s, max_bytes):
        calls.append((request.full_url, timeout_s, max_bytes))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if request.full_url == eva.META_URL:
            dest.write_text(json.dumps({"name": "EVA (ejemplo)", "license": {"name": "CC BY-SA 4.0"}}), encoding="utf-8")
        else:
            dest.write_text(pages.pop(0), encoding="utf-8")
        return dest

    return fetch


def csv_page(header, rows):
    return "\n".join([",".join(header), *(",".join(r) for r in rows)]) + "\n"


def test_la_descarga_sigue_las_paginas_y_guarda_todo_con_los_metadatos(tmp_path, monkeypatch):
    header = list(eva.COLUMNS.values())
    full = [[f"{i}"] * len(header) for i in range(3)]
    calls = []
    monkeypatch.setattr(eva, "PAGE_ROWS", 3)
    monkeypatch.setattr(eva, "fetch", fake_fetch([csv_page(header, full), csv_page(header, full[:1])], calls))
    eva.download(["15", "25"], tmp_path)
    saved = (tmp_path / eva.ROWS_FILE).read_text(encoding="utf-8").splitlines()
    # Dos páginas (3 filas y 1, la última corta) y los metadatos, todo por `fetch` con su tope de tiempo y tamaño.
    assert len(saved) == 1 + 4 and "%24offset=3" in calls[1][0]
    assert calls[-1] == (eva.META_URL, eva.META_TIMEOUT_S, eva.META_MAX_BYTES)
    assert json.loads((tmp_path / eva.META_FILE).read_text(encoding="utf-8"))["license"] == "CC BY-SA 4.0"


def test_paginas_con_columnas_distintas_no_se_guardan(tmp_path, monkeypatch):
    header = list(eva.COLUMNS.values())
    calls = []
    monkeypatch.setattr(eva, "PAGE_ROWS", 1)
    pages = [csv_page(header, [["1"] * len(header)]), csv_page([*header, "otra"], [["2"] * (len(header) + 1)])]
    monkeypatch.setattr(eva, "fetch", fake_fetch(pages, calls))
    with pytest.raises(eva.EvaError, match="columnas distintas"):
        eva.download(["15"], tmp_path)
    assert not (tmp_path / eva.ROWS_FILE).exists()


def test_una_respuesta_sin_filas_no_se_guarda(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(eva, "fetch", fake_fetch([""], calls))
    with pytest.raises(eva.EvaError, match="no devolvió filas"):
        eva.download(["15"], tmp_path)
    assert not (tmp_path / eva.ROWS_FILE).exists()


def test_si_datos_gov_co_falla_se_avisa_y_se_sigue(tmp_path, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise OSError("sin red (ejemplo)")

    monkeypatch.setattr(eva, "fetch", broken)
    with caplog.at_level("WARNING"):
        build.download_supply(["15"], tmp_path)
    assert any("source_skipped" in str(record.msg) for record in caplog.records)
