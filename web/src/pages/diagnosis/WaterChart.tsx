import { useState } from "react";
import { useWidth } from "@/hooks/useWidth";
import { sourceName, sourceNote } from "@/features/diagnosis/signals";
import type { WaterSeries } from "@/features/diagnosis/trends";
import type { Version } from "@/features/version";

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const MONTH = new Intl.DateTimeFormat("es-CO", { month: "short", timeZone: "UTC" });
const monthOf = (iso: string) => MONTH.format(new Date(`${iso}T00:00:00Z`)).replace(".", "");

// Se dibuja en píxeles, al ancho de la tarjeta (`useWidth`): el texto mide lo mismo en el celular y en el escritorio.
const H = 200;
const PAD = { left: 40, right: 8, top: 12, bottom: 24 };
const PLOT_H = H - PAD.top - PAD.bottom;

type Point = WaterSeries["points"][number];
const shortYear = (p: Point) => p.precip_mm !== null && p.need_mm !== null && p.precip_mm < p.need_mm;

/** «Lluvia de ago a dic frente a lo que necesita el cultivo (papa), en mm»: los meses, el cultivo y la unidad. */
export function waterTitle(cropName: string, from: string | null | undefined, to: string | null | undefined): string {
  const months = from && to ? ` de ${monthOf(from)} a ${monthOf(to)}` : " de la ventana";
  return `Lluvia${months} frente a lo que necesita el cultivo (${cropName.toLowerCase()}), en mm`;
}

/**
 * La lluvia de la ventana, año por año, frente a lo que necesita el cultivo (HU-093; diseño `design/pantallas/detalle.py`):
 * una barra por año y la necesidad como línea punteada. Un año en que no alcanzó se dibuja vacío y punteado, y la leyenda
 * dice cuántos: forma, no solo color. Dice el periodo y de qué fuente es la lluvia (la que calculó la señal, R8). Un año
 * sin dato no tiene barra (R1), y sin datos la serie dice «sin datos» en vez de una gráfica en cero. Es historia, no pronóstico.
 */
