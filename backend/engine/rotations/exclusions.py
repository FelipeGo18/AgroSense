"""Fase 1 de HU-081: motivos de exclusión que no necesitan fechas (R3; specs/01-reglas.md, «Aptitud del cultivo en la
zona» y «Estrategias de rotación», pasos 2 a 4). Junta los motivos `rule`, `not_suitable` y `soil_ph`. Un dato que falta
nunca excluye: da una limitación (R1). Cada motivo lleva sus fuentes (R8).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from backend.engine.rotations.candidates import FALLOW, CropInfo
from backend.engine.rotations.rules import FilterRule, Motive, rule_motives
from backend.engine.suitability import INSUFFICIENT_DATA, NOT_SUITABLE, Suitability, suitability

# Lo arma la API para que la razón y las fuentes sean las de `/diagnostics`; el motor no arma ese texto.
SuitabilityExplainer = Callable[[CropInfo, Suitability], tuple[str, tuple[str, ...]]]

_KIND_ORDER = {"rule": 0, "not_suitable": 1, "soil_ph": 2}


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
