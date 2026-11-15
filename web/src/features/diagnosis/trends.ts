import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";

export type TrendsResponse = Schemas["TrendsResponse"];
export type WaterSeries = Schemas["WaterSeries"];

/**
 * Las series de una ventana para las gráficas (`GET /trends`): la lluvia frente a lo que necesita el cultivo, por año
 * (HU-093), y el verdor normal de la zona (HU-215). Es una lectura: no guarda nada (R9). La usan el diagnóstico y el
 * ciclo de una estrategia; con la misma ventana, se pide una sola vez.
 */
export function useTrends(
  municipalityId: string | null | undefined,
  cropId: string | null | undefined,
  sowingDate: string | null | undefined,
) {
  const query =
    municipalityId && cropId && sowingDate
      ? new URLSearchParams({ municipality_id: municipalityId, crop_id: cropId, sowing_date: sowingDate })
      : null;
  return useQuery({
    queryKey: ["trends", query?.toString()],
    queryFn: () => api<TrendsResponse>(`/trends?${query}`),
    enabled: query !== null,
    retry: false,
    staleTime: Infinity,
  });
}
