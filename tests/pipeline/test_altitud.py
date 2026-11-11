"""Altitud y pendiente de NASADEM (HU-206): mosaicos, rejilla de 250 m, municipios y publicación (R1, R4, R7, R8).

Sin red: los mosaicos son de ejemplo (R5), con el tamaño y la georreferencia de los de NASADEM en Planetary Computer.
"""

import io
import json
import math

import numpy as np
import polars as pl
import pytest
import shapely
import shapely.geometry
import tifffile

from pipeline import build
from pipeline.settings import get_settings
from pipeline.sources import dane_mgn, nasadem
from tests.conftest import SAMPLE_MUNICIPALITIES
from tests.pipeline.test_clima_diario import REGION, dane_cache, no_network, write_cache


@pytest.fixture(autouse=True)
def fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def geotiff(elevation: np.ndarray, lat: int, lon: int) -> bytes:
    """Un mosaico de ejemplo (R5) con la georreferencia de NASADEM: píxel de 1 segundo, centro en segundos enteros."""
    extratags = [
        (33550, "d", 3, (1 / 3600, 1 / 3600, 0.0), True),  # ModelPixelScale
        (33922, "d", 6, (0.0, 0.0, 0.0, float(lon), float(lat + 1), 0.0), True),  # ModelTiepoint
        # GeoKeyDirectory: modelo geográfico (1024 = 2), punto de amarre en el centro del píxel (1025 = 2), WGS84.
        (34735, "H", 16, (1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 2, 2048, 0, 1, 4326), True),
    ]
    out = io.BytesIO()
    tifffile.imwrite(out, elevation.astype(np.int16), compression="zlib", extratags=extratags)
    return out.getvalue()


def flat(value: int) -> np.ndarray:
    return np.full((nasadem.PIXELS, nasadem.PIXELS), value, dtype=np.int16)


def cell_id(lat: float, lon: float) -> str:
    """La llave del contrato («La rejilla de 250 m»), calculada aparte del adaptador."""
    return f"{math.floor((90 - lat) / 0.0025)}_{math.floor((lon + 180) / 0.0025)}"


# ---------- Mosaicos ----------


def test_el_nombre_del_mosaico_es_su_esquina_suroeste():
    assert nasadem.tile_name(5, -74) == "n05w074"
    assert nasadem.tile_name(-1, 10) == "s01e010"


def test_un_mosaico_se_lee_con_los_pixeles_vacios_en_nulo(tmp_path):
    elevation = flat(2600)
    elevation[0, 0] = nasadem.NODATA
    path = tmp_path / "n05w074.tif"
    path.write_bytes(geotiff(elevation, 5, -74))
    read = nasadem.read_tile(path, 5, -74)
    assert np.isnan(read[0, 0]) and read[1, 1] == 2600


@pytest.mark.parametrize(
    ("size", "lat", "lon", "message"),
    [(nasadem.PIXELS, 6, -74, "empieza en"), (10, 5, -74, "mide")],
    ids=["otro-grado", "otro-tamano"],
)
def test_un_mosaico_que_no_es_el_esperado_no_se_lee(tmp_path, size, lat, lon, message):
    path = tmp_path / "mosaico.tif"
    path.write_bytes(geotiff(np.full((size, size), 2600), 5, -74))
    with pytest.raises(nasadem.TileError, match=message):
        nasadem.read_tile(path, lat, lon)


# ---------- La rejilla de 250 m ----------


def test_cada_celda_son_9_por_9_pixeles_y_su_llave_es_la_del_contrato():
    cells = nasadem.tile_cells(flat(2600).astype(np.float32), 5, -74)
    assert cells.height == 400 * 400 and cells["cell_id"].n_unique() == cells.height
    assert set(cells["pixels"].to_list()) == {81}
    # Tunja, con la llave calculada como dice el contrato.
    tunja = cells.filter(pl.col("cell_id") == cell_id(5.53988, -73.355539)).to_dicts()[0]
    assert (tunja["altitude_m"], tunja["slope_pct"]) == (2600.0, 0.0)
    assert abs(tunja["lat"] - 5.53988) < 0.0025 and abs(tunja["lon"] + 73.355539) < 0.0025
    # Los centros quedan dentro del grado del mosaico.
    assert cells["lat"].min() > 5 and cells["lat"].max() < 6 and cells["lon"].min() > -74 and cells["lon"].max() < -73


