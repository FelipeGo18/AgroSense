import { Link, useNavigate } from "react-router";
import { PATHS } from "@/app/paths";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { ExampleLabel } from "@/components/ui/Labels";
import { harvestNote, useMunicipalitySoil } from "@/features/diagnosis/signals";
import { formatDate, todayIso, type SowPlan } from "@/features/farm/seasons";
import {
  cycleParams,
  strategyKey,
  useTrends,
  useWaterPlan,
  waterRequest,
  weeksBetween,
  windowSpans,
  type OpenCycle,
} from "@/features/strategies/cycle";
import { cycleKind, sequence, type Cycle } from "@/features/strategies/strategies";
import type { Version } from "@/features/version";
import { DiagnosisLights } from "@/pages/diagnosis/Lights";
import { SignalList } from "@/pages/diagnosis/SignalList";
import { SuitabilityScore } from "@/pages/diagnosis/Suitability";
import { CycleWater } from "./CycleWater";
import { GreenChart } from "./GreenChart";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

export interface CycleViewProps {
  open: OpenCycle;
  params: URLSearchParams;
  backTo: string;
  municipalityId: string;
  irrigated: boolean | null | undefined;
  /** El área de la entrada: la escrita sin cuenta, o la del terreno del lote. Nula si no se sabe. */
  areaHa: number | null;
  names: Map<string, string>;
  kinds: Map<string, string>;
  version: Version | undefined;
  signedIn: boolean;
  /** Las versiones de la respuesta de las estrategias (R4): un descanso no tiene diagnóstico, pero sí versión. */
  versions: { dataset: string | null; rules: string | null };
  /** Con lote: dónde registrar la siembra del primer ciclo y de qué siembras viene ese terreno. */
  lot: { lotId: string; follows: string[] } | null;
}

/**
 * El ciclo de una estrategia (HU-215; diseño `design/pantallas/ciclo.py`). No pide un diagnóstico aparte: usa el
 * `diagnosis` que vino con el ciclo y las mismas piezas del resultado del diagnóstico (luces, aptitud y señales). Suma el
 * agua del ciclo, la humedad del suelo de la zona y cuándo suele estar verde el campo. Un descanso no tiene semáforo.
 */