export function WaterChart({
  series,
  status,
  cropName,
  from,
  to,
  version,
}: {
  series: WaterSeries | undefined;
  /** El estado de `GET /trends`: mientras carga o si falla, se dice, no se dibuja una serie vacía. */
  status: "pending" | "error" | "success";
  cropName: string;
  from: string | null | undefined;
  to: string | null | undefined;
  version: Version | undefined;
}) {
  const [active, setActive] = useState<number | null>(null);
  const [box, W] = useWidth<HTMLDivElement>(320);
  const PLOT_W = Math.max(120, W - PAD.left - PAD.right);
  // Un valor que falta (nulo o ausente) es «sin dato» (R1): nunca un cero.
  const points = (series?.points ?? [])
    .map((p) => ({ year: p.year, precip_mm: p.precip_mm ?? null, need_mm: p.need_mm ?? null }))
    .sort((a, b) => a.year - b.year);
  const title = waterTitle(cropName, from, to);
  if (status !== "success") {
    return (
      <div className="relative flex flex-col gap-1 border-2 border-dashed border-superficie-borde px-3 py-2 text-[15px]">
        <p className="font-bold">{title}</p>
        <p role={status === "pending" ? "status" : undefined} className="text-texto-secundario">
          {status === "pending" ? "Cargando la lluvia año por año…" : "No pudimos cargar la lluvia año por año. Intente más tarde."}
        </p>
      </div>
    );
  }
  if (!series || series.status !== "available" || points.every((p) => p.precip_mm === null && p.need_mm === null)) {
    return (
      <div className="relative flex flex-col gap-1 border-2 border-dashed border-superficie-borde px-3 py-2 text-[15px]">
        <p className="font-bold">{title}</p>
        <p className="text-texto-secundario">
          <span aria-hidden="true">? </span>Sin datos suficientes de la lluvia de esta ventana año por año.
        </p>
      </div>
    );
  }
  const values = points.flatMap((p) => [p.precip_mm, p.need_mm]).filter((v): v is number => v !== null);
  const top = Math.max(100, Math.ceil((Math.max(...values) * 1.15) / 100) * 100);
  const n = points.length;
  const slot = PLOT_W / n;
  const barW = slot * 0.6;
  const x = (i: number) => PAD.left + i * slot + (slot - barW) / 2;
  const y = (v: number) => PAD.top + PLOT_H - (v / top) * PLOT_H;
  const short = points.filter(shortYear).length;
  const counted = points.filter((p) => p.precip_mm !== null && p.need_mm !== null).length;
  const need = points.map((p, i) => (p.need_mm === null ? null : { cx: x(i) + barW / 2, cy: y(p.need_mm) }));
  const shown = active === null ? null : points.find((p) => p.year === active);
  const years = `${points[0].year}–${points[n - 1].year}`;
  const source = series.source_id ? sourceName(series.source_id, version) : null;
  const note = series.source_id ? sourceNote(series.source_id) : null;

  return (
    <figure className="relative flex min-w-0 flex-col gap-2">
      <figcaption className="text-[15px] font-bold">{title}</figcaption>
      <div ref={box} className="w-full min-w-0">
        <svg
          width={W}
          height={H}
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`${title}, años ${years}. La lluvia no alcanzó en ${short} de ${counted} años.`}
          className="block"
          onMouseLeave={() => setActive(null)}
        >
          {[0, 0.5, 1].map((t) => (
            <g key={t}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(top * t)}
                y2={y(top * t)}
                stroke={t === 0 ? "var(--color-texto-principal)" : "var(--color-superficie-borde)"}
                strokeWidth={t === 0 ? 1.5 : 1}
              />
              <text x={PAD.left - 6} y={y(top * t) + 4} textAnchor="end" fontSize="13" fill="var(--color-texto-secundario)">
                {NUMBER.format(top * t)}
              </text>
            </g>
          ))}
          {points.map((p, i) =>
            p.precip_mm === null ? null : (
              <rect
                key={p.year}
                x={x(i)}
                y={y(p.precip_mm)}
                width={barW}
                height={Math.max(0, y(0) - y(p.precip_mm))}
                rx="2"
                fill={shortYear(p) ? "var(--color-superficie-panel)" : "var(--color-paleta-cielo)"}
                stroke="var(--color-oscuro-cielo)"
                strokeWidth="1.5"
                strokeDasharray={shortYear(p) ? "4 3" : undefined}
                opacity={active !== null && active !== p.year ? 0.5 : 1}
              />
            ),
          )}
          {/* La necesidad del cultivo, año por año: una línea punteada que se corta donde no hay dato. */}
          {need.map((point, i) => {
            const next = need[i + 1];
            return point && next ? (
              <line
                key={i}
                x1={point.cx}
                y1={point.cy}
                x2={next.cx}
                y2={next.cy}
                stroke="var(--color-texto-principal)"
                strokeWidth="2"
                strokeDasharray="6 4"
              />
            ) : null;
          })}
          {need.map((point, i) =>
            point ? <circle key={points[i].year} cx={point.cx} cy={point.cy} r="2.5" fill="var(--color-texto-principal)" /> : null,
          )}
          {points.map((p, i) => (
            <text key={p.year} x={x(i) + barW / 2} y={H - 6} textAnchor="middle" fontSize="13" fill="var(--color-texto-secundario)">
              {String(p.year).slice(-2)}
            </text>
          ))}
          {/* Zonas de toque: una por año, más anchas que la barra. */}
          {points.map((p, i) => (
            <rect
              key={p.year}
              x={PAD.left + i * slot}
              y={PAD.top}
              width={slot}
              height={PLOT_H}
              fill="transparent"
              onMouseEnter={() => setActive(p.year)}
              onClick={() => setActive(p.year)}
            />
          ))}
        </svg>
      </div>
      <p aria-live="polite" className="min-h-6 text-[14px]">
        {shown
          ? `${shown.year}: llovieron ${shown.precip_mm === null ? "sin dato" : `${NUMBER.format(shown.precip_mm)} mm`}; necesitaba ${
              shown.need_mm === null ? "sin dato" : `${NUMBER.format(shown.need_mm)} mm`
            }.`
          : "Pase o toque un año para ver sus cifras."}
      </p>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[14px]" aria-label="Leyenda">
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block size-3 border-[1.5px] border-oscuro-cielo bg-paleta-cielo" />
          Lluvia
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block w-5 border-t-2 border-dashed border-texto-principal" />
          Lo que necesita
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block size-3 border-[1.5px] border-dashed border-oscuro-cielo bg-superficie-panel" />
          Años en que la lluvia no alcanzó: {short} de {counted}
        </li>
      </ul>
      <p className="text-[14px] text-texto-secundario">
        Años {years}
        {source ? ` · Lluvia: ${source}` : ""}. Es la historia de la zona, no un pronóstico.
        {note ? ` ${note}` : ""}
      </p>
      <details className="text-[14px]">
        <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
          Ver los datos en una tabla
        </summary>
        <table className="mt-1 w-full text-left">
          <thead>
            <tr>
              <th className="py-1 pr-3">Año</th>
              <th className="py-1 pr-3">Lluvia</th>
              <th className="py-1">Necesita</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.year} className="border-t border-superficie-borde">
                <td className="py-1 pr-3">{p.year}</td>
                <td className="py-1 pr-3">{p.precip_mm === null ? "Sin dato" : `${NUMBER.format(p.precip_mm)} mm`}</td>
                <td className="py-1">{p.need_mm === null ? "Sin dato" : `${NUMBER.format(p.need_mm)} mm`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
