import { useRef } from "react";
import { Link } from "react-router";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot } from "@/components/mascot/Mascot";
import { Card } from "@/components/ui/Card";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { Spinner } from "@/components/ui/Spinner";
import { StateCard } from "@/components/ui/StateCard";
import { TrafficLightBadge, type Light } from "@/components/ui/TrafficLightBadge";
import { P0_SIGNALS, SIGNAL_NAME } from "@/features/diagnosis/signals";
import { useVersion, type Version } from "@/features/version";
import { useAnimated } from "@/hooks/useLightMode";
import { useMotionEffect } from "@/hooks/useMotionEffect";
import { gsap } from "@/lib/motion";
import { BANDS, NEVER, STEPS } from "./content";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";
const LIGHTS: Light[] = ["green", "yellow", "red", "not_evaluable"];

/** Una fila de la tabla `sources` tal como la publica el dataset (GET /version). */
interface Source {
  source_id: string;
  name: string;
  institution: string;
  url: string | null;
  coverage: string | null;
  period_covered: string | null;
  license: string | null;
}

const text = (value: unknown): string | null => (typeof value === "string" && value.trim() ? value : null);

function toSource(row: Record<string, unknown>): Source | null {
  const source_id = text(row.source_id);
  const name = text(row.name);
  if (!source_id || !name) return null;
  return {
    source_id,
    name,
    institution: text(row.institution) ?? "",
    url: text(row.url),
    coverage: text(row.coverage),
    period_covered: text(row.period_covered),
    license: text(row.license),
  };
}

/** La NASA es el núcleo (decisión 12): sus productos van primero; las demás fuentes, después. */
export function splitSources(rows: Version["sources"]): { nasa: Source[]; others: Source[] } {
  const sources = rows.map(toSource).filter((s): s is Source => s !== null);
  const isNasa = (s: Source) => /\bNASA\b/.test(`${s.name} ${s.institution}`);
  const byName = (a: Source, b: Source) => a.name.localeCompare(b.name, "es");
  return { nasa: sources.filter(isNasa).sort(byName), others: sources.filter((s) => !isNasa(s)).sort(byName) };
}

function SectionTitle({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="flex max-w-[880px] flex-col gap-2">
      <h2 className="text-[clamp(1.5rem,3vw,2rem)]">{title}</h2>
      {sub && <p className="text-texto-secundario">{sub}</p>}
    </div>
  );
}

const CELL = "block py-1 pr-4 align-top [overflow-wrap:anywhere] md:table-cell md:py-3";

function SourceRows({ group, sources }: { group: string; sources: Source[] }) {
  return (
    <tbody className="block md:table-row-group">
      <tr className="block md:table-row">
        <th
          colSpan={4}
          scope="colgroup"
          className="block pt-5 pb-1 text-left text-sm font-bold tracking-wide text-texto-secundario uppercase md:table-cell"
        >
          {group}
        </th>
      </tr>
      {sources.map((s) => (
        <tr key={s.source_id} className="block border-t-2 border-paleta-niebla py-3 md:table-row md:py-0">
          <td className={`${CELL} min-w-0 md:w-[38%]`}>
            <span className="block font-bold">
              {s.url ? (
                <a href={s.url} target="_blank" rel="noreferrer" className={`${LINK} inline-flex min-h-11 items-center`}>
                  {s.name}
                </a>
              ) : (
                s.name
              )}
            </span>
            {s.institution && <span className="block text-sm text-texto-secundario">{s.institution}</span>}
          </td>
          <td className={`${CELL} md:w-[20%]`}>
            <span className="font-bold md:hidden">Cobertura: </span>
            {s.coverage ?? "Sin dato"}
          </td>
          <td className={`${CELL} md:w-[17%]`}>
            <span className="font-bold md:hidden">Periodo: </span>
            {s.period_covered ?? "Sin dato"}
          </td>
          <td className={`${CELL} text-sm`}>
            <span className="font-bold md:hidden">Licencia: </span>
            {s.license ?? "Sin licencia explícita: se usan cifras con su cita"}
          </td>
        </tr>
      ))}
    </tbody>
  );
}

