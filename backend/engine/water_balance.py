"""Balance hídrico de un cultivo por etapa y por mes (M7, HU-144; specs/01-reglas.md, «Las seis señales», `water`).

Para cada mes que toca la ventana de siembra:

- **Lo que necesita el cultivo** (`need_mm`) es la ET0 normal de la zona por el Kc de cada día de la ventana (FAO-56,
  `fao_56`). El Kc de un día sale de las etapas de la ficha como en la figura 25 de FAO-56: constante en la inicial;
  en línea recta de la inicial a la media en el desarrollo; constante en la media; y en línea recta de la media al Kc
  final en la etapa final (el `kc` de la etapa final de la ficha es el del final de la etapa). La ET0 normal de un mes
  se reparte por igual entre sus días.
- **La lluvia efectiva** sale de la lluvia del mes con las fórmulas del manual de la FAO para planear el riego
  (Brouwer y Heibloem, 1986, sección 4.2, `fao_manual_riego_3`): 0,8 P - 25 con más de 75 mm al mes y 0,6 P - 10 con
  75 mm o menos, nunca negativa. Se calcula con la lluvia de todo el mes y se toma la parte de los días de la ventana.
- **El suelo guarda agua entre lluvias** según su textura: lo que sobra en un mes queda en el suelo, hasta lo que la
  raíz puede usar sin estrés, y se gasta en los meses siguientes. Lo que puede guardar es el agua disponible de la
  textura (NRCS, National Engineering Handbook, parte 652, capítulo 2, tabla 2-1, `nrcs_neh652_cap2`) por la
  profundidad de la raíz y por la fracción que se puede gastar sin estrés (FAO-56, tabla 22, `fao_56_tabla_22`;
  ecuaciones 82 y 83: TAW = 1000 (θFC - θWP) Zr y RAW = p TAW).
- **El déficit** es lo que falta después de la lluvia efectiva y del agua guardada: lo que habría que regar.

Es un rango (R10): el déficit más bajo usa el agua disponible más alta de la textura y la raíz más profunda, y el más
alto, las más bajas. Se calcula para el año normal (`precip_normal_mm`) y para el año seco (`precip_dry_mm`); la señal
`water` usa el seco (decidido por Felipe el 11 de noviembre de 2026).

Supuestos, dichos en `docs/registro-de-decisiones.md` y aprobados por Felipe el 14 de noviembre de 2026 (PR #96):

- El suelo empieza la ventana sin agua guardada: no se sabe cuánta tiene el lote el día de la siembra, y es lo más
  prudente (nunca promete agua que puede no estar).
- La raíz tiene su profundidad máxima desde la siembra (FAO-56 la hace crecer): el agua guardada en las primeras
  etapas se sobrestima un poco, igual en todos los cultivos.
- `p` es el de la tabla 22, sin el ajuste por la ET del día (FAO-56, ecuación 84 en la nota de la tabla).

Sin la textura o sin la raíz de la ficha, el balance se hace sin agua guardada y `retention` es falso: quien lo llama
lo agrega a las limitaciones (R1). Sin el Kc de alguna etapa, no hay balance (`kc_missing`). Un mes sin ET0 o sin la
lluvia de la fuente usada no tiene déficit, y el total tampoco: nunca se suma con huecos (R1). Es una función pura:
no lee archivos ni el reloj; el clima, el suelo y la ficha llegan como argumentos (R4, R6). Misma entrada, mismo
resultado.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from backend.engine.stages import CropWindow

# Las fuentes del método (R8): el pipeline las publica en `sources` desde `catalog/crops.yaml`.
SOURCE_IDS = {
    "need": "fao_56",
    "effective_rain": "fao_manual_riego_3",
    "available_water": "nrcs_neh652_cap2",
    "root_zone": "fao_56_tabla_22",
}

# Agua disponible por textura, en m³ de agua por m³ de suelo (es la misma cifra que la tabla da en pulgadas por
# pulgada): NRCS, NEH parte 652, cap. 2 (septiembre de 1997), tabla 2-1, p. 2-5, con el rango de cada clase. Las
# clases son las del triángulo del USDA con los nombres del IGAC que publica `texture_class` (HU-181). La arena, la
# arena franca y el franco arenoso son las filas «Sand», «Loamy sand» y «Sandy loam» (sin «fine» ni «coarse»).
AVAILABLE_WATER = {
    "arenoso": (0.01, 0.03),
    "arenoso franco": (0.06, 0.08),
    "franco arenoso": (0.11, 0.13),
    "franco": (0.16, 0.18),
    "franco limoso": (0.19, 0.21),
    "limoso": (0.16, 0.18),
    "franco arcillo arenoso": (0.14, 0.16),
    "franco arcilloso": (0.19, 0.21),
    "franco arcillo limoso": (0.19, 0.21),
    "arcillo arenoso": (0.15, 0.17),
    "arcillo limoso": (0.15, 0.17),
    "arcilloso": (0.14, 0.16),
}

KC_MISSING = "kc_missing"
NORMAL, DRY = "normal", "dry"
YEARS = (NORMAL, DRY)
# 1 mm de agua sobre 1 ha son 10 m³.
M3_PER_MM_HA = 10.0

Range = tuple[float, float]


@dataclass(frozen=True)
class MonthClimate:
    """El clima normal de la zona en un mes del año: la ET0 normal (`climate_month.et0_normal_mm`) y la lluvia del año
    normal y del año seco de la fuente que dice `sources.yaml` (`precip_normal_mm` y `precip_dry_mm`). Nulo: sin dato."""

    et0_mm: float | None
    rain_normal_mm: float | None
    rain_dry_mm: float | None

    def rain(self, year: str) -> float | None:
        return self.rain_normal_mm if year == NORMAL else self.rain_dry_mm


@dataclass(frozen=True)
class RootZone:
    """La raíz del cultivo según su ficha (FAO-56, tabla 22): profundidad máxima efectiva, en m, y fracción del agua
    disponible que se puede gastar sin estrés."""

    depth_min_m: float
    depth_max_m: float
    depletion_p: float


@dataclass(frozen=True)
class WaterMonthBalance:
    year: int
    month: int
    days: int
    stages: tuple[str, ...]
    status: str
    need_mm: float | None
    # La lluvia que cae en los días de la ventana (la de todo el mes, en proporción a sus días), por año.
    rain_mm: dict[str, float | None]
    # El déficit [mínimo, máximo] de cada año; nulo si falta la lluvia de ese año o la ET0 del mes.
    deficit_mm: dict[str, Range | None]


@dataclass(frozen=True)
class WaterBalance:
    status: str
    reason: str | None
    months: tuple[WaterMonthBalance, ...]
    # Si se tuvo en cuenta el agua que guarda el suelo. Falso sin textura o sin raíz: va a las limitaciones (R1).
    retention: bool
    need_mm: float | None
    deficit_mm: dict[str, Range | None]

    def covered_pct(self, year: str = DRY) -> Range | None:
        """Qué porcentaje de lo que necesita el cultivo en la ventana cubren la lluvia y el agua guardada, [mínimo,
        máximo]. Es lo que califica la señal `water` (con el año seco). Nulo sin balance completo (R1)."""
        deficit = self.deficit_mm.get(year)
        if self.need_mm is None or deficit is None:
            return None
        if self.need_mm == 0:
            return (100.0, 100.0)
        low, high = (round(max(0.0, 100 * (1 - d / self.need_mm)), 1) for d in (deficit[1], deficit[0]))
        return (low, high)


def root_zone(crop: dict) -> RootZone | None:
    """La raíz de la ficha del cultivo (`crops`): nula si falta alguno de sus tres valores (R1)."""
    values = [crop.get(k) for k in ("root_depth_min_m", "root_depth_max_m", "depletion_p")]
    if any(v is None or v != v for v in values):
        return None
    return RootZone(*(float(v) for v in values))


def effective_rain_mm(rain_mm: float) -> float:
    """La lluvia efectiva de un mes (FAO, manual 3 de riego, 1986, sección 4.2), nunca negativa."""
    value = 0.8 * rain_mm - 25 if rain_mm > 75 else 0.6 * rain_mm - 10
    return max(0.0, value)


def storable_mm(texture_class: str | None, root: RootZone | None) -> Range | None:
    """El agua que el suelo puede guardar para el cultivo sin estrés, RAW = p × 1000 × agua disponible × raíz, en mm,
    [mínimo, máximo]. Nulo sin textura conocida o sin raíz (R1)."""
    water = AVAILABLE_WATER.get(texture_class or "")
    if water is None or root is None:
        return None
    return (
        root.depletion_p * 1000 * water[0] * root.depth_min_m,
        root.depletion_p * 1000 * water[1] * root.depth_max_m,
    )


def _daily_kc(window: CropWindow) -> dict[date, float] | None:
    """El Kc de cada día de la ventana (FAO-56, figura 25). Nulo si falta el Kc que pide alguna etapa."""
    spans = [period.span for period in window.periods]
    by_stage = {span.stage: span.kc for span in spans}
    initial, mid = by_stage.get("initial"), by_stage.get("mid")
    result: dict[date, float] = {}
    for period in window.periods:
        stage, length = period.span.stage, period.span.days
        if stage == "initial":
            start = end = initial
        elif stage == "development":
            start, end = initial, mid
        elif stage == "mid":
            start = end = mid
        else:
            start, end = mid, period.span.kc
        if start is None or end is None:
            return None
        for offset in range(length):
            # En las etapas de cambio, el Kc del día i (de 1 a L) es el de la recta en i / L (FAO-56, ecuación 66).
            result[period.start + timedelta(days=offset)] = start + (end - start) * (offset + 1) / length
    return result


def _month_rain(climate: MonthClimate | None, year: str, share: float) -> tuple[float | None, float | None]:
    """La lluvia de los días de la ventana en el mes y su parte efectiva."""
    rain = None if climate is None else climate.rain(year)
    if rain is None:
        return None, None
    return rain * share, effective_rain_mm(rain) * share


def water_balance(
    window: CropWindow, climate: dict[int, MonthClimate], texture_class: str | None = None, root: RootZone | None = None
) -> WaterBalance:
    """El balance de la ventana, mes por mes. `climate` va por mes del año (1 a 12): el clima normal de la zona."""
    kc = _daily_kc(window)
    if kc is None:
        return WaterBalance(INSUFFICIENT_DATA, KC_MISSING, (), False, None, {NORMAL: None, DRY: None})
    storable = storable_mm(texture_class, root)
    capacity = {"low": storable[1], "high": storable[0]} if storable else {"low": 0.0, "high": 0.0}
    # El agua guardada al empezar el mes, por año y por extremo del rango («low» da el déficit mínimo).
    stored = {(year, end): 0.0 for year in YEARS for end in capacity}
    months, total_need, total = [], 0.0, {(year, end): 0.0 for year in YEARS for end in capacity}
    complete = {year: True for year in YEARS}
    for month in window.months():
        days_in_month = calendar.monthrange(month.year, month.month)[1]
        share = month.days / days_in_month
        normal = climate.get(month.month)
        et0 = None if normal is None else normal.et0_mm
        need = None
        if et0 is not None:
            first = max(window.sowing_date, date(month.year, month.month, 1))
            need = sum(et0 / days_in_month * kc[first + timedelta(days=d)] for d in range(month.days))
            total_need += need
        rain, deficit = {}, {}
        for year in YEARS:
            rain[year], effective = _month_rain(normal, year, share)
            if need is None or effective is None:
                deficit[year] = None
                complete[year] = False
                # Sin dato no se sabe cuánta agua quedó: el mes siguiente empieza sin agua guardada, como la siembra.
                for end in capacity:
                    stored[(year, end)] = 0.0
                continue
            values = {}
            for end, cap in capacity.items():
                balance = effective - need
                if balance >= 0:
                    stored[(year, end)] = min(cap, stored[(year, end)] + balance)
                    values[end] = 0.0
                else:
                    used = min(stored[(year, end)], -balance)
                    stored[(year, end)] -= used
                    values[end] = -balance - used
                total[(year, end)] += values[end]
            deficit[year] = (round(values["low"], 1), round(values["high"], 1))
        status = AVAILABLE if need is not None and any(value is not None for value in deficit.values()) else INSUFFICIENT_DATA
        months.append(
            WaterMonthBalance(
                year=month.year,
                month=month.month,
                days=month.days,
                stages=month.stages,
                status=status,
                need_mm=None if need is None else round(need, 1),
                rain_mm={year: None if value is None else round(value, 1) for year, value in rain.items()},
                deficit_mm=deficit,
            )
        )
    has_need = all(month.need_mm is not None for month in months)
    deficit_total = {
        year: (round(total[(year, "low")], 1), round(total[(year, "high")], 1)) if complete[year] and has_need else None for year in YEARS
    }
    status = AVAILABLE if has_need and any(value is not None for value in deficit_total.values()) else INSUFFICIENT_DATA
    return WaterBalance(
        status=status,
        reason=None,
        months=tuple(months),
        retention=storable is not None,
        need_mm=round(total_need, 1) if has_need else None,
        deficit_mm=deficit_total,
    )


def volume_m3(deficit_mm: Range | None, area_ha: float) -> Range | None:
    """El volumen de un déficit sobre un área: 1 mm en 1 ha son 10 m³. Nulo si el déficit es nulo."""
    if deficit_mm is None:
        return None
    return (round(deficit_mm[0] * M3_PER_MM_HA * area_ha, 1), round(deficit_mm[1] * M3_PER_MM_HA * area_ha, 1))
