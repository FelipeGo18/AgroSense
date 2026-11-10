import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";
import type { Boundary } from "./geo";

export type Municipality = Schemas["MunicipalityItem"];
export type LotListItem = Schemas["LotListItem"];
export type LotDetail = Schemas["LotDetail"];
export type Lot = Schemas["LotOut"];
export type LotCreate = Schemas["LotCreate"];
export type LotPatch = Schemas["LotPatch"];

const LOTS = ["lots"] as const;
const lotKey = (lotId: string) => ["lots", lotId] as const;

/** Los municipios de la región (GET /catalogs/municipalities). Cambian solo con un dataset nuevo: se piden una vez. */
export function useMunicipalities() {
  return useQuery({
    queryKey: ["catalogs", "municipalities"],
    queryFn: () => api<Municipality[]>("/catalogs/municipalities"),
    staleTime: Infinity,
    retry: false,
  });
}

export interface BoundaryFeature {
  type: "Feature";
  properties: { municipality_id: string; name: string; source_id: string };
  geometry: Boundary;
}

/** El límite del municipio (GET /catalogs/municipalities/{id}/boundary): para centrar el mapa y validar el dibujo. */
export function useBoundary(municipalityId: string | null | undefined) {
  return useQuery({
    queryKey: ["catalogs", "boundary", municipalityId],
    queryFn: () => api<BoundaryFeature>(`/catalogs/municipalities/${municipalityId}/boundary`),
    enabled: Boolean(municipalityId),
    staleTime: Infinity,
    retry: false,
  });
}

/** Por código, para escribir el nombre del municipio de cada lote. */
export function byId(municipalities: Municipality[] | undefined) {
  return new Map((municipalities ?? []).map((m) => [m.municipality_id, m]));
}

/** Los lotes de quien tiene la sesión. Con `enabled` en falso (sin sesión) no se piden: la API respondería 401. */
export function useLots(enabled = true) {
  return useQuery({ queryKey: LOTS, queryFn: () => api<LotListItem[]>("/lots"), retry: false, enabled });
}

export function useLot(lotId: string) {
  return useQuery({ queryKey: lotKey(lotId), queryFn: () => api<LotDetail>(`/lots/${lotId}`), retry: false });
}

export function useCreateLot() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: LotCreate) => api<Lot>("/lots", { body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: LOTS }),
  });
}

export function useUpdateLot(lotId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: LotPatch) => api<Lot>(`/lots/${lotId}`, { method: "PATCH", body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: LOTS }),
  });
}

export function useDeleteLot(lotId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>(`/lots/${lotId}`, { method: "DELETE" }),
    onSuccess: () => {
      client.removeQueries({ queryKey: lotKey(lotId) });
      void client.invalidateQueries({ queryKey: LOTS });
    },
  });
}

const HA = new Intl.NumberFormat("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** «2,50 ha». */
export const formatHa = (value: number) => `${HA.format(value)} ha`;

/**
 * Lo que se escribe en «Área del lote (ha)»: acepta coma o punto decimal («2,5» o «2.5»). Nulo si no es un número
 * mayor que cero o si pasa del tope de la API.
 */
export function parseHa(text: string): number | null {
  const clean = text.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(clean)) return null;
  const value = Number(clean);
  return value > 0 && value <= 100_000 ? value : null;
}

/** Lo que se escribe en el campo, a partir del área guardada: «2,5». */
export const haText = (value: number) => String(value).replace(".", ",");
