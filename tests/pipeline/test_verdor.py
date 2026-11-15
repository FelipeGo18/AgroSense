"""Verdor del campo por municipio con MODIS NDVI (HU-208): `ndvi_municipality` y `ndvi_municipality_normal`.

Sin red: los píxeles, el NDVI y las nubes son de ejemplo (R5), en la tesela h10v08 de la rejilla sinusoidal de MODIS.
"""

import gzip
import json

import numpy as np
import polars as pl
import pytest
import shapely

from pipeline import build
from pipeline.sources import modis_ndvi

CONFIG = modis_ndvi.Config(sample_step=1, min_valid_pct=30, first_year=2023, last_year=2025, min_years=3)
REGION_NDVI = {"sample_step": 1, "min_valid_pct": 30, "normal": {"first_year": 2023, "last_year": 2025, "min_years": 3}}
ROWS = [
    ("15001", 2023, 1, 0.5, 80.0, "ok", "modis_ndvi"),
    ("15001", 2024, 1, 0.7, 90.0, "ok", "modis_ndvi"),
    ("15001", 2025, 1, 0.6, 40.0, "ok", "modis_ndvi"),
    # Un año fuera de la normal y un periodo nublado no cuentan.
    ("15001", 2026, 1, 0.9, 95.0, "ok", "modis_ndvi"),
    ("15001", 2023, 2, 0.4, 10.0, "partial", "modis_ndvi"),
    ("15001", 2024, 2, 0.6, 70.0, "ok", "modis_ndvi"),
]


def boundaries(*places: tuple[str, shapely.Geometry]) -> pl.DataFrame:
    return pl.DataFrame(
        {"municipality_id": [p[0] for p in places], "geometry": [shapely.to_wkb(p[1]) for p in places]},
        schema={"municipality_id": pl.String, "geometry": pl.Binary},
    )


def table(rows=ROWS) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=modis_ndvi.NDVI_SCHEMA, orient="row")


def test_el_periodo_es_el_compuesto_de_16_dias_del_ano():
    assert [modis_ndvi.period_of(day) for day in (1, 16, 17, 337, 353)] == [1, 1, 2, 22, 23]


def test_el_centro_de_un_pixel_vuelve_a_su_fila_y_columna():
    """La proyección sinusoidal de MODIS: ir del píxel a la latitud y longitud y volver da el mismo píxel."""
    lat, lon = modis_ndvi.pixel_center(2000, 3000)
    row, col = modis_ndvi.pixel_of(lat, lon)
    assert (row, col) == pytest.approx((2000.5, 3000.5))
    # La región piloto (Tunja, 5,53° N y 73,36° O) cae en la tesela h10v08.
    row, col = modis_ndvi.pixel_of(5.53, -73.36)
    assert 0 <= row < modis_ndvi.PIXELS and 0 <= col < modis_ndvi.PIXELS


def test_una_region_fuera_de_la_tesela_no_se_baja():
    with pytest.raises(ValueError, match="h10v08"):
        modis_ndvi.window(boundaries(("05001", shapely.box(-76, 11, -75.9, 11.1))), 4)


def csv_response(area, ndvi=lambda row, col: 5000, reliability=lambda row, col: 0) -> str:
    """Una respuesta de ejemplo de OPeNDAP en CSV (R5): una línea por fila de cada capa, con un valor por columna."""
    row0, row1, col0, col1, step = area
    rows, cols = modis_ndvi.shape(area)
    lines = ["Dataset: MOD13Q1.A2024001.h10v08.061.dmrpp"]
    for field, value in ((modis_ndvi.NDVI_FIELD, ndvi), (modis_ndvi.RELIABILITY_FIELD, reliability)):
        for i in range(rows):
            values = ", ".join(str(value(row0 + i * step, col0 + j * step)) for j in range(cols))
            lines.append(f"{modis_ndvi.GROUP}/{field}[{i}], {values}")
    return "\n".join(lines) + "\n"


AREA = (2000, 2001, 3000, 3002, 1)


