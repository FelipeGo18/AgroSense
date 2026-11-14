"""Suelo de la región con SoilGrids (HU-181): `grid_cells` y `soil_municipality` (R1, R4, R7, R8).

Sin red: los mosaicos son de ejemplo (R5), GeoTIFF con la forma y la georreferencia que devuelve el WCS de SoilGrids.
"""

import json

import numpy as np
import polars as pl
import pytest
import tifffile

from pipeline import build, schema
from pipeline.sources import soilgrids

LAT, LON = 5, -74  # el mosaico de 5° a 6° N y de 74° a 73° O
N = soilgrids.CELLS_PER_DEGREE


def write_tile(folder, values=lambda prop, depth, stat: 50, lat=LAT, lon=LON):
    """Un mosaico de ejemplo (R5): cada mapa con un valor constante, en las unidades de SoilGrids."""
    name = soilgrids.tile_name(lat, lon)
    (folder / name).mkdir(parents=True, exist_ok=True)
    tags = [
        (33550, "d", 3, (schema.GRID_STEP_DEG, schema.GRID_STEP_DEG, 0.0), False),
        (33922, "d", 6, (0.0, 0.0, 0.0, float(lon), float(lat + 1), 0.0), False),
    ]
    for prop, coverage in soilgrids.coverages():
        _, depth, stat = coverage.split("_")
        array = values(prop, depth, stat)
        if np.isscalar(array):
            array = np.full((N, N), array, dtype=np.int16)
        tifffile.imwrite(folder / name / f"{coverage}.tif", array.astype(np.int16), extratags=tags)
    meta = {"downloaded_at": "2026-11-13T15:00:00+00:00", "tiles": [name], "coverages": [c for _, c in soilgrids.coverages()]}
    (folder / soilgrids.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    return folder


# Valores de ejemplo de un suelo andino, en las unidades de SoilGrids: pH × 10, carbono en dg/kg, nitrógeno en cg/kg y
# fracciones en g/kg.
TYPICAL = {"phh2o": 55, "soc": 300, "nitrogen": 250, "clay": 280, "sand": 400, "silt": 320}


def typical(prop, depth, stat):
    offset = {"Q0.05": -5, "Q0.95": 5}.get(stat, 0)
    return TYPICAL[prop] + offset * (10 if prop == "soc" else 1)


@pytest.mark.parametrize(
    ("clay", "sand", "silt", "expected"),
    [
        (28, 40, 32, "franco arcilloso"),
        (5, 90, 5, "arenoso"),
        (8, 80, 12, "arenoso franco"),
        (10, 65, 25, "franco arenoso"),
        (18, 42, 40, "franco"),
        (15, 25, 60, "franco limoso"),
        (5, 5, 90, "limoso"),
        (25, 55, 20, "franco arcillo arenoso"),
        (32, 10, 58, "franco arcillo limoso"),
        (38, 50, 12, "arcillo arenoso"),
        (45, 5, 50, "arcillo limoso"),
        (55, 20, 25, "arcilloso"),
    ],
)
def test_la_clase_de_textura_es_la_del_triangulo_del_usda(clay, sand, silt, expected):
    assert soilgrids.texture_class(clay, sand, silt) == expected


def test_sin_una_fraccion_no_hay_clase():
    assert soilgrids.texture_class(None, 40, 30) is None


def test_de_0_a_30_cm_es_el_promedio_ponderado_por_el_grosor_de_cada_capa():
    maps = {"0-5cm": np.full((2, 2), 50), "5-15cm": np.full((2, 2), 60), "15-30cm": np.full((2, 2), 70)}
    assert soilgrids.layered(maps, 10)[0, 0] == pytest.approx((5 * 5.0 + 10 * 6.0 + 15 * 7.0) / 30)


def test_un_pixel_sin_dato_en_una_capa_deja_la_propiedad_nula():
    maps = {"0-5cm": np.array([[50, 0]]), "5-15cm": np.array([[60, 60]]), "15-30cm": np.array([[70, 70]])}
    result = soilgrids.layered(maps, 10)
    assert not np.isnan(result[0, 0]) and np.isnan(result[0, 1])


def test_el_mosaico_trae_cada_celda_con_su_id_y_sus_unidades(tmp_path):
    cache = write_tile(tmp_path / "soilgrids", typical)
    soil, meta = soilgrids.read_cache([(LAT, LON)], cache)
    assert soil.height == N * N and meta["tiles"] == ["n05w074"]
    # La esquina noroeste del mosaico es la celda que contiene (5,999°, −73,999°).
    corner = soil.filter(pl.col("cell_id") == schema.cell_id(5.999, -73.999)).to_dicts()[0]
    assert (corner["ph"], corner["ph_p05"], corner["ph_p95"]) == (5.5, 5.0, 6.0)
    assert (corner["soc_g_kg"], corner["soc_p05"], corner["soc_p95"]) == (30.0, 25.0, 35.0)
    assert (corner["nitrogen_g_kg"], corner["clay_pct"], corner["sand_pct"], corner["silt_pct"]) == (2.5, 28.0, 40.0, 32.0)
    assert schema.cell_id(5.001, -73.001) in set(soil["cell_id"])


def test_un_mosaico_con_otra_esquina_no_se_lee(tmp_path):
    cache = write_tile(tmp_path / "soilgrids", typical, lat=6)
    path = cache / soilgrids.tile_name(6, LON) / "phh2o_0-5cm_mean.tif"
    with pytest.raises(soilgrids.TileError, match="esquina"):
        soilgrids.read_tile(path, LAT, LON)


def test_sin_la_cache_completa_no_se_lee(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        soilgrids.read_cache([(LAT, LON)], tmp_path / "vacia")


def grid(cells: list[tuple[str, float, float, str]]) -> pl.DataFrame:
    """Una `grid_cells` de NASADEM de ejemplo (R5), sin suelo, como la deja `nasadem.grid_cells`."""
    rows = []
    for municipality_id, lat, lon, _ in cells:
        rows.append(
            {
                "cell_id": schema.cell_id(lat, lon),
                "lat": lat,
                "lon": lon,
                "municipality_id": municipality_id,
                "altitude_m": 2600.0,
                "slope_pct": 8.0,
                **dict.fromkeys(soilgrids.NUMERIC),
                "texture_class": None,
                "quality": "partial",
                "source_ids": ["nasadem"],
            }
        )
    return schema.typed("grid_cells", pl.DataFrame(rows))


def test_la_celda_con_suelo_y_altitud_es_ok_y_cita_las_dos_fuentes(tmp_path):
    soil, _ = soilgrids.read_cache([(LAT, LON)], write_tile(tmp_path / "soilgrids", typical))
    table = soilgrids.with_soil(grid([("15001", 5.55, -73.35, "")]), soil)
    schema.check("grid_cells", schema.typed("grid_cells", table))
    row = table.to_dicts()[0]
    assert (row["ph"], row["texture_class"], row["quality"], row["source_ids"]) == (5.5, "franco arcilloso", "ok", ["nasadem", "soilgrids"])


def test_una_celda_sin_suelo_queda_nula_y_partial(tmp_path):
    # El pH vale 0 en toda la capa de 0 a 5 cm: «sin dato» (agua o zona urbana).
    def values(prop, depth, stat):
        return 0 if prop == "phh2o" and depth == "0-5cm" else typical(prop, depth, stat)

    soil, _ = soilgrids.read_cache([(LAT, LON)], write_tile(tmp_path / "soilgrids", values))
    row = soilgrids.with_soil(grid([("15001", 5.55, -73.35, "")]), soil).to_dicts()[0]
    assert row["ph"] is None and row["soc_g_kg"] == 30.0 and row["quality"] == "partial"


def test_el_suelo_del_municipio_es_la_mediana_de_sus_celdas_y_la_textura_mas_frecuente(tmp_path):
    # Tres celdas: la arcilla cambia con la fila del mosaico, la de arriba es más arenosa.
    def values(prop, depth, stat):
        if prop not in ("clay", "sand"):
            return typical(prop, depth, stat)
        array = np.full((N, N), TYPICAL[prop], dtype=np.int16)
        array[0, :] = 100 if prop == "clay" else 650  # fila de arriba: franco arenoso
        return array

    soil, _ = soilgrids.read_cache([(LAT, LON)], write_tile(tmp_path / "soilgrids", values))
    cells = [("15001", 5.9988, -73.9, ""), ("15001", 5.55, -73.35, ""), ("15001", 5.45, -73.25, "")]
    table = soilgrids.soil_municipality(soilgrids.with_soil(grid(cells), soil))
    schema.check("soil_municipality", schema.typed("soil_municipality", table))
    row = table.to_dicts()[0]
    assert (row["clay_pct"], row["texture_class"], row["cells"], row["quality"]) == (28.0, "franco arcilloso", 3, "ok")


def test_un_municipio_con_pocas_celdas_con_suelo_es_partial_y_sin_ninguna_no_tiene_fila(tmp_path):
    def values(prop, depth, stat):
        array = np.full((N, N), typical(prop, depth, stat), dtype=np.int16)
        array[:, 200:] = 0  # la mitad oriental del mosaico, sin dato
        return array

    soil, _ = soilgrids.read_cache([(LAT, LON)], write_tile(tmp_path / "soilgrids", values))
    cells = [("15001", 5.5, -73.9, ""), ("15001", 5.5, -73.2, ""), ("25001", 5.5, -73.1, "")]
    table = soilgrids.soil_municipality(soilgrids.with_soil(grid(cells), soil))
    assert table["municipality_id"].to_list() == ["15001"]
    assert (table["cells"][0], table["quality"][0]) == (1, "partial")


def test_un_ph_fuera_de_0_a_14_no_se_publica(tmp_path):
    soil, _ = soilgrids.read_cache([(LAT, LON)], write_tile(tmp_path / "soilgrids", typical))
    table = soilgrids.soil_municipality(soilgrids.with_soil(grid([("15001", 5.55, -73.35, "")]), soil))
    municipalities = pl.DataFrame({"municipality_id": ["15001"]})
    sources = pl.DataFrame({"source_id": ["soilgrids"]})
    build.validate_soil(table, municipalities, sources)
    with pytest.raises(build.ValidationError, match="suelo"):
        build.validate_soil(table.with_columns(pl.lit(15.0).alias("ph")), municipalities, sources)


def test_lo_publicado_en_el_repositorio_tiene_el_suelo_de_casi_todos_los_municipios():
    folder = build.PUBLISHED
    if not (folder / "soil_municipality.parquet").exists():
        pytest.skip("data/published no trae soil_municipality en esta imagen")
    soil = pl.read_parquet(folder / "soil_municipality.parquet")
    assert soil.height >= 230 and soil["ph"].is_between(3.5, 8.5).all()
    assert set(soil["texture_class"].drop_nulls()) <= {
        "arenoso", "arenoso franco", "franco arenoso", "franco", "franco limoso", "limoso", "franco arcillo arenoso",
        "franco arcilloso", "franco arcillo limoso", "arcillo arenoso", "arcillo limoso", "arcilloso",
    }  # fmt: skip
