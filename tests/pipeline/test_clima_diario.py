"""Clima diario de NASA POWER (HU-041): celdas, caché, corrección por altitud y `climate_day` (R1, R4, R7, R8).

Sin red: las respuestas de POWER son de ejemplo (R5), con la forma que devuelve la API diaria por punto.
"""

import io
import json
import urllib.error
from datetime import date

import polars as pl
import pytest

from pipeline import build, schema
from pipeline.settings import get_settings
from pipeline.sources import dane, nasa_power
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION

LAPSE = {
    "temp_max_c_per_m": 0.0058,
    "temp_min_c_per_m": 0.0059,
    "source": {"source_id": "gradiente_de_ejemplo", "name": "Gradiente de ejemplo de las pruebas", "url": "https://example.org"},
}
# El periodo normal de `region.yaml` (`climate_normal`): sin él no hay `climate_month` ni temperatura media anual.
NORMAL = {"first_year": 1991, "last_year": 2020, "min_years": 24, "min_day_share": 0.9, "dry_quantile": 0.2}
REGION = {
    **SAMPLE_REGION,
    "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS},
    "temperature_lapse_rate": LAPSE,
    "climate_normal": NORMAL,
}
# Samacá y Villa de Leyva caen en la misma celda; Zipaquirá, en la de al lado.
NORTH, SOUTH = "5.500_-73.750", "5.000_-73.750"


@pytest.fixture(autouse=True)
def fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def response(cell, elevation, days):
    """Una respuesta de POWER de ejemplo (R5). `days`: {AAAAMMDD: (mínima, máxima, lluvia)}; -999 es día sin dato."""
    lat, lon = nasa_power.cell_center(cell)
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat, elevation]},
        "properties": {
            # Las variables que el ejemplo no da (humedad, radiación, viento) van con un valor de ejemplo cualquiera.
            "parameter": {
                name: {day: values[i] if i < len(values) else 0.5 for day, values in days.items()}
                for i, name in enumerate(nasa_power.PARAMETERS)
            }
        },
        "header": {"api": {"version": "v2.10.3", "name": "POWER Daily API"}, "fill_value": -999.0},
    }


DAYS = {
    "20240101": (10.0, 20.0, 1.5),
    "20240102": (-999.0, 21.0, 0.0),  # sin mínima: queda nula y el día es parcial
    "20240103": (-999.0, -999.0, -999.0),  # sin nada: no se publica
}


