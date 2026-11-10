import type { ReactNode } from "react";
import { EstimateLabel } from "@/components/ui/Labels";
import { Plate } from "@/components/ui/Plate";
import { signalTone } from "@/components/ui/SignalCard";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { StatusIcon, TONE_STYLE } from "@/components/ui/StatusMark";
import {
  SIGNAL_NAME,
  SOIL_ESTIMATE,
  formatValue,
  indicatorName,
  irrigationNote,
  isGrave,
  isP0,
  orderedSignals,
  phRange,
  sourceName,
  sourceNote,
  supplyNote,
  type MunicipalitySoil,
  type Signal,
  type SourceValue,
  type SupplySemester,
} from "@/features/diagnosis/signals";
import type { Version } from "@/features/version";

export interface SignalListProps {
  signals: Record<string, Signal> | null | undefined;
  /** La señal que más limita la ventana con las prioridades de quien consulta (`overall.limiting_signal`). */
  limiting: string | null | undefined;
  irrigated: boolean | null | undefined;
  supplySemester: SupplySemester | null | undefined;
  soil: MunicipalitySoil | undefined;
  version: Version | undefined;
}

/**
 * Las señales de la ventana (HU-092): las seis del P0 en su orden y las del P1 solo si vienen. Cada una con su estado en
 * forma y texto, su calificación de 0 a 100 (sin barra si no la tiene, R1), sus razones y, cuando trae varias fuentes,
 * todas juntas con la que calculó la señal marcada (R8). Nunca un valor combinado.
 */