def test_la_respuesta_en_csv_se_lee_por_fila_y_columna():
    ndvi, reliability = modis_ndvi.parse_csv(
        csv_response(AREA, ndvi=lambda row, col: 10 * (row - 2000) + (col - 3000), reliability=lambda row, col: 3), AREA
    )
    assert ndvi.tolist() == [[0, 1, 2], [10, 11, 12]]
    assert reliability.tolist() == [[3, 3, 3], [3, 3, 3]]


def test_una_respuesta_incompleta_no_se_lee():
    lines = csv_response(AREA).splitlines()
    with pytest.raises(modis_ndvi.DownloadError, match="filas"):
        modis_ndvi.parse_csv("\n".join(lines[:-1]), AREA)


def test_la_mediana_solo_usa_los_pixeles_sin_nubes_y_dice_cuantos_hay():
    """Cuatro píxeles del municipio 0: uno con nube (3), uno con el valor de relleno y dos válidos (bueno y marginal)."""
    ndvi = np.array([[6000, 8000], [-3000, 4000]])
    reliability = np.array([[0, 1], [0, 3]])
    owner = np.array([[0, 0], [0, 0]])
    rows = modis_ndvi.composite_rows(ndvi, reliability, owner, ["15001"], 2024, 5, min_valid_pct=30)
    assert rows == [("15001", 2024, 5, 0.7, 50.0, "ok", "modis_ndvi")]


def test_con_pocos_pixeles_validos_es_partial_y_sin_ninguno_no_hay_fila():
    ndvi = np.array([[6000, 6000, 6000, 6000], [5000, 5000, 5000, 5000]])
    reliability = np.array([[0, 3, 3, 3], [3, 3, 3, 3]])
    owner = np.array([[0, 0, 0, 0], [1, 1, 1, 1]])
    rows = modis_ndvi.composite_rows(ndvi, reliability, owner, ["15001", "15002"], 2024, 5, min_valid_pct=30)
    # 1 de 4 píxeles válidos (25 %) es partial; el municipio todo nublado no se publica, nunca se interpola (R1).
    assert rows == [("15001", 2024, 5, 0.6, 25.0, "partial", "modis_ndvi")]


def test_un_pixel_fuera_de_los_municipios_no_cuenta():
    ndvi = np.array([[2000, 9000]])
    reliability = np.array([[0, 0]])
    owner = np.array([[0, -1]])
    assert modis_ndvi.composite_rows(ndvi, reliability, owner, ["15001"], 2024, 5, 30)[0][3:5] == (0.2, 100.0)


def test_cada_pixel_va_con_el_municipio_que_contiene_su_centro():
    lat0, lon0 = modis_ndvi.pixel_center(2000, 3000)
    lat1, lon1 = modis_ndvi.pixel_center(2000, 3002)
    # Un municipio que contiene el centro del primer píxel y otro el del tercero; el del medio no cae en ninguno.
    place = boundaries(
        ("15001", shapely.box(lon0 - 0.0005, lat0 - 0.0005, lon0 + 0.0005, lat0 + 0.0005)),
        ("15002", shapely.box(lon1 - 0.0005, lat1 - 0.0005, lon1 + 0.0005, lat1 + 0.0005)),
    )
    owner = modis_ndvi.pixel_municipality(place, (2000, 2000, 3000, 3002, 1))
    assert owner.tolist() == [[0, -1, 1]]


def test_la_normal_promedia_los_anos_ok_del_periodo_normal():
    normal = modis_ndvi.ndvi_normal(table(), CONFIG)
    by_period = {row["period"]: row for row in normal.to_dicts()}
    assert by_period[1] == {
        "municipality_id": "15001",
        "period": 1,
        "ndvi_normal": 0.6,
        "years": 3,
        "quality": "ok",
        "source_id": "modis_ndvi",
    }
    # El periodo 2 solo tiene un año ok: la normal es partial y lo dice (R1).
    assert (by_period[2]["ndvi_normal"], by_period[2]["years"], by_period[2]["quality"]) == (0.6, 1, "partial")