def write_cache(folder, cells=(NORTH, SOUTH), elevations=(2476.01, 2600.0)):
    folder.mkdir(parents=True, exist_ok=True)
    for cell, elevation in zip(cells, elevations, strict=True):
        (folder / f"{cell}.json").write_text(json.dumps(response(cell, elevation, DAYS)), encoding="utf-8")
    meta = {"downloaded_at": "2026-11-09T14:00:00+00:00", "requested_end": "2024-01-03", "cells": list(cells)}
    (folder / nasa_power.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    return folder


def municipalities(altitudes=None):
    """Los municipios de ejemplo; `altitudes` les pone una altitud, como la que traerá NASADEM (HU-206)."""
    table = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    if altitudes:
        table = table.with_columns(
            pl.col("municipality_id").replace_strict(altitudes, default=None, return_dtype=pl.Float64).alias("altitude_m")
        )
    return table


# ---------- Celdas de POWER ----------


def test_los_puntos_de_una_celda_comparten_celda_y_un_borde_las_separa():
    """Comprobado contra la API el 9 de noviembre de 2026: Úmbita y Chía dan la misma serie; La Capilla y Tenza, no."""
    assert nasa_power.cell_of(5.221, -73.457) == nasa_power.cell_of(4.867, -74.050) == "5.000_-73.750"
    assert nasa_power.cell_of(5.096, -73.444) == "5.000_-73.750"
    assert nasa_power.cell_of(5.077, -73.421) == "5.000_-73.125"
    assert nasa_power.cell_center("5.000_-73.125") == (5.0, -73.125)


def test_se_baja_una_vez_por_celda_y_no_por_municipio():
    assert nasa_power.cells(municipalities()) == [SOUTH, NORTH]
    sin_punto = municipalities().with_columns(pl.lit(None, dtype=pl.Float64).alias("lat"))
    assert nasa_power.cells(sin_punto) == []


# ---------- Caché ----------


def test_un_dia_sin_dato_de_power_queda_nulo_no_en_menos_999(tmp_path):
    series, meta = nasa_power.read_cache([NORTH, SOUTH], write_cache(tmp_path))
    north = series.filter(pl.col("cell") == NORTH)
    assert north["date"].to_list() == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    assert north["temp_min_c"].to_list() == [10.0, None, None]
    assert north["precip_mm"].to_list() == [1.5, 0.0, None]
    assert meta["elevations"] == {NORTH: 2476.01, SOUTH: 2600.0}
    assert meta["api_version"] == "v2.10.3"


def test_sin_la_cache_o_con_celdas_de_menos_dice_como_bajarla(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        nasa_power.read_cache([NORTH], tmp_path)
    write_cache(tmp_path, cells=(NORTH,), elevations=(2476.01,))
    with pytest.raises(FileNotFoundError, match="le faltan 1 celdas"):
        nasa_power.read_cache([NORTH, SOUTH], tmp_path)


# ---------- Altura de la celda y corrección por altitud ----------


def test_cada_municipio_recibe_la_altura_de_su_celda_y_su_fuente():
    table = nasa_power.with_cell_elevation(municipalities(), {NORTH: 2476.01, SOUTH: 2600.0})
    rows = {row["municipality_id"]: row for row in table.to_dicts()}
    assert rows["15646"]["climate_cell_elevation_m"] == rows["15407"]["climate_cell_elevation_m"] == 2476.01
    assert rows["25899"]["climate_cell_elevation_m"] == 2600.0
    assert rows["15646"]["source_ids"] == ["dane_divipola", "nasa_power"]


def test_un_municipio_fuera_de_las_celdas_bajadas_queda_sin_altura_ni_fuente():
    table = nasa_power.with_cell_elevation(municipalities(), {NORTH: 2476.01})
    zipaquira = table.filter(pl.col("municipality_id") == "25899").to_dicts()[0]
    assert zipaquira["climate_cell_elevation_m"] is None and zipaquira["source_ids"] == ["dane_divipola"]


def climate(altitudes, cache, lapse=LAPSE):
    """`climate_day` de los municipios de ejemplo con la caché de `cache` y las altitudes dadas."""
    series, meta = nasa_power.read_cache([NORTH, SOUTH], cache)
    table = nasa_power.with_cell_elevation(municipalities(altitudes), meta["elevations"])
    return nasa_power.climate_day(series, table, lapse)


def test_la_temperatura_se_corrige_con_la_altura_de_la_celda_y_la_del_municipio(tmp_path):
    """Samacá a 2600 m en una celda de 2476,01 m: 123,99 m más arriba, más frío (0,0059 y 0,0058 °C por metro)."""
    table = climate({"15646": 2600.0}, cache=write_cache(tmp_path))
    first = table.filter(pl.col("date") == date(2024, 1, 1)).to_dicts()[0]
    assert first["municipality_id"] == "15646"
    assert first["temp_min_c"] == round(10.0 - 0.0059 * 123.99, 2) == 9.27
    assert first["temp_max_c"] == round(20.0 - 0.0058 * 123.99, 2) == 19.28
    assert first["quality"] == "ok" and first["source_id"] == "nasa_power"


def test_un_municipio_mas_bajo_que_su_celda_queda_mas_caliente(tmp_path):
    table = climate({"15407": 2076.01}, cache=write_cache(tmp_path))
    assert table.filter(pl.col("date") == date(2024, 1, 1))["temp_min_c"].to_list() == [round(10.0 + 0.0059 * 400, 2)]


def test_un_dia_con_un_solo_dato_es_parcial_y_uno_sin_datos_no_se_publica(tmp_path):
    table = climate({"15646": 2476.01}, cache=write_cache(tmp_path))
    assert table["date"].to_list() == [date(2024, 1, 1), date(2024, 1, 2)]
    partial = table.filter(pl.col("date") == date(2024, 1, 2)).to_dicts()[0]
    assert partial["temp_min_c"] is None and partial["temp_max_c"] == 21.0 and partial["quality"] == "partial"


def test_sin_altitud_o_sin_gradiente_no_se_publica_una_temperatura_sin_corregir(tmp_path):
    cache = write_cache(tmp_path)
    assert climate({}, cache=cache).is_empty()
    assert climate({"15646": 2600.0}, lapse=None, cache=cache).is_empty()
    con_una = climate({"15646": 2600.0}, cache=cache)
    assert con_una["municipality_id"].unique().to_list() == ["15646"]


def test_climate_day_cumple_el_contrato_y_sale_igual_dos_veces(tmp_path):
    cache = write_cache(tmp_path)
    altitudes = {"15646": 2600.0, "15407": 2150.0, "25899": 2650.0}
    table = climate(altitudes, cache=cache)
    schema.check("climate_day", table)
    assert table.equals(climate(altitudes, cache=cache))
    assert table.select("municipality_id", "date").is_duplicated().sum() == 0


# ---------- Descarga ----------


class FakePower:
    """Hace de la API de POWER: responde lo de `bodies` en orden; un `Exception` en la lista se lanza."""

    def __init__(self, *bodies):
        self.bodies, self.urls = list(bodies), []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        body = self.bodies.pop(0)
        if isinstance(body, Exception):
            raise body
        return io.BytesIO(json.dumps(body).encode() if isinstance(body, dict) else body)


@pytest.fixture
def no_pause(monkeypatch):
    monkeypatch.setattr(nasa_power, "PAUSE_S", 0)


def test_baja_cada_celda_a_la_cache_y_al_final_su_manifiesto(tmp_path, monkeypatch, no_pause):
    fake = FakePower(response(SOUTH, 2600.0, DAYS), response(NORTH, 2476.01, DAYS))
    monkeypatch.setattr(nasa_power.urllib.request, "urlopen", fake)
    nasa_power.download([SOUTH, NORTH], tmp_path, end=date(2024, 1, 3))
    assert "latitude=5.000" in fake.urls[0] and "longitude=-73.750" in fake.urls[0]
    assert "start=19810101" in fake.urls[0] and "end=20240103" in fake.urls[0] and "T2M_MIN%2CT2M_MAX%2CPRECTOTCORR" in fake.urls[0]
    series, meta = nasa_power.read_cache([SOUTH, NORTH], tmp_path)
    assert meta["cells"] == [SOUTH, NORTH] and series.height == 6
    assert not list(tmp_path.glob("*.part"))


def test_una_descarga_cortada_se_reintenta(tmp_path, monkeypatch, no_pause):
    fake = FakePower(urllib.error.URLError("conexión cortada"), response(NORTH, 2476.01, DAYS))
    monkeypatch.setattr(nasa_power.urllib.request, "urlopen", fake)
    nasa_power.download([NORTH], tmp_path, end=date(2024, 1, 3))
    assert len(fake.urls) == 2 and (tmp_path / f"{NORTH}.json").exists()


@pytest.mark.parametrize(
    "bad",
    [
        b"x" * 2048,  # pasa del tamaño máximo
        b'{"geometry": {}, "properties": {"parameter": {}}}',  # no trae las variables pedidas
    ],
)
def test_una_respuesta_mala_no_deja_cache_y_el_error_dice_la_celda(tmp_path, monkeypatch, no_pause, bad):
    monkeypatch.setenv("AGROSENSE_POWER_MAX_MB", "0.001")
    monkeypatch.setattr(nasa_power.urllib.request, "urlopen", FakePower(*[bad] * nasa_power.ATTEMPTS))
    with pytest.raises(nasa_power.DownloadError, match=NORTH):
        nasa_power.download([NORTH], tmp_path, end=date(2024, 1, 3))
    assert list(tmp_path.iterdir()) == []


def test_los_limites_de_la_descarga_salen_del_env(monkeypatch):
    monkeypatch.setenv("AGROSENSE_POWER_TIMEOUT_S", "30")
    monkeypatch.setenv("AGROSENSE_POWER_MAX_MB", "5")
    settings = get_settings()
    assert (settings.power_timeout_s, settings.power_max_mb) == (30, 5)


# ---------- Fuente y publicación ----------


def test_la_fuente_dice_que_es_un_reanalisis_su_celda_y_la_cita_de_power(tmp_path):
    series, meta = nasa_power.read_cache([NORTH, SOUTH], write_cache(tmp_path))
    row = nasa_power.source(series, meta)
    assert row["source_id"] == "nasa_power" and "reanálisis" in row["notes"] and "0,625°" in row["notes"]
    assert row["period_covered"] == "Del 2024-01-01 al 2024-01-02"
    # La cita va en `citation`, no en `license` (R8).
    assert "POWER Project's Daily 2.10.3 version on 2026/11/09" in row["citation"]
    assert row["citation"].startswith("The data was obtained from National Aeronautics and Space Administration (NASA)")
    assert "The data was obtained" not in row["license"]


def test_sin_version_de_la_api_la_cita_no_nombra_ninguna(tmp_path):
    """Si la respuesta de POWER no trae la versión, no se inventa una (R5)."""
    series, meta = nasa_power.read_cache([NORTH, SOUTH], write_cache(tmp_path))
    meta = {**meta, "api_version": None}
    citation = nasa_power.source(series, meta)["citation"]
    assert "version" not in citation and "2.x" not in citation
    assert citation.startswith("The data was obtained from National Aeronautics and Space Administration (NASA)")


def sources_with_climate(tmp_path):
    series, meta = nasa_power.read_cache([NORTH, SOUTH], write_cache(tmp_path / "power"))
    rows = [dane.source(SAMPLE_META), nasa_power.source(series, meta), LAPSE["source"]]
    return pl.DataFrame(rows), meta


def test_publica_climate_day_con_su_fila_en_el_manifiesto(tmp_path):
    sources, meta = sources_with_climate(tmp_path)
    table = nasa_power.with_cell_elevation(municipalities({"15646": 2600.0}), meta["elevations"])
    day = climate({"15646": 2600.0}, cache=tmp_path / "power")
    manifest = build.publish(REGION, table, sources, tmp_path / "published", climate=day)
    assert manifest["tables"]["climate_day"] == {"rows": 2, "coverage": "1 municipios con altitud, del 2024-01-01 al 2024-01-02"}
    assert pl.read_parquet(tmp_path / "published" / "climate_day.parquet").equals(day)


def test_sin_filas_de_clima_no_se_escribe_la_tabla(tmp_path):
    sources, _ = sources_with_climate(tmp_path)
    empty = pl.DataFrame(schema=nasa_power.DAY_SCHEMA)
    manifest = build.publish(REGION, municipalities(), sources, tmp_path / "published", climate=empty)
    assert "climate_day" not in manifest["tables"] and not (tmp_path / "published" / "climate_day.parquet").exists()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (pl.lit("99999").alias("municipality_id"), "no están en `municipalities`"),
        (pl.lit("inventada").alias("source_id"), "inventada"),
    ],
)
def test_un_clima_que_no_cuadra_no_se_publica(tmp_path, change, message):
    sources, _ = sources_with_climate(tmp_path)
    day = climate({"15646": 2600.0}, cache=tmp_path / "power").with_columns(change)
    with pytest.raises(build.ValidationError, match=message):
        build.publish(REGION, municipalities(), sources, tmp_path / "published", climate=day)
    assert not (tmp_path / "published" / "manifest.json").exists()