def test_la_altitud_es_el_promedio_y_la_pendiente_se_mide_a_30_m():
    # Baja 1 m por cada píxel hacia el sur: 1 m cada 30,7 m (110 574 m por grado / 3600), un 3,3 % de pendiente.
    rows = np.arange(nasadem.PIXELS, dtype=np.float32)[:, None]
    elevation = np.broadcast_to(3000 - rows, (nasadem.PIXELS, nasadem.PIXELS)).copy()
    cells = nasadem.tile_cells(elevation, 5, -74)
    first = cells.filter(pl.col("cell_id") == cell_id(5.9999, -73.9999)).to_dicts()[0]
    assert first["altitude_m"] == 3000 - 4  # el promedio de las filas 0 a 8
    assert first["slope_pct"] == pytest.approx(100 / (nasadem.M_PER_DEG_LAT / 3600), abs=0.05)


def test_un_pixel_vacio_no_cuenta_y_una_celda_sin_pixeles_queda_nula():
    elevation = flat(2600).astype(np.float32)
    elevation[0:9, 0:9] = np.nan  # la celda de la esquina noroeste, toda vacía
    elevation[0, 20] = np.nan  # un píxel de la tercera celda
    cells = nasadem.tile_cells(elevation, 5, -74)
    empty = cells.filter(pl.col("cell_id") == cell_id(5.9999, -73.9999)).to_dicts()[0]
    assert (empty["altitude_m"], empty["slope_pct"], empty["pixels"]) == (None, None, 0)
    third = cells.filter(pl.col("cell_id") == cell_id(5.9999, -73.9999 + 2 * 0.0025)).to_dicts()[0]
    assert (third["altitude_m"], third["pixels"]) == (2600.0, 80)


def boundaries(squares: dict[str, tuple[float, float, float, float]]) -> pl.DataFrame:
    return pl.DataFrame({"municipality_id": list(squares), "geometry": [shapely.to_wkb(shapely.box(*box)) for box in squares.values()]})


def test_cada_celda_va_con_el_municipio_que_contiene_su_centro():
    cells = nasadem.tile_cells(flat(2600).astype(np.float32), 5, -74)
    assigned = nasadem.assign(cells, boundaries({"15001": (-73.40, 5.50, -73.30, 5.60), "15646": (-73.50, 5.40, -73.45, 5.45)}))
    counts = dict(assigned.group_by("municipality_id").len().iter_rows())
    # 0,1° = 40 celdas por lado; 0,05° = 20. Las celdas de fuera de la región no se publican.
    assert counts == {"15001": 1600, "15646": 400}


def test_la_altitud_del_municipio_es_la_de_su_cabecera_y_la_pendiente_la_mediana():
    """Decidido por Felipe el 10 de noviembre de 2026: la altitud corrige la temperatura del pueblo y del valle; la
    pendiente es la de todo el terreno."""
    town = cell_id(5.5399, -73.3555)
    cells = pl.DataFrame(
        {
            "cell_id": [town, "1_1", "1_2", "2_1"],
            "municipality_id": ["15001"] * 3 + ["15646"],
            "altitude_m": [2711.0, 2600.0, 3500.0, None],
            "slope_pct": [5.0, 10.0, 40.0, None],
        }
    )
    municipalities = pl.DataFrame({"municipality_id": ["15001", "15646"], "lat": [5.5399, 5.4925], "lon": [-73.3555, -73.4856]})
    terrain = {row["municipality_id"]: row for row in nasadem.municipality_terrain(cells, municipalities).to_dicts()}
    assert terrain["15001"] == {"municipality_id": "15001", "altitude_m": 2711.0, "slope_pct": 10.0, "cells": 3}
    # Sin celda de la cabecera con dato, la altitud queda nula: no se rellena con otra celda (R1).
    assert terrain["15646"]["altitude_m"] is None and terrain["15646"]["cells"] == 0


