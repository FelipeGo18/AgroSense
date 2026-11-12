import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import type { Version } from "@/features/version";

export type Signal = Schemas["Signal"];
export type SourceValue = Schemas["SourceValue"];
export type SupplySemester = Schemas["SupplySemester"];
export type MunicipalitySoil = Schemas["MunicipalitySoil"];

/**
 * Las señales de una ventana, como las muestra el resultado del diagnóstico (HU-092). Las seis del P0 van siempre en
 * este orden; las del P1 solo si vienen en la respuesta (`specs/01-reglas.md`, «Señales de una ventana»): no se inventan.
 */
export const P0_SIGNALS = ["water", "frost", "heat", "soil", "supply", "market"] as const;
export const P1_SIGNALS = ["excess_rain", "disease", "harvest_weather"] as const;
export type P0Signal = (typeof P0_SIGNALS)[number];

export const SIGNAL_NAME: Record<string, string> = {
  water: "Agua",
  frost: "Heladas",
  heat: "Calor",
  soil: "Suelo",
  supply: "Oferta",
  market: "Mercado",
  excess_rain: "Exceso de lluvia",
  disease: "Enfermedades por clima",
  harvest_weather: "Clima en la cosecha",
};

export const isP0 = (key: string): key is P0Signal => (P0_SIGNALS as readonly string[]).includes(key);

/**
 * Los campos nulos pueden no venir en la respuesta (los ejemplos los omiten). Aquí «no viene» y `null` son lo mismo, para
 * que una señal sin datos nunca se lea como calificación 0 (R1).
 */
export function normalized(signal: Signal): Signal {
  return { ...signal, level: signal.level ?? null, score: signal.score ?? null, sources: signal.sources ?? null };
}

/** Las señales en su orden: las seis del P0 que vengan, después las del P1 que vengan. Ninguna otra. */
export function orderedSignals(signals: Record<string, Signal> | null | undefined): [string, Signal][] {
  if (!signals) return [];
  return [...P0_SIGNALS, ...P1_SIGNALS].flatMap((key) => (signals[key] ? [[key, normalized(signals[key])] as [string, Signal]] : []));
}

/**
 * Las señales que pueden ser críticas (`specs/01-reglas.md`, «Señales de una ventana»). El suelo, las enfermedades y el
 * clima en la cosecha nunca lo son: aunque la respuesta dijera otra cosa, la pantalla no las anuncia como riesgo grave.
 */
const CAN_BE_CRITICAL = new Set(["water", "frost", "heat", "supply", "market", "excess_rain"]);
export const isGrave = (key: string, signal: Signal) =>
  CAN_BE_CRITICAL.has(key) && signal.critical === true && signal.level === "unfavorable";

/** Cómo se estimó la cosecha (R5: solo se cita lo que el motor evaluó). En el MVP, por la duración de las etapas (HU-220). */
export function harvestNote(basis: "calendar" | "normal_year" | null | undefined): string {
  return basis === "normal_year"
    ? "Estimación con un año normal, no es pronóstico."
    : "Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico.";
}

/** La señal de agua dice con qué riego se evaluó (HU-092). Nulo se evalúa como sin riego y se dice. */
export function irrigationNote(irrigated: boolean | null | undefined): string {
  if (irrigated === true) return "Evaluada con riego: la falta de lluvia no se cuenta como riesgo.";
  if (irrigated === false) return "Evaluada sin riego.";
  return "Evaluada sin riego, porque no dijo si tiene riego.";
}

/** La señal de oferta dice de qué año y semestre de EVA es el dato y si es preliminar (HU-092). */
export function supplyNote(semester: SupplySemester | null | undefined): string {
  if (!semester) return "Sin dato de EVA para el semestre en que cae la siembra.";
  return `Dato de EVA de ${semester.year}, semestre ${semester.semester}${semester.preliminary ? ", preliminar" : ""}.`;
}

const INDICATOR_NAME: Record<string, string> = {
  precip_mm: "Lluvia en la ventana",
  soil_wetness_root: "Humedad del suelo en la raíz",
  sm_rootzone_m3_m3: "Humedad del suelo en la raíz",
  planted_change_pct: "Cambio del área sembrada",
};

/** Sin nombre conocido, el código del indicador: nunca se inventa uno. */
export const indicatorName = (indicator: string) => INDICATOR_NAME[indicator] ?? indicator;

/**
 * Lo que hay que decir de cada producto de la NASA junto a su valor (`docs/fuentes.md`; R8 y R10): POWER es un reanálisis,
 * no una observación directa, y la humedad del suelo es un dato de la zona, con su resolución.
 */
const SOURCE_NOTE: Record<string, string> = {
  nasa_power: "Reanálisis: un modelo con observaciones, no una medición directa de satélite. Dato de la zona, en celdas de unos 50 km.",
  imerg: "Lluvia estimada por satélite. Dato de la zona, en celdas de unos 10 km.",
  smap: "Satélite. Dato de la zona, en celdas de 9 km.",
};
export const sourceNote = (sourceId: string) => SOURCE_NOTE[sourceId] ?? null;

/** El nombre de los productos de la NASA, de EVA y de SoilGrids como los nombra `docs/fuentes.md`, para cuando su fila aún no está publicada. */
const PRODUCT_NAME: Record<string, string> = {
  nasa_power: "NASA POWER",
  imerg: "GPM IMERG (NASA y JAXA)",
  smap: "SMAP (NASA)",
  nasadem: "NASADEM (NASA)",
  eva: "EVA (UPRA)",
  soilgrids: "SoilGrids (ISRIC)",
};

/**
 * El nombre y la institución de una fuente, de `GET /version` (la tabla `sources`, R8). Si su fila todavía no está
 * publicada, el nombre del producto de `docs/fuentes.md`; si tampoco, el código: nunca se inventa un nombre.
 */
export function sourceName(sourceId: string, version: Version | undefined): string {
  const row = version?.sources.find((s) => s.source_id === sourceId) as { name?: string; institution?: string } | undefined;
  if (!row?.name) return PRODUCT_NAME[sourceId] ?? sourceId;
  return row.institution ? `${row.name} (${row.institution})` : row.name;
}

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

/** «410 mm», «35 %», «0,61 fracción». Sin valor: «Sin dato» (R1). */
export function formatValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return "Sin dato";
  return `${NUMBER.format(value)} ${unit}`.trim();
}

/** «pH estimado de 5,2 a 5,8» con el rango p05–p95 (R10). Sin rango, nada: no se inventa. */
export function phRange(soil: MunicipalitySoil | undefined): string | null {
  const ph = soil?.ph;
  if (!ph || ph.p05 === null || ph.p95 === null) return null;
  const middle = ph.value === null ? "" : ` (valor central ${NUMBER.format(ph.value)})`;
  return `pH estimado de ${NUMBER.format(ph.p05)} a ${NUMBER.format(ph.p95)}${middle}`;
}

export const SOIL_ESTIMATE = "Estimación de un mapa global de 250 m. Un análisis de suelo de su lote es más preciso.";

/** El suelo estimado del municipio (`GET /catalogs/municipalities/{id}/soil`), para el rango de la señal de suelo. */
export function useMunicipalitySoil(municipalityId: string | null | undefined) {
  return useQuery({
    queryKey: ["catalogs", "soil", municipalityId],
    queryFn: () => api<MunicipalitySoil>(`/catalogs/municipalities/${municipalityId}/soil`),
    enabled: Boolean(municipalityId),
    staleTime: Infinity,
    retry: false,
  });
}
