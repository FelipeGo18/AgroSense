import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { TextField } from "@/components/ui/TextField";
import { byId, parseHa, useCreateLot, useLots, useMunicipalities, type Municipality } from "@/features/farm/lots";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { AREA_ERROR, AREA_HINT, Eyebrow, IRRIGATION, IRRIGATION_HINT, NAME_ERROR, WithoutDrawing, placeName } from "./common";
import { ZoneChoice } from "./ZoneChoice";

const OTHER = "otro";
const option = (m: Municipality): Option => ({ id: m.municipality_id, label: m.name, hint: m.department });

/**
 * Agregar lote (HU-164, HU-169), entrega 1. Figma: «D0 · Agregar lote o zona» y «Lote sin dibujar / Área a mano».
 * Paso 1: dónde está (una zona donde ya tiene lotes u otro municipio). Paso 2: el lote sin dibujar (área a mano,
 * nombre y riego), en dos columnas en escritorio para que quepa sin scroll. El mapa llega con la entrega 2.
 */
export function AddLotPage() {
  return <RequireSession>{() => <AddLot />}</RequireSession>;
}

function AddLot() {
  const navigate = useNavigate();
  const municipalities = useMunicipalities();
  const lots = useLots();
  const create = useCreateLot();
  const places = byId(municipalities.data);
  // Las zonas donde ya tiene lotes, con cuántos lotes tiene en cada una, en el orden en que las agregó.
  const counts = new Map<string, number>();
  for (const lot of lots.data ?? [])
    if (places.has(lot.municipality_id)) counts.set(lot.municipality_id, (counts.get(lot.municipality_id) ?? 0) + 1);
  const zones = [...counts.keys()];

  const [step, setStep] = useState<1 | 2>(1);
  const [zone, setZone] = useState<string | null>(null);
  const [other, setOther] = useState<Option | null>(null);
  const [area, setArea] = useState("");
  const [name, setName] = useState("");
  const [irrigated, setIrrigated] = useState<boolean | null>(null);
  const [tried, setTried] = useState(false);

  const chosenZone = zone ?? zones[0] ?? OTHER;
  const municipalityId = chosenZone === OTHER ? (other?.id ?? null) : chosenZone;
  const municipality = municipalityId ? places.get(municipalityId) : undefined;
  const errors = { area: parseHa(area) === null ? AREA_ERROR : undefined, name: name.trim() ? undefined : NAME_ERROR };

  const save = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    const areaHa = parseHa(area);
    if (!municipalityId || areaHa === null || errors.name) return;
    create.mutate(
      { name: name.trim(), municipality_id: municipalityId, area_ha: areaHa, irrigated },
      { onSuccess: (lot) => void navigate(PATHS.lot(lot.lot_id), { state: { notice: "Lote guardado." } }) },
    );
  };

  const cancel = (
    <Link to={PATHS.farm} className={`${LINK} min-h-11 self-center py-2`}>
      Cancelar
    </Link>
  );

  return (
    <FormScene scene="region" mood={step === 2 ? "idle" : "guide"} wide={step === 2} rejected={create.error}>
      <title>Agregar lote · AgroSense</title>
      {municipalities.isPending ? (
        <p role="status">Cargando los municipios…</p>
      ) : municipalities.isError ? (
        <>
          <Alert>
            {municipalities.error instanceof ApiError && municipalities.error.status === 503
              ? municipalities.error.message
              : "No pudimos cargar los municipios. Intente de nuevo en un momento."}
          </Alert>
          <Button variant="secondary" className="self-start" onClick={() => void municipalities.refetch()}>
            Volver a intentar
          </Button>
          {cancel}
        </>
      ) : step === 1 ? (
        <>
          <header>
            <Eyebrow>Agregar lote</Eyebrow>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">¿Dónde está el lote nuevo?</h1>
          </header>
          {zones.length > 0 && (
            <ZoneChoice
              legend="En una zona donde ya tiene lotes"
              choices={[
                ...zones.map((id) => ({
                  value: id,
                  title: placeName(places.get(id), id),
                  note: counts.get(id) === 1 ? "1 lote" : `${counts.get(id)} lotes`,
                })),
                { value: OTHER, title: "En otro municipio", note: "Se agrega como una zona nueva" },
              ]}
              value={chosenZone}
              onChange={setZone}
            />
          )}
          {chosenZone === OTHER && (
            <div className="flex flex-col gap-1">
              <Combobox
                label="Municipio"
                options={municipalities.data.map(option)}
                value={other}
                onChange={setOther}
                placeholder="Escriba el nombre del municipio"
                emptyText="Ese municipio no está en la región de AgroSense. Revise cómo lo escribió."
              />
              <p className="text-[15px] text-texto-secundario">Solo aparecen los municipios con datos de la región piloto.</p>
            </div>
          )}
          {tried && !municipalityId && (
            <p role="alert" className="font-bold text-oscuro-rojo">
              Elija el municipio de su lote.
            </p>
          )}
          <Button
            className="mt-1"
            onClick={() => {
              setTried(!municipalityId);
              if (municipalityId) setStep(2);
            }}
          >
            Seguir
          </Button>
          {cancel}
        </>
      ) : (
        <>
          <button type="button" onClick={() => setStep(1)} className={`${LINK} min-h-11 self-start`}>
            ‹ {placeName(municipality, municipalityId!)}
          </button>
          <header>
            <Eyebrow>Paso 2 de 2</Eyebrow>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Su lote, sin dibujar</h1>
          </header>
          {create.isError && (
            <Alert>{create.error instanceof ApiError ? create.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>
          )}
          <form onSubmit={save} noValidate className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
              <div className="flex flex-col gap-4">
                <TextField
                  label="Área del lote (ha)"
                  name="area_ha"
                  inputMode="decimal"
                  autoComplete="off"
                  placeholder="2,5"
                  value={area}
                  onChange={(event) => setArea(event.target.value)}
                  hint={AREA_HINT}
                  error={tried ? errors.area : undefined}
                />
                <TextField
                  label="Nombre del lote"
                  name="name"
                  maxLength={60}
                  autoComplete="off"
                  placeholder="La Esperanza"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  error={tried ? errors.name : undefined}
                />
              </div>
              <div className="flex flex-col gap-4">
                <WithoutDrawing place={municipality?.name ?? "su municipio"} />
                <ChoiceGroup
                  legend="¿Este lote tiene riego?"
                  choices={IRRIGATION}
                  value={irrigated}
                  onChange={setIrrigated}
                  hint={IRRIGATION_HINT}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 items-center gap-2 lg:grid-cols-2 lg:gap-8">
              <Button type="submit" loading={create.isPending} loadingText="Guardando…">
                Guardar lote
              </Button>
              {cancel}
            </div>
          </form>
        </>
      )}
    </FormScene>
  );
}
