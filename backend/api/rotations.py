"""Las estrategias de rotación con la forma del contrato (HU-084; `POST /api/v1/rotations`).

Es la capa delgada de la API (R6): pasa el catálogo, las reglas de rotación y el suelo y la pendiente de la zona (o del
lote) a los tipos del motor, y arma la respuesta con lo que el motor devuelve:

1. las candidatas (`candidates`), sin la igual a la rotación actual (`drop_current`, HU-223), antes de cortar a 10;
2. el filtro de HU-081 (`StrategyCycles.filter`): reglas, aptitud, pH y alto riesgo, con `excluded` y sus conteos;
3. de cada sugerida que pasa, sus ciclos con su diagnóstico (HU-213), su salud del suelo (HU-212), sus criterios y su
   total (HU-082), su `vs_current` (HU-223) y sus razones (HU-083), y el orden (`rank_strategies`);
4. la rotación actual (decisión 14), con el mismo cálculo y sus motivos en `issues`: nunca se excluye (R3).

No lee el reloj más allá de lo que valida la ruta, no escribe en la base de datos ni guarda la consulta (R9).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.api.calc_models import (
    Exclusion,
    HealthCriterion,
    Issue,
    RotationResponse,
    Scores,
    Strategy,
    VsCurrent,
)
from backend.api.lot_soil import zone_soil, zone_terrain
from backend.api.soil_signals import LOT_SOIL_LIMITATION
from backend.api.strategy_cycles import StrategyCycles
from backend.api.window_diagnosis import WindowQuery, suitability_result
from backend.config.versions import rules_version
from backend.dataset import NON_SOIL_SOURCE, Dataset
from backend.engine.rotations.candidates import CropInfo, candidates
from backend.engine.rotations.current import NO_CURRENT_LIMITATION, current_sequence, drop_current, truncation_limitation, vs_current
from backend.engine.rotations.exclusions import SoilPh, current_issues, high_risk_motives, phase1
from backend.engine.rotations.ranking import CycleScores, StrategyScores, rank_strategies, score_strategy
from backend.engine.rotations.reasons import CURRENT, SUGGESTED, strategy_reasons
from backend.engine.rotations.rules import FilterRule, Motive
from backend.engine.rotations.soil_health import Criterion, HealthRule, SlopeInfo, SoilCarbon, SoilCrop
from backend.engine.soil_signal import ESTIMATE_LABEL
from backend.engine.suitability import Suitability
from common import signal_sources

# La frase del contrato (ejemplo de la respuesta): `soil_health` compara, no predice (decisión 4).
COMPARISON_LIMITATION = "Compara estrategias según reglas con fuente. No predice cuánto va a mejorar el suelo"
NO_RULES_LIMITATION = "Las reglas de rotación no están publicadas en esta versión del dataset: ninguna regla filtra ni califica"
NO_SLOPE_LIMITATION = "Sin la pendiente estimada del terreno: la erosión no se evaluó"
NO_SOIL_LIMITATION = "Sin el suelo estimado de la zona: no se revisó el pH ni el carbono orgánico"
# Hasta 10 sugeridas y 10 descartadas (decisión 15).
LIMIT = 10


def _name(crop: Mapping[str, Any]) -> str:
    """El nombre del cultivo en minúscula y sin la aclaración entre paréntesis de la ficha: «avena con vicia», no
    «avena con vicia (abono verde)», como se nombra en una lista («se compararon papa y avena con vicia»)."""
    return re.sub(r"\s*\([^)]*\)", "", str(crop.get("name_es") or crop.get("crop_id", ""))).strip().lower()


def _names(crop_ids: Sequence[str], crops: Mapping[str, Mapping[str, Any]]) -> str:
    """«papa y avena», «papa, avena y arveja»: los nombres del catálogo en minúscula."""
    names = [_name(crops.get(crop_id, {"crop_id": crop_id})) for crop_id in crop_ids]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


def crop_infos(crops: Mapping[str, Mapping[str, Any]]) -> dict[str, CropInfo]:
    """Lo que el filtro lee de cada ficha. El catálogo publicado no trae la fuente de cada valor, solo las de la ficha
    (`source_ids`): el rango de pH se cita con ellas (R8; specs/01-reglas.md, «la fuente va en `source_ids` del cultivo,
    no por valor»), y `ph_source_id` solo dice si la ficha cita alguna fuente (ver `_motive_sources`)."""
    result = {}
    for crop_id, crop in crops.items():
        sources = crop.get("source_ids") or []
        result[crop_id] = CropInfo(
            crop_id=crop_id,
            kind=crop["kind"],
            family=crop.get("family"),
            secondary_families=tuple(crop.get("secondary_families") or ()),
            name_es=crop.get("name_es"),
            article=crop.get("article"),
            tmean_min_c=crop.get("tmean_min_c"),
            tmean_opt_min_c=crop.get("tmean_opt_min_c"),
            tmean_opt_max_c=crop.get("tmean_opt_max_c"),
            tmean_max_c=crop.get("tmean_max_c"),
            ph_min=crop.get("ph_min"),
            ph_max=crop.get("ph_max"),
            ph_source_id=sources[0] if sources else None,
        )
    return result


def soil_crops(crops: Mapping[str, Mapping[str, Any]]) -> dict[str, SoilCrop]:
    return {
        crop_id: SoilCrop(
            crop_id=crop_id,
            kind=crop["kind"],
            family=crop.get("family"),
            secondary_families=tuple(crop.get("secondary_families") or ()),
            fixes_nitrogen=crop.get("fixes_nitrogen"),
        )
        for crop_id, crop in crops.items()
    }


def filter_rules(rules: Sequence[Mapping[str, Any]]) -> list[FilterRule]:
    return [
        FilterRule(r["rule_id"], r["condition_type"], r["params"] or {}, r["reason_template"], r["source_id"])
        for r in rules
        if r.get("kind") == "filter"
    ]


def health_rules(rules: Sequence[Mapping[str, Any]]) -> list[HealthRule]:
    return [
        HealthRule(
            r["rule_id"], r["criterion"], r["condition_type"], r["params"] or {}, r["levels"] or {}, r["reason_template"], r["source_id"]
        )
        for r in rules
        if r.get("kind") == "health"
    ]


@dataclass(frozen=True)
class ZoneGround:
    """El suelo y la pendiente de la consulta, ya leídos, con de dónde salen (`lot` o `municipality`)."""

    ph: SoilPh | None
    carbon: SoilCarbon | None
    slope: SlopeInfo | None
    soil_basis: str
    slope_basis: str
    # Si hay un suelo estimado (con o sin pH): para el rótulo de estimación (R10).
    has_soil: bool


def _soil_source(source_ids: Sequence[str]) -> str | None:
    """La fuente del suelo que se cita: SoilGrids si está entre las de la fila o de las celdas; si no, la primera."""
    if not source_ids:
        return None
    return "soilgrids" if "soilgrids" in source_ids else sorted(source_ids)[0]


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if number == number else None  # NaN no es un dato (R1)


def zone_ground(dataset: Dataset, query: WindowQuery) -> ZoneGround:
    """El suelo (pH y carbono) y la pendiente del lote dibujado o, sin dibujo, del municipio (HU-182, HU-184). Lo que
    falta queda nulo: nunca se sustituye el lote por el municipio en silencio (R1). Nada se guarda (R9)."""
    municipality, lot = query.municipality, query.lot
    drawn = lot is not None and lot.geometry is not None
    row = zone_soil(dataset, municipality, lot)
    ph = carbon = None
    if row is not None:
        source = _soil_source(row.get("source_ids") or [])
        p05, p95 = _finite(row.get("ph_p05")), _finite(row.get("ph_p95"))
        if source is not None and p05 is not None and p95 is not None:
            ph = SoilPh(p05, p95, source)
        if source is not None:
            carbon = SoilCarbon(_finite(row.get("soc_g_kg")), _finite(row.get("soc_p05")), _finite(row.get("soc_p95")), source)
    if lot is None:
        slope_pct, slope_basis = municipality.slope_pct, "municipality"
    else:
        terrain = zone_terrain(dataset, municipality, lot)
        slope_pct = None if terrain is None else terrain["slope_pct"]
        slope_basis = "lot" if drawn else "municipality"
    slope = None if slope_pct is None else SlopeInfo(_finite(slope_pct), NON_SOIL_SOURCE, slope_basis)
    return ZoneGround(ph, carbon, slope, "lot" if drawn else "municipality", slope_basis, row is not None)


def _temperature_sources(dataset: Dataset, query: WindowQuery) -> tuple[str, ...]:
    """Las fuentes de la temperatura de la zona con que se decide la aptitud: la temperatura de la región (la de las
    señales de clima en `sources.yaml`), el gradiente con que se corrige por altitud y, con un lote, NASADEM."""
    region_sources = signal_sources.get_signal_sources().for_region(dataset.region["id"])
    found = [region_sources["heat"].used] if "heat" in region_sources else []
    lapse = dataset.region.get("temperature_lapse_rate") or {}
    if lapse.get("source_id"):
        found.append(lapse["source_id"])
    if query.zone.basis == "lot":
        found.append(NON_SOIL_SOURCE)
    return tuple(found)


@dataclass(frozen=True)
class Evaluated:
    """Una estrategia ya calculada, antes de su `rank` y de su `vs_current`."""

    crop_ids: tuple[str, ...]
    scores: StrategyScores
    strategy: Strategy
    cycle_scores: tuple[CycleScores, ...]
    health: dict[str, Criterion]


def _health(health: Mapping[str, Criterion]) -> dict[str, HealthCriterion]:
    return {
        name: HealthCriterion(
            status=c.status, level=c.level, rule_ids=list(c.rule_ids), source_ids=list(c.source_ids), reasons=list(c.reasons)
        )
        for name, c in health.items()
    }


class RotationBuilder:
    """Una consulta de `/rotations`: el catálogo, las reglas y el suelo pasados una sola vez a los tipos del motor."""

    def __init__(
        self,
        dataset: Dataset,
        query: WindowQuery,
        cycles: StrategyCycles,
        priorities: Mapping[str, int],
    ) -> None:
        self.dataset = dataset
        self.query = query
        self.sc = cycles
        self.priorities = dict(priorities)
        self.crops = crop_infos(dataset.crops)
        self.soil_crops = soil_crops(dataset.crops)
        self.filters = filter_rules(dataset.rotation_rules)
        self.health_rules = health_rules(dataset.rotation_rules)
        self.ground = zone_ground(dataset, query)
        self.temperature_sources = _temperature_sources(dataset, query)

    # ------------------------------------------------------------ fuentes y motivos

    def explain(self, crop: CropInfo, result: Suitability) -> tuple[str, tuple[str, ...]]:
        """La misma frase de `/diagnostics` (`suitability.reasons`) y las fuentes de la ficha y de la temperatura."""
        ficha = self.dataset.crops[crop.crop_id]
        reason = suitability_result(ficha, result, self.query.zone, self.query.municipality).reasons[0]
        return reason, (*(ficha.get("source_ids") or ()), *self.temperature_sources)

    def _motive_sources(self, motive: Motive) -> list[str]:
        """Las fuentes de un motivo, sin repetir. En `soil_ph`, las de la ficha (el catálogo publicado no trae la fuente
        de cada valor) y la del suelo."""
        sources: Sequence[str] = motive.source_ids
        if motive.kind == "soil_ph" and motive.crop_id in self.dataset.crops and self.ground.ph is not None:
            sources = (*(self.dataset.crops[motive.crop_id].get("source_ids") or ()), self.ground.ph.source_id)
        return list(dict.fromkeys(sources))

    def issue(self, motive: Motive) -> Issue:
        return Issue(
            cycle=motive.cycle,
            kind=motive.kind,
            rule_id=motive.rule_id,
            signal=motive.signal,
            crop_id=motive.crop_id,
            reason=motive.reason,
            source_ids=self._motive_sources(motive),
        )

    def exclusion(self, crop_ids: Sequence[str], motive: Motive) -> Exclusion:
        return Exclusion(crop_ids=list(crop_ids), **self.issue(motive).model_dump())

    # ------------------------------------------------------------ estrategias

    def datable(self, crop_id: str) -> bool:
        """Si el ciclo de este cultivo se puede fechar: sus etapas o, en el descanso, sus días (R1)."""
        return self.sc.plan((crop_id,)) is not None

    def evaluate(self, sequence: Sequence[str], kind: str) -> Evaluated:
        """Los ciclos, la salud del suelo, los criterios y el total de una estrategia que se puede fechar."""
        planned = self.sc.plan(sequence)
        if planned is None:  # quien llama ya quitó las que no se pueden fechar
            raise ValueError(f"La estrategia {tuple(sequence)} no se puede fechar")
        g = self.ground
        health = self.sc.soil_health(planned, self.soil_crops, self.health_rules, g.carbon, g.slope)
        cycle_scores = self.sc.cycle_scores(planned)
        scores = score_strategy(tuple(sequence), cycle_scores, health, self.query.weights, self.priorities)
        limitations = list(scores.limitations)
        if self.query.lot is not None and self.query.lot.geometry is None and g.has_soil:
            limitations.append(LOT_SOIL_LIMITATION)
        strategy = Strategy(
            rank=None,
            kind=kind,
            crop_ids=list(sequence),
            total_score=scores.total_score,
            scores=Scores(**scores.scores),
            vs_current=None,
            cycles=self.sc.cycles(planned),
            soil_health=_health(health),
            issues=[],
            reasons=[],
            limitations=list(dict.fromkeys(limitations)),
        )
        return Evaluated(tuple(sequence), scores, strategy, cycle_scores, health)

    def reasons(self, item: Evaluated, vs: Mapping[str, int | None] | None, kind: str) -> list[str]:
        return list(strategy_reasons(item.scores, self.priorities, item.cycle_scores, item.health, self.query.weights, vs, kind=kind))

    def current_issues(self, sequence: Sequence[str]) -> list[Issue]:
        """Todos los motivos de la rotación actual, de las dos fases (`current_issues`): nunca se excluye (R3)."""
        first = phase1(
            sequence,
            self.sc.history.crop_ids,
            self.crops,
            self.filters,
            self.query.zone.tmean_annual_c,
            self.ground.ph,
            self.explain,
            history_basis=self.sc.history.basis,
        )
        risk = high_risk_motives(sequence, self.sc.diagnoser()(sequence))
        return [self.issue(m) for m in current_issues(first, risk)]


def build_rotations(
    dataset: Dataset,
    query: WindowQuery,
    sowing_date: date,
    previous_crop_ids: Sequence[str],
    current_crop_ids: Sequence[str] | None,
    n_cycles: int,
    priorities: Mapping[str, int],
    base_limitations: Sequence[str] = (),
) -> RotationResponse:
    """La respuesta de `/rotations` para una consulta ya validada por la ruta."""
    sc = StrategyCycles(query, sowing_date, previous_crop_ids, current_crop_ids)
    builder = RotationBuilder(dataset, query, sc, priorities)
    crops = dataset.crops
    limitations: list[str] = list(base_limitations)

    # Un cultivo que no se puede fechar (sin etapas o, el descanso, sin días) no se puede revisar: se quita y se dice (R1).
    undatable = sorted(crop_id for crop_id in builder.crops if not builder.datable(crop_id))
    usable = [info for crop_id, info in builder.crops.items() if crop_id not in undatable]
    if undatable:
        limitations.append(
            f"No se armaron estrategias con {_names(undatable, crops)}: falta la duración de su ficha (etapas o días de descanso)"
        )

    # La rotación actual con exactamente `cycles` cultivos (HU-223): con menos se repite, con más se toman los primeros.
    found = current_sequence(current_crop_ids, n_cycles)
    current = None if found is None else found.crop_ids
    truncated = truncation_limitation(current_crop_ids, n_cycles, {crop_id: _name(crop) for crop_id, crop in crops.items()})
    if truncated is not None:
        limitations.append(truncated)

    # Las candidatas, sin la igual a la actual, que no se repite (antes de cortar a 10).
    sequences = drop_current(candidates(usable, n_cycles), current)
    result = sc.filter(sequences, builder.crops, builder.filters, builder.ground.ph, builder.explain, LIMIT)
    limitations.extend(result.limitations)

    evaluated = {seq: builder.evaluate(seq, SUGGESTED) for seq in result.survivors}
    ranked = rank_strategies([item.scores for item in evaluated.values()], LIMIT)

    current_item = None
    current_strategy = None
    if current is None:
        limitations.append(NO_CURRENT_LIMITATION)
    elif any(crop_id in undatable for crop_id in current):
        limitations.append("No se pudo armar su rotación actual: a uno de sus cultivos le falta la duración en su ficha")
    else:
        current_item = builder.evaluate(current, CURRENT)
        current_strategy = current_item.strategy.model_copy(
            update={"issues": builder.current_issues(current), "reasons": builder.reasons(current_item, None, CURRENT)}
        )

    strategies = []
    for ranked_item in ranked:
        item = evaluated[ranked_item.crop_ids]
        vs = None
        if current_item is not None:
            vs = vs_current(item.scores.scores, item.scores.total_score, current_item.scores.scores, current_item.scores.total_score)
        strategies.append(
            item.strategy.model_copy(
                update={
                    "rank": ranked_item.rank,
                    "vs_current": None if vs is None else VsCurrent(**vs),
                    "reasons": builder.reasons(item, vs, SUGGESTED),
                }
            )
        )

    if not dataset.rotation_rules:
        limitations.append(NO_RULES_LIMITATION)
    if builder.ground.ph is None and builder.ground.carbon is None:
        limitations.append(NO_SOIL_LIMITATION)
    if builder.ground.slope is None:
        limitations.append(NO_SLOPE_LIMITATION)
    limitations.append(COMPARISON_LIMITATION)
    if builder.ground.has_soil:
        limitations.append(ESTIMATE_LABEL)

    summary = result.summary
    return RotationResponse(
        strategies=strategies,
        current_strategy=current_strategy,
        excluded=[builder.exclusion(e.crop_ids, e.motive) for e in summary.excluded],
        excluded_counts=summary.counts,
        weights=dict(priorities),
        soil_basis=builder.ground.soil_basis,
        slope_basis=builder.ground.slope_basis,
        limitations=list(dict.fromkeys(limitations)),
        versions={"dataset": dataset.version, "rules": rules_version(dataset.rules_version)},
    )