export function SignalList({ signals, limiting, irrigated, supplySemester, soil, version }: SignalListProps) {
  const list = orderedSignals(signals);
  if (list.length === 0) return null;
  return (
    <ul className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label="Señales de la ventana">
      {list.map(([key, signal]) => (
        <SignalItem key={key} id={key} signal={signal} limiting={key === limiting}>
          {key === "water" && <Note>{irrigationNote(irrigated)}</Note>}
          {/* Con riego, la señal dice cuánto riego haría falta: es un resultado de riego y lleva su rótulo (R10). */}
          {key === "water" && irrigated === true && <EstimateLabel />}
          {key === "supply" && <Note>{supplyNote(supplySemester)}</Note>}
          {key === "soil" && <SoilNote soil={soil} />}
          {signal.reasons.length > 0 && (
            <ul className="relative flex list-disc flex-col gap-1 pl-5">
              {signal.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          {signal.sources && signal.sources.length > 0 && <Sources sources={signal.sources} version={version} />}
        </SignalItem>
      ))}
    </ul>
  );
}

function SignalItem({ id, signal, limiting, children }: { id: string; signal: Signal; limiting: boolean; children: ReactNode }) {
  const name = SIGNAL_NAME[id] ?? id;
  const headingId = `senal-${id}`;
  return (
    <li className="relative flex min-w-0 flex-col gap-3 px-5 pt-5 pb-6" data-signal={id}>
      <Plate
        c={14}
        fill="var(--color-superficie-panel)"
        stroke={limiting ? "var(--color-paleta-calabaza)" : "var(--color-superficie-borde)"}
        strokeWidth={limiting ? 3 : 2}
      />
      <div className="relative flex min-w-0 items-center gap-3">
        {isP0(id) && <SignalIcon signal={id} />}
        <h3 id={headingId} className="min-w-0 text-[clamp(1.1rem,2.5vw,1.3rem)]">
          {name}
        </h3>
      </div>
      {limiting && <LimitingTag />}
      <StatusBadge signal={signal} grave={isGrave(id, signal)} />
      <Score score={signal.score} />
      {children}
    </li>
  );
}

/** «Lo que más limita», con forma (un banderín) y texto, no solo con el borde de color. */
function LimitingTag() {
  return (
    <p className="relative inline-flex w-fit items-center gap-2 font-bold text-oscuro-calabaza">
      <svg aria-hidden="true" viewBox="0 0 20 22" className="size-5 shrink-0">
        <polygon points="3,1 5,1 5,21 3,21" fill="var(--color-paleta-noche)" />
        <polygon points="5,2 18,6 5,11" fill="var(--color-paleta-calabaza)" />
      </svg>
      Lo que más limita
    </p>
  );
}

/** El estado con silueta, ícono y texto (W2): «Desfavorable» es un cuadrado; «Datos insuficientes», una línea punteada con «?»; «No aplica», un guion. */
function StatusBadge({ signal, grave }: { signal: Signal; grave: boolean }) {
  const { tone, label } = signalTone({ ...signal, level: signal.level ?? null });
  const style = TONE_STYLE[tone];
  return (
    <span
      data-tone={tone}
      className={`relative inline-flex min-h-12 w-fit max-w-full items-center gap-2.5 px-5 py-2 font-bold ${style.ink}`}
    >
      <Plate {...style.plate} c={Math.min(style.plate.c ?? 10, 10)} />
      <span className="relative flex items-center gap-2.5">
        <StatusIcon icon={style.icon} />
        {grave ? `${label} · riesgo grave` : label}
      </span>
    </span>
  );
}

/** La calificación de 0 a 100 junto al nivel. Sin calificación no se dibuja nada: una barra en cero diría «muy mal» (R1). */
function Score({ score }: { score: number | null | undefined }) {
  if (score === null || score === undefined) return null;
  const value = Math.max(0, Math.min(100, score));
  return (
    <div className="relative flex flex-col gap-1.5">
      <p>
        Calificación: <span className="font-bold">{Math.round(value)}</span> de 100
      </p>
      <div aria-hidden="true" className="h-3 w-full overflow-hidden bg-superficie-panel-suave">
        <div className="h-full bg-oscuro-oliva" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <p className="relative text-[15px] leading-snug text-texto-secundario">{children}</p>;
}

/** El suelo lleva su rango y el rótulo de estimación (R10). Es el del municipio: el del lote llega con HU-182. */
function SoilNote({ soil }: { soil: MunicipalitySoil | undefined }) {
  const range = phRange(soil);
  return (
    <div className="relative flex flex-col gap-1 border-2 border-dashed border-oscuro-cielo/60 bg-[#E6F0F5] px-3 py-2 text-[15px] leading-snug">
      {range && <p className="font-bold">{range}, en el municipio.</p>}
      <p>{SOIL_ESTIMATE}</p>
    </div>
  );
}

/**
 * Todas las fuentes de un indicador juntas, cada una con su valor, su origen y su fecha, y cuál calculó la señal (R8).
 * Nunca se mezclan ni se promedian.
 */
function Sources({ sources, version }: { sources: SourceValue[]; version: Version | undefined }) {
  return (
    <div className="relative flex flex-col gap-2">
      <p className="text-[15px] font-bold">Qué dice cada fuente</p>
      <ul className="flex flex-col gap-2">
        {sources.map((source) => {
          const note = sourceNote(source.source_id);
          return (
            <li
              key={`${source.source_id}-${source.indicator}`}
              className={`flex min-w-0 flex-col gap-0.5 border-l-4 py-1 pl-3 text-[15px] leading-snug ${
                source.used ? "border-oscuro-oliva" : "border-superficie-borde"
              }`}
            >
              <UsedTag used={source.used} />
              <p>
                <span className="font-bold">{indicatorName(source.indicator)}:</span> {formatValue(source.value, source.unit)}
                {source.preliminary ? " (preliminar)" : ""}
              </p>
              <p className="text-texto-secundario">
                {sourceName(source.source_id, version)} · {source.period ? `periodo ${source.period}` : "periodo no informado"}
              </p>
              {note && <p className="text-texto-secundario">{note}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** «Usada para la luz» (rombo lleno) o «Para contrastar» (rombo vacío): forma y texto. */
function UsedTag({ used }: { used: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 font-bold">
      <svg aria-hidden="true" viewBox="0 0 14 14" className="size-3.5 shrink-0">
        <polygon
          points="7,1 13,7 7,13 1,7"
          fill={used ? "var(--color-oscuro-oliva)" : "none"}
          stroke="var(--color-oscuro-oliva)"
          strokeWidth="2"
        />
      </svg>
      {used ? "Usada para la luz" : "Para contrastar"}
    </span>
  );
}
