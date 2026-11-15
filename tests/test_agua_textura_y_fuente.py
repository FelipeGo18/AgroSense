"""Lo que la API le pasa al balance hídrico de la señal de agua (HU-071): la textura del suelo del lote o del municipio,
y el clima de la fuente de lluvia que calcula la señal, nunca el de contraste (R1).

Las celdas de la rejilla son sintéticas y los balances son de ejemplo (R5). El dataset es una copia del de ejemplo del
repositorio (`data/examples/`, rotulado como ejemplo), con la lluvia rotulada con la fuente de su tabla
(`tests/ejemplos_con_fuente.py`): Samacá, con suelo «franco arcilloso». «Hoy» queda fijo en el 14 de noviembre de 2026
en la región (R4).
"""

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest
from fastapi.testclient import TestClient

from backend.api import window_signals as window_signals_module
from backend.api.lot_terrain import lot_texture, zone_texture
from backend.api.main import app
from backend.api.water_signals import RainNormal, WaterMonth, ZoneWater
from backend.config.settings import get_settings
from backend.dataset import Grid, get_dataset
from backend.engine.stages import StageSpan, crop_window
from backend.engine.water_signal import RainSource, WaterBalanceSummary
from common import region
from common.grid import GRID_STEP_DEG as STEP
from common.grid import cell_id, cell_key
from tests.ejemplos_con_fuente import EXAMPLES, examples_with_sources

SAMACA = "15646"
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
APRIL, NOVEMBER = "2027-04-01", "2026-11-01"
EXAMPLE_BALANCE = WaterBalanceSummary(need_mm=400.0, dry_deficit_mm=(0.0, 0.0), retention=True)

# Una esquina de rejilla cerca de Duitama.
R0, C0 = 3_000, 59_000


# ---------- la textura de un lote: la clase más frecuente de sus celdas ----------


def make_grid(textures: dict[tuple[int, int], str | None], with_texture: bool = True) -> Grid:
    """Una rejilla de ejemplo con textura por celda (`None`: sin dato), codificada como la carga el dataset."""
    items = sorted(textures.items(), key=lambda item: cell_key(f"{item[0][0]}_{item[0][1]}"))
    keys = np.array([cell_key(f"{row}_{col}") for (row, col), _ in items], dtype=np.int64)
    altitudes = np.full(len(items), 2600.0)
    if not with_texture:
        return Grid(keys=keys, altitude_m=altitudes)
    classes = tuple(sorted({texture for _, texture in items if texture is not None}))
    codes = np.array([-1 if texture is None else classes.index(texture) for _, texture in items], dtype=np.int16)
    return Grid(keys=keys, altitude_m=altitudes, texture_code=codes, texture_classes=classes)


def block(rows: int, cols: int) -> dict:
    """El polígono (GeoJSON, lon y lat) que cubre exactamente `rows × cols` celdas desde la (R0, C0)."""
    north, west = 90 - R0 * STEP, -180 + C0 * STEP
    south, east = 90 - (R0 + rows) * STEP, -180 + (C0 + cols) * STEP
    ring = [[west, north], [east, north], [east, south], [west, south], [west, north]]
    return {"type": "Polygon", "coordinates": [ring]}


