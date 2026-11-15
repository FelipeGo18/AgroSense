import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";

export type Crop = Schemas["CropItem"];
export type Season = Schemas["SeasonOut"];

/**
 * Una siembra que llega armada desde el primer ciclo de una estrategia (HU-215): su cultivo, su fecha, el terreno del
 * que viene, su área y el diagnóstico que vio la persona. Se guarda con la siembra solo si no cambia el cultivo ni la
 * fecha (HU-165): con otro cultivo u otra fecha, ese diagnóstico ya no es el de lo que sembró.
 */
export interface SowPlan {
  crop_id: string;
  sowing_date: string;
  follows_season_ids: string[];
  area_ha: number;
  diagnosis: Pick<
    SeasonCreate,
    | "diagnosis_light"
    | "diagnosis_light_default"
    | "diagnosis_action"
    | "diagnosis_weights"
    | "diagnosis_irrigated"
    | "dataset_version"
    | "rules_version"
  >;
}
export type SeasonCreate = Schemas["SeasonCreate"];
export type SeasonPatch = Schemas["SeasonPatch"];

/** Los cultivos del catálogo (GET /catalogs/crops). Cambian solo con un dataset nuevo: se piden una vez. */
export function useCrops() {
  return useQuery({ queryKey: ["catalogs", "crops"], queryFn: () => api<Crop[]>("/catalogs/crops"), staleTime: Infinity, retry: false });
}

export function cropNames(crops: Crop[] | undefined) {
  return new Map((crops ?? []).map((crop) => [crop.crop_id, crop.name_es]));
}

function historyQuery(lotId: string) {
  return {
    queryKey: ["lots", lotId, "seasons"],
    queryFn: () => api<Season[]>(`/lots/${lotId}/seasons`),
    retry: false,
    enabled: Boolean(lotId),
  } as const;
}

/**
 * El historial del lote (GET /lots/{id}/seasons), de la siembra más reciente a la más antigua, sin lo borrado. La API
 * trae también las siembras borradas hace menos de 30 días (HU-204): esas son `useDeletedSeasons`.
 */
export function useSeasons(lotId: string) {
  return useQuery({ ...historyQuery(lotId), select: (seasons: Season[]) => seasons.filter((season) => !season.deleted_at) });
}

/** Las siembras del lote borradas hace menos de 30 días, que se pueden restaurar (HU-204). Comparte la petición. */
export function useDeletedSeasons(lotId: string) {
  return useQuery({ ...historyQuery(lotId), select: (seasons: Season[]) => seasons.filter((season) => season.deleted_at) });
}

/** Tras registrar, cosechar, corregir o borrar cambian el lote, su historial y la lista de Mi finca. */
function useRefresh(lotId: string) {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: ["lots"] });
    void client.invalidateQueries({ queryKey: ["lots", lotId] });
  };
}

export function useCreateSeason(lotId: string) {
  const refresh = useRefresh(lotId);
  return useMutation({ mutationFn: (body: SeasonCreate) => api<Season>(`/lots/${lotId}/seasons`, { body }), onSuccess: refresh });
}

export function useUpdateSeason(lotId: string, seasonId: string) {
  const refresh = useRefresh(lotId);
  return useMutation({
    mutationFn: (body: SeasonPatch) => api<Season>(`/seasons/${seasonId}`, { method: "PATCH", body }),
    onSuccess: refresh,
  });
}

export function useDeleteSeason(lotId: string, seasonId: string) {
  const refresh = useRefresh(lotId);
  return useMutation({ mutationFn: () => api<void>(`/seasons/${seasonId}`, { method: "DELETE" }), onSuccess: refresh });
}

/** Restaura una siembra borrada hace menos de 30 días (HU-204). Si ya no cabe en el lote, la API responde 422. */
export function useRestoreSeason(lotId: string, seasonId: string) {
  const refresh = useRefresh(lotId);
  return useMutation({ mutationFn: () => api<Season>(`/seasons/${seasonId}/restore`, { method: "POST" }), onSuccess: refresh });
}

/** Las etapas son las de FAO-56 (catalog/crops.yaml): se nombran como las dice el manual, sin inventar otras. */
export const STAGE_NAMES: Record<string, string> = {
  initial: "Etapa inicial",
  development: "Desarrollo",
  mid: "Etapa media",
  late: "Etapa final",
};
export const STAGE_ORDER = ["initial", "development", "mid", "late"];

const DATE = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const SHORT = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** «2 de agosto de 2026», a partir de una fecha ISO (sin hora). */
export const formatDate = (iso: string) => DATE.format(new Date(`${iso}T00:00:00Z`));
export const formatShortDate = (iso: string) => SHORT.format(new Date(`${iso}T00:00:00Z`));

const LOCAL_DATE = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });

/** «14 de diciembre de 2026», a partir de una fecha con hora (`restorable_until`), en la hora del navegador. */
export const formatLocalDate = (iso: string) => LOCAL_DATE.format(new Date(iso));

/** Lo borrado se puede restaurar durante 30 días (HU-204; contrato, «Base de datos de cuentas»). */
export const RESTORE_DAYS = 30;

/** Hasta cuándo se podrá restaurar lo que se borre ahora: la API lo dice exacto en `restorable_until` después de borrar. */
export const restoreDeadline = () => LOCAL_DATE.format(new Date(Date.now() + RESTORE_DAYS * 86_400_000));

/** Hoy en el formato de los campos de fecha (aaaa-mm-dd), en la hora del navegador. */
export function todayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}
