import { ApiLanguageNotice } from "@/components/ui/ApiLanguageNotice";
import { t, locale } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { ApiError, type Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useChanges, type ChangesResponse } from "@/features/changes/changes";
import { SIGNAL_NAME } from "@/features/diagnosis/signals";
import { ChangesContext, useChangesContext } from "./ChangesContext";

type Period = Schemas["Period"];
type Periods = Schemas["Periods"];

type Indicator = "frost_freq_pct" | "precip_normal_mm" | "tmax_p90_c";

const NOTICE = () => t("pages.changes.ChangesPage.thisIsYourAreasHistoryItIs");

const MONTHS = () =>
  Array.from({ length: 12 }, (_, month) => {
    const name = new Intl.DateTimeFormat(locale(), { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2020, month, 1)));
    return name.charAt(0).toUpperCase() + name.slice(1);
  });

const NUMBER = () =>
  new Intl.NumberFormat(locale(), {
    maximumFractionDigits: 1,
  });

const INDICATORS = (): {
  key: Indicator;
  title: string;
  unit: string;
  differenceUnit: string;
}[] => [
  {
    key: "frost_freq_pct",
    title: t("landing.signal.frost"),
    unit: "%",
    differenceUnit: t("units.percentagePoints"),
  },
  {
    key: "precip_normal_mm",
    title: t("pages.changes.ChangesPage.normalRainfall"),
    unit: "mm",
    differenceUnit: "mm",
  },
  {
    key: "tmax_p90_c",
    title: t("pages.changes.ChangesPage.maximumTemperature90thPercentile"),
    unit: "°C",
    differenceUnit: "°C",
  },
];

function periodLabel(period: Period) {
  return t("pages.changes.ChangesPage.betweenAnd", { v0: period.start_year, v1: period.end_year });
}

function sourceLabel(sourceId: string) {
  if (sourceId === "nasa_power") return "NASA POWER";
  if (/imerg/i.test(sourceId)) return "GPM IMERG";
  return sourceId;
}

function Missing() {
  useTranslation();
  return (
    <span className="inline-flex items-start gap-2">
      <span aria-hidden="true">◇</span>
      <span>{t("features.strategies.strategies.insufficientData")}</span>
    </span>
  );
}

function PeriodValue({
  label,
  value,
  unit,
  minimum,
  maximum,
  before,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  minimum: number;
  maximum: number;
  before: boolean;
}) {
  useTranslation();
  const known = value != null;
  const width = known ? ((value - minimum) / (maximum - minimum)) * 100 : 0;

  return (
    <div className="min-w-0">
      <p className="text-sm text-texto-secundario">{label}</p>

      {known ? (
        <>
          <p className="font-bold">
            {NUMBER().format(value)} {unit}
          </p>
          <div aria-hidden="true" className="mt-1 h-3 border border-current">
            <div
              className="h-full"
              style={{
                width: `${Math.max(0, Math.min(100, width))}%`,
                background: before ? "repeating-linear-gradient(135deg, currentColor 0 2px, transparent 2px 5px)" : "currentColor",
              }}
            />
          </div>
        </>
      ) : (
        <div className="mt-1 border-2 border-dashed p-2 text-sm">
          <Missing />
        </div>
      )}
    </div>
  );
}

