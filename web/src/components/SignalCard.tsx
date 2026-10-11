import { Plate, Stake } from "./Plate";
import { StatusIcon, TONE_STYLE, type Tone } from "./StatusMark";

/** Forma de cada señal en la respuesta de diagnóstico (specs/02-contratos.md). */
export interface Signal {
  status: "available" | "insufficient_data" | "not_applicable";
  level: "favorable" | "moderate" | "unfavorable" | null;
  indicators: string[];
  reasons: string[];
}

export type SignalKind = "climate" | "supply" | "market";

const KIND_TITLE: Record<SignalKind, string> = {
  climate: "Clima",
  supply: "Oferta · área sembrada",
  market: "Mercado",
};

const LEVEL: Record<NonNullable<Signal["level"]>, { tone: Tone; label: string }> = {
  favorable: { tone: "green", label: "Favorable" },
  moderate: { tone: "yellow", label: "Moderado" },
  unfavorable: { tone: "red", label: "Desfavorable" },
};

/** R1: disponibilidad y nivel son campos distintos; sin datos nunca se pinta como riesgo. */
export function signalTone(signal: Signal): { tone: Tone; label: string } {
  if (signal.status === "insufficient_data") return { tone: "insufficient_data", label: "Datos insuficientes" };
  if (signal.status === "not_applicable" || signal.level === null) return { tone: "not_applicable", label: "No aplica" };
  return LEVEL[signal.level];
}

/** Íconos low-poly del tipo de señal: nube con gota, brote en el surco y costal. */
function KindIcon({ kind }: { kind: SignalKind }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 44 46" className="absolute top-5 right-6 size-11">
      {kind === "climate" && (
        <>
          <polygon
            points="6,26 12,14 22,10 32,14 38,24 34,30 10,30"
            fill="var(--color-paleta-niebla)"
            stroke="var(--color-oscuro-cielo)"
            strokeWidth="2"
          />
          <polygon points="12,14 22,10 20,30 10,30" fill="color-mix(in srgb, var(--color-paleta-niebla), black 6%)" />
          <polygon points="24,33 28,40 24,44 20,40" fill="var(--color-oscuro-cielo)" />
        </>
      )}
      {kind === "supply" && (
        <>
          <polygon points="2,34 42,34 38,42 6,42" fill="var(--color-paleta-tierra)" />
          <polygon points="21,34 23,34 23,16 21,16" fill="var(--color-oscuro-brote)" />
          <polygon points="22,22 8,12 12,26" fill="var(--color-paleta-brote)" />
          <polygon points="22,18 38,6 34,22" fill="color-mix(in srgb, var(--color-paleta-brote), black 10%)" />
        </>
      )}
      {kind === "market" && (
        <>
          <polygon
            points="14,8 30,8 26,14 38,30 34,42 10,42 6,30 18,14"
            fill="var(--color-paleta-trigo)"
            stroke="var(--color-oscuro-trigo)"
            strokeWidth="2"
          />
          <polygon points="18,14 26,14 22,42 10,42 6,30" fill="color-mix(in srgb, var(--color-paleta-trigo), white 12%)" />
          <polygon points="16,14 28,14 28,17 16,17" fill="var(--color-oscuro-trigo)" />
        </>
      )}
    </svg>
  );
}

/** Bruma de «datos insuficientes»: nubes facetadas de niebla al pie del letrero. */
function Mist() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 500 70"
      preserveAspectRatio="xMidYMax meet"
      className="pointer-events-none absolute inset-x-1 bottom-1 h-[70px] w-[calc(100%-8px)]"
    >
      <polygon points="220,62 240,38 280,24 324,18 370,32 402,52 390,64" fill="var(--color-paleta-niebla)" />
      <polygon points="280,24 324,18 370,32 320,64" fill="color-mix(in srgb, var(--color-paleta-niebla), black 5%)" />
      <polygon points="53,66 69,47 101,36 136,31 173,42 199,58 189,68" fill="var(--color-paleta-niebla)" />
      <polygon points="367,68 381,51 409,41 440,37 472,46 494,60 486,69" fill="var(--color-paleta-niebla)" />
    </svg>
  );
}

export interface SignalCardProps {
  kind: SignalKind;
  signal?: Signal;
  loading?: boolean;
}

/** Tarjeta de señal: un letrero de campo sobre dos estacas, con un banderín de estado. */
export function SignalCard({ kind, signal, loading = false }: SignalCardProps) {
  const headingId = `signal-${kind}`;
  const pending = loading || !signal;
  const insufficient = !pending && signal.status === "insufficient_data";
  return (
    <div className="flex h-full flex-col">
      <article aria-labelledby={headingId} aria-busy={pending || undefined} className="relative flex min-h-[250px] grow flex-col gap-4 p-7">
        <Plate
          c={16}
          fill="var(--color-superficie-panel)"
          stroke={insufficient ? "var(--color-oscuro-cielo)" : "var(--color-superficie-borde)"}
          dash={insufficient ? "3 5" : undefined}
        />
        {insufficient && <Mist />}
        <KindIcon kind={kind} />
        <h3 id={headingId} className="relative pr-14 text-lg">
          {KIND_TITLE[kind]}
        </h3>
        {pending ? (
          <div role="status" className="relative flex flex-col gap-3">
            <span className="sr-only">Cargando señal</span>
            <span aria-hidden="true" className="relative block h-[52px] w-48 max-w-full animate-pulse motion-reduce:animate-none">
              <Plate fill="var(--color-superficie-panel-suave)" />
            </span>
            <span aria-hidden="true" className="block h-4 w-full animate-pulse bg-superficie-panel-suave motion-reduce:animate-none" />
            <span aria-hidden="true" className="block h-4 w-3/4 animate-pulse bg-superficie-panel-suave motion-reduce:animate-none" />
          </div>
        ) : (
          <SignalBody signal={signal} />
        )}
      </article>
      <div aria-hidden="true" className="-mt-1.5 flex justify-between px-[60px]">
        <Stake />
        <Stake />
      </div>
    </div>
  );
}

function SignalBody({ signal }: { signal: Signal }) {
  const { tone, label } = signalTone(signal);
  const style = TONE_STYLE[tone];
  return (
    <>
      <span
        data-tone={tone}
        className={`relative inline-flex h-[52px] w-fit items-center gap-2.5 px-5 font-bold whitespace-nowrap ${style.ink}`}
      >
        <Plate {...style.plate} c={Math.min(style.plate.c ?? 10, 10)} />
        <span className="relative flex items-center gap-2.5">
          <StatusIcon icon={style.icon} />
          {label}
        </span>
      </span>
      {signal.reasons.length > 0 && (
        <ul className="relative list-disc pl-5 text-texto-principal">
          {signal.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </>
  );
}