# ---------- Descarga ----------


class FakeBlob:
    """Hace de Planetary Computer: el permiso de lectura y después los mosaicos de `tiles`, en orden."""

    def __init__(self, *tiles):
        self.tiles, self.urls = list(tiles), []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        if request.full_url == nasadem.SAS_URL:
            return io.BytesIO(json.dumps({"token": "se=ejemplo&sig=ejemplo"}).encode())
        tile = self.tiles.pop(0)
        if isinstance(tile, Exception):
            raise tile
        return io.BytesIO(tile)


@pytest.fixture(scope="module")
def tile_n05w074():
    return geotiff(flat(2600), 5, -74)


def test_baja_cada_mosaico_y_al_final_su_manifiesto(tmp_path, monkeypatch, tile_n05w074):
    monkeypatch.setattr(nasadem, "PAUSE_S", 0)
    fake = FakeBlob(OSError("conexión cortada"), tile_n05w074)
    monkeypatch.setattr(nasadem.urllib.request, "urlopen", fake)
    nasadem.download([(5, -74)], tmp_path)
    assert fake.urls[1].endswith("NASADEM_HGT_n05w074.tif?se=ejemplo&sig=ejemplo")
    # Se reintentó con un permiso nuevo.
    assert fake.urls.count(nasadem.SAS_URL) == 2
    meta = json.loads((tmp_path / nasadem.META_FILE).read_text(encoding="utf-8"))
    assert meta["tiles"] == ["n05w074"] and (tmp_path / "n05w074.tif").exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["n05w074.tif", nasadem.META_FILE]


def test_un_mosaico_malo_no_deja_cache_y_el_error_dice_cual(tmp_path, monkeypatch):
    monkeypatch.setattr(nasadem, "PAUSE_S", 0)
    wrong = geotiff(flat(2600), 6, -74)  # otro grado
    monkeypatch.setattr(nasadem.urllib.request, "urlopen", FakeBlob(*[wrong] * nasadem.ATTEMPTS))
    with pytest.raises(nasadem.DownloadError, match="n05w074"):
        nasadem.download([(5, -74)], tmp_path)
    assert list(tmp_path.iterdir()) == []


# ---------- Publicación ----------


