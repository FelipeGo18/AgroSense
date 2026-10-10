import { useLayoutEffect, useRef, useState } from "react";

/**
 * Geometría del estilo diorama low-poly (HU-153). Es la misma de design/kit/build_kit_svg.py:
 * esquinas biseladas, cara triangulada con luz desde la izquierda y canto inferior.
 * Las medidas (bisel, canto, facetas, trazos) están documentadas en design/tokens/tokens.json.
 */

export type Pt = [number, number];

export function chamfer(x: number, y: number, w: number, h: number, c: number): Pt[] {
  if (c <= 0) return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
  return [
    [x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c],
    [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c],
  ];
}

export const pts = (points: Pt[]) => points.map(([x, y]) => `${+x.toFixed(2)},${+y.toFixed(2)}`).join(" ");

/** Aclara (f > 0) u oscurece (f < 0) un color CSS, incluidas las variables de los tokens. */
export function tone(color: string, f: number) {
  if (f === 0) return color;
  return `color-mix(in srgb, ${color}, ${f > 0 ? "white" : "black"} ${Math.abs(f) * 100}%)`;
}

const TONES = [0.06, -0.015, 0.035, -0.05, 0.015, -0.03, 0.045, -0.065, 0];

export function facets(x: number, y: number, w: number, h: number, c: number, base: string) {
  const out: { points: Pt[]; fill: string }[] = [];
  if (c > 0) {
    out.push({ points: [[x + c, y], [x + c, y + h], [x, y + h - c], [x, y + c]], fill: tone(base, 0.12) });
    out.push({ points: [[x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h]], fill: tone(base, -0.12) });
  }
  const x0 = x + Math.max(c, 0);
  const span = w - 2 * Math.max(c, 0);
  const top = [0, 0.22, 0.47, 0.71, 1].map((t) => x0 + span * t);
  const bot = [0, 0.11, 0.35, 0.6, 0.86, 1].map((t) => x0 + span * t);
  const tris: Pt[][] = [];
  for (let i = 0; i < top.length - 1; i++) {
    tris.push([[top[i], y], [top[i + 1], y], [bot[i + 1], y + h]]);
    tris.push([[top[i], y], [bot[i + 1], y + h], [bot[i], y + h]]);
  }
  tris.push([[top[top.length - 1], y], [bot[bot.length - 1], y + h], [bot[bot.length - 2], y + h]]);
  tris.forEach((points, i) => out.push({ points, fill: tone(base, TONES[i % TONES.length]) }));
  return out;
}

/** Tamaño en píxeles del elemento que contiene al SVG, para dibujar biseles exactos. */
export function useParentSize<T extends Element>() {
  const ref = useRef<T>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const parent = ref.current?.parentElement;
    if (!parent) return;
    const measure = () => setSize({ w: parent.clientWidth, h: parent.clientHeight });
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(parent);
    return () => observer.disconnect();
  }, []);
  return [ref, size] as const;
}

export interface PlateProps {
  /** Tamaño del bisel en píxeles; 0 da esquinas rectas. */
  c?: number;
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  dash?: string;
  faceted?: boolean;
  /** Canto inferior del bloque, en píxeles. */
  depth?: number;
  side?: string;
  /** Espacio que la cara deja libre arriba y abajo dentro del elemento. */
  top?: number;
  bottom?: number;
  /** Contorno de foco: «focus» lo muestra con :focus-visible del padre; true, siempre. */
  ring?: boolean | "focus";
}

/** Fondo vectorial de una pieza. Va como primer hijo de un elemento con `position: relative`. */
export function Plate({
  c = 10,
  fill,
  stroke,
  strokeWidth = 3,
  dash,
  faceted = false,
  depth = 0,
  side,
  top = 0,
  bottom = 0,
  ring = false,
}: PlateProps) {
  const [ref, { w, h }] = useParentSize<SVGSVGElement>();
  const faceH = h - top - bottom;
  const inset = stroke ? strokeWidth / 2 : 0;
  const face = chamfer(inset, top + inset, w - 2 * inset, faceH - 2 * inset, c);
  return (
    <svg ref={ref} aria-hidden="true" className="plate pointer-events-none absolute inset-0 size-full overflow-visible">
      {w > 0 && faceH > 0 && (
        <>
          {ring && (
            <polygon
              className={ring === "focus" ? "plate-ring" : undefined}
              points={pts(chamfer(-4.5, -4.5, w + 9, h + 9, c + 4))}
              fill="none"
              stroke="var(--color-accion-foco)"
              strokeWidth={3}
              strokeLinejoin="round"
            />
          )}
          {depth > 0 && side && <polygon points={pts(chamfer(0, top + depth, w, faceH, c))} fill={side} />}
          <g className="plate-face">
            <polygon points={pts(face)} fill={fill} />
            {faceted &&
              facets(inset, top + inset, w - 2 * inset, faceH - 2 * inset, c, fill).map((f, i) => (
                <polygon key={i} points={pts(f.points)} fill={f.fill} />
              ))}
            {stroke && (
              <polygon
                points={pts(face)}
                fill="none"
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeDasharray={dash}
                strokeLinejoin="round"
              />
            )}
          </g>
        </>
      )}
    </svg>
  );
}

/** Estaca de madera que clava un letrero en la parcela. */
export function Stake({ ghost = false, className = "" }: { ghost?: boolean; className?: string }) {
  return (
    <svg aria-hidden="true" width="16" height="34" viewBox="0 0 16 34" className={`shrink-0 ${className}`}>
      {ghost ? (
        <polygon points="1.5,0 14.5,0 14.5,25 8,32 1.5,25" fill="none" stroke="var(--color-oscuro-cielo)" strokeWidth="2.5" strokeDasharray="6 4" />
      ) : (
        <>
          <polygon points="0,0 16,0 16,26 8,34 0,26" fill="var(--color-estaca-luz)" />
          <polygon points="8,0 16,0 16,26 8,34" fill="var(--color-estaca-sombra)" />
        </>
      )}
    </svg>
  );
}
