import { ApiLanguageNotice } from "@/components/ui/ApiLanguageNotice";
import { cropName as cropLabel } from "@/features/farm/seasons";
import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "@/components/layout/LanguageLink";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { SceneBackdrop } from "@/components/layout/SceneBackdrop";
import { TopBar } from "@/components/layout/TopBar";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { ExampleLabel } from "@/components/ui/Labels";
import { SelectField } from "@/components/ui/SelectField";
import { StateCard, type StateCardAction } from "@/components/ui/StateCard";
import { DiagnosisSkeleton } from "./DiagnosisSkeleton";
import { useSession } from "@/features/auth/session";
import {
  IRRIGATION_CHOICES,
  fromParams,
  hasConsult,
  monthName,
  sowingMonths,
  toParams,
  toRequest,
  useDiagnosis,
  validate,
  type ConsultErrors,
  type ConsultField,
  type ConsultForm,
  type DiagnosisRequest,
  type DiagnosisResponse,
  type Irrigation,
} from "@/features/diagnosis/consult";
import { harvestNote, orderedSignals } from "@/features/diagnosis/signals";
import { strategiesLink } from "@/features/diagnosis/lights";
import { asksOtherWindow } from "@/features/diagnosis/windows";
import { byId, useLots, useMunicipalities, type LotListItem } from "@/features/farm/lots";
import { useVersion } from "@/features/version";
import { useSignalPriorities } from "@/features/diagnosis/priorities";
import { useTrends } from "@/features/diagnosis/trends";
import { DiagnosisLights } from "./Lights";
import { PrioritiesPanel } from "./PrioritiesPanel";
import { SignalList } from "./SignalList";
import { WaterChart } from "./WaterChart";
import { BestWindows, NotSuitable, SuitabilityScore } from "./Suitability";
import { formatDate, useCrops } from "@/features/farm/seasons";
import { irrigationText, placeName } from "@/pages/farm/common";
import { changesLink } from "@/features/changes/changes";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

const IRRIGATION_HINT = () => t("pages.diagnosis.DiagnosisPage.withIrrigationRainfallShortagesDoNotCount");

// Mensaje de backend/api/calculations.py, _check_sowing_date.
// Mantener sincronizado: la API usa invalid_input para varias validaciones.
// i18n-audit.test.ts comprueba la coincidencia con _check_sowing_date sin cambiar el contrato.
const SOWING_DATE_OUT_OF_RANGE_MESSAGE = "La fecha de siembra debe estar entre este mes y los próximos doce.";
/**
 * Diagnóstico de una fecha de siembra, la «consulta suelta» (HU-091; `specs/05-frontend.md`, parte C). El agricultor
 * elige municipio, cultivo, cuándo sembrar y si tiene riego, solo entre opciones válidas; con cuenta, puede elegir uno de
 * sus lotes y entonces el municipio y el riego salen del lote. La consulta va en la dirección: al enviarla se pide el
 * diagnóstico (`POST /diagnostics`, que no guarda nada, R9). El resultado completo (señales, razones y limitaciones)
 * llega con HU-092. Es una página quieta: se ve igual en modo ligero.
 */
