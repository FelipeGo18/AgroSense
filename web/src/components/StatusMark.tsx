import type { PlateProps } from "./Plate";

/**
 * Silueta + ícono + texto para los estados del semáforo y de las señales (W2: nunca solo color).
 * «No evaluable» y «datos insuficientes» nunca usan rojo ni se parecen a un riesgo (R1).
 */

export type Tone = "green" | "yellow" | "red" | "not_evaluable" | "insufficient_data" | "not_applicable";

type Icon = "octagon" | "triangle" | "square" | "ring" | "question" | "dash";

export const TONE_STYLE: Record<Tone, { plate: PlateProps; ink: string; icon: Icon }> = {
  green: {
    plate: { c: 26, fill: "var(--color-semaforo-verde-fondo)", stroke: "var(--color-semaforo-verde-borde)", faceted: true },
    ink: "text-semaforo-verde-texto",
    icon: "octagon",
  },
  yellow: {
    plate: { c: 10, fill: "var(--color-semaforo-amarillo-fondo)", stroke: "var(--color-semaforo-amarillo-borde)", faceted: true },
    ink: "text-semaforo-amarillo-texto",
    icon: "triangle",
  },
  red: {
    plate: { c: 0, fill: "var(--color-semaforo-rojo-fondo)", stroke: "var(--color-semaforo-rojo-borde)", faceted: true },
    ink: "text-semaforo-rojo-texto",
    icon: "square",
  },
  not_evaluable: {
    plate: { c: 10, fill: "var(--color-semaforo-no-evaluable-fondo)", stroke: "var(--color-semaforo-no-evaluable-borde)", dash: "9 6" },
    ink: "text-semaforo-no-evaluable-texto",
    icon: "ring",
  },
  insufficient_data: {
    plate: { c: 10, fill: "var(--color-semaforo-datos-insuficientes-fondo)", stroke: "var(--color-semaforo-datos-insuficientes-borde)", dash: "3 5" },
    ink: "text-semaforo-datos-insuficientes-texto",
    icon: "question",
  },
  not_applicable: {
    plate: { c: 10, fill: "var(--color-superficie-panel)", stroke: "var(--color-superficie-borde)" },
    ink: "text-texto-secundario",
    icon: "dash",
  },
};

const OCTAGON = "14.14,0 20,5.86 20,14.14 14.14,20 5.86,20 0,14.14 0,5.86 5.86,0";

export function StatusIcon({ icon }: { icon: Icon }) {
  if (icon === "question" || icon === "dash") {
    return (
      <span aria-hidden="true" className="w-5 shrink-0 text-center font-bold">
        {icon === "question" ? "?" : "–"}
      </span>
    );
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="size-5 shrink-0">
      {icon === "octagon" && <polygon points={OCTAGON} fill="currentColor" />}
      {icon === "triangle" && <polygon points="10,0 20,18 0,18" fill="currentColor" />}
      {icon === "square" && <polygon points="2,2 18,2 18,18 2,18" fill="currentColor" />}
      {icon === "ring" && (
        <polygon points="13.2,2.2 17.8,6.8 17.8,13.2 13.2,17.8 6.8,17.8 2.2,13.2 2.2,6.8 6.8,2.2" fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="4 3" />
      )}
    </svg>
  );
}
