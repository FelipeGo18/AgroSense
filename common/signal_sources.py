"""Qué fuente calcula cada señal en cada región: lee y valida `catalog/sources.yaml` (HU-122; decisión 11).

Está en `common/` porque lo usan los dos: el pipeline lo revisa contra las fuentes que publica antes de escribir nada, y
la API lo lee al arrancar para pasárselo al motor ya leído (R6). Ninguno importa al otro.

- `check_shape`: la forma del archivo (versión, regiones, las seis señales del P0 y `planned`).
- `check_sources`: cada `source_id` está en `sources` o en `planned` (R8); una fuente de `planned` que ya se publica
  también es un error, para que no se quede en la lista por olvido.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SIGNAL_SOURCES_FILE = Path(__file__).resolve().parent.parent / "catalog" / "sources.yaml"
P0_SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
# Lo que dice `water`: de dónde sale la lluvia, la ET0 y la humedad del suelo que se muestra para contrastar.
WATER_SINGLE = ("rain", "et0")
WATER_LISTS = ("rain_contrast", "soil_moisture_contrast")


class SignalSourcesError(ValueError):
    """`catalog/sources.yaml` no sirve. El mensaje dice qué hay que corregir."""


@dataclass(frozen=True)
class SignalSource:
    """La fuente que calcula una señal (`used`) y las de contraste. En `water`, `used` es la de la lluvia."""

    used: str
    contrast: tuple[str, ...] = ()
    # Solo `water`: la ET0 y la humedad del suelo para contrastar.
    et0: str | None = None
    soil_moisture_contrast: tuple[str, ...] = ()
    # El aviso fijo que lleva la señal, si lo hay: `rain_caveat` en `water` y `frost_caveat` en `frost`.
    caveat: str | None = None

    def source_ids(self) -> set[str]:
        ids = {self.used, *self.contrast, *self.soil_moisture_contrast}
        return ids | ({self.et0} if self.et0 else set())


@dataclass(frozen=True)
class SignalSources:
    version: str
    regions: dict[str, dict[str, SignalSource]]
    planned: dict[str, str] = field(default_factory=dict)

    def for_region(self, region_id: str) -> dict[str, SignalSource]:
        if region_id not in self.regions:
            raise SignalSourcesError(f"catalog/sources.yaml no tiene la región «{region_id}».")
        return self.regions[region_id]

    def source_ids(self) -> set[str]:
        return {source for region in self.regions.values() for signal in region.values() for source in signal.source_ids()}

    def is_planned(self, source_id: str) -> bool:
        return source_id in self.planned


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SignalSourcesError(f"{where} debe ser un `source_id` (texto).")
    return value.strip()


def _texts(value: Any, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise SignalSourcesError(f"{where} debe ser una lista de `source_id`.")
    return tuple(_text(item, where) for item in value)


def _signal(region: str, signal: str, entry: Any) -> SignalSource:
    where = f"`{region}.{signal}` en catalog/sources.yaml"
    if not isinstance(entry, dict):
        raise SignalSourcesError(f"{where} debe decir qué fuente la calcula.")
    if signal == "water":
        missing = [key for key in WATER_SINGLE if key not in entry]
        if missing:
            raise SignalSourcesError(f"{where} debe decir de dónde salen {' y '.join(missing)}.")
        caveat = entry.get("rain_caveat")
        if caveat is not None and (not isinstance(caveat, str) or not caveat.strip()):
            raise SignalSourcesError(f"`rain_caveat` de {where} debe ser un texto.")
        return SignalSource(
            used=_text(entry["rain"], f"`rain` de {where}"),
            contrast=_texts(entry.get("rain_contrast"), f"`rain_contrast` de {where}"),
            et0=_text(entry["et0"], f"`et0` de {where}"),
            soil_moisture_contrast=_texts(entry.get("soil_moisture_contrast"), f"`soil_moisture_contrast` de {where}"),
            caveat=" ".join(caveat.split()) if caveat else None,
        )
    if "used" not in entry:
        raise SignalSourcesError(f"{where} debe tener `used`: la fuente que la calcula.")
    # Solo `frost`: el aviso que va con la señal de heladas, si lo hay (aprobado por Felipe el 13 de noviembre de 2026).
    caveat = entry.get("frost_caveat") if signal == "frost" else None
    if caveat is not None and (not isinstance(caveat, str) or not caveat.strip()):
        raise SignalSourcesError(f"`frost_caveat` de {where} debe ser un texto.")
    return SignalSource(
        used=_text(entry["used"], f"`used` de {where}"),
        contrast=_texts(entry.get("contrast"), f"`contrast` de {where}"),
        caveat=" ".join(caveat.split()) if caveat else None,
    )


def check_shape(data: Any) -> SignalSources:
    """Comprueba la forma del archivo ya leído y lo devuelve como `SignalSources`."""
    if not isinstance(data, dict) or not isinstance(data.get("regions"), dict) or not data["regions"]:
        raise SignalSourcesError("catalog/sources.yaml debe tener `version` y al menos una región en `regions`.")
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SignalSourcesError('catalog/sources.yaml debe tener `version` como texto (por ejemplo "1.0.0").')
    regions = {}
    for region, signals in data["regions"].items():
        if not isinstance(signals, dict):
            raise SignalSourcesError(f"La región «{region}» de catalog/sources.yaml debe tener sus señales.")
        missing = [signal for signal in P0_SIGNALS if signal not in signals]
        if missing:
            raise SignalSourcesError(f"A la región «{region}» de catalog/sources.yaml le faltan las señales: {', '.join(missing)}.")
        unknown = sorted(set(signals) - set(P0_SIGNALS))
        if unknown:
            raise SignalSourcesError(f"La región «{region}» de catalog/sources.yaml tiene señales que no son del P0: {', '.join(unknown)}.")
        regions[region] = {signal: _signal(region, signal, signals[signal]) for signal in P0_SIGNALS}
    planned = data.get("planned") or {}
    if not isinstance(planned, dict) or not all(isinstance(hu, str) and hu.startswith("HU-") for hu in planned.values()):
        raise SignalSourcesError("`planned` de catalog/sources.yaml debe ser `source_id: HU-xxx`, la HU que trae la fuente.")
    return SignalSources(version=version.strip(), regions=regions, planned=dict(planned))


def check_sources(config: SignalSources, region_id: str, published: set[str], adapters: set[str]) -> list[str]:
    """R8 para la región que se publica. Falla si una fuente que se nombra no está en `sources`, ni tiene adaptador, ni
    está en `planned` (un error de escritura), o si una fuente de `planned` ya se publica.

    Devuelve las que tienen adaptador pero no se publicaron esta vez (por ejemplo, falta su caché): no es un error,
    porque sin ellas la señal es `insufficient_data` (R1), pero quien llama lo dice en el log.
    """
    named = {source for signal in config.for_region(region_id).values() for source in signal.source_ids()}
    unknown = sorted(source for source in named if source not in published | adapters and not config.is_planned(source))
    if unknown:
        raise SignalSourcesError(
            f"catalog/sources.yaml nombra fuentes que no están en `sources` ni en `planned`: {', '.join(unknown)} (R8)."
        )
    stale = sorted(source for source in config.planned if source in published | adapters)
    if stale:
        raise SignalSourcesError(f"Estas fuentes ya tienen adaptador y siguen en `planned` de catalog/sources.yaml: {', '.join(stale)}.")
    return sorted(source for source in named if source in adapters and source not in published)


def load_signal_sources(path: Path = SIGNAL_SOURCES_FILE) -> SignalSources:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SignalSourcesError(f"No existe {path.name}: sin él no se sabe qué fuente calcula cada señal.") from error
    except yaml.YAMLError as error:
        raise SignalSourcesError(f"{path.name} no es YAML válido: {error}") from error
    return check_shape(data)


@lru_cache
def get_signal_sources() -> SignalSources:
    return load_signal_sources()
