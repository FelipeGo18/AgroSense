"""Los datos de la señal de suelo (HU-183): lee el suelo estimado del municipio (`soil_municipality`, HU-181, ya cargado
en `dataset.soil`) y llama al motor con todo ya leído (R6). Sin errores HTTP, sin base de datos y sin guardar nada (R9).

El suelo no cambia con la fecha: el diagnóstico calcula la señal una vez por consulta y la misma va en todas las ventanas
(`window_signals`).

Con un lote dibujado usa las medianas de su polígono (HU-182). Sin dibujo usa
el municipio y lo dice en las limitaciones (R10).
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from backend.accounts.farm_models import Lot
from backend.api.lot_soil import zone_soil
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
    lot: Lot | None,
    crop: Mapping[str, Any],
    thresholds: Thresholds,
    crop_name: str,
) -> SoilSignalResult:
    """La señal `soil` del cultivo en el municipio: un `SoilSignalResult` del motor, que cumple `SignalResult`
    (`window_signals`) y va tal cual en cada ventana. `crop` es la ficha (`dataset.crops[crop_id]`) y `crop_name` su
    nombre con artículo («la papa»). Con lote sin dibujo y suelo, el suelo es el del municipio y
    se suma `LOT_SOIL_LIMITATION`."""
    row = zone_soil(dataset, municipality, lot)
    ph = None if row is None else ZoneSoilPh(row.get("ph"), row.get("ph_p05"), row.get("ph_p95"))
    result = soil_signal(ph, crop, thresholds, crop_name)
    # Solo si hay un suelo estimado del municipio que decirlo (PR #129): sin suelo, la señal ya dice que no lo hay.
    if lot is not None and lot.geometry is None and result.status == AVAILABLE:
        result = replace(result, limitations=(*result.limitations, LOT_SOIL_LIMITATION))
    return result
