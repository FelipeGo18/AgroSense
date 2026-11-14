"""La altitud de un lote dibujado y la temperatura corregida a esa altitud (HU-191, pieza A; contrato, «La rejilla de 250 m»).

`lot_altitude` es la mediana de las celdas de `grid_cells` cuyo centro cae dentro del polígono; un lote más chico que una
celda usa la celda que contiene su centro y lo dice. Las celdas de las pruebas son sintéticas, de ejemplo (R5).
"""

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from backend.api.lot_terrain import LotAltitude, lot_altitude, tmean_at_altitude
from backend.dataset import Grid
from common.grid import GRID_STEP_DEG as STEP
from common.grid import cell_center, cell_key
from pipeline import climate_normals
from pipeline.sources import nasa_power

# Una esquina de rejilla cerca de Duitama: la celda (R0, C0) y las que la rodean.
R0, C0 = 3_000, 59_000


def make_grid(values: dict[tuple[int, int], float]) -> Grid:
    """Una rejilla de ejemplo: `{(fila, columna): altitud}`; `nan` es una celda sin dato."""
    items = sorted(values.items(), key=lambda item: cell_key(f"{item[0][0]}_{item[0][1]}"))
    keys = np.array([cell_key(f"{row}_{col}") for (row, col), _ in items], dtype=np.int64)
    return Grid(keys=keys, altitude_m=np.array([altitude for _, altitude in items], dtype=np.float64))


def polygon(*points: tuple[float, float]) -> dict:
    """GeoJSON Polygon con anillo cerrado, de puntos (lat, lon)."""
    ring = [[lon, lat] for lat, lon in points]
    return {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}


def corner(row: int, col: int) -> tuple[float, float]:
    """La esquina noroeste de la celda (fila, columna)."""
    return 90 - row * STEP, -180 + col * STEP


def block(rows: int, cols: int, row0: int = R0, col0: int = C0) -> dict:
    """El polígono que cubre exactamente `rows × cols` celdas desde la (row0, col0)."""
    (n, w), (s, e) = corner(row0, col0), corner(row0 + rows, col0 + cols)
    return polygon((n, w), (n, e), (s, e), (s, w))


def cells(rows: int, cols: int, altitudes: list[float], row0: int = R0, col0: int = C0) -> dict[tuple[int, int], float]:
    positions = [(row0 + r, col0 + c) for r in range(rows) for c in range(cols)]
    return dict(zip(positions, altitudes, strict=True))


def test_el_resultado_trae_altitud_celdas_y_si_fue_por_el_centro():
    assert LotAltitude(altitude_m=3000.0, cells=9, by_center=False) == LotAltitude(3000.0, 9, False)


def test_un_poligono_de_3_por_3_celdas_da_la_mediana_de_esas_9():
    altitudes = [2900, 2950, 3000, 3100, 3200, 3300, 3500, 3600, 4000]
    # Alrededor hay celdas muy distintas: no deben contar.
    around = {(R0 - 1, C0 + 1): 100.0, (R0 + 3, C0 + 1): 9000.0, (R0 + 1, C0 - 1): 100.0, (R0 + 1, C0 + 3): 9000.0}
    result = lot_altitude(block(3, 3), make_grid({**cells(3, 3, altitudes), **around}))
    assert result == LotAltitude(altitude_m=3200, cells=9, by_center=False)


def test_con_un_numero_par_de_celdas_es_el_promedio_de_las_dos_del_medio():
    result = lot_altitude(block(2, 2), make_grid(cells(2, 2, [1000, 1001, 1003, 1004])))
    assert result == LotAltitude(altitude_m=1002, cells=4, by_center=False)


@pytest.mark.parametrize(("altitudes", "expected"), [([1000.2, 1000.3, 1000.4], 1000), ([1000.6, 1000.7, 1000.9], 1001)])
def test_la_altitud_se_redondea_a_metros_enteros(altitudes, expected):
    result = lot_altitude(block(1, 3), make_grid(cells(1, 3, altitudes)))
    assert result.altitude_m == expected and float(result.altitude_m).is_integer()


