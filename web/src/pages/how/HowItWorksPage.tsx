import { t } from "@/lib/i18n";
import { ApiLanguageNotice } from "@/components/ui/ApiLanguageNotice";
import { useTranslation } from "react-i18next";
import { useRef, type ReactNode } from "react";
import { Link } from "@/components/layout/LanguageLink";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { SmoothScroll } from "@/components/layout/SmoothScroll";
import { TopBar } from "@/components/layout/TopBar";
import type { MascotMood } from "@/components/mascot/Mascot";
import { MascotFlyer, MascotGuide, MascotSlot } from "@/components/mascot/MascotGuide";
import { Card } from "@/components/ui/Card";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { Spinner } from "@/components/ui/Spinner";
import { StateCard } from "@/components/ui/StateCard";
import { TrafficLightBadge, type Light } from "@/components/ui/TrafficLightBadge";
import { P0_SIGNALS, SIGNAL_NAME } from "@/features/diagnosis/signals";
import { useVersion, type Version } from "@/features/version";
import { useActiveSection } from "@/hooks/useActiveSection";
import { useAnimated } from "@/hooks/useLightMode";
import { useMotionEffect } from "@/hooks/useMotionEffect";
import { gsap } from "@/lib/motion";
import { BANDS, NEVER, SECTION_MOODS, STEPS, STOPS_BASE, STOPS_WITH_DATA, type StopId } from "./content";

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

/** El título de una sección con el lugar de la mascota a la izquierda: la mascota llega y señala la sección. */
function SectionTitle({ title, titleId, sub, stop }: { title: string; titleId?: string; sub?: string; stop: keyof typeof SECTION_MOODS }) {
  useTranslation();
  return (
    <div className="flex items-center gap-4 md:gap-6">
      <MascotSlot id={stop} mood={SECTION_MOODS[stop]} className="w-[72px] md:w-[120px]" />
      <div className="flex max-w-[880px] min-w-0 flex-col gap-2">
        <h2 id={titleId} className="text-[clamp(1.5rem,3vw,2rem)]">
          {title}
        </h2>
        {sub && <p className="text-texto-secundario">{sub}</p>}
      </div>
    </div>
  );
}

/**
 * Un tramo del camino de «Cómo se decide»: el lugar de la mascota a la izquierda y la tarjeta numerada a la derecha. La mascota señala la tarjeta (su brazo apunta a la derecha); sin
 * globo, porque la tarjeta ya lo explica. En el celular, la mascota va encima de la tarjeta.
 */
function PathStop({ stop, mood, children }: { stop: StopId; mood: MascotMood; children: ReactNode }) {
  useTranslation();
  return (
    <li id={stop} data-reveal-item className="flex scroll-mt-32 flex-col gap-2 md:flex-row md:items-center md:gap-6">
      <MascotSlot id={stop} mood={mood} className="w-[72px] md:w-[120px]" />
      <div className="min-w-0 md:max-w-[880px] md:flex-1">{children}</div>
    </li>
  );
}

const CELL = "block py-1 pr-4 align-top [overflow-wrap:anywhere] md:table-cell md:py-3";

function SourceRows({ group, sources }: { group: string; sources: Source[] }) {
  useTranslation();
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
            <span className="font-bold md:hidden">{t("pages.how.HowItWorksPage.coverage")} </span>
            {s.coverage ?? t("features.diagnosis.signals.noData")}
          </td>
          <td className={`${CELL} md:w-[17%]`}>
            <span className="font-bold md:hidden">{t("pages.how.HowItWorksPage.period")} </span>
            {s.period_covered ?? t("features.diagnosis.signals.noData")}
          </td>
          <td className={`${CELL} text-sm`}>
            <span className="font-bold md:hidden">{t("pages.how.HowItWorksPage.license")} </span>
            {s.license ?? t("pages.how.HowItWorksPage.noExplicitLicenseFiguresUsedWithAttribution")}
          </td>
        </tr>
      ))}
    </tbody>
  );
}

function SourceTable({ group, sources }: { group: string; sources: Source[] }) {
  useTranslation();
  return (
    <table data-sources className="block w-full border-collapse text-left md:table md:table-fixed">
      <thead className="hidden md:table-header-group">
        <tr className="text-sm text-texto-secundario">
          <th scope="col" className="pr-4 pb-2 font-bold">
            {t("pages.how.HowItWorksPage.source")}
          </th>
          <th scope="col" className="pr-4 pb-2 font-bold">
            {t("pages.how.HowItWorksPage.coverage2")}
          </th>
          <th scope="col" className="pr-4 pb-2 font-bold">
            {t("pages.how.HowItWorksPage.period2")}
          </th>
          <th scope="col" className="pb-2 font-bold">
            {t("pages.how.HowItWorksPage.license2")}
          </th>
        </tr>
      </thead>
      <SourceRows group={group} sources={sources} />
    </table>
  );
}

