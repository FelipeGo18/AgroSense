"""Fases 1 y 2 de HU-081 (R3; specs/01-reglas.md, «Aptitud del cultivo en la zona» y «Estrategias de rotación», pasos
2 a 4). La fase 1 junta los motivos que no necesitan fechas: `rule`, `not_suitable` y `soil_ph`. La fase 2 suma
`high_risk` con los diagnósticos de ciclo, y el resumen arma `excluded` y los conteos. Un dato que falta nunca
excluye: da una limitación (R1). Cada motivo lleva sus fuentes (R8).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from backend.engine.rotations.candidates import FALLOW, CropInfo
from backend.engine.rotations.rules import FilterRule, Motive, rule_motives
from backend.engine.signal_score import CLIMATE_CRITICAL_SIGNALS, SignalScore, is_grave
from backend.engine.suitability import INSUFFICIENT_DATA, NOT_SUITABLE, Suitability, suitability
from common.signals import P0_SIGNALS

# Lo arma la API para que la razón y las fuentes sean las de `/diagnostics`; el motor no arma ese texto.
SuitabilityExplainer = Callable[[CropInfo, Suitability], tuple[str, tuple[str, ...]]]

_KIND_ORDER = {"rule": 0, "not_suitable": 1, "soil_ph": 2, "high_risk": 3}
# Las señales de riesgo grave de clima, en el orden del contrato (`P0_SIGNALS`): una sola definición (R2, R4).
CLIMATE_SIGNALS = tuple(s for s in P0_SIGNALS if s in CLIMATE_CRITICAL_SIGNALS)


@dataclass(frozen=True)
class SoilPh:
    """Intervalo estimado del pH del suelo de la zona o del lote (p05 a p95) y la fuente que lo da (R10)."""

    p05: float
    p95: float
    source_id: str


@dataclass(frozen=True)
class Phase1Result:
    motives: tuple[Motive, ...]
    limitations: tuple[str, ...]


def _first_cycles(sequence: Sequence[str], crops: Mapping[str, CropInfo]) -> list[tuple[int, str, CropInfo]]:
    """(ciclo, crop_id, ficha) de cada cultivo en su primer ciclo; sin descansos ni cultivos fuera del catálogo."""
    seen: dict[str, tuple[int, str, CropInfo]] = {}
    for i, crop_id in enumerate(sequence, start=1):
        crop = crops.get(crop_id)
        if crop is not None and crop.kind != FALLOW:
            seen.setdefault(crop_id, (i, crop_id, crop))
    return list(seen.values())


def _name(crop: CropInfo) -> str:
    return crop.name_es.lower() if crop.name_es else crop.crop_id


def suitability_motives(
    sequence: Sequence[str],
    crops: Mapping[str, CropInfo],
    tmean_annual_c: float | None,
    explain: SuitabilityExplainer,
) -> tuple[list[Motive], list[str]]:
    """Un motivo `not_suitable` por cultivo, en su primer ciclo, si su temperatura media anual queda fuera del rango
    absoluto de la ficha (decide `suitability`). `insufficient_data` no excluye: una limitación por cultivo (R1).
    El descanso no se evalúa."""
    motives: list[Motive] = []
    limitations: list[str] = []
    for cycle, crop_id, crop in _first_cycles(sequence, crops):
        result = suitability(crop.tmean_min_c, crop.tmean_opt_min_c, crop.tmean_opt_max_c, crop.tmean_max_c, tmean_annual_c)
        if result.level == NOT_SUITABLE:
            reason, source_ids = explain(crop, result)
            motives.append(Motive("not_suitable", cycle, reason, tuple(source_ids), crop_id=crop_id))
        elif result.level == INSUFFICIENT_DATA:
            limitations.append(
                f"No se pudo comprobar si {_name(crop)} se da en la zona: falta la temperatura media anual o un límite de su ficha"
            )
    return motives, limitations


def _ph(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def ph_motives(
    sequence: Sequence[str],
    crops: Mapping[str, CropInfo],
    soil: SoilPh | None,
) -> tuple[list[Motive], list[str]]:
    """Un motivo `soil_ph` por cultivo, en su primer ciclo, si el pH que tolera queda fuera de todo el intervalo
    estimado del suelo (`ph_max < p05` o `ph_min > p95`; tocar un borde no excluye). Sin suelo o sin el rango de la
    ficha con fuente, no excluye: una limitación por cultivo (R1, R8). El descanso no se revisa."""
    motives: list[Motive] = []
    limitations: list[str] = []
    for cycle, crop_id, crop in _first_cycles(sequence, crops):
        if soil is None or crop.ph_min is None or crop.ph_max is None or not crop.ph_source_id:
            limitations.append(f"No se pudo comprobar el pH del suelo para {_name(crop)}: falta el pH del suelo o su rango en la ficha")
        elif crop.ph_max < soil.p05 or crop.ph_min > soil.p95:
            who = f"{crop.article} {_name(crop)}" if crop.article else _name(crop)
            reason = (
                f"El pH del suelo de la zona ({_ph(soil.p05)} a {_ph(soil.p95)}) queda fuera del que tolera "
                f"{who} ({_ph(crop.ph_min)} a {_ph(crop.ph_max)})"
            )
            motives.append(Motive("soil_ph", cycle, reason, (crop.ph_source_id, soil.source_id), crop_id=crop_id))
    return motives, limitations


def phase1(
    sequence: Sequence[str],
    previous_crop_ids: Sequence[str],
    crops: Mapping[str, CropInfo],
    rules: Sequence[FilterRule],
    tmean_annual_c: float | None,
    soil: SoilPh | None,
    explain: SuitabilityExplainer,
) -> Phase1Result:
    """Une los motivos de la fase 1, ordenados por `kind` (`rule`, `not_suitable`, `soil_ph`), luego por ciclo y luego
    por `rule_id` o `crop_id` (R4): así el primero es el que muestra `excluded` (contrato, «Varios motivos», aprobado por
    Felipe el 14 de noviembre de 2026). Las limitaciones van sin repetir, por primera aparición: aptitud y luego pH."""
    suit, suit_lim = suitability_motives(sequence, crops, tmean_annual_c, explain)
    ph, ph_lim = ph_motives(sequence, crops, soil)
    motives = [*rule_motives(sequence, previous_crop_ids, crops, rules), *suit, *ph]
    motives.sort(key=lambda m: (_KIND_ORDER[m.kind], m.cycle, m.rule_id or "", m.crop_id or ""))
    return Phase1Result(tuple(motives), tuple(dict.fromkeys([*suit_lim, *ph_lim])))


@dataclass(frozen=True)
class SignalReason:
    """Calificación de una señal de un ciclo con la razón y las fuentes que el diagnóstico ya armó (R5, R8)."""

    score: SignalScore
    reason: str
    source_ids: tuple[str, ...]


CycleDiagnosis = Mapping[str, SignalReason]


def high_risk_motives(sequence: Sequence[str | None], diagnoses: Sequence[CycleDiagnosis | None]) -> list[Motive]:
    """Fase 2: un motivo `high_risk` por cada señal de clima `unfavorable` y crítica de un ciclo, sin mirar los pesos:
    un riesgo grave no lo compensa nada (R2). El descanso (`None`) no se revisa; `supply`, `market` y `soil` nunca
    excluyen. Orden: por ciclo y, dentro del ciclo, el de `CLIMATE_SIGNALS` (R4). Un diagnóstico por ciclo: si las
    longitudes no coinciden, falla (un ciclo sin revisar podría esconder un riesgo grave)."""
    motives: list[Motive] = []
    for cycle, (crop_id, diagnosis) in enumerate(zip(sequence, diagnoses, strict=True), start=1):
        for name in CLIMATE_SIGNALS if diagnosis is not None else ():
            found = diagnosis.get(name)
            if found is not None and is_grave(found.score):
                motives.append(Motive("high_risk", cycle, found.reason, tuple(found.source_ids), signal=name, crop_id=crop_id))
    return motives


def _signal_rank(signal: str | None) -> int:
    """Lugar de la señal en `P0_SIGNALS`; -1 sin señal; las que no son del P0, después de todas (R4)."""
    if signal is None:
        return -1
    return P0_SIGNALS.index(signal) if signal in P0_SIGNALS else len(P0_SIGNALS)


def _tail_key(m: Motive) -> tuple[str, int, str]:
    return (m.rule_id or "", _signal_rank(m.signal), m.crop_id or "")


def _kind_key(m: Motive) -> tuple:
    """Llave completa de `excluded`: `kind`, ciclo y desempate (R4)."""
    return (_KIND_ORDER[m.kind], m.cycle, *_tail_key(m))


def _cycle_key(m: Motive) -> tuple:
    """Llave completa de `issues`: el ciclo primero, luego `kind` y el mismo desempate (R4)."""
    return (m.cycle, _KIND_ORDER[m.kind], *_tail_key(m))


@dataclass(frozen=True)
class Excluded:
    """Una estrategia descartada con su primer motivo y cuántos motivos tuvo en total."""

    crop_ids: tuple[str, ...]
    motive: Motive
    motive_count: int


@dataclass(frozen=True)
class ExclusionSummary:
    excluded: tuple[Excluded, ...]
    counts: dict[str, int]


def summarize_exclusions(strategies: Sequence[tuple[Sequence[str], Sequence[Motive]]], limit: int = 10) -> ExclusionSummary:
    """Arma `excluded` y `counts`. Cada descartada cuenta una vez, por su primer motivo en el orden `rule`,
    `not_suitable`, `soil_ph`, `high_risk`; con el mismo `kind` gana el de menor ciclo y, si sigue el empate,
    `rule_id`, la señal en el orden de `P0_SIGNALS` y `crop_id` (S2, R4). `counts` trae siempre las cuatro llaves.
    `excluded` va por `motive_count` y luego por `crop_ids` (R4), cortado en `limit`. Una estrategia sin motivos no
    está descartada: es un error de quien llama y lanza `ValueError`."""
    counts = dict.fromkeys(_KIND_ORDER, 0)
    rows: list[Excluded] = []
    for crop_ids, motives in strategies:
        if not motives:
            raise ValueError(f"La estrategia {tuple(crop_ids)} no tiene motivos: solo se resumen las descartadas")
        first = min(motives, key=_kind_key)
        counts[first.kind] += 1
        rows.append(Excluded(tuple(crop_ids), first, len(motives)))
    rows.sort(key=lambda e: (e.motive_count, e.crop_ids))
    return ExclusionSummary(tuple(rows[:limit]), counts)


def current_issues(result: Phase1Result, high_risk: Sequence[Motive]) -> tuple[Motive, ...]:
    """`issues` de la estrategia actual: todos los motivos de las dos fases, sin quitar repetidos (S3), por ciclo, luego
    por `kind` y luego por `rule_id`, la señal en el orden de `P0_SIGNALS` y `crop_id` (S1, R4). Nunca se excluye en silencio."""
    both = [*result.motives, *high_risk]
    both.sort(key=_cycle_key)
    return tuple(both)


# Lo arma la API: un diagnóstico por ciclo (None en el descanso); el motor no lo calcula (R6).
Diagnoser = Callable[[Sequence[str]], Sequence[CycleDiagnosis | None]]


@dataclass(frozen=True)
class FilterResult:
    survivors: tuple[tuple[str, ...], ...]
    limitations: tuple[str, ...]
    summary: ExclusionSummary


def filter_strategies(
    candidates: Sequence[Sequence[str]],
    previous_crop_ids: Sequence[str],
    crops: Mapping[str, CropInfo],
    rules: Sequence[FilterRule],
    tmean_annual_c: float | None,
    soil: SoilPh | None,
    explain: SuitabilityExplainer,
    diagnose: Diagnoser,
    limit: int = 10,
) -> FilterResult:
    """Orquesta las fases (R3): la fase 1 corre sobre cada candidata y `diagnose` solo se pide a las que no tienen
    motivos; a esas se les revisa `high_risk_motives`. Una descartada cuenta por los motivos de la fase en que quedó
    fuera. Devuelve las que sobreviven en el orden recibido, las limitaciones sin repetir (por primera aparición) y
    el resumen de `excluded` (R4)."""
    survivors: list[tuple[str, ...]] = []
    dropped: list[tuple[Sequence[str], Sequence[Motive]]] = []
    limitations: list[str] = []
    for sequence in candidates:
        first = phase1(sequence, previous_crop_ids, crops, rules, tmean_annual_c, soil, explain)
        limitations.extend(first.limitations)
        if first.motives:
            dropped.append((sequence, first.motives))
            continue
        risk = high_risk_motives(sequence, diagnose(sequence))
        if risk:
            dropped.append((sequence, risk))
        else:
            survivors.append(tuple(sequence))
    return FilterResult(tuple(survivors), tuple(dict.fromkeys(limitations)), summarize_exclusions(dropped, limit))
