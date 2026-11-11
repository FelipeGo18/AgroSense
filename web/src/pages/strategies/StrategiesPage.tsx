import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { ExampleLabel } from "@/components/ui/Labels";
import { PriorityControl } from "@/components/ui/PriorityControl";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { useSession } from "@/features/auth/session";
import { IRRIGATION_CHOICES, monthName, sowingMonths, type Irrigation } from "@/features/diagnosis/consult";
import { useSignalPriorities } from "@/features/diagnosis/priorities";
import { byId, formatHa, useLot, useLots, useMunicipalities } from "@/features/farm/lots";
import { cropNames, formatShortDate, useCrops, useSeasons } from "@/features/farm/seasons";
import {
  START_PRIORITIES,
  allZero,
  currentFromHistory,
  explain422,
  freeHarvested,
  fromParams,
  hasEntry,
  previousFromSeasons,
  toParams,
  toRequest,
  useRotations,
  validate,
  writeArea,
  type LotFacts,
  type Mode,
  type RotationRequest,
  type RotationResponse,
  type RotationWeights,
  type StrategyErrors,
  type StrategyField,
  type StrategyForm,
} from "@/features/strategies/entry";
import { irrigationText, placeName } from "@/pages/farm/common";
import { PreviousChoice } from "@/pages/farm/SeasonParts";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";
const SLOT_LABELS = ["Lo último que sembró", "Lo de antes", "Lo de antes de eso"];
const CURRENT_LABELS = ["Primero siembra", "Después", "Después (si son tres)"];

/**
 * Entrada a las estrategias de rotación (HU-214), la entrada principal del MVP (decisión 12): «Consultar» lleva aquí.
 * Sin cuenta pide municipio, área, qué había antes, cuándo sembrar el primer ciclo, riego, cuántos ciclos y la rotación
 * que viene haciendo (HU-223). Con cuenta, desde un lote: su municipio, su riego, el terreno que va a sembrar y su
 * historial. Las prioridades de la rotación (HU-101) empiezan iguales; las de las señales son las mismas de la consulta
 * del diagnóstico (HU-202). La lista completa de estrategias es HU-102: aquí, un resumen. Es una página quieta.
 */
