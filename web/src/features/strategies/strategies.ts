import type { Schemas } from "@/api/client";
import type { Tone } from "@/components/ui/StatusMark";
import { SIGNAL_NAME, sourceName, type MunicipalitySoil } from "@/features/diagnosis/signals";
import type { Version } from "@/features/version";
import type { RotationWeights } from "./entry";

export type Strategy = Schemas["Strategy"];
export type Cycle = Schemas["Cycle"];
export type HealthCriterion = Schemas["HealthCriterion"];
export type Exclusion = Schemas["Exclusion"];
export type Issue = Schemas["Issue"];
export type VsCurrent = Schemas["VsCurrent"];

/**
 * Cómo se lee una estrategia (HU-102): sus ciclos, su desglose por criterio, su salud del suelo, sus problemas y las
 * descartadas. Todo sale de la respuesta de `POST /rotations`; aquí no se calcula ningún puntaje (R5).
 */

/** Los cuatro criterios del orden, en el orden del diseño. */
export const CRITERIA: { key: keyof RotationWeights; label: string }[] = [
  { key: "water", label: "Agua" },
  { key: "soil", label: "Suelo" },
  { key: "income", label: "Ingreso" },
  { key: "risk", label: "Riesgo" },
];

/** Los cinco criterios de la salud del suelo (decisión 14 suma la erosión). */
export const HEALTH_CRITERIA: { key: string; label: string }[] = [
  { key: "nitrogen", label: "Nitrógeno" },
  { key: "organic_carbon", label: "Carbono orgánico" },
  { key: "soil_cover", label: "Suelo cubierto" },
  { key: "pest_break", label: "Corte de plagas" },
  { key: "erosion", label: "Erosión" },
];

const LEVEL_TONE: Record<string, { tone: Tone; label: string }> = {
  favorable: { tone: "green", label: "Favorable" },
  moderate: { tone: "yellow", label: "Moderado" },
  unfavorable: { tone: "red", label: "Desfavorable" },
};

/**
 * El nivel de un criterio de la salud del suelo con forma y texto. Sin datos se dice «Sin datos suficientes», con su
 * signo de pregunta, nunca como malo (R1). Un criterio que falta en la respuesta tampoco se inventa: es «sin datos».
 */
export function healthTone(criterion: HealthCriterion | undefined): { tone: Tone; label: string } {
  if (!criterion || criterion.status === "insufficient_data") return { tone: "insufficient_data", label: "Sin datos suficientes" };
  if (criterion.status === "not_applicable") return { tone: "not_applicable", label: "No aplica" };
  return (criterion.level && LEVEL_TONE[criterion.level]) || { tone: "insufficient_data", label: "Sin datos suficientes" };
}

/** «Agrosavia · NASADEM»: las fuentes con su nombre de `GET /version` (R8). Sin fuentes, nulo: no se inventa ninguna. */
export function sourcesText(sourceIds: string[] | null | undefined, version: Version | undefined): string | null {
  const ids = [...new Set(sourceIds ?? [])];
  return ids.length ? ids.map((id) => sourceName(id, version)).join(" · ") : null;
}

export interface Delta {
  /** up: gana frente a lo de hoy; down: pierde; same: igual. */
  shape: "up" | "down" | "same";
  /** «6 más que hoy», «9 menos que hoy», «Igual que hoy». */
  words: string;
}

/** Lo que una sugerida gana o pierde frente a la rotación actual (`vs_current`), con forma y texto. Nulo: no se dice nada. */
export function delta(value: number | null | undefined): Delta | null {
  if (value === null || value === undefined) return null;
  const n = Math.round(value);
  if (n > 0) return { shape: "up", words: `${n} más que hoy` };
  if (n < 0) return { shape: "down", words: `${-n} menos que hoy` };
  return { shape: "same", words: "Igual que hoy" };
}

/** «Papa → Arveja → Papa», con el nombre del catálogo (el código si no está, nunca un nombre inventado). */
export const sequence = (cropIds: string[], names: Map<string, string>) => cropIds.map((id) => names.get(id) ?? id).join(" → ");

/** Cuántas se descartaron en total, por todos los motivos (`excluded_counts`); `excluded` trae solo las primeras 10. */
export const excludedTotal = (counts: Record<string, number> | null | undefined) =>
  Object.values(counts ?? {}).reduce((total, n) => total + n, 0);

const KIND_WORDS: Record<string, [string, string]> = {
  rule: ["por una regla de rotación", "por reglas de rotación"],
  high_risk: ["por un riesgo grave de clima", "por riesgo grave de clima"],
  not_suitable: ["porque un cultivo no se da en su zona", "porque un cultivo no se da en su zona"],
  soil_ph: ["por el pH del suelo", "por el pH del suelo"],
};

/** «212 por reglas de rotación, 48 por riesgo grave de clima»: solo los motivos que descartaron alguna. */
export function excludedBreakdown(counts: Record<string, number> | null | undefined): string {
  return Object.entries(counts ?? {})
    .filter(([, n]) => n > 0)
    .map(([kind, n]) => `${n} ${(KIND_WORDS[kind] ?? [kind, kind])[n === 1 ? 0 : 1]}`)
    .join(", ");
}

/** El motivo de una descartada o de un problema de la rotación actual, en pocas palabras, antes de su razón. */
export function exclusionTitle(item: Pick<Issue, "kind" | "signal" | "cycle">): string {
  switch (item.kind) {
    case "rule":
      return `Ciclo ${item.cycle}: no cumple una regla de rotación`;
    case "not_suitable":
      return `Ciclo ${item.cycle}: no se da en su zona`;
    case "soil_ph":
      return `Ciclo ${item.cycle}: el pH del suelo queda fuera de lo que tolera`;
    case "high_risk":
      return `Ciclo ${item.cycle}: alto riesgo de clima${item.signal ? ` (${(SIGNAL_NAME[item.signal] ?? item.signal).toLowerCase()})` : ""}`;
  }
}

/** Abono verde, descanso o cultivo, según el catálogo (`kind`). */
export type CycleKind = "crop" | "cover" | "fallow";
export const cycleKind = (cropId: string, kinds: Map<string, string>): CycleKind => {
  const kind = kinds.get(cropId);
  return kind === "cover" || kind === "fallow" ? kind : "crop";
};

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });

/** «carbono orgánico de 25 a 38 g/kg» con su rango del 5 al 95 % (R10). Sin rango, nulo. */
export function socRange(soil: MunicipalitySoil | undefined): string | null {
  const soc = soil?.soc_g_kg;
  if (!soc || soc.p05 === null || soc.p95 === null) return null;
  return `carbono orgánico de ${NUMBER.format(soc.p05)} a ${NUMBER.format(soc.p95)} g/kg`;
}
