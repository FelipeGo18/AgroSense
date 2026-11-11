"""Umbrales de las señales: lee y valida `thresholds.yaml` (HU-075; specs/02-contratos.md, «Configuración versionada»).

Si el archivo no cumple su forma, la API no arranca y dice por qué. El motor nunca abre este archivo: recibe los
umbrales ya leídos (R6). Una señal sin fuente para su curva (`curve: null`) es `insufficient_data` (R1, R8).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.config.weights import P0_SIGNALS

THRESHOLDS_FILE = Path(__file__).with_name("thresholds.yaml")
# Las señales cuya curva sale de la ficha del cultivo (`curve: crop`).
CROP_CURVES = frozenset({"heat", "soil"})
# El suelo nunca es crítico: es una estimación de un mapa de 250 m (R10).
NEVER_CRITICAL = frozenset({"soil"})
FROM_CROP = "crop"


class ThresholdsError(ValueError):
    """`thresholds.yaml` no sirve. El mensaje dice qué hay que corregir."""


@dataclass(frozen=True)
class SignalThreshold:
    variable: str
    unit: str
    # Los puntos [valor, calificación], `FROM_CROP` o `None` (sin fuente: `insufficient_data`).
    curve: tuple[tuple[float, float], ...] | str | None
    critical_below: float | None
    source_id: str | None
    note: str | None = None

    @property
    def available(self) -> bool:
        """Si la señal se puede calificar: sin curva con fuente, no (R1)."""
        return self.curve is not None


@dataclass(frozen=True)
class Thresholds:
    version: str
    favorable: float
    moderate: float
    levels_source_id: str | None
    signals: dict[str, SignalThreshold]

    def source_ids(self) -> set[str]:
        """Las fuentes que cita el archivo, para revisarlas contra `sources` (R8)."""
        cited = {self.levels_source_id} | {signal.source_id for signal in self.signals.values()}
        return {source for source in cited if source}


def _score(value: Any, where: str) -> float:
    # `bool` es un `int` en Python: «true» no es una calificación.
    if not isinstance(value, int | float) or isinstance(value, bool) or not 0 <= value <= 100:
        raise ThresholdsError(f"{where} debe ser un número de 0 a 100.")
    return float(value)


def _curve(signal: str, curve: Any, name: str) -> tuple[tuple[float, float], ...] | str | None:
    if curve is None:
        return None
    if curve == FROM_CROP:
        if signal not in CROP_CURVES:
            raise ThresholdsError(f"En {name}, `{signal}` no puede usar `curve: crop`: solo {', '.join(sorted(CROP_CURVES))}.")
        return FROM_CROP
    if signal in CROP_CURVES:
        raise ThresholdsError(f"En {name}, la curva de `{signal}` sale de la ficha del cultivo: debe ser `crop`.")
    if not isinstance(curve, list) or len(curve) < 2:
        raise ThresholdsError(f"En {name}, la curva de `{signal}` debe tener al menos dos puntos [valor, calificación].")
    points = []
    for point in curve:
        if not isinstance(point, list) or len(point) != 2:
            raise ThresholdsError(f"En {name}, cada punto de la curva de `{signal}` debe ser [valor, calificación].")
        value, score = point
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise ThresholdsError(f"En {name}, un valor de la curva de `{signal}` no es un número: {value!r}.")
        points.append((float(value), _score(score, f"La calificación de un punto de `{signal}` en {name}")))
    values = [value for value, _ in points]
    if any(later <= earlier for earlier, later in zip(values, values[1:], strict=False)):
        raise ThresholdsError(f"En {name}, los valores de la curva de `{signal}` deben ir en orden creciente y sin repetir.")
    return tuple(points)


def _signal(signal: str, entry: Any, name: str) -> SignalThreshold:
    if not isinstance(entry, dict):
        raise ThresholdsError(f"En {name}, `{signal}` debe tener `variable`, `unit`, `curve`, `critical_below` y `source_id`.")
    for field in ("variable", "unit"):
        if not isinstance(entry.get(field), str):
            raise ThresholdsError(f"En {name}, `{signal}` debe tener `{field}` como texto.")
    if not entry["variable"].strip():
        raise ThresholdsError(f"En {name}, `{signal}` debe decir qué `variable` califica.")
    curve = _curve(signal, entry.get("curve"), name)
    critical = entry.get("critical_below")
    source = entry.get("source_id")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise ThresholdsError(f"En {name}, el `source_id` de `{signal}` debe ser texto o nulo.")
    if curve is None:
        # Sin fuente no hay curva ni umbral crítico: nada se inventa (R1, R8).
        if critical is not None or source is not None:
            raise ThresholdsError(f"En {name}, `{signal}` no tiene curva: su `critical_below` y su `source_id` deben ser nulos.")
        return SignalThreshold(entry["variable"], entry["unit"], None, None, None, entry.get("note"))
    if not source:
        raise ThresholdsError(f"En {name}, la curva de `{signal}` no cita su fuente (`source_id`, R8).")
    if signal in NEVER_CRITICAL:
        if critical is not None:
            raise ThresholdsError(f"En {name}, `{signal}` nunca es crítica (R10): su `critical_below` debe ser nulo.")
    elif critical is None:
        raise ThresholdsError(f"En {name}, `{signal}` tiene curva y le falta `critical_below`.")
    else:
        critical = _score(critical, f"El `critical_below` de `{signal}` en {name}")
    return SignalThreshold(entry["variable"], entry["unit"], curve, critical, source.strip(), entry.get("note"))


def load_thresholds(path: Path = THRESHOLDS_FILE) -> Thresholds:
    """Lee el archivo y comprueba su forma: versión, cortes de nivel y una entrada por cada señal del P0."""
    name = path.name
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ThresholdsError(f"No existe {name}: sin él no se puede calificar ninguna señal.") from error
    except yaml.YAMLError as error:
        raise ThresholdsError(f"{name} no es YAML válido: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("levels"), dict) or not isinstance(data.get("signals"), dict):
        raise ThresholdsError(f"{name} debe tener `version`, `levels` y `signals`.")
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ThresholdsError(f'{name} debe tener `version` como texto (por ejemplo "1.0.0").')

    levels = data["levels"]
    favorable = _score(levels.get("favorable"), f"`levels.favorable` en {name}")
    moderate = _score(levels.get("moderate"), f"`levels.moderate` en {name}")
    if not 0 < moderate < favorable:
        raise ThresholdsError(f"En {name}, `levels.moderate` debe ser mayor que 0 y menor que `levels.favorable`.")

    entries = data["signals"]
    missing = [signal for signal in P0_SIGNALS if signal not in entries]
    if missing:
        raise ThresholdsError(f"A {name} le faltan las señales: {', '.join(missing)}.")
    unknown = sorted(set(entries) - set(P0_SIGNALS))
    if unknown:
        raise ThresholdsError(f"{name} tiene señales que no son del P0: {', '.join(unknown)}.")
    signals = {signal: _signal(signal, entries[signal], name) for signal in P0_SIGNALS}
    return Thresholds(
        version=version.strip(),
        favorable=favorable,
        moderate=moderate,
        levels_source_id=levels.get("source_id"),
        signals=signals,
    )


@lru_cache
def get_thresholds() -> Thresholds:
    return load_thresholds()
