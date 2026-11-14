import { useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
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
import { harvestNote, orderedSignals, useMunicipalitySoil } from "@/features/diagnosis/signals";
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

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

const IRRIGATION_HINT =
  "Con riego, la falta de lluvia no se cuenta como riesgo. Si no sabe, se evalúa como sin riego y el resultado lo dice.";

/**
 * Diagnóstico de una fecha de siembra, la «consulta suelta» (HU-091; `specs/05-frontend.md`, parte C). El agricultor
 * elige municipio, cultivo, cuándo sembrar y si tiene riego, solo entre opciones válidas; con cuenta, puede elegir uno de
 * sus lotes y entonces el municipio y el riego salen del lote. La consulta va en la dirección: al enviarla se pide el
 * diagnóstico (`POST /diagnostics`, que no guarda nada, R9). El resultado completo (señales, razones y limitaciones)
 * llega con HU-092. Es una página quieta: se ve igual en modo ligero.
 */
export function DiagnosisPage() {
  const [params, setParams] = useSearchParams();
  const { user, loading: sessionLoading } = useSession();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  // Los lotes solo con sesión: sin ella la API respondería 401.
  const lots = useLots(Boolean(user));
  const myLots = user ? (lots.data ?? []) : [];

  const months = useMemo(() => sowingMonths(), []);
  const formRef = useRef<HTMLFormElement>(null);
  const [form, setForm] = useState<ConsultForm>(() => fromParams(params));
  // Validación inmediata: el error de un campo aparece apenas se usa (al elegir, o al salir del buscador sin escoger).
  // Al intentar enviar, o si la dirección ya traía una consulta, aparecen los de todos.
  const [tried, setTried] = useState(() => hasConsult(params));
  const [touched, setTouched] = useState<ReadonlySet<ConsultField>>(() => new Set());
  // Si la dirección cambia desde afuera (una de las mejores fechas, «Elegir otro cultivo», volver atrás), el formulario
  // muestra esa consulta. Al enviar también cambia, con lo mismo que ya tiene el formulario.
  const search = params.toString();
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
      ? toRequest(sent, sentLot, priorities.value)
      : null;
  const diagnosis = useDiagnosis(request);
  const cropName = crops.data?.find((c) => c.crop_id === sent.cropId)?.name_es;
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

  return (
    <div className="min-h-svh bg-paleta-niebla">
      <title>Diagnóstico de una siembra · AgroSense</title>
      <TopBar />
      {/* El espacio de abajo es para los cerros del pie de página. */}
      <main className="container-page pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        <header className="flex max-w-[880px] min-w-0 flex-col gap-3">
          <Eyebrow>Diagnóstico de una siembra</Eyebrow>
          <h1 className="text-[clamp(1.75rem,4vw,3rem)]">¿Conviene sembrar en esa fecha?</h1>
          <p>
            Elija dónde, qué y cuándo quiere sembrar. Le decimos cómo le ha ido a ese cultivo en esa época del año en su zona. Es la
            historia de su zona, no un pronóstico.
          </p>
        </header>

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
                aria-label="Consulta del diagnóstico"
              >
                {myLots.length > 0 && (
                  <SelectField
                    label="¿Para cuál terreno?"
                    value={form.lotId}
                    onChange={(e) => change({ lotId: e.target.value })}
                    options={[
                      { value: "", label: "Otro municipio, sin un lote" },
                      ...myLots.map((l) => ({
                        value: l.lot_id,
                        label: `${l.name} · ${placeName(places.get(l.municipality_id), l.municipality_id)}`,
                      })),
                    ]}
                    hint="Con uno de sus lotes, el municipio y el riego salen del lote."
                  />
                )}

                {lot ? (
                  <LotFacts lot={lot} place={placeName(places.get(lot.municipality_id), lot.municipality_id)} />
                ) : (
                  <Combobox
                    label="Municipio"
                    placeholder="Escriba el nombre de su municipio"
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
                  label="Cultivo"
                  value={form.cropId}
                  disabled={crops.isPending}
                  onChange={(e) => {
                    change({ cropId: e.target.value });
                    touch("crop");
                  }}
                  options={[
                    { value: "", label: crops.isPending ? "Cargando cultivos…" : "Elija un cultivo" },
                    ...(crops.data ?? []).filter((c) => c.kind === "crop").map((c) => ({ value: c.crop_id, label: c.name_es })),
                  ]}
                  error={errors.crop}
                />

                <SelectField
                  name="sowing_month"
                  label="¿Cuándo quiere sembrar?"
                  value={form.month}
                  onChange={(e) => {
                    change({ month: e.target.value });
                    touch("month");
                  }}
                  options={[{ value: "", label: "Elija un mes" }, ...months]}
                  hint="Este mes o uno de los once siguientes. Evaluamos desde el día 1 de ese mes hasta la cosecha estimada."
                  error={errors.month}
                />

                {!lot && (
                  <ChoiceGroup<Irrigation | "">
                    legend="¿Tiene riego?"
                    choices={IRRIGATION_CHOICES}
                    value={form.irrigation}
                    onChange={(irrigation) => {
                      change({ irrigation });
                      touch("irrigation");
                    }}
                    hint={IRRIGATION_HINT}
                    error={errors.irrigation}
                  />
                )}

                <PrioritiesPanel priorities={priorities} />

                <Button type="submit" disabled={!catalogsReady} className="w-full sm:w-auto sm:self-start">
                  Ver el diagnóstico
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
  if (error instanceof ApiError && error.status !== 0) return `No pudimos cargar los municipios y los cultivos: ${error.message}`;
  return "No pudimos cargar los municipios y los cultivos. Revise su conexión y recargue la página.";
}

/** Con un lote: su municipio y su riego, que no se preguntan. El riego se cambia en el lote. */
function LotFacts({ lot, place }: { lot: LotListItem; place: string }) {
  return (
    <div className="flex flex-col gap-1 border-2 border-oscuro-cielo/60 bg-[#E6F0F5] px-4 py-3 text-[15px] leading-snug">
      <p>
        <span className="font-bold">Municipio:</span> {place}, el de su lote.
      </p>
      <p>
        <span className="font-bold">{irrigationText(lot.irrigated)}</span>, según su lote.{" "}
        {lot.irrigated === null && "Se evalúa como sin riego y el resultado lo dice. "}
        <Link to={PATHS.editLot(lot.lot_id)} className={LINK}>
          Cambiarlo en el lote
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
  if (!request) {
    return (
      <section aria-labelledby="resultado" className="flex min-w-0 flex-col gap-3">
        <h2 id="resultado" className="text-[clamp(1.25rem,3vw,1.75rem)]">
          Resultado
        </h2>
        {zeroPriorities ? (
          <Alert>Todas sus prioridades están en 0. Suba al menos una en «Sus prioridades · Ajustar» para ver el diagnóstico.</Alert>
        ) : lotMissing ? (
          <Alert>
            Ese lote no está entre los suyos o no ha entrado con su cuenta.{" "}
            <Link to={PATHS.login} className={LINK}>
              Entrar
            </Link>{" "}
            o elija un municipio.
          </Alert>
        ) : (
          <p className="text-texto-secundario">
            {waitingLot ? "Cargando su lote…" : "Elija municipio, cultivo, cuándo sembrar y si tiene riego, y toque «Ver el diagnóstico»."}
          </p>
        )}
      </section>
    );
  }
  return (
    <section aria-labelledby="resultado" aria-busy={diagnosis.isPending || undefined} className="flex min-w-0 flex-col gap-4">
      <h2 id="resultado" className="text-[clamp(1.25rem,3vw,1.75rem)]">
        Resultado para {monthName(sentMonth)}
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
  // 1. Sin conexión: falla la red o modo offline (status 0)
  if (error instanceof ApiError && (error.status === 0 || error.code === "offline")) {
    return (
      <StateCard
        title="Sin conexión"
        description="Revise la señal. Lo que ya consultó sigue en pantalla; para calcular otra fecha hace falta internet."
        mood="idle"
        actions={[{ label: "Reintentar", variant: "primary", onClick: onRetry }]}
      />
    );
  }
  // 2. Un 404 de /diagnostics indica que el lote no existe o no pertenece a la persona.
  if (error instanceof ApiError && error.status === 404) {
    const actions: StateCardAction[] = [];
    if (hasOtherLots) {
      actions.push({ label: "Elegir otro lote", variant: "primary", onClick: onChooseAnotherLot });
    }
    actions.push({
      label: "Consultar sin lote",
      variant: hasOtherLots ? "secondary" : "primary",
      onClick: onConsultWithoutLot,
    });
    return (
      <StateCard
        title="Ese lote no existe o no es suyo"
        description={
          hasOtherLots
            ? "Elija otro de sus lotes o continúe la consulta por municipio."
            : "Puede continuar la consulta por municipio, sin usar este lote."
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
    error.message === "La fecha de siembra debe estar entre este mes y los próximos doce."
  ) {
    return (
      <StateCard
        title="Esa fecha no se puede consultar"
        description="Elija un mes de los próximos doce: una fecha que ya pasó o más lejana no tiene ventana que evaluar"
        mood="guide"
        actions={[{ label: "Cambiar la fecha", variant: "primary", onClick: onChangeSowingMonth }]}
      />
    );
  }
  if (error instanceof ApiError && error.status === 422) {
    return (
      <StateCard
        title="Revise lo que eligió"
        description={error.message}
        mood="guide"
        actions={[{ label: "Volver al formulario", variant: "secondary", onClick: onReturnToForm }]}
      />
    );
  }
  if (error instanceof ApiError && error.status === 501) {
    return (
      <StateCard
        title="Este cálculo todavía no está disponible"
        description="El cálculo del diagnóstico aún no está construido."
        mood="idle"
      />
    );
  }
  if (error instanceof ApiError && error.status === 503 && error.code === "dataset_unavailable") {
    return (
      <StateCard
        title="Los datos no están disponibles en este momento"
        description="Intente más tarde."
        mood="no_data"
        actions={[{ label: "Reintentar", variant: "primary", onClick: onRetry }]}
      />
    );
  }
  // 4. Un fallo interno o no reconocido conserva el código de soporte y permite reintentar.
  const code = error instanceof ApiError && error.requestId ? error.requestId : null;
  return (
    <StateCard
      title="Algo falló de nuestro lado"
      description="No pudimos calcular su diagnóstico. No es su culpa: lo que eligió sigue aquí. Vuelva a intentar en un momento."
      mood="idle"
      code={code}
      actions={[{ label: "Reintentar", variant: "primary", onClick: onRetry }]}
    />
  );
}
/**
 * El resumen (HU-092, HU-203). La acción primero. Si la luz con sus prioridades y la del criterio de AgroSense coinciden,
 * se ve una sola; si difieren, las dos con su acción y su factor que más limita, la suya primero y más grande, y una
 * línea que dice por qué difieren. Con «rotar» en cualquiera de las dos, el camino a las estrategias.
 */
function Summary({ data }: { data: DiagnosisResponse }) {
  const rotate = data.overall.action === "rotate" || data.overall_default.action === "rotate";
  const example = data.versions.dataset === "ejemplo" && <ExampleLabel>respuesta simulada</ExampleLabel>;
  // Un cultivo que no se da en la zona tiene su propio letrero, sin semáforo, señales ni ventanas (HU-194).
  if (data.suitability.level === "not_suitable") {
    return (
      <Card bodyClassName="gap-4">
        {example}
        <NotSuitable data={data} />
        <p className="text-[15px] text-texto-secundario">Es información para decidir. La decisión es suya.</p>
      </Card>
    );
  }
  return (
    <Card bodyClassName="gap-4">
      {example}
      <DiagnosisLights overall={data.overall} overallDefault={data.overall_default} weights={data.weights} />
      {data.window && (
        <p>
          Siembra el {formatDate(data.window.sowing_start)} · cosecha estimada el {formatDate(data.window.harvest_estimate)}.{" "}
          <span className="text-texto-secundario">{harvestNote(data.window.harvest_basis)}</span>
        </p>
      )}
      <SuitabilityScore score={data.suitability.score} />
      {asksOtherWindow(data.overall, data.overall_default) && <BestWindows data={data} strategiesShown={rotate} />}
      {rotate && (
        <ButtonLink to={strategiesLink(data.request)} variant="secondary" className="w-full sm:w-auto sm:self-start">
          Ver estrategias de rotación
        </ButtonLink>
      )}
      <p className="text-[15px] text-texto-secundario">Es información para decidir. La decisión es suya.</p>
    </Card>
  );
}

/**
 * El detalle del resultado (HU-092): las señales de la ventana y las limitaciones. Va a todo el ancho, debajo de la
 * consulta y del resumen. Con un cultivo que no es apto no hay señales (`signals` nulo): solo las limitaciones.
 */
function Details({ data }: { data: DiagnosisResponse }) {
  const version = useVersion();
  const crops = useCrops();
  const soil = useMunicipalitySoil(data.signals?.soil ? data.request.municipality_id : null);
  // La lluvia de la ventana año por año, para la gráfica de la señal de agua (HU-093).
  const trends = useTrends(data.signals?.water ? data.request.municipality_id : null, data.request.crop_id, data.request.sowing_date);
  const cropName = crops.data?.find((c) => c.crop_id === data.request.crop_id)?.name_es ?? data.request.crop_id;
  const hasSignals = orderedSignals(data.signals).length > 0;
  return (
    <div className="mt-10 flex min-w-0 flex-col gap-8">
      {hasSignals && (
        <section aria-labelledby="senales" className="flex min-w-0 flex-col gap-4">
          <h2 id="senales" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            Las señales de esta ventana
          </h2>
          <p className="max-w-[880px]">
            Cada señal se mide contra lo que este cultivo necesita o aguanta, con una calificación de 0 a 100. Ninguna se promedia con otra
            para decidir la luz: una señal desfavorable no la compensan las demás.
          </p>
          <SignalList
            signals={data.signals}
            limiting={data.overall.limiting_signal}
            irrigated={data.request.irrigated}
            weights={data.weights}
            supplySemester={data.window?.supply_semester}
            soil={soil.data}
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
            Limitaciones de este resultado
          </h2>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {data.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
