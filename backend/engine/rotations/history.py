"""Historia única del terreno (HU-081, decisión 6): una sola función arma los cultivos anteriores y su `history_basis`,
y el filtro y `soil_health` los usan igual (R4, R5). Python puro (R6)."""

from collections.abc import Sequence
from dataclasses import dataclass

HISTORY_BASES = ("declared", "current_rotation", "none")
HISTORY_TEXT = {
    "none": "No hay cultivos anteriores del terreno: solo se revisan los ciclos de la estrategia",
    "current_rotation": "Se supuso que antes del primer ciclo el terreno siguió su rotación actual",
}
MAX_HISTORY = 3


@dataclass(frozen=True)
class TerrainHistory:
    """Cultivos anteriores del más reciente al más antiguo y de dónde salen (`history_basis`)."""

    crop_ids: tuple[str, ...]
    basis: str


def terrain_history(previous_crop_ids: Sequence[str] | None, current_crop_ids: Sequence[str] | None) -> TerrainHistory:
    """`previous_crop_ids` con cultivos: tal cual (`declared`, sin recortar: llega validada por la API). Si no, la
    rotación actual recorrida del último al primero y repetida o recortada a exactamente 3 cultivos
    (`current_rotation`): `[a, b, c, d]` da `(d, c, b)` y `[papa]` da `(papa, papa, papa)`. Ninguna: `()` y `none`.
    No muta las entradas."""
    if previous_crop_ids:
        return TerrainHistory(tuple(previous_crop_ids), "declared")
    if current_crop_ids:
        backwards = tuple(reversed(current_crop_ids))
        return TerrainHistory(tuple(backwards[i % len(backwards)] for i in range(MAX_HISTORY)), "current_rotation")
    return TerrainHistory((), "none")


def check_history(previous_crop_ids: Sequence[str], history_basis: str) -> None:
    """`ValueError` si `history_basis` no es válido o contradice la lista de cultivos anteriores."""
    if history_basis not in HISTORY_BASES:
        raise ValueError(f"history_basis {history_basis!r} no es válido: use uno de 'declared', 'current_rotation' o 'none'")
    if (history_basis == "none") == bool(previous_crop_ids):
        raise ValueError(
            f"history_basis {history_basis!r} contradice previous_crop_ids ({len(previous_crop_ids)} cultivos): "
            "'none' va sin cultivos anteriores; 'declared' y 'current_rotation' van con ellos"
        )
