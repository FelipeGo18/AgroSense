import { Link } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ExampleLabel } from "@/components/ui/Labels";
import { explain422, type RotationResponse, type RotationWeights, type useRotations } from "@/features/strategies/entry";
import {
  excludedBreakdown,
  excludedTotal,
  exclusionTitle,
  sequence,
  sourcesText,
  type Exclusion,
  type Strategy,
} from "@/features/strategies/strategies";
import type { Version } from "@/features/version";
import { StrategyCard } from "./StrategyCard";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";
const NOT_FORECAST = "Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo.";
const YOUR_CALL = "Es información para decidir. La decisión es suya.";

export interface StrategyResultsProps {
  rotations: ReturnType<typeof useRotations>;
  weights: RotationWeights;
  cycles: 2 | 3;
  names: Map<string, string>;
  kinds: Map<string, string>;
  version: Version | undefined;
  /** Volver a la entrada, con lo que ya escribió. */
  onEdit: () => void;
  /** Volver a la entrada para escribir la rotación que viene haciendo (HU-223). */
  onWriteCurrent: () => void;
  /** Probar el mismo terreno con dos ciclos. */
  onTwoCycles: () => void;
  /** La dirección del detalle de un ciclo de una estrategia (HU-215). */
  cycleLink: (strategy: Strategy, cycle: number) => string;
}

/**
 * El resultado de las estrategias (HU-102): lo que siembra hoy primero, las sugeridas en su orden, las descartadas a
 * pedido y, sin estrategias válidas, un estado vacío que propone qué cambiar. Al mover una prioridad se vuelve a pedir
 * y, mientras llega, se sigue viendo el orden anterior con un aviso.
 */
