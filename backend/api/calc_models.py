"""Modelos de los endpoints de cálculo (HU-012; specs/02-contratos.md, «Cuerpos y respuestas»).

Son el contrato en código: de aquí sale el OpenAPI y, de él, los tipos de la web (`web/src/api/schema.d.ts`). Los
valores permitidos son los de `specs/01-reglas.md` («Valores permitidos»). Los ejemplos de cada estado están en
`backend/api/calc_examples.py` y una prueba revisa que todos cumplan estos modelos.
"""

import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["available", "insufficient_data", "not_applicable"]
Level = Literal["favorable", "moderate", "unfavorable"]
Light = Literal["green", "yellow", "red", "not_evaluable"]
Action = Literal["sow", "other_window", "rotate", "review_data"]
Suitability = Literal["suitable", "not_suitable", "insufficient_data"]
WeightsBasis = Literal["default", "farmer"]
HarvestBasis = Literal["calendar", "normal_year"]
Basis = Literal["lot", "municipality"]
SignalName = Literal["water", "frost", "heat", "soil", "supply", "market"]
HealthCriterionName = Literal["nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion"]
Quality = Literal["ok", "partial"]

MunicipalityId = Annotated[str, Field(pattern=r"^\d{5}$", examples=["15646"])]
CropId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40, examples=["papa"])]
Weight = Annotated[int, Field(ge=0, le=5)]
Score = Annotated[int, Field(ge=0, le=100)]


class Versions(BaseModel):
    """Las versiones del dataset y de las reglas con que se calculó (R4)."""

    dataset: str | None
    rules: str | None


class SignalWeights(BaseModel):
    """El peso de 0 a 5 de cada señal del P0. Todas en 0 responde 422."""

    model_config = ConfigDict(extra="forbid")

    water: Weight
    frost: Weight
    heat: Weight
    soil: Weight
    supply: Weight
    market: Weight

    @model_validator(mode="after")
    def _not_all_zero(self) -> "SignalWeights":
        if not any(self.model_dump().values()):
            raise ValueError("al menos una señal debe pesar más de 0")
        return self


class RotationWeights(BaseModel):
    """El peso de 0 a 5 de cada criterio de las estrategias. Todos en 0 responde 422."""

    model_config = ConfigDict(extra="forbid")

    water: Weight
    soil: Weight
    income: Weight
    risk: Weight

    @model_validator(mode="after")
    def _not_all_zero(self) -> "RotationWeights":
        if not any(self.model_dump().values()):
            raise ValueError("al menos un criterio debe pesar más de 0")
        return self


# ------------------------------------------------------------------ diagnóstico


class DiagnosisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipality_id: MunicipalityId
    crop_id: CropId
    sowing_date: date
    irrigated: bool | None = None
    priorities: SignalWeights | None = None
    lot_id: uuid.UUID | None = None


class SuitabilityResult(BaseModel):
    level: Suitability
    # Nota informativa de 0 a 100: no entra al semáforo ni al orden.
    score: Score | None
    basis: Basis
    tmean_annual_c: float | None
    altitude_m: float | None
    reasons: list[str]


class SupplySemester(BaseModel):
    year: int
    semester: Literal["A", "B"]
    preliminary: bool


class Window(BaseModel):
    sowing_start: date
    harvest_estimate: date
    harvest_basis: HarvestBasis
    supply_semester: SupplySemester | None


class LightResult(BaseModel):
    light: Light
    action: Action
    high_risk: bool
    weights_basis: WeightsBasis
    limiting_signal: SignalName | None
    reasons: list[str]


class SourceValue(BaseModel):
    """Una fuente de un indicador, para contrastar. `used` dice cuál calculó la señal; nunca se mezclan."""

    source_id: str
    indicator: str
    value: float | None
    unit: str
    period: str | None = None
    preliminary: bool | None = None
    used: bool


class Signal(BaseModel):
    status: Status
    level: Level | None
    critical: bool
    score: Score | None
    counts: bool
    indicators: list[str]
    reasons: list[str]
    sources: list[SourceValue] | None = None


class WindowSummary(BaseModel):
    sowing_start: date
    harvest_estimate: date
    limiting_signal: SignalName | None
    limiting_score: Score | None
    weighted_score: Score | None
    high_risk: bool


class DiagnosisCore(BaseModel):
    """Lo que trae el diagnóstico de una ventana; un ciclo de una estrategia lo trae igual (HU-213)."""

    suitability: SuitabilityResult
    # Nulos cuando el cultivo no es apto para la zona: no se evalúan ventanas.
    window: Window | None
    overall: LightResult
    overall_default: LightResult
    weights: SignalWeights
    signals: dict[SignalName, Signal] | None
    limitations: list[str]
    versions: Versions


