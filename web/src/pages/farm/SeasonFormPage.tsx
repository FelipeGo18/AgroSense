import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { formatHa, haText, parseHa, useLot, type LotDetail } from "@/features/farm/lots";
import {
  cropNames,
  formatDate,
  formatShortDate,
  todayIso,
  useCreateSeason,
  useCrops,
  useDeleteSeason,
  useSeasons,
  useUpdateSeason,
  type Crop,
  type Season,
  type SowPlan,
} from "@/features/farm/seasons";
import { LIGHT_LABEL, type Light } from "@/components/ui/TrafficLightBadge";
import { useEntrance } from "@/hooks/useEntrance";
import { AccountShell, LINK } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { AREA_ERROR } from "./common";
import { LotBar, PreviousChoice, type Part } from "./SeasonParts";

/**
 * Registrar la siembra (HU-165). Figma: «E · Registrar siembra». Qué había antes en ese terreno (una o varias siembras
 * cosechadas, o nada), el cultivo, el área y la fecha. A la derecha, cómo queda el lote. Con `?despues=` viene de
 * registrar esa cosecha y la deja marcada.
 */
export function SowPage() {
  return <SeasonScreen mode="create" />;
}

/** Corregir o borrar una siembra (HU-165). Figma: «Siembra / Editar» y «Confirmar borrar». */
export function EditSeasonPage() {
  return <SeasonScreen mode="edit" />;
}

function SeasonScreen({ mode }: { mode: "create" | "edit" }) {
  const { lotId = "", seasonId = "" } = useParams();
  const lot = useLot(lotId);
  const seasons = useSeasons(lotId);
  const crops = useCrops();
  const season = mode === "edit" ? seasons.data?.find((s) => s.season_id === seasonId) : undefined;
  const failed = lot.isError || seasons.isError || crops.isError || (mode === "edit" && seasons.isSuccess && !season);
  const loading = lot.isPending || seasons.isPending || crops.isPending;
  return (
    <AccountShell>
      {() =>
        failed ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <Alert>
              {lot.error instanceof ApiError && lot.error.status === 404
                ? "Ese lote no existe o no es suyo."
                : mode === "edit" && seasons.isSuccess && !season
                  ? "Esa siembra no existe o no es suya."
                  : "No pudimos cargar los datos. Intente de nuevo en un momento."}
            </Alert>
          </Shell>
        ) : loading ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <p role="status">Cargando…</p>
          </Shell>
        ) : (
          <SeasonForm mode={mode} lot={lot.data!} seasons={seasons.data!} crops={crops.data!} season={season} />
        )
      }
    </AccountShell>
  );
}

/** El marco de las pantallas de siembra y cosecha: «‹ lote» y el contenido, con la entrada de la página. */
export function Shell({ lotId, lotName, children, aside }: { lotId: string; lotName?: string; children: ReactNode; aside?: ReactNode }) {
  const page = useEntrance<HTMLDivElement>();
  return (
    <div ref={page} className="container-page flex flex-col gap-5 pt-[112px] md:pt-[128px]">
      <Link to={PATHS.lot(lotId)} className={`${LINK} min-h-11 self-start py-2`}>
        ‹ {lotName ?? "El lote"}
      </Link>
      <div className="grid grid-cols-1 items-start gap-7 lg:grid-cols-[minmax(0,560px)_minmax(0,1fr)]">
        <div data-enter>
          <Card bodyClassName="gap-4">{children}</Card>
        </div>
        {aside && <div data-enter>{aside}</div>}
      </div>
    </div>
  );
}

const sum = (values: number[]) => values.reduce((total, value) => total + value, 0);

