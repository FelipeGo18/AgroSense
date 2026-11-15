import { GuideNote } from "./GuideNote";
import type { StopId } from "./content";

/** Encabezado de una parada: a la izquierda el título; a la derecha, la mascota con lo que dice. */
export function SectionHeader({ stop, title, children }: { stop: Exclude<StopId, "inicio">; title: string; children: string }) {
  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
      <div data-reveal="left">
        <h2 id={`${stop}-titulo`} tabIndex={-1} data-section-title className="text-[clamp(1.875rem,3.2vw,2.75rem)] outline-none">
          {title}
        </h2>
        <p className="mt-3 max-w-[46rem] text-[clamp(1rem,1.4vw,1.25rem)]">{children}</p>
      </div>
      <GuideNote stop={stop} className="self-end lg:self-auto" />
    </div>
  );
}

/** Borde de nubes facetadas con el que una sección sube sobre la portada: tapa el paso del espacio al contenido. */
export function CloudEdge({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 1440 200"
      preserveAspectRatio="none"
      className={`pointer-events-none absolute inset-x-0 bottom-full -mb-px block h-[16vh] w-full ${className}`}
    >
      <polygon
        points="0,200 0,80 140,40 280,90 420,10 560,70 700,0 840,60 980,5 1120,75 1260,30 1440,70 1440,200"
        fill="currentColor"
        opacity={0.55}
      />
      <polygon
        points="0,200 0,120 100,90 220,130 340,60 470,110 600,40 730,95 860,20 990,100 1120,55 1250,120 1360,80 1440,110 1440,200"
        fill="currentColor"
      />
    </svg>
  );
}
