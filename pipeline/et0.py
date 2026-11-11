"""Evapotranspiración de referencia (ET0) diaria por Penman-Monteith, como la define FAO-56 (HU-143).

Allen, Pereira, Raes y Smith (1998), *Crop evapotranspiration*, FAO Irrigation and Drainage Paper 56, capítulo 3
(fuente `fao_56` del catálogo). Ecuación 6, para un pasto de referencia, con el flujo de calor del suelo diario en cero
(ecuación 42):

    ET0 = [0,408 Δ (Rn − G) + γ (900 / (T + 273)) u2 (es − ea)] / [Δ + γ (1 + 0,34 u2)]

- `T`: la media de la máxima y la mínima (ecuación 9). `es`: el promedio de la presión de saturación de la máxima y la
  mínima (ecuaciones 11 y 12). `ea`: con la humedad relativa media, `ea = RHmedia / 100 × es` (ecuación 19), porque
  NASA POWER da la humedad media del día y no la máxima ni la mínima.
- `γ`: con la presión de la altitud (ecuaciones 7 y 8).
- `Rn`: la radiación neta (ecuaciones 38 y 39), con un albedo de 0,23, la radiación de cielo despejado
  `Rso = (0,75 + 2·10⁻⁵ z) Ra` (ecuación 37) y la extraterrestre `Ra` de la latitud y el día del año (ecuaciones 21 a 25).

Son expresiones de Polars, sin leer archivos: las usa `nasa_power.climate_month`. Un día al que le falta una variable
no tiene ET0 (R1).
"""

import math

import polars as pl

SOLAR_CONSTANT = 0.0820  # MJ m⁻² min⁻¹ (ecuación 21)
STEFAN_BOLTZMANN = 4.903e-9  # MJ K⁻⁴ m⁻² día⁻¹ (ecuación 39)
ALBEDO = 0.23  # pasto de referencia (ecuación 38)


def _saturation(t: pl.Expr) -> pl.Expr:
    """Presión de vapor de saturación a la temperatura `t` (°C), en kPa (ecuación 11)."""
    return 0.6108 * ((17.27 * t) / (t + 237.3)).exp()


def extraterrestrial(lat_deg: pl.Expr, day_of_year: pl.Expr) -> pl.Expr:
    """`Ra`, la radiación que llega al tope de la atmósfera, en MJ/m²/día (ecuaciones 21 a 25)."""
    phi = lat_deg * (math.pi / 180)
    dr = 1 + 0.033 * (2 * math.pi / 365 * day_of_year).cos()
    delta = 0.409 * (2 * math.pi / 365 * day_of_year - 1.39).sin()
    ws = (-(phi.tan()) * delta.tan()).clip(-1, 1).arccos()
    return 24 * 60 / math.pi * SOLAR_CONSTANT * dr * (ws * phi.sin() * delta.sin() + phi.cos() * delta.cos() * ws.sin())


def penman_monteith(
    tmin: pl.Expr,
    tmax: pl.Expr,
    rh_mean: pl.Expr,
    wind_2m: pl.Expr,
    radiation: pl.Expr,
    lat_deg: pl.Expr,
    altitude_m: pl.Expr,
    day_of_year: pl.Expr,
) -> pl.Expr:
    """La ET0 de un día en mm, con la mínima y la máxima en °C, la humedad relativa media en %, el viento a 2 m en m/s,
    la radiación solar en MJ/m²/día, la latitud en grados y la altitud en metros."""
    t = (tmax + tmin) / 2
    es = (_saturation(tmax) + _saturation(tmin)) / 2
    ea = rh_mean / 100 * es
    slope = 4098 * _saturation(t) / (t + 237.3) ** 2
    pressure = 101.3 * ((293 - 0.0065 * altitude_m) / 293) ** 5.26
    gamma = 0.665e-3 * pressure
    ra = extraterrestrial(lat_deg, day_of_year)
    rso = (0.75 + 2e-5 * altitude_m) * ra
    relative = (radiation / rso).clip(upper_bound=1.0)
    rns = (1 - ALBEDO) * radiation
    rnl = STEFAN_BOLTZMANN * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * ea.sqrt()) * (1.35 * relative - 0.35)
    rn = rns - rnl
    et0 = (0.408 * slope * rn + gamma * (900 / (t + 273)) * wind_2m * (es - ea)) / (slope + gamma * (1 + 0.34 * wind_2m))
    # Un día con radiación nula, o un modelo que da un valor negativo por redondeo, no deja ET0 negativa.
    return et0.clip(lower_bound=0)
