import { formatPesos, formatShortDay, seasonPercent, shortMonthName, type Price, type Season } from "@/features/market/prices";

/**
 * Gráficas de «Precios» (HU-221), en SVG propio. Son quietas: no tienen nada que animar, así que se ven igual en modo
 * ligero. Cada una lleva su resumen escrito: la gráfica nunca es la única forma de leer el dato.
 */

// Lienzos angostos a propósito: en el celular la gráfica mide unos 300 px y el texto tiene que seguir leyéndose.
const W = 360;
const H = 210;
const PAD = { top: 12, right: 8, bottom: 26, left: 62 };

/** Tres valores redondos para el eje: el mínimo, el medio y el máximo, redondeados a una cifra legible. */
function ticks(low: number, high: number) {
  const step = 10 ** Math.max(1, Math.floor(Math.log10(Math.max(high - low, 1))));
  const bottom = Math.floor(low / step) * step;
  const top = Math.ceil(high / step) * step;
  return [bottom, (bottom + top) / 2, top];
}

/** El precio medio de cada día del último año, con la franja entre el mínimo y el máximo. */
export function PriceChart({ days }: { days: Price[] }) {
  if (days.length < 2) return null;
  const values = days.flatMap((d) => [d.min_cop_kg ?? d.avg_cop_kg, d.max_cop_kg ?? d.avg_cop_kg]);
  const [bottom, middle, top] = ticks(Math.min(...values), Math.max(...values));
  const first = Date.parse(days[0].date);
  const span = Date.parse(days[days.length - 1].date) - first || 1;
  const x = (day: string) => PAD.left + ((Date.parse(day) - first) / span) * (W - PAD.left - PAD.right);
  const y = (value: number) => PAD.top + (1 - (value - bottom) / (top - bottom || 1)) * (H - PAD.top - PAD.bottom);
  const line = days.map((d, i) => `${i ? "L" : "M"}${x(d.date).toFixed(1)},${y(d.avg_cop_kg).toFixed(1)}`).join("");
  const band =
    days.map((d, i) => `${i ? "L" : "M"}${x(d.date).toFixed(1)},${y(d.max_cop_kg ?? d.avg_cop_kg).toFixed(1)}`).join("") +
    [...days]
      .reverse()
      .map((d) => `L${x(d.date).toFixed(1)},${y(d.min_cop_kg ?? d.avg_cop_kg).toFixed(1)}`)
      .join("") +
    "Z";
  // Una marca por trimestre, contando hacia atrás desde el último día: siempre cae el último.
  const marks = [0, 1, 2, 3].map((q) => days[Math.max(0, days.length - 1 - Math.round((q * (days.length - 1)) / 3))]);
  const low = days.reduce((a, b) => (b.avg_cop_kg < a.avg_cop_kg ? b : a));
  const high = days.reduce((a, b) => (b.avg_cop_kg > a.avg_cop_kg ? b : a));
  const summary = `Precio medio más bajo: ${formatPesos(low.avg_cop_kg)} el ${formatShortDay(low.date)}. Más alto: ${formatPesos(high.avg_cop_kg)} el ${formatShortDay(high.date)}.`;
  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Precio por kilo del último año. ${summary}`} className="h-auto w-full">
        {[bottom, middle, top].map((value) => (
          <g key={value}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(value)} y2={y(value)} stroke="var(--color-superficie-borde)" strokeWidth="1" />
            <text x={PAD.left - 6} y={y(value) + 4} textAnchor="end" fontSize="12" fill="var(--color-texto-secundario)">
              {formatPesos(value)}
            </text>
          </g>
        ))}
        <path d={band} fill="var(--color-paleta-oliva)" opacity="0.18" />
        <path d={line} fill="none" stroke="var(--color-oscuro-oliva)" strokeWidth="2.5" strokeLinejoin="round" />
        {marks.map((d, i) => (
          <text
            key={d.date}
            x={x(d.date)}
            y={H - 6}
            textAnchor={i === 0 ? "end" : i === marks.length - 1 ? "start" : "middle"}
            fontSize="12"
            fill="var(--color-texto-secundario)"
          >
            {formatShortDay(d.date)}
          </text>
        ))}
      </svg>
      <figcaption className="text-[15px] leading-snug text-texto-secundario">
        La línea es el precio medio de cada día; la franja, el mínimo y el máximo. {summary}
      </figcaption>
    </figure>
  );
}

const SW = 360;
const SH = 220;
const SPAD = { top: 22, bottom: 44, side: 4 };

/**
 * En qué meses suele estar más caro o más barato que el resto de su año. Las barras salen de la línea del promedio del
 * año: hacia arriba, más caro; hacia abajo, más barato. Cada barra lleva su porcentaje escrito.
 */
export function SeasonChart({ season }: { season: Season }) {
  const percents = season.months.map((m) => seasonPercent(m.seasonal_index));
  const reach = Math.max(10, ...percents.map(Math.abs));
  const zero = SPAD.top + (SH - SPAD.top - SPAD.bottom) / 2;
  const scale = (SH - SPAD.top - SPAD.bottom) / 2 / reach;
  const slot = (SW - 2 * SPAD.side) / 12;
  return (
    <svg viewBox={`0 0 ${SW} ${SH}`} aria-hidden="true" className="h-auto w-full">
      {season.months.map((m, i) => {
        const p = percents[i];
        const cx = SPAD.side + slot * i + slot / 2;
        const height = Math.abs(p) * scale;
        const above = p > 0;
        return (
          <g key={m.month}>
            <rect
              x={cx - slot * 0.32}
              y={above ? zero - height : zero}
              width={slot * 0.64}
              height={Math.max(height, 1)}
              fill={above ? "var(--color-paleta-calabaza)" : "var(--color-paleta-cielo)"}
              stroke={above ? "var(--color-oscuro-calabaza)" : "var(--color-oscuro-cielo)"}
              strokeWidth="1.5"
            />
            <text
              x={cx}
              y={above ? zero - height - 6 : zero + height + 16}
              textAnchor="middle"
              fontSize="11"
              fontWeight="700"
              fill="var(--color-texto-principal)"
            >
              {p > 0 ? `+${p}` : p}
            </text>
            <text x={cx} y={SH - 6} textAnchor="middle" fontSize="11" fill="var(--color-texto-secundario)">
              {shortMonthName(m.month)}
            </text>
          </g>
        );
      })}
      <line x1={SPAD.side} x2={SW - SPAD.side} y1={zero} y2={zero} stroke="var(--color-texto-principal)" strokeWidth="1.5" />
    </svg>
  );
}
