"""Lluvia por satélite de GPM IMERG por municipio (HU-207): `precip_month`.

Sin red: las celdas y la lluvia son de ejemplo (R5), en la rejilla de 0,1° de IMERG.
"""

import json

import polars as pl
import pytest
import shapely

from pipeline import build, climate_normals
from pipeline.sources import imerg

NORMAL = climate_normals.Normal(first_year=2001, last_year=2024, min_years=20, min_day_share=0.9, dry_quantile=0.2)


def boundaries(*places: tuple[str, shapely.Geometry]) -> pl.DataFrame:
    return pl.DataFrame(
        {"municipality_id": [p[0] for p in places], "geometry": [shapely.to_wkb(p[1]) for p in places]},
        schema={"municipality_id": pl.String, "geometry": pl.Binary},
    )


def cell_months(values: dict[tuple[int, int], float | None], years=range(2001, 2025), month=1) -> pl.DataFrame:
    rows = [(row, col, year, month, value) for (row, col), value in values.items() for year in years]
    return pl.DataFrame(rows, schema=imerg.CELL_MONTH_SCHEMA, orient="row")


# Una celda de 0,1° cerca de Tunja: de 5,5° a 5,6° N y de 73,4° a 73,3° O.
ROW, COL = imerg.cell_index(5.55, -73.35)


def test_la_celda_de_un_punto_y_su_recuadro():
    box = imerg.cell_box(ROW, COL)
    assert shapely.bounds(box) == pytest.approx((-73.4, 5.5, -73.3, 5.6))


def test_el_peso_es_el_area_de_la_celda_dentro_del_municipio():
    # Un municipio que cubre toda una celda y la mitad de la del oriente.
    place = shapely.box(-73.4, 5.5, -73.25, 5.6)
    table = imerg.weights(boundaries(("15001", place)))
    by_cell = {(r, c): w for _, r, c, w in table.iter_rows()}
    assert set(by_cell) == {(ROW, COL), (ROW, COL + 1)}
    assert by_cell[(ROW, COL)] == pytest.approx(2 * by_cell[(ROW, COL + 1)])


def test_una_celda_que_solo_toca_el_borde_no_cuenta():
    table = imerg.weights(boundaries(("15001", shapely.box(-73.4, 5.5, -73.3, 5.6))))
    assert table.select("row", "col").rows() == [(ROW, COL)]


def test_la_lluvia_del_municipio_es_el_promedio_ponderado_por_area():
    place = boundaries(("15001", shapely.box(-73.4, 5.5, -73.25, 5.6)))
    table = imerg.precip_month(cell_months({(ROW, COL): 90.0, (ROW, COL + 1): 30.0}), imerg.weights(place), NORMAL)
    row = table.filter(pl.col("year") == 2010).to_dicts()[0]
    # 90 con peso 2 y 30 con peso 1.
    assert row["precip_mm"] == pytest.approx(70.0)
    assert (row["precip_normal_mm"], row["normal_period"], row["quality"], row["source_id"]) == (70.0, "2001-2024", "ok", "imerg")


def test_el_ano_seco_es_el_percentil_20_del_periodo_normal():
    place = boundaries(("15001", imerg.cell_box(ROW, COL)))
    rain = pl.concat(
        [cell_months({(ROW, COL): float(10 * i)}, years=[2000 + i]) for i in range(1, 25)]
        # Fuera del periodo normal: no cuenta.
        + [cell_months({(ROW, COL): 5000.0}, years=[2025])]
    )
    row = imerg.precip_month(rain, imerg.weights(place), NORMAL).filter(pl.col("year") == 2010).to_dicts()[0]
    assert row["precip_normal_mm"] == pytest.approx(125.0)
    assert row["precip_dry_mm"] == pytest.approx(56.0)


def test_sin_20_anos_completos_no_hay_normal_y_el_mes_es_partial():
    place = boundaries(("15001", imerg.cell_box(ROW, COL)))
    table = imerg.precip_month(cell_months({(ROW, COL): 50.0}, years=range(2001, 2020)), imerg.weights(place), NORMAL)
    row = table.to_dicts()[0]
    assert row["precip_normal_mm"] is None and row["normal_period"] is None and row["quality"] == "partial"


