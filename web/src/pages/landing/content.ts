import type { MascotMood, MascotSeed } from "@/components/mascot/Mascot";
import type { SignalKey } from "@/components/ui/SignalIcon";
import type { TONE_LABEL } from "@/components/ui/StatusTag";

/** Textos y datos de muestra de la portada. Vienen del diseño aprobado en Figma (design/pantallas/inicio.py). */

/** Paradas del recorrido, en orden: cada una es una sección y un lugar para la mascota. */
export const STOPS = [
  { id: "inicio", label: "Inicio" },
  { id: "preguntas", label: "Cuatro preguntas" },
  { id: "ejemplo", label: "Un ejemplo" },
  { id: "fuentes", label: "Los datos" },
] as const;

export type StopId = (typeof STOPS)[number]["id"];
export const STOP_IDS: readonly StopId[] = STOPS.map((stop) => stop.id);

/** Lo que dice la mascota al llegar a cada parada y a dónde invita a seguir. */
export const GUIDE: Record<Exclude<StopId, "inicio">, { say: string; mood: MascotMood; next: StopId | null; nextLabel: string }> = {
  preguntas: {
    say: "Estas son las cuatro preguntas que le ayudo a responder.",
    mood: "guide",
    next: "ejemplo",
    nextLabel: "Ver un ejemplo",
  },
  ejemplo: {
    say: "Así reviso cada ciclo: primero qué conviene hacer y después por qué.",
    mood: "guide",
    next: "fuentes",
    nextLabel: "Ver de dónde salen los datos",
  },
  fuentes: {
    say: "Todo sale de datos abiertos. La decisión siempre es suya.",
    mood: "celebrate",
    next: null,
    nextLabel: "Volver arriba",
  },
};

/** Las cuatro preguntas del flujo del MVP (decisión 12): estrategias, cada ciclo, agua del plan y qué cambió. */
export const QUESTIONS: { title: string; text: string; icon: "priority" | "light" | "water" | "frost"; seed: MascotSeed }[] = [
  {
    title: "¿Qué siembro y en qué orden?",
    text: "Estrategias de rotación de hasta 3 ciclos, comparadas por agua, suelo, ingreso y riesgo según lo que a usted le importa.",
    icon: "priority",
    seed: "sprouted",
  },
  {
    title: "¿Conviene cada siembra?",
    text: "Un semáforo por ciclo con seis señales: agua, heladas, calor, suelo, oferta y mercado.",
    icon: "light",
    seed: "bean",
  },
  {
    title: "¿Cuánta agua va a necesitar?",
    text: "Mes a mes, el agua que faltaría en cada ciclo, en rangos. Es una estimación con el clima de la zona.",
    icon: "water",
    seed: "maize",
  },
  {
    title: "¿Qué cambió en su zona?",
    text: "Heladas, lluvia y calor de dos periodos de la historia, lado a lado. No es un pronóstico.",
    icon: "frost",
    seed: "sprouted",
  },
];

/** El mismo caso del resultado amarillo del diseño. Son cifras de muestra y se rotulan como ejemplo (R5). */
export const PREVIEW = {
  summary: "Papa en Samacá, sembrando el 2 de agosto de 2027. Primero lo que conviene hacer; después, por qué. Cifras de muestra.",
  action: "Mejor otro cultivo en esta fecha",
  reason: "Se está sembrando mucha más papa que antes en Samacá. El clima de esta fecha sí le sirve: agua y calor bien, heladas moderadas.",
  signals: [
    { key: "water", name: "Agua", tone: "green", detail: "86/100 · alcanzó en 7 de 10 años" },
    { key: "frost", name: "Heladas", tone: "yellow", detail: "58/100 · heló 12 de cada 100 años" },
    { key: "heat", name: "Calor", tone: "green", detail: "94/100 · aguanta hasta 28 °C" },
    { key: "soil", name: "Suelo", tone: "green", detail: "80/100 · pH apto (estimado)" },
    { key: "supply", name: "Oferta", tone: "red", detail: "30/100 · +35 % de área sembrada" },
    { key: "market", name: "Mercado", tone: "insufficient_data", detail: "Sin datos de precios" },
  ] satisfies { key: SignalKey; name: string; tone: keyof typeof TONE_LABEL; detail: string }[],
};

export const SOURCES = [
  { kind: "Clima", name: "NASA POWER", text: "Lluvia, temperatura, heladas y calor de su municipio." },
  { kind: "Suelo", name: "SoilGrids · ISRIC", text: "pH, carbono orgánico y textura, estimados en celdas de 250 m." },
  {
    kind: "Oferta",
    name: "EVA",
    full: "Evaluaciones Agropecuarias",
    text: "Cuánto se sembró de cada cultivo, por municipio, junto a otras fuentes.",
  },
  { kind: "Mercado", name: "SIPSA · DANE", text: "Precios mayoristas, cuando hay datos de la zona." },
];

export const GLOBE_CREDIT = "Contornos: Natural Earth · Color: NASA Blue Marble";
