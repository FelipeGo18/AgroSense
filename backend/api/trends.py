"""Las series de `/trends` (HU-078; specs/02-contratos.md, «Respuesta de `GET /api/v1/trends`»).

Tres series, cada una en su unidad: el agua de la ventana por año, el área sembrada del semestre por año y el verdor
normal del municipio por periodo de 16 días. Es historia de la zona, no un pronóstico. Solo se lee el dataset
publicado: nada se guarda ni va al log (R9). Sin datos, la serie viene vacía con `insufficient_data` (R1).

**Agua.** La ventana es la del cultivo sembrado en `sowing_date` (`crop_window`, por calendario). Se proyecta sobre cada
año histórico `Y`: las mismas fechas (mes y día), con sus meses en `Y` y, si la ventana pasa de diciembre a enero, los
siguientes en `Y + 1`. La lluvia y la necesidad las suma el motor (`backend.engine.water_need`):

- **Prorrateo por días:** cada mes de la ventana aporta la fracción de su total mensual igual a los días de la ventana
  que caen en él sobre los días de ese mes en el año histórico (un febrero de 2016 tiene 29, uno de 2015, 28). La
  misma fracción vale para la lluvia y para la ETc, así que se comparan mes por mes. Un 29 de febrero de la ventana no
  existe en un año histórico de febrero de 28 días: no aporta lluvia ni necesidad, y una siembra el 29 de febrero se
  proyecta en esos años desde el 1 de marzo. La fracción de un mes nunca pasa de 1.
- **Necesidad:** ETc = Kc × ET0, con la curva de Kc de FAO-56 (Allen et al. 1998, Estudio FAO Riego y Drenaje 56,
  cap. 6, figura 25 y ecuación 66): constante en la inicial y la media, en rampa en el desarrollo y en la final.
- **Periodo:** los años son los que la fuente de lluvia publica para el municipio, del primer `(año, mes)` con fila al
  último. Un año entra solo si su ventana proyectada cae entera en ese periodo: un año al que el dataset no llega (por
  ejemplo, el último año de IMERG, publicado hasta septiembre, para una ventana que llega a octubre) no es un dato que
  falta, es un año fuera del periodo. La ET0 no recorta años.
- Dentro del periodo, un año al que le falta la lluvia de algún mes de la ventana se muestra con `precip_mm` nulo
  (como 2017 en el ejemplo del contrato), y uno al que le falta la ET0 de algún mes o el Kc, con `need_mm` nulo. Nunca
  un cero (R1).
- Si ningún año tiene lluvia, la serie es `insufficient_data` y viene vacía.
"""

from calendar import monthrange
from datetime import date

import polars as pl

from backend.api.calc_models import (
    NdviSeries,
    SupplyPoint,
    SupplySeries,
    TrendsRequestEcho,
    TrendsResponse,
    Versions,
    WaterPoint,
    WaterSeries,
)
from backend.api.monthly_climate import MonthlySeries, monthly_et0, monthly_rain, water_sources
from backend.config.versions import rules_version
from backend.dataset import Dataset
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from backend.engine.stages import CropWindow, crop_window
from backend.engine.water_need import window_etc_mm, window_rain_mm
from common import signal_sources

WATER_MISSING = "Sin la lluvia de {source} para esta ventana en la zona: la serie de agua viene vacía"
SUPPLY_MISSING = "Sin el área sembrada de {source} del semestre {semester} en la zona: la serie de oferta viene vacía"
NDVI_WITHOUT_SOURCE = "El verdor todavía no tiene una fuente asignada para la región: la serie de verdor viene vacía"


def semester(sowing_date: date) -> str:
    """El semestre de EVA en que cae la siembra: A de enero a junio, B de julio a diciembre (CLAUDE.md, «Ventanas de
    siembra»). Solo existe para leer la oferta: la decisión se evalúa por ventana."""
    return "A" if sowing_date.month <= 6 else "B"


