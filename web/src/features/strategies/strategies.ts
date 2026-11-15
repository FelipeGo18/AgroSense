import { t, locale } from "@/lib/i18n";
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
export const CRITERIA = (): { key: keyof RotationWeights; label: string }[] => [
  { key: "water", label: t("landing.signal.water") },
  { key: "soil", label: t("landing.signal.soil") },
  { key: "income", label: t("components.ui.PriorityControl.income") },
  { key: "risk", label: t("components.ui.PriorityControl.risk") },
];

/** Los cinco criterios de la salud del suelo (decisión 14 suma la erosión). */
export const HEALTH_CRITERIA = (): { key: string; label: string }[] => [
  { key: "nitrogen", label: t("features.strategies.strategies.nitrogen") },
  { key: "organic_carbon", label: t("components.soil.SoilFacts.organicCarbon") },
  { key: "soil_cover", label: t("features.strategies.strategies.soilCover") },
  { key: "pest_break", label: t("features.strategies.strategies.pestBreak") },
  { key: "erosion", label: t("features.strategies.strategies.erosion") },
];

const LEVEL_TONE = (): Record<string, { tone: Tone; label: string }> => ({
  favorable: { tone: "green", label: t("status.green") },
  moderate: { tone: "yellow", label: t("status.yellow") },
  unfavorable: { tone: "red", label: t("status.red") },
});

/**
 * El nivel de un criterio de la salud del suelo con forma y texto. Sin datos se dice «Sin datos suficientes», con su
 * signo de pregunta, nunca como malo (R1). Un criterio que falta en la respuesta tampoco se inventa: es «sin datos».
 */
export function healthTone(criterion: HealthCriterion | undefined): { tone: Tone; label: string } {
  if (!criterion || criterion.status === "insufficient_data")
    return { tone: "insufficient_data", label: t("features.strategies.strategies.insufficientData") };
  if (criterion.status === "not_applicable") return { tone: "not_applicable", label: t("status.not_applicable") };
  return (
    (criterion.level && LEVEL_TONE()[criterion.level]) || {
      tone: "insufficient_data",
      label: t("features.strategies.strategies.insufficientData"),
    }
  );
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
  if (n > 0) return { shape: "up", words: t("features.strategies.strategies.moreThanToday", { v0: n }) };
  if (n < 0) return { shape: "down", words: t("features.strategies.strategies.lessThanToday", { v0: -n }) };
  return { shape: "same", words: t("features.strategies.strategies.sameAsToday") };
}

/** «Papa → Arveja → Papa», con el nombre del catálogo (el código si no está, nunca un nombre inventado). */
export const sequence = (cropIds: string[], names: Map<string, string>) => cropIds.map((id) => names.get(id) ?? id).join(" → ");

/** Cuántas se descartaron en total, por todos los motivos (`excluded_counts`); `excluded` trae solo las primeras 10. */
export const excludedTotal = (counts: Record<string, number> | null | undefined) =>
  Object.values(counts ?? {}).reduce((total, n) => total + n, 0);

const KIND_WORDS = (): Record<string, [string, string]> => ({
  rule: [t("features.strategies.strategies.dueToARotationRule"), t("features.strategies.strategies.dueToRotationRules")],
  high_risk: [t("features.strategies.strategies.dueToSevereClimateRisk"), t("features.strategies.strategies.dueToSevereClimateRisk2")],
  not_suitable: [
    t("features.strategies.strategies.becauseACropIsUnsuitableForThe"),
    t("features.strategies.strategies.becauseACropIsUnsuitableForThe"),
  ],
  soil_ph: [t("features.strategies.strategies.dueToSoilPh"), t("features.strategies.strategies.dueToSoilPh")],
});

/** «212 por reglas de rotación, 48 por riesgo grave de clima»: solo los motivos que descartaron alguna. */
export function excludedBreakdown(counts: Record<string, number> | null | undefined): string {
  return Object.entries(counts ?? {})
    .filter(([, n]) => n > 0)
    .map(([kind, n]) => `${n} ${(KIND_WORDS()[kind] ?? [kind, kind])[n === 1 ? 0 : 1]}`)
    .join(", ");
}

/** El motivo de una descartada o de un problema de la rotación actual, en pocas palabras, antes de su razón. */
export function exclusionTitle(item: Pick<Issue, "kind" | "signal" | "cycle">): string {
  switch (item.kind) {
    case "rule":
      return t("features.strategies.strategies.cycleViolatesARotationRule", { v0: item.cycle });
    case "not_suitable":
      return t("features.strategies.strategies.cycleUnsuitableForTheArea", { v0: item.cycle });
    case "soil_ph":
      return t("features.strategies.strategies.cycleSoilPhIsOutsideTheCrops", { v0: item.cycle });
    case "high_risk":
      return t("features.strategies.strategies.cycleHighClimateRisk", {
        v0: item.cycle,
        v1: item.signal ? ` (${(SIGNAL_NAME()[item.signal] ?? item.signal).toLowerCase()})` : "",
      });
  }
}

/** Abono verde, descanso o cultivo, según el catálogo (`kind`). */
export type CycleKind = "crop" | "cover" | "fallow";
export const cycleKind = (cropId: string, kinds: Map<string, string>): CycleKind => {
  const kind = kinds.get(cropId);
  return kind === "cover" || kind === "fallow" ? kind : "crop";
};

const NUMBER = () => new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 });

/** «carbono orgánico de 25 a 38 g/kg» con su rango del 5 al 95 % (R10). Sin rango, nulo. */
export function socRange(soil: MunicipalitySoil | undefined): string | null {
  const soc = soil?.soc_g_kg;
  if (!soc || soc.p05 === null || soc.p95 === null) return null;
  return t("features.strategies.strategies.organicCarbonFromToGkg", { v0: NUMBER().format(soc.p05), v1: NUMBER().format(soc.p95) });
}
