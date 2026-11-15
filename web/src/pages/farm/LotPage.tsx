import { useId, useState, type ReactNode } from "react";
import { Link, useLocation, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { MapScene, PANEL_WIDTH } from "@/components/layout/MapScene";
import { LotMap } from "@/components/map/LotMap";
import { LiveLot } from "@/components/farm/LiveLot";
import { useAnimated } from "@/hooks/useLightMode";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import type { LotPolygon } from "@/features/farm/geo";
import { byId, formatHa, useBoundary, useLot, useMunicipalities, type LotDetail } from "@/features/farm/lots";
import {
  STAGE_NAMES,
  STAGE_ORDER,
  cropNames,
  formatDate,
  formatLocalDate,
  formatShortDate,
  useCrops,
  useDeletedSeasons,
  useRestoreSeason,
  useSeasons,
  type Season,
} from "@/features/farm/seasons";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { SoilDetails } from "@/components/soil/SoilDetails";
import { WithoutDrawing, irrigationText, placeName } from "./common";
import { LotChangesLink } from "@/pages/changes/LotChangesLink";

/**
 * El lote (HU-164, HU-169): su contorno en el mapa, lo que se sabe de él, sus siembras en curso y su suelo. Editar y
 * borrar van en «Editar lote» (Figma: «D1 · Editar lote»). Un lote sin dibujar muestra su municipio y se puede
 * dibujar. Las siembras se registran, cosechan y corrigen en sus pantallas (HU-165). «Ver estrategias de rotación» lleva
 * a las estrategias con este lote (HU-214). El suelo viene del detalle de la API (HU-182), explicado con su origen
 * y sus rangos (HU-185). El lote vivo es HU-187 (P1). Las siembras borradas hace menos de 30 días se ven aparte, en «Borradas hace
 * poco», con «Restaurar» (HU-204).
 */
export function LotPage() {
  return <RequireSession>{() => <LotView />}</RequireSession>;
}

function LotView() {
  const { lotId = "" } = useParams();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const lot = useLot(lotId);
  const animated = useAnimated();
  const crops = useCrops();
  // El lote vivo (HU-187) es la vista de entrada; el mapa sigue a un toque.
  const [view, setView] = useState<"finca" | "mapa">("finca");
  // En escritorio, el panel se oculta para recorrer la finca o el mapa a pantalla completa.
  const [panelOpen, setPanelOpen] = useState(true);
  const municipalities = useMunicipalities();
  const boundary = useBoundary(lot.data?.municipality_id);
  const municipality = lot.data ? byId(municipalities.data).get(lot.data.municipality_id) : undefined;
  const back = (
    <Link to={PATHS.farm} className={`${LINK} min-h-11 self-start py-2`}>
      ‹ Mi finca
    </Link>
  );

  if (lot.isPending || lot.isError) {
    return (
      <FormScene scene="region" mood={lot.isError ? "no_data" : "idle"}>
        <title>Lote · Mi finca · AgroSense</title>
        {back}
        {lot.isPending ? (
          <p role="status">Cargando el lote…</p>
        ) : (
          <Alert>
            {lot.error instanceof ApiError && lot.error.status === 404
              ? "Ese lote no existe o no es suyo."
              : "No pudimos cargar el lote. Intente de nuevo."}
          </Alert>
        )}
      </FormScene>
    );
  }
  const geometry = lot.data.geometry as unknown as LotPolygon | null;
  const town = municipality?.name ?? "su municipio";
  return (
    <MapScene
      panelOpen={panelOpen}
      onTogglePanel={() => setPanelOpen((open) => !open)}
      map={
        <>
          {view === "finca" ? (
            <div className={`size-full ${panelOpen ? "md:pl-[440px]" : ""}`}>
              <LiveLot
                seasons={lot.data.current_seasons.map((season) => ({
                  seasonId: season.season_id,
                  cropId: season.crop_id,
                  areaHa: season.area_ha,
                  stage: season.stage ?? null,
                }))}
                lotAreaHa={lot.data.area_ha}
                cropName={(id: string) => cropNames(crops.data).get(id) ?? id}
                animated={animated}
              />
            </div>
          ) : (
            <LotMap
              boundary={boundary.data?.geometry ?? null}
              focus={geometry}
              lots={geometry ? [{ id: lot.data.lot_id, name: lot.data.name, geometry, selected: true }] : []}
              panelWidth={panelOpen ? PANEL_WIDTH : 0}
            />
          )}
          <div
            role="group"
            aria-label="Cómo ver el lote"
            className="absolute right-3 bottom-6 z-10 flex gap-1 rounded-md bg-superficie-panel p-1 shadow-md md:top-[104px] md:right-8 md:bottom-auto"
          >
            {(["finca", "mapa"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={view === option}
                onClick={() => setView(option)}
                className={`min-h-11 min-w-11 rounded-sm px-4 font-bold ${
                  view === option ? "bg-accion-primaria text-texto-sobre-oscuro" : "text-texto-principal"
                }`}
              >
                {option === "finca" ? "Su finca" : "Mapa"}
              </button>
            ))}
          </div>
          {view === "finca" && (
            <p
              className={`absolute top-[88px] left-3 z-10 max-w-[calc(100%-1.5rem)] rounded-md bg-superficie-panel/95 px-3 py-2 text-[13px] md:top-auto md:bottom-6 md:max-w-[26rem] ${panelOpen ? "md:left-[488px]" : "md:left-8"}`}
            >
              <span className="md:hidden">Ilustración de su lote, no una imagen de él.</span>
              <span className="hidden md:inline">
                Ilustración de su lote: cada siembra ocupa su parte del área y se dibuja en su etapa por calendario. No es una imagen del
                lote.
              </span>
            </p>
          )}
        </>
      }
    >
      <title>{`${lot.data.name} · Mi finca · AgroSense`}</title>
      {back}
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <Eyebrow>{placeName(municipality, lot.data.municipality_id)}</Eyebrow>
          <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.data.name}</h1>
        </div>
        <ButtonLink to={PATHS.editLot(lot.data.lot_id)} variant="secondary" className="w-full sm:w-[180px]">
          Editar lote
        </ButtonLink>
      </header>
      {notice && (
        <p role="status" className="border-l-8 border-oscuro-oliva bg-paleta-niebla px-4 py-2 font-bold">
          {notice}
        </p>
      )}
      <Section title="Su lote">
        <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1">
          <dt className="font-bold">Área</dt>
          <dd>
            {formatHa(lot.data.area_ha)} · {geometry ? "calculada con su dibujo" : "escrita a mano"}
          </dd>
          <dt className="font-bold">Riego</dt>
          <dd>{irrigationText(lot.data.irrigated)}</dd>
        </dl>
        {!geometry && (
          <>
            <WithoutDrawing place={town} />
            <Link to={PATHS.drawLot(lot.data.lot_id)} className={`${LINK} min-h-11 self-start py-2`}>
              Dibujar en el mapa
            </Link>
          </>
        )}
      </Section>
      <Seasons lot={lot.data} />
      <LotChangesLink
        key={lot.data.lot_id}
        municipalityId={lot.data.municipality_id}
        irrigated={lot.data.irrigated}
        currentSeasons={lot.data.current_seasons}
      />
      <Section title="Suelo estimado">
        <SoilDetails municipalityId={lot.data.municipality_id} lotId={lot.data.lot_id} open />
      </Section>
    </MapScene>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h2 id={id} className="text-[20px]">
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * Las siembras en curso (GET /lots/{id}, `current_seasons`) con su etapa por calendario (HU-220), y lo ya cosechado
 * (GET /lots/{id}/seasons). Registrar siembra, cosecha y corregir van en sus pantallas (HU-165).
 */
function Seasons({ lot }: { lot: LotDetail }) {
  const crops = useCrops();
  const history = useSeasons(lot.lot_id);
  const names = cropNames(crops.data);
  const name = (id: string) => names.get(id) ?? id;
  const used = lot.current_seasons.reduce((total, season) => total + season.area_ha, 0);
  const free = Math.max(lot.area_ha - used, 0);
  const harvested = (history.data ?? []).filter((season) => season.harvest_date);
  return (
    <>
      <Section title="Siembras en curso">
        {lot.current_seasons.length === 0 ? (
          <p className="text-texto-secundario">Sin siembra en curso.</p>
        ) : (
          <ul className="flex flex-col gap-4">
            {lot.current_seasons.map((season) => (
              <li key={season.season_id} className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="text-[18px] font-bold">{name(season.crop_id)}</span>
                  <span className="text-[14px] text-texto-secundario">{formatHa(season.area_ha)}</span>
                </div>
                <p className="text-[15px]">
                  {season.stage ? `${STAGE_NAMES[season.stage] ?? season.stage} · ` : ""}día {season.days_since_sowing}
                  <span className="text-texto-secundario"> · sembrado el {formatDate(season.sowing_date)}</span>
                </p>
                {season.stage && <StageBar stage={season.stage} progress={season.stage_progress_pct ?? 0} />}
                {season.harvest_estimate && (
                  <p className="text-[14px] text-texto-secundario">
                    {season.harvest_due
                      ? `La cosecha estimada era el ${formatDate(season.harvest_estimate)}: ¿ya cosechó?`
                      : `Cosecha estimada: ${formatDate(season.harvest_estimate)}.`}{" "}
                    Sale de la duración de las etapas del cultivo, no de lo que se ve en el lote.
                  </p>
                )}
                <div className="flex flex-wrap gap-x-6">
                  <Link to={PATHS.harvest(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2`}>
                    Registrar cosecha
                  </Link>
                  <Link to={PATHS.editSeason(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2`}>
                    Corregir
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
        {free > 0.0001 ? (
          <ButtonLink to={PATHS.sow(lot.lot_id)} className="w-full sm:w-[240px]">
            Registrar siembra
          </ButtonLink>
        ) : (
          <p className="text-[14px] text-texto-secundario">Todo el lote está sembrado. Registre una cosecha para sembrar de nuevo.</p>
        )}
        {/* La entrada a las estrategias con este lote (HU-164, HU-214): su municipio, su riego y su historial. */}
        <ButtonLink to={`${PATHS.consult}?lote=${lot.lot_id}`} variant="secondary" className="w-full sm:w-auto sm:self-start">
          Ver estrategias de rotación
        </ButtonLink>
      </Section>
      {harvested.length > 0 && (
        <Section title="Ya cosechado">
          <ul className="flex flex-col gap-1">
            {harvested.map((season) => (
              <li key={season.season_id} className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="min-w-0">
                  <span className="font-bold">{name(season.crop_id)}</span>
                  <span className="text-[14px] text-texto-secundario">
                    {" "}
                    · {formatHa(season.area_ha)} · {formatShortDate(season.sowing_date)} a {formatShortDate(season.harvest_date!)}
                  </span>
                </span>
                <Link to={PATHS.editSeason(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2 text-[15px]`}>
                  Corregir
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <DeletedSeasons lotId={lot.lot_id} name={name} />
    </>
  );
}

/** Las siembras borradas hace menos de 30 días (HU-204): cada una dice hasta cuándo se puede restaurar. */
function DeletedSeasons({ lotId, name }: { lotId: string; name: (id: string) => string }) {
  const deleted = useDeletedSeasons(lotId);
  const [restored, setRestored] = useState<string | null>(null);
  if (!deleted.data?.length && !restored) return null;
  return (
    <Section title="Borradas hace poco">
      {restored && (
        <p role="status" className="border-l-8 border-oscuro-oliva bg-paleta-niebla px-4 py-2 font-bold">
          {restored}: siembra restaurada.
        </p>
      )}
      {deleted.data && deleted.data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {deleted.data.map((season) => (
            <li key={season.season_id}>
              <DeletedSeasonRow season={season} name={name(season.crop_id)} onRestored={() => setRestored(name(season.crop_id))} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function DeletedSeasonRow({ season, name, onRestored }: { season: Season; name: string; onRestored: () => void }) {
  const restore = useRestoreSeason(season.lot_id, season.season_id);
  const dates = season.harvest_date
    ? `${formatShortDate(season.sowing_date)} a ${formatShortDate(season.harvest_date)}`
    : `sembrada el ${formatShortDate(season.sowing_date)}`;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span className="flex min-w-0 flex-col">
          <span>
            <span className="font-bold">{name}</span>
            <span className="text-[14px] text-texto-secundario">
              {" "}
              · {formatHa(season.area_ha)} · {dates}
            </span>
          </span>
          {season.restorable_until && (
            <span className="text-[14px] text-texto-secundario">
              Borrada · se puede restaurar hasta el {formatLocalDate(season.restorable_until)}
            </span>
          )}
        </span>
        <Button
          variant="secondary"
          className="w-full sm:w-auto"
          loading={restore.isPending}
          loadingText="Restaurando…"
          aria-label={`Restaurar ${name.toLowerCase()}, sembrada el ${formatShortDate(season.sowing_date)}`}
          onClick={() => restore.mutate(undefined, { onSuccess: onRestored })}
        >
          Restaurar
        </Button>
      </div>
      {restore.error && <Alert>{restore.error instanceof ApiError ? restore.error.message : "Algo falló. Intente de nuevo."}</Alert>}
    </div>
  );
}

/** Las cuatro etapas de FAO-56 en fila: las pasadas llenas, la de hoy hasta donde va, las que faltan vacías. */
function StageBar({ stage, progress }: { stage: string; progress: number }) {
  const current = STAGE_ORDER.indexOf(stage);
  return (
    <div
      role="img"
      aria-label={`${STAGE_NAMES[stage] ?? stage}: lleva el ${Math.round(progress)} % de la etapa`}
      className="grid grid-cols-4 gap-1"
    >
      {STAGE_ORDER.map((key, index) => {
        const fill = index < current ? 100 : index === current ? progress : 0;
        return (
          <div key={key} className="flex min-w-0 flex-col gap-1">
            <span className="relative h-3 border border-superficie-borde bg-superficie-panel">
              <span className="absolute inset-y-0 left-0 bg-accion-primaria" style={{ width: `${fill}%` }} />
            </span>
            <span className={`truncate text-[12px] ${index === current ? "font-bold" : "text-texto-secundario"}`}>{STAGE_NAMES[key]}</span>
          </div>
        );
      })}
    </div>
  );
}
