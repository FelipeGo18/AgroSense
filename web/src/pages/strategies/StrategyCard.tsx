import type { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { Plate } from "@/components/ui/Plate";
import { StatusIcon, TONE_STYLE, type Tone } from "@/components/ui/StatusMark";
import { LIGHT_LABEL, type Light } from "@/components/ui/TrafficLightBadge";
import { SIGNAL_NAME, harvestNote } from "@/features/diagnosis/signals";
import { formatShortDate } from "@/features/farm/seasons";
import type { RotationWeights } from "@/features/strategies/entry";
import {
  CRITERIA,
  HEALTH_CRITERIA,
  cycleKind,
  delta,
  exclusionTitle,
  healthTone,
  sequence,
  sourcesText,
  type Cycle,
  type Delta,
  type Issue,
  type Strategy,
} from "@/features/strategies/strategies";
import type { Version } from "@/features/version";

export interface StrategyCardProps {
  strategy: Strategy;
  names: Map<string, string>;
  kinds: Map<string, string>;
  weights: RotationWeights;
  version: Version | undefined;
}

/**
 * Una estrategia (HU-102): su puesto y su puntaje, sus ciclos en orden con su luz, el desglose por criterio con lo que gana
 * o pierde frente a lo de hoy, sus razones y su salud del suelo. La rotación actual usa la misma tarjeta, rotulada «Lo
 * que siembra hoy», sin puesto y con sus problemas a la vista (decisión 14).
 */
export function StrategyCard({ strategy, names, kinds, weights, version }: StrategyCardProps) {
  const current = strategy.kind === "current";
  const title = sequence(strategy.crop_ids, names);
  const total = delta(strategy.vs_current?.total);
  return (
    <article aria-label={current ? `Lo que siembra hoy: ${title}` : `Estrategia ${strategy.rank}: ${title}`} className="min-w-0">
      <Card bodyClassName="gap-5">
        <header className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 items-start gap-3">
            <RankBadge current={current} rank={strategy.rank} />
            <div className="flex min-w-0 flex-col gap-0.5">
              <h3 className="text-[clamp(1.1rem,2.5vw,1.35rem)] leading-tight break-words">
                {current ? `Lo que siembra hoy: ${title}` : title}
              </h3>
              {current && <p className="text-[15px] text-texto-secundario">Se evalúa igual que las demás y no entra al orden.</p>}
            </div>
          </div>
          <div className="flex flex-col items-end">
            {strategy.total_score === null || strategy.total_score === undefined ? (
              <p className="text-[15px] font-bold text-texto-secundario">Sin puntaje total</p>
            ) : (
              <p className="leading-none">
                <span className="font-titulos text-[2rem] font-semibold">{Math.round(strategy.total_score)}</span>{" "}
                <span className="text-[15px] text-texto-secundario">de 100</span>
              </p>
            )}
            {total && <DeltaText delta={total} suffix="en total" />}
          </div>
        </header>

        <Cycles cycles={strategy.cycles} names={names} kinds={kinds} />

        <Breakdown strategy={strategy} weights={weights} />

        {strategy.reasons.length > 0 && (
          <ul className="flex list-disc flex-col gap-1 pl-5 text-[15px]">
            {strategy.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}

        {current && (strategy.issues ?? []).length > 0 && <Issues issues={strategy.issues ?? []} version={version} />}

        <SoilHealth health={strategy.soil_health} version={version} />

        {strategy.limitations.length > 0 && (
          <div className="flex flex-col gap-1 text-[15px] text-texto-secundario">
            <p className="font-bold">Limitaciones</p>
            <ul className="flex list-disc flex-col gap-1 pl-5">
              {strategy.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </article>
  );
}

/** El puesto en un rombo, o «HOY» en la rotación actual, que no entra al orden. */
function RankBadge({ current, rank }: { current: boolean; rank: number | null }) {
  if (current) {
    return (
      <span className="relative inline-flex h-9 shrink-0 items-center px-2.5 text-sm font-bold text-white">
        <Plate c={6} fill="var(--color-oscuro-cielo)" />
        <span className="relative">HOY</span>
      </span>
    );
  }
  return (
    <span className="relative inline-flex size-11 shrink-0 items-center justify-center font-bold" role="img" aria-label={`Puesto ${rank}`}>
      <svg aria-hidden="true" viewBox="0 0 44 44" className="absolute inset-0 size-full">
        <polygon
          points="22,2 42,22 22,42 2,22"
          fill="var(--color-superficie-panel-suave)"
          stroke="var(--color-oscuro-oliva)"
          strokeWidth="2.5"
        />
      </svg>
      <span className="relative" aria-hidden="true">
        {rank}
      </span>
    </span>
  );
}

/** Gana (triángulo arriba), pierde (triángulo abajo) o igual (raya), con su texto: nunca solo color ni solo signo. */
function DeltaText({ delta: d, suffix }: { delta: Delta; suffix?: string }) {
  const color = d.shape === "up" ? "text-oscuro-oliva" : d.shape === "down" ? "text-oscuro-rojo" : "text-texto-secundario";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[14px] font-bold ${color}`}>
      <svg aria-hidden="true" viewBox="0 0 12 12" className="size-3 shrink-0">
        {d.shape === "up" && <polygon points="6,1 11,11 1,11" fill="currentColor" />}
        {d.shape === "down" && <polygon points="1,1 11,1 6,11" fill="currentColor" />}
        {d.shape === "same" && <rect x="1" y="5" width="10" height="2" fill="currentColor" />}
      </svg>
      {suffix && d.shape !== "same" ? `${d.words} ${suffix}` : d.words}
    </span>
  );
}

/** Los ciclos en orden. Un descanso no tiene luz: no se siembra. Un abono verde se incorpora en vez de cosecharse. */
function Cycles({ cycles, names, kinds }: { cycles: Cycle[]; names: Map<string, string>; kinds: Map<string, string> }) {
  const bases = new Set(cycles.filter((c) => cycleKind(c.crop_id, kinds) !== "fallow").map((c) => c.harvest_basis));
  return (
    <div className="flex flex-col gap-2">
      <ol className={`grid grid-cols-1 gap-3 ${cycles.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
        {cycles.map((cycle) => (
          <CycleBox
            key={cycle.cycle}
            cycle={cycle}
            total={cycles.length}
            name={names.get(cycle.crop_id) ?? cycle.crop_id}
            kind={cycleKind(cycle.crop_id, kinds)}
          />
        ))}
      </ol>
      {[...bases].map((basis) => (
        <p key={basis} className="text-[14px] text-texto-secundario">
          {harvestNote(basis)}
        </p>
      ))}
    </div>
  );
}

function CycleBox({ cycle, total, name, kind }: { cycle: Cycle; total: number; name: string; kind: "crop" | "cover" | "fallow" }) {
  const fallow = kind === "fallow";
  return (
    <li
      aria-label={`Ciclo ${cycle.cycle} de ${total}: ${name}`}
      className={`flex min-w-0 flex-col gap-1.5 border-2 px-3 py-3 text-[15px] leading-snug ${
        fallow ? "border-dashed border-superficie-borde bg-superficie-panel" : "border-superficie-borde bg-superficie-panel-suave"
      }`}
    >
      <p className="text-[13px] font-bold tracking-wide text-texto-secundario uppercase">Ciclo {cycle.cycle}</p>
      <p className="font-titulos text-[1.1rem] leading-tight font-semibold break-words">{name}</p>
      {kind === "cover" && <p className="w-fit border-2 border-oscuro-oliva px-1.5 text-[13px] font-bold text-oscuro-oliva">Abono verde</p>}
      {fallow ? (
        <>
          <p>Desde el {formatShortDate(cycle.sowing_date)}</p>
          <p>Hasta el {formatShortDate(cycle.harvest_estimate)}</p>
          <p className="text-[14px] font-bold text-texto-secundario">Sin semáforo: no se siembra</p>
        </>
      ) : (
        <>
          <p>Siembra {formatShortDate(cycle.sowing_date)}</p>
          <p>
            {kind === "cover" ? "Se incorpora" : "Cosecha"} ~{formatShortDate(cycle.harvest_estimate)}
          </p>
          {cycle.light ? <LightTag light={cycle.light} /> : <p className="text-[14px] text-texto-secundario">Sin luz para este ciclo</p>}
          {cycle.light_default && cycle.light_default !== cycle.light && (
            <p className="text-[14px]">
              Con el criterio de AgroSense: <span className="font-bold">{LIGHT_LABEL[cycle.light_default].toLowerCase()}</span>
            </p>
          )}
          {cycle.limiting_signal && (
            <p className="text-[14px] font-bold text-texto-secundario">
              Limita: {(SIGNAL_NAME[cycle.limiting_signal] ?? cycle.limiting_signal).toLowerCase()}
            </p>
          )}
          {cycle.high_risk && <p className="text-[14px] font-bold text-oscuro-rojo">Alto riesgo de clima en este ciclo</p>}
        </>
      )}
    </li>
  );
}

/** La luz de un ciclo con silueta, ícono y texto, en pequeño (W2). */
function LightTag({ light }: { light: Light }) {
  const style = TONE_STYLE[light];
  return (
    <span
      data-light={light}
      className={`relative inline-flex min-h-9 w-fit items-center gap-2 px-3 py-1 text-[14px] font-bold ${style.ink}`}
    >
      <Plate {...style.plate} c={Math.min(style.plate.c ?? 8, 8)} strokeWidth={2} />
      <span className="relative flex items-center gap-2">
        <StatusIcon icon={style.icon} />
        {LIGHT_LABEL[light]}
      </span>
    </span>
  );
}

/**
 * El desglose por criterio (de 0 a 100) con el peso que le dio el agricultor y, en las sugeridas, lo que ganan o pierden
 * frente a lo de hoy. Un criterio sin datos no tiene barra: una barra en cero diría «muy mal» (R1).
 */
function Breakdown({ strategy, weights }: { strategy: Strategy; weights: RotationWeights }) {
  return (
    <dl className="flex flex-col gap-2.5">
      {CRITERIA.map(({ key, label }) => {
        const score = strategy.scores[key];
        const d = delta(strategy.vs_current?.[key]);
        return (
          <div key={key} className="flex min-w-0 flex-col gap-1">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <dt className="font-bold">{label}</dt>
              <dd className="flex flex-wrap items-baseline gap-x-3 text-[15px]">
                {score === null || score === undefined ? (
                  <span className="text-texto-secundario">Sin datos: no entra al total</span>
                ) : (
                  <span>
                    <span className="font-bold">{Math.round(score)}</span> de 100
                  </span>
                )}
                <span className="text-texto-secundario">peso {weights[key]}</span>
                {d && <DeltaText delta={d} />}
              </dd>
            </div>
            {score !== null && score !== undefined && (
              <div aria-hidden="true" className="h-2.5 w-full bg-superficie-panel-suave">
                <div className="h-full bg-oscuro-oliva" style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
              </div>
            )}
          </div>
        );
      })}
    </dl>
  );
}

/** Por qué lo de hoy no cumple: la regla que viola, el cultivo no apto, el pH o el ciclo de alto riesgo, con su fuente. */
function Issues({ issues, version }: { issues: Issue[]; version: Version | undefined }) {
  return (
    <section
      aria-label="Lo que no cumple"
      className="flex flex-col gap-2 border-l-4 border-oscuro-rojo bg-superficie-panel-suave px-4 py-3"
    >
      <p className="font-bold">Lo que no cumple</p>
      <ul className="flex flex-col gap-2 text-[15px] leading-snug">
        {issues.map((issue, i) => (
          <li key={`${issue.cycle}-${issue.kind}-${i}`} className="flex flex-col gap-0.5">
            <span className="font-bold">{exclusionTitle(issue)}</span>
            <span>{issue.reason}</span>
            <SourceLine ids={issue.source_ids} version={version} />
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * La salud del suelo: cinco criterios, cada uno con su nivel en forma y texto, su razón y la fuente de su regla (R8).
 * Es una comparación entre estrategias por reglas, no una predicción de cuánto mejora el suelo (decisión 4).
 */
function SoilHealth({ health, version }: { health: Strategy["soil_health"]; version: Version | undefined }) {
  return (
    <section aria-label="Salud del suelo" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <p className="font-bold">Salud del suelo</p>
        <p className="text-[14px] font-bold text-oscuro-cielo">Comparación, no predicción</p>
      </div>
      <ul className="flex flex-col">
        {HEALTH_CRITERIA.map(({ key, label }) => {
          const criterion = health[key];
          const { tone, label: level } = healthTone(criterion);
          return (
            <li
              key={key}
              className="grid grid-cols-1 gap-x-4 gap-y-1 border-t-2 border-superficie-borde py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)]"
            >
              <div className="flex items-start gap-2">
                <LevelMark tone={tone} />
                <div className="flex flex-col">
                  <span className="font-bold">{label}</span>
                  <span
                    className={`text-[14px] font-bold ${tone === "insufficient_data" || tone === "not_applicable" ? "text-texto-secundario" : ""}`}
                  >
                    {level}
                  </span>
                </div>
              </div>
              <div className="flex min-w-0 flex-col gap-0.5 text-[15px] leading-snug">
                {(criterion?.reasons ?? []).map((reason) => (
                  <p key={reason}>{reason}</p>
                ))}
                <SourceLine ids={criterion?.source_ids} version={version} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** La forma del nivel en el color del borde de su estado: sobre fondo blanco, la tinta del letrero no se ve. */
function LevelMark({ tone }: { tone: Tone }) {
  return (
    <span className="mt-0.5 inline-flex" style={{ color: TONE_STYLE[tone].plate.stroke }}>
      <StatusIcon icon={TONE_STYLE[tone].icon} />
    </span>
  );
}

function SourceLine({ ids, version }: { ids: string[] | null | undefined; version: Version | undefined }) {
  const text = sourcesText(ids, version);
  return text ? <Small>Fuente: {text}</Small> : null;
}

function Small({ children }: { children: ReactNode }) {
  return <span className="text-[14px] text-texto-secundario">{children}</span>;
}
