import type { Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";
import { PRIORITY_SIGNALS, type SignalWeights } from "@/features/diagnosis/priorities";
import { SIGNAL_NAME, type Signal } from "@/features/diagnosis/signals";

type DiagnosisRequestEcho = Schemas["DiagnosisRequestEcho"];
type LightResult = Schemas["LightResult"];

/**
 * Las dos luces (HU-203, decisión 10): la de las prioridades de quien consulta (`overall`) y la del criterio de
 * AgroSense (`overall_default`). Si son la misma luz se ve una sola; si difieren, las dos, la suya primero.
 */
export const sameLight = (overall: LightResult, byDefault: LightResult) => overall.light === byDefault.light;

/**
 * Los riesgos graves de clima cuentan siempre, aunque su peso sea 0 (`specs/01-reglas.md`, «Las prioridades del
 * agricultor»): agua, heladas, calor y, en P1, exceso de lluvia.
 */
const CLIMATE = new Set(["water", "frost", "heat", "excess_rain"]);

/** «Cuenta siempre: riesgo grave»: una señal de clima crítica que cuenta aunque la persona le puso peso 0. */
export function countsAlways(key: string, signal: Signal, weights: Partial<Record<string, number>> | null | undefined): boolean {
  return CLIMATE.has(key) && weights?.[key] === 0 && signal.counts === true && signal.critical === true && signal.level === "unfavorable";
}

/** «No cuenta para la luz con sus prioridades»: la señal se sigue viendo, pero con su peso no cambia la luz. */
export const notCounted = (signal: Signal) => signal.counts === false;

const WITH_ARTICLE: Record<string, string> = {
  water: "el agua",
  frost: "las heladas",
  heat: "el calor",
  soil: "el suelo",
  supply: "la oferta",
  market: "el mercado",
};

/**
 * La línea que dice por qué difieren las luces (`specs/05-frontend.md`, «Dos luces»): qué pesos puso la persona
 * distintos de los de AgroSense. «Usted puso la oferta en 0 (AgroSense: 2) y el agua en 5 (AgroSense: 3).» Sin los
 * pesos de AgroSense no se compara: se dice solo que usa los suyos.
 */
export function whyDifferent(weights: Partial<SignalWeights> | null | undefined, defaults: SignalWeights | null | undefined): string {
  if (!weights || !defaults) return "Las luces difieren porque usted usa sus propias prioridades.";
  const changes = PRIORITY_SIGNALS.filter(({ key }) => weights[key] !== undefined && weights[key] !== defaults[key]).map(
    ({ key }) => `${WITH_ARTICLE[key] ?? SIGNAL_NAME[key]} en ${weights[key]} (AgroSense: ${defaults[key]})`,
  );
  if (changes.length === 0) return "Las luces difieren porque usted usa sus propias prioridades.";
  const list = changes.length === 1 ? changes[0] : `${changes.slice(0, -1).join(", ")} y ${changes.at(-1)}`;
  return `Usted puso ${list}.`;
}

const IRRIGATION_PARAM = (irrigated: boolean | null) => (irrigated === true ? "si" : irrigated === false ? "no" : "nose");

/**
 * «Ver estrategias de rotación» (HU-203 → HU-214): la entrada a las estrategias con el municipio (o el lote), la fecha
 * de siembra y el cultivo consultado como el que había antes en el terreno. HU-214 los toma ya elegidos.
 */
export function strategiesLink(request: DiagnosisRequestEcho): string {
  const params = new URLSearchParams();
  if (request.lot_id) params.set("lote", request.lot_id);
  else params.set("municipio", request.municipality_id);
  params.set("siembra", request.sowing_date.slice(0, 7));
  params.set("anterior", request.crop_id);
  if (!request.lot_id) params.set("riego", IRRIGATION_PARAM(request.irrigated));
  return `${PATHS.consult}?${params.toString()}`;
}