function Comparison({
  data,
  indicator,
  title,
  unit,
  differenceUnit,
}: {
  data: ChangesResponse;
  indicator: Indicator;
  title: string;
  unit: string;
  differenceUnit: string;
}) {
  useTranslation();
  const periods = indicator === "precip_normal_mm" ? (data.precip_periods ?? data.periods) : data.periods;

  const sameSource = periods.before.source_id === periods.after.source_id;

  // La escala incluye ambos periodos y los doce meses.
  // Un valor nulo nunca participa como cero.
  const values = data.months.flatMap((month) => {
    const metric = month[indicator];
    return [metric.before, metric.after].filter((value): value is number => value != null);
  });

  const minimum = Math.min(0, ...values);
  const maximum = Math.max(minimum + 1, ...values);

  const imerg = /imerg/i.test(periods.before.source_id);
  const power = periods.before.source_id === "nasa_power";

  return (
    <Card>
      <h2 className="text-xl">{title}</h2>
      <p>
        {periodLabel(periods.before)} · {periodLabel(periods.after)}
      </p>

      {!sameSource ? (
        <p role="alert">{t("pages.changes.ChangesPage.thesePeriodsCannotBeComparedBecauseThey")}</p>
      ) : (
        <>
          <p className="text-sm text-texto-secundario">
            {t("pages.strategies.StrategyCard.source")} {sourceLabel(periods.before.source_id)}
            {t("pages.changes.ChangesPage.units")} {unit}.
          </p>

          {power && <p className="text-sm">{t("pages.changes.ChangesPage.nasaPowerIsAReanalysisAModel")}</p>}

          {imerg && <p className="text-sm">{t("pages.changes.ChangesPage.imergDataStartsIn2000SoIts")}</p>}

          <p className="text-sm">{t("pages.changes.ChangesPage.beforeHatchedBarsAfterSolidBarsAll")}</p>

          <ol className="flex flex-col gap-5">
            {MONTHS().map((monthName, index) => {
              const metric = data.months.find((month) => month.month === index + 1)?.[indicator];

              const comparable = metric?.status === "available" && metric.before != null && metric.after != null && metric.change != null;

              return (
                <li key={monthName} className="border-t border-superficie-borde pt-3">
                  <h3 className="font-bold">{monthName}</h3>

                  <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <PeriodValue
                      label={periodLabel(periods.before)}
                      value={metric?.before}
                      unit={unit}
                      minimum={minimum}
                      maximum={maximum}
                      before
                    />
                    <PeriodValue
                      label={periodLabel(periods.after)}
                      value={metric?.after}
                      unit={unit}
                      minimum={minimum}
                      maximum={maximum}
                      before={false}
                    />
                  </div>

                  <div className="mt-2 text-sm">
                    {comparable ? (
                      <p>
                        {t("pages.changes.ChangesPage.changeAfterMinusBefore")} {metric.change! > 0 ? "+" : ""}
                        {NUMBER().format(metric.change!)} {differenceUnit}.
                      </p>
                    ) : (
                      <>
                        <p>{t("pages.changes.ChangesPage.changeBetweenPeriods")}</p>
                        <Missing />
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Card>
  );
}

function Windows({ periods, windows }: { periods: Periods; windows: ChangesResponse["best_windows"] }) {
  useTranslation();
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-2xl">{t("pages.changes.ChangesPage.bestPlantingDatesBeforeAndAfter")}</h2>

      <p>{t("pages.changes.ChangesPage.usingAgrosenseWeightsOnlyClimateChangesSupply")}</p>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {(["before", "after"] as const).map((side) => (
          <Card key={side}>
            <h3 className="text-xl">{periodLabel(periods[side])}</h3>

            {windows[side].length === 0 ? (
              <p>{t("pages.changes.ChangesPage.theResponseIncludesNoBestWindowsFor")}</p>
            ) : (
              <ol className="flex list-decimal flex-col gap-4 pl-6">
                {windows[side].map((window) => (
                  <li key={window.month}>
                    <p className="font-bold">
                      {t("pages.changes.ChangesPage.plantIn")} {MONTHS()[window.month - 1]?.toLowerCase()}
                    </p>

                    {window.limiting_score != null ? (
                      <p>
                        {t("pages.changes.ChangesPage.limitingFactor")} {NUMBER().format(window.limiting_score)}/100
                        {window.limiting_signal ? ` · ${SIGNAL_NAME()[window.limiting_signal]}` : ""}
                      </p>
                    ) : (
                      <Missing />
                    )}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}

export function ChangesPage() {
  useTranslation();
  const context = useChangesContext();
  const { municipalityId, cropId, irrigation } = context;

  const irrigated = irrigation === "si" ? true : irrigation === "no" ? false : null;

  const complete = context.valid;
  const query = useChanges(complete ? municipalityId : null, complete ? cropId : null, irrigated);
  const data = query.data;

  const diagnosisParams = new URLSearchParams();
  if (municipalityId) diagnosisParams.set("municipio", municipalityId);
  if (cropId) diagnosisParams.set("cultivo", cropId);
  if (irrigation === "si" || irrigation === "no") {
    diagnosisParams.set("riego", irrigation);
  }

  const diagnosisUrl = `${PATHS.diagnosis}?${diagnosisParams.toString()}`;

  return (
    <>
      <TopBar />

      <main className="container-page flex min-h-svh flex-col gap-7 pt-28 pb-40">
        <title>{t("pages.changes.ChangesPage.whatChangedInYourAreaAgrosense")}</title>
        <ApiLanguageNotice />
        <Card>
          <h1 className="text-[clamp(1.75rem,5vw,3rem)]">{t("landing.question.changes")}</h1>

          <p className="border-2 border-current p-3 font-bold">{NOTICE()}</p>

          <p>{t("pages.changes.ChangesPage.twoHistoricalPeriodsInTheMunicipalityFrost")}</p>
          <ChangesContext context={context} />

          <ButtonLink to={diagnosisUrl} variant="secondary" className="self-start">
            {t("pages.changes.ChangesPage.goToPlantingDiagnosis")}
          </ButtonLink>
        </Card>

        {!context.ready && !context.error && <p role="status">{t("pages.changes.ChangesPage.loadingMunicipalitiesAndCrops")}</p>}
        {context.ready && !complete && (
          <Card>
            <p>{t("pages.changes.ChangesPage.chooseAMunicipalityCropAndIrrigationOption")}</p>
          </Card>
        )}

        {complete && query.isPending && <p role="status">{t("pages.changes.ChangesPage.loadingTheHistoricalComparison")}</p>}

        {complete && query.isError && (
          <Card>
            <p role="alert">
              {query.error instanceof ApiError && query.error.status === 501
                ? t("pages.changes.ChangesPage.theHistoricalComparisonIsNotAvailableFor")
                : query.error.message}
            </p>

            <Button onClick={() => void query.refetch()} className="self-start">
              {t("pages.account.PrioritiesCard.tryAgain")}
            </Button>
          </Card>
        )}

        {complete && data && (
          <>
            {data.versions.dataset === "ejemplo" && (
              <p className="border-2 border-dashed p-3 font-bold">
                {t("pages.changes.ChangesPage.exampleDataDoesNotRepresentActualObservations")}
              </p>
            )}

            {data.suitability.level === "not_suitable" ? (
              <Card>
                <h2 className="text-xl">{t("pages.diagnosis.Suitability.thisCropIsUnsuitableForYourArea")}</h2>
                {data.suitability.reasons.map((reason, index) => (
                  <p lang="es" key={index}>
                    {reason}
                  </p>
                ))}
                <p>{t("pages.changes.ChangesPage.onlyTheAreasClimateIsShownThere")}</p>
                <Button variant="secondary" className="self-start" onClick={() => context.change("cultivo", "")}>
                  {t("pages.diagnosis.Suitability.chooseAnotherCrop")}
                </Button>
              </Card>
            ) : (
              <>
                {data.suitability.level === "insufficient_data" && (
                  <p className="border-2 border-dashed p-3">
                    {t("pages.changes.ChangesPage.insufficientDataToConfirmCropSuitabilityThis")}
                  </p>
                )}

                <Windows periods={data.periods} windows={data.best_windows} />
              </>
            )}

            <section aria-label={t("pages.changes.ChangesPage.monthlyClimateComparisons")} className="flex flex-col gap-6">
              {INDICATORS().map((indicator) => (
                <Comparison
                  key={indicator.key}
                  data={data}
                  indicator={indicator.key}
                  title={indicator.title}
                  unit={indicator.unit}
                  differenceUnit={indicator.differenceUnit}
                />
              ))}
            </section>

            <Card>
              <h2 className="text-xl">{t("pages.changes.ChangesPage.whatTheDataSays")}</h2>
              {data.reasons.length > 0 ? (
                data.reasons.map((reason, index) => (
                  <p lang="es" key={index}>
                    {reason}
                  </p>
                ))
              ) : (
                <p>{t("pages.changes.ChangesPage.theResponseIncludesNoAdditionalExplanations")}</p>
              )}

              <h2 className="text-xl">{t("pages.strategies.StrategyCard.limitations")}</h2>
              {data.limitations.length > 0 ? (
                <ul className="list-disc space-y-2 pl-6">
                  {data.limitations.map((limitation, index) => (
                    <li lang="es" key={index}>
                      {limitation}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t("pages.changes.ChangesPage.theResponseStatesNoAdditionalLimitations")}</p>
              )}

              <p className="text-sm text-texto-secundario">
                {t("pages.changes.ChangesPage.dataset")} {data.versions.dataset} {t("pages.changes.ChangesPage.rules")}{" "}
                {data.versions.rules}
              </p>
            </Card>
          </>
        )}
      </main>

      <Footer />
    </>
  );
}
