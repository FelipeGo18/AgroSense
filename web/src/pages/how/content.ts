/**
 * Textos de «¿Cómo funciona y de dónde sale esto?» (HU-122, HU-198). Diseño: design/pantallas/transversal.py, `how`.
 * Cada paso resume una regla de specs/01-reglas.md: si una regla cambia, cambia aquí. Lo que viene de la API (versiones,
 * pesos por defecto y su porqué, fuentes) no está aquí: sale de GET /api/v1/version.
 */

import type { MascotMood } from "@/components/mascot/Mascot";

/**
 * Paradas del recorrido, en orden: cada una tiene un lugar para la mascota, que baja por la explicación paso a paso
 * (como en Inicio) y termina en el pie de página. «Pesos» y «Fuentes» salen de GET /version: sin ellos, el recorrido
 * se las salta.
 */
const PATH = ["inicio", "paso-1", "paso-2", "paso-3", "paso-4", "paso-5", "paso-6", "nota", "luces"] as const;
export const STOPS_BASE = [...PATH, "no-hace"] as const;
export const STOPS_WITH_DATA = [...PATH, "pesos", "fuentes", "no-hace"] as const;
export type StopId = (typeof STOPS_WITH_DATA)[number];

/** Lo que dice la mascota en una parada y a dónde invita a seguir. */
export interface GuideLine {
  say: string;
  mood: MascotMood;
  next: StopId | null;
  nextLabel: string;
}

export interface Step extends GuideLine {
  id: StopId;
  title: string;
  body: string;
}

/** Cómo se decide, en el orden en que lo hace el motor. Cada paso es una parada del recorrido. */
export const STEPS: Step[] = [
  {
    id: "paso-1",
    title: "Estrategias para su terreno",
    body: "Armamos rotaciones de hasta 3 ciclos que cumplen las reglas agronómicas, cada una con su fuente, y las comparamos por agua, suelo, ingreso y riesgo, también contra la rotación que usted ya hace. Es una comparación: no predice cuánto mejora su suelo.",
    say: "Empiezo por su terreno: junto cultivos en orden y descarto los que rompen una regla.",
    mood: "guide",
    next: "paso-2",
    nextLabel: "Siguiente paso",
  },
  {
    id: "paso-2",
    title: "¿Se da en su zona?",
    body: "Primero miramos si el cultivo se da con la temperatura media de su municipio (NASA POWER, corregida por la altitud con NASADEM), según su ficha. Si no se da, se lo decimos y no evaluamos fechas.",
    say: "Antes de mirar fechas, reviso si el cultivo aguanta la temperatura de su zona.",
    mood: "watch",
    next: "paso-3",
    nextLabel: "Siguiente paso",
  },
  {
    id: "paso-3",
    title: "Seis señales de 0 a 100",
    body: "Para la fecha que eligió y lo que dura el cultivo: agua, heladas, calor, suelo, oferta y mercado. Cada una se compara con lo que ese cultivo necesita o aguanta.",
    say: "Luego califico seis señales, cada una contra lo que ese cultivo necesita.",
    mood: "guide",
    next: "paso-4",
    nextLabel: "Siguiente paso",
  },
  {
    id: "paso-4",
    title: "Un semáforo por reglas",
    body: "Una señal mala y grave basta para el rojo: no se compensa con las buenas. Sin datos de agua no damos semáforo; sin datos de oferta, se calcula sin ella.",
    say: "Si una señal grave sale mal, pongo rojo aunque las demás estén bien.",
    mood: "deny",
    next: "paso-5",
    nextLabel: "Siguiente paso",
  },
  {
    id: "paso-5",
    title: "Sus prioridades",
    body: "Cada señal pesa de 0 a 5. Un riesgo grave de agua, heladas o calor cuenta siempre. Si su luz y la de AgroSense difieren, le mostramos las dos.",
    say: "Usted dice qué le importa más. Si su luz y la mía no coinciden, le muestro las dos.",
    mood: "watch",
    next: "paso-6",
    nextLabel: "Siguiente paso",
  },
  {
    id: "paso-6",
    title: "Las mejores fechas",
    body: "Ordenamos las fechas del año por lo que más limita a cada una y, entre parecidas, por sus prioridades. Una fecha con un riesgo grave nunca queda entre las mejores.",
    say: "Al final ordeno las fechas: primero lo que más limita, después lo que usted prefiere.",
    mood: "celebrate",
    next: "nota",
    nextLabel: "Ver cómo leo una nota",
  },
];

/** Lo que dice la mascota en las paradas que no son pasos. */
export const GUIDE: Record<"nota" | "luces" | "pesos" | "fuentes" | "no-hace", GuideLine> = {
  nota: {
    say: "Una nota de 70 o más es favorable; por debajo de 40, desfavorable.",
    mood: "guide",
    next: "luces",
    nextLabel: "Ver las luces",
  },
  luces: {
    say: "Y así se ven las luces del semáforo. Sin datos de agua, no doy luz.",
    mood: "guide",
    next: "pesos",
    nextLabel: "Ver cuánto pesa cada señal",
  },
  pesos: {
    say: "Estos son mis pesos por defecto. Usted los puede cambiar en sus prioridades.",
    mood: "guide",
    next: "fuentes",
    nextLabel: "Ver de dónde salen los datos",
  },
  fuentes: {
    say: "Todo sale de estas fuentes, con su licencia. Las de la NASA van primero.",
    mood: "guide",
    next: "no-hace",
    nextLabel: "Ver lo que no hago",
  },
  "no-hace": {
    say: "Y esto nunca lo hago. La decisión es suya.",
    mood: "idle",
    next: null,
    nextLabel: "Volver arriba",
  },
};

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
