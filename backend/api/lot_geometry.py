"""El contorno dibujado de un lote (HU-164; specs/02-contratos.md, «Cuerpos de cuenta»).

Un contorno es un polígono GeoJSON en WGS84, de un solo anillo (sin huecos), sin cruces, de área mayor que cero y
dentro del límite de su municipio. Su área la calcula la API sobre el elipsoide WGS84: la que envíe la web se ignora.
"""

import math
from dataclasses import dataclass
from typing import Any

import shapely
from pyproj import Geod
from shapely.geometry import Polygon, mapping
from shapely.geometry.base import BaseGeometry

from backend.api.errors import ApiError

_GEOD = Geod(ellps="WGS84")
# El límite publicado está simplificado a unos 10 m (pipeline/sources/dane_mgn.py): se deja el mismo margen para que
# un lote pegado al borde no se rechace por la simplificación.
EDGE_TOLERANCE_DEGREES = 0.0001
MAX_POINTS = 500
MAX_AREA_HA = 100_000
# Coordenadas con 7 decimales: unos 1,1 cm. Más no aporta y agranda lo guardado.
DECIMALS = 7


@dataclass(frozen=True)
class Drawn:
    geometry: dict[str, Any]
    area_ha: float


def _invalid(message: str, why: str) -> ApiError:
    return ApiError(422, "invalid_geometry", message, log=f"Contorno rechazado: {why}")


def _ring(geojson: dict[str, Any]) -> list[tuple[float, float]]:
    if geojson.get("type") != "Polygon" or not isinstance(geojson.get("coordinates"), list):
        raise _invalid("El contorno del lote debe ser un polígono.", "no es un Polygon de GeoJSON")
    rings = geojson["coordinates"]
    if len(rings) != 1:
        raise _invalid("El contorno del lote debe ser una sola figura, sin huecos.", "tiene huecos o ningún anillo")
    ring = rings[0]
    if not isinstance(ring, list) or not 4 <= len(ring) <= MAX_POINTS + 1:
        raise _invalid(f"El contorno debe tener entre 3 y {MAX_POINTS} puntos.", "número de puntos fuera de rango")
    points = []
    for position in ring:
        if not isinstance(position, list | tuple) or len(position) < 2:
            raise _invalid("El contorno tiene un punto mal formado.", "posición mal formada")
        lon, lat = position[0], position[1]
        if not all(isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) for v in (lon, lat)):
            raise _invalid("El contorno tiene un punto mal formado.", "coordenada no numérica")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise _invalid("El contorno tiene un punto fuera del mapa.", "coordenada fuera de rango")
        points.append((float(lon), float(lat)))
    return points


def drawn_lot(geojson: dict[str, Any], boundary: BaseGeometry, place: str) -> Drawn:
    """Valida el contorno contra el límite del municipio y devuelve el contorno normalizado y su área en hectáreas."""
    polygon = Polygon(_ring(geojson))
    if not polygon.is_valid:
        raise _invalid("Las líneas del contorno se cruzan. Mueva los puntos para que no se crucen.", shapely.is_valid_reason(polygon))
    if polygon.area <= 0:
        raise _invalid("El contorno no encierra ningún área.", "área cero")
    if not boundary.buffer(EDGE_TOLERANCE_DEGREES).covers(polygon):
        raise ApiError(
            422,
            "geometry_outside_municipality",
            f"Su lote se sale de {place}. Mueva los puntos dentro del límite del municipio.",
            log="Contorno rechazado: se sale del límite de su municipio",
        )
    # Sentido antihorario (el de GeoJSON) y coordenadas redondeadas: el mismo dibujo se guarda siempre igual (R4).
    polygon = shapely.set_precision(shapely.geometry.polygon.orient(polygon, sign=1.0), 10**-DECIMALS)
    area_m2, _ = _GEOD.geometry_area_perimeter(polygon)
    area_ha = round(abs(area_m2) / 10_000, 4)
    if area_ha <= 0 or area_ha > MAX_AREA_HA:
        raise _invalid("El área del contorno está fuera de lo posible para un lote.", f"área de {area_ha} ha")
    return Drawn(geometry=dict(mapping(polygon)), area_ha=area_ha)


def as_geojson(geometry: dict[str, Any]) -> dict[str, Any]:
    """`mapping` devuelve tuplas; en la base y en la respuesta van listas, como en GeoJSON."""
    return {"type": geometry["type"], "coordinates": [[list(point) for point in ring] for ring in geometry["coordinates"]]}