def cells(textures: list[str | None], cols: int = 2) -> dict[tuple[int, int], str | None]:
    return {(R0 + index // cols, C0 + index % cols): texture for index, texture in enumerate(textures)}


def test_la_textura_del_lote_es_la_mas_frecuente_de_sus_celdas():
    around = {(R0 - 1, C0): "arenoso", (R0 + 2, C0): "arenoso", (R0, C0 - 1): "arenoso"}
    grid = make_grid({**cells(["franco", "arcilloso", "franco", "franco limoso"]), **around})
    assert lot_texture(block(2, 2), grid) == "franco"


def test_en_un_empate_gana_la_primera_en_orden_alfabetico():
    """R4, como el pipeline en `soil_municipality`."""
    assert lot_texture(block(2, 2), make_grid(cells(["franco", "arcilloso", "franco", "arcilloso"]))) == "arcilloso"


def test_las_celdas_sin_textura_no_cuentan_y_sin_ninguna_es_nula():
    """R1: una celda sin dato no se rellena; sin ninguna, no hay textura."""
    assert lot_texture(block(2, 2), make_grid(cells([None, None, None, "limoso"]))) == "limoso"
    assert lot_texture(block(2, 2), make_grid(cells([None, None, None, None]))) is None
    assert lot_texture(block(2, 2), make_grid({})) is None


def test_una_rejilla_sin_textura_publicada_da_textura_nula():
    assert lot_texture(block(2, 2), make_grid(cells(["franco"] * 4), with_texture=False)) is None


def test_un_lote_mas_chico_que_una_celda_usa_la_de_su_centro():
    tiny = {
        "type": "Polygon",
        "coordinates": [
            [
                [-180 + (C0 + 0.4) * STEP, 90 - (R0 + 0.4) * STEP],
                [-180 + (C0 + 0.6) * STEP, 90 - (R0 + 0.4) * STEP],
                [-180 + (C0 + 0.6) * STEP, 90 - (R0 + 0.6) * STEP],
                [-180 + (C0 + 0.4) * STEP, 90 - (R0 + 0.4) * STEP],
            ]
        ],
    }
    assert lot_texture(tiny, make_grid({(R0, C0): "franco arenoso", (R0, C0 + 1): "arcilloso"})) == "franco arenoso"


def test_la_textura_de_la_zona_es_la_del_lote_con_contorno_y_si_no_la_del_municipio():
    """Contrato, «La rejilla de 250 m»: un lote sin polígono usa el suelo de su municipio. Con contorno, la de sus celdas
    y nunca la del municipio (R1, como la altitud)."""
    municipality = SimpleNamespace(municipality_id=SAMACA)
    grid = make_grid(cells(["arenoso"] * 4))
    dataset = SimpleNamespace(grid=grid, soil={SAMACA: {"texture_class": "franco arcilloso"}})
    assert zone_texture(dataset, municipality, None) == "franco arcilloso"
    assert zone_texture(dataset, municipality, SimpleNamespace(geometry=None)) == "franco arcilloso"
    assert zone_texture(dataset, municipality, SimpleNamespace(geometry=block(2, 2))) == "arenoso"
    outside = {"type": "Polygon", "coordinates": [[[0.0, 0.0], [0.001, 0.0], [0.001, -0.001], [0.0, 0.0]]]}
    assert zone_texture(dataset, municipality, SimpleNamespace(geometry=outside)) is None
    assert zone_texture(SimpleNamespace(grid=None, soil=dataset.soil), municipality, SimpleNamespace(geometry=block(2, 2))) is None
    assert zone_texture(SimpleNamespace(grid=grid, soil={}), municipality, None) is None


# ---------- lo que recibe el balance en /diagnostics ----------


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return TODAY.astimezone(tz) if tz else TODAY

    monkeypatch.setattr(region, "datetime", Clock)


def use(monkeypatch, folder: Path) -> None:
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder.resolve()))
    get_settings.cache_clear()


@pytest.fixture
def examples(tmp_path, monkeypatch):
    use(monkeypatch, examples_with_sources(tmp_path / "ejemplos"))


@pytest.fixture
def examples_copy(tmp_path, monkeypatch):
    folder = examples_with_sources(tmp_path / "ejemplos")
    use(monkeypatch, folder)
    return folder


def record_balance(monkeypatch) -> list[tuple]:
    """Cambia el balance de producción por uno de ejemplo que guarda con qué se llamó: estas pruebas miran qué recibe
    `balance_for` (la ventana, el clima, la textura y el cultivo), no su cuenta."""
    calls = []

    def balance_for(*args):
        calls.append(args)
        return EXAMPLE_BALANCE

    monkeypatch.setattr(window_signals_module, "balance_for", balance_for)
    return calls


def diagnose(**extra) -> dict:
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL, **extra}
    response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    return response.json()


def test_el_dataset_carga_la_textura_de_la_rejilla(examples):
    grid = get_dataset().grid
    assert grid.texture_classes == ("franco arcilloso",)
    assert grid.texture_code is not None and len(grid.texture_code) == len(grid.keys)


