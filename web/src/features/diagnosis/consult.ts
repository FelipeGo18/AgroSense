import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import { REGION_TIME_ZONE } from "@/app/config";
import type { Crop } from "@/features/farm/seasons";
import type { LotListItem, Municipality } from "@/features/farm/lots";

export type DiagnosisRequest = Schemas["DiagnosisRequest"];
export type DiagnosisResponse = Schemas["DiagnosisResponse"];

/**
 * La consulta del diagnóstico de una ventana (HU-091): municipio, cultivo, cuándo sembrar y riego. Vive en la dirección
 * (`/diagnostico?municipio=15646&cultivo=papa&siembra=2026-12&riego=no`): se puede compartir, volver atrás y, desde otras
 * pantallas, abrir una consulta ya armada. Con `lote=`, el municipio y el riego salen del lote.
 */
export type Irrigation = "si" | "no" | "nose";

export interface ConsultForm {
  municipalityId: string;
  cropId: string;
  /** Mes de siembra, `aaaa-mm`. La web envía su día 1 (`specs/02-contratos.md`, «Fechas»). */
  month: string;
  irrigation: Irrigation | "";
  /** Con un lote propio (con sesión): su municipio y su riego mandan. */
  lotId: string;
}

export type ConsultField = "municipality" | "crop" | "month" | "irrigation";
export type ConsultErrors = Partial<Record<ConsultField, string>>;

export const EMPTY_FORM: ConsultForm = { municipalityId: "", cropId: "", month: "", irrigation: "", lotId: "" };

export const IRRIGATION_CHOICES: { value: Irrigation; label: string }[] = [
  { value: "si", label: "Sí" },
  { value: "no", label: "No" },
  { value: "nose", label: "No sé" },
];

const IRRIGATED: Record<Irrigation, boolean | null> = { si: true, no: false, nose: null };

export const ERRORS: Record<ConsultField, string> = {
  municipality: "Elija su municipio de la lista.",
  crop: "Elija un cultivo de la lista.",
  month: "Elija el mes en que quiere sembrar.",
  irrigation: "Diga si tiene riego. Si no sabe, elija «No sé».",
};

const MONTH = new Intl.DateTimeFormat("es-CO", { month: "long", year: "numeric", timeZone: "UTC" });
// El año y el mes de un instante en la hora de la región, no en la del navegador.
const REGION_MONTH = new Intl.DateTimeFormat("en-US", { timeZone: REGION_TIME_ZONE, year: "numeric", month: "numeric" });
const pad = (n: number) => String(n).padStart(2, "0");

/** El año y el mes (0 a 11) en curso en la región. */
export function regionMonth(now: Date): [number, number] {
  const parts = REGION_MONTH.formatToParts(now);
  const part = (type: "year" | "month") => Number(parts.find((p) => p.type === type)?.value);
  return [part("year"), part("month") - 1];
}

/**
 * Los doce meses entre los que se elige cuándo sembrar: el mes en curso y los once siguientes. El mes en curso vale
 * aunque su día 1 ya haya pasado, y se cuenta en la hora de la región, como en la API (`specs/02-contratos.md`,
 * «Fechas»): así la web nunca ofrece un mes que la API rechaza.
 */
export function sowingMonths(now: Date = new Date()): { value: string; label: string }[] {
  const [year, month] = regionMonth(now);
  return Array.from({ length: 12 }, (_, i) => {
    const date = new Date(Date.UTC(year, month + i, 1));
    const value = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}`;
    // Solo el mes: «septiembre de 2027» cabe en el selector a 320 px. Que el primero es el mes en curso lo dice la ayuda.
    return { value, label: MONTH.format(date) };
  });
}

/** El día 1 del mes elegido: la fecha de siembra que se envía. */
export const sowingDate = (month: string) => `${month}-01`;

/** «diciembre de 2026», para decir el mes elegido. */
export const monthName = (month: string) => MONTH.format(new Date(`${month}-01T00:00:00Z`));

export function fromParams(params: URLSearchParams): ConsultForm {
  const irrigation = params.get("riego") ?? "";
  return {
    municipalityId: params.get("municipio") ?? "",
    cropId: params.get("cultivo") ?? "",
    month: params.get("siembra") ?? "",
    irrigation: irrigation === "si" || irrigation === "no" || irrigation === "nose" ? irrigation : "",
    lotId: params.get("lote") ?? "",
  };
}

/** La consulta en la dirección. Con lote, el municipio y el riego no van: salen del lote. */
export function toParams(form: ConsultForm): URLSearchParams {
  const params = new URLSearchParams();
  if (form.lotId) params.set("lote", form.lotId);
  else params.set("municipio", form.municipalityId);
  params.set("cultivo", form.cropId);
  params.set("siembra", form.month);
  if (!form.lotId) params.set("riego", form.irrigation);
  return params;
}

/** Si la dirección trae alguna consulta (aunque esté incompleta): entonces se valida de una vez. */
export const hasConsult = (params: URLSearchParams) => ["municipio", "cultivo", "siembra", "riego", "lote"].some((key) => params.has(key));

export interface Catalogs {
  municipalities: Municipality[];
  crops: Crop[];
  months: string[];
  lot?: LotListItem;
}

/** Solo opciones del catálogo (W1): un código que no está en la lista no es un valor. Para el diagnóstico, solo `kind = crop`. */
export function validate(form: ConsultForm, { municipalities, crops, months, lot }: Catalogs): ConsultErrors {
  const errors: ConsultErrors = {};
  if (!lot && !municipalities.some((m) => m.municipality_id === form.municipalityId)) errors.municipality = ERRORS.municipality;
  if (!crops.some((c) => c.crop_id === form.cropId && c.kind === "crop")) errors.crop = ERRORS.crop;
  if (!months.includes(form.month)) errors.month = ERRORS.month;
  if (!lot && !form.irrigation) errors.irrigation = ERRORS.irrigation;
  return errors;
}

/** El cuerpo de `POST /diagnostics`. Con lote: su municipio, su riego y `lot_id`. Las prioridades llegan con HU-202. */
export function toRequest(form: ConsultForm, lot?: LotListItem): DiagnosisRequest {
  if (lot) {
    return {
      municipality_id: lot.municipality_id,
      crop_id: form.cropId,
      sowing_date: sowingDate(form.month),
      irrigated: lot.irrigated,
      lot_id: lot.lot_id,
    };
  }
  return {
    municipality_id: form.municipalityId,
    crop_id: form.cropId,
    sowing_date: sowingDate(form.month),
    irrigated: IRRIGATED[form.irrigation as Irrigation],
    lot_id: null,
  };
}

/**
 * El diagnóstico de la consulta. Calcular no es guardar (R9): la API no guarda nada, así que se pide como una lectura y
 * se recuerda mientras dure la visita. Sin consulta válida no se pide.
 */
export function useDiagnosis(request: DiagnosisRequest | null) {
  return useQuery({
    queryKey: ["diagnostics", request],
    queryFn: () => api<DiagnosisResponse>("/diagnostics", { body: request }),
    enabled: request !== null,
    retry: false,
    staleTime: Infinity,
  });
}
