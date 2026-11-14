import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { PriorityControl } from "@/components/ui/PriorityControl";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { useSession } from "@/features/auth/session";
import { IRRIGATION_CHOICES, monthName, sowingMonths, type Irrigation } from "@/features/diagnosis/consult";
import { useSignalPriorities } from "@/features/diagnosis/priorities";
import { SOIL_ESTIMATE, phRange, useMunicipalitySoil } from "@/features/diagnosis/signals";
import { byId, formatHa, useLot, useLots, useMunicipalities } from "@/features/farm/lots";
import { cropNames, formatShortDate, useCrops, useSeasons } from "@/features/farm/seasons";
import {
  START_PRIORITIES,
  allZero,
  currentFromHistory,
  freeHarvested,
  fromParams,
  hasEntry,
  parseArea,
  previousFromSeasons,
  toParams,
  toRequest,
  useRotations,
  validate,
  writeArea,
  writeGuestConsult,
  type LotFacts,
  type Mode,
  type RotationRequest,
  type RotationWeights,
  type StrategyErrors,
  type StrategyField,
  type StrategyForm,
} from "@/features/strategies/entry";
import { cycleParams, findCycle, strategyKey, withoutCycle } from "@/features/strategies/cycle";
import { sequence, socRange } from "@/features/strategies/strategies";
import { useVersion } from "@/features/version";
import { irrigationText, placeName } from "@/pages/farm/common";
import { PreviousChoice } from "@/pages/farm/SeasonParts";
import { CycleView } from "./CycleView";
import { StrategyResults } from "./StrategyResults";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";
const SLOT_LABELS = ["Lo último que sembró", "Lo de antes", "Lo de antes de eso"];
const CURRENT_LABELS = ["Primero siembra", "Después", "Después (si son tres)"];
const IRRIGATION_WORDS: Record<Irrigation, string> = {
  si: "con riego",
  no: "sin riego",
  nose: "sin saber si tiene riego (se evalúa sin riego)",
};

/**
 * Estrategias de rotación, la entrada principal del MVP (decisión 12): «Consultar» lleva aquí.
 *
 * - **La entrada (HU-214):** sin cuenta pide municipio, área, qué había antes, cuándo sembrar el primer ciclo, riego,
 *   cuántos ciclos y la rotación que viene haciendo (HU-223). Con cuenta, desde un lote: su municipio, su riego, el
 *   terreno que va a sembrar y su historial.
 * - **El resultado (HU-102):** un resumen de la entrada con «Cambiar», las prioridades de la rotación al lado (HU-101:
 *   al moverlas el orden cambia), lo que siembra hoy, las estrategias en orden, las descartadas y el estado vacío.
 *
 * Las prioridades de la rotación empiezan iguales; las de las señales son las de la consulta del diagnóstico (HU-202).
 * Es una página quieta: nada se anima.
 */
