"""Los datos de la señal de agua (HU-071): lee del dataset publicado el clima del agua de un municipio una sola vez por
consulta (`zone_water`), arma `signals.water.sources` de cada ventana y llama al motor con todo ya leído (R6). Solo lee:
sin errores HTTP, sin base de datos y sin guardar nada (R9). El balance hídrico lo pide `window_signals.balance_for`, el
único punto que cambia cuando entre el de HU-144 (PR #96).

**Qué se lee.** Qué fuente calcula cada cosa lo dice `catalog/sources.yaml` (`water`, con
`monthly_climate.water_sources`), y las filas de cada fuente salen de `monthly_climate.rain_rows` y `climate_rows`, las
mismas que lee `/trends` (HU-078): una sola regla para saber de qué tabla sale la lluvia de una fuente, y solo las filas
rotuladas con ella (las del dataset de ejemplo, `source_id = ejemplo`, no pasan por ninguna fuente, R5). De esas filas,
la señal lee la normal de cada mes del año, no la serie de cada año que leen las tendencias:

- La lluvia normal y la del año seco de la fuente que calcula la señal (`rain`) y de las de contraste (`rain_contrast`),
  por mes del año, con el periodo de su normal: el `normal_period` de su tabla (`precip_month`, GPM IMERG) o, en
  `climate_month` (NASA POWER), que no lo trae, el `climate_normal` del manifiesto.
- La ET0 normal (`et0`, NASA POWER: `climate_month.et0_normal_mm`, FAO-56).
- La humedad del suelo de raíces de la zona que se muestra para contrastar (`soil_moisture_contrast`): la modelada por
  NASA POWER (`climate_month.soil_wetness_root`, fracción de 0 a 1). Una fuente de `planned` no se muestra (SMAP, HU-210);
  tampoco una sin lector aquí.

**`signals.water.sources`** (contrato, «Respuesta de diagnóstico»): la lluvia de la ventana de cada fuente, del año seco
(`precip_dry_mm`) y normal (`precip_normal_mm`), sumada con `window_rain_mm` (`backend/engine/water_need.py`, el
prorrateo por días de HU-078), en mm y con el periodo de la normal de cada fuente; `used = true` solo en el año seco de la
fuente que calcula la señal, también cuando la señal no se califica (es la que se habría usado). Después, con
`used = false`, la humedad del suelo. Nunca se promedian ni una rellena a la otra (decisión 11, R1).

**La humedad del suelo de la ventana** es el promedio de los meses que toca la ventana, cada uno pesado por sus días en
ella (como el prorrateo de la lluvia), y la de cada mes es la normal: el promedio de los años del periodo normal
(`climate_normal`) con dato, si son al menos `min_years`. Sin uno de esos meses, nula (R1). Decisión del 14 de noviembre
de 2026 (HU-071), pendiente de aprobar: la ventana entera y no solo el mes de siembra, porque es la que se compara con la
lluvia de la ventana; es contraste y no cambia la calificación.

**El nombre de la fuente** en la razón sale de la tabla `sources` del dataset: su `name` hasta el primer « · » («NASA
POWER · Datos diarios…» → «NASA POWER»). Si la tabla no trae la fuente (el dataset de ejemplo), el nombre corto de
`SHORT_NAMES` («GPM IMERG», «NASA POWER») y, si tampoco está ahí, el `source_id`. Decisión del 14 de noviembre de 2026
(HU-071), pendiente de aprobar.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

from backend.api import monthly_climate
from backend.api.climate_signals import climate_normal
from backend.api.monthly_climate import climate_rows, number_or_none, rain_rows
from backend.config.thresholds import Thresholds
from backend.dataset import Dataset
from backend.engine.sensitive_signal import ClimateNormal
from backend.engine.stages import CropWindow
from backend.engine.water_need import window_rain_mm
from backend.engine.water_signal import RainSource, WaterBalanceSummary, missing_data, water_signal
from common import signal_sources

# Por qué estos `source_id` viven aquí, en el adaptador y no en el motor (R6, R7): son los productos que este adaptador
# sabe leer del dataset publicado. `POWER` es el único con lector de humedad del suelo hoy (SMAP llega con HU-210). Los
# nombres cortos son solo un respaldo para la razón: el nombre que vale es el de la tabla `sources` del dataset
# (`source_name`), y `SHORT_NAMES` solo se usa si la tabla no trae la fuente, como en el dataset de ejemplo.
POWER = "nasa_power"
SHORT_NAMES = {"imerg": "GPM IMERG", POWER: "NASA POWER"}
DRY, NORMAL = "precip_dry_mm", "precip_normal_mm"
WETNESS = "soil_wetness_root"
MM, FRACTION = "mm", "fracción"
PERIOD = re.compile(r"^(\d{4})-(\d{4})$")


@dataclass(frozen=True)
class WaterMonth:
    """El clima normal de la zona en un mes del año, con la forma de `MonthClimate` del balance de HU-144 (PR #96): la
    ET0 normal y la lluvia del año normal y del año seco de la fuente que calcula la señal. Nulo: sin dato (R1)."""

    et0_mm: float | None
    rain_normal_mm: float | None
    rain_dry_mm: float | None


@dataclass(frozen=True)
class RainNormal:
    """La lluvia normal y la del año seco de una fuente por mes del año (1 a 12) y el periodo de su normal (nulo si no
    se sabe)."""

    source_id: str
    normal_mm: Mapping[int, float | None]
    dry_mm: Mapping[int, float | None]
    period: tuple[int, int] | None

    def period_text(self) -> str | None:
        return None if self.period is None else f"{self.period[0]}-{self.period[1]}"


@dataclass(frozen=True)
class Wetness:
    """La humedad del suelo normal de una fuente por mes del año, en su unidad, y el periodo de su normal."""

    source_id: str
    indicator: str
    unit: str
    by_month: Mapping[int, float | None]
    period: str | None


@dataclass(frozen=True)
class ZoneWater:
    """Lo que la señal de agua lee del dataset para un municipio, una vez por consulta."""

    rain: RainNormal
    source: RainSource
    contrast: tuple[RainNormal, ...]
    et0_mm: Mapping[int, float | None]
    wetness: tuple[Wetness, ...]

    def months(self) -> dict[int, WaterMonth]:
        """El clima normal de cada mes del año para el balance hídrico (HU-144), con la lluvia de la fuente que calcula
        la señal: nunca la de contraste (R1)."""
        return {
            month: WaterMonth(self.et0_mm.get(month), self.rain.normal_mm.get(month), self.rain.dry_mm.get(month)) for month in range(1, 13)
        }

    def missing(self, window: CropWindow) -> tuple[str, ...]:
        """Por qué no se puede pedir el balance de la ventana: los meses sin la lluvia del año seco de la fuente que
        calcula la señal o sin la ET0, con el texto del motor (`missing_data`, R1). Vacío si están todos."""
        months = window.months()
        no_rain = [month for month in months if self.rain.dry_mm.get(month.month) is None]
        no_et0 = [month for month in months if self.et0_mm.get(month.month) is None]
        return missing_data(self.source, no_rain, no_et0)


@dataclass(frozen=True)
class SourceReading:
    """Una entrada de `signals.water.sources`, con los nombres de campo de `SourceValue` del contrato."""

    source_id: str
    indicator: str
    value: float | None
    unit: str
    period: str | None
    used: bool


@dataclass(frozen=True)
class WaterSignal:
    """La señal `water` de una ventana: la del motor (`ClimateSignalResult`) con sus fuentes para contrastar."""

    status: str
    level: str | None
    critical: bool
    score: int | None
    indicators: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    sources: tuple[SourceReading, ...]


def _by_month(rows: pl.DataFrame | None, column: str) -> dict[int, float | None]:
    """El valor normal de cada mes del año: las tablas lo repiten en cada año, así que vale el primero con dato. Un mes
    sin filas, o sin dato en ninguna, no está (R1)."""
    if rows is None or rows.is_empty() or column not in rows.columns:
        return {}
    values = rows.sort("year").group_by("month", maintain_order=True).agg(pl.col(column).drop_nans().drop_nulls().first())
    numbers = ((int(month), number_or_none(value)) for month, value in values.iter_rows())
    return {month: number for month, number in numbers if number is not None}


def _period(rows: pl.DataFrame | None, normal: ClimateNormal | None) -> tuple[int, int] | None:
    """El periodo de la normal de las filas de lluvia de una fuente: el `normal_period` de su tabla («2001-2024», en
    `precip_month`), si es uno solo y se entiende; en `climate_month`, que no lo trae, el `climate_normal` del
    manifiesto. Nulo si la fuente no se publica (R1)."""
    if rows is None:
        return None
    if "normal_period" not in rows.columns:
        return None if normal is None else (normal.first_year, normal.last_year)
    periods = rows["normal_period"].drop_nulls().unique().to_list()
    match = PERIOD.match(periods[0]) if len(periods) == 1 else None
    return (int(match[1]), int(match[2])) if match else None


def _rain_normal(dataset: Dataset, municipality_id: str, source_id: str, normal: ClimateNormal | None) -> RainNormal:
    rows = rain_rows(dataset, municipality_id, source_id)
    return RainNormal(source_id, _by_month(rows, NORMAL), _by_month(rows, DRY), _period(rows, normal))


def _power_wetness(dataset: Dataset, municipality_id: str, normal: ClimateNormal | None) -> Wetness:
    """La humedad del suelo de raíces normal de NASA POWER por mes: el promedio de los años del periodo normal con dato,
    si son al menos `min_years` (R1). Sin el periodo normal, sin dato."""
    table, by_month = climate_rows(dataset, municipality_id, POWER), {}
    if table is not None and normal is not None and WETNESS in table.columns:
        rows = (
            table.filter(pl.col("year").is_between(normal.first_year, normal.last_year))
            .filter(pl.col(WETNESS).is_not_null() & pl.col(WETNESS).is_not_nan())
            .group_by("month")
            .agg(pl.col(WETNESS).mean().alias("mean"), pl.len().alias("years"))
        )
        by_month = {int(month): float(mean) for month, mean, years in rows.iter_rows() if years >= normal.min_years}
    period = None if normal is None else f"{normal.first_year}-{normal.last_year}"
    return Wetness(POWER, WETNESS, FRACTION, by_month, period)


def source_name(dataset: Dataset, source_id: str) -> str:
    """El nombre de la fuente como lo dice la razón (ver el módulo)."""
    row = next((row for row in dataset.sources if row.get("source_id") == source_id), None)
    name = (row or {}).get("name")
    if isinstance(name, str) and name.strip():
        return name.split(" · ")[0].strip()
    return SHORT_NAMES.get(source_id, source_id)


def zone_water(dataset: Dataset, municipality_id: str) -> ZoneWater:
    """El clima del agua del municipio para todas las ventanas de una consulta."""
    config = monthly_climate.water_sources(dataset)
    normal = climate_normal(dataset)
    planned = signal_sources.get_signal_sources().is_planned
    rain = _rain_normal(dataset, municipality_id, config.used, normal)
    # Una fuente de `planned` todavía no se publica: no se muestra (`catalog/sources.yaml`).
    contrast = tuple(
        _rain_normal(dataset, municipality_id, source_id, normal)
        for source_id in config.contrast
        if source_id != config.used and not planned(source_id)
    )
    # Solo la humedad de NASA POWER tiene lector hoy; la de SMAP llega con HU-210.
    wetness = tuple(
        _power_wetness(dataset, municipality_id, normal)
        for source_id in config.soil_moisture_contrast
        if source_id == POWER and not planned(source_id)
    )
    et0 = _by_month(climate_rows(dataset, municipality_id, config.et0), "et0_normal_mm") if config.et0 else {}
    name = source_name(dataset, config.used)
    first, last = rain.period if rain.period is not None else (None, None)
    return ZoneWater(rain, RainSource(name, first, last, config.caveat), contrast, et0, wetness)


def _window_rain(window: CropWindow, by_month: Mapping[int, float | None]) -> float | None:
    """La lluvia de la ventana con el prorrateo por días de `window_rain_mm` (HU-078). Nula si falta algún mes (R1)."""
    total = window_rain_mm(window, {(month.year, month.month): by_month.get(month.month) for month in window.months()})
    return None if total is None else round(total, 1)


def _window_mean(window: CropWindow, by_month: Mapping[int, float | None]) -> float | None:
    """El promedio de un valor mensual en la ventana, cada mes pesado por sus días en ella. Nulo si falta algún mes."""
    months = window.months()
    values = [by_month.get(month.month) for month in months]
    if any(value is None for value in values):
        return None
    return round(sum(value * month.days for value, month in zip(values, months, strict=True)) / sum(month.days for month in months), 2)


def water_sources(zone: ZoneWater, window: CropWindow | None) -> tuple[SourceReading, ...]:
    """`signals.water.sources` de la ventana (ver el módulo). Sin ventana, los valores son nulos."""
    readings = []
    for rain in (zone.rain, *zone.contrast):
        used = rain is zone.rain
        for indicator, by_month in ((DRY, rain.dry_mm), (NORMAL, rain.normal_mm)):
            value = None if window is None else _window_rain(window, by_month)
            readings.append(SourceReading(rain.source_id, indicator, value, MM, rain.period_text(), used and indicator == DRY))
    for wetness in zone.wetness:
        value = None if window is None else _window_mean(window, wetness.by_month)
        readings.append(SourceReading(wetness.source_id, wetness.indicator, value, wetness.unit, wetness.period, False))
    return tuple(readings)


def water_in(
    zone: ZoneWater,
    window: CropWindow | None,
    balance: WaterBalanceSummary | None,
    irrigated: bool | None,
    thresholds: Thresholds,
    crop_name: str,
) -> WaterSignal:
    """La señal `water` de la ventana con el clima ya leído y el balance que dio `balance_for` (nulo: sin balance). Si a
    la ventana le faltan datos de la fuente que calcula la señal (`ZoneWater.missing`), la razón lo dice (R5)."""
    missing = () if window is None else zone.missing(window)
    result = water_signal(balance, irrigated, zone.source, window, thresholds, crop_name, missing)
    return WaterSignal(
        result.status,
        result.level,
        result.critical,
        result.score,
        result.indicators,
        result.reasons,
        result.limitations,
        water_sources(zone, window),
    )