def test_un_periodo_sin_anos_ok_no_tiene_normal():
    rows = [("15001", 2024, 3, 0.4, 10.0, "partial", "modis_ndvi")]
    assert modis_ndvi.ndvi_normal(table(rows), CONFIG).is_empty()


def test_la_normal_no_depende_del_orden_de_las_filas():
    first = modis_ndvi.ndvi_normal(table(), CONFIG)
    for seed in range(5):
        assert modis_ndvi.ndvi_normal(table().sample(fraction=1.0, shuffle=True, seed=seed), CONFIG).equals(first)


def test_sin_el_bloque_ndvi_en_la_region_no_hay_verdor():
    assert modis_ndvi.config_from_region({}) is None
    assert modis_ndvi.config_from_region({"ndvi": REGION_NDVI}) == CONFIG


def test_el_verdor_de_la_region_baja_desde_2023():
    region = build.load_region()
    config = modis_ndvi.config_from_region(region)
    assert config is not None and config.first_year == 2023 and config.last_year == 2025


def test_sin_token_de_earthdata_la_descarga_lo_dice_y_no_usa_la_red(tmp_path, monkeypatch):
    from pipeline.settings import get_settings

    monkeypatch.setattr(get_settings(), "earthdata_token", None)
    monkeypatch.setattr(modis_ndvi.urllib.request, "urlopen", lambda *a, **k: pytest.fail("no debe usar la red"))
    lat, lon = modis_ndvi.pixel_center(2000, 3000)
    with pytest.raises(modis_ndvi.DownloadError, match="AGROSENSE_EARTHDATA_TOKEN"):
        modis_ndvi.download(boundaries(("15001", shapely.box(lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01))), CONFIG, tmp_path)


class FakeResponse:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode()

    def read(self, *args):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_un_compuesto_de_otra_version_no_se_usa(monkeypatch):
    feed = {"feed": {"entry": [{"title": "MOD13Q1.A2024001.h10v08.062.2024022131623"}]}}
    monkeypatch.setattr(modis_ndvi.urllib.request, "urlopen", lambda *a, **k: FakeResponse(feed))
    with pytest.raises(modis_ndvi.DownloadError, match="061"):
        modis_ndvi.granules(10)


def test_un_compuesto_reprocesado_queda_el_ultimo():
    """El CMR puede traer dos veces el mismo compuesto: queda el de nombre mayor (el que se generó después)."""
    feed = {
        "feed": {
            "entry": [
                {"title": "MOD13Q1.A2024017.h10v08.061.2024040000000"},
                {"title": "MOD13Q1.A2024001.h10v08.061.2024022131623"},
                {"title": "MOD13Q1.A2024001.h10v08.061.2024300000000"},
            ]
        }
    }
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(modis_ndvi.urllib.request, "urlopen", lambda *a, **k: FakeResponse(feed))
        assert modis_ndvi.granules(10) == [
            (2024, 1, "MOD13Q1.A2024001.h10v08.061.2024300000000"),
            (2024, 17, "MOD13Q1.A2024017.h10v08.061.2024040000000"),
        ]