function SeasonForm({
  mode,
  lot,
  seasons,
  crops,
  season,
}: {
  mode: "create" | "edit";
  lot: LotDetail;
  seasons: Season[];
  crops: Crop[];
  season?: Season;
}) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const names = cropNames(crops);
  const create = useCreateSeason(lot.lot_id);
  const update = useUpdateSeason(lot.lot_id, season?.season_id ?? "");
  const remove = useDeleteSeason(lot.lot_id, season?.season_id ?? "");
  const saving = mode === "create" ? create : update;
  const after = params.get("despues");
  // Desde el primer ciclo de una estrategia llega la siembra armada, con el diagnóstico que vio (HU-215).
  const location = useLocation();
  const plan = mode === "create" ? (location.state as { plan?: SowPlan } | null)?.plan : undefined;

  const [follows, setFollows] = useState<string[]>(
    season ? season.follows_season_ids : plan ? plan.follows_season_ids : after ? [after] : [],
  );
  const [crop, setCrop] = useState(season?.crop_id ?? plan?.crop_id ?? "");
  const [sowing, setSowing] = useState(season?.sowing_date ?? plan?.sowing_date ?? todayIso());
  const [tried, setTried] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // Lo que ocupan las demás siembras en curso; si se corrige una en curso, no se cuenta a sí misma.
  const others = lot.current_seasons.filter((s) => s.season_id !== season?.season_id);
  const free = Math.max(lot.area_ha - sum(others.map((s) => s.area_ha)), 0);

  // Lo de antes: siembras cosechadas del lote, cosechadas el día de la siembra o antes (y nunca la misma).
  const options = seasons
    .filter((s) => s.harvest_date && s.season_id !== season?.season_id && s.harvest_date <= sowing)
    .map((s) => {
      const next = seasons.filter((n) => n.season_id !== season?.season_id && n.follows_season_ids.includes(s.season_id));
      return {
        id: s.season_id,
        ha: s.area_ha,
        title: names.get(s.crop_id) ?? s.crop_id,
        note: `${formatHa(s.area_ha)} · cosechada el ${formatShortDate(s.harvest_date!)}${
          next.length ? ` · después vino ${next.map((n) => (names.get(n.crop_id) ?? n.crop_id).toLowerCase()).join(" y ")}` : ""
        }`,
      };
    });
  const chosen = follows.filter((id) => options.some((o) => o.id === id));

  // Mientras no lo escriba, el área sugerida es la de lo que había antes (si cabe) o todo lo libre.
  const [areaText, setArea] = useState<string | null>(season ? haText(season.area_ha) : plan ? haText(plan.area_ha) : null);
  const before = sum(options.filter((o) => chosen.includes(o.id)).map((o) => o.ha));
  const area = areaText ?? haText(Math.round((before > 0 ? Math.min(before, free) : free) * 100) / 100);
  const areaHa = parseHa(area);
  const harvested = !!season?.harvest_date;

  // El diagnóstico de la estrategia vale mientras no cambien el cultivo ni la fecha: es el de esa ventana.
  const planHolds = Boolean(plan && crop === plan.crop_id && sowing === plan.sowing_date);
  const planLight = plan?.diagnosis.diagnosis_light as Light | null | undefined;

  const errors = {
    crop: crop ? undefined : "Elija el cultivo.",
    area:
      areaHa === null
        ? AREA_ERROR
        : !harvested && areaHa > free + 0.00001
          ? `No cabe: en el lote quedan ${formatHa(free)} libres.`
          : undefined,
    sowing: !sowing
      ? "Escriba la fecha de siembra."
      : sowing > todayIso()
        ? "La fecha de siembra no puede ser posterior a hoy."
        : undefined,
  };
  const save = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (Object.values(errors).some(Boolean) || areaHa === null) return;
    const body = {
      crop_id: crop,
      sowing_date: sowing,
      area_ha: areaHa,
      follows_season_ids: chosen,
      ...(planHolds && plan ? plan.diagnosis : {}),
    };
    const notice = mode === "create" ? `Siembra de ${(names.get(crop) ?? crop).toLowerCase()} registrada.` : "Cambios guardados.";
    const done = () => void navigate(PATHS.lot(lot.lot_id), { state: { notice } });
    if (mode === "create") create.mutate(body, { onSuccess: done });
    else update.mutate(body, { onSuccess: done });
  };

  const name = crop ? (names.get(crop) ?? crop) : "Nueva siembra";
  const parts: Part[] = [
    ...(harvested ? [] : [{ key: "nueva", label: name, ha: areaHa ?? 0, highlight: true }]),
    ...others.map((s) => ({ key: s.season_id, label: names.get(s.crop_id) ?? s.crop_id, ha: s.area_ha })),
  ];
  const left = lot.area_ha - sum(parts.map((p) => p.ha));
  if (left > 0.0001) parts.push({ key: "libre", label: "Libre", ha: left, free: true });

  return (
    <Shell
      lotId={lot.lot_id}
      lotName={lot.name}
      aside={
        <Card bodyClassName="gap-3">
          <Eyebrow>Cómo queda el lote</Eyebrow>
          <h2 className="text-[22px]">
            {harvested ? "La siembra ya está cosechada" : crop ? `Con ${name.toLowerCase()} sembrada` : "Con la siembra nueva"}
          </h2>
          <LotBar parts={parts} total={lot.area_ha} />
          <p className="text-[15px] text-texto-secundario">
            {chosen.length > 0 &&
              `${(names.get(crop) ?? "La siembra").replace(/^./, (c) => c.toUpperCase())} ocupa el terreno donde estuvo ${chosen
                .map((id) => (options.find((o) => o.id === id)?.title ?? "").toLowerCase())
                .join(" y ")}. `}
            {left > 0.0001 ? `Queda libre ${formatHa(left)}.` : "No queda terreno libre."}
          </p>
        </Card>
      }
    >
      <title>{mode === "create" ? `Registrar siembra · ${lot.name} · AgroSense` : `Editar siembra · ${lot.name} · AgroSense`}</title>
      <header>
        <Eyebrow>{mode === "create" ? "Mi finca" : "Editar siembra"}</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">
          {mode === "create" ? "Registrar la siembra" : `Corregir la ${name.toLowerCase()}`}
        </h1>
      </header>
      {saving.isError && <Alert>{saving.error instanceof ApiError ? saving.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>}
      <form onSubmit={save} noValidate className="flex flex-col gap-5">
        <PreviousChoice options={options} value={chosen} onChange={setFollows} />
        <p className="-mt-3 text-[14px] text-texto-secundario">
          Para dividirlo en dos cultivos, registre uno y luego el otro marcando el mismo terreno.
        </p>
        <SelectField
          label="Cultivo"
          value={crop}
          onChange={(event) => setCrop(event.target.value)}
          options={[{ value: "", label: "Elija el cultivo" }, ...crops.map((c) => ({ value: c.crop_id, label: c.name_es }))]}
          error={tried ? errors.crop : undefined}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField
            label="Área que siembra (ha)"
            name="area_ha"
            inputMode="decimal"
            autoComplete="off"
            value={area}
            onChange={(event) => setArea(event.target.value)}
            hint={
              harvested ? "La que ocupó." : mode === "edit" ? `Caben hasta ${formatHa(free)}.` : `Hay ${formatHa(free)} libres en el lote.`
            }
            error={tried ? errors.area : undefined}
          />
          <TextField
            label="Fecha de siembra"
            name="sowing_date"
            type="date"
            max={todayIso()}
            value={sowing}
            onChange={(event) => setSowing(event.target.value)}
            hint={sowing ? formatDate(sowing) : undefined}
            error={tried ? errors.sowing : undefined}
          />
        </div>
        <p className="border-l-8 border-superficie-borde bg-paleta-niebla px-4 py-3 text-[15px]">
          {season?.diagnosis_light
            ? "Se conserva el diagnóstico que vio al sembrar: es el de ese día y no se recalcula."
            : plan && planHolds
              ? `Se guarda con el diagnóstico que vio en la estrategia${planLight ? ` (${LIGHT_LABEL[planLight].toLowerCase()})` : ""}: es el de esa ventana y no se recalcula.`
              : plan
                ? "Cambió el cultivo o la fecha: el diagnóstico de la estrategia ya no corresponde a esta siembra y no se guarda."
                : "Sin diagnóstico al sembrar: cuando consulte el diagnóstico antes de sembrar, se guardará con la siembra."}
        </p>
        <Button type="submit" loading={saving.isPending} loadingText="Guardando…">
          {mode === "create" ? "Guardar siembra" : "Guardar cambios"}
        </Button>
        <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-end py-2`}>
          Cancelar
        </Link>
      </form>
      {mode === "edit" && season && (
        <>
          <section aria-labelledby="borrar" className="flex flex-col gap-2 border-t-2 border-superficie-borde pt-4">
            <h2 id="borrar" className="text-[18px]">
              Borrar esta siembra
            </h2>
            <p className="text-[14px] text-texto-secundario">Deja de verse en el lote y en su historial.</p>
            <Button variant="danger" className="w-full sm:w-[240px]" onClick={() => setConfirming(true)}>
              Borrar esta siembra
            </Button>
          </section>
          <ConfirmDialog
            open={confirming}
            onOpenChange={(next) => {
              setConfirming(next);
              if (!next) remove.reset();
            }}
            title={`¿Borrar la ${name.toLowerCase()}?`}
            cancelLabel="No, volver"
            confirmLabel="Sí, borrar la siembra"
            busy={remove.isPending}
            busyLabel="Borrando…"
            onConfirm={() =>
              remove.mutate(undefined, {
                onSuccess: () => void navigate(PATHS.lot(lot.lot_id), { replace: true, state: { notice: "Siembra borrada." } }),
              })
            }
          >
            <p>
              {name}, {formatHa(season.area_ha)}, sembrada el {formatDate(season.sowing_date)}. Deja de verse en el lote y en su historial.
            </p>
            {remove.error && <Alert>{remove.error instanceof ApiError ? remove.error.message : "Algo falló. Intente de nuevo."}</Alert>}
          </ConfirmDialog>
        </>
      )}
    </Shell>
  );
}
