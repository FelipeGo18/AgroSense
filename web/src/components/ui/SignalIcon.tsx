import { pts, tone, type Pt } from "./Plate";

/** Las seis señales de una ventana de siembra, con sus nombres del contrato (specs/01-reglas.md). */
export type SignalKey = "water" | "frost" | "heat" | "soil" | "supply" | "market";

const around = (cx: number, cy: number, r: number, angle: number): Pt => [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];

// Cristal de hielo: seis puntas, cada una con su cara de luz y su cara de sombra.
const FROST = Array.from({ length: 6 }, (_, i) => {
  const a = ((60 * i - 90) * Math.PI) / 180;
  const tip = around(22, 22, 20, a);
  return { lit: [[22, 22], around(22, 22, 7, a - 0.5), tip] as Pt[], shaded: [[22, 22], tip, around(22, 22, 7, a + 0.5)] as Pt[] };
});

// Sol: ocho rayos alrededor de un bloque biselado.
const RAYS = Array.from({ length: 8 }, (_, i) => {
  const a = (Math.PI / 4) * i;
  return [around(22, 22, 12, a - 0.3), around(22, 22, 21, a), around(22, 22, 12, a + 0.3)] as Pt[];
});

/** Ícono low-poly de 44 × 44 de una señal. Misma geometría que design/pantallas/senales.py. */
export function SignalIcon({ signal, className = "" }: { signal: SignalKey; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 44 46" className={`size-11 shrink-0 ${className}`}>
      {signal === "water" && (
        <>
          <polygon points="2,36 42,36 38,43 6,43" fill="var(--color-paleta-tierra)" />
          <polygon
            points="22,2 34,20 30,32 14,32 10,20"
            fill="var(--color-paleta-cielo)"
            stroke="var(--color-oscuro-cielo)"
            strokeWidth="2"
          />
          <polygon points="22,2 10,20 14,32 22,32" fill={tone("var(--color-paleta-cielo)", 0.18)} />
        </>
      )}
      {signal === "frost" &&
        FROST.map((ray, i) => (
          <g key={i}>
            <polygon points={pts(ray.lit)} fill="var(--color-paleta-niebla)" stroke="var(--color-oscuro-cielo)" strokeWidth="1.5" />
            <polygon points={pts(ray.shaded)} fill={tone("var(--color-paleta-niebla)", -0.12)} />
          </g>
        ))}
      {signal === "heat" && (
        <>
          {RAYS.map((ray, i) => (
            <polygon key={i} points={pts(ray)} fill="var(--color-paleta-calabaza)" />
          ))}
          <polygon
            points="17,11 27,11 33,17 33,27 27,33 17,33 11,27 11,17"
            fill="var(--color-paleta-trigo)"
            stroke="var(--color-oscuro-calabaza)"
            strokeWidth="2"
          />
          <polygon points="11,17 17,11 27,11 19,23" fill={tone("var(--color-paleta-trigo)", 0.2)} />
        </>
      )}
      {signal === "soil" && (
        <>
          <polygon points="4,16 40,16 42,24 2,24" fill="var(--color-paleta-brote)" stroke="var(--color-oscuro-brote)" strokeWidth="1.5" />
          <polygon points="2,24 42,24 40,33 4,33" fill="var(--color-paleta-tierra)" />
          <polygon points="4,33 40,33 36,42 8,42" fill="var(--color-oscuro-tierra)" />
          <polygon points="12,27 18,27 16,30" fill={tone("var(--color-paleta-tierra)", 0.25)} />
          <polygon points="28,36 34,36 31,39" fill={tone("var(--color-oscuro-tierra)", 0.3)} />
        </>
      )}
      {signal === "supply" && (
        <>
          <polygon points="2,34 42,34 38,42 6,42" fill="var(--color-paleta-tierra)" />
          <polygon points="21,34 23,34 23,16 21,16" fill="var(--color-oscuro-brote)" />
          <polygon points="22,22 8,12 12,26" fill="var(--color-paleta-brote)" />
          <polygon points="22,18 38,6 34,22" fill={tone("var(--color-paleta-brote)", -0.1)} />
        </>
      )}
      {signal === "market" && (
        <>
          <polygon
            points="14,8 30,8 26,14 38,30 34,42 10,42 6,30 18,14"
            fill="var(--color-paleta-trigo)"
            stroke="var(--color-oscuro-trigo)"
            strokeWidth="2"
          />
          <polygon points="18,14 26,14 22,42 10,42 6,30" fill={tone("var(--color-paleta-trigo)", 0.12)} />
          <polygon points="16,14 28,14 28,17 16,17" fill="var(--color-oscuro-trigo)" />
        </>
      )}
    </svg>
  );
}
