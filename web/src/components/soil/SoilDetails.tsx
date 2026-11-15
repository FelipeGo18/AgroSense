import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  const lot = useLot(lotId ?? "");
  const municipal = useMunicipalitySoil(lotId ? null : municipalityId);
  const query = lotId ? lot : municipal;
  const raw = lot.data?.soil;
  const soil = lotId ? (raw ? lotSoilProperties(raw) : undefined) : municipal.data;
  const place = lotId && raw?.basis === "lot" ? t("soil.details.plot") : t("soil.details.municipality");
  return (
    <details open={open} className="relative min-w-0 text-[15px]">
      <summary className="flex min-h-11 cursor-pointer items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
        {t("soil.details.open")}
      </summary>
      <div className="flex min-w-0 flex-col gap-3 pt-2">
        {query.isPending ? (
          <p role="status">{t("soil.details.loading")}</p>
        ) : query.isError ? (
          <>
            <p role="alert">{t("soil.details.error")}</p>
            <button type="button" className="min-h-11 self-start font-bold underline" onClick={() => void query.refetch()}>
              {t("common.retry")}
            </button>
          </>
        ) : soil ? (
          <SoilFacts soil={soil} place={place} />
        ) : (
          <p>{t("soil.details.missing", { place: lotId ? t("soil.details.plotShort") : t("soil.details.municipality") })}</p>
        )}
      </div>
    </details>
  );
}
