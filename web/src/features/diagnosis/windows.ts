import type { Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";

type DiagnosisRequestEcho = Schemas["DiagnosisRequestEcho"];
export type WindowSummary = Schemas["WindowSummary"];
export type Suitability = Schemas["SuitabilityResult"];

/**
 * La nota de aptitud en la escala de cinco semillas (HU-194): una semilla por cada 20 puntos, redondeado (92 → 5,
 * 50 → 3, 9 → 0). Es informativa: no es una señal ni cambia la luz. Sin nota no hay semillas: cero semillas diría «no
 * apto» (R1).
 */
export function seedsFor(score: number | null | undefined): number | null {
  if (score === null || score === undefined) return null;
  return Math.round(Math.max(0, Math.min(100, score)) / 20);
}

const IRRIGATION_PARAM = (irrigated: boolean | null) => (irrigated === true ? "si" : irrigated === false ? "no" : "nose");

/** La consulta del diagnóstico en la dirección, como la arma la consulta (HU-091), a partir de lo que la API respondió. */
function consultParams(request: DiagnosisRequestEcho, { cropId, month }: { cropId: string | null; month: string }) {
  const params = new URLSearchParams();
  if (request.lot_id) params.set("lote", request.lot_id);
  else params.set("municipio", request.municipality_id);
  if (cropId) params.set("cultivo", cropId);
  params.set("siembra", month);
  if (!request.lot_id) params.set("riego", IRRIGATION_PARAM(request.irrigated));
  return params;
}

/** Tocar una de las mejores ventanas consulta el diagnóstico de esa fecha: el mismo lugar, cultivo y riego. */
export function windowLink(request: DiagnosisRequestEcho, sowingStart: string): string {
  return `${PATHS.diagnosis}?${consultParams(request, { cropId: request.crop_id, month: sowingStart.slice(0, 7) }).toString()}`;
}

/** «Elegir otro cultivo»: la misma consulta sin cultivo, para elegir otro en el formulario. */
export function otherCropLink(request: DiagnosisRequestEcho): string {
  return `${PATHS.diagnosis}?${consultParams(request, { cropId: null, month: request.sowing_date.slice(0, 7) }).toString()}`;
}

/** Si alguna de las dos luces dice «otra fecha»: entonces se muestran las mejores ventanas (`specs/02-contratos.md`). */
export const asksOtherWindow = (overall: { action: string }, byDefault: { action: string }) =>
  overall.action === "other_window" || byDefault.action === "other_window";

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });

/** «Temperatura media anual de 26,3 °C a 300 m de altitud, la del municipio»: el dato con que se decidió la aptitud. */
export function suitabilityFacts(suitability: Suitability): string | null {
  if (suitability.tmean_annual_c === null || suitability.tmean_annual_c === undefined) return null;
  const altitude =
    suitability.altitude_m === null || suitability.altitude_m === undefined
      ? ""
      : ` a ${new Intl.NumberFormat("es-CO").format(Math.round(suitability.altitude_m))} m de altitud`;
  const basis = suitability.basis === "lot" ? "la de su lote" : "la del municipio";
  return `Temperatura media anual de ${NUMBER.format(suitability.tmean_annual_c)} °C${altitude}, ${basis}.`;
}
