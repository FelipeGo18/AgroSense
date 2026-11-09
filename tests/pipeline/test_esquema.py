"""HU-011: el esquema en código coincide con el contrato, y lo publicado y los ejemplos cumplen el esquema."""

import json
import re
from pathlib import Path

import polars as pl
import pytest

from pipeline import examples, schema

CONTRACT = Path("specs/02-contratos.md")
PUBLISHED = Path("data/published")
EXAMPLES = Path("data/examples")
# Lo real que se copia en los ejemplos; todo lo demás es inventado y cita `ejemplo`.
REAL_IN_EXAMPLES = {"crops", "crop_stages", "municipality_boundaries", "sources"}


def contract_tables() -> dict[str, str]:
    """Las filas de «Tablas publicadas» del contrato: nombre de la tabla → texto de la fila."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("## Tablas publicadas (Parquet)", 1)[1].split("\n### ", 1)[0]
    rows = {}
    for line in section.splitlines():
        found = re.match(r"\| `([a-z_]+)`", line)
        if found:
            rows[found.group(1)] = line
    return rows


def test_el_esquema_tiene_las_mismas_tablas_que_el_contrato():
    assert set(schema.TABLES) == set(contract_tables())


@pytest.mark.parametrize("name", sorted(schema.TABLES))
def test_cada_columna_del_esquema_esta_en_el_contrato(name):
    row = contract_tables()[name]
    missing = [col for col in schema.TABLES[name].columns if f"`{col}`" not in row]
    assert not missing, f"{name}: columnas del esquema que el contrato no nombra: {missing}"
    assert all(f"`{col}`" in row for col in schema.TABLES[name].key)


def test_la_celda_de_un_punto_contiene_ese_punto():
    for lat, lon in [(5.492161, -73.485589), (4.7, -74.1), (-0.001, 0.001)]:
        cell = schema.cell_id(lat, lon)
        center_lat, center_lon = schema.cell_center(cell)
        assert abs(center_lat - lat) <= schema.GRID_STEP_DEG / 2 + 1e-9
        assert abs(center_lon - lon) <= schema.GRID_STEP_DEG / 2 + 1e-9
        assert schema.cell_id(center_lat, center_lon) == cell


def test_check_rechaza_una_tabla_que_no_cumple():
    good = pl.DataFrame(
        {"municipality_id": ["15646"], "month": [1], "frost_freq_pct": [10.0]},
    )
    with pytest.raises(schema.SchemaError, match="columnas"):
        schema.check("climate_risk_month", good)
    with pytest.raises(schema.SchemaError, match="no es una tabla"):
        schema.check("no_existe", good)


def _check_folder(folder: Path, names: list[str]) -> dict[str, pl.DataFrame]:
    tables = {name: pl.read_parquet(folder / f"{name}.parquet") for name in names}
    for name, table in tables.items():
        schema.check(name, table)
    known = set(tables["sources"]["source_id"].to_list())
    for name, table in tables.items():
        assert schema.cited_sources(name, table) <= known, f"{name} cita fuentes que no están en `sources` (R8)"
    if "municipalities" in tables:
        towns = set(tables["municipalities"]["municipality_id"].to_list())
        for name, table in tables.items():
            if "municipality_id" in table.columns and name != "municipalities":
                assert set(table["municipality_id"].to_list()) <= towns, f"{name} usa municipios que no están (R7)"
    if "crops" in tables:
        crops = set(tables["crops"]["crop_id"].to_list())
        for name, table in tables.items():
            if "crop_id" in table.columns and name != "crops":
                assert set(table["crop_id"].to_list()) <= crops, f"{name} usa cultivos que no están en el catálogo"
    return tables


def test_lo_publicado_cumple_el_esquema_y_el_manifiesto():
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    files = sorted(path.stem for path in PUBLISHED.glob("*.parquet"))
    assert sorted(manifest["tables"]) == files
    tables = _check_folder(PUBLISHED, files)
    for name, info in manifest["tables"].items():
        assert tables[name].height == info["rows"]


def test_los_ejemplos_cubren_todo_el_contrato_y_lo_cumplen():
    manifest = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["example"] is True
    assert sorted(manifest["tables"]) == sorted(schema.TABLES)
    tables = _check_folder(EXAMPLES, sorted(schema.TABLES))
    for name, info in manifest["tables"].items():
        assert tables[name].height == info["rows"]


@pytest.mark.parametrize("name", sorted(set(schema.TABLES) - REAL_IN_EXAMPLES))
def test_cada_cifra_inventada_esta_rotulada_como_ejemplo(name):
    table = pl.read_parquet(EXAMPLES / f"{name}.parquet")
    cited = schema.cited_sources(name, table)
    assert examples.SOURCE_ID in cited, f"{name} no cita la fuente `ejemplo` (R5)"
    if schema.TABLES[name].source_column == "source_id":
        assert cited == {examples.SOURCE_ID}


def test_las_celdas_de_ejemplo_cuadran_con_sus_coordenadas():
    cells = pl.read_parquet(EXAMPLES / "grid_cells.parquet")
    for cell, lat, lon in cells.select("cell_id", "lat", "lon").iter_rows():
        assert schema.cell_id(lat, lon) == cell


def test_los_ejemplos_son_deterministas(tmp_path):
    """Mismo comando, mismos archivos (R4): se regeneran y se comparan con los del repositorio."""
    written = examples.write(examples.build(), tmp_path)
    for name in written["tables"]:
        assert pl.read_parquet(tmp_path / f"{name}.parquet").equals(pl.read_parquet(EXAMPLES / f"{name}.parquet")), name