def test_el_balance_recibe_la_ventana_el_clima_de_la_fuente_usada_la_textura_y_la_ficha(examples, monkeypatch):
    """Lo que recibe `water_balance` de HU-144: el clima normal por mes con la lluvia de GPM IMERG (la de
    `water.rain` en `catalog/sources.yaml`), nunca la de NASA POWER, la ET0 de NASA POWER, la textura del municipio
    (sin lote) y la ficha del cultivo."""
    calls = record_balance(monkeypatch)
    assert diagnose()["signals"]["water"]["status"] == "available"
    window, climate, texture, crop = calls[0]
    assert window.sowing_date.isoformat() == APRIL
    assert texture == "franco arcilloso"
    assert crop["crop_id"] == "papa"
    imerg = pl.read_parquet(EXAMPLES / "precip_month.parquet").filter((pl.col("municipality_id") == SAMACA) & (pl.col("year") == 2015))
    power = pl.read_parquet(EXAMPLES / "climate_month.parquet").filter((pl.col("municipality_id") == SAMACA) & (pl.col("year") == 2015))
    assert set(climate) == set(range(1, 13))
    for month in range(1, 13):
        rain = imerg.filter(pl.col("month") == month).row(0, named=True)
        et0 = power.filter(pl.col("month") == month).row(0, named=True)["et0_normal_mm"]
        assert climate[month] == WaterMonth(et0, rain["precip_normal_mm"], rain["precip_dry_mm"])


def test_sin_la_lluvia_de_la_fuente_usada_el_agua_es_sin_datos_aunque_power_tenga(examples_copy, monkeypatch):
    """HU-071 y `catalog/sources.yaml`: si la fuente que calcula la señal no tiene dato para el municipio, la señal es
    `insufficient_data` aunque la de contraste tenga; nunca se cambia a la otra (R1). El balance ni se pide, la
    limitación lo dice y la de contraste se sigue mostrando, sin `used`."""
    table = pl.read_parquet(examples_copy / "precip_month.parquet")
    table.filter(pl.col("municipality_id") != SAMACA).write_parquet(examples_copy / "precip_month.parquet")
    calls = record_balance(monkeypatch)
    body = diagnose()
    water = body["signals"]["water"]
    assert calls == []
    assert (water["status"], water["level"], water["score"], water["critical"]) == ("insufficient_data", None, None, False)
    # La razón dice la causa real: falta la lluvia de la fuente que calcula la señal, no «el balance hídrico» (R5).
    assert water["reasons"][0].startswith("Sin la lluvia de GPM IMERG para la zona ")
    assert "no se usa otra fuente en su lugar" in water["reasons"][0]
    assert "balance hídrico" not in water["reasons"][0]
    assert body["limitations"].count(water["reasons"][0]) == 1
    values = {(source["source_id"], source["indicator"]): source for source in water["sources"]}
    assert values[("imerg", "precip_dry_mm")]["value"] is None and values[("imerg", "precip_dry_mm")]["used"] is True
    assert values[("nasa_power", "precip_dry_mm")]["value"] is not None and values[("nasa_power", "precip_dry_mm")]["used"] is False


def test_sin_la_et0_el_agua_es_sin_datos_y_lo_dice(examples_copy, monkeypatch):
    """HU-071: sin `climate_month` para el municipio no hay lo que pide el cultivo: `insufficient_data` (R1)."""
    table = pl.read_parquet(examples_copy / "climate_month.parquet")
    table.filter(pl.col("municipality_id") != SAMACA).write_parquet(examples_copy / "climate_month.parquet")
    calls = record_balance(monkeypatch)
    body = diagnose()
    assert calls == []
    water = body["signals"]["water"]
    assert water["status"] == "insufficient_data"
    assert water["reasons"][0].startswith("Sin la evapotranspiración de referencia de la zona ")
    assert "balance hídrico" not in water["reasons"][0]
    assert body["limitations"].count(water["reasons"][0]) == 1


# ---------- `ZoneWater.missing`: un solo mes sin dato y una ventana que cruza el fin de año ----------