def test_un_mes_con_el_90_por_ciento_del_area_es_partial_y_con_menos_no_se_publica():
    # Diez celdas iguales en una fila; la última sin dato: el 90 % del área.
    place = boundaries(("15001", shapely.box(-73.4, 5.5, -72.4, 5.6)))
    weights = imerg.weights(place)
    values = {(ROW, COL + i): 40.0 for i in range(9)} | {(ROW, COL + 9): None}
    table = imerg.precip_month(cell_months(values), weights, NORMAL)
    assert set(table["quality"]) == {"partial"} and table["precip_mm"].to_list()[0] == pytest.approx(40.0)
    # Con dos celdas sin dato (80 %), la fila no se publica (R1).
    values[(ROW, COL + 8)] = None
    assert imerg.precip_month(cell_months(values), weights, NORMAL).is_empty()


def test_la_tasa_mensual_en_mm_por_hora_se_vuelve_el_total_del_mes():
    assert imerg.monthly_total_mm(0.1, 2024, 2) == pytest.approx(0.1 * 24 * 29)
    assert imerg.monthly_total_mm(-9999.9, 2024, 2) is None
    assert imerg.monthly_total_mm(float("nan"), 2024, 2) is None


def test_la_normal_de_imerg_vive_en_la_region_con_los_cortes_de_climate_normal():
    assert imerg.normal_from_region(build.load_region()) == NORMAL


def test_el_recuadro_cubre_todos_los_municipios():
    place = boundaries(("15001", shapely.box(-73.45, 5.45, -73.25, 5.62)), ("15238", shapely.box(-73.05, 5.80, -72.95, 5.85)))
    row0, row1, col0, col1 = imerg.window(place)
    assert (row0, col0) == imerg.cell_index(5.45, -73.45)
    assert (row1, col1) == imerg.cell_index(5.85, -72.95)


# ---------- La descarga y la caché ----------


def csv_response(area: tuple[int, int, int, int], rate=lambda row, col: 0.1) -> str:
    """Una respuesta de ejemplo de OPeNDAP en CSV (R5), con la forma que devuelve Earthdata: una línea por columna."""
    row0, row1, col0, col1 = area
    lines = ["Dataset: 3B-MO.MS.MRG.3IMERG.20240101-S000000-E235959.01.V07B.HDF5"]
    for k, col in enumerate(range(col0, col1 + 1)):
        lines.append(f"/Grid/precipitation[0][{k}], " + ", ".join(str(rate(row, col)) for row in range(row0, row1 + 1)))
    return "\n".join(lines) + "\n"


def test_la_respuesta_en_csv_se_lee_por_fila_y_columna():
    area = (ROW, ROW + 1, COL, COL + 2)
    cells = imerg.parse_csv(csv_response(area, rate=lambda row, col: float(10 * (row - ROW) + (col - COL))), area)
    assert len(cells) == 6
    assert (ROW + 1, COL + 2, 12.0) in cells and (ROW, COL, 0.0) in cells


def test_una_respuesta_incompleta_no_se_lee():
    area = (ROW, ROW + 1, COL, COL + 2)
    text = csv_response(area).splitlines()
    with pytest.raises(imerg.DownloadError, match="celdas"):
        imerg.parse_csv("\n".join(text[:-1]), area)


def test_sin_token_de_earthdata_la_descarga_lo_dice_y_no_usa_la_red(tmp_path, monkeypatch):
    from pipeline.settings import get_settings

    monkeypatch.delenv("AGROSENSE_EARTHDATA_TOKEN", raising=False)
    monkeypatch.setattr(get_settings(), "earthdata_token", None)
    monkeypatch.setattr(imerg.urllib.request, "urlopen", lambda *a, **k: pytest.fail("no debe usar la red"))
    place = boundaries(("15001", imerg.cell_box(ROW, COL)))
    with pytest.raises(imerg.DownloadError, match="AGROSENSE_EARTHDATA_TOKEN"):
        imerg.download(place, tmp_path / "imerg")


