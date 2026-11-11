import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import type { Irrigation } from "@/features/diagnosis/consult";
import type { SignalWeights } from "@/features/diagnosis/priorities";
import type { Season } from "@/features/farm/seasons";

export type RotationRequest = Schemas["RotationRequest"];
export type RotationResponse = Schemas["RotationResponse"];
export type RotationWeights = Schemas["RotationWeights"];

/**
 * La entrada a las estrategias de rotación (HU-214). Sin cuenta: municipio, área, qué había antes, cuándo sembrar el
 * primer ciclo, riego, cuántos ciclos y la rotación que viene haciendo (HU-223). Con cuenta, desde el lote: su
 * municipio, su riego y su historial.
 *
 * Va en la dirección, salvo el área: sin cuenta, el área solo se usa en este navegador para el agua del plan (HU-215) y
 * nunca llega al servidor ni a sus logs (R9). Por eso vive en `sessionStorage`, no en la dirección.
 */
export type Mode = "" | "none" | "crops";

export interface StrategyForm {
  municipalityId: string;
  areaText: string;
  /** Qué había antes: nada (primera siembra) o hasta 3 cultivos, el más reciente primero. */
  previousMode: Mode;
  previous: [string, string, string];
  month: string;
  irrigation: Irrigation | "";
  cycles: 2 | 3;
  /** La rotación que viene haciendo (HU-223): opcional; de 2 a 3 cultivos, en el orden en que los siembra. */
  currentMode: Mode;
  current: [string, string, string];
  /** Con cuenta: el lote y las siembras cosechadas de las que viene el terreno. */
  lotId: string;
  seasonIds: string[];
}

export type StrategyField = "municipality" | "area" | "previous" | "month" | "irrigation" | "current";
export type StrategyErrors = Partial<Record<StrategyField, string>>;

/** Las cuatro prioridades de la rotación (HU-101) empiezan iguales: ninguna pesa más hasta que la persona las mueva. */
export const START_PRIORITIES: RotationWeights = { water: 3, soil: 3, income: 3, risk: 3 };

export const EMPTY_STRATEGY: StrategyForm = {
  municipalityId: "",
  areaText: "",
  previousMode: "",
  previous: ["", "", ""],
  month: "",
  irrigation: "",
  cycles: 3,
  currentMode: "none",
  current: ["", "", ""],
  lotId: "",
  seasonIds: [],
};

export const STRATEGY_ERRORS: Record<StrategyField, string> = {
  municipality: "Elija su municipio de la lista.",
  area: "Escriba el área en hectáreas, mayor que cero (por ejemplo, 2,5).",
  previous: "Diga qué había antes: elija «Nada» o el último cultivo, y no deje huecos entre los cultivos.",
  month: "Elija el mes en que sembraría el primer ciclo.",
  irrigation: "Diga si tiene riego. Si no sabe, elija «No sé».",
  current: "Elija al menos dos cultivos, en el orden en que los siembra, o «No tengo una rotación fija».",
};

const AREA_KEY = "agrosense.area";

/** El área de la consulta, solo en esta pestaña (R9). Sin almacenamiento, vale mientras dure la página. */
export function readArea(): string {
  try {
    return sessionStorage.getItem(AREA_KEY) ?? "";
  } catch {
    return "";
  }
}

export function writeArea(text: string) {
  try {
    if (text) sessionStorage.setItem(AREA_KEY, text);
    else sessionStorage.removeItem(AREA_KEY);
  } catch {
    // Sin almacenamiento, el área vale solo en esta página.
  }
}

const IRRIGATED: Record<Irrigation, boolean | null> = { si: true, no: false, nose: null };
const list = (value: string | null) => (value ? value.split(",").filter(Boolean).slice(0, 3) : []);
const triple = (values: string[]): [string, string, string] => [values[0] ?? "", values[1] ?? "", values[2] ?? ""];
const filled = (values: string[]) => values.filter(Boolean);