export function DiagnosisPage() {
  useTranslation();
  const [params, setParams] = useSearchParams();
  const { user, loading: sessionLoading } = useSession();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  // Los lotes solo con sesión: sin ella la API respondería 401.
  const lots = useLots(Boolean(user));
  const myLots = user ? (lots.data ?? []) : [];

  const months = sowingMonths();
  const formRef = useRef<HTMLFormElement>(null);
  const [form, setForm] = useState<ConsultForm>(() => fromParams(params));
  // Validación inmediata: el error de un campo aparece apenas se usa (al elegir, o al salir del buscador sin escoger).
  // Al intentar enviar, o si la dirección ya traía una consulta, aparecen los de todos.
  const [tried, setTried] = useState(() => hasConsult(params));
  const [touched, setTouched] = useState<ReadonlySet<ConsultField>>(() => new Set());
  // Si la dirección cambia desde afuera (una de las mejores fechas, «Elegir otro cultivo», volver atrás), el formulario
  // muestra esa consulta. Al enviar también cambia, con lo mismo que ya tiene el formulario.
  const search = new URLSearchParams([...params].filter(([key]) => key !== "lang")).toString();
  const [shownSearch, setShownSearch] = useState(search);
  if (search !== shownSearch) {
    setShownSearch(search);
    setForm(fromParams(params));
    setTouched(new Set());
    setTried(hasConsult(params));
  }
  const touch = (field: ConsultField) => setTouched((current) => (current.has(field) ? current : new Set(current).add(field)));

  const places = byId(municipalities.data);
  const catalogsReady = municipalities.isSuccess && crops.isSuccess;
  const lot = myLots.find((l) => l.lot_id === form.lotId);
  const catalogs = {
    municipalities: municipalities.data ?? [],
    crops: crops.data ?? [],
    months: months.map((m) => m.value),
    lot,
  };
  const allErrors: ConsultErrors = catalogsReady ? validate(form, catalogs) : {};
  const errors: ConsultErrors = Object.fromEntries(
    Object.entries(allErrors).filter(([field]) => tried || touched.has(field as ConsultField)),
  );

  // Lo que se consulta es lo de la dirección, no lo que se está escribiendo: cambia solo al enviar.
  const sent = fromParams(params);
  const sentLot = myLots.find((l) => l.lot_id === sent.lotId);
  const hasOtherLots = myLots.some((l) => l.lot_id !== sent.lotId);
  // Con `?lote=`: se espera la sesión y los lotes. Si no hay sesión o el lote no es suyo, se dice y no se consulta.
  const waitingLot = Boolean(sent.lotId) && (sessionLoading || (Boolean(user) && lots.isPending));
  const lotMissing = Boolean(sent.lotId) && !waitingLot && !sentLot;
  // Las prioridades de quien consulta (HU-202): se espera a saberlas para no pedir dos veces, y con todas en 0 no se pide.
  const priorities = useSignalPriorities();
  const request: DiagnosisRequest | null =
    catalogsReady &&
    hasConsult(params) &&
    !waitingLot &&
    !lotMissing &&
    priorities.ready &&
    !priorities.allZero &&
    Object.keys(validate(sent, { ...catalogs, lot: sentLot })).length === 0
      ? toRequest(sent, sentLot, priorities.request)
      : null;
  const diagnosis = useDiagnosis(request);
  const cropName = cropLabel(crops.data?.find((c) => c.crop_id === sent.cropId));
  const place = sentLot ? sentLot.name : places.get(sent.municipalityId)?.name;
  const summaryParts = [cropName, sent.month ? monthName(sent.month) : null, place].filter(Boolean);
  const querySummary = summaryParts.length > 0 ? summaryParts.join(" · ") : undefined;

  const returnToForm = () => {
    formRef.current?.querySelector<HTMLElement>("input, select, button")?.focus();
  };
  const changeSowingMonth = () => {
    formRef.current?.querySelector<HTMLSelectElement>('select[name="sowing_month"]')?.focus();
  };
  const focusLotSelector = () => {
    formRef.current?.querySelector<HTMLSelectElement>("select")?.focus();
  };

  const consultWithoutLot = () => {
    const municipalityId = sentLot?.municipality_id ?? sent.municipalityId;
    if (!municipalityId) return;

    const irrigation = sentLot ? (sentLot.irrigated === null ? "nose" : sentLot.irrigated ? "si" : "no") : sent.irrigation;
    setParams(toParams({ ...sent, municipalityId, irrigation, lotId: "" }), { preventScrollReset: true });
  };

  const change = (patch: Partial<ConsultForm>) => setForm((current) => ({ ...current, ...patch }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!catalogsReady || Object.keys(validate(form, catalogs)).length > 0) return;
    // Un lote que no está entre los suyos no viaja en la dirección.
    setParams(toParams(lot ? form : { ...form, lotId: "" }), { preventScrollReset: true });
  };

  // El paisaje del diseño (diagnostico.py): de fondo completo mientras se elige; en franja arriba con el resultado, y
  // la de la vereda si el cultivo no se da en la zona.
  const notSuitable = diagnosis.data?.suitability.level === "not_suitable";
  return (
    <div className="relative isolate min-h-svh bg-paleta-niebla">
      <title>{t("pages.diagnosis.DiagnosisPage.plantingDiagnosisAgrosense")}</title>
      <SceneBackdrop scene={notSuitable ? "vereda" : "municipio"} variant={request ? "band" : "full"} />
      <TopBar />
      {/* El espacio de abajo es para los cerros del pie de página. */}
      <main className="container-page pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        {/* Sobre el paisaje, el encabezado va en un panel claro para que se lea (en el diseño va dentro de la tarjeta). */}
        <header className="flex max-w-[880px] min-w-0 flex-col gap-3 rounded-lg bg-superficie-panel/95 px-5 py-4 shadow-sm">
          <Eyebrow>{t("footer.diagnosis")}</Eyebrow>
          <h1 className="text-[clamp(1.75rem,4vw,3rem)]">{t("pages.diagnosis.DiagnosisPage.isThisASuitablePlantingDate")}</h1>
          <p>{t("pages.diagnosis.DiagnosisPage.chooseWhereWhatAndWhenToPlant")}</p>
        </header>
        <ApiLanguageNotice />

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card bodyClassName="gap-6">
            {municipalities.isError || crops.isError ? (
              <Alert>{catalogErrorText(municipalities.error ?? crops.error)}</Alert>
            ) : (
              <form
                ref={formRef}
                noValidate
                onSubmit={submit}
                className="flex min-w-0 flex-col gap-6"
                aria-label={t("pages.diagnosis.DiagnosisPage.diagnosisInputs")}
              >
                {myLots.length > 0 && (
                  <SelectField
                    label={t("pages.strategies.StrategiesPage.whichLand")}
                    value={form.lotId}
                    onChange={(e) => change({ lotId: e.target.value })}
                    options={[
                      { value: "", label: t("pages.strategies.StrategiesPage.anotherMunicipalityWithoutAPlot") },
                      ...myLots.map((l) => ({
                        value: l.lot_id,
                        label: `${l.name} · ${placeName(places.get(l.municipality_id), l.municipality_id)}`,
                      })),
                    ]}
                    hint={t("pages.diagnosis.DiagnosisPage.withOneOfYourPlotsTheMunicipality")}
                  />
                )}

                {lot ? (
                  <LotFacts lot={lot} place={placeName(places.get(lot.municipality_id), lot.municipality_id)} />
                ) : (
                  <Combobox
                    label={t("pages.farm.AddLotPage.municipality")}
                    placeholder={t("pages.strategies.StrategiesPage.enterYourMunicipalityName")}
                    loading={municipalities.isPending}
                    options={(municipalities.data ?? []).map((m) => ({ id: m.municipality_id, label: m.name, hint: m.department }))}
                    value={optionFor(form.municipalityId, places)}
                    onChange={(option) => {
                      change({ municipalityId: option.id });
                      touch("municipality");
                    }}
                    onBlur={() => touch("municipality")}
                    error={errors.municipality}
                  />
                )}

                <SelectField
                  label={t("pages.farm.SeasonFormPage.crop")}
                  value={form.cropId}
                  disabled={crops.isPending}
                  onChange={(e) => {
                    change({ cropId: e.target.value });
                    touch("crop");
                  }}
                  options={[
                    {
                      value: "",
                      label: crops.isPending
                        ? t("pages.changes.LotChangesLink.loadingCrops")
                        : t("pages.changes.LotChangesLink.chooseACrop"),
                    },
                    ...(crops.data ?? []).filter((c) => c.kind === "crop").map((c) => ({ value: c.crop_id, label: cropLabel(c) })),
                  ]}
                  error={errors.crop}
                />

                <SelectField
                  name="sowing_month"
                  label={t("pages.diagnosis.DiagnosisPage.whenDoYouWantToPlant")}
                  value={form.month}
                  onChange={(e) => {
                    change({ month: e.target.value });
                    touch("month");
                  }}
                  options={[{ value: "", label: t("pages.strategies.StrategiesPage.chooseAMonth") }, ...months]}
                  hint={t("pages.diagnosis.DiagnosisPage.thisMonthOrOneOfTheNext")}
                  error={errors.month}
                />

                {!lot && (
                  <ChoiceGroup<Irrigation | "">
                    legend={t("pages.changes.ChangesContext.doYouHaveIrrigation")}
                    choices={IRRIGATION_CHOICES()}
                    value={form.irrigation}
                    onChange={(irrigation) => {
                      change({ irrigation });
                      touch("irrigation");
                    }}
                    hint={IRRIGATION_HINT()}
                    error={errors.irrigation}
                  />
                )}

                <PrioritiesPanel priorities={priorities} />

                <Button type="submit" disabled={!catalogsReady} className="w-full sm:w-auto sm:self-start">
                  {t("pages.diagnosis.DiagnosisPage.viewDiagnosis")}
                </Button>
              </form>
            )}
          </Card>

          <Result
            request={request}
            sentMonth={sent.month}
            diagnosis={diagnosis}
            waitingLot={waitingLot}
            lotMissing={lotMissing}
            zeroPriorities={hasConsult(params) && priorities.allZero}
            querySummary={querySummary}
            hasOtherLots={hasOtherLots}
            onChooseAnotherLot={focusLotSelector}
            onConsultWithoutLot={consultWithoutLot}
            onReturnToForm={returnToForm}
            onChangeSowingMonth={changeSowingMonth}
          />
        </div>
        {request && (
          <ButtonLink
            to={changesLink(request.municipality_id, request.crop_id, request.irrigated)}
            variant="secondary"
            className="mt-6 w-full sm:w-auto"
          >
            {t("pages.changes.LotChangesLink.seeWhatHasChangedInYourArea")}
          </ButtonLink>
        )}
        {request && diagnosis.isSuccess && <Details data={diagnosis.data} />}
      </main>
      <Footer />
    </div>
  );
}

