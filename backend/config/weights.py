"""Pesos por defecto de las señales: lee y valida `weights.yaml` (HU-075, HU-198).

Si falta una señal del P0 o un peso está fuera de rango, la API no arranca y dice por qué. El motor nunca abre este
archivo: recibe los pesos ya leídos (R6).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

WEIGHTS_FILE = Path(__file__).with_name("weights.yaml")
# Las seis señales del P0, en el orden en que se muestran.
P0_SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
MAX_WEIGHT = 5


class WeightsError(ValueError):
    """`weights.yaml` no sirve. El mensaje dice qué hay que corregir."""


@dataclass(frozen=True)
class DefaultWeights:
    version: str
    status: str
    weights: dict[str, int]
    reasons: dict[str, str]


def load_weights(path: Path = WEIGHTS_FILE) -> DefaultWeights:
    """Lee el archivo y comprueba que cada señal del P0 tenga un peso entero de 1 a 5 con su porqué."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise WeightsError(f"No existe {path.name}: sin él no hay criterio de AgroSense.") from error
    except yaml.YAMLError as error:
        raise WeightsError(f"{path.name} no es YAML válido: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("weights"), dict):
        raise WeightsError(f"{path.name} debe tener `version` y `weights`.")
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise WeightsError(f'{path.name} debe tener `version` como texto (por ejemplo "1.0.0").')

    entries = data["weights"]
    missing = [signal for signal in P0_SIGNALS if signal not in entries]
    if missing:
        raise WeightsError(f"A {path.name} le falta el peso de: {', '.join(missing)}.")
    unknown = sorted(set(entries) - set(P0_SIGNALS))
    if unknown:
        raise WeightsError(f"{path.name} tiene señales que no son del P0: {', '.join(unknown)}.")

    weights: dict[str, int] = {}
    reasons: dict[str, str] = {}
    for signal in P0_SIGNALS:
        entry = entries[signal]
        weight = entry.get("weight") if isinstance(entry, dict) else None
        # `bool` es un `int` en Python: «true» no es un peso.
        if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= MAX_WEIGHT:
            raise WeightsError(
                f"El peso de `{signal}` en {path.name} debe ser un entero de 1 a {MAX_WEIGHT}: ningún peso por defecto es 0, "
                "porque el criterio de AgroSense mira las seis señales."
            )
        why = entry.get("why")
        if not isinstance(why, str) or not why.strip():
            raise WeightsError(f"El peso de `{signal}` en {path.name} no dice su porqué (`why`).")
        weights[signal] = weight
        reasons[signal] = why.strip()
    return DefaultWeights(version=version.strip(), status=str(data.get("status", "approved")), weights=weights, reasons=reasons)


@lru_cache
def get_default_weights() -> DefaultWeights:
    return load_weights()