def test_un_centro_justo_en_el_borde_del_poligono_cuenta():
    # Del centro de la celda (R0, C0) al centro de la (R0 + 2, C0 + 2): los centros de las 8 celdas de afuera quedan
    # justo sobre el borde y el de la del medio, adentro. Si el borde no contara, la mediana sería la del medio (100).
    north, west = cell_center(f"{R0}_{C0}")
    south, east = cell_center(f"{R0 + 2}_{C0 + 2}")
    edge = polygon((north, west), (north, east), (south, east), (south, west))
    altitudes = [1000, 1001, 1002, 1003, 100, 1004, 1005, 1006, 1007]
    result = lot_altitude(edge, make_grid(cells(3, 3, altitudes)))
    assert result == LotAltitude(altitude_m=1003, cells=9, by_center=False)


def test_las_celdas_sin_altitud_no_cuentan_y_no_se_rellenan():
    nan = float("nan")
    altitudes = [nan, 3000, nan, 3002, 3004, nan, 3006, 3008, 3010]
    result = lot_altitude(block(3, 3), make_grid(cells(3, 3, altitudes)))
    assert result == LotAltitude(altitude_m=3005, cells=6, by_center=False)


def test_las_celdas_que_no_estan_en_la_tabla_tampoco_cuentan():
    present = {(R0, C0): 2000.0, (R0, C0 + 1): 2002.0}
    result = lot_altitude(block(3, 3), make_grid(present))
    assert result == LotAltitude(altitude_m=2001, cells=2, by_center=False)


def test_un_lote_mas_chico_que_una_celda_usa_la_celda_que_contiene_su_centro():
    north, west = corner(R0, C0)
    # Un cuadrado de unos 20 m, a un tercio de la celda: ningún centro de celda cae dentro.
    lat, lon = north - 0.3 * STEP, west + 0.3 * STEP
    tiny = polygon((lat + 0.0001, lon - 0.0001), (lat + 0.0001, lon + 0.0001), (lat - 0.0001, lon + 0.0001), (lat - 0.0001, lon - 0.0001))
    result = lot_altitude(tiny, make_grid({(R0, C0): 2750.0, (R0, C0 + 1): 1.0, (R0 + 1, C0): 2.0, (R0 + 1, C0 + 1): 3.0}))
    assert result == LotAltitude(altitude_m=2750, cells=1, by_center=True)


def test_un_lote_chico_sobre_una_celda_sin_dato_no_tiene_altitud():
    north, west = corner(R0, C0)
    lat, lon = north - 0.3 * STEP, west + 0.3 * STEP
    tiny = polygon((lat + 0.0001, lon - 0.0001), (lat + 0.0001, lon + 0.0001), (lat - 0.0001, lon + 0.0001), (lat - 0.0001, lon - 0.0001))
    result = lot_altitude(tiny, make_grid({(R0, C0): float("nan")}))
    assert result.altitude_m is None and result.by_center is True


def test_sin_ninguna_celda_con_dato_la_altitud_es_nula():
    nan = float("nan")
    result = lot_altitude(block(3, 3), make_grid(cells(3, 3, [nan] * 9)))
    assert result == LotAltitude(altitude_m=None, cells=0, by_center=False)


def test_con_la_tabla_vacia_la_altitud_es_nula():
    result = lot_altitude(block(3, 3), make_grid({}))
    assert result.altitude_m is None and result.cells == 0


def test_el_resultado_no_depende_del_vertice_con_que_empieza_el_poligono():
    values = {(R0 + r, C0 + c): 2800.0 + 37 * r * r + 11 * c + (5 if (r + c) % 2 else 0) for r in range(-1, 6) for c in range(-1, 6)}
    grid = make_grid(values)
    # Un polígono irregular, no alineado con la rejilla.
    ring = [
        (90 - (R0 + 0.2) * STEP, -180 + (C0 + 0.3) * STEP),
        (90 - (R0 + 0.1) * STEP, -180 + (C0 + 4.4) * STEP),
        (90 - (R0 + 3.7) * STEP, -180 + (C0 + 5.1) * STEP),
        (90 - (R0 + 4.6) * STEP, -180 + (C0 + 2.2) * STEP),
        (90 - (R0 + 2.0) * STEP, -180 + (C0 + 0.9) * STEP),
    ]
    expected = lot_altitude(polygon(*ring), grid)
    assert expected.cells > 1 and expected.by_center is False
    for start in range(1, len(ring)):
        assert lot_altitude(polygon(*ring[start:], *ring[:start]), grid) == expected
    assert lot_altitude(polygon(*reversed(ring)), grid) == expected


