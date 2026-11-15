"""Parámetros versionados de HU-217/218: lectura fuera del motor (R6)."""

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path

import yaml

from common.region import REGION_FILE


@dataclass(frozen=True)
class ChangeParameters:
    min_year_share: float
    dry_quantile: float


def load_change_parameters(path: Path = REGION_FILE) -> ChangeParameters:
    """Los cortes de HU-216/HU-143; sin ellos no se inventan valores por defecto."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        share, quantile = data["change_periods"]["min_year_share"], data["climate_normal"]["dry_quantile"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in (share, quantile)):
            raise ValueError("Los cortes deben ser números finitos")
        if not 0 < share <= 1 or not 0 <= quantile <= 1:
            raise ValueError("Los cortes están fuera de rango")
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"Configuración de comparación histórica inválida en {path.name}") from error
    return ChangeParameters(float(share), float(quantile))


@lru_cache
def get_change_parameters() -> ChangeParameters:
    return load_change_parameters()
