/**
 * Geometría de la Tierra de la portada. Los datos salen de design/globo/build_globo.py (`export_web`):
 * facetas en la esfera unidad, con x a la derecha, y al norte y z hacia la cámara cuando el meridiano 0 está al frente.
 */

export interface GlobeData {
  source: string;
  /** Las coordenadas vienen multiplicadas por este número. */
  scale: number;
  ocean_color: string;
  light: [number, number, number];
  /** Triángulos del mar: nueve números por faceta. */
  ocean: number[][];
  colors: string[];
  /** Facetas de tierra: índice de color, normal y puntos. */
  land: [color: number, normal: number[], points: number[]][];
  /** Contorno de la región piloto. */
  outline: number[][];
  pilot: { lon: number; lat: number; vec: number[] };
}

export type Rgb = [number, number, number];

export const parseHex = (hex: string): Rgb => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as Rgb;

/** Aclara (f > 0) u oscurece (f < 0) un color, igual que `shade` del kit de diseño. */
export function shade([r, g, b]: Rgb, f: number) {
  const mix = (c: number) => Math.round(f >= 0 ? c + (255 - c) * f : c * (1 + f));
  return `rgb(${mix(r)} ${mix(g)} ${mix(b)})`;
}

/** Cuánta luz recibe una faceta según hacia dónde mira, con los mismos topes que el diseño. */
export function lightFactor(normalDotLight: number, jitter: number) {
  return Math.max(-0.38, Math.min(0.14, (normalDotLight - 0.62) * 0.55 + jitter));
}

export interface Rotation {
  cosLon: number;
  sinLon: number;
  cosLat: number;
  sinLat: number;
}

/** Giro que deja (lon0, lat0) al frente. */
export function rotation(lon0: number, lat0: number): Rotation {
  const lon = (-lon0 * Math.PI) / 180;
  const lat = (lat0 * Math.PI) / 180;
  return { cosLon: Math.cos(lon), sinLon: Math.sin(lon), cosLat: Math.cos(lat), sinLat: Math.sin(lat) };
}

/** Aplica el giro al punto que empieza en `data[i]` y lo escribe en `out`. */
export function rotateInto(out: number[], data: ArrayLike<number>, i: number, r: Rotation) {
  const x = data[i] * r.cosLon + data[i + 2] * r.sinLon;
  const z = -data[i] * r.sinLon + data[i + 2] * r.cosLon;
  out[0] = x;
  out[1] = data[i + 1] * r.cosLat - z * r.sinLat;
  out[2] = data[i + 1] * r.sinLat + z * r.cosLat;
}

/** Va de la longitud `from` a `to` por el camino corto. `t` de 0 a 1. */
export function lerpLon(from: number, to: number, t: number) {
  const delta = ((((to - from) % 360) + 540) % 360) - 180;
  return from + delta * t;
}

/** Generador de números con semilla: las estrellas salen siempre en el mismo sitio. */
export function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