function optionFor(id: string, places: Map<string, { name: string; department: string }>): Option | null {
  const place = places.get(id);
  return place ? { id, label: place.name, hint: place.department } : null;
}

/** Sin catálogo no hay consulta. Un 503 trae su motivo (por ejemplo, el dataset no está publicado); lo demás es la red. */
function catalogErrorText(error: Error | null): string {
  if (error instanceof ApiError && error.status !== 0)
    return t("pages.diagnosis.DiagnosisPage.weCouldNotLoadMunicipalitiesAndCrops", { v0: error.message });
  return t("pages.strategies.StrategiesPage.weCouldNotLoadMunicipalitiesAndCrops");
}

/** Con un lote: su municipio y su riego, que no se preguntan. El riego se cambia en el lote. */
function LotFacts({ lot, place }: { lot: LotListItem; place: string }) {
  useTranslation();
  return (
    <div className="flex flex-col gap-1 border-2 border-oscuro-cielo/60 bg-[#E6F0F5] px-4 py-3 text-[15px] leading-snug">
      <p>
        <span className="font-bold">{t("pages.strategies.StrategiesPage.municipality")}</span> {place}
        {t("pages.strategies.StrategiesPage.fromYourPlot")}
      </p>
      <p>
        <span className="font-bold">{irrigationText(lot.irrigated)}</span>
        {t("pages.strategies.StrategiesPage.accordingToYourPlot")}{" "}
        {lot.irrigated === null && t("pages.diagnosis.DiagnosisPage.assessedWithoutIrrigationAndStatedInThe")}
        <Link to={PATHS.editLot(lot.lot_id)} className={LINK}>
          {t("pages.strategies.StrategiesPage.changeItInThePlot")}
        </Link>
      </p>
    </div>
  );
}
interface ResultProps {
  request: DiagnosisRequest | null;
  sentMonth: string;
  diagnosis: ReturnType<typeof useDiagnosis>;
  waitingLot: boolean;
  lotMissing: boolean;
  zeroPriorities: boolean;
  querySummary?: string;
  hasOtherLots: boolean;
  onChooseAnotherLot: () => void;
  onConsultWithoutLot: () => void;
  onReturnToForm: () => void;
  onChangeSowingMonth: () => void;
}
function Result({
  request,
  sentMonth,
  diagnosis,
  waitingLot,
  lotMissing,
  zeroPriorities,
  querySummary,
  hasOtherLots,
  onChooseAnotherLot,
  onConsultWithoutLot,
  onReturnToForm,
  onChangeSowingMonth,
}: Readonly<ResultProps>) {
  useTranslation();
  if (!request) {
    return (
      <section aria-labelledby="resultado" className="flex min-w-0 flex-col gap-3 rounded-lg bg-superficie-panel/95 px-5 py-4 shadow-sm">
        <h2 id="resultado" className="text-[clamp(1.25rem,3vw,1.75rem)]">
          {t("pages.diagnosis.DiagnosisPage.result")}
        </h2>
        {zeroPriorities ? (
          <Alert>{t("pages.diagnosis.DiagnosisPage.allPrioritiesAreSetTo0Increase")}</Alert>
        ) : lotMissing ? (
          <Alert>
            {t("pages.strategies.StrategiesPage.thatPlotIsNotYoursOrYou")}{" "}
            <Link to={PATHS.login} className={LINK}>
              {t("login.submit")}
            </Link>{" "}
            {t("pages.strategies.StrategiesPage.orChooseAMunicipality")}
          </Alert>
        ) : (
          <p className="text-texto-secundario">
            {waitingLot
              ? t("pages.strategies.StrategiesPage.loadingYourPlot")
              : t("pages.diagnosis.DiagnosisPage.chooseAMunicipalityCropPlantingMonthAnd")}
          </p>
        )}
      </section>
    );
  }
  return (
    <section
      aria-labelledby="resultado"
      aria-busy={diagnosis.isPending || undefined}
      className="flex min-w-0 flex-col gap-4 rounded-lg bg-superficie-panel/95 px-5 py-4 shadow-sm"
    >
      <h2 id="resultado" className="text-[clamp(1.25rem,3vw,1.75rem)]">
        {t("pages.diagnosis.DiagnosisPage.resultFor")} {monthName(sentMonth)}
      </h2>
      {diagnosis.isPending ? (
        <DiagnosisSkeleton querySummary={querySummary} />
      ) : diagnosis.isError ? (
        <DiagnosisError
          error={diagnosis.error}
          onRetry={() => void diagnosis.refetch()}
          hasOtherLots={hasOtherLots}
          onChooseAnotherLot={onChooseAnotherLot}
          onConsultWithoutLot={onConsultWithoutLot}
          onReturnToForm={onReturnToForm}
          onChangeSowingMonth={onChangeSowingMonth}
        />
      ) : (
        <Summary data={diagnosis.data} />
      )}
    </section>
  );
}

