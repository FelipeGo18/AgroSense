/**
 * Cuentas de geografía del lote en el navegador: el área del dibujo mientras se dibuja y si se sale del municipio.
 * Son para avisar al instante; la API vuelve a validar y calcula el área que se guarda (backend/api/lot_geometry.py).
 */

export type Position = [number, number];
export interface LotPolygon {
  type: "Polygon";
  coordinates: Position[][];
}
export interface Boundary {
  type: "Polygon" | "MultiPolygon";
  coordinates: Position[][] | Position[][][];
}

// Radio de una esfera con la misma área que el elipsoide WGS84: el área queda muy cerca de la que calcula la API.
const EARTH_RADIUS_M = 6_371_007;
const rad = (degrees: number) => (degrees * Math.PI) / 180;

/** Área de un anillo sobre la esfera, en m² (la fórmula del exceso esférico, la misma de Turf). */
function ringArea(ring: Position[]): number {
  let total = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [lon1, lat1] = ring[i];
    const [lon2, lat2] = ring[i + 1];
    total += rad(lon2 - lon1) * (2 + Math.sin(rad(lat1)) + Math.sin(rad(lat2)));
  }
  return Math.abs((total * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
}

/** Hectáreas del dibujo, con dos decimales. */
export function areaHa(polygon: LotPolygon): number {
  return Math.round((ringArea(polygon.coordinates[0]) / 10_000) * 100) / 100;
}

/** Metros cuadrados, para el «25.100 m²» del recuadro del área. */
export const areaM2 = (polygon: LotPolygon) => Math.round(ringArea(polygon.coordinates[0]));

function insideRing([x, y]: Position, ring: Position[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function polygons(boundary: Boundary): Position[][][] {
  return boundary.type === "Polygon" ? [boundary.coordinates as Position[][]] : (boundary.coordinates as Position[][][]);
}

/** Si un punto cae dentro del límite (dentro del anillo exterior y fuera de sus huecos). */
export function inside(point: Position, boundary: Boundary): boolean {
  return polygons(boundary).some(([outer, ...holes]) => insideRing(point, outer) && !holes.some((hole) => insideRing(point, hole)));
}

/** Los puntos del dibujo que quedan fuera del municipio: se pintan en rojo y se pide moverlos. */
export function pointsOutside(polygon: LotPolygon, boundary: Boundary): Position[] {
  return polygon.coordinates[0].slice(0, -1).filter((point) => !inside(point, boundary));
}

/** Caja [oeste, sur, este, norte] de una geometría, para encuadrar el mapa. */
export function bbox(geometry: LotPolygon | Boundary): [number, number, number, number] {
  const points =
    geometry.type === "Polygon" ? (geometry.coordinates as Position[][]).flat() : (geometry.coordinates as Position[][][]).flat(2);
  const lons = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}

/** El centro de la caja: donde va la etiqueta del área sobre el lote. */
export function center(geometry: LotPolygon): Position {
  const [w, s, e, n] = bbox(geometry);
  return [(w + e) / 2, (s + n) / 2];
}

const M2 = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
export const formatM2 = (value: number) => `${M2.format(value)} m²`;