# Una ventana de ejemplo (R5) de 29 + 61 + 30 días sembrada el 2 de noviembre de 2026: toca de noviembre a marzo
# (cosecha el 2 de marzo de 2027).
EXAMPLE_STAGES = [StageSpan("initial", 29, kc=0.5), StageSpan("mid", 61, kc=1.15), StageSpan("late", 30, kc=0.75)]
YEAR_END = crop_window(EXAMPLE_STAGES, date(2026, 11, 2))


def example_zone(no_dry: frozenset[int] = frozenset(), no_et0: frozenset[int] = frozenset()) -> ZoneWater:
    """Un clima de ejemplo (R5) con todos los meses, salvo los que se piden sin dato."""
    full = {month: 10.0 for month in range(1, 13)}
    dry = {month: value for month, value in full.items() if month not in no_dry}
    et0 = {month: 90.0 for month in range(1, 13) if month not in no_et0}
    rain = RainNormal("imerg", full, dry, (2001, 2024))
    return ZoneWater(rain, RainSource("GPM IMERG", 2001, 2024, None), (), et0, ())


def test_la_ventana_de_ejemplo_cruza_el_fin_de_ano():
    assert [(month.year, month.month) for month in YEAR_END.months()] == [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]


def test_sin_la_et0_de_un_solo_mes_de_la_ventana_falta_solo_ese_mes():
    """El enero del año siguiente se busca por su mes del año (las normales no tienen año): falta solo enero."""
    assert example_zone().missing(YEAR_END) == ()
    assert example_zone(no_et0=frozenset({1})).missing(YEAR_END) == (
        "Sin la evapotranspiración de referencia de la zona en enero: el agua no se evalúa",
    )
    # Un mes fuera de la ventana no cuenta.
    assert example_zone(no_dry=frozenset({7}), no_et0=frozenset({6})).missing(YEAR_END) == ()


def test_sin_la_lluvia_de_diciembre_y_la_et0_de_enero_faltan_las_dos_en_orden():
    assert example_zone(no_dry=frozenset({12}), no_et0=frozenset({1})).missing(YEAR_END) == (
        "Sin la lluvia de GPM IMERG para la zona en diciembre: el agua no se evalúa, y no se usa otra fuente en su lugar",
        "Sin la evapotranspiración de referencia de la zona en enero: el agua no se evalúa",
    )


def test_sin_la_et0_de_enero_una_siembra_de_noviembre_no_pide_el_balance(examples_copy, monkeypatch):
    """En `/diagnostics`: la papa sembrada en noviembre cruza el fin de año; sin la ET0 de enero (solo ese mes), el balance
    de esa ventana no se pide y la razón nombra enero. Ninguna ventana que toque enero llega a `balance_for` (R1)."""
    table = pl.read_parquet(examples_copy / "climate_month.parquet")
    in_january = (pl.col("municipality_id") == SAMACA) & (pl.col("month") == 1)
    table.with_columns(pl.when(in_january).then(None).otherwise(pl.col("et0_normal_mm")).alias("et0_normal_mm")).write_parquet(
        examples_copy / "climate_month.parquet"
    )
    calls = record_balance(monkeypatch)
    body = diagnose(sowing_date=NOVEMBER)
    water = body["signals"]["water"]
    # La premisa: la ventana de la papa sembrada en noviembre toca diciembre y enero del año siguiente.
    months = [(month.year, month.month) for month in _papa_window(NOVEMBER).months()]
    assert (2026, 12) in months and (2027, 1) in months
    assert water["status"] == "insufficient_data"
    assert water["reasons"] == ["Sin la evapotranspiración de referencia de la zona en enero: el agua no se evalúa"]
    assert not any(month.month == 1 for window, *_ in calls for month in window.months())


def _papa_window(sowing_date: str):
    """La ventana de la papa del dataset en uso, para comprobar la premisa de la prueba (que cruza el fin de año)."""
    return crop_window(get_dataset().stages["papa"], date.fromisoformat(sowing_date))


# ---------- las mejores ventanas: el mismo riego y el mismo suelo que la ventana consultada ----------