class DiagnosisRequestEcho(BaseModel):
    municipality_id: str
    crop_id: str
    sowing_date: date
    irrigated: bool | None
    lot_id: uuid.UUID | None


class DiagnosisResponse(DiagnosisCore):
    request: DiagnosisRequestEcho
    # Solo cuando alguna acción es `other_window`: hasta tres, nunca de alto riesgo.
    best_windows: list[WindowSummary] | None = None


# ------------------------------------------------------------------ estrategias de rotación


class RotationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipality_id: MunicipalityId
    sowing_date: date
    previous_crop_ids: list[CropId] = Field(default_factory=list, max_length=3)
    current_crop_ids: list[CropId] | None = Field(None, min_length=2, max_length=3)
    cycles: Literal[2, 3] = 3
    priorities: RotationWeights
    signal_priorities: SignalWeights | None = None
    irrigated: bool | None = None
    lot_id: uuid.UUID | None = None


class Scores(BaseModel):
    water: Score | None
    soil: Score | None
    income: Score | None
    risk: Score | None


class VsCurrent(BaseModel):
    """Cuánto gana (positivo) o pierde una estrategia frente a la rotación actual. Nulo si no califica en alguna."""

    water: int | None
    soil: int | None
    income: int | None
    risk: int | None
    total: int | None


class Cycle(BaseModel):
    cycle: Annotated[int, Field(ge=1, le=3)]
    crop_id: str
    sowing_date: date
    # En un descanso, hasta cuándo dura, con la duración de su ficha.
    harvest_estimate: date
    harvest_basis: HarvestBasis
    # Nulos en un descanso: no tiene diagnóstico.
    light: Light | None
    light_default: Light | None
    limiting_signal: SignalName | None
    high_risk: bool
    diagnosis: DiagnosisCore | None = None


class HealthCriterion(BaseModel):
    status: Status
    level: Level | None
    rule_ids: list[str]
    # Las fuentes de esas reglas (R8), para que la web las cite sin otro catálogo. Vacía sin regla con fuente.
    source_ids: list[str]
    reasons: list[str]


ExclusionKind = Literal["rule", "not_suitable", "soil_ph", "high_risk"]


class Issue(BaseModel):
    """Por qué una estrategia no cumple: la regla que viola, el cultivo no apto, el pH o el ciclo de alto riesgo."""

    cycle: Annotated[int, Field(ge=1, le=3)]
    kind: ExclusionKind
    rule_id: str | None = None
    signal: SignalName | None = None
    reason: str
    # De dónde sale el motivo (R8): la fuente de la regla, de la ficha del cultivo, del suelo o del clima de la señal.
    source_ids: list[str]


class Exclusion(Issue):
    crop_ids: list[str]


class Strategy(BaseModel):
    # Nulo en la rotación actual: no entra al orden.
    rank: int | None
    kind: Literal["current", "suggested"]
    crop_ids: list[str]
    total_score: Score | None
    scores: Scores
    vs_current: VsCurrent | None = None
    cycles: list[Cycle]
    soil_health: dict[HealthCriterionName, HealthCriterion]
    # Solo en la rotación actual: nunca se excluye, pero dice por qué no cumple (decisión 14).
    issues: list[Issue] = Field(default_factory=list)
    reasons: list[str]
    limitations: list[str]


class RotationResponse(BaseModel):
    strategies: list[Strategy] = Field(max_length=10)
    current_strategy: Strategy | None
    excluded: list[Exclusion] = Field(max_length=10)
    excluded_counts: dict[ExclusionKind, int]
    weights: RotationWeights
    soil_basis: Basis
    slope_basis: Basis
    limitations: list[str]
    versions: Versions


# ------------------------------------------------------------------ plan de agua


class WaterPlanCrop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_id: CropId
    area_pct: Annotated[float, Field(gt=0, le=100)]
    sowing_date: date


class WaterPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    municipality_id: MunicipalityId
    total_area_ha: Annotated[float, Field(gt=0, le=100_000)]
    crops: list[WaterPlanCrop] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def _at_most_100(self) -> "WaterPlanRequest":
        if sum(crop.area_pct for crop in self.crops) > 100:
            raise ValueError("los porcentajes de área pasan de 100")
        return self


Range = Annotated[list[float], Field(min_length=2, max_length=2, description="[mínimo, máximo] (R10)")]


class YearRange(BaseModel):
    normal: Range | None
    dry: Range | None


class RainYear(BaseModel):
    normal: float | None
    dry: float | None