export function StrategyResults({
  rotations,
  weights,
  cycles,
  names,
  kinds,
  version,
  onEdit,
  onWriteCurrent,
  onTwoCycles,
  cycleLink,
}: StrategyResultsProps) {
  if (rotations.isPending) {
    return (
      <p role="status" className="mt-8">
        Comparando estrategias…
      </p>
    );
  }
  if (rotations.isError) {
    return (
      <div className="mt-8 flex flex-col items-start gap-4">
        <Alert>{errorText(rotations.error)}</Alert>
        <Button variant="secondary" onClick={onEdit}>
          Cambiar los datos
        </Button>
      </div>
    );
  }
  const data = rotations.data;
  const empty = data.strategies.length === 0;
  const cardProps = { names, kinds, weights: data.weights ?? weights, version };
  return (
    <div aria-busy={rotations.isPlaceholderData || undefined} className="mt-8 flex min-w-0 flex-col gap-10">
      <div className="flex flex-col gap-3">
        <Banner tone="estimate">{NOT_FORECAST}</Banner>
        <div className="flex flex-wrap items-center gap-3">
          {data.versions.dataset === "ejemplo" && <ExampleLabel>respuesta simulada</ExampleLabel>}
          {rotations.isPlaceholderData && (
            <p role="status" className="font-bold text-texto-secundario">
              Actualizando con sus prioridades…
            </p>
          )}
        </div>
      </div>

      {data.current_strategy ? (
        <section aria-labelledby="hoy" className="flex min-w-0 flex-col gap-4">
          <SectionTitle id="hoy" title="Lo que usted siembra hoy">
            Su rotación de siempre, evaluada con los mismos criterios. Cada estrategia de abajo dice cuánto gana o pierde frente a ella.
          </SectionTitle>
          <StrategyCard strategy={data.current_strategy} {...cardProps} cycleLink={(n) => cycleLink(data.current_strategy!, n)} />
        </section>
      ) : (
        !empty && (
          <section aria-labelledby="hoy" className="flex min-w-0 flex-col gap-4">
            <SectionTitle id="hoy" title="Lo que usted siembra hoy" />
            <div className="flex flex-col items-start gap-3 border-2 border-dashed border-superficie-borde bg-superficie-panel px-5 py-4">
              <p>
                No nos dijo qué viene sembrando en este terreno, así que no hay con qué comparar. Si lo escribe, cada estrategia dice cuánto
                gana o pierde frente a lo de hoy.
              </p>
              <Button variant="secondary" onClick={onWriteCurrent}>
                Escribir lo que siembro
              </Button>
            </div>
          </section>
        )
      )}

      {empty ? (
        <section
          aria-labelledby="ninguna"
          className="flex flex-col items-start gap-4 border-2 border-dashed border-oscuro-cielo/60 bg-superficie-panel px-5 py-5"
        >
          <h2 id="ninguna" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            Ninguna estrategia cumple las reglas con estos datos
          </h2>
          <p className="max-w-[760px]">
            No es que su terreno sea malo: abajo está por qué se descartó cada una. Pruebe con otra fecha de siembra
            {cycles === 3 ? " o con dos ciclos en vez de tres" : ""}.
          </p>
          <div className="flex w-full flex-wrap gap-3">
            <Button onClick={onEdit} className="w-full sm:w-auto">
              Cambiar la fecha
            </Button>
            {cycles === 3 && (
              <Button variant="secondary" onClick={onTwoCycles} className="w-full sm:w-auto">
                Probar con 2 ciclos
              </Button>
            )}
          </div>
        </section>
      ) : (
        <section aria-labelledby="ordenadas" className="flex min-w-0 flex-col gap-4">
          <SectionTitle id="ordenadas" title="Estrategias ordenadas por lo que le importa">
            Solo las que cumplen las reglas de rotación. Puntaje de 0 a 100 por criterio, ponderado por sus prioridades.
          </SectionTitle>
          <ol className="grid grid-cols-1 gap-8 xl:grid-cols-2">
            {data.strategies.map((strategy) => (
              <li key={strategy.crop_ids.join("-")} className="min-w-0">
                <StrategyCard strategy={strategy} {...cardProps} cycleLink={(n) => cycleLink(strategy, n)} />
              </li>
            ))}
          </ol>
        </section>
      )}

      <Excluded data={data} names={names} version={version} open={empty} />

      {data.limitations.length > 0 && (
        <section aria-labelledby="limitaciones" className="flex flex-col gap-2">
          <h2 id="limitaciones" className="text-[clamp(1.1rem,2.5vw,1.35rem)]">
            Limitaciones
          </h2>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {data.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-col gap-3">
        <Banner tone="decision">{YOUR_CALL}</Banner>
        <div className="flex flex-wrap items-center justify-between gap-3 text-[15px] text-texto-secundario">
          <p>
            Datos {data.versions.dataset ?? "sin versión"} · Reglas {data.versions.rules ?? "sin versión"}
          </p>
          <Link to={PATHS.howItWorks} className={`${LINK} inline-flex min-h-11 items-center`}>
            ¿Cómo se arma este orden?
          </Link>
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ id, title, children }: { id: string; title: string; children?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <h2 id={id} className="text-[clamp(1.25rem,3vw,1.75rem)]">
        {title}
      </h2>
      {children && <p className="max-w-[880px] text-texto-secundario">{children}</p>}
    </div>
  );
}

function Banner({ tone, children }: { tone: "estimate" | "decision"; children: string }) {
  const style = tone === "estimate" ? "border-oscuro-cielo bg-[#E6F0F5]" : "border-oscuro-oliva bg-[#EEF2E4]";
  return <p className={`border-2 px-4 py-3 font-bold ${style}`}>{children}</p>;
}

/**
 * Las descartadas, a pedido (R3): la secuencia, el ciclo y su motivo, con la fuente. La API trae hasta 10 y cuenta
 * todas por motivo (`excluded_counts`): se dice cuántas son y cuántas se ven. Sin estrategias válidas, ya abiertas.
 */
function Excluded({
  data,
  names,
  version,
  open,
}: {
  data: RotationResponse;
  names: Map<string, string>;
  version: Version | undefined;
  open: boolean;
}) {
  const total = excludedTotal(data.excluded_counts);
  if (total === 0 && data.excluded.length === 0) return null;
  const count = Math.max(total, data.excluded.length);
  return (
    <details open={open} className="group border-2 border-dashed border-superficie-borde bg-superficie-panel px-5 py-3">
      <summary className="flex min-h-11 cursor-pointer flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span className="font-bold">
          {count === 1
            ? "1 estrategia descartada, con su regla o motivo"
            : `${count} estrategias descartadas, cada una con su regla o motivo`}
        </span>
        <span className={`${LINK} group-open:hidden`}>Ver por qué</span>
        <span className={`${LINK} hidden group-open:inline`}>Ocultar</span>
      </summary>
      <div className="flex flex-col gap-3 pt-3 pb-2">
        {data.excluded.length < count && (
          <p className="text-[15px] text-texto-secundario">
            Aquí van las primeras {data.excluded.length}. En total se descartaron {excludedBreakdown(data.excluded_counts)}.
          </p>
        )}
        <ul className="flex flex-col">
          {data.excluded.map((item, i) => (
            <ExcludedItem key={`${item.crop_ids.join("-")}-${i}`} item={item} names={names} version={version} />
          ))}
        </ul>
      </div>
    </details>
  );
}

function ExcludedItem({ item, names, version }: { item: Exclusion; names: Map<string, string>; version: Version | undefined }) {
  const source = sourcesText(item.source_ids, version);
  return (
    <li className="flex min-w-0 gap-3 border-t-2 border-superficie-borde py-3">
      <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 size-5 shrink-0 text-texto-principal">
        <rect x="1" y="1" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M5 5 L15 15 M15 5 L5 15" stroke="currentColor" strokeWidth="2" />
      </svg>
      <div className="flex min-w-0 flex-col gap-0.5 leading-snug">
        <p className="font-bold break-words">{sequence(item.crop_ids, names)}</p>
        <p className="text-[15px] font-bold">{exclusionTitle(item)}</p>
        <p className="text-[15px]">{item.reason}</p>
        {source && <p className="text-[14px] text-texto-secundario">Fuente: {source}</p>}
      </div>
    </li>
  );
}

function errorText(error: Error): string {
  if (error instanceof ApiError && error.status === 422) return explain422(error.message);
  if (error instanceof ApiError && error.status === 501)
    return "El cálculo de las estrategias todavía no está listo en el servidor. Intente más tarde.";
  return error.message;
}