export function StrategiesPage() {
  const [params, setParams] = useSearchParams();
  const { user, loading: sessionLoading } = useSession();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  const version = useVersion();
  const lots = useLots(Boolean(user));
  const myLots = user ? (lots.data ?? []) : [];
  const months = useMemo(() => sowingMonths(), []);
  const signalPriorities = useSignalPriorities();
  const [priorities, setPriorities] = useState<RotationWeights>(START_PRIORITIES);

  const [form, setForm] = useState<StrategyForm>(() => fromParams(params));
  const [tried, setTried] = useState(() => hasEntry(params));
  const [editing, setEditing] = useState(false);
  const [touched, setTouched] = useState<ReadonlySet<StrategyField>>(() => new Set());
  const touch = (field: StrategyField) => setTouched((current) => (current.has(field) ? current : new Set(current).add(field)));
  // Si la dirección cambia desde afuera (por ejemplo, volver atrás), la página la muestra.
  const search = params.toString();
  const [shownSearch, setShownSearch] = useState(search);
  if (search !== shownSearch) {
    setShownSearch(search);
    setForm(fromParams(params));
    setTouched(new Set());
    setTried(hasEntry(params));
    setEditing(false);
  }

  // El lote de la consulta: el del formulario mientras se llena, el de la dirección para consultar.
  const lot = useLot(form.lotId);
  const seasons = useSeasons(form.lotId);
  const places = byId(municipalities.data);
  const names = cropNames(crops.data);
  const kinds = new Map((crops.data ?? []).map((crop) => [crop.crop_id, crop.kind]));
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

  // Lo que se consultó: lo de la dirección. Se muestra el resultado si es válido y no se está cambiando.
  const sent = fromParams(params);
  const sentLotReady = !sent.lotId || (sent.lotId === form.lotId && lot.isSuccess && seasons.isSuccess);
  const lotMissing = Boolean(sent.lotId) && !sessionLoading && (!user || lot.isError);
  const sentErrors = catalogsReady && sentLotReady ? validate(sent, { ...context, lot: Boolean(sent.lotId) }) : null;
  const sentValid = hasEntry(params) && !lotMissing && sentErrors !== null && Object.keys(sentErrors).length === 0;
  const resolving = hasEntry(params) && !editing && !lotMissing && sentErrors === null && !municipalities.isError && !crops.isError;
  const showResult = sentValid && !editing;
  const zeroPriorities = allZero(priorities) || signalPriorities.allZero;
  const request: RotationRequest | null =
    sentValid && signalPriorities.ready && !zeroPriorities
      ? toRequest(sent, priorities, signalPriorities.value, sent.lotId ? lotFacts : undefined)
      : null;
  const rotations = useRotations(request);
  const soil = useMunicipalitySoil(showResult && rotations.data?.soil_basis === "municipality" ? request?.municipality_id : null);
  // El ciclo abierto (HU-215): `estrategia` y `ciclo` en la dirección. Si no existe en la respuesta, se ve la lista.
  const openCycle =
    showResult && request && !zeroPriorities ? findCycle(rotations.data, params.get("estrategia"), params.get("ciclo")) : null;
  const areaHa = sent.lotId ? (lot.data ? lotArea : null) : parseArea(sent.areaText);

  // Al volver a la entrada desde el resultado, el foco va a su título: el contenido cambió de lugar.
  const formTitle = useRef<HTMLHeadingElement>(null);
  const focusForm = useRef(false);
  useEffect(() => {
    if (focusForm.current && !showResult) {
      formTitle.current?.focus();
      focusForm.current = false;
    }
  }, [showResult]);

  const change = (patch: Partial<StrategyForm>) => setForm((current) => ({ ...current, ...patch }));
  const setSlot = (key: "previous" | "current", index: number, value: string) => {
    const next = [...form[key]] as [string, string, string];
    next[index] = value;
    change({ [key]: next });
  };
  const edit = (patch: Partial<StrategyForm> = {}) => {
    setForm({ ...fromParams(params), ...patch });
    setTouched(new Set());
    setTried(false);
    setEditing(true);
    focusForm.current = true;
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!catalogsReady || !lotReady || Object.keys(validate(form, context)).length > 0) return;
    if (!form.lotId) writeArea(form.areaText.trim());
    if (!user && !form.lotId) writeGuestConsult(form);
    setEditing(false);
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
        {openCycle && request ? (
          <CycleView
            open={openCycle}
            params={params}
            backTo={`${PATHS.consult}?${withoutCycle(params)}`}
            municipalityId={request.municipality_id}
            irrigated={request.irrigated}
            areaHa={areaHa}
            names={names}
            kinds={kinds}
            version={version.data}
            signedIn={Boolean(user)}
            versions={rotations.data!.versions}
            lot={sent.lotId ? { lotId: sent.lotId, follows: sent.seasonIds } : null}
          />
        ) : showResult ? (
          <>
            <Card bodyClassName="gap-8">
              <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
                <EntrySummary
                  place={sent.lotId && lot.data ? lot.data.municipality_id : sent.municipalityId}
                  places={places}
                  title={`Estrategias para los próximos ${sent.cycles} ciclos`}
                  rows={summaryRows(
                    sent,
                    names,
                    lot.data && sent.lotId ? { name: lot.data.name, area: lotArea, irrigated: lot.data.irrigated } : null,
                    lotFacts?.previous,
                  )}
                  soilBasis={rotations.data?.soil_basis ?? null}
                  soil={soil.data}
                  onEdit={() => edit()}
                />
                <section aria-labelledby="prioridades" className="flex min-w-0 flex-col gap-2">
                  <h2 id="prioridades" className="text-[clamp(1.15rem,2.5vw,1.4rem)]">
                    ¿Qué busca en la rotación?
                  </h2>
                  <p className="text-[15px] text-texto-secundario">Toque las semillas: el orden cambia al instante.</p>
                  <div className="-mx-6 px-2 sm:mx-0 sm:px-0">
                    <PriorityControl value={priorities} onChange={setPriorities} />
                  </div>
                </section>
              </div>
            </Card>
            {zeroPriorities ? (
              <div className="mt-8">
                <Alert>Todas sus prioridades están en 0. Suba al menos una para comparar estrategias.</Alert>
              </div>
            ) : request === null ? (
              <p role="status" className="mt-8">
                Comparando estrategias…
              </p>
            ) : (
              <StrategyResults
                rotations={rotations}
                weights={priorities}
                cycles={sent.cycles}
                names={names}
                kinds={kinds}
                version={version.data}
                onEdit={() => edit()}
                onWriteCurrent={() => edit({ currentMode: "crops" })}
                onTwoCycles={() => setParams(toParams({ ...sent, cycles: 2 }), { preventScrollReset: true })}
                cycleLink={(strategy, n) => `${PATHS.consult}?${cycleParams(params, strategyKey(strategy), n)}`}
              />
            )}
            {!user && !sessionLoading && (
              <Card bodyClassName="gap-3">
                <h2 className="text-[clamp(1.15rem,2.5vw,1.4rem)]">¿Quiere guardar este lote?</h2>
                <p>
                  Cree su cuenta y lo que acaba de consultar se convierte en su primer lote, listo para registrar siembras y ver su
                  historial.
                </p>
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                  <ButtonLink to={PATHS.signup} onClick={() => writeGuestConsult(sent)}>
                    Crear cuenta
                  </ButtonLink>
                  <span>
                    ¿Ya tiene cuenta?{" "}
                    <Link
                      to={PATHS.login}
                      onClick={() => writeGuestConsult(sent)}
                      className={`${LINK} inline-flex min-h-11 min-w-11 items-center justify-center`}
                    >
                      Entrar
                    </Link>
                  </span>
                </div>
              </Card>
            )}
          </>
        ) : (
          <div className="flex max-w-[760px] min-w-0 flex-col gap-8">
            <header className="flex min-w-0 flex-col gap-3">
              <Eyebrow>Estrategias de rotación</Eyebrow>
              <h1 ref={formTitle} tabIndex={-1} className="text-[clamp(1.75rem,4vw,3rem)] outline-none">
                ¿Qué sembrar en los próximos ciclos?
              </h1>
              <p>
                Le mostramos estrategias de dos o tres ciclos que cumplen las reglas de rotación y se dan en su zona, comparadas por agua,
                suelo, ingreso y riesgo según lo que a usted le importa. Es la historia de su zona, no un pronóstico.
              </p>
            </header>

            {lotMissing && (
              <Alert>
                Ese lote no está entre los suyos o no ha entrado con su cuenta.{" "}
                <Link to={PATHS.login} className={LINK}>
                  Entrar
                </Link>{" "}
                o elija un municipio.
              </Alert>
            )}

            {resolving ? (
              <p role="status">Cargando su consulta…</p>
            ) : (
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
                              Viene del diagnóstico: tomamos {(names.get(form.previous[0]) ?? form.previous[0]).toLowerCase()} como lo que
                              había antes en el terreno.
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
                          hint="Solo se usa para calcular el agua que necesitaría cada ciclo. No se guarda."
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
                      <summary className="flex min-h-11 cursor-pointer items-center font-bold">
                        ¿Qué busca en la rotación? · Ajustar
                      </summary>
                      <div className="pt-2 pb-3">
                        <PriorityControl value={priorities} onChange={setPriorities} />
                      </div>
                    </details>

                    <div className="flex flex-wrap gap-3">
                      <Button type="submit" disabled={!catalogsReady} className="w-full sm:w-auto">
                        Ver estrategias
                      </Button>
                      {editing && sentValid && (
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-full sm:w-auto"
                          onClick={() => {
                            setEditing(false);
                            setForm(fromParams(params));
                          }}
                        >
                          Volver sin cambiar
                        </Button>
                      )}
                    </div>
                  </form>
                )}
              </Card>
            )}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

interface SummaryRow {
  label: string;
  value: string;
}

/** Lo que se consultó, en palabras: el terreno y lo de antes, lo que viene sembrando, el primer ciclo y el riego. */
function summaryRows(
  sent: StrategyForm,
  names: Map<string, string>,
  lot: { name: string; area: number; irrigated: boolean | null } | null,
  lotPrevious: string[] | undefined,
): SummaryRow[] {
  const previous = lot ? (lotPrevious ?? []) : sent.previousMode === "none" ? [] : sent.previous.filter(Boolean);
  const before = previous.length ? `antes: ${sequence(previous, names).toLowerCase()}` : "antes: nada, es la primera siembra";
  const area = parseArea(sent.areaText);
  const land = lot
    ? `${lot.name} · ${formatHa(lot.area)} · ${before}`
    : `${area === null ? "Sin área" : formatHa(area)} · ${before} · sin cuenta`;
  const current = sent.currentMode === "crops" ? sequence(sent.current.filter(Boolean), names) : "No tiene una rotación fija";
  const water = lot ? irrigationText(lot.irrigated).toLowerCase() : sent.irrigation ? IRRIGATION_WORDS[sent.irrigation] : "";
  return [
    { label: "Terreno y lo que había antes", value: land },
    { label: "Lo que viene sembrando", value: current },
    { label: "Primer ciclo y riego", value: `${monthName(sent.month)} · ${water}` },
  ];
}

/**
 * El resumen de la consulta con «Cambiar» (vuelve a la entrada con lo escrito) y el suelo que se usó, con su rango y el
 * rótulo de estimación (R10). El suelo del lote llega con HU-182: hasta entonces se dice de dónde sale, sin cifras.
 */
function EntrySummary({
  place,
  places,
  title,
  rows,
  soilBasis,
  soil,
  onEdit,
}: {
  place: string;
  places: Map<string, { name: string; department: string }>;
  title: string;
  rows: SummaryRow[];
  soilBasis: "lot" | "municipality" | null;
  soil: Parameters<typeof phRange>[0];
  onEdit: () => void;
}) {
  const town = places.get(place);
  const where = town ? `${town.name}, ${town.department}` : place;
  const soilValues = [phRange(soil), socRange(soil)].filter(Boolean).join(" · ");
  return (
    <section aria-labelledby="consulta" className="flex min-w-0 flex-col gap-3">
      <Eyebrow>Estrategias · {where}</Eyebrow>
      <h1 id="consulta" className="text-[clamp(1.5rem,3.5vw,2.25rem)] leading-tight">
        {title}
      </h1>
      <ul className="flex flex-col gap-2">
        {rows.map((row) => (
          <li
            key={row.label}
            className="flex min-w-0 flex-wrap items-start justify-between gap-x-3 gap-y-1 bg-superficie-panel-suave px-4 py-2.5"
          >
            <div className="flex min-w-0 flex-col">
              <p className="text-[14px] text-texto-secundario">{row.label}</p>
              <p className="font-bold break-words">{row.value}</p>
            </div>
            <button type="button" onClick={onEdit} className={`${LINK} min-h-11`} aria-label={`Cambiar: ${row.label.toLowerCase()}`}>
              Cambiar
            </button>
          </li>
        ))}
        {soilBasis && (
          <li className="flex min-w-0 flex-col bg-superficie-panel-suave px-4 py-2.5">
            <p className="text-[14px] text-texto-secundario">
              {soilBasis === "lot" ? "Suelo estimado de su lote · 250 m" : `Suelo estimado de ${town?.name ?? "su municipio"} · 250 m`}
            </p>
            <p className="font-bold break-words">
              {soilBasis === "lot" ? "El que usó el cálculo para su lote" : soilValues || "Sin rango publicado"}
            </p>
          </li>
        )}
      </ul>
      {soilBasis && <p className="text-[15px] text-texto-secundario">{SOIL_ESTIMATE}</p>}
    </section>
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
