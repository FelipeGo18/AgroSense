import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";

export type ChangesResponse = Schemas["ChangesResponse"];

export function changesLink(municipalityId: string, cropId: string, irrigated?: boolean | null) {
  const params = new URLSearchParams({ municipio: municipalityId, cultivo: cropId });
  if (irrigated != null) params.set("riego", irrigated ? "si" : "no");
  return `${PATHS.changes}?${params}`;
}

export function useChanges(municipalityId: string | null, cropId: string | null, irrigated: boolean | null) {
  const params = new URLSearchParams();

  if (municipalityId) params.set("municipality_id", municipalityId);
  if (cropId) params.set("crop_id", cropId);
  if (irrigated !== null) params.set("irrigated", String(irrigated));

  return useQuery({
    queryKey: ["changes", municipalityId, cropId, irrigated],
    queryFn: () => api<ChangesResponse>(`/changes?${params}`),
    enabled: Boolean(municipalityId && cropId),
    retry: false,
    staleTime: Infinity,
  });
}
