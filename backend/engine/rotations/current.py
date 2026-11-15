"""La rotación actual como referencia de las estrategias (HU-223, decisión 14).

Qué hace este módulo, en Python puro (R6: recibe valores y devuelve valores):

- `current_sequence`: arma la secuencia de la rotación actual con exactamente `cycles`
  cultivos. Con menos cultivos se repite desde el primero; con más, se conservan los
  primeros `cycles` (supuesto por confirmar con Felipe). Sin cultivos, no hay referencia
  y devuelve `None` (R1): quien llama agrega `NO_CURRENT_LIMITATION` a las limitaciones.
- `drop_current`: quita de las candidatas la que es igual a la actual (mismos `crop_id`
  en el mismo orden), porque una sugerida igual a la actual no se repite. Conserva el
  orden de las candidatas (R4).
- `vs_current`: cuánto gana o pierde una estrategia sugerida frente a la actual en cada
  criterio y en el total (sugerida menos actual, sobre los enteros). Un valor nulo o
  ausente en cualquiera de los dos lados da nula esa clave, nunca 0 (R1).

El puntaje de la actual sale del mismo `score_strategy` de HU-082, sin código aparte:
se arma y se evalúa como cualquier estrategia. Armar `current_strategy` en la respuesta
(con sus `issues`, sin excluirla nunca: R3) es de HU-084.
"""

from collections.abc import Mapping, Sequence

from backend.engine.rotations.ranking import CRITERIA

NO_CURRENT_LIMITATION = "Sin rotación actual: no hay una referencia para comparar las estrategias"

_VALID_CYCLES = (2, 3)


def current_sequence(current_crop_ids: Sequence[str] | None, cycles: int) -> tuple[str, ...] | None:
    """La rotación actual con exactamente `cycles` cultivos, o `None` si no hay."""
    if cycles not in _VALID_CYCLES:
        raise ValueError(f"cycles debe ser 2 o 3, no {cycles!r}")
    if not current_crop_ids:
        return None
    crops = tuple(current_crop_ids)
    return tuple(crops[i % len(crops)] for i in range(cycles))


def drop_current(candidates: Sequence[Sequence[str]], current: Sequence[str] | None) -> tuple[tuple[str, ...], ...]:
    """Las candidatas sin la igual a la actual (mismo orden de cultivos), en su orden."""
    sequences = tuple(tuple(candidate) for candidate in candidates)
    if current is None:
        return sequences
    reference = tuple(current)
    return tuple(sequence for sequence in sequences if sequence != reference)


def _difference(suggested: int | None, current: int | None) -> int | None:
    if suggested is None or current is None:
        return None
    return suggested - current


def vs_current(
    suggested_scores: Mapping[str, int | None],
    suggested_total: int | None,
    current_scores: Mapping[str, int | None] | None,
    current_total: int | None,
) -> dict[str, int | None] | None:
    """Sugerida menos actual por criterio y en `total`; `None` sin rotación actual."""
    if current_scores is None:
        return None
    result: dict[str, int | None] = {
        criterion: _difference(suggested_scores.get(criterion), current_scores.get(criterion)) for criterion in CRITERIA
    }
    result["total"] = _difference(suggested_total, current_total)
    return result