/** De la dirección, incluido lo que manda el diagnóstico («Ver estrategias de rotación», HU-203). */
export function fromParams(params: URLSearchParams): StrategyForm {
  const irrigation = params.get("riego") ?? "";
  const previous = params.get("anterior");
  const current = list(params.get("actual"));
  return {
    ...EMPTY_STRATEGY,
    municipalityId: params.get("municipio") ?? "",
    areaText: readArea(),
    previousMode: previous === "ninguno" ? "none" : previous ? "crops" : "",
    previous: previous && previous !== "ninguno" ? triple(list(previous)) : ["", "", ""],
    month: params.get("siembra") ?? "",
    irrigation: irrigation === "si" || irrigation === "no" || irrigation === "nose" ? irrigation : "",
    cycles: params.get("ciclos") === "2" ? 2 : 3,
    currentMode: current.length > 0 ? "crops" : "none",
    current: triple(current),
    lotId: params.get("lote") ?? "",
    seasonIds: list(params.get("siembras")),
  };
}

/** A la dirección. El área nunca va (R9). Con lote, el municipio y el riego salen del lote. */
export function toParams(form: StrategyForm): URLSearchParams {
  const params = new URLSearchParams();
  if (form.lotId) {
    params.set("lote", form.lotId);
    if (form.seasonIds.length) params.set("siembras", form.seasonIds.join(","));
  } else params.set("municipio", form.municipalityId);
  params.set("siembra", form.month);
  if (!form.lotId) {
    params.set("anterior", form.previousMode === "none" ? "ninguno" : filled(form.previous).join(","));
    params.set("riego", form.irrigation);
  } else if (form.previousMode === "crops") {
    params.set("anterior", filled(form.previous).join(","));
  }
  params.set("ciclos", String(form.cycles));
  if (form.currentMode === "crops") params.set("actual", filled(form.current).join(","));
  return params;
}

export const hasEntry = (params: URLSearchParams) => ["municipio", "lote", "siembra"].some((key) => params.has(key));

/** Sin huecos: si hay un cultivo en la casilla 3, también en la 2 y en la 1. */
const noGaps = (values: string[]) => values.every((value, i) => !value || values.slice(0, i).every(Boolean));

export interface StrategyContext {
  municipalityIds: Set<string>;
  cropIds: Set<string>;
  months: string[];
  /** Con lote, el municipio, el riego y el área salen de él, y lo de antes, de sus siembras. */
  lot: boolean;
}

export function validate(form: StrategyForm, { municipalityIds, cropIds, months, lot }: StrategyContext): StrategyErrors {
  const errors: StrategyErrors = {};
  if (!lot && !municipalityIds.has(form.municipalityId)) errors.municipality = STRATEGY_ERRORS.municipality;
  if (!lot && parseArea(form.areaText) === null) errors.area = STRATEGY_ERRORS.area;
  if (!lot) {
    const prev = filled(form.previous);
    const bad =
      form.previousMode === "" ||
      (form.previousMode === "crops" && (prev.length === 0 || !noGaps(form.previous) || prev.some((id) => !cropIds.has(id))));
    if (bad) errors.previous = STRATEGY_ERRORS.previous;
  }
  if (!months.includes(form.month)) errors.month = STRATEGY_ERRORS.month;
  if (!lot && !form.irrigation) errors.irrigation = STRATEGY_ERRORS.irrigation;
  if (form.currentMode === "crops") {
    const current = filled(form.current);
    if (current.length < 2 || !noGaps(form.current) || current.some((id) => !cropIds.has(id))) errors.current = STRATEGY_ERRORS.current;
  }
  return errors;
}

/** «2,5» → 2,5 ha. Mayor que cero; lo demás no sirve. */
export function parseArea(text: string): number | null {
  const clean = text.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(clean)) return null;
  const value = Number(clean);
  return value > 0 && value <= 100_000 ? value : null;
}

/** Las siembras de un lote que dejaron el terreno libre: cosechadas y sin otra siembra encima. */
export function freeHarvested(seasons: Season[]): Season[] {
  return seasons.filter((s) => s.harvest_date && !seasons.some((n) => n.follows_season_ids.includes(s.season_id)));
}