def write_cache(folder, area, months, rate=lambda row, col: 0.1):
    """Una caché de IMERG de ejemplo (R5): un CSV por mes y su manifiesto."""
    folder.mkdir(parents=True, exist_ok=True)
    for year, month in months:
        imerg.month_file(folder, year, month).write_text(csv_response(area, rate), encoding="utf-8")
    meta = {
        "downloaded_at": "2026-11-11T15:00:00+00:00",
        "product": imerg.PRODUCT,
        "window": list(area),
        "months": [f"{y}-{m:02d}" for y, m in months],
        "versions": ["V07B"],
    }
    (folder / imerg.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    return folder


def test_la_cache_da_el_total_del_mes_de_cada_celda(tmp_path):
    place = boundaries(("15001", imerg.cell_box(ROW, COL)))
    area = imerg.window(place)
    folder = write_cache(tmp_path / "imerg", area, [(2024, 2)], rate=lambda row, col: -9999.9 if col > COL else 0.1)
    cells, meta = imerg.read_cache(place, folder)
    by_cell = {(r, c): v for r, c, _, _, v in cells.iter_rows()}
    assert by_cell[(ROW, COL)] == pytest.approx(0.1 * 24 * 29)
    # Un dato que falta queda nulo, nunca relleno (R1).
    assert all(v is None for (r, c), v in by_cell.items() if c > COL)
    assert meta["months"] == ["2024-02"]


def test_una_cache_que_no_cubre_la_region_no_se_usa(tmp_path):
    place = boundaries(("15001", shapely.box(-73.4, 5.5, -73.1, 5.6)))
    write_cache(tmp_path / "imerg", (ROW, ROW, COL, COL), [(2024, 1)])
    with pytest.raises(FileNotFoundError, match="no cubre"):
        imerg.read_cache(place, tmp_path / "imerg")


def test_con_la_cache_de_imerg_se_publica_precip_month_con_su_fuente(tmp_path, monkeypatch):
    """`precip_month` sale de la caché de IMERG y de los límites de los municipios, con su fila en `sources` (R8)."""
    from tests.pipeline.test_altitud import places_cache
    from tests.pipeline.test_clima_diario import REGION

    region = {**REGION, "imerg_normal": {"first_year": 2001, "last_year": 2024, "min_years": 20}}
    monkeypatch.setattr(build, "load_region", lambda: region)
    raw = places_cache(tmp_path / "raw")
    from pipeline.sources import dane_mgn

    features, _ = dane_mgn.read_cache(region["region"]["departments"], raw)
    area = imerg.window(dane_mgn.boundaries(features))
    rain = write_cache(tmp_path / "imerg", area, [(y, 1) for y in range(2001, 2025)])
    folder = tmp_path / "published"
    manifest = build.build(folder=folder, cache=raw, power_cache=tmp_path / "sin-power", rain_cache=rain)
    table = pl.read_parquet(folder / "precip_month.parquet")
    assert set(table["municipality_id"]) == {"15407", "15646", "25899"} and table.height == 3 * 24
    assert set(table["quality"]) == {"ok"} and set(table["normal_period"]) == {"2001-2024"}
    assert table["precip_mm"].to_list()[0] == pytest.approx(round(0.1 * 24 * 31, 1))
    sources = pl.read_parquet(folder / "sources.parquet").filter(pl.col("source_id") == "imerg").to_dicts()
    assert sources and "10.5067/GPM/IMERG/3B-MONTH/07" in sources[0]["citation"]
    assert "2001-2024" in manifest["tables"]["precip_month"]["coverage"]
    build.verify(folder, region["dataset_version"])


def test_sin_la_cache_de_imerg_se_publica_lo_demas(tmp_path, monkeypatch):
    from tests.pipeline.test_clima_diario import REGION, dane_cache

    monkeypatch.setattr(build, "load_region", lambda: {**REGION, "imerg_normal": {"first_year": 2001, "last_year": 2024, "min_years": 20}})
    manifest = build.build(folder=tmp_path / "published", cache=dane_cache(tmp_path / "raw"), power_cache=tmp_path / "sin-power")
    assert "precip_month" not in manifest["tables"] and manifest["tables"]["municipalities"]["rows"] == 3


def test_el_mismo_dato_en_otro_orden_da_la_misma_tabla():
    """R4: la suma de las celdas y el promedio de los años no dependen del orden de las filas (con valores al borde del
    redondeo, sumar en otro orden cambiaba la normal en 0,1 mm)."""
    place = boundaries(("15001", shapely.box(-73.4, 5.5, -73.05, 5.6)))
    weights = imerg.weights(place)
    values = {(ROW, COL + i): 10.0 / 3 + i * 0.05 for i in range(4)}
    rain = pl.concat([cell_months(values, years=[y]).with_columns(pl.col("precip_mm") + y / 7) for y in range(2001, 2025)])
    first = imerg.precip_month(rain, weights, NORMAL)
    for seed in range(5):
        shuffled = imerg.precip_month(
            rain.sample(fraction=1.0, shuffle=True, seed=seed), weights.sample(fraction=1.0, shuffle=True, seed=seed), NORMAL
        )
        assert shuffled.equals(first)
