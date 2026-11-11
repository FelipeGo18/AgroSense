import { useState } from "react";
import type { Schemas } from "@/api/client";

type NdviPoint = Schemas["NdviPoint"];

const MONTHS = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
const MONTH_NAMES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];
const NUMBER = new Intl.NumberFormat("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Lienzo en unidades del SVG; se escala al ancho de la tarjeta.
const W = 640;
const H = 220;
const PAD = { left: 40, right: 12, top: 16, bottom: 28 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;
const Y_MIN = 0;
const Y_MAX = 1;

const x = (period: number) => PAD.left + ((period - 1) / 22) * PLOT_W;
const y = (value: number) => PAD.top + (1 - (value - Y_MIN) / (Y_MAX - Y_MIN)) * PLOT_H;
/** El periodo de 16 días que empieza ese día del año, para decir en palabras a qué época corresponde. */
const periodMonth = (period: number) => MONTH_NAMES[Math.min(11, Math.floor(((period - 1) * 16) / 30.5))];

/**
 * Cuándo suele estar verde el campo de la zona (HU-215): el NDVI normal de MODIS por periodos de 16 días, con la ventana
 * del ciclo sombreada. Una sola serie, así que no lleva leyenda: el título la nombra. Un periodo sin dato no se dibuja
 * (la línea se corta, R1). Se puede leer en una tabla, y cada punto dice su valor al pasar o tocar.
 */
export function GreenChart({ points, spans }: { points: NdviPoint[]; spans: [number, number][] }) {
  const [active, setActive] = useState<number | null>(null);
  const valued = points.filter((p): p is NdviPoint & { ndvi_normal: number } => p.ndvi_normal !== null);
  // Tramos sin cortes: un periodo sin dato parte la línea.
  const runs: (NdviPoint & { ndvi_normal: number })[][] = [];
  for (const point of [...valued].sort((a, b) => a.period - b.period)) {
    const last = runs.at(-1);
    if (last && last.at(-1)!.period === point.period - 1) last.push(point);
    else runs.push([point]);
  }
  const shown = active === null ? null : valued.find((p) => p.period === active);
  return (
    <figure className="flex min-w-0 flex-col gap-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Verdor normal de la zona a lo largo del año, de 0 a 1, con la ventana de este ciclo sombreada"
        className="h-auto w-full"
        onMouseLeave={() => setActive(null)}
      >
        {spans.map(([from, to]) => (
          <rect
            key={`${from}-${to}`}
            x={x(from) - PLOT_W / 44}
            y={PAD.top}
            width={x(to) - x(from) + PLOT_W / 22}
            height={PLOT_H}
            fill="var(--color-paleta-calabaza)"
            opacity="0.18"
          />
        ))}
        {[0, 0.5, 1].map((tick) => (
          <g key={tick}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} stroke="var(--color-superficie-borde)" strokeWidth="1" />
            <text x={PAD.left - 6} y={y(tick) + 4} textAnchor="end" fontSize="11" fill="var(--color-texto-secundario)">
              {NUMBER.format(tick)}
            </text>
          </g>
        ))}
        {MONTHS.map((label, i) => (
          <text key={i} x={x(1 + (i * 22) / 11.5)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--color-texto-secundario)">
            {label}
          </text>
        ))}
        {runs.map((run) => (
          <polyline
            key={run[0].period}
            points={run.map((p) => `${x(p.period)},${y(p.ndvi_normal)}`).join(" ")}
            fill="none"
            stroke="var(--color-oscuro-oliva)"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        ))}
        {shown && (
          <>
            <line
              x1={x(shown.period)}
              x2={x(shown.period)}
              y1={PAD.top}
              y2={PAD.top + PLOT_H}
              stroke="var(--color-texto-secundario)"
              strokeWidth="1"
            />
            <circle cx={x(shown.period)} cy={y(shown.ndvi_normal)} r="4" fill="var(--color-oscuro-oliva)" stroke="white" strokeWidth="2" />
          </>
        )}
        {/* Zonas de toque más anchas que la marca: una por periodo. */}
        {valued.map((p) => (
          <rect
            key={p.period}
            x={x(p.period) - PLOT_W / 44}
            y={PAD.top}
            width={PLOT_W / 22}
            height={PLOT_H}
            fill="transparent"
            onMouseEnter={() => setActive(p.period)}
            onClick={() => setActive(p.period)}
          />
        ))}
      </svg>
      <p aria-live="polite" className="min-h-6 text-[15px]">
        {shown
          ? `Periodo ${shown.period} (desde ${periodMonth(shown.period)}): verdor normal ${NUMBER.format(shown.ndvi_normal)}`
          : "Pase o toque la gráfica para ver el valor de cada periodo. La franja es la ventana de este ciclo."}
      </p>
      <details className="text-[15px]">
        <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
          Ver los datos en una tabla
        </summary>
        <table className="mt-2 w-full max-w-[420px] text-left">
          <thead>
            <tr>
              <th className="py-1 pr-4">Periodo de 16 días</th>
              <th className="py-1">Verdor normal (NDVI)</th>
            </tr>
          </thead>
          <tbody>
            {[...points]
              .sort((a, b) => a.period - b.period)
              .map((p) => (
                <tr key={p.period} className="border-t border-superficie-borde">
                  <td className="py-1 pr-4">
                    {p.period} · desde {periodMonth(p.period)}
                  </td>
                  <td className="py-1">{p.ndvi_normal === null ? "Sin dato" : NUMBER.format(p.ndvi_normal)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
