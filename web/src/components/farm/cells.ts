/**
 * Cómo se reparte el lote vivo (HU-187): cuántos cubos tiene, cuántos le tocan a cada siembra en curso según su parte
 * del área, en qué etapa se dibuja cada una y qué cielo tiene según la hora. Lógica pura, sin dibujo: el dibujo sale
 * del diseño (`design/finca/exportar_web.py`).
 */

/** Una siembra en curso del lote, lo que el diorama necesita de ella. */
export interface LiveSeason {
  seasonId: string;
  cropId: string;
  areaHa: number;
  /** Etapa de FAO-56 de la ficha (`initial`, `development`, `mid`, `late`), o nula si no se sabe. */
  stage: string | null;
}

export interface LiveCell {
  /** La siembra que ocupa el cubo, o nula si es la parte libre del lote. */
  season: LiveSeason | null;
}

/** Los cultivos que el diseño sabe dibujar (los del catálogo de AgroSense). Otro cultivo se dibuja como parte libre. */
export const DRAWN_CROPS = ["papa", "maiz", "arveja", "haba", "zanahoria", "cebolla_bulbo", "avena_vicia", "descanso"] as const;

/** La etapa del dibujo (1 a 4) para cada etapa de FAO-56. Sin etapa, la primera: el cultivo recién nace. */
const DRAW_STAGE: Record<string, number> = { initial: 1, development: 2, mid: 3, late: 4 };
export const drawStage = (stage: string | null) => (stage ? (DRAW_STAGE[stage] ?? 1) : 1);

/**
 * Reparte los cubos del lote: cada siembra recibe al menos uno y el resto se reparte por su parte del área (el mayor
 * resto primero); lo que sobra del área es la parte libre. Con hasta tres siembras, 4 cubos (2 × 2); con más, 6 (3 × 2).
 * El orden es el de las siembras (R4: las mismas siembras dan el mismo dibujo).
 */
export function allocateCells(seasons: LiveSeason[], lotAreaHa: number): { layout: "2x2" | "3x2"; cells: LiveCell[] } {
  const layout = seasons.length > 3 ? "3x2" : "2x2";
  const total = layout === "3x2" ? 6 : 4;
  const sown = seasons.slice(0, total);
  const area = Math.max(
    lotAreaHa,
    sown.reduce((sum, s) => sum + s.areaHa, 0),
    1e-9,
  );
  const freeArea = Math.max(area - sown.reduce((sum, s) => sum + s.areaHa, 0), 0);
  const parts = [...sown.map((s) => s.areaHa), freeArea];
  const ideal = parts.map((a) => (a / area) * total);
  // Al menos un cubo por siembra; la parte libre solo si queda área sin sembrar.
  const counts = ideal.map((x, i) => (i < sown.length ? Math.max(1, Math.floor(x)) : Math.floor(x)));
  let left = total - counts.reduce((a, b) => a + b, 0);
  const order = ideal
    .map((x, i) => ({ i, rest: x - Math.floor(x) }))
    .filter(({ i }) => i < sown.length || freeArea > 0)
    .sort((a, b) => b.rest - a.rest || a.i - b.i);
  for (let k = 0; left > 0 && order.length; k = (k + 1) % order.length, left--) counts[order[k].i] += 1;
  // Si las siembras mínimas pasan del total (más siembras que cubos no ocurre: se cortan arriba), se quita de la mayor.
  while (counts.reduce((a, b) => a + b, 0) > total) {
    const biggest = counts.indexOf(Math.max(...counts));
    counts[biggest] -= 1;
  }
  const cells: LiveCell[] = [];
  sown.forEach((season, i) => {
    for (let n = 0; n < counts[i]; n++) cells.push({ season });
  });
  while (cells.length < total) cells.push({ season: null });
  return { layout, cells };
}

export type TimeOfDay = "dia" | "atardecer" | "noche";

/** El cielo según la hora local: día de 6 a 17, atardecer de 17 a 19 y noche el resto. Es ambiente, no un dato. */
export function timeOfDay(date: Date): TimeOfDay {
  const hour = date.getHours();
  if (hour >= 6 && hour < 17) return "dia";
  if (hour >= 17 && hour < 19) return "atardecer";
  return "noche";
}