interface DiagnosisErrorProps {
  error: Error;
  onRetry: () => void;
  hasOtherLots: boolean;
  onChooseAnotherLot: () => void;
  onConsultWithoutLot: () => void;
  onReturnToForm: () => void;
  onChangeSowingMonth: () => void;
}

/**
 * Traduce un fallo de la API o de la red a una tarjeta de estado clara (HU-094; W6).
 * Separa los códigos de error que requieren mensajes o acciones distintos.
 */
function DiagnosisError({
  error,
  onRetry,
  hasOtherLots,
  onChooseAnotherLot,
  onConsultWithoutLot,
  onReturnToForm,
  onChangeSowingMonth,
}: Readonly<DiagnosisErrorProps>) {
  useTranslation();
  // 1. Sin conexión: falla la red o modo offline (status 0)
  if (error instanceof ApiError && (error.status === 0 || error.code === "offline")) {
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.offline")}
        description={t("pages.diagnosis.DiagnosisPage.checkYourConnectionExistingResultsRemainVisible")}
        mood="idle"
        actions={[{ label: t("pages.diagnosis.DiagnosisPage.tryAgain"), variant: "primary", onClick: onRetry }]}
      />
    );
  }
  // 2. Un 404 de /diagnostics indica que el lote no existe o no pertenece a la persona.
  if (error instanceof ApiError && error.status === 404) {
    const actions: StateCardAction[] = [];
    if (hasOtherLots) {
      actions.push({ label: t("pages.diagnosis.DiagnosisPage.chooseAnotherPlot"), variant: "primary", onClick: onChooseAnotherLot });
    }
    actions.push({
      label: t("pages.diagnosis.DiagnosisPage.continueWithoutAPlot"),
      variant: hasOtherLots ? "secondary" : "primary",
      onClick: onConsultWithoutLot,
    });
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.thatPlotDoesNotExistOrIs")}
        description={
          hasOtherLots
            ? t("pages.diagnosis.DiagnosisPage.chooseAnotherPlotOrContinueByMunicipality")
            : t("pages.diagnosis.DiagnosisPage.youCanContinueByMunicipalityWithoutUsing")
        }
        mood="guide"
        actions={actions}
      />
    );
  }
  // 3. La API explica qué dato de entrada debe revisarse.
  if (
    error instanceof ApiError &&
    error.status === 422 &&
    error.code === "invalid_input" &&
    error.message === SOWING_DATE_OUT_OF_RANGE_MESSAGE
  ) {
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.thatDateCannotBeAssessed")}
        description={t("pages.diagnosis.DiagnosisPage.chooseAMonthWithinTheNextTwelve")}
        mood="guide"
        actions={[{ label: t("pages.strategies.StrategyResults.changeTheDate"), variant: "primary", onClick: onChangeSowingMonth }]}
      />
    );
  }
  // HU-094: un municipio fuera de la región no es un error de quien consulta: es «sin cobertura».
  if (error instanceof ApiError && error.status === 422 && error.code === "outside_region") {
    return (
      <StateCard
        title={t("changes.error.coverage.title")}
        description={error.message}
        mood="no_data"
        actions={[{ label: t("changes.error.coverage.action"), variant: "secondary", onClick: onReturnToForm }]}
      />
    );
  }
  if (error instanceof ApiError && error.status === 422) {
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.reviewYourChoices")}
        description={error.message}
        mood="guide"
        actions={[{ label: t("pages.diagnosis.DiagnosisPage.backToTheForm"), variant: "secondary", onClick: onReturnToForm }]}
      />
    );
  }
  if (error instanceof ApiError && error.status === 501) {
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.thisCalculationIsNotAvailableYet")}
        description={t("pages.diagnosis.DiagnosisPage.theDiagnosisCalculationHasNotBeenImplemented")}
        mood="idle"
      />
    );
  }
  if (error instanceof ApiError && error.status === 503 && error.code === "dataset_unavailable") {
    return (
      <StateCard
        title={t("pages.diagnosis.DiagnosisPage.dataIsNotAvailableRightNow")}
        description={t("pages.diagnosis.DiagnosisPage.tryAgainLater")}
        mood="no_data"
        actions={[{ label: t("pages.diagnosis.DiagnosisPage.tryAgain"), variant: "primary", onClick: onRetry }]}
      />
    );
  }
  // 4. Un fallo interno o no reconocido conserva el código de soporte y permite reintentar.
  const code = error instanceof ApiError && error.requestId ? error.requestId : null;
  return (
    <StateCard
      title={t("pages.diagnosis.DiagnosisPage.somethingWentWrongOnOurSide")}
      description={t("pages.diagnosis.DiagnosisPage.weCouldNotCalculateYourDiagnosisYour")}
      mood="idle"
      code={code}
      actions={[{ label: t("pages.diagnosis.DiagnosisPage.tryAgain"), variant: "primary", onClick: onRetry }]}
    />
  );
}
/**
 * El resumen (HU-092, HU-203). La acción primero. Si la luz con sus prioridades y la del criterio de AgroSense coinciden,
 * se ve una sola; si difieren, las dos con su acción y su factor que más limita, la suya primero y más grande, y una
 * línea que dice por qué difieren. Con «rotar» en cualquiera de las dos, el camino a las estrategias.
 */