def dane_cache(folder):
    from tests.pipeline.test_municipios import feature_collection

    folder.mkdir(parents=True, exist_ok=True)
    (folder / dane.ROWS_FILE).write_text(json.dumps(SAMPLE_MUNICIPALITIES), encoding="utf-8")
    (folder / dane.META_FILE).write_text(json.dumps(SAMPLE_META), encoding="utf-8")
    for department, ids in (("15", ["15407", "15646"]), ("25", ["25899"])):
        (folder / build.dane_mgn._file(department)).write_text(json.dumps(feature_collection(ids)), encoding="utf-8")
    return folder


def no_network(*args, **kwargs):
    raise AssertionError("no debe usar la red")


def test_sin_la_cache_de_power_se_publica_lo_demas_sin_clima(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "load_region", lambda: {**REGION})
    monkeypatch.setattr(nasa_power.urllib.request, "urlopen", no_network)
    manifest = build.build(
        folder=tmp_path / "published",
        cache=dane_cache(tmp_path / "raw"),
        market_cache=tmp_path / "sin-sipsa",
        power_cache=tmp_path / "sin-clima",
    )
    assert manifest["tables"]["municipalities"]["rows"] == 3 and "climate_day" not in manifest["tables"]
    published = pl.read_parquet(tmp_path / "published" / "municipalities.parquet")
    assert published["climate_cell_elevation_m"].null_count() == 3
    assert "nasa_power" not in pl.read_parquet(tmp_path / "published" / "sources.parquet")["source_id"].to_list()