function SourceTable({ group, sources }: { group: string; sources: Source[] }) {
  return (
    <table data-sources className="block w-full border-collapse text-left md:table md:table-fixed">
      <thead className="hidden md:table-header-group">
        <tr className="text-sm text-texto-secundario">
          <th scope="col" className="pr-4 pb-2 font-bold">
            Fuente
          </th>
          <th scope="col" className="pr-4 pb-2 font-bold">
            Cobertura
          </th>
          <th scope="col" className="pr-4 pb-2 font-bold">
            Periodo
          </th>
          <th scope="col" className="pb-2 font-bold">
            Licencia
          </th>
        </tr>
      </thead>
      <SourceRows group={group} sources={sources} />
    </table>
  );
}

function Sources({ version }: { version: Version }) {
  const { nasa, others } = splitSources(version.sources);
  if (!nasa.length && !others.length) {
    return (
      <StateCard
        dashed
        mood="no_data"
        title="Sin fuentes publicadas"
        description="Todavía no hay un dataset publicado en este servidor: no mostramos fuentes que no se están usando."
      />
    );
  }
  return (
    <Card>
      {nasa.length > 0 && <SourceTable group="Observaciones de la Tierra de la NASA" sources={nasa} />}
      {others.length > 0 && (
        // Las demás fuentes son muchas (cada ficha cita las suyas): se abren a pedido, para que la NASA quede a la vista.
        <details className="group">
          <summary className={`${LINK} inline-flex min-h-11 cursor-pointer items-center`}>
            Ver las {others.length} fuentes de cultivos, suelo, municipios y mercado
          </summary>
          <SourceTable group="Cultivos, suelo, municipios y mercado" sources={others} />
        </details>
      )}
      <p className="text-sm text-texto-secundario">
        NASA POWER es un reanálisis (un modelo con observaciones), no una medición directa de satélite; la lluvia y el verdor son de celdas
        de kilómetros o de 250 m: datos de la zona, no de su lote. Las fuentes de un mismo indicador se muestran juntas y nunca se mezclan.
      </p>
    </Card>
  );
}

function Weights({ version }: { version: Version }) {
  return (
    <Card>
      <ul data-reveal className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {P0_SIGNALS.map((key) => (
          <li key={key} data-reveal-item className="flex min-w-0 flex-col gap-2">
            <span className="flex items-center gap-3">
              <SignalIcon signal={key} />
              <span className="flex flex-col">
                <span className="font-bold">{SIGNAL_NAME[key]}</span>
                <span className="[font-family:var(--font-titulos)] text-[1.375rem] leading-tight font-semibold">
                  {version.default_weights[key] ?? 0} de 5
                </span>
              </span>
            </span>
            {version.weights_reasons[key] && <span className="text-sm text-texto-secundario">{version.weights_reasons[key]}</span>}
          </li>
        ))}
      </ul>
      <p className="text-texto-secundario">
        Un riesgo grave de agua, heladas o calor cuenta siempre, aunque el peso sea 0. Son criterio del equipo (versión{" "}
        {version.weights_version}), no un dato agronómico: usted los puede cambiar en sus prioridades.
      </p>
    </Card>
  );
}

function versionLine(version: Version): string {
  const parts = [
    version.dataset_version ? `Datos ${version.dataset_version}` : "Sin dataset publicado",
    version.rules_version ? `Reglas ${version.rules_version}` : null,
    version.region ? `Región: ${version.region}` : null,
  ];
  return `${parts.filter(Boolean).join(" · ")}. Cada respuesta dice qué versión usó.`;
}