export function StrategiesPage() {
  const [params, setParams] = useSearchParams();
  const { user, loading: sessionLoading } = useSession();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  const lots = useLots(Boolean(user));
  const myLots = user ? (lots.data ?? []) : [];
  const months = useMemo(() => sowingMonths(), []);
  const signalPriorities = useSignalPriorities();
  const [priorities, setPriorities] = useState<RotationWeights>(START_PRIORITIES);

  const [form, setForm] = useState<StrategyForm>(() => fromParams(params));
  const [tried, setTried] = useState(() => hasEntry(params));
  const [touched, setTouched] = useState<ReadonlySet<StrategyField>>(() => new Set());
  const touch = (field: StrategyField) => setTouched((current) => (current.has(field) ? current : new Set(current).add(field)));
  // Si la dirección cambia desde afuera (por ejemplo, volver atrás), el formulario la muestra.
  const search = params.toString();
  const [shownSearch, setShownSearch] = useState(search);
  if (search !== shownSearch) {
    setShownSearch(search);
    setForm(fromParams(params));
    setTouched(new Set());
    setTried(hasEntry(params));
  }

  // El lote de la consulta: el del formulario mientras se llena, el de la dirección para consultar.
  const lot = useLot(form.lotId);
  const seasons = useSeasons(form.lotId);
  const places = byId(municipalities.data);
  const names = cropNames(crops.data);
  const catalogsReady = municipalities.isSuccess && crops.isSuccess;
  const lotReady = !form.lotId || (lot.isSuccess && seasons.isSuccess);
  const context = {
    municipalityIds: new Set((municipalities.data ?? []).map((m) => m.municipality_id)),
    cropIds: new Set((crops.data ?? []).map((c) => c.crop_id)),
    months: months.map((m) => m.value),
    lot: Boolean(form.lotId),
  };

  // Con lote: el terreno libre que se va a sembrar y lo que había antes, de sus siembras cosechadas.
  const free = lot.data ? Math.max(lot.data.area_ha - lot.data.current_seasons.reduce((total, s) => total + s.area_ha, 0), 0) : 0;
  const harvested = freeHarvested(seasons.data ?? []);
  const chosen = harvested.filter((s) => form.seasonIds.includes(s.season_id));
  const lotFacts: LotFacts | undefined = lot.data
    ? {
        lotId: lot.data.lot_id,
        municipalityId: lot.data.municipality_id,
        irrigated: lot.data.irrigated,
        // Lo de antes: las siembras elegidas; si no eligió ninguna y viene del diagnóstico, el cultivo que consultó.
        previous: chosen.length ? previousFromSeasons(chosen) : form.previousMode === "crops" ? form.previous.filter(Boolean) : [],
      }
    : undefined;
  const lotArea = chosen.length ? chosen.reduce((total, s) => total + s.area_ha, 0) : free;

  const allErrors: StrategyErrors = catalogsReady && lotReady ? validate(form, context) : {};
  const errors: StrategyErrors = Object.fromEntries(
    Object.entries(allErrors).filter(([field]) => tried || touched.has(field as StrategyField)),
  );

  const sent = fromParams(params);
  const sentLotReady = !sent.lotId || (sent.lotId === form.lotId && lot.isSuccess && seasons.isSuccess);
  const lotMissing = Boolean(sent.lotId) && !sessionLoading && (!user || lot.isError);
  const zeroPriorities = allZero(priorities);
  const request: RotationRequest | null =
    catalogsReady &&
    hasEntry(params) &&
    sentLotReady &&
    !lotMissing &&
    signalPriorities.ready &&
    !signalPriorities.allZero &&
    !zeroPriorities &&
    Object.keys(validate(sent, { ...context, lot: Boolean(sent.lotId) })).length === 0
      ? toRequest(sent, priorities, signalPriorities.value, sent.lotId ? lotFacts : undefined)
      : null;
  const rotations = useRotations(request);

  const change = (patch: Partial<StrategyForm>) => setForm((current) => ({ ...current, ...patch }));
  const setSlot = (key: "previous" | "current", index: number, value: string) => {
    const next = [...form[key]] as [string, string, string];
    next[index] = value;
    change({ [key]: next });
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!catalogsReady || !lotReady || Object.keys(validate(form, context)).length > 0) return;
    if (!form.lotId) writeArea(form.areaText.trim());
    setParams(toParams(form), { preventScrollReset: true });
  };

  // Con lote y el historial cargado, la rotación que viene haciendo se arma con él (se puede corregir).
  const chooseSeasons = (ids: string[]) => {
    const picked = harvested.filter((s) => ids.includes(s.season_id));
    const history = currentFromHistory(picked, seasons.data ?? []);
    change({
      seasonIds: ids,
      previousMode: ids.length ? "none" : form.previousMode,
      ...(history.length >= 2 ? { currentMode: "crops" as Mode, current: [history[0] ?? "", history[1] ?? "", history[2] ?? ""] } : {}),
    });
  };

  const cropOptions = (empty: string) => [
    { value: "", label: empty },
    ...(crops.data ?? []).map((crop) => ({ value: crop.crop_id, label: crop.name_es })),
  ];

  return (
    <div className="min-h-svh bg-paleta-niebla">
      <title>Estrategias de rotación · AgroSense</title>
      <TopBar />
      <main className="container-page pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        <header className="flex max-w-[880px] min-w-0 flex-col gap-3">
          <Eyebrow>Estrategias de rotación</Eyebrow>
          <h1 className="text-[clamp(1.75rem,4vw,3rem)]">¿Qué sembrar en los próximos ciclos?</h1>
          <p>
            Le mostramos estrategias de dos o tres ciclos que cumplen las reglas de rotación y se dan en su zona, comparadas por agua,
            suelo, ingreso y riesgo según lo que a usted le importa. Es la historia de su zona, no un pronóstico.
          </p>
        </header>

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card bodyClassName="gap-6">
            {municipalities.isError || crops.isError ? (
              <Alert>No pudimos cargar los municipios y los cultivos. Revise su conexión y recargue la página.</Alert>
            ) : (
              <form noValidate onSubmit={submit} className="flex min-w-0 flex-col gap-6" aria-label="Entrada a las estrategias">
                {myLots.length > 0 && (
                  <SelectField
                    label="¿Para cuál terreno?"
                    value={form.lotId}
                    onChange={(e) => change({ lotId: e.target.value, seasonIds: [] })}
                    options={[
                      { value: "", label: "Otro municipio, sin un lote" },
                      ...myLots.map((l) => ({
                        value: l.lot_id,
                        label: `${l.name} · ${placeName(places.get(l.municipality_id), l.municipality_id)}`,
                      })),
                    ]}
                    hint="Con uno de sus lotes, el municipio, el riego y lo que había antes salen del lote."
                  />
                )}

                {form.lotId ? (
                  lot.isError ? (
                    <Alert>No pudimos cargar ese lote. Puede que no sea suyo o que no haya entrado con su cuenta.</Alert>
                  ) : !lot.data || !seasons.data ? (
                    <p role="status" className="text-texto-secundario">
                      Cargando su lote…
                    </p>
                  ) : (
                    <>
                      <div className="flex flex-col gap-1 border-2 border-oscuro-cielo/60 bg-[#E6F0F5] px-4 py-3 text-[15px] leading-snug">
                        <p>
                          <span className="font-bold">Municipio:</span>{" "}
                          {placeName(places.get(lot.data.municipality_id), lot.data.municipality_id)}, el de su lote.
                        </p>
                        <p>
                          <span className="font-bold">{irrigationText(lot.data.irrigated)}</span>, según su lote.{" "}
                          <Link to={PATHS.editLot(lot.data.lot_id)} className={LINK}>
                            Cambiarlo en el lote
                          </Link>
                        </p>
                        <p>
                          <span className="font-bold">Área:</span>{" "}
                          {lotArea > 0
                            ? `${formatHa(lotArea)}${chosen.length ? ", la de lo que cosechó" : ", la libre del lote"}.`
                            : "hoy no queda terreno libre en el lote. Elija abajo lo que ya cosechó, si va a sembrar ahí."}
                        </p>
                      </div>
                      <PreviousChoice
                        options={harvested.map((s) => ({
                          id: s.season_id,
                          title: names.get(s.crop_id) ?? s.crop_id,
                          note: `${formatHa(s.area_ha)} · cosechada el ${formatShortDate(s.harvest_date!)}`,
                        }))}
                        value={form.seasonIds}
                        onChange={chooseSeasons}
                      />
                      {form.seasonIds.length === 0 && form.previousMode === "crops" && form.previous[0] && (
                        <p className="text-[15px] text-texto-secundario">
                          Viene del diagnóstico: tomamos {(names.get(form.previous[0]) ?? form.previous[0]).toLowerCase()} como lo que había
                          antes en el terreno.
                        </p>
                      )}
                    </>
                  )
                ) : (
                  <>
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
                    <TextField
                      label="Área del terreno, en hectáreas"
                      inputMode="decimal"
                      value={form.areaText}
                      onChange={(e) => change({ areaText: e.target.value })}
                      onBlur={() => touch("area")}
                      hint="Solo se usa en este dispositivo, para calcular el agua del plan. No se envía a AgroSense."
                      error={errors.area}
                    />
                    <Slots
                      legend="¿Qué había antes en el terreno?"
                      noneLabel="Nada: es la primera siembra aquí"
                      someLabel="Uno o más cultivos"
                      mode={form.previousMode}
                      values={form.previous}
                      labels={SLOT_LABELS}
                      options={cropOptions("—")}
                      error={errors.previous}
                      onMode={(previousMode) => {
                        change({ previousMode });
                        touch("previous");
                      }}
                      onSlot={(i, value) => {
                        setSlot("previous", i, value);
                        touch("previous");
                      }}
                    />
                  </>
                )}

                <SelectField
                  label="¿Cuándo sembraría el primer ciclo?"
                  value={form.month}
                  onChange={(e) => {
                    change({ month: e.target.value });
                    touch("month");
                  }}
                  options={[{ value: "", label: "Elija un mes" }, ...months]}
                  hint="Este mes o uno de los once siguientes. Los ciclos que siguen se siembran al cosechar el anterior."
                  error={errors.month}
                />

                {!form.lotId && (
                  <ChoiceGroup<Irrigation | "">
                    legend="¿Tiene riego?"
                    choices={IRRIGATION_CHOICES}
                    value={form.irrigation}
                    onChange={(irrigation) => {
                      change({ irrigation });
                      touch("irrigation");
                    }}
                    hint="Con riego, la falta de lluvia no se cuenta como riesgo. Si no sabe, se evalúa como sin riego."
                    error={errors.irrigation}
                  />
                )}

                <ChoiceGroup<2 | 3>
                  legend="¿Cuántos ciclos quiere planear?"
                  choices={[
                    { value: 2, label: "2 ciclos" },
                    { value: 3, label: "3 ciclos" },
                  ]}
                  value={form.cycles}
                  onChange={(cycles) => change({ cycles })}
                />

                <Slots
                  legend="¿Qué viene sembrando en este terreno?"
                  noneLabel="No tengo una rotación fija"
                  someLabel="Sí, en este orden"
                  mode={form.currentMode}
                  values={form.current}
                  labels={CURRENT_LABELS}
                  options={cropOptions("—")}
                  hint="Opcional. Si la dice, la comparamos con las estrategias: es su punto de partida."
                  error={errors.current}
                  onMode={(currentMode) => {
                    change({ currentMode });
                    touch("current");
                  }}
                  onSlot={(i, value) => {
                    setSlot("current", i, value);
                    touch("current");
                  }}
                />

                <details className="-mx-6 flex min-w-0 flex-col border-2 border-superficie-borde bg-superficie-panel-suave px-2 py-2 sm:mx-0 sm:px-4">
                  <summary className="flex min-h-11 cursor-pointer items-center font-bold">¿Qué busca en la rotación? · Ajustar</summary>
                  <div className="pt-2 pb-3">
                    <PriorityControl value={priorities} onChange={setPriorities} />
                  </div>
                </details>

                <Button type="submit" disabled={!catalogsReady} className="w-full sm:w-auto sm:self-start">
                  Ver estrategias
                </Button>
              </form>
            )}
          </Card>

          <Result
            request={request}
            month={sent.month}
            rotations={rotations}
            names={names}
            waitingLot={Boolean(sent.lotId) && !sentLotReady && !lotMissing}
            lotMissing={lotMissing}
            zeroPriorities={hasEntry(params) && (zeroPriorities || signalPriorities.allZero)}
          />
        </div>
      </main>
      <Footer />
    </div>
  );
}

