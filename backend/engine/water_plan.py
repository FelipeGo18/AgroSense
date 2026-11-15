"""El plan de agua de una finca o de un ciclo de una estrategia (M7, HU-146; specs/02-contratos.md, «Cuerpo de
`POST /api/v1/water-plans`»).

Por cada cultivo del plan y por cada mes de su ventana, el balance hídrico de HU-144 (`water_balance.py`): lo que pide
el cultivo, la lluvia del año normal y del año seco de la fuente que dice `catalog/sources.yaml`, el déficit como rango
(R10) y su volumen en m³ sobre el área del cultivo (`volume_m3`). No hay otra cuenta del agua: este módulo solo agrega
encima la etapa del mes, el volumen, la suma de la finca, la humedad del suelo para contrastar y las limitaciones.

- **La etapa del mes** es la que ocupa la mayor parte del mes (`WindowMonth.main_stage`); si empatan, la primera.
- **Un mes sin la lluvia de la fuente usada** es `insufficient_data`, con la lluvia, el déficit y el volumen nulos; sin
  la ET0, también sin lo que pide el cultivo. El total del cultivo es la suma de sus meses, nulo si le falta alguno (R1).
- **La finca** suma, por cada mes que toca algún cultivo, el volumen de los cultivos que lo tocan: el mínimo con los
  mínimos y el máximo con los máximos. Si a un cultivo le falta ese mes, el volumen de la finca de ese mes es nulo; y el
  total, si le falta el total a algún cultivo. Nunca se suma con huecos (R1). Un cultivo sin etapas no dice qué meses
  toca: ningún mes de la finca se puede sumar.
- **Un descanso** (`fallow`) no es un cultivo: no tiene etapas ni Kc, no se le inventa agua (R5) y no es un dato que
  falta, así que no cambia la finca. Aprobado por Haider (docs/registro-de-decisiones.md, PR #135).
- **La humedad del suelo** de la zona (NASA POWER y, cuando exista, SMAP) se muestra para contrastar: la normal de cada
  mes del año que toca alguna ventana, por fuente. No entra al déficit (decisión 11).

Es una estimación con el clima de la zona, no una medición del lote (R10), y lo dice siempre. Función pura (R6): no lee
archivos, ni el dataset, ni el reloj; misma entrada, mismo resultado (R4). No guarda nada (R9).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from backend.engine.stages import CropWindow, WindowMonth
from backend.engine.water_balance import AVAILABLE_WATER, KC_MISSING, YEARS, MonthClimate, Range, RootZone, volume_m3, water_balance
from backend.engine.water_notes import NO_RETENTION, RainSource, missing_data
from common.text import capitalized, of

# El rótulo de estimación del contrato (R10): va siempre.
ESTIMATE = "Es una estimación con el clima de la zona: verifique la humedad del suelo en su lote"

ByYear = dict[str, Range | None]
MonthKey = tuple[int, int]


def fallow_note(name: str) -> str:
    """Por qué un descanso no trae agua. `name` lleva su artículo («el descanso»)."""
    return (
        f"{capitalized(name)} no es un cultivo: no tiene etapas ni Kc, así que su agua no se calcula y no entra en el volumen de la finca"
    )


def no_window_note(name: str) -> str:
    """Por qué un cultivo sin etapas no trae agua: no se sabe cuánto dura ni qué meses toca (R1)."""
    return f"La ficha {of(name)} no trae sus etapas: su agua no se calcula y el volumen de la finca queda sin dato"


def kc_missing_note(name: str) -> str:
    """Por qué un cultivo sin el Kc de alguna etapa no trae agua (HU-144, `KC_MISSING`)."""
    return (
        f"La ficha {of(name)} no trae con fuente el Kc de todas sus etapas: su agua no se calcula y el volumen de la finca "
        "queda sin dato en sus meses"
    )


def no_root_note(name: str) -> str:
    """Con la textura del suelo, pero sin la raíz del cultivo en su ficha: ese cultivo va sin el agua guardada."""
    return (
        f"El agua {of(name)} se calculó sin la que guarda el suelo, porque su ficha no trae la raíz con fuente: puede faltar "
        "menos agua de la que se dice. Verifique la humedad del suelo en campo."
    )


# `kind` del descanso en el catálogo (`crops`): no es un cultivo y no tiene agua.
FALLOW = "fallow"


@dataclass(frozen=True)
class PlanCrop:
    """Un cultivo del plan, tal como llega en la consulta y en su ficha. `name` lleva su artículo («la papa»), para las
    limitaciones; `kind` es el de la ficha (`crop`, `cover` o `fallow`); `area_pct`, su parte del área de la
    finca. `window` es su ventana por calendario (`stages.crop_window`; nula sin etapas) y `root`, la raíz de su ficha
    (`water_balance.root_zone`; nula si falta)."""

    crop_id: str
    name: str
    kind: str | None
    area_pct: float
    sowing_date: date
    window: CropWindow | None
    root: RootZone | None

    @property
    def fallow(self) -> bool:
        return self.kind == FALLOW

    def area_ha(self, total_area_ha: float) -> float:
        """Su área en hectáreas: su porcentaje del área de la finca."""
        return round(total_area_ha * self.area_pct / 100, 4)


class MoistureNormal(Protocol):
    """La humedad del suelo normal de la zona según una fuente, por mes del año (1 a 12), en su unidad. Nulo: sin dato.
    La lee la API del dataset (`water_signals.Wetness`)."""

    @property
    def source_id(self) -> str: ...

    @property
    def indicator(self) -> str: ...

    @property
    def unit(self) -> str: ...

    @property
    def by_month(self) -> Mapping[int, float | None]: ...


@dataclass(frozen=True)
class PlanMonth:
    year: int
    month: int
    status: str
    stage: str | None
    need_mm: float | None
    rain_mm: dict[str, float | None]
    deficit_mm: ByYear
    volume_m3: ByYear


@dataclass(frozen=True)
class CropPlan:
    crop_id: str
    area_ha: float
    sowing_date: date
    harvest_estimate: date | None
    harvest_basis: str | None
    months: tuple[PlanMonth, ...]
    total_volume_m3: ByYear


@dataclass(frozen=True)
class FarmMonth:
    year: int
    month: int
    volume_m3: ByYear


@dataclass(frozen=True)
class FarmWater:
    months: tuple[FarmMonth, ...]
    total_volume_m3: ByYear


@dataclass(frozen=True)
class MoistureMonth:
    month: int
    source_id: str
    indicator: str
    value: float | None
    unit: str


@dataclass(frozen=True)
class WaterPlan:
    crops: tuple[CropPlan, ...]
    farm: FarmWater
    soil_moisture: tuple[MoistureMonth, ...]
    # Si algún cultivo usó la textura del suelo (el agua que guarda): la API cita entonces la fuente del suelo.
    soil_used: bool
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class _FarmPart:
    """Lo que un cultivo con ventana aporta a la finca: los meses que toca y su volumen por mes y en total (nulos sin
    balance)."""

    keys: frozenset[MonthKey]
    volumes: Mapping[MonthKey, ByYear] | None
    total: ByYear


def _nothing() -> ByYear:
    return dict.fromkeys(YEARS)


def _sum(parts: Sequence[Range | None]) -> Range | None:
    """Mínimos con mínimos y máximos con máximos. Nulo si falta alguno, o si no hay nada que sumar (R1)."""
    if not parts or any(part is None for part in parts):
        return None
    return (round(sum(part[0] for part in parts), 1), round(sum(part[1] for part in parts), 1))


def _key(month: WindowMonth) -> MonthKey:
    return (month.year, month.month)


def _farm(parts: Sequence[_FarmPart], unknown_months: bool) -> FarmWater:
    """La finca: el volumen sumado por mes y en total. `unknown_months`: algún cultivo sin etapas, que no dice qué meses
    toca, así que ningún mes se puede sumar (R1)."""
    months = []
    for key in sorted({key for part in parts for key in part.keys}):
        touching = [part for part in parts if key in part.keys]
        volume = {
            year: None if unknown_months else _sum([None if part.volumes is None else part.volumes[key][year] for part in touching])
            for year in YEARS
        }
        months.append(FarmMonth(key[0], key[1], volume))
    total = {year: None if unknown_months else _sum([part.total[year] for part in parts]) for year in YEARS}
    return FarmWater(tuple(months), total)


def _moisture(touched: Sequence[WindowMonth], moisture: Sequence[MoistureNormal]) -> tuple[MoistureMonth, ...]:
    """La humedad normal de cada mes del año que toca alguna ventana, por fuente y en orden de aparición, sin repetir
    mes. Sin dato de un mes, nula (R1): nunca se rellena con otra fuente."""
    months = list(dict.fromkeys(month.month for month in sorted(touched, key=_key)))
    readings = []
    for source in moisture:
        for month in months:
            value = source.by_month.get(month)
            value = None if value is None else round(value, 2)
            readings.append(MoistureMonth(month, source.source_id, source.indicator, value, source.unit))
    return tuple(readings)


def water_plan(
    crops: Sequence[PlanCrop],
    total_area_ha: float,
    climate: Mapping[int, MonthClimate],
    texture_class: str | None,
    rain: RainSource,
    moisture: Sequence[MoistureNormal] = (),
) -> WaterPlan:
    """El plan de agua (ver el módulo). `climate` es el clima normal de la zona por mes del año (1 a 12), con la lluvia
    de la fuente que calcula el agua (`rain`); `texture_class`, la textura del suelo del municipio (nula: sin el agua
    que guarda el suelo); `moisture`, la humedad del suelo de cada fuente para contrastar. Los cultivos salen en el
    orden en que llegan."""
    climate = dict(climate)
    texture_known = (texture_class or "") in AVAILABLE_WATER
    results: list[CropPlan] = []
    parts: list[_FarmPart] = []
    crop_notes: list[str] = []
    retention_notes: list[str] = []
    touched: list[WindowMonth] = []
    no_rain: dict[MonthKey, WindowMonth] = {}
    no_et0: dict[MonthKey, WindowMonth] = {}
    unknown_months, soil_used = False, False

    for crop in crops:
        area_ha = crop.area_ha(total_area_ha)
        window = None if crop.fallow else crop.window
        empty = CropPlan(
            crop.crop_id,
            area_ha,
            crop.sowing_date,
            None if window is None else window.harvest_estimate,
            None if window is None else window.harvest_basis,
            (),
            _nothing(),
        )
        if crop.fallow:
            crop_notes.append(fallow_note(crop.name))
            results.append(empty)
            continue
        if window is None:
            crop_notes.append(no_window_note(crop.name))
            unknown_months = True
            results.append(empty)
            continue
        window_months = window.months()
        touched.extend(window_months)
        keys = frozenset(_key(month) for month in window_months)
        balance = water_balance(window, climate, texture_class, crop.root)
        if balance.reason == KC_MISSING:
            crop_notes.append(kc_missing_note(crop.name))
            parts.append(_FarmPart(keys, None, _nothing()))
            results.append(empty)
            continue
        soil_used = soil_used or balance.retention
        if not balance.retention:
            # Sin la textura vale para todos los cultivos; con ella, falta la raíz de este.
            retention_notes.append(no_root_note(crop.name) if texture_known else NO_RETENTION)
        for month in window_months:
            normal = climate.get(month.month)
            if normal is None or normal.rain_normal_mm is None or normal.rain_dry_mm is None:
                no_rain.setdefault(_key(month), month)
            if normal is None or normal.et0_mm is None:
                no_et0.setdefault(_key(month), month)
        months = tuple(
            PlanMonth(
                year=balanced.year,
                month=balanced.month,
                status=balanced.status,
                stage=month.main_stage,
                need_mm=balanced.need_mm,
                rain_mm=dict(balanced.rain_mm),
                deficit_mm=dict(balanced.deficit_mm),
                volume_m3={year: volume_m3(balanced.deficit_mm[year], area_ha) for year in YEARS},
            )
            for balanced, month in zip(balance.months, window_months, strict=True)
        )
        # La suma de sus meses, no el déficit total del balance (redondeado aparte): así los meses dan el total.
        total = {year: _sum([month.volume_m3[year] for month in months]) for year in YEARS}
        parts.append(_FarmPart(keys, {(month.year, month.month): month.volume_m3 for month in months}, total))
        results.append(CropPlan(crop.crop_id, area_ha, crop.sowing_date, window.harvest_estimate, window.harvest_basis, months, total))

    missing = missing_data(rain, [no_rain[key] for key in sorted(no_rain)], [no_et0[key] for key in sorted(no_et0)])
    caveat = (rain.caveat,) if rain.caveat else ()
    limitations = (ESTIMATE, *crop_notes, *retention_notes, *missing, *caveat)
    return WaterPlan(
        crops=tuple(results),
        farm=_farm(parts, unknown_months),
        soil_moisture=_moisture(touched, moisture),
        soil_used=soil_used,
        limitations=tuple(dict.fromkeys(limitations)),
    )