class WaterMonth(BaseModel):
    year: int
    month: Annotated[int, Field(ge=1, le=12)]
    status: Status = "available"
    stage: str | None
    need_mm: float | None
    rain_mm: RainYear
    deficit_mm: YearRange
    volume_m3: YearRange


class WaterPlanCropResult(BaseModel):
    crop_id: str
    area_ha: float
    sowing_date: date
    harvest_estimate: date | None
    harvest_basis: HarvestBasis | None
    months: list[WaterMonth]
    total_volume_m3: YearRange


class FarmMonth(BaseModel):
    year: int
    month: Annotated[int, Field(ge=1, le=12)]
    volume_m3: YearRange


class FarmWater(BaseModel):
    months: list[FarmMonth]
    total_volume_m3: YearRange


class SoilMoisture(BaseModel):
    month: Annotated[int, Field(ge=1, le=12)]
    source_id: str
    indicator: str
    value: float | None
    unit: str


class WaterSources(BaseModel):
    rain: str | None
    et0: str | None
    soil: str | None


class WaterPlanResponse(BaseModel):
    request: WaterPlanRequest
    crops: list[WaterPlanCropResult]
    farm: FarmWater
    soil_moisture: list[SoilMoisture]
    sources: WaterSources
    soil_basis: Basis
    limitations: list[str]
    versions: Versions


# ------------------------------------------------------------------ qué cambió


class Period(BaseModel):
    period_id: str
    start_year: int
    end_year: int
    source_id: str


class Periods(BaseModel):
    before: Period
    after: Period


class Change(BaseModel):
    status: Status
    before: float | None
    after: float | None
    change: float | None


class MonthChange(BaseModel):
    month: Annotated[int, Field(ge=1, le=12)]
    frost_freq_pct: Change
    precip_normal_mm: Change
    tmax_p90_c: Change


class MonthWindow(BaseModel):
    month: Annotated[int, Field(ge=1, le=12)]
    limiting_signal: SignalName | None
    limiting_score: Score | None
    high_risk: bool


class BestWindowsByPeriod(BaseModel):
    before: list[MonthWindow] = Field(max_length=3)
    after: list[MonthWindow] = Field(max_length=3)


class ChangesRequestEcho(BaseModel):
    municipality_id: str
    crop_id: str
    irrigated: bool | None


class ChangesResponse(BaseModel):
    request: ChangesRequestEcho
    periods: Periods
    # Solo si `sources.yaml` da la lluvia a una fuente con otros periodos (GPM IMERG, desde 2001).
    precip_periods: Periods | None = None
    suitability: SuitabilityResult
    months: list[MonthChange]
    best_windows: BestWindowsByPeriod
    weights_basis: WeightsBasis
    reasons: list[str]
    limitations: list[str]
    versions: Versions


# ------------------------------------------------------------------ tendencias


class TrendsRequestEcho(BaseModel):
    municipality_id: str
    crop_id: str
    sowing_date: date


class WaterPoint(BaseModel):
    year: int
    precip_mm: float | None
    need_mm: float | None


class SupplyPoint(BaseModel):
    year: int
    planted_ha: float | None
    preliminary: bool | None


class NdviPoint(BaseModel):
    period: Annotated[int, Field(ge=1, le=23)]
    ndvi_normal: float | None


class WaterSeries(BaseModel):
    status: Status
    source_id: str | None
    unit: Literal["mm"] = "mm"
    points: list[WaterPoint]


class SupplySeries(BaseModel):
    status: Status
    source_id: str | None
    unit: Literal["ha"] = "ha"
    semester: Literal["A", "B"] | None
    points: list[SupplyPoint]


class NdviSeries(BaseModel):
    status: Status
    source_id: str | None
    quality: Quality | None
    points: list[NdviPoint]


class TrendsResponse(BaseModel):
    request: TrendsRequestEcho
    water: WaterSeries
    supply: SupplySeries
    ndvi: NdviSeries
    versions: Versions


# ------------------------------------------------------------------ suelo del municipio


class SoilRange(BaseModel):
    value: float | None
    p05: float | None
    p95: float | None


class MunicipalitySoil(BaseModel):
    """El suelo estimado del municipio (`soil_municipality`): una estimación de 250 m, no del lote (R10)."""

    municipality_id: str
    ph: SoilRange
    soc_g_kg: SoilRange
    nitrogen_g_kg: float | None
    clay_pct: float | None
    sand_pct: float | None
    silt_pct: float | None
    texture_class: str | None
    slope_pct: float | None
    cells: int | None
    quality: Quality
    source_id: str
    versions: Versions


# ------------------------------------------------------------------ errores


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorBody(BaseModel):
    """La forma de todo error de la API (contrato, «Errores»)."""

    error: ErrorDetail