export function CycleView({
  open,
  params,
  backTo,
  municipalityId,
  irrigated,
  areaHa,
  names,
  kinds,
  version,
  signedIn,
  versions,
  lot,
}: CycleViewProps) {
  const { strategy, cycle } = open;
  const key = strategyKey(strategy);
  const total = strategy.cycles.length;
  const name = (c: Cycle) => names.get(c.crop_id) ?? c.crop_id;
  const kind = cycleKind(cycle.crop_id, kinds);
  const fallow = kind === "fallow";
  const link = (n: number) => `${PATHS.consult}?${cycleParams(params, key, n)}`;
  const previous = strategy.cycles.find((c) => c.cycle === cycle.cycle - 1);
  const next = strategy.cycles.find((c) => c.cycle === cycle.cycle + 1);
  const diagnosis = cycle.diagnosis;
  const example = diagnosis?.versions.dataset === "ejemplo";

  return (
    <div className="flex min-w-0 flex-col gap-10">
      <title>{`Ciclo ${cycle.cycle} de ${total}: ${name(cycle)} · AgroSense`}</title>
      <div className="max-w-[960px]">
        <Card bodyClassName="gap-5">
          <Link to={backTo} className={`${LINK} inline-flex min-h-11 items-center self-start`}>
            ‹ Volver a las estrategias
          </Link>
          <Eyebrow>
            {strategy.kind === "current" ? "Lo que siembra hoy" : "Estrategia"} · {sequence(strategy.crop_ids, names)}
          </Eyebrow>
          <nav aria-label="Ciclos de la estrategia">
            <ol className={`grid grid-cols-1 gap-2 ${total === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
              {strategy.cycles.map((c) => {
                const current = c.cycle === cycle.cycle;
                return (
                  <li key={c.cycle}>
                    <Link
                      to={link(c.cycle)}
                      aria-current={current ? "page" : undefined}
                      className={`flex min-h-11 items-center justify-center border-2 px-3 py-2 text-center font-bold ${
                        current ? "border-texto-principal bg-texto-principal text-white" : "border-superficie-borde bg-superficie-panel"
                      }`}
                    >
                      {c.cycle} · {name(c)}
                    </Link>
                  </li>
                );
              })}
            </ol>
          </nav>
          <h1 className="text-[clamp(1.6rem,3.5vw,2.5rem)] leading-tight">
            Ciclo {cycle.cycle} de {total}: {name(cycle).toLowerCase()}
          </h1>

          {fallow ? (
            <Rest cycle={cycle} reasons={strategy.reasons} />
          ) : (
            <>
              <div className="flex flex-col gap-0.5">
                <p className="font-bold">
                  Siembra el {formatDate(cycle.sowing_date)} → {kind === "cover" ? "se incorpora" : "cosecha estimada"} ~
                  {formatDate(cycle.harvest_estimate)}
                </p>
                <p className="text-[15px] text-texto-secundario">{harvestNote(cycle.harvest_basis)}</p>
              </div>
              {example && <ExampleLabel>respuesta simulada</ExampleLabel>}
              {diagnosis ? (
                <DiagnosisLights overall={diagnosis.overall} overallDefault={diagnosis.overall_default} weights={diagnosis.weights} />
              ) : (
                <p className="border-2 border-dashed border-superficie-borde px-4 py-3">
                  <span aria-hidden="true">? </span>Este ciclo no trae su diagnóstico: no se puede decir cómo le va al cultivo en esa
                  ventana.
                </p>
              )}
              {cycle.cycle === 1 && (
                <Register cycle={cycle} name={name(cycle)} signedIn={signedIn} lot={lot} areaHa={areaHa} irrigated={irrigated} />
              )}
            </>
          )}

          <div className="flex flex-wrap justify-between gap-3 border-t-2 border-superficie-borde pt-3">
            {previous ? (
              <Link to={link(previous.cycle)} className={`${LINK} inline-flex min-h-11 items-center`}>
                ‹ Ciclo {previous.cycle}: {name(previous).toLowerCase()}
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link to={link(next.cycle)} className={`${LINK} inline-flex min-h-11 items-center`}>
                Ciclo {next.cycle}: {name(next).toLowerCase()} ›
              </Link>
            )}
          </div>
        </Card>
      </div>

      {fallow
        ? next && (
            <div className="max-w-[960px]">
              <AfterRest next={next} name={name(next)} to={link(next.cycle)} />
            </div>
          )
        : diagnosis && (
            <CycleDetails
              cycle={cycle}
              cropName={name(cycle)}
              diagnosis={diagnosis}
              municipalityId={municipalityId}
              irrigated={irrigated}
              areaHa={areaHa}
              version={version}
            />
          )}

      <div className="flex flex-col gap-3">
        <p className="border-2 border-oscuro-oliva bg-[#EEF2E4] px-4 py-3 font-bold">Es información para decidir. La decisión es suya.</p>
        <p className="text-[15px] text-texto-secundario">
          Datos {(diagnosis?.versions ?? versions).dataset ?? "sin versión"} · Reglas{" "}
          {(diagnosis?.versions ?? versions).rules ?? "sin versión"}
        </p>
      </div>
    </div>
  );
}

/** Un descanso no tiene semáforo: dice cuánto dura y por qué la estrategia lo propone (sus razones, con regla y fuente). */
function Rest({ cycle, reasons }: { cycle: Cycle; reasons: string[] }) {
  return (
    <>
      <p className="font-bold">
        Del {formatDate(cycle.sowing_date)} al {formatDate(cycle.harvest_estimate)} ·{" "}
        {weeksBetween(cycle.sowing_date, cycle.harvest_estimate)} semanas sin sembrar.
      </p>
      <div className="flex items-start gap-3 border-2 border-dashed border-superficie-borde px-4 py-3">
        <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 size-5 shrink-0">
          <polygon points="10,1 19,10 10,19 1,10" fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
        <div className="flex flex-col gap-1">
          <p className="font-bold">Sin semáforo: en un descanso no se siembra</p>
          <p className="text-[15px] text-texto-secundario">No hay fecha que evaluar ni señales que calificar.</p>
        </div>
      </div>
      {reasons.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="font-bold">Por qué la estrategia lo propone</p>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function AfterRest({ next, name, to }: { next: Cycle; name: string; to: string }) {
  return (
    <Card bodyClassName="gap-2">
      <h2 className="text-[clamp(1.15rem,2.5vw,1.4rem)]">Después del descanso</h2>
      <p>
        El ciclo {next.cycle} es {name.toLowerCase()}, sembrando el {formatDate(next.sowing_date)}.
      </p>
      <Link to={to} className={`${LINK} inline-flex min-h-11 items-center self-start`}>
        Ver el ciclo {next.cycle}: {name.toLowerCase()}
      </Link>
    </Card>
  );
}

/**
 * Registrar la siembra del primer ciclo (HU-165). Con cuenta y lote, lleva al formulario de siembra ya armado y con el
 * diagnóstico que vio. La siembra se registra cuando ya se sembró: si la fecha todavía no llega, se dice cuándo. Sin
 * cuenta, crear una; con cuenta pero sin lote, consultar desde uno de sus lotes.
 */
function Register({
  cycle,
  name,
  signedIn,
  lot,
  areaHa,
  irrigated,
}: {
  cycle: Cycle;
  name: string;
  signedIn: boolean;
  lot: CycleViewProps["lot"];
  areaHa: number | null;
  irrigated: boolean | null | undefined;
}) {
  const navigate = useNavigate();
  if (!signedIn) {
    return (
      <ButtonLink to={PATHS.signup} className="w-full sm:w-auto sm:self-start">
        Crear cuenta y registrarla
      </ButtonLink>
    );
  }
  if (!lot) {
    return (
      <p className="text-[15px]">
        Para registrar esta siembra, consulte las estrategias desde uno de sus lotes.{" "}
        <Link to={PATHS.farm} className={LINK}>
          Ir a Mi finca
        </Link>
      </p>
    );
  }
  if (cycle.sowing_date > todayIso()) {
    return (
      <p className="text-[15px]">
        Cuando la siembre, desde el {formatDate(cycle.sowing_date)}, regístrela en su lote.{" "}
        <Link to={PATHS.lot(lot.lotId)} className={LINK}>
          Ir a mi lote
        </Link>
      </p>
    );
  }
  const diagnosis = cycle.diagnosis;
  const plan: SowPlan = {
    crop_id: cycle.crop_id,
    sowing_date: cycle.sowing_date,
    follows_season_ids: lot.follows,
    area_ha: areaHa ?? 0,
    diagnosis: {
      diagnosis_light: diagnosis?.overall.light ?? null,
      diagnosis_light_default: diagnosis?.overall_default.light ?? null,
      diagnosis_action: diagnosis?.overall.action ?? null,
      diagnosis_weights: diagnosis?.weights ? { ...diagnosis.weights } : null,
      diagnosis_irrigated: irrigated ?? null,
      dataset_version: diagnosis?.versions.dataset ?? null,
      rules_version: diagnosis?.versions.rules ?? null,
    },
  };
  return (
    <Button className="w-full sm:w-auto sm:self-start" onClick={() => void navigate(PATHS.sow(lot.lotId), { state: { plan } })}>
      Registrar esta siembra de {name.toLowerCase()}
    </Button>
  );
}

function CycleDetails({
  cycle,
  cropName,
  diagnosis,
  municipalityId,
  irrigated,
  areaHa,
  version,
}: {
  cycle: Cycle;
  cropName: string;
  diagnosis: NonNullable<Cycle["diagnosis"]>;
  municipalityId: string;
  irrigated: boolean | null | undefined;
  areaHa: number | null;
  version: Version | undefined;
}) {
  const soil = useMunicipalitySoil(diagnosis.signals?.soil ? municipalityId : null);
  const water = useWaterPlan(waterRequest(municipalityId, areaHa, cycle));
  const trends = useTrends(municipalityId, cycle.crop_id, cycle.sowing_date);
  const ndvi = trends.data?.ndvi;
  const changes = `${PATHS.changes}?${new URLSearchParams({ municipio: municipalityId, cultivo: cycle.crop_id })}`;
  return (
    <>
      <section
        aria-labelledby="aptitud"
        className="flex max-w-[960px] min-w-0 flex-col gap-2 border-2 border-oscuro-oliva/40 bg-[#EEF2E4] px-5 py-4"
      >
        <h2 id="aptitud" className="text-[clamp(1.1rem,2.5vw,1.3rem)]">
          {diagnosis.suitability.level === "not_suitable"
            ? "No se da en su zona"
            : diagnosis.suitability.level === "suitable"
              ? "Se da en su zona"
              : "Aptitud sin datos suficientes"}
        </h2>
        {diagnosis.suitability.reasons.map((reason) => (
          <p key={reason} className="text-[15px]">
            {reason}
          </p>
        ))}
        <SuitabilityScore score={diagnosis.suitability.score} />
      </section>

      {diagnosis.signals && (
        <section aria-labelledby="senales" className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 id="senales" className="text-[clamp(1.25rem,3vw,1.75rem)]">
              Las seis señales de este ciclo
            </h2>
            <p className="max-w-[880px] text-texto-secundario">
              Las mismas del diagnóstico, calificadas de 0 a 100 frente a lo que necesita {cropName.toLowerCase()}. Ninguna se promedia con
              otra.
            </p>
          </div>
          <SignalList
            signals={diagnosis.signals}
            limiting={diagnosis.overall.limiting_signal}
            irrigated={irrigated}
            weights={diagnosis.weights}
            supplySemester={diagnosis.window?.supply_semester}
            soil={soil.data}
            version={version}
          />
        </section>
      )}

      <CycleWater water={water} cropName={cropName} areaHa={areaHa} irrigated={irrigated} version={version} />

      <section aria-labelledby="verdor" className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="verdor" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            Verdor de la zona
          </h2>
          <p className="font-bold">Cuándo suele estar verde el campo en su zona · MODIS, 250 m</p>
        </div>
        <Card bodyClassName="gap-3">
          {trends.isPending ? (
            <p role="status">Cargando el verdor…</p>
          ) : !ndvi || ndvi.status !== "available" || ndvi.points.every((p) => p.ndvi_normal === null) ? (
            <p className="text-texto-secundario">
              <span aria-hidden="true">? </span>Sin datos suficientes del verdor de su zona.
            </p>
          ) : (
            <>
              <GreenChart points={ndvi.points} spans={windowSpans(cycle.sowing_date, cycle.harvest_estimate)} />
              <p className="text-[14px] text-texto-secundario">
                Dato de la zona, a 250 m: mezcla cultivos, pastos y bosque. No es una medición de su lote ni dice cómo le irá a su cultivo.
                {ndvi.quality === "partial" ? " Hay periodos con pocos datos." : ""}
              </p>
            </>
          )}
        </Card>
      </section>

      <Card bodyClassName="gap-2">
        <h2 className="text-[clamp(1.1rem,2.5vw,1.3rem)]">¿Qué cambió en su zona?</h2>
        <p>
          Heladas, lluvia y calor de dos periodos de la historia de su zona, y cómo se movieron las mejores fechas de{" "}
          {cropName.toLowerCase()}. No es un pronóstico.
        </p>
        <Link to={changes} className={`${LINK} inline-flex min-h-11 items-center self-start`}>
          Ver qué cambió en su zona
        </Link>
      </Card>

      {diagnosis.limitations.length > 0 && (
        <section aria-labelledby="limitaciones-ciclo" className="flex max-w-[880px] min-w-0 flex-col gap-2">
          <h2 id="limitaciones-ciclo" className="text-[clamp(1.1rem,2.5vw,1.35rem)]">
            Limitaciones de este ciclo
          </h2>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {diagnosis.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