/**
 * «¿Cómo funciona y de dónde sale esto?» (HU-122, HU-198): cómo se decide, los pesos por defecto con su porqué, las
 * fuentes con su licencia y la versión de los datos, y lo que AgroSense no hace. Lo que cambia sale de GET /version;
 * nada se inventa (R5). Diseño: design/pantallas/transversal.py, `how`. Es una página quieta: se ve igual en modo
 * ligero.
 */
export function HowItWorksPage() {
  const version = useVersion();
  const animated = useAnimated();
  const root = useRef<HTMLDivElement>(null);
  const hasData = Boolean(version.data);

  // Con movimiento: la cabecera entra de lado, las bandas de la nota crecen y cada grupo de tarjetas aparece uno tras otro
  // al llegar a la vista. En modo ligero no corre: todo se dibuja quieto y a la vista (web/CLAUDE.md, «Modo ligero»).
  // Corre otra vez cuando llegan los pesos y las fuentes, para animar solo lo que aún no se animó.
  useMotionEffect(
    () => {
      if (!animated || !root.current) return;
      const fresh = (selector: string) =>
        gsap.utils.toArray<HTMLElement>(selector, root.current).filter((el) => {
          // Lo que está dentro de una lista cerrada («Ver las … fuentes») no se anima: al abrirla, ya está a la vista.
          if (el.dataset.revealed || el.closest("details")) return false;
          el.dataset.revealed = "1";
          return true;
        });
      fresh("[data-intro]").forEach((el) =>
        gsap.from(el.children, {
          x: -28,
          autoAlpha: 0,
          duration: 0.6,
          ease: "power2.out",
          stagger: 0.1,
          clearProps: "transform,opacity,visibility",
        }),
      );
      fresh("[data-intro-mascot]").forEach((el) =>
        gsap.from(el, { y: -40, rotation: -8, autoAlpha: 0, duration: 0.9, ease: "back.out(1.6)", delay: 0.2, clearProps: "all" }),
      );
      fresh("[data-bands]").forEach((el) =>
        gsap.from(el.children, {
          scaleX: 0,
          transformOrigin: "left center",
          duration: 0.6,
          ease: "power3.out",
          stagger: 0.15,
          clearProps: "transform",
          scrollTrigger: { trigger: el, start: "top 90%", once: true },
        }),
      );
      fresh("[data-reveal]").forEach((el) =>
        gsap.from(el.querySelectorAll(":scope > [data-reveal-item]"), {
          y: 28,
          autoAlpha: 0,
          duration: 0.55,
          ease: "power2.out",
          stagger: 0.08,
          clearProps: "transform,opacity,visibility",
          scrollTrigger: { trigger: el, start: "top 88%", once: true },
        }),
      );
      fresh("[data-sources] tbody tr").forEach((el) =>
        gsap.from(el, {
          x: -16,
          autoAlpha: 0,
          duration: 0.4,
          ease: "power2.out",
          clearProps: "transform,opacity,visibility",
          scrollTrigger: { trigger: el, start: "top 95%", once: true },
        }),
      );
    },
    { scope: root, dependencies: [animated, hasData] },
  );

  return (
    <div ref={root} className="min-h-svh bg-paleta-niebla">
      <title>¿Cómo funciona? · AgroSense</title>
      <TopBar />
      <main className="container-page flex flex-col gap-12 pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        <div className="flex items-start justify-between gap-8">
          <header data-intro className="flex max-w-[880px] min-w-0 flex-col gap-3">
            <h1 className="text-[clamp(1.75rem,4vw,3rem)]">¿Cómo funciona?</h1>
            <p className="text-[clamp(1rem,1.6vw,1.125rem)]">
              AgroSense mira lo que ha pasado en su zona con observaciones de la Tierra de la NASA, datos abiertos y reglas que se pueden
              leer. No es un pronóstico: usted decide.
            </p>
          </header>
          <div data-intro-mascot className="hidden lg:block">
            <Mascot mood="guide" decorative lively={animated} className="h-auto w-[200px]" />
          </div>
        </div>

        <section className="flex flex-col gap-6" aria-labelledby="como-se-decide">
          <h2 id="como-se-decide" className="text-[clamp(1.5rem,3vw,2rem)]">
            Cómo se decide
          </h2>
          <ol data-reveal className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {STEPS.map((step, i) => (
              <li key={step.title} data-reveal-item className="flex">
                <Card className="w-full">
                  <span
                    aria-hidden="true"
                    className="inline-flex size-10 shrink-0 items-center justify-center self-start bg-paleta-calabaza font-bold"
                  >
                    {i + 1}
                  </span>
                  <h3 className="min-w-0 text-[1.125rem]">{step.title}</h3>
                  <p className="text-sm">{step.body}</p>
                </Card>
              </li>
            ))}
          </ol>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <h3 className="text-[clamp(1.125rem,2vw,1.25rem)]">De la nota al nivel</h3>
              <ul data-bands className="flex gap-[3px]">
                {BANDS.map((band) => (
                  <li
                    key={band.label}
                    className={`flex min-w-0 flex-col items-center px-1 py-2 text-center text-sm font-bold ${band.ink}`}
                    style={{ background: band.fill, flexGrow: band.to - band.from + 1, flexBasis: 0 }}
                  >
                    {band.label}
                    <span className="font-normal">
                      {band.from} a {band.to}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-texto-secundario">Una señal sin datos no tiene nota y no cuenta como riesgo.</p>
            </Card>
            <Card>
              <h3 className="text-[clamp(1.125rem,2vw,1.25rem)]">Las luces</h3>
              <ul data-reveal className="flex flex-wrap gap-4">
                {LIGHTS.map((light) => (
                  <li key={light} data-reveal-item>
                    <TrafficLightBadge light={light} />
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </section>

        {version.isPending && (
          <p role="status" className="flex items-center gap-3 text-texto-secundario">
            <Spinner /> Cargando los pesos, las fuentes y la versión de los datos…
          </p>
        )}
        {version.isError && (
          <StateCard
            title="No pudimos cargar las fuentes"
            description="Los pesos por defecto, las fuentes y la versión de los datos salen del servidor, que no respondió."
            actions={[{ label: "Volver a intentar", onClick: () => void version.refetch() }]}
          />
        )}
        {version.data && (
          <>
            <section className="flex flex-col gap-6" aria-label="Pesos por defecto">
              <SectionTitle title="Pesos por defecto" sub="Cuánto pesa cada señal si usted no cambia sus prioridades, y por qué." />
              <Weights version={version.data} />
            </section>
            <section className="flex flex-col gap-6" aria-label="Fuentes y versión">
              <SectionTitle title="Fuentes y versión" sub={versionLine(version.data)} />
              <Sources version={version.data} />
            </section>
          </>
        )}

        <section className="flex flex-col gap-6" aria-labelledby="no-hace">
          <h2 id="no-hace" className="text-[clamp(1.5rem,3vw,2rem)]">
            Lo que AgroSense no hace
          </h2>
          <Card>
            <ul data-reveal className="flex flex-col gap-3">
              {NEVER.map((item) => (
                <li key={item} data-reveal-item className="flex gap-3">
                  <span aria-hidden="true" className="mt-1.5 size-4 shrink-0 bg-oscuro-rojo" />
                  <span className="min-w-0">{item}</span>
                </li>
              ))}
            </ul>
          </Card>
          <p className="flex flex-wrap gap-x-8 gap-y-3">
            <Link to={PATHS.consult} className={`${LINK} inline-flex min-h-11 items-center`}>
              Consultar estrategias
            </Link>
            <Link to={PATHS.dataPolicy} className={`${LINK} inline-flex min-h-11 items-center`}>
              Política de datos
            </Link>
          </p>
        </section>
      </main>
      <Footer />
    </div>
  );
}