function optionFor(id: string, places: Map<string, { name: string; department: string }>): Option | null {
  const place = places.get(id);
  return place ? { id, label: place.name, hint: place.department } : null;
}

/** «Nada / Uno o más» y, con «uno o más», hasta tres casillas en orden, sin huecos. */
function Slots({
  legend,
  noneLabel,
  someLabel,
  mode,
  values,
  labels,
  options,
  hint,
  error,
  onMode,
  onSlot,
}: {
  legend: string;
  noneLabel: string;
  someLabel: string;
  mode: Mode;
  values: [string, string, string];
  labels: string[];
  options: { value: string; label: string }[];
  hint?: string;
  error?: string;
  onMode: (mode: Mode) => void;
  onSlot: (index: number, value: string) => void;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <ChoiceGroup<Mode>
        legend={legend}
        choices={[
          { value: "none", label: noneLabel },
          { value: "crops", label: someLabel },
        ]}
        value={mode}
        onChange={onMode}
        hint={hint}
        error={mode === "crops" ? undefined : error}
      />
      {mode === "crops" && (
        <div className="grid grid-cols-1 gap-3">
          {labels.map((label, i) => (
            <SelectField key={label} label={label} value={values[i]} onChange={(e) => onSlot(i, e.target.value)} options={options} />
          ))}
          {error && (
            <p role="alert" className="text-[15px] leading-snug font-bold text-oscuro-rojo">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Result({
  request,
  month,
  rotations,
  names,
  waitingLot,
  lotMissing,
  zeroPriorities,
}: {
  request: RotationRequest | null;
  month: string;
  rotations: ReturnType<typeof useRotations>;
  names: Map<string, string>;
  waitingLot: boolean;
  lotMissing: boolean;
  zeroPriorities: boolean;
}) {
  const heading = (
    <h2 id="resultado" className="text-[clamp(1.25rem,3vw,1.75rem)]">
      {request ? `Estrategias desde ${monthName(month)}` : "Estrategias"}
    </h2>
  );
  if (!request) {
    return (
      <section aria-labelledby="resultado" className="flex min-w-0 flex-col gap-3">
        {heading}
        {zeroPriorities ? (
          <Alert>Todas sus prioridades están en 0. Suba al menos una para comparar estrategias.</Alert>
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
            {waitingLot ? "Cargando su lote…" : "Llene los datos de su terreno y toque «Ver estrategias»."}
          </p>
        )}
      </section>
    );
  }
  return (
    <section aria-labelledby="resultado" aria-busy={rotations.isPending || undefined} className="flex min-w-0 flex-col gap-4">
      {heading}
      {rotations.isPending ? (
        <p role="status">Comparando estrategias…</p>
      ) : rotations.isError ? (
        <Alert>{errorText(rotations.error)}</Alert>
      ) : (
        <Summary data={rotations.data} names={names} />
      )}
    </section>
  );
}

function errorText(error: Error): string {
  if (error instanceof ApiError && error.status === 422) return explain422(error.message);
  if (error instanceof ApiError && error.status === 501)
    return "El cálculo de las estrategias todavía no está listo en el servidor. Intente más tarde.";
  return error.message;
}

const sequence = (cropIds: string[], names: Map<string, string>) => cropIds.map((id) => names.get(id) ?? id).join(" → ");

/** Un resumen hasta que exista la lista completa (HU-102): cuántas, las primeras, la suya y cuántas se descartaron. */
function Summary({ data, names }: { data: RotationResponse; names: Map<string, string> }) {
  const top = data.strategies.slice(0, 3);
  const excluded = Object.values(data.excluded_counts ?? {}).reduce((total, n) => total + n, 0);
  return (
    <Card bodyClassName="gap-4">
      {data.versions.dataset === "ejemplo" && <ExampleLabel>respuesta simulada</ExampleLabel>}
      {top.length === 0 ? (
        <p className="font-bold">Ninguna estrategia cumple las reglas y se da en su zona con esos datos.</p>
      ) : (
        <>
          <p className="font-titulos text-[clamp(1.25rem,3vw,1.6rem)] leading-tight font-semibold">
            {data.strategies.length === 1 ? "Encontramos 1 estrategia" : `Encontramos ${data.strategies.length} estrategias`}
          </p>
          <ol className="flex flex-col gap-2">
            {top.map((strategy) => (
              <li key={strategy.crop_ids.join("-")} className="flex min-w-0 flex-col">
                <span className="font-bold">
                  {strategy.rank}. {sequence(strategy.crop_ids, names)}
                </span>
                {strategy.total_score !== null && strategy.total_score !== undefined && (
                  <span className="text-[15px] text-texto-secundario">
                    Puntaje con sus prioridades: {Math.round(strategy.total_score)} de 100
                  </span>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
      {data.current_strategy && (
        <p>
          <span className="font-bold">Su rotación actual:</span> {sequence(data.current_strategy.crop_ids, names)}
          {data.current_strategy.total_score !== null && data.current_strategy.total_score !== undefined
            ? ` · ${Math.round(data.current_strategy.total_score)} de 100`
            : ""}
        </p>
      )}
      {excluded > 0 && (
        <p className="text-[15px] text-texto-secundario">
          Se descartaron {excluded} combinaciones que no cumplen las reglas o tienen riesgo alto.
        </p>
      )}
      {data.limitations.length > 0 && (
        <List title="Limitaciones">
          {data.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </List>
      )}
      <p className="text-[15px] text-texto-secundario">
        Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo.
      </p>
      <p className="text-[15px] text-texto-secundario">Es información para decidir. La decisión es suya.</p>
    </Card>
  );
}

function List({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="font-bold">{title}</p>
      <ul className="flex list-disc flex-col gap-1 pl-5">{children}</ul>
    </div>
  );
}
