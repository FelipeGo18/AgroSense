import { SoilFacts, type SoilProperties } from "@/components/soil/SoilFacts";
import { useMunicipalitySoil } from "@/features/diagnosis/signals";
import { useLot } from "@/features/farm/lots";

export interface SoilContext {
  municipalityId: string;
  lotId?: string | null;
}

/** El detalle del lote publica las propiedades planas de grid_cells, no SoilRange. */
export function lotSoilProperties(soil: Record<string, unknown>): SoilProperties {
  const number = (key: string) => (typeof soil[key] === "number" && Number.isFinite(soil[key]) ? (soil[key] as number) : null);
  return {
    ph: { value: number("ph"), p05: number("ph_p05"), p95: number("ph_p95") },
    soc_g_kg: { value: number("soc_g_kg"), p05: number("soc_p05"), p95: number("soc_p95") },
    texture_class: typeof soil.texture_class === "string" ? soil.texture_class : null,
    quality: soil.quality === "ok" ? "ok" : "partial",
  };
}

/** Sin suelo del polígono no se sustituye por el municipal (R1). Las consultas comparten la caché. */
export function SoilDetails({ municipalityId, lotId, open = false }: SoilContext & { open?: boolean }) {
  const lot = useLot(lotId ?? "");
  const municipal = useMunicipalitySoil(lotId ? null : municipalityId);
  const query = lotId ? lot : municipal;
  const raw = lot.data?.soil;
  const soil = lotId ? (raw ? lotSoilProperties(raw) : undefined) : municipal.data;
  const place = lotId && raw?.basis === "lot" ? "su lote dibujado" : "su municipio";
  return (
    <details open={open} className="relative min-w-0 text-[15px]">
      <summary className="flex min-h-11 cursor-pointer items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
        Ver el suelo usado y qué significa
      </summary>
      <div className="flex min-w-0 flex-col gap-3 pt-2">
        {query.isPending ? (
          <p role="status">Cargando los datos del suelo…</p>
        ) : query.isError ? (
          <>
            <p role="alert">No se pudieron cargar los datos del suelo.</p>
            <button type="button" className="min-h-11 self-start font-bold underline" onClick={() => void query.refetch()}>
              Reintentar
            </button>
          </>
        ) : soil ? (
          <SoilFacts soil={soil} place={place} />
        ) : (
          <p>Sin datos del suelo de {lotId ? "su lote" : "su municipio"}. Para conocer el suelo de su lote, haga un análisis de suelo.</p>
        )}
      </div>
    </details>
  );
}
