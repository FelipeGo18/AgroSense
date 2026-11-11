import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export type Version = components["schemas"]["Version"];

/**
 * Qué versiones y qué criterio usa AgroSense (GET /version). De aquí salen los pesos por defecto de las señales: el
 * «criterio de AgroSense» que se muestra junto a las prioridades de quien consulta. Cambia muy poco: se pide una vez.
 */
export function useVersion() {
  // Si falla, no se vuelve a pedir sola cada vez que un componente se monta: con la API caída serían decenas de
  // peticiones. Se reintenta a mano («Volver a intentar» de Mi cuenta llama a `refetch`).
  return useQuery({
    queryKey: ["version"],
    queryFn: () => api<Version>("/version"),
    staleTime: Infinity,
    retry: false,
    retryOnMount: false,
  });
}
