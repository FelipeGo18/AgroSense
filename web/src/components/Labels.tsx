import type { ReactNode } from "react";
import { Plate, pts, tone, useParentSize } from "./Plate";

/** Silueta de etiqueta colgante de vivero: punta a la izquierda con su ojal. */
function TagShape() {
  const [ref, { w, h }] = useParentSize<SVGSVGElement>();
  const fill = "var(--color-rotulo-ejemplo-fondo)";
  return (
    <svg ref={ref} aria-hidden="true" className="pointer-events-none absolute inset-0 size-full overflow-visible">
      {w > 0 && (
        <>
          <polygon
            points={pts([
              [14, 1],
              [w - 1, 1],
              [w - 1, h - 1],
              [14, h - 1],
              [1, h / 2],
            ])}
            fill={fill}
            stroke="var(--color-oscuro-calabaza)"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <polygon
            points={pts([
              [14, 2],
              [w * 0.45, 2],
              [w * 0.3, h - 2],
              [14, h - 2],
              [2.5, h / 2],
            ])}
            fill={tone(fill, 0.1)}
          />
          <circle cx="16" cy={h / 2} r="4" fill="var(--color-superficie-panel)" stroke="var(--color-oscuro-calabaza)" strokeWidth="2" />
        </>
      )}
    </svg>
  );
}

/** Rótulo obligatorio junto a todo dato ficticio (R5). */
export function ExampleLabel({ children = "datos ficticios" }: { children?: ReactNode }) {
  return (
    <span className="relative inline-flex min-h-10 items-center gap-2 py-1.5 pr-4 pl-8 text-sm text-texto-principal">
      <TagShape />
      <span className="relative font-bold tracking-wide uppercase">Ejemplo</span>
      <span className="relative" aria-hidden="true">
        ·
      </span>
      <span className="relative">{children}</span>
    </span>
  );
}

export const ESTIMATE_TEXT = "Estimación con el clima de la zona. Verifique la humedad del suelo en su lote";

/** Rótulo obligatorio junto a todo resultado de riego (R10). El texto es fijo. */
export function EstimateLabel() {
  return (
    <p className="relative inline-flex min-h-12 items-center gap-3 px-4 py-2 text-sm text-texto-principal">
      <Plate fill="var(--color-rotulo-estimacion-fondo)" stroke="var(--color-oscuro-cielo)" strokeWidth={2} />
      <svg aria-hidden="true" viewBox="0 0 24 28" className="relative h-7 w-6 shrink-0">
        <polygon
          points="12,1 22,17 18,27 6,27 2,17"
          fill="var(--color-paleta-cielo)"
          stroke="var(--color-oscuro-cielo)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <polygon points="12,1 22,17 18,27 12,27" fill="var(--color-oscuro-cielo)" />
      </svg>
      <span className="relative">{ESTIMATE_TEXT}</span>
    </p>
  );
}
