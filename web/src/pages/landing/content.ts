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

/**
 * El caso de Güicán de la Sierra (15332): papa sembrada el 7 de diciembre de 2026, en un municipio alto. Es un ejemplo y
 * se rotula así (R5). Las cifras son las que respondió el motor con el dataset 2026.11.25 para esa consulta, sin riego y
 * con el criterio de AgroSense; no se inventa ninguna. La oferta sale sin datos (HU-072 todavía no existe) y el mercado sin calificar (decisión 17).
 */
type PreviewSignal = { key: SignalKey; name: string; tone: keyof typeof TONE_LABEL; detail: string };

export const PREVIEW = {
  summary:
    "Papa en Güicán de la Sierra (Boyacá), sembrando el 7 de diciembre de 2026, sin riego. Primero lo que conviene hacer; después, por qué.",
  light: "red" as const,
  action: "Mejor otra fecha",
  reason:
    "Sembrando en diciembre, heló durante el cultivo (de diciembre a mayo) 53 de cada 100 años, de 1991 a 2020: es un riesgo grave que ninguna otra señal compensa. Y en un año seco la lluvia cubre el 57 % de lo que necesita la papa.",
  signals: [
    { key: "water", name: "Agua", tone: "red", detail: "33/100 · en un año seco cubre el 57 %" },
    { key: "frost", name: "Heladas", tone: "red", detail: "31/100 · heló 53 de cada 100 años, de 1991 a 2020 · riesgo grave" },
    { key: "heat", name: "Calor", tone: "green", detail: "100/100 · máxima de 19,4 °C; aguanta hasta 30 °C" },
    { key: "soil", name: "Suelo", tone: "green", detail: "100/100 · pH 5,8 (estimado)" },
    { key: "supply", name: "Oferta", tone: "insufficient_data", detail: "Esta versión de AgroSense todavía no evalúa la oferta" },
    { key: "market", name: "Mercado", tone: "unrated", detail: "No cambia la luz" },
  ] as PreviewSignal[],
};

/**
 * Las fuentes, como las calcula AgroSense: los productos de la NASA primero (decisión 12). La lluvia es GPM IMERG
 * (`catalog/sources.yaml`); NASA POWER es un reanálisis y se dice así (R8).
 */
export const SOURCES = [
  { kind: "Lluvia", name: "GPM IMERG · NASA", text: "La lluvia de su municipio vista por satélite, desde 2000." },
  {
    kind: "Clima",
    name: "NASA POWER",
    text: "Temperatura, heladas, calor y evaporación. Es un reanálisis (un modelo con observaciones), no una foto del satélite.",
  },
  { kind: "Altitud", name: "NASADEM · NASA", text: "La altura y la pendiente de su municipio o de su lote, a 30 m." },
  { kind: "Suelo", name: "SoilGrids · ISRIC", text: "pH, carbono orgánico y textura, estimados en celdas de 250 m." },
  {
    kind: "Oferta",
    name: "EVA",
    full: "Evaluaciones Agropecuarias",
    text: "Cuánto se sembró de cada cultivo, por municipio, junto a otras fuentes.",
  },
  { kind: "Mercado", name: "SIPSA · DANE", text: "Precios mayoristas de Corabastos y Tunja." },
];

export const GLOBE_CREDIT = "Contornos: Natural Earth · Color: NASA Blue Marble";