def write_cache(folder, area, composites, ndvi=lambda row, col: 5000, reliability=lambda row, col: 0):
    """Una caché de MODIS de ejemplo (R5): un CSV comprimido por compuesto y su manifiesto."""
    folder.mkdir(parents=True, exist_ok=True)
    for year, day in composites:
        with gzip.open(modis_ndvi.composite_file(folder, year, day), "wt", encoding="utf-8") as file:
            file.write(csv_response(area, ndvi, reliability))
    meta = {
        "downloaded_at": "2026-11-14T20:33:27+00:00",
        "product": modis_ndvi.PRODUCT,
        "version": modis_ndvi.VERSION,
        "tile": modis_ndvi.TILE,
        "window": list(area),
        "composites": [f"{y}{d:03d}" for y, d in composites],
    }
    (folder / modis_ndvi.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    return folder


def test_sin_la_cache_o_con_otro_recuadro_no_se_lee(tmp_path):
    lat, lon = modis_ndvi.pixel_center(2000, 3000)
    place = boundaries(("15001", shapely.box(lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01)))
    with pytest.raises(FileNotFoundError, match="--descargar"):
        modis_ndvi.read_cache(place, CONFIG, tmp_path / "vacia")
    write_cache(tmp_path / "otra", (1, 2, 1, 2, 1), [(2024, 1)])
    with pytest.raises(FileNotFoundError, match="otro recuadro"):
        modis_ndvi.read_cache(place, CONFIG, tmp_path / "otra")


def region_with_ndvi():
    from tests.pipeline.test_clima_diario import REGION

    return {**REGION, "ndvi": REGION_NDVI}


def test_con_la_cache_de_modis_se_publica_el_verdor_con_su_fuente(tmp_path, monkeypatch):
    """`ndvi_municipality` y su normal salen de la caché de MODIS y de los límites, con su fila en `sources` (R8)."""
    from pipeline.sources import dane_mgn
    from tests.pipeline.test_altitud import places_cache

    region = region_with_ndvi()
    monkeypatch.setattr(build, "load_region", lambda: region)
    raw = places_cache(tmp_path / "raw")
    features, _ = dane_mgn.read_cache(region["region"]["departments"], raw)
    area = modis_ndvi.window(dane_mgn.boundaries(features), 1)
    composites = [(year, day) for year in (2023, 2024, 2025) for day in (1, 17)]
    cache = write_cache(tmp_path / "modis", area, composites)
    folder = tmp_path / "published"
    manifest = build.build(
        folder=folder, cache=raw, power_cache=tmp_path / "sin-power", rain_cache=tmp_path / "sin-imerg", ndvi_cache=cache
    )
    by_period = pl.read_parquet(folder / "ndvi_municipality.parquet")
    assert set(by_period["municipality_id"]) == {"15407", "15646", "25899"} and by_period.height == 3 * 6
    assert set(by_period["ndvi_median"]) == {0.5} and set(by_period["quality"]) == {"ok"}
    normal = pl.read_parquet(folder / "ndvi_municipality_normal.parquet")
    assert normal.height == 3 * 2 and set(normal["years"]) == {3} and set(normal["quality"]) == {"ok"}
    sources = pl.read_parquet(folder / "sources.parquet").filter(pl.col("source_id") == "modis_ndvi").to_dicts()
    assert sources and "10.5067/MODIS/MOD13Q1.061" in sources[0]["citation"] and "no del lote" in sources[0]["notes"]
    assert "2023-2025" in manifest["tables"]["ndvi_municipality_normal"]["coverage"]
    build.verify(folder, region["dataset_version"])


def test_sin_la_cache_de_modis_se_publica_lo_demas(tmp_path, monkeypatch):
    from tests.pipeline.test_clima_diario import dane_cache

    monkeypatch.setattr(build, "load_region", region_with_ndvi)
    manifest = build.build(
        folder=tmp_path / "published",
        cache=dane_cache(tmp_path / "raw"),
        power_cache=tmp_path / "sin-power",
        ndvi_cache=tmp_path / "sin-modis",
    )
    assert "ndvi_municipality" not in manifest["tables"] and manifest["tables"]["municipalities"]["rows"] == 3


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"municipality_id": "99999"}, "no están en `municipalities`"),
        ({"ndvi_median": 1.5}, "NDVI fuera"),
        ({"period": 24}, "NDVI fuera"),
        ({"valid_pixels_pct": 0.0}, "píxeles válidos"),
        ({"source_id": "otra"}, "no está en `sources`"),
    ],
)
def test_un_verdor_imposible_no_se_publica(change, message):
    municipalities = pl.DataFrame({"municipality_id": ["15001"]})
    sources = pl.DataFrame({"source_id": ["modis_ndvi"]})
    by_period = table().with_columns(pl.lit(value).alias(column) for column, value in change.items())
    normal = modis_ndvi.ndvi_normal(table(), CONFIG)
    with pytest.raises(build.ValidationError, match=message):
        build.validate_ndvi(by_period, normal, municipalities, sources)