def record_irrigation(monkeypatch) -> list[bool | None]:
    """Espía el riego con que se arma la señal de agua de cada ventana, sin cambiar lo que devuelve."""
    seen, original = [], window_signals_module.water_in

    def water_in(zone, window, balance, irrigated, thresholds, crop_name):
        seen.append(irrigated)
        return original(zone, window, balance, irrigated, thresholds, crop_name)

    monkeypatch.setattr(window_signals_module, "water_in", water_in)
    return seen


def test_las_mejores_ventanas_usan_el_mismo_riego_y_la_misma_textura(examples, monkeypatch):
    """Sembrando en noviembre la helada es crítica: la acción es `other_window` y se califican las ventanas de los
    próximos doce meses. Todas con el riego y la textura de la consulta, no con otros (HU-071)."""
    calls = record_balance(monkeypatch)
    irrigation = record_irrigation(monkeypatch)
    body = diagnose(sowing_date=NOVEMBER, irrigated=True)
    assert body["overall_default"]["action"] == "other_window" and body["best_windows"]
    assert len(calls) > 1 and len(irrigation) == len(calls)
    assert {texture for _, _, texture, _ in calls} == {"franco arcilloso"}
    assert set(irrigation) == {True}


# ---------- con un lote dibujado: la textura del lote gana sobre la del municipio ----------

SAMACA_CENTER = (5.4925, -73.4856)


def write_sandy_grid(folder: Path) -> None:
    """Una `grid_cells.parquet` de ejemplo (R5): una caja de ±0,03° alrededor de Samacá, arenosa y a la altitud del
    municipio (para que la aptitud no cambie con el lote)."""
    municipalities = pl.read_parquet(folder / "municipalities.parquet")
    altitude = municipalities.filter(pl.col("municipality_id") == SAMACA)["altitude_m"][0]
    lat, lon = SAMACA_CENTER
    steps = np.arange(-0.03, 0.03, STEP)
    ids = sorted({cell_id(lat + dlat, lon + dlon) for dlat in steps for dlon in steps})
    pl.DataFrame(
        {"cell_id": ids, "altitude_m": [altitude] * len(ids), "texture_class": ["arenoso"] * len(ids)},
        schema={"cell_id": pl.String, "altitude_m": pl.Float64, "texture_class": pl.String},
    ).write_parquet(folder / "grid_cells.parquet")


def square_around(lat: float, lon: float, half: float = 0.01) -> dict:
    ring = [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def test_con_un_lote_dibujado_el_balance_recibe_la_textura_del_lote(examples_copy, client, monkeypatch):
    """Samacá es «franco arcilloso» en `soil_municipality`; las celdas del lote, «arenoso». Con `lot_id` de un lote con
    contorno, la textura que llega a `balance_for` es la del lote, en la ventana consultada y en las mejores ventanas, y
    el riego es el del lote. Sin lote, la del municipio (contrato, «La rejilla de 250 m»)."""
    write_sandy_grid(examples_copy)
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "username": "rosa.samaca",
            "password": "papaya-criolla-2026",
            "display_name": "Rosa",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    assert registered.status_code == 201, registered.json()
    lot = client.post(
        "/api/v1/lots",
        json={"name": "El Alto", "municipality_id": SAMACA, "geometry": square_around(*SAMACA_CENTER), "irrigated": True},
    )
    assert lot.status_code == 201, lot.json()

    calls = record_balance(monkeypatch)
    irrigation = record_irrigation(monkeypatch)
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": NOVEMBER}
    response = client.post("/api/v1/diagnostics", json={**body, "lot_id": lot.json()["lot_id"]})
    assert response.status_code == 200, response.json()
    assert response.json()["suitability"]["basis"] == "lot"
    assert response.json()["best_windows"], "la helada de noviembre lleva a calificar las mejores ventanas"
    assert calls[0][0].sowing_date.isoformat() == NOVEMBER
    assert {texture for _, _, texture, _ in calls} == {"arenoso"}
    assert set(irrigation) == {True}

    calls.clear()
    assert client.post("/api/v1/diagnostics", json=body).status_code == 200
    assert calls and {texture for _, _, texture, _ in calls} == {"franco arcilloso"}
