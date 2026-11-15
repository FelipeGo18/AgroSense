import { t } from "@/lib/i18n";
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
export const STEPS = (): Step[] => [
  {
    id: "paso-1",
    title: t("pages.how.content.strategiesForYourLand"),
    body: t("pages.how.content.weBuildRotationsOfUpTo3"),
    mood: "guide",
  },
  {
    id: "paso-2",
    title: t("pages.how.content.isItSuitableForYourArea"),
    body: t("pages.how.content.firstWeCheckWhetherTheCropSuits"),
    mood: "guide",
  },
  {
    id: "paso-3",
    title: t("pages.how.content.sixSignalsScoredFrom0To100"),
    body: t("pages.how.content.forYourChosenDateAndTheCrops"),
    mood: "guide",
  },
  {
    id: "paso-4",
    title: t("pages.how.content.aRulebasedTrafficLight"),
    body: t("pages.how.content.oneSeverelyUnfavorableSignalIsEnoughFor"),
    mood: "guide",
  },
  {
    id: "paso-5",
    title: t("pages.account.PrioritiesCard.yourPriorities"),
    body: t("pages.how.content.eachSignalHasAWeightFrom0"),
    mood: "guide",
  },
  {
    id: "paso-6",
    title: t("pages.how.content.theBestDates"),
    body: t("pages.how.content.weRankDatesByTheirMostLimiting"),
    mood: "guide",
  },
];

/** El gesto de la mascota en las secciones de abajo, donde también señala a qué se refiere. */
export const SECTION_MOODS: Record<"pesos" | "fuentes" | "no-hace", MascotMood> = { pesos: "guide", fuentes: "guide", "no-hace": "guide" };

/** De la calificación al nivel (specs/01-reglas.md, «Cómo se califica cada señal»). */
export const BANDS = () =>
  [
    { label: t("status.red"), from: 0, to: 39, fill: "var(--color-semaforo-rojo-fondo)", ink: "text-semaforo-rojo-texto" },
    {
      label: t("pages.how.content.moderate"),
      from: 40,
      to: 69,
      fill: "var(--color-semaforo-amarillo-fondo)",
      ink: "text-semaforo-amarillo-texto",
    },
    { label: t("status.green"), from: 70, to: 100, fill: "var(--color-semaforo-verde-fondo)", ink: "text-semaforo-verde-texto" },
  ] as const;

/** Lo que AgroSense nunca hace («Lo que nunca se hace» de CLAUDE.md y las reglas R1, R2, R9 y R10). */
export const NEVER = (): string[] => [
  t("pages.how.content.doesNotForecastWeatherPricesOrHarvests"),
  t("pages.how.content.doesNotPredictSoilImprovementItCompares"),
  t("pages.how.content.doesNotUseTodaysWeatherForCalculations"),
  t("pages.how.content.doesNotFillMissingDataOrMix"),
  t("pages.how.content.doesNotMeasureYourPlotSoilAnd"),
  t("pages.how.content.doesNotSaveFarmDataWithoutAn"),
  t("pages.how.content.doesNotDecideForYouTheDecision"),
];
