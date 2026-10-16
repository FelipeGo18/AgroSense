import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { MapScene, PANEL_WIDTH } from "@/components/layout/MapScene";
import { LotMap, type DrawMode } from "@/components/map/LotMap";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TextField } from "@/components/ui/TextField";
import { areaHa, areaM2, formatM2, pointsOutside, type LotPolygon } from "@/features/farm/geo";
import {
  byId,
  formatHa,
  haText,
  parseHa,
  useBoundary,
  useDeleteLot,
  useLot,
  useMunicipalities,
  useUpdateLot,
  type LotDetail,
} from "@/features/farm/lots";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { DRAW_STEPS } from "./AddLotPage";
import { AREA_ERROR, DrawSteps, DrawnArea, Eyebrow, IRRIGATION, IRRIGATION_HINT, NAME_ERROR, OutsideWarning, placeName } from "./common";

/**
 * Editar lote (HU-164). Figma: «D1 · Editar lote» y «confirmar borrar». El contorno se corrige moviendo sus puntos en
 * el mapa; un lote sin dibujar se puede dibujar (con `?dibujar` el mapa abre listo para eso) o seguir con el área
 * escrita. Cambia el nombre, el contorno o el área y el riego (PATCH /lots/{id}); «Borrar este lote» pide confirmar.
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
  const [params] = useSearchParams();
  const update = useUpdateLot(lot.lot_id);
  const remove = useDeleteLot(lot.lot_id);
  const municipalities = useMunicipalities();
  const boundary = useBoundary(lot.municipality_id);
  const saved = lot.geometry as unknown as LotPolygon | null;
  const [geometry, setGeometry] = useState<LotPolygon | null>(saved);
  const [mode, setMode] = useState<DrawMode>(saved ? "move" : params.has("dibujar") ? "draw" : "view");
  const [name, setName] = useState(lot.name);
  const [area, setArea] = useState(haText(lot.area_ha));
  const [irrigated, setIrrigated] = useState<boolean | null>(lot.irrigated ?? null);
  const [tried, setTried] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const place = byId(municipalities.data).get(lot.municipality_id);
  const town = place?.name ?? "su municipio";
  const outside = Boolean(geometry && boundary.data && pointsOutside(geometry, boundary.data.geometry).length > 0);
  // Un lote dibujado sigue dibujado: si se borra el dibujo, hay que volver a dibujarlo antes de guardar.
  const errors = {
    area: !geometry && parseHa(area) === null ? AREA_ERROR : undefined,
    name: name.trim() ? undefined : NAME_ERROR,
    drawing: saved && !geometry ? "Vuelva a dibujar el contorno del lote." : undefined,
  };
  const sown = lot.current_seasons.reduce((sum, season) => sum + season.area_ha, 0);
  const crops = lot.current_seasons.length;
  const summary = `${placeName(place, lot.municipality_id)} · ${crops === 0 ? "Sin siembra en curso" : crops === 1 ? "1 siembra en curso" : `${crops} siembras en curso`}`;

  const save = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (outside || Object.values(errors).some(Boolean)) return;
    const changedDrawing = JSON.stringify(geometry) !== JSON.stringify(saved);
    update.mutate(
      {
        name: name.trim(),
        irrigated,
        ...(geometry ? (changedDrawing ? { geometry: { ...geometry } } : {}) : { area_ha: parseHa(area)! }),
      },
      { onSuccess: () => void navigate(PATHS.lot(lot.lot_id), { state: { notice: "Cambios guardados." } }) },
    );
  };

  return (
    <MapScene
      map={
        <LotMap
          boundary={boundary.data?.geometry ?? null}
          focus={saved}
          panelWidth={PANEL_WIDTH}
          drawing={{
            geometry,
            onChange: setGeometry,
            mode,
            onModeChange: setMode,
            areaLabel: geometry ? formatHa(areaHa(geometry)) : undefined,
            outside,
          }}
        />
      }
    >
      <title>{`Editar ${lot.name} · AgroSense`}</title>
      <header>
        <Eyebrow>Editar lote</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.name}</h1>
        <p className="text-[15px] text-texto-secundario">{summary}</p>
      </header>
      {mode === "draw" && <DrawSteps steps={DRAW_STEPS} />}
      {update.isError && <Alert>{update.error instanceof ApiError ? update.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>}
      <form onSubmit={save} noValidate className="flex flex-col gap-4">
        {outside ? (
          <OutsideWarning place={town} />
        ) : geometry ? (
          <>
            <DrawnArea ha={formatHa(areaHa(geometry))} m2={formatM2(areaM2(geometry))} />
            <p className="-mt-2 text-[14px] text-texto-secundario">
              Mueva los puntos en el mapa para cambiar el contorno.
              {sown > 0 && ` No puede quedar más chico que lo sembrado (${formatHa(sown)}).`}
            </p>
          </>
        ) : (
          <>
            {tried && errors.drawing && (
              <p role="alert" className="font-bold text-oscuro-rojo">
                {errors.drawing}
              </p>
            )}
            {!saved && (
              <TextField
                label="Área del lote (ha)"
                name="area_ha"
                inputMode="decimal"
                autoComplete="off"
                value={area}
                onChange={(event) => setArea(event.target.value)}
                hint={
                  sown > 0
                    ? `No puede quedar más chico que lo sembrado (${formatHa(sown)}).`
                    : "Escrita a mano. O dibuje el lote en el mapa."
                }
                error={tried ? errors.area : undefined}
              />
            )}
          </>
        )}
        <TextField
          label="Nombre del lote"
          name="name"
          maxLength={60}
          autoComplete="off"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={tried ? errors.name : undefined}
        />
        <ChoiceGroup
          legend="¿Este lote tiene riego?"
          choices={IRRIGATION}
          value={irrigated}
          onChange={setIrrigated}
          hint={IRRIGATION_HINT}
        />
        <p className="bg-[#EEF2E6] px-4 py-3 text-[14px] leading-snug">
          Al cambiar el riego se recalculan el diagnóstico, las estrategias y el agua de este lote. Las siembras ya registradas guardan el
          diagnóstico que vieron.
        </p>
        <Button type="submit" disabled={outside} loading={update.isPending} loadingText="Guardando…">
          Guardar cambios
        </Button>
        <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-center py-2`}>
          Cancelar
        </Link>
      </form>
      <section aria-labelledby="borrar" className="flex flex-col gap-2 border-t-2 border-superficie-borde pt-4">
        <h2 id="borrar" className="text-[18px]">
          Borrar este lote
        </h2>
        <p className="text-[14px] text-texto-secundario">Deja de verse con sus siembras y su historial.</p>
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
    </MapScene>
  );
}
