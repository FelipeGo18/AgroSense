import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import type { RotationResponse } from "./entry";
import type { Cycle, Strategy } from "./strategies";

export type WaterPlanRequest = Schemas["WaterPlanRequest"];
export type WaterPlanResponse = Schemas["WaterPlanResponse"];
export type WaterMonth = Schemas["WaterMonth"];
export type SoilMoisture = Schemas["SoilMoisture"];

/**
 * El ciclo de una estrategia (HU-215): se abre en la misma dirección de la consulta con `estrategia` (su secuencia de
 * cultivos, u «hoy» para la rotación actual) y `ciclo` (1 a 3). Así se puede volver atrás, compartir y recargar, y el resultado no
 * se vuelve a calcular: es la misma consulta, que ya está en la memoria de la visita.
 */
export const TODAY = "hoy";

export function cycleParams(params: URLSearchParams, strategyKey: string, cycle: number): URLSearchParams {
  const next = new URLSearchParams(params);
  next.set("estrategia", strategyKey);
  next.set("ciclo", String(cycle));
  return next;
}

export function withoutCycle(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  next.delete("estrategia");
  next.delete("ciclo");
  return next;
}

/**
 * La llave de una estrategia en la dirección: «hoy» para la rotación actual y, para una sugerida, su secuencia de
 * cultivos (`avena_vicia-arveja-papa`), que es única en la respuesta. No el puesto: con otras prioridades el orden cambia
 * y el puesto 1 sería otra estrategia.
 */
export const strategyKey = (strategy: Strategy) => (strategy.kind === "current" ? TODAY : strategy.crop_ids.join("-"));

export interface OpenCycle {
  strategy: Strategy;
  cycle: Cycle;
}

/** El ciclo que pide la dirección, si existe en la respuesta. Si no (otra consulta, otro orden), nulo: se vuelve a la lista. */
export function findCycle(data: RotationResponse | undefined, key: string | null, n: string | null): OpenCycle | null {
  if (!data || !key || !n) return null;
  const strategy = key === TODAY ? data.current_strategy : data.strategies.find((s) => s.crop_ids.join("-") === key);
  const cycle = strategy?.cycles.find((c) => String(c.cycle) === n);
  return strategy && cycle ? { strategy, cycle } : null;
}

/**
 * El agua del ciclo (`POST /water-plans`): su cultivo, su fecha y el área de la entrada, todo el terreno (`area_pct`
 * 100). Calcular no es guardar (R9): la API no guarda la finca ni quién consultó.
 */
export function waterRequest(municipalityId: string, areaHa: number | null, cycle: Cycle): WaterPlanRequest | null {
  if (!areaHa || areaHa <= 0) return null;
  return {
    municipality_id: municipalityId,
    total_area_ha: areaHa,
    crops: [{ crop_id: cycle.crop_id, area_pct: 100, sowing_date: cycle.sowing_date }],
  };
}

export function useWaterPlan(request: WaterPlanRequest | null) {
  return useQuery({
    queryKey: ["water-plans", request],
    queryFn: () => api<WaterPlanResponse>("/water-plans", { body: request }),
    enabled: request !== null,
    retry: false,
    staleTime: Infinity,
  });
}

/** Sin riego (o sin saberlo) la falta de lluvia es sed; con riego, el agua que habría que poner (`specs/05-frontend.md`). */
export const shortfallWords = (irrigated: boolean | null | undefined) =>
  irrigated === true ? "riego que haría falta" : "el cultivo pasaría sed";

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });

/** «8 a 20 mm» o «20 mm». Sin rango, nulo (R1). Un rango, nunca un número solo, porque es una estimación (R10). */
export function formatRange(range: number[] | null | undefined, unit: string): string | null {
  if (!range || range.length < 2) return null;
  const [low, high] = range;
  return low === high ? `${NUMBER.format(low)} ${unit}` : `${NUMBER.format(low)} a ${NUMBER.format(high)} ${unit}`;
}

/** Un mes sin déficit trae `[0, 0]`: la lluvia alcanza. */
export const noShortfall = (range: number[] | null | undefined) => Boolean(range && range.length >= 2 && range[1] === 0);

const DAY = 86_400_000;
const utc = (iso: string) => new Date(`${iso}T00:00:00Z`).getTime();

/** Las semanas de un descanso, de su inicio a su fin. */
export const weeksBetween = (from: string, to: string) => Math.max(1, Math.round((utc(to) - utc(from)) / (7 * DAY)));

/** El periodo de 16 días del NDVI de MODIS (1 a 23) en que cae una fecha, por su día del año. */
export function ndviPeriod(iso: string): number {
  const date = new Date(`${iso}T00:00:00Z`);
  const start = Date.UTC(date.getUTCFullYear(), 0, 1);
  const dayOfYear = Math.floor((date.getTime() - start) / DAY) + 1;
  return Math.min(23, Math.floor((dayOfYear - 1) / 16) + 1);
}

/**
 * Los periodos del NDVI que cubre la ventana de un ciclo, como tramos `[desde, hasta]`. Si pasa de diciembre a enero
 * son dos tramos; si dura un año o más, todo el año.
 */
export function windowSpans(sowing: string, harvest: string): [number, number][] {
  if (utc(harvest) - utc(sowing) >= 365 * DAY) return [[1, 23]];
  const from = ndviPeriod(sowing);
  const to = ndviPeriod(harvest);
  return from <= to
    ? [[from, to]]
    : [
        [from, 23],
        [1, to],
      ];
}
