import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export type Version = components["schemas"]["Version"];

/**
 * Qué versiones y qué criterio usa AgroSense (GET /version). De aquí salen los pesos por defecto de las señales: el
 * «criterio de AgroSense» que se muestra junto a las prioridades de quien consulta. Cambia muy poco: se pide una vez.
 */
export function useVersion() {
  return useQuery({ queryKey: ["version"], queryFn: () => api<Version>("/version"), staleTime: Infinity, retry: false });
}