function Summary({ data }: { data: DiagnosisResponse }) {
  useTranslation();
  const rotate = data.overall.action === "rotate" || data.overall_default.action === "rotate";
  const example = data.versions.dataset === "ejemplo" && <ExampleLabel>{t("pages.strategies.CycleView.simulatedResponse")}</ExampleLabel>;
  // Un cultivo que no se da en la zona tiene su propio letrero, sin semáforo, señales ni ventanas (HU-194).
  if (data.suitability.level === "not_suitable") {
    return (
      <Card bodyClassName="gap-4">
        {example}
        <NotSuitable data={data} />
        <p className="text-[15px] text-texto-secundario">{t("pages.strategies.CycleView.informationToHelpYouDecideTheDecision")}</p>
      </Card>
    );
  }
  return (
    <Card bodyClassName="gap-4">
      {example}
      <DiagnosisLights overall={data.overall} overallDefault={data.overall_default} weights={data.weights} />
      {data.window && (
        <p>
          {t("pages.strategies.CycleView.plantingOn")} {formatDate(data.window.sowing_start)}{" "}
          {t("pages.diagnosis.DiagnosisPage.estimatedHarvestOn")} {formatDate(data.window.harvest_estimate)}.{" "}
          <span className="text-texto-secundario">{harvestNote(data.window.harvest_basis)}</span>
        </p>
      )}
      <SuitabilityScore score={data.suitability.score} />
      {asksOtherWindow(data.overall, data.overall_default) && <BestWindows data={data} strategiesShown={rotate} />}
      {rotate && (
        <ButtonLink to={strategiesLink(data.request)} variant="secondary" className="w-full sm:w-auto sm:self-start">
          {t("pages.farm.LotPage.viewRotationStrategies")}
        </ButtonLink>
      )}
      <p className="text-[15px] text-texto-secundario">{t("pages.strategies.CycleView.informationToHelpYouDecideTheDecision")}</p>
    </Card>
  );
}

