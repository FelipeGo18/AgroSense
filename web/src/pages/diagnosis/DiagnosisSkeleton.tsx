import { Card } from "@/components/ui/Card";
import { Mascot } from "@/components/mascot/Mascot";

/** Las 6 señales que el diagnóstico calculará (identificadores estables para keys de React). */
const SKELETON_SIGNALS = ["water", "frost", "heat", "soil", "supply", "market"] as const;

export interface DiagnosisSkeletonProps {
  /** Resumen de lo que se calcula (ej: "Papa · siembra 1 mar 2027 · Samacá"). */
  querySummary?: string;
  className?: string;
}

/**
 * Esqueleto de carga del diagnóstico (HU-094; W6).
 * Muestra la silueta de lo que viene sin inventar datos (R5).
 * Sigue el diseño oficial de `design/pantallas/estados_resultado.py:loading`.
 */
export function DiagnosisSkeleton({ querySummary, className = "" }: Readonly<DiagnosisSkeletonProps>) {
  return (
    <Card className={className} bodyClassName="gap-5">
      <div role="status" aria-busy="true" aria-live="polite" className="flex min-w-0 flex-col gap-4">
        <span className="sr-only">Calculando su diagnóstico. Por favor espere.</span>
        {/* Encabezado: Título, resumen de consulta y mascota volando */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="font-titulos text-[20px] leading-tight font-semibold text-texto-principal sm:text-[22px]">
              Calculando su diagnóstico…
            </h3>
            <p className="text-[15px] text-texto-secundario">{querySummary ?? "Calculando su ventana de siembra…"}</p>
          </div>
          <Mascot mood="flying" size={82} decorative className="-mt-2 -mr-1 shrink-0" />
        </div>
        {/* Silueta de la acción principal y la luz del semáforo */}
        <div className="flex flex-wrap items-center gap-4 pt-1">
          {/* Bloque del semáforo */}
          <div className="h-11 w-36 rounded-md bg-paleta-niebla animated:animate-pulse" />
          {/* Líneas de texto del semáforo */}
          <div className="flex flex-col gap-2">
            <div className="h-4 w-44 max-w-[70vw] rounded bg-paleta-niebla animated:animate-pulse" />
            <div className="h-3 w-28 max-w-[50vw] rounded bg-paleta-niebla animated:animate-pulse" />
          </div>
        </div>
        {/* Rejilla de las 6 señales: 2 columnas en celular, 3 en tablet, 6 en escritorio */}
        <div className="mt-2 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
          {SKELETON_SIGNALS.map((signalId) => (
            <div key={signalId} className="bg-surface flex min-w-0 flex-col gap-2 rounded-lg border border-superficie-borde/60 p-3">
              {/* Título de la señal */}
              <div className="h-3 w-1/2 rounded bg-paleta-niebla animated:animate-pulse" />
              {/* Razón / explicación */}
              <div className="h-2.5 w-full rounded bg-paleta-niebla animated:animate-pulse" />
              <div className="h-2.5 w-3/4 rounded bg-paleta-niebla animated:animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