def _mm(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def _project(series: MonthlySeries, window: CropWindow, year: int) -> dict[tuple[int, int], float | None]:
    """Los valores de `series` para los meses de la ventana, tomados del año histórico `year` (y del siguiente para los
    meses que pasan de diciembre a enero). La llave es la del calendario de la ventana, la que espera el motor."""
    shift = year - window.sowing_date.year
    return {(month.year, month.month): series.values.get((month.year + shift, month.month)) for month in window.months()}


def _historical_days(window: CropWindow, year: int) -> dict[tuple[int, int], int]:
    """Los días de cada mes histórico del que salen los totales (un febrero de 2016 tiene 29, el de 2027, 28)."""
    shift = year - window.sowing_date.year
    return {(month.year, month.month): monthrange(month.year + shift, month.month)[1] for month in window.months()}


def water_series(dataset: Dataset, municipality_id: str, crop_id: str, sowing_date: date) -> WaterSeries:
    sources = water_sources(dataset)
    empty = WaterSeries(status=INSUFFICIENT_DATA, source_id=sources.used, points=[])
    window = crop_window(dataset.stages.get(crop_id, []), sowing_date)
    if window is None:
        return empty
    rain = monthly_rain(dataset, municipality_id, sources.used)
    if not rain.years:
        return empty
    et0 = monthly_et0(dataset, municipality_id, sources.et0) if sources.et0 else MonthlySeries("", {})
    first, last = min(rain.values), max(rain.values)
    points = []
    for year in range(first[0], last[0] + 1):
        # Solo los años cuya ventana proyectada cae entera en el periodo que la fuente publica para el municipio.
        historical = [(month.year + year - sowing_date.year, month.month) for month in window.months()]
        if historical[0] < first or historical[-1] > last:
            continue
        days = _historical_days(window, year)
        points.append(
            WaterPoint(
                year=year,
                precip_mm=_mm(window_rain_mm(window, _project(rain, window, year), days)),
                need_mm=_mm(window_etc_mm(window, _project(et0, window, year), days)),
            )
        )
    if all(point.precip_mm is None for point in points):
        return empty
    return WaterSeries(status=AVAILABLE, source_id=sources.used, points=points)


def supply_series(dataset: Dataset, municipality_id: str, crop_id: str, sowing_date: date) -> SupplySeries:
    """El área sembrada del semestre de la siembra, por año, de la fuente `supply.used` de la región (EVA).

    Solo esa fuente: si el dataset trae otras (FAOSTAT, reportes), no se mezclan (R1, R8). Hoy `supply_semester` no
    está en el dataset publicado: la llenarán HU-031 y HU-032; mientras tanto, la serie es `insufficient_data`.
    """
    source_id = signal_sources.get_signal_sources().for_region(dataset.region["id"])["supply"].used
    half = semester(sowing_date)
    empty = SupplySeries(status=INSUFFICIENT_DATA, source_id=source_id, semester=half, points=[])
    table = dataset.supply_semester
    if table is None:
        return empty
    rows = table.filter(
        (pl.col("municipality_id") == municipality_id)
        & (pl.col("crop_id") == crop_id)
        & (pl.col("semester") == half)
        & (pl.col("source_id") == source_id)
    ).sort("year")
    points = [
        SupplyPoint(year=int(year), planted_ha=planted, preliminary=preliminary)
        for year, planted, preliminary in rows.select("year", "planted_ha", "preliminary").iter_rows()
    ]
    if all(point.planted_ha is None for point in points):
        return empty
    return SupplySeries(status=AVAILABLE, source_id=source_id, semester=half, points=points)


def ndvi_series() -> NdviSeries:
    """El verdor normal del municipio por periodo de 16 días (1 a 23), de `ndvi_municipality_normal` (HU-208).

    Viene vacía con `insufficient_data` mientras `catalog/sources.yaml` no le asigne una fuente al verdor: hoy solo
    asigna las seis señales, y el verdor no es una. Nunca se elige una fuente por otra regla, como el orden alfabético
    (R1, R8; decidido por Felipe el 14 nov 2026, PR #104). `limitations` lo dice.
    """
    return NdviSeries(status=INSUFFICIENT_DATA, source_id=None, quality=None, points=[])


def _limitations(water: WaterSeries, supply: SupplySeries, ndvi: NdviSeries) -> list[str]:
    """Una por serie vacía, en el orden de la respuesta (R1)."""
    limitations = []
    if water.status == INSUFFICIENT_DATA:
        limitations.append(WATER_MISSING.format(source=water.source_id))
    if supply.status == INSUFFICIENT_DATA:
        limitations.append(SUPPLY_MISSING.format(source=supply.source_id, semester=supply.semester))
    if ndvi.status == INSUFFICIENT_DATA:
        limitations.append(NDVI_WITHOUT_SOURCE)
    return limitations


def trends(dataset: Dataset, municipality_id: str, crop_id: str, sowing_date: date) -> TrendsResponse:
    """Las tres series de una consulta ya validada (municipio y cultivo `kind = crop` del catálogo)."""
    water = water_series(dataset, municipality_id, crop_id, sowing_date)
    supply = supply_series(dataset, municipality_id, crop_id, sowing_date)
    ndvi = ndvi_series()
    return TrendsResponse(
        request=TrendsRequestEcho(municipality_id=municipality_id, crop_id=crop_id, sowing_date=sowing_date),
        water=water,
        supply=supply,
        ndvi=ndvi,
        limitations=_limitations(water, supply, ndvi),
        versions=Versions(dataset=dataset.version, rules=rules_version(dataset.rules_version)),
    )
