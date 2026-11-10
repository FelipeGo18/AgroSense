"""ET0 por Penman-Monteith (HU-143) contra el ejemplo resuelto de FAO-56 (Allen y otros, 1998, capítulo 4, ejemplo 18)."""

import math

import polars as pl
import pytest

from pipeline import et0


def saturation(t: float) -> float:
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def test_el_ejemplo_18_de_fao_56_da_3_9_mm():
    """Bruselas, 6 de julio (día 187), 50°48' N, 100 m: máxima 21,5 °C, mínima 12,3 °C, viento a 2 m de 2,078 m/s y
    radiación de 22,07 MJ/m². El ejemplo da `ea = 1,409 kPa`: aquí entra como la humedad media que da esa `ea`."""
    es = (saturation(21.5) + saturation(12.3)) / 2
    assert es == pytest.approx(1.997, abs=0.001)
    rh = 1.409 / es * 100
    row = pl.DataFrame({"x": [0]}).select(
        et0.penman_monteith(
            pl.lit(12.3), pl.lit(21.5), pl.lit(rh), pl.lit(2.078), pl.lit(22.07), pl.lit(50 + 48 / 60), pl.lit(100.0), pl.lit(187)
        ).alias("et0"),
        et0.extraterrestrial(pl.lit(50 + 48 / 60), pl.lit(187)).alias("ra"),
    )
    assert row["ra"][0] == pytest.approx(41.09, abs=0.01)
    assert round(row["et0"][0], 1) == 3.9


def test_un_dia_sin_una_variable_no_tiene_et0():
    row = pl.DataFrame({"rs": [None]}, schema={"rs": pl.Float64}).select(
        et0.penman_monteith(pl.lit(8.0), pl.lit(19.0), pl.lit(80.0), pl.lit(2.0), pl.col("rs"), pl.lit(5.5), pl.lit(2600.0), pl.lit(10))
    )
    assert row.to_series()[0] is None


def test_mas_arriba_y_mas_frio_hay_menos_et0():
    """La misma radiación y el mismo viento: a 3000 m y 6 °C menos, la ET0 baja."""
    frame = pl.DataFrame({"tmin": [12.0, 6.0], "tmax": [24.0, 18.0], "z": [1000.0, 3000.0]})
    values = frame.select(
        et0.penman_monteith(pl.col("tmin"), pl.col("tmax"), pl.lit(75.0), pl.lit(2.0), pl.lit(16.0), pl.lit(5.5), pl.col("z"), pl.lit(60))
    ).to_series()
    assert values[1] < values[0]