@pytest.fixture(scope="module")
def dem_cache(tmp_path_factory):
    """Mosaicos de ejemplo planos, a 2600 m, que cubren los municipios de ejemplo."""
    folder = tmp_path_factory.mktemp("nasadem")
    names = []
    for lat, lon in ((4, -75), (4, -74), (5, -75), (5, -74)):
        name = nasadem.tile_name(lat, lon)
        (folder / f"{name}.tif").write_bytes(geotiff(flat(2600), lat, lon))
        names.append(name)
    meta = {"downloaded_at": "2026-11-10T13:00:00+00:00", "tiles": names}
    (folder / nasadem.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    return folder


def places_cache(folder):
    """La caché de DIVIPOLA de ejemplo con límites en su lugar real: un cuadrado de 0,1° alrededor del punto de cada
    municipio (ejemplo, R5). Los de `dane_cache` están cerca de (0, 0), donde no hay mosaicos de ejemplo."""
    folder = dane_cache(folder)
    points = {
        row["cod_mpio"]: (float(row["latitud"].replace(",", ".")), float(row["longitud"].replace(",", ".")))
        for row in SAMPLE_MUNICIPALITIES
    }
    for department, ids in (("15", ["15407", "15646"]), ("25", ["25899"])):
        features = [
            {
                "type": "Feature",
                "properties": {"mpio_cdpmp": mid, "mpio_cnmbre": "X"},
                "geometry": shapely.geometry.mapping(
                    shapely.box(points[mid][1] - 0.05, points[mid][0] - 0.05, points[mid][1] + 0.05, points[mid][0] + 0.05)
                ),
            }
            for mid in ids
        ]
        (folder / dane_mgn._file(department)).write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return folder


def test_con_la_altitud_se_publican_la_rejilla_y_el_clima_diario(tmp_path, monkeypatch, dem_cache):
    """Con NASADEM, `climate_day` sale corregida por altitud (HU-041, HU-044) y `grid_cells` con la altitud y la pendiente."""
    monkeypatch.setattr(build, "load_region", lambda: {**REGION})
    monkeypatch.setattr(nasadem.urllib.request, "urlopen", no_network)
    folder = tmp_path / "published"
    manifest = build.build(
        folder=folder, cache=places_cache(tmp_path / "raw"), power_cache=write_cache(tmp_path / "power"), dem_cache=dem_cache
    )
    assert {"grid_cells", "climate_day"} <= set(manifest["tables"])
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    assert municipalities["altitude_m"].to_list() == [2600.0, 2600.0, 2600.0]
    assert municipalities["slope_pct"].to_list() == [0.0, 0.0, 0.0]
    assert all("nasadem" in ids for ids in municipalities["source_ids"].to_list())
    grid = pl.read_parquet(folder / "grid_cells.parquet")
    # Los límites de ejemplo son cuadrados de 0,1°: unas 40 × 40 celdas cada uno, sin repetir ninguna.
    counts = dict(grid.group_by("municipality_id").len().iter_rows())
    assert set(counts) == {"15407", "15646", "25899"} and all(1560 <= n <= 1640 for n in counts.values())
    assert grid["cell_id"].n_unique() == grid.height
    # Sin el suelo (HU-181), a cada celda le falta una fuente: `partial`, como dice el contrato (R1).
    assert set(grid["quality"].to_list()) == {"partial"} and grid["ph"].null_count() == grid.height
    # Zipaquirá (2600 m) está a la altura de su celda de POWER: su temperatura no cambia.
    zipaquira = pl.read_parquet(folder / "climate_day.parquet").filter(pl.col("municipality_id") == "25899")
    assert zipaquira.filter(pl.col("date") == pl.date(2024, 1, 1))["temp_min_c"].to_list() == [10.0]
    assert "nasadem" in pl.read_parquet(folder / "sources.parquet")["source_id"].to_list()
    build.verify(folder, REGION["dataset_version"])


def test_sin_la_cache_de_nasadem_no_se_publica_el_clima_diario(tmp_path, monkeypatch):
    """Sin altitud no se corrige la temperatura, y no se publica sin corregir (R1)."""
    monkeypatch.setattr(build, "load_region", lambda: {**REGION})
    folder = tmp_path / "published"
    manifest = build.build(folder=folder, cache=places_cache(tmp_path / "raw"), power_cache=write_cache(tmp_path / "power"))
    assert "grid_cells" not in manifest["tables"] and "climate_day" not in manifest["tables"]
    assert pl.read_parquet(folder / "municipalities.parquet")["altitude_m"].null_count() == 3


def test_el_terreno_publicado_en_el_repositorio_cumple_el_contrato():
    """El dataset de la demo: todos los municipios con altitud y pendiente de NASADEM."""
    folder = build.PUBLISHED
    if not (folder / "grid_cells.parquet").exists():
        pytest.skip("data/published no trae la rejilla en esta imagen")
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    assert municipalities["altitude_m"].null_count() == 0 and municipalities["slope_pct"].null_count() == 0
    grid = pl.scan_parquet(folder / "grid_cells.parquet").select("municipality_id").unique().collect()
    assert set(grid["municipality_id"].to_list()) == set(municipalities["municipality_id"].to_list())
