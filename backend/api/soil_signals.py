"""Los datos de la señal de suelo (HU-183): lee el suelo estimado del municipio (`soil_municipality`, HU-181, ya cargado
en `dataset.soil`) y llama al motor con todo ya leído (R6). Sin errores HTTP, sin base de datos y sin guardar nada (R9).

El suelo no cambia con la fecha: el diagnóstico calcula la señal una vez por consulta y la misma va en todas las ventanas
(`window_signals`).

**El suelo es siempre el del municipio.** El suelo de un lote (la mediana de las celdas de `grid_cells` de su polígono)
es de HU-182: mientras no exista, una consulta con `lot_id` sigue usando el del municipio y lo dice en las limitaciones
con la frase del contrato (`LOT_SOIL_LIMITATION`; R1, R10). El lote no se lee aquí: solo si la consulta trae uno.
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from backend.config.thresholds import Thresholds
from backend.dataset import Dataset, Municipality
from backend.engine.signal_score import AVAILABLE
from backend.engine.soil_signal import SoilSignalResult, ZoneSoilPh, soil_signal

# La frase del contrato («Respuesta de diagnóstico», `limitations`).
LOT_SOIL_LIMITATION = "Suelo estimado para el municipio, no para su lote"


def zone_soil_ph(dataset: Dataset, municipality_id: str) -> ZoneSoilPh | None:
    """El pH del suelo del municipio tal como está publicado (`ph`, `ph_p05`, `ph_p95`). Sin fila: nulo (R1). Qué valor
    sirve (un nulo, un NaN) lo decide la señal en el motor."""
    row = dataset.soil.get(municipality_id)
    if row is None:
        return None
    return ZoneSoilPh(row.get("ph"), row.get("ph_p05"), row.get("ph_p95"))


def soil_for(
    dataset: Dataset,
    municipality: Municipality,
    has_lot: bool,
    crop: Mapping[str, Any],
    thresholds: Thresholds,
    crop_name: str,
) -> SoilSignalResult:
    """La señal `soil` del cultivo en el municipio: un `SoilSignalResult` del motor, que cumple `SignalResult`
    (`window_signals`) y va tal cual en cada ventana. `crop` es la ficha (`dataset.crops[crop_id]`) y `crop_name` su
    nombre con artículo («la papa»). Con `has_lot` y suelo, el suelo sigue siendo el del municipio y
    se suma `LOT_SOIL_LIMITATION`."""
    result = soil_signal(zone_soil_ph(dataset, municipality.municipality_id), crop, thresholds, crop_name)
    # Solo si hay un suelo estimado del municipio que decirlo (PR #129): sin suelo, la señal ya dice que no lo hay.
    if has_lot and result.status == AVAILABLE:
        result = replace(result, limitations=(*result.limitations, LOT_SOIL_LIMITATION))
    return result