/**
 * El detalle del resultado (HU-092): las señales de la ventana y las limitaciones. Va a todo el ancho, debajo de la
 * consulta y del resumen. Con un cultivo que no es apto no hay señales (`signals` nulo): solo las limitaciones.
 */
function Details({ data }: { data: DiagnosisResponse }) {
  useTranslation();
  const version = useVersion();
  const crops = useCrops();
  // La lluvia de la ventana año por año, para la gráfica de la señal de agua (HU-093).
  const trends = useTrends(data.signals?.water ? data.request.municipality_id : null, data.request.crop_id, data.request.sowing_date);
  const cropName = cropLabel(crops.data?.find((c) => c.crop_id === data.request.crop_id)) ?? data.request.crop_id;
  const hasSignals = orderedSignals(data.signals).length > 0;
  return (
    <div className="mt-10 flex min-w-0 flex-col gap-8">
      {hasSignals && (
        <section aria-labelledby="senales" className="flex min-w-0 flex-col gap-4">
          <h2 id="senales" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            {t("pages.diagnosis.DiagnosisPage.signalsForThisWindow")}
          </h2>
          <p className="max-w-[880px]">{t("pages.diagnosis.DiagnosisPage.eachSignalIsScoredFrom0To")}</p>
          <SignalList
            signals={data.signals}
            limiting={data.overall.limiting_signal}
            irrigated={data.request.irrigated}
            weights={data.weights}
            supplySemester={data.window?.supply_semester}
            soilContext={{ municipalityId: data.request.municipality_id, lotId: data.request.lot_id }}
            version={version.data}
            waterChart={
              <WaterChart
                series={trends.data?.water}
                status={trends.status}
                cropName={cropName}
                from={data.window?.sowing_start}
                to={data.window?.harvest_estimate}
                version={version.data}
              />
            }
          />
        </section>
      )}
      {data.limitations.length > 0 && (
        <section aria-labelledby="limitaciones" className="flex max-w-[880px] min-w-0 flex-col gap-3">
          <h2 id="limitaciones" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            {t("pages.diagnosis.DiagnosisPage.limitationsOfThisResult")}
          </h2>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {data.limitations.map((limitation) => (
              <li lang="es" key={limitation}>
                {limitation}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
