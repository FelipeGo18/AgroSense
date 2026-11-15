"""Los datos de la señal de oferta (HU-072, decisión 17): el semestre de EVA en que cae la siembra, leído del dataset
publicado (`supply_semester`). Son lecturas sin errores HTTP, sin base de datos y sin guardar nada (R9). El motor recibe
el semestre ya armado (`backend.engine.supply_signal`, R6).

La fuente es la que `sources.yaml` dice para `supply` en la región (en la piloto, EVA): sin dato de esa fuente, la señal
es `insufficient_data` y ninguna otra la reemplaza (R1).
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from typing import Any

import polars as pl

from backend.dataset import Dataset
from backend.engine.supply_signal import SupplySemester, SupplySignalResult, supply_signal
from common.signal_sources import get_signal_sources

# Los años anteriores con que HU-032 calcula `planted_change_pct` (el mismo semestre de los tres años anteriores).
BASELINE_YEARS = 3


@dataclass(frozen=True)
class SupplySource:
    """Una entrada de `signals.supply.sources`, con los nombres de campo de `SourceValue` del contrato: el área de EVA
    que respalda la señal, para que la web cite la fuente (R8; revisión del PR #174). Una sola hoy; las demás fuentes de
    la oferta llegan con HU-200 (P1)."""

    source_id: str
    indicator: str
    value: float | None
    unit: str
    period: str | None
    preliminary: bool | None
    used: bool


@dataclass(frozen=True)
class SupplySignal(SupplySignalResult):
    """La señal `supply` del motor con su fuente para contrastar (`ContrastedSignal`). El motor no la conoce: es un
    campo de la API, como en el agua."""

    sources: tuple[SupplySource, ...] = ()


def semester_of(day: date) -> str:
    """El semestre de EVA en que cae una fecha: A de enero a junio y B de julio a diciembre (decisión 11)."""
    return "A" if day.month <= 6 else "B"


def supply_semester(dataset: Dataset, municipality_id: str, crop_id: str, sowing: date, source_id: str) -> SupplySemester | None:
    """La fila de `supply_semester` del semestre en que cae la siembra, del último año con dato de ese semestre, de la
    fuente `source_id`. Sin tabla, sin fila o sin área sembrada: None (R1)."""
    table = dataset.supply_semester
    if table is None:
        return None
    semester = semester_of(sowing)
    rows = table.filter(
        (pl.col("municipality_id") == municipality_id)
        & (pl.col("crop_id") == crop_id)
        & (pl.col("semester") == semester)
        & (pl.col("source_id") == source_id)
        & pl.col("planted_ha").is_not_null()
    )
    if rows.is_empty():
        return None
    by_year = {row["year"]: row for row in rows.iter_rows(named=True)}
    year = max(by_year)
    row = by_year[year]
    previous = by_year.get(year - 1)
    baseline = sum(1 for y in range(year - BASELINE_YEARS, year) if y in by_year)
    return SupplySemester(
        year=year,
        semester=semester,
        preliminary=bool(row["preliminary"]),
        planted_ha=float(row["planted_ha"]),
        planted_change_pct=row["planted_change_pct"],
        same_as_previous=None if previous is None else previous["planted_ha"] == row["planted_ha"],
        complete_baseline=baseline == BASELINE_YEARS,
    )


def supply_in(dataset: Dataset, municipality_id: str, crop_id: str, crop: Mapping[str, Any], sowing: date | None) -> SupplySignalResult:
    """La señal `supply` de una ventana que se siembra en `sowing` (None sin ventana: sin fecha no hay semestre), con la
    fuente de `sources.yaml` para la región. La usan `/diagnostics`, los ciclos de `/rotations` y `/changes`, para que
    digan lo mismo."""
    # Sin tabla o sin fecha no hay qué leer, y no se pide la fuente: como el agua, solo se busca cuando hay datos.
    semester, source_id = None, None
    if sowing is not None and dataset.supply_semester is not None:
        source_id = get_signal_sources().for_region(dataset.region["id"])["supply"].used
        semester = supply_semester(dataset, municipality_id, crop_id, sowing, source_id)
    result = supply_signal(semester, str(crop.get("name_es") or crop_id).lower())
    if semester is None or source_id is None:
        return result
    source = SupplySource(
        source_id=source_id,
        indicator="planted_ha",
        value=semester.planted_ha,
        unit="ha",
        period=f"{semester.year} {semester.semester}",
        preliminary=semester.preliminary,
        used=True,
    )
    return SupplySignal(*(getattr(result, field.name) for field in fields(result)), sources=(source,))
