import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TextField } from "@/components/ui/TextField";
import {
  byId,
  formatHa,
  haText,
  parseHa,
  useDeleteLot,
  useLot,
  useMunicipalities,
  useUpdateLot,
  type LotDetail,
} from "@/features/farm/lots";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { AREA_ERROR, Eyebrow, IRRIGATION, IRRIGATION_HINT, NAME_ERROR, placeName } from "./common";

/**
 * Editar lote (HU-164). Figma: «D1 · Editar lote» y «confirmar borrar». Sin dibujo, el área se escribe (en vez del
 * contorno en el mapa, que llega con la entrega 2). Cambia el nombre, el área y el riego (PATCH /lots/{id}); «Borrar
 * este lote» pide confirmar (DELETE /lots/{id}). En escritorio va en dos columnas, para que quepa sin scroll.
 */
export function EditLotPage() {
  return <RequireSession>{() => <EditLotLoader />}</RequireSession>;
}

function EditLotLoader() {
  const { lotId = "" } = useParams();
  const lot = useLot(lotId);
  if (lot.isPending || lot.isError) {
    return (
      <FormScene scene="region" mood={lot.isError ? "no_data" : "idle"}>
        <title>Editar lote · AgroSense</title>
        {lot.isPending ? (
          <p role="status">Cargando el lote…</p>
        ) : (
          <>
            <Alert>
              {lot.error instanceof ApiError && lot.error.status === 404
                ? "Ese lote no existe o no es suyo."
                : "No pudimos cargar el lote. Intente de nuevo."}
            </Alert>
            <Link to={PATHS.farm} className={`${LINK} min-h-11 self-start py-2`}>
              Volver a Mi finca
            </Link>
          </>
        )}
      </FormScene>
    );
  }
  // Se monta con el lote ya cargado: el formulario parte de sus valores.
  return <EditLot lot={lot.data} />;
}

function EditLot({ lot }: { lot: LotDetail }) {
  const navigate = useNavigate();
  const update = useUpdateLot(lot.lot_id);
  const remove = useDeleteLot(lot.lot_id);
  const municipalities = useMunicipalities();
  const [name, setName] = useState(lot.name);
  const [area, setArea] = useState(haText(lot.area_ha));
  const [irrigated, setIrrigated] = useState<boolean | null>(lot.irrigated ?? null);
  const [tried, setTried] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const errors = { area: parseHa(area) === null ? AREA_ERROR : undefined, name: name.trim() ? undefined : NAME_ERROR };
  const sown = lot.current_seasons.reduce((sum, season) => sum + season.area_ha, 0);
  const crops = lot.current_seasons.length;
  const summary = `${crops === 0 ? "Sin siembra en curso" : crops === 1 ? "1 siembra en curso" : `${crops} siembras en curso`} · ${formatHa(lot.area_ha)}`;

  const save = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    const areaHa = parseHa(area);
    if (areaHa === null || errors.name) return;
    update.mutate(
      { name: name.trim(), area_ha: areaHa, irrigated },
      { onSuccess: () => void navigate(PATHS.lot(lot.lot_id), { state: { notice: "Cambios guardados." } }) },
    );
  };

  return (
    <FormScene scene="region" mood="idle" wide rejected={update.error ?? remove.error}>
      <title>{`Editar ${lot.name} · AgroSense`}</title>
      <header>
        <Eyebrow>Editar lote</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.name}</h1>
        <p className="text-[15px] text-texto-secundario">{summary}</p>
      </header>
      {update.isError && <Alert>{update.error instanceof ApiError ? update.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>}
      <form onSubmit={save} noValidate className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
          <div className="flex flex-col gap-4">
            <TextField
              label="Nombre del lote"
              name="name"
              maxLength={60}
              autoComplete="off"
              value={name}
              onChange={(event) => setName(event.target.value)}
              error={tried ? errors.name : undefined}
            />
            <TextField
              label="Área del lote (ha)"
              name="area_ha"
              inputMode="decimal"
              autoComplete="off"
              value={area}
              onChange={(event) => setArea(event.target.value)}
              hint={sown > 0 ? `No puede quedar más chico que lo sembrado (${formatHa(sown)}).` : "En hectáreas, escrita a mano."}
              error={tried ? errors.area : undefined}
            />
            <div>
              <p className="font-bold">Zona</p>
              <p>{placeName(byId(municipalities.data).get(lot.municipality_id), lot.municipality_id)}</p>
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <ChoiceGroup
              legend="¿Este lote tiene riego?"
              choices={IRRIGATION}
              value={irrigated}
              onChange={setIrrigated}
              hint={IRRIGATION_HINT}
            />
            <p className="bg-[#EEF2E6] px-4 py-3 text-[14px] leading-snug">
              Al cambiar el riego se recalculan el diagnóstico, las estrategias y el agua de este lote. Las siembras ya registradas guardan
              el diagnóstico que vieron.
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 items-center gap-2 lg:grid-cols-2 lg:gap-8">
          <Button type="submit" loading={update.isPending} loadingText="Guardando…">
            Guardar cambios
          </Button>
          <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-center justify-self-center py-2`}>
            Cancelar
          </Link>
        </div>
      </form>
      <section
        aria-labelledby="borrar"
        className="mt-1 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-t-2 border-superficie-borde pt-4"
      >
        <div className="min-w-0 flex-1 basis-[260px]">
          <h2 id="borrar" className="text-[18px]">
            Borrar este lote
          </h2>
          <p className="text-[14px] text-texto-secundario">Deja de verse con sus siembras y su historial.</p>
        </div>
        <Button variant="danger" className="w-full sm:w-[220px]" onClick={() => setConfirming(true)}>
          Borrar este lote
        </Button>
      </section>
      <ConfirmDialog
        open={confirming}
        onOpenChange={(next) => {
          setConfirming(next);
          if (!next) remove.reset();
        }}
        title={`¿Borrar ${lot.name}?`}
        cancelLabel="No, volver"
        confirmLabel="Sí, borrar el lote"
        busy={remove.isPending}
        busyLabel="Borrando…"
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => void navigate(PATHS.farm, { replace: true }) })}
      >
        <ul className="flex flex-col gap-2">
          {[
            crops > 0
              ? `Deja de verse en Mi finca con sus ${crops === 1 ? "siembra en curso" : `${crops} siembras en curso`} y su historial.`
              : "Deja de verse en Mi finca con su historial.",
          ].map((item) => (
            <li key={item} className="flex gap-3">
              <span aria-hidden="true" className="mt-1.5 block size-3.5 shrink-0 bg-oscuro-rojo" />
              {item}
            </li>
          ))}
        </ul>
        {remove.error && <Alert>{remove.error instanceof ApiError ? remove.error.message : "Algo falló. Intente de nuevo."}</Alert>}
      </ConfirmDialog>
    </FormScene>
  );
}
