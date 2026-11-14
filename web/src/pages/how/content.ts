/**
 * Textos de «¿Cómo funciona y de dónde sale esto?» (HU-122, HU-198). Diseño: design/pantallas/transversal.py, `how`.
 * Cada paso resume una regla de specs/01-reglas.md: si una regla cambia, cambia aquí. Lo que viene de la API (versiones,
 * pesos por defecto y su porqué, fuentes) no está aquí: sale de GET /api/v1/version.
 */

import type { MascotMood } from "@/components/mascot/Mascot";

/**
 * Paradas del recorrido, en orden: la mascota baja por los pasos numerados señalando cada tarjeta (como en Inicio) y
 * termina en el pie de página. «Pesos» y «Fuentes» salen de GET /version: sin ellos, el recorrido se las salta.
 */
const PATH = ["inicio", "paso-1", "paso-2", "paso-3", "paso-4", "paso-5", "paso-6"] as const;
export const STOPS_BASE = [...PATH, "no-hace"] as const;
export const STOPS_WITH_DATA = [...PATH, "pesos", "fuentes", "no-hace"] as const;
export type StopId = (typeof STOPS_WITH_DATA)[number];

/** Un paso del camino: su tarjeta y el gesto de la mascota, que la señala (sin globo: lo explica la tarjeta). */
export interface Step {
  id: StopId;
  title: string;
  body: string;
  mood: MascotMood;
}

/** Cómo se decide, en el orden en que lo hace el motor. Cada paso es una parada del recorrido. */
export const STEPS: Step[] = [
  {
    id: "paso-1",
    title: "Estrategias para su terreno",
    body: "Armamos rotaciones de hasta 3 ciclos que cumplen las reglas agronómicas, cada una con su fuente, y las comparamos por agua, suelo, ingreso y riesgo, también contra la rotación que usted ya hace. Es una comparación: no predice cuánto mejora su suelo.",
    mood: "guide",
  },
  {
    id: "paso-2",
    title: "¿Se da en su zona?",
    body: "Primero miramos si el cultivo se da con la temperatura media de su municipio (NASA POWER, corregida por la altitud con NASADEM), según su ficha. Si no se da, se lo decimos y no evaluamos fechas.",
    mood: "guide",
  },
  {
    id: "paso-3",
    title: "Seis señales de 0 a 100",
    body: "Para la fecha que eligió y lo que dura el cultivo: agua, heladas, calor, suelo, oferta y mercado. Cada una se compara con lo que ese cultivo necesita o aguanta.",
    mood: "guide",
  },
  {
    id: "paso-4",
    title: "Un semáforo por reglas",
    body: "Una señal mala y grave basta para el rojo: no se compensa con las buenas. Sin datos de agua no damos semáforo; sin datos de oferta, se calcula sin ella.",
    mood: "guide",
  },
  {
    id: "paso-5",
    title: "Sus prioridades",
    body: "Cada señal pesa de 0 a 5. Un riesgo grave de agua, heladas o calor cuenta siempre. Si su luz y la de AgroSense difieren, le mostramos las dos.",
    mood: "guide",
  },
  {
    id: "paso-6",
    title: "Las mejores fechas",
    body: "Ordenamos las fechas del año por lo que más limita a cada una y, entre parecidas, por sus prioridades. Una fecha con un riesgo grave nunca queda entre las mejores.",
    mood: "guide",
  },
];

/** El gesto de la mascota en las secciones de abajo, donde también señala a qué se refiere. */
export const SECTION_MOODS: Record<"pesos" | "fuentes" | "no-hace", MascotMood> = { pesos: "guide", fuentes: "guide", "no-hace": "guide" };

/** De la calificación al nivel (specs/01-reglas.md, «Cómo se califica cada señal»). */
export const BANDS = [
  { label: "Desfavorable", from: 0, to: 39, fill: "var(--color-semaforo-rojo-fondo)", ink: "text-semaforo-rojo-texto" },
  { label: "Moderada", from: 40, to: 69, fill: "var(--color-semaforo-amarillo-fondo)", ink: "text-semaforo-amarillo-texto" },
  { label: "Favorable", from: 70, to: 100, fill: "var(--color-semaforo-verde-fondo)", ink: "text-semaforo-verde-texto" },
] as const;

/** Lo que AgroSense nunca hace («Lo que nunca se hace» de CLAUDE.md y las reglas R1, R2, R9 y R10). */
export const NEVER: string[] = [
  "No pronostica el clima, el precio ni la cosecha: muestra lo que ha pasado en su zona.",
  "No predice cuánto mejora su suelo: compara estrategias según reglas con fuente.",
  "No usa el clima de hoy para calcular: solo para la escena.",
  "No rellena datos que faltan ni mezcla fuentes: si falta una, lo dice.",
  "No mide su lote: el suelo y el riego son estimaciones de la zona; verifique en campo.",
  "No guarda los datos de su finca sin cuenta ni quién consultó.",
  "No decide por usted: la decisión es suya.",
];