function Sources({ version }: { version: Version }) {
  useTranslation();
  const { nasa, others } = splitSources(version.sources);
  if (!nasa.length && !others.length) {
    return (
      <StateCard
        dashed
        mood="no_data"
        title={t("pages.how.HowItWorksPage.noPublishedSources")}
        description={t("pages.how.HowItWorksPage.noDatasetHasBeenPublishedOnThis")}
      />
    );
  }
  return (
    <Card>
      {nasa.length > 0 && <SourceTable group={t("how.nasaGroup")} sources={nasa} />}
      {others.length > 0 && (
        // Las demás fuentes son muchas (cada ficha cita las suyas): se abren a pedido, para que la NASA quede a la vista.
        <details className="group">
          <summary className={`${LINK} inline-flex min-h-11 cursor-pointer items-center`}>
            {t("pages.how.HowItWorksPage.viewThe")} {others.length} {t("pages.how.HowItWorksPage.cropSoilMunicipalityAndMarketSources")}
          </summary>
          <SourceTable group={t("how.otherGroup")} sources={others} />
        </details>
      )}
      <p className="text-sm text-texto-secundario">{t("pages.how.HowItWorksPage.nasaPowerIsAReanalysisAModel")}</p>
    </Card>
  );
}

function Weights({ version }: { version: Version }) {
  useTranslation();
  return (
    <Card>
      <ApiLanguageNotice />
      <ul data-reveal className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {P0_SIGNALS.map((key) => (
          <li key={key} data-reveal-item className="flex min-w-0 flex-col gap-2">
            <span className="flex items-center gap-3">
              <SignalIcon signal={key} />
              <span className="flex flex-col">
                <span className="font-bold">{SIGNAL_NAME()[key]}</span>
                <span className="[font-family:var(--font-titulos)] text-[1.375rem] leading-tight font-semibold">
                  {version.default_weights[key] ?? 0} {t("pages.how.HowItWorksPage.outOf5")}
                </span>
              </span>
            </span>
            {version.weights_reasons[key] && (
              <span lang="es" className="text-sm text-texto-secundario">
                {version.weights_reasons[key]}
              </span>
            )}
          </li>
        ))}
      </ul>
      <p className="text-texto-secundario">
        {t("pages.how.HowItWorksPage.severeWaterFrostOrHeatRiskAlways")} {version.weights_version}
        {t("pages.how.HowItWorksPage.notAgronomicDataYouCanChangeThem")}
      </p>
    </Card>
  );
}

function versionLine(version: Version): string {
  const parts = [
    version.dataset_version
      ? t("pages.how.HowItWorksPage.data", { v0: version.dataset_version })
      : t("pages.how.HowItWorksPage.noPublishedDataset"),
    version.rules_version ? t("pages.how.HowItWorksPage.rules", { v0: version.rules_version }) : null,
    version.region ? t("pages.how.HowItWorksPage.region", { v0: version.region }) : null,
  ];
  return t("pages.how.HowItWorksPage.eachResultIdentifiesTheVersionUsed", { v0: parts.filter(Boolean).join(" · ") });
}

/**
 * «¿Cómo funciona y de dónde sale esto?» (HU-122, HU-198): cómo se decide, los pesos por defecto con su porqué, las
 * fuentes con su licencia y la versión de los datos, y lo que AgroSense no hace. Lo que cambia sale de GET /version;
 * nada se inventa (R5). Diseño: design/pantallas/transversal.py, `how`. Es una página quieta: se ve igual en modo
 * ligero.
 */