# La corrección por altitud (decisión 6.1: el gradiente sale del manifiesto, `dataset.region["temperature_lapse_rate"]`).
LAPSE = {"temp_max_c_per_m": 0.0058, "temp_min_c_per_m": 0.0059, "source_id": "cenicafe_lapse_rate"}


def test_un_lote_840_m_mas_arriba_que_la_cabecera_baja_4_9_grados():
    # 840 × (0,0059 + 0,0058) / 2 = 4,914 °C, que a un decimal es 4,9.
    assert tmean_at_altitude(12.8, reference_altitude_m=2660, altitude_m=3500, lapse_rate=LAPSE) == 7.9


def test_un_lote_mas_abajo_que_la_cabecera_es_mas_calido():
    # Samacá a 2660 m, lote a 2400 m: 12,8 + 260 × 0,00585 = 14,321 -> 14,3.
    assert tmean_at_altitude(12.8, reference_altitude_m=2660, altitude_m=2400, lapse_rate=LAPSE) == 14.3


def test_a_la_misma_altitud_no_cambia():
    assert tmean_at_altitude(12.8, reference_altitude_m=2660, altitude_m=2660, lapse_rate=LAPSE) == 12.8


def test_el_gradiente_se_lee_de_lo_que_se_le_pasa_no_esta_escrito_en_el_codigo():
    other = {"temp_max_c_per_m": 0.0100, "temp_min_c_per_m": 0.0060}
    # 1000 × 0,008 = 8,0 °C.
    assert tmean_at_altitude(20.0, reference_altitude_m=0, altitude_m=1000, lapse_rate=other) == 12.0


def test_la_temperatura_sale_redondeada_a_un_decimal():
    value = tmean_at_altitude(12.8, reference_altitude_m=2660, altitude_m=3333, lapse_rate=LAPSE)
    assert value == round(value, 1) == 8.9


# Equivalencia con el pipeline: corregir `climate_day` a la altitud del lote y sacar su media anual da lo mismo (0,1 °C
# como mucho, por el redondeo de 2 decimales por día y 1 en la media) que corregir la media del municipio con la fórmula.
NORMAL = climate_normals.Normal(first_year=1991, last_year=2020, min_years=24, min_day_share=0.9, dry_quantile=0.2)


def power_series(lat: float, lon: float) -> pl.DataFrame:
    """Temperaturas de ejemplo (R5) de una celda de POWER, con un ciclo anual y un poco de ruido determinista."""
    days = [date(1991, 1, 1) + timedelta(days=i) for i in range((date(2020, 12, 31) - date(1991, 1, 1)).days + 1)]
    return pl.DataFrame(
        {
            "cell": nasa_power.cell_of(lat, lon),
            "date": days,
            "temp_min_c": [14.0 + 2.5 * np.sin(d.timetuple().tm_yday / 58.0) + (d.toordinal() % 7) * 0.137 for d in days],
            "temp_max_c": [24.0 + 3.1 * np.sin(d.timetuple().tm_yday / 61.0) + (d.toordinal() % 11) * 0.093 for d in days],
        }
    )


@pytest.mark.parametrize("lot_altitude_m", [3500, 2400, 2661, 1200])
def test_la_formula_coincide_con_corregir_el_clima_diario_a_la_altitud_del_lote(lot_altitude_m):
    lat, lon, cell_height = 5.5, -73.0, 2900.0
    municipalities = pl.DataFrame(
        {
            "municipality_id": ["15646", "LOTE1"],
            "lat": [lat, lat],
            "lon": [lon, lon],
            "altitude_m": [2660.0, float(lot_altitude_m)],
            "climate_cell_elevation_m": [cell_height, cell_height],
        }
    )
    lapse = {"temp_max_c_per_m": 0.0058, "temp_min_c_per_m": 0.0059}
    day = nasa_power.climate_day(power_series(lat, lon), municipalities, lapse)
    tmean = dict(climate_normals.tmean_annual(day, NORMAL).select("municipality_id", "tmean_annual_c").iter_rows())
    by_formula = tmean_at_altitude(tmean["15646"], reference_altitude_m=2660, altitude_m=lot_altitude_m, lapse_rate=lapse)
    assert abs(by_formula - tmean["LOTE1"]) <= 0.1 + 1e-9
