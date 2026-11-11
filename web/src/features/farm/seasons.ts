import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";

export type Crop = Schemas["CropItem"];
export type Season = Schemas["SeasonOut"];
export type SeasonCreate = Schemas["SeasonCreate"];
export type SeasonPatch = Schemas["SeasonPatch"];

/** Los cultivos del catálogo (GET /catalogs/crops). Cambian solo con un dataset nuevo: se piden una vez. */
export function useCrops() {
  return useQuery({ queryKey: ["catalogs", "crops"], queryFn: () => api<Crop[]>("/catalogs/crops"), staleTime: Infinity, retry: false });
}

export function cropNames(crops: Crop[] | undefined) {
  return new Map((crops ?? []).map((crop) => [crop.crop_id, crop.name_es]));
}

/** El historial del lote (GET /lots/{id}/seasons): de la siembra más reciente a la más antigua. */
export function useSeasons(lotId: string) {
  return useQuery({
    queryKey: ["lots", lotId, "seasons"],
    queryFn: () => api<Season[]>(`/lots/${lotId}/seasons`),
    retry: false,
    enabled: Boolean(lotId),
  });
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

/** Hoy en el formato de los campos de fecha (aaaa-mm-dd), en la hora del navegador. */
export function todayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}
