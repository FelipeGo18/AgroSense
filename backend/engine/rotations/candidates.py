"""Candidatas de una estrategia de rotación (HU-081, paso 0; specs/01-reglas.md, «Estrategias de rotación»).

Todas las secuencias de `cycles` ciclos con los cultivos del catálogo, sin el mismo `crop_id` en dos ciclos seguidos
y sin dos descansos seguidos (decisión 15). Salen en orden alfabético por `crop_id`, ciclo por ciclo, sin depender
del orden de la entrada (R4).
"""

from dataclasses import dataclass
from itertools import product

FALLOW = "fallow"


@dataclass(frozen=True)
class CropInfo:
    """Lo que el motor necesita de la ficha de un cultivo para armar y filtrar estrategias: `kind` es 'crop',
    'cover' o 'fallow'; `family` es nula si la ficha no la trae (R1); `secondary_families` solo la usa
    `family_return_min_cycles`."""

    crop_id: str
    kind: str
    family: str | None
    secondary_families: tuple[str, ...] = ()
    # Aptitud y pH (HU-081, fase 1): de la ficha; nulos si la ficha no los trae con fuente (R1, R8).
    name_es: str | None = None
    article: str | None = None
    tmean_min_c: float | None = None
    tmean_opt_min_c: float | None = None
    tmean_opt_max_c: float | None = None
    tmean_max_c: float | None = None
    ph_min: float | None = None
    ph_max: float | None = None
    ph_source_id: str | None = None


def candidates(crops: list[CropInfo], cycles: int) -> list[tuple[str, ...]]:
    """Secuencias de `crop_id` de longitud `cycles` (2 o 3), en orden alfabético ciclo por ciclo.

    Un par seguido no puede repetir el `crop_id` ni ser dos `kind == "fallow"`. Con `cycles` fuera de 2–3 lanza
    `ValueError`."""
    if cycles not in (2, 3):
        raise ValueError(f"cycles debe ser 2 o 3, no {cycles}")
    kinds = {c.crop_id: c.kind for c in crops}
    ids = sorted(kinds)

    def allowed(a: str, b: str) -> bool:
        return a != b and not (kinds[a] == FALLOW and kinds[b] == FALLOW)

    return [seq for seq in product(ids, repeat=cycles) if all(allowed(a, b) for a, b in zip(seq, seq[1:], strict=False))]