/** Lo de antes con cuenta: los cultivos de las siembras elegidas, la más reciente primero, hasta 3 (`previous_crop_ids`). */
export function previousFromSeasons(chosen: Season[]): string[] {
  return [...chosen]
    .sort((a, b) => (b.harvest_date ?? "").localeCompare(a.harvest_date ?? ""))
    .map((s) => s.crop_id)
    .slice(0, 3);
}

/**
 * La rotación que viene haciendo, armada con el historial del terreno (HU-214, HU-223): las siembras elegidas y todas
 * las de las que vienen, del más antiguo al más reciente; las últimas tres. Con menos de dos no hay rotación que armar.
 */
export function currentFromHistory(chosen: Season[], seasons: Season[]): string[] {
  const byId = new Map(seasons.map((s) => [s.season_id, s]));
  const seen = new Map<string, Season>();
  const pending = [...chosen];
  while (pending.length) {
    const season = pending.pop()!;
    if (seen.has(season.season_id)) continue;
    seen.set(season.season_id, season);
    for (const id of season.follows_season_ids) {
      const before = byId.get(id);
      if (before) pending.push(before);
    }
  }
  const history = [...seen.values()].sort((a, b) => a.sowing_date.localeCompare(b.sowing_date)).map((s) => s.crop_id);
  const last = history.slice(-3);
  return last.length >= 2 ? last : [];
}

export interface LotFacts {
  lotId: string;
  municipalityId: string;
  irrigated: boolean | null;
  previous: string[];
}

/** El cuerpo de `POST /rotations`. Sin `signal_priorities` (el criterio de AgroSense no cargó), la API usa los suyos. */
export function toRequest(
  form: StrategyForm,
  priorities: RotationWeights,
  signalPriorities: SignalWeights | null,
  lot?: LotFacts,
): RotationRequest {
  const current = filled(form.current);
  return {
    municipality_id: lot ? lot.municipalityId : form.municipalityId,
    sowing_date: `${form.month}-01`,
    previous_crop_ids: lot ? lot.previous : form.previousMode === "none" ? [] : filled(form.previous),
    current_crop_ids: form.currentMode === "crops" && current.length >= 2 ? current : null,
    cycles: form.cycles,
    priorities,
    signal_priorities: signalPriorities,
    irrigated: lot ? lot.irrigated : IRRIGATED[form.irrigation as Irrigation],
    lot_id: lot ? lot.lotId : null,
  };
}

export const allZero = (p: RotationWeights) => p.water === 0 && p.soil === 0 && p.income === 0 && p.risk === 0;

/** Calcular no es guardar (R9): la API no guarda nada; se pide como una lectura y se recuerda en la visita. */
export function useRotations(request: RotationRequest | null) {
  return useQuery({
    queryKey: ["rotations", request],
    queryFn: () => api<RotationResponse>("/rotations", { body: request }),
    enabled: request !== null,
    retry: false,
    staleTime: Infinity,
  });
}

const FIELD_WORDS: Record<string, string> = {
  municipality_id: "el municipio",
  sowing_date: "el mes de siembra",
  previous_crop_ids: "lo que había antes",
  current_crop_ids: "la rotación que viene haciendo",
  cycles: "los ciclos",
  priorities: "sus prioridades de la rotación",
  signal_priorities: "sus prioridades de las señales",
  irrigated: "el riego",
  lot_id: "el lote",
};

/**
 * Un 422 en palabras sencillas (HU-214): la API dice «Revise: priorities, cycles»; aquí, «Revise: sus prioridades de la
 * rotación y los ciclos». Lo que no se reconoce se deja como viene.
 */
export function explain422(message: string): string {
  const match = message.match(/Revise:\s*(.+?)\.?$/);
  if (!match) return message;
  const words = match[1]
    .split(",")
    .map((field) => field.trim().split(".")[0])
    .filter((field, i, all) => field && all.indexOf(field) === i)
    .map((field) => FIELD_WORDS[field] ?? field);
  const joined = words.length > 1 ? `${words.slice(0, -1).join(", ")} y ${words.at(-1)}` : words[0];
  return `Hay un dato que no sirve para consultar. Revise ${joined}.`;
}