def test_con_la_cache_de_power_y_sin_altitud_publica_la_altura_de_la_celda_pero_no_el_clima(tmp_path, monkeypatch):
    """Hoy: la altitud de los municipios llega con NASADEM (HU-206). Hasta entonces, `climate_day` no se publica (R1)."""
    monkeypatch.setattr(build, "load_region", lambda: {**REGION})
    monkeypatch.setattr(nasa_power.urllib.request, "urlopen", no_network)
    folder = tmp_path / "published"
    manifest = build.build(
        folder=folder, cache=dane_cache(tmp_path / "raw"), market_cache=tmp_path / "sin-sipsa", power_cache=write_cache(tmp_path / "power")
    )
    assert "climate_day" not in manifest["tables"]
    published = pl.read_parquet(folder / "municipalities.parquet")
    assert published["climate_cell_elevation_m"].to_list() == [2476.01, 2476.01, 2600.0]
    assert {"nasa_power", "gradiente_de_ejemplo"} <= set(pl.read_parquet(folder / "sources.parquet")["source_id"].to_list())


def test_el_gradiente_de_la_region_tiene_valor_y_fuente():
    """El gradiente real de `pipeline/region.yaml`: región Andina, Chaves y Jaramillo (1999), tabla 3 (R8)."""
    lapse = build.load_region()["temperature_lapse_rate"]
    assert (lapse["temp_max_c_per_m"], lapse["temp_min_c_per_m"]) == (0.0058, 0.0059)
    assert lapse["source"]["source_id"] == "cenicafe_lapse_rate" and lapse["source"]["url"].startswith("https://")
    assert lapse["source"]["citation"].startswith("Chaves Córdoba, B. y Jaramillo Robledo, A. (1999)")