export function HowItWorksPage() {
  useTranslation();
  const version = useVersion();
  const animated = useAnimated();
  const root = useRef<HTMLDivElement>(null);
  const hasData = Boolean(version.data);
  // Las paradas de «Pesos» y «Fuentes» llegan con /version: con otra lista, la sección activa las vuelve a observar.
  const active = useActiveSection(hasData ? STOPS_WITH_DATA : STOPS_BASE) as StopId;

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
    <SmoothScroll enabled={animated}>
      <MascotGuide active={active} flying={animated}>
        <div ref={root} className="min-h-svh bg-paleta-niebla">
          <title>{t("pages.how.HowItWorksPage.howDoesItWorkAgrosense")}</title>
          <TopBar />
          <main className="container-page flex flex-col gap-12 pt-[112px] pb-40 md:pt-[128px] md:pb-48">
            <div id="inicio" className="flex scroll-mt-32 items-start justify-between gap-8">
              <header data-intro className="flex max-w-[880px] min-w-0 flex-col gap-3">
                <h1 className="text-[clamp(1.75rem,4vw,3rem)]">{t("pages.how.HowItWorksPage.howDoesItWork")}</h1>
                <p className="text-[clamp(1rem,1.6vw,1.125rem)]">
                  {t("pages.how.HowItWorksPage.agrosenseExaminesYourAreasHistoryUsingNasa")}
                </p>
              </header>
              <MascotSlot id="inicio" mood="guide" className="hidden w-[200px] lg:block" />
            </div>

            <section className="flex flex-col gap-8" aria-labelledby="como-se-decide-titulo">
              <h2 id="como-se-decide-titulo" className="text-[clamp(1.5rem,3vw,2rem)]">
                {t("pages.how.HowItWorksPage.howDecisionsAreMade")}
              </h2>
              <ol data-reveal className="flex flex-col gap-8">
                {STEPS().map((step, i) => (
                  <PathStop key={step.id} stop={step.id} mood={step.mood}>
                    <Card>
                      <span
                        aria-hidden="true"
                        className="inline-flex size-10 shrink-0 items-center justify-center self-start bg-paleta-calabaza font-bold"
                      >
                        {i + 1}
                      </span>
                      <h3 className="min-w-0 text-[1.125rem]">{step.title}</h3>
                      <p>{step.body}</p>
                    </Card>
                  </PathStop>
                ))}
              </ol>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <Card>
                  <h3 className="text-[clamp(1.125rem,2vw,1.25rem)]">{t("pages.how.HowItWorksPage.fromScoreToLevel")}</h3>
                  <ul data-bands className="flex gap-[3px]">
                    {BANDS().map((band) => (
                      <li
                        key={band.label}
                        className={`flex min-w-0 flex-col items-center px-1 py-2 text-center text-sm font-bold ${band.ink}`}
                        style={{ background: band.fill, flexGrow: band.to - band.from + 1, flexBasis: 0 }}
                      >
                        {band.label}
                        <span className="font-normal">
                          {band.from} {t("pages.farm.LotPage.to")} {band.to}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="text-texto-secundario">{t("pages.how.HowItWorksPage.aSignalWithoutDataHasNoScore")}</p>
                </Card>

                <Card>
                  <h3 className="text-[clamp(1.125rem,2vw,1.25rem)]">{t("pages.how.HowItWorksPage.theTrafficLights")}</h3>
                  <ul className="flex flex-wrap gap-4">
                    {LIGHTS.map((light) => (
                      <li key={light}>
                        <TrafficLightBadge light={light} />
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>
            </section>

            {version.isPending && (
              <p role="status" className="flex items-center gap-3 text-texto-secundario">
                <Spinner /> {t("pages.how.HowItWorksPage.loadingWeightsSourcesAndDataVersion")}
              </p>
            )}
            {version.isError && (
              <StateCard
                title={t("pages.how.HowItWorksPage.weCouldNotLoadTheSources")}
                description={t("pages.how.HowItWorksPage.defaultWeightsSourcesAndTheDataVersion")}
                actions={[{ label: t("pages.account.PrioritiesCard.tryAgain"), onClick: () => void version.refetch() }]}
              />
            )}
            {version.data && (
              <>
                <section id="pesos" className="flex scroll-mt-32 flex-col gap-6" aria-label={t("pages.how.HowItWorksPage.defaultWeights")}>
                  <SectionTitle stop="pesos" title={t("pages.how.HowItWorksPage.defaultWeights")} sub={t("how.weightsIntro")} />
                  <Weights version={version.data} />
                </section>
                <section
                  id="fuentes"
                  className="flex scroll-mt-32 flex-col gap-6"
                  aria-label={t("pages.how.HowItWorksPage.sourcesAndVersion")}
                >
                  <SectionTitle stop="fuentes" title={t("pages.how.HowItWorksPage.sourcesAndVersion")} sub={versionLine(version.data)} />
                  <Sources version={version.data} />
                </section>
              </>
            )}

            <section id="no-hace" className="flex scroll-mt-32 flex-col gap-6" aria-labelledby="no-hace-titulo">
              <SectionTitle stop="no-hace" titleId="no-hace-titulo" title={t("pages.how.HowItWorksPage.whatAgrosenseDoesNotDo")} />
              <Card>
                <ul data-reveal className="flex flex-col gap-3">
                  {NEVER().map((item) => (
                    <li key={item} data-reveal-item className="flex gap-3">
                      <span aria-hidden="true" className="mt-1.5 size-4 shrink-0 bg-oscuro-rojo" />
                      <span className="min-w-0">{item}</span>
                    </li>
                  ))}
                </ul>
              </Card>
              <p className="flex flex-wrap gap-x-8 gap-y-3">
                <Link to={PATHS.consult} className={`${LINK} inline-flex min-h-11 items-center`}>
                  {t("pages.how.HowItWorksPage.exploreStrategies")}
                </Link>
                <Link to={PATHS.dataPolicy} className={`${LINK} inline-flex min-h-11 items-center`}>
                  {t("pages.how.HowItWorksPage.dataPolicy")}
                </Link>
              </p>
            </section>
          </main>
          <Footer aside={<MascotSlot id="pie" mood="idle" className="w-[84px]" />} />
          <MascotFlyer />
        </div>
      </MascotGuide>
    </SmoothScroll>
  );
}
