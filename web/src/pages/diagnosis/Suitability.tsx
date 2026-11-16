import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { Link } from "@/components/layout/LanguageLink";
import { ButtonLink } from "@/components/ui/Button";
import { Seed } from "@/components/ui/PriorityControl";
import type { DiagnosisResponse } from "@/features/diagnosis/consult";
import { strategiesLink } from "@/features/diagnosis/lights";
import { SIGNAL_NAME } from "@/features/diagnosis/signals";
import { otherCropLink, seedsFor, suitabilityFacts, windowLink, type WindowSummary } from "@/features/diagnosis/windows";
import { formatDate } from "@/features/farm/seasons";

export const NOT_FORECAST = () => t("pages.diagnosis.Suitability.basedOnTheAreasHistoryThisIs");

/**
 * La nota de aptitud de 0 a 100 con su número y la escala de cinco semillas (HU-194). Es informativa: no es una señal
 * ni cambia la luz. Sin nota no se dibuja nada: cero semillas diría «no apto» (R1).
 */
export function SuitabilityScore({ score }: { score: number | null | undefined }) {
  useTranslation();
  const seeds = seedsFor(score);
  if (seeds === null || score === null || score === undefined) return null;
  const value = Math.round(score);
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <p>
        {t("pages.diagnosis.Suitability.areaSuitabilityForThisCrop")} <span className="font-bold">{value}</span>{" "}
        {t("pages.diagnosis.SignalList.outOf100")}
      </p>
      <div role="img" aria-label={t("pages.diagnosis.Suitability.outOf5Seeds", { v0: seeds })} className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className="size-7">
            <Seed filled={n <= seeds} />
          </span>
        ))}
      </div>
      <p className="text-[15px] text-texto-secundario">{t("pages.diagnosis.Suitability.thisIsInformationalItDoesNotChange")}</p>
    </div>
  );
}

/**
 * «Este cultivo no se da en su zona» (HU-194; `specs/05-frontend.md`, «Cultivo no apto»): un letrero propio, sin
 * semáforo, señales ni ventanas. La nota de aptitud, el dato con que se decidió, la razón con su fuente, y qué hacer:
 * elegir otro cultivo o ver las estrategias de rotación.
 */
export function NotSuitable({ data }: { data: DiagnosisResponse }) {
  useTranslation();
  const facts = suitabilityFacts(data.suitability);
  const reasons = data.suitability.reasons ?? [];
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <p className="flex items-center gap-3 font-titulos text-[clamp(1.4rem,3.5vw,2rem)] leading-tight font-semibold">
        <svg aria-hidden="true" viewBox="0 0 40 40" className="size-10 shrink-0">
          <polygon points="4,36 36,36 32,30 8,30" fill="var(--color-paleta-tierra)" />
          <polygon points="19,30 21,30 21,14 19,14" fill="var(--color-oscuro-brote)" />
          <polygon points="20,18 9,10 12,21" fill="var(--color-paleta-brote)" />
          <path d="M6 6 L34 34 M34 6 L6 34" stroke="var(--color-oscuro-rojo)" strokeWidth="4" strokeLinecap="round" />
        </svg>
        {t("pages.diagnosis.Suitability.thisCropIsUnsuitableForYourArea")}
      </p>
      <SuitabilityScore score={data.suitability.score} />
      {facts && <p>{facts}</p>}
      {reasons.length > 0 && (
        <ul className="flex list-disc flex-col gap-1 pl-5" aria-label={t("pages.diagnosis.Suitability.whyItIsUnsuitable")}>
          {reasons.map((reason) => (
            <li lang="es" key={reason}>
              {reason}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <ButtonLink to={otherCropLink(data.request)} className="w-full sm:w-auto">
          {t("pages.diagnosis.Suitability.chooseAnotherCrop")}
        </ButtonLink>
        <ButtonLink to={strategiesLink(data.request)} variant="secondary" className="w-full sm:w-auto">
          {t("pages.farm.LotPage.viewRotationStrategies")}
        </ButtonLink>
      </div>
    </div>
  );
}

/**
 * Las mejores ventanas de los próximos doce meses, cuando alguna luz dice «otra fecha» (HU-194). Cada una con su fecha
 * de siembra y su cosecha estimada, la nota de lo que más la limita (el número principal) y el promedio con sus
 * prioridades (secundario). Tocar una consulta el diagnóstico de esa fecha. Si no hay ninguna sin riesgo alto, se dice
 * y se ofrecen las estrategias, salvo que el resumen ya tenga ese botón (`strategiesShown`, cuando la otra luz dice
 * «rotar»): nunca dos botones iguales.
 */
export function BestWindows({ data, strategiesShown = false }: { data: DiagnosisResponse; strategiesShown?: boolean }) {
  useTranslation();
  const windows = data.best_windows ?? [];
  return (
    <section aria-labelledby="mejores-fechas" className="flex min-w-0 flex-col gap-3 border-t-2 border-superficie-borde pt-4">
      <h3 id="mejores-fechas" className="text-[clamp(1.1rem,2.5vw,1.35rem)]">
        {t("pages.diagnosis.Suitability.bestDatesOverTheNextTwelveMonths")}
      </h3>
      <p className="text-[15px] text-texto-secundario">{NOT_FORECAST()}</p>
      {windows.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {windows.map((window) => (
            <li key={window.sowing_start}>
              <WindowLink data={data} window={window} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="font-bold">{t("pages.diagnosis.Suitability.thereIsNoWindowWithoutHighRisk")}</p>
          {!strategiesShown && (
            <ButtonLink to={strategiesLink(data.request)} variant="secondary" className="w-full sm:w-auto sm:self-start">
              {t("pages.farm.LotPage.viewRotationStrategies")}
            </ButtonLink>
          )}
        </div>
      )}
    </section>
  );
}

function WindowLink({ data, window }: { data: DiagnosisResponse; window: WindowSummary }) {
  useTranslation();
  const limiting = window.limiting_signal ? (SIGNAL_NAME()[window.limiting_signal] ?? window.limiting_signal) : null;
  return (
    <Link
      to={windowLink(data.request, window.sowing_start)}
      className="flex min-h-11 min-w-0 flex-col gap-0.5 border-2 border-superficie-borde bg-superficie-panel px-4 py-3 outline-none hover:border-oscuro-oliva focus-visible:outline-3 focus-visible:outline-accion-foco"
    >
      <span className="font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
        {t("pages.diagnosis.Suitability.plantOn")} {formatDate(window.sowing_start)}
      </span>
      <span className="text-[15px]">
        {t("pages.diagnosis.Suitability.estimatedHarvestOn")} {formatDate(window.harvest_estimate)}
      </span>
      {window.limiting_score !== null && window.limiting_score !== undefined && (
        <span>
          {t("pages.diagnosis.SignalList.mostLimitingFactor")}
          {limiting ? ` (${limiting})` : ""}: <span className="text-lg font-bold">{Math.round(window.limiting_score)}</span>{" "}
          {t("pages.diagnosis.SignalList.outOf100")}
        </span>
      )}
      {window.weighted_score !== null && window.weighted_score !== undefined && (
        <span className="text-[15px] text-texto-secundario">
          {t("pages.diagnosis.Suitability.averageWithYourPriorities")} {Math.round(window.weighted_score)}{" "}
          {t("pages.diagnosis.SignalList.outOf100")}
        </span>
      )}
    </Link>
  );
}
