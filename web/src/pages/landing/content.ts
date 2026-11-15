import type { MascotMood, MascotSeed } from "@/components/mascot/Mascot";
import type { SignalKey } from "@/components/ui/SignalIcon";
import type { TONE_LABEL } from "@/components/ui/StatusTag";

/** Textos y datos de muestra de la portada. Vienen del diseño aprobado en Figma (design/pantallas/inicio.py). */

/** Paradas del recorrido, en orden: cada una es una sección y un lugar para la mascota. */
export const STOPS = [
  { id: "inicio", label: "landing.stop.home" },
  { id: "preguntas", label: "landing.stop.questions" },
  { id: "ejemplo", label: "landing.stop.example" },
  { id: "fuentes", label: "landing.stop.sources" },
] as const;

export type StopId = (typeof STOPS)[number]["id"];
export const STOP_IDS: readonly StopId[] = STOPS.map((stop) => stop.id);

/** Lo que dice la mascota al llegar a cada parada y a dónde invita a seguir. */
export const GUIDE: Record<Exclude<StopId, "inicio">, { say: string; mood: MascotMood; next: StopId | null; nextLabel: string }> = {
  preguntas: {
    say: "landing.guide.questions",
    mood: "guide",
    next: "ejemplo",
    nextLabel: "landing.guide.exampleLink",
  },
  ejemplo: {
    say: "landing.guide.example",
    mood: "guide",
    next: "fuentes",
    nextLabel: "landing.guide.sourcesLink",
  },
  fuentes: {
    say: "landing.guide.sources",
    mood: "celebrate",
    next: null,
    nextLabel: "landing.guide.top",
  },
};

/** Las cuatro preguntas del flujo del MVP (decisión 12): estrategias, cada ciclo, agua del plan y qué cambió. */
export const QUESTIONS: { title: string; text: string; icon: "priority" | "light" | "water" | "frost"; seed: MascotSeed }[] = [
  {
    title: "landing.question.rotation",
    text: "landing.question.rotationText",
    icon: "priority",
    seed: "sprouted",
  },
  {
    title: "landing.question.planting",
    text: "landing.question.plantingText",
    icon: "light",
    seed: "bean",
  },
  {
    title: "landing.question.water",
    text: "landing.question.waterText",
    icon: "water",
    seed: "maize",
  },
  {
    title: "landing.question.changes",
    text: "landing.question.changesText",
    icon: "frost",
    seed: "sprouted",
  },
];

/** El mismo caso del resultado amarillo del diseño. Son cifras de muestra y se rotulan como ejemplo (R5). */
export const PREVIEW = {
  summary: "landing.preview.summary",
  action: "landing.preview.action",
  reason: "landing.preview.reason",
  signals: [
    { key: "water", name: "landing.signal.water", tone: "green", detail: "landing.detail.water" },
    { key: "frost", name: "landing.signal.frost", tone: "yellow", detail: "landing.detail.frost" },
    { key: "heat", name: "landing.signal.heat", tone: "green", detail: "landing.detail.heat" },
    { key: "soil", name: "landing.signal.soil", tone: "green", detail: "landing.detail.soil" },
    { key: "supply", name: "landing.signal.supply", tone: "red", detail: "landing.detail.supply" },
    { key: "market", name: "landing.signal.market", tone: "insufficient_data", detail: "landing.detail.market" },
  ] satisfies { key: SignalKey; name: string; tone: keyof ReturnType<typeof TONE_LABEL>; detail: string }[],
};

export const SOURCES = [
  { kind: "landing.source.climate", name: "NASA POWER", text: "landing.source.power" },
  { kind: "landing.signal.soil", name: "SoilGrids · ISRIC", text: "landing.source.soil" },
  {
    kind: "landing.signal.supply",
    name: "EVA",
    full: "landing.source.evaName",
    text: "landing.source.eva",
  },
  { kind: "landing.signal.market", name: "SIPSA · DANE", text: "landing.source.sipsa" },
];

export const GLOBE_CREDIT = "landing.globe.credit";
