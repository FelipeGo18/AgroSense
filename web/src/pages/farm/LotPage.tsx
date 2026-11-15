import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useId, type ReactNode } from "react";
import { useLocation, useParams } from "react-router";
import { Link } from "@/components/layout/LanguageLink";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { MapScene, PANEL_WIDTH } from "@/components/layout/MapScene";
import { LotMap } from "@/components/map/LotMap";
import { Alert } from "@/components/ui/Alert";
import { ButtonLink } from "@/components/ui/Button";
import type { LotPolygon } from "@/features/farm/geo";
import { byId, formatHa, useBoundary, useLot, useMunicipalities, type LotDetail } from "@/features/farm/lots";
import { STAGE_NAMES, STAGE_ORDER, cropNames, formatDate, formatShortDate, useCrops, useSeasons } from "@/features/farm/seasons";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { SoilFacts } from "@/components/soil/SoilFacts";
import { useMunicipalitySoil } from "@/features/diagnosis/signals";
import { WithoutDrawing, irrigationText, placeName } from "./common";
import { LotChangesLink } from "@/pages/changes/LotChangesLink";

/**
 * El lote (HU-164, HU-169): su contorno en el mapa, lo que se sabe de él, sus siembras en curso y su suelo. Editar y
 * borrar van en «Editar lote» (Figma: «D1 · Editar lote»). Un lote sin dibujar muestra su municipio y se puede
 * dibujar. Las siembras se registran, cosechan y corrigen en sus pantallas (HU-165). «Ver estrategias de rotación» lleva
 * a las estrategias con este lote (HU-214). El suelo es el estimado de su municipio (HU-185); el del polígono del lote es
 * HU-182 (P1). El lote vivo es HU-187 (P1).
 */
export function LotPage() {
  useTranslation();
  return <RequireSession>{() => <LotView />}</RequireSession>;
}

function LotView() {
  useTranslation();
  const { lotId = "" } = useParams();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const lot = useLot(lotId);
  const municipalities = useMunicipalities();
  const boundary = useBoundary(lot.data?.municipality_id);
  const municipality = lot.data ? byId(municipalities.data).get(lot.data.municipality_id) : undefined;
  const back = (
    <Link to={PATHS.farm} className={`${LINK} min-h-11 self-start py-2`}>
      {t("pages.farm.LotPage.myFarm")}
    </Link>
  );

  if (lot.isPending || lot.isError) {
    return (
      <FormScene scene="region" mood={lot.isError ? "no_data" : "idle"}>
        <title>{t("pages.farm.LotPage.plotMyFarmAgrosense")}</title>
        {back}
        {lot.isPending ? (
          <p role="status">{t("pages.farm.LotPage.loadingThePlot")}</p>
        ) : (
          <Alert>
            {lot.error instanceof ApiError && lot.error.status === 404
              ? t("pages.farm.LotPage.thatPlotDoesNotExistOrIs")
              : t("pages.farm.LotPage.weCouldNotLoadThePlotTry")}
          </Alert>
        )}
      </FormScene>
    );
  }
  const geometry = lot.data.geometry as unknown as LotPolygon | null;
  const town = municipality?.name ?? t("pages.farm.FarmPage.yourMunicipality");
  return (
    <MapScene
      map={
        <LotMap
          boundary={boundary.data?.geometry ?? null}
          focus={geometry}
          lots={geometry ? [{ id: lot.data.lot_id, name: lot.data.name, geometry, selected: true }] : []}
          panelWidth={PANEL_WIDTH}
        />
      }
    >
      <title>{t("pages.farm.LotPage.myFarmAgrosense", { v0: lot.data.name })}</title>
      {back}
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <Eyebrow>{placeName(municipality, lot.data.municipality_id)}</Eyebrow>
          <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.data.name}</h1>
        </div>
        <ButtonLink to={PATHS.editLot(lot.data.lot_id)} variant="secondary" className="w-full sm:w-[180px]">
          {t("pages.farm.LotPage.editPlot")}
        </ButtonLink>
      </header>
      {notice && (
        <p role="status" className="border-l-8 border-oscuro-oliva bg-paleta-niebla px-4 py-2 font-bold">
          {notice}
        </p>
      )}
      <Section title={t("pages.farm.LotPage.yourPlot")}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1">
          <dt className="font-bold">{t("pages.farm.LotPage.area")}</dt>
          <dd>
            {formatHa(lot.data.area_ha)} · {geometry ? t("pages.farm.LotPage.calculatedFromYourBoundary") : t("farm.manuallyEntered")}
          </dd>
          <dt className="font-bold">{t("pages.farm.LotPage.irrigation")}</dt>
          <dd>{irrigationText(lot.data.irrigated)}</dd>
        </dl>
        {!geometry && (
          <>
            <WithoutDrawing place={town} />
            <Link to={PATHS.drawLot(lot.data.lot_id)} className={`${LINK} min-h-11 self-start py-2`}>
              {t("pages.farm.FarmPage.drawOnTheMap")}
            </Link>
          </>
        )}
      </Section>
      <Seasons lot={lot.data} />
      <LotChangesLink municipalityId={lot.data.municipality_id} irrigated={lot.data.irrigated} />
      <Soil municipalityId={lot.data.municipality_id} town={town} />
    </MapScene>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  useTranslation();
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
  useTranslation();
  const crops = useCrops();
  const history = useSeasons(lot.lot_id);
  const names = cropNames(crops.data);
  const name = (id: string) => names.get(id) ?? id;
  const used = lot.current_seasons.reduce((total, season) => total + season.area_ha, 0);
  const free = Math.max(lot.area_ha - used, 0);
  const harvested = (history.data ?? []).filter((season) => season.harvest_date);
  return (
    <>
      <Section title={t("pages.farm.LotPage.plantingsInProgress")}>
        {lot.current_seasons.length === 0 ? (
          <p className="text-texto-secundario">{t("pages.farm.LotPage.noPlantingInProgress")}</p>
        ) : (
          <ul className="flex flex-col gap-4">
            {lot.current_seasons.map((season) => (
              <li key={season.season_id} className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="text-[18px] font-bold">{name(season.crop_id)}</span>
                  <span className="text-[14px] text-texto-secundario">{formatHa(season.area_ha)}</span>
                </div>
                <p className="text-[15px]">
                  {season.stage ? `${STAGE_NAMES()[season.stage] ?? season.stage} · ` : ""}
                  {t("pages.farm.LotPage.day")} {season.days_since_sowing}
                  <span className="text-texto-secundario">
                    {" "}
                    {t("pages.farm.LotPage.plantedOn")} {formatDate(season.sowing_date)}
                  </span>
                </p>
                {season.stage && <StageBar stage={season.stage} progress={season.stage_progress_pct ?? 0} />}
                {season.harvest_estimate && (
                  <p className="text-[14px] text-texto-secundario">
                    {season.harvest_due
                      ? t("pages.farm.LotPage.theEstimatedHarvestDateWasHaveYou", { v0: formatDate(season.harvest_estimate) })
                      : t("pages.farm.LotPage.estimatedHarvest", { v0: formatDate(season.harvest_estimate) })}{" "}
                    {t("pages.farm.LotPage.basedOnCropStageDurationsNotOn")}
                  </p>
                )}
                <div className="flex flex-wrap gap-x-6">
                  <Link to={PATHS.harvest(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2`}>
                    {t("pages.farm.LotPage.recordHarvest")}
                  </Link>
                  <Link to={PATHS.editSeason(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2`}>
                    {t("pages.farm.LotPage.correct")}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
        {free > 0.0001 ? (
          <ButtonLink to={PATHS.sow(lot.lot_id)} className="w-full sm:w-[240px]">
            {t("pages.farm.LotPage.recordPlanting")}
          </ButtonLink>
        ) : (
          <p className="text-[14px] text-texto-secundario">{t("pages.farm.LotPage.theWholePlotIsPlantedRecordA")}</p>
        )}
        {/* La entrada a las estrategias con este lote (HU-164, HU-214): su municipio, su riego y su historial. */}
        <ButtonLink to={`${PATHS.consult}?lote=${lot.lot_id}`} variant="secondary" className="w-full sm:w-auto sm:self-start">
          {t("pages.farm.LotPage.viewRotationStrategies")}
        </ButtonLink>
      </Section>
      {harvested.length > 0 && (
        <Section title={t("pages.farm.LotPage.alreadyHarvested")}>
          <ul className="flex flex-col gap-1">
            {harvested.map((season) => (
              <li key={season.season_id} className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="min-w-0">
                  <span className="font-bold">{name(season.crop_id)}</span>
                  <span className="text-[14px] text-texto-secundario">
                    {" "}
                    · {formatHa(season.area_ha)} · {formatShortDate(season.sowing_date)} {t("pages.farm.LotPage.to")}{" "}
                    {formatShortDate(season.harvest_date!)}
                  </span>
                </span>
                <Link to={PATHS.editSeason(lot.lot_id, season.season_id)} className={`${LINK} min-h-11 py-2 text-[15px]`}>
                  {t("pages.farm.LotPage.correct")}
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </>
  );
}

/** Las cuatro etapas de FAO-56 en fila: las pasadas llenas, la de hoy hasta donde va, las que faltan vacías. */
function StageBar({ stage, progress }: { stage: string; progress: number }) {
  useTranslation();
  const current = STAGE_ORDER.indexOf(stage);
  return (
    <div
      role="img"
      aria-label={t("pages.farm.LotPage.throughThisStage", { v0: STAGE_NAMES()[stage] ?? stage, v1: Math.round(progress) })}
      className="grid grid-cols-4 gap-1"
    >
      {STAGE_ORDER.map((key, index) => {
        const fill = index < current ? 100 : index === current ? progress : 0;
        return (
          <div key={key} className="flex min-w-0 flex-col gap-1">
            <span className="relative h-3 border border-superficie-borde bg-superficie-panel">
              <span className="absolute inset-y-0 left-0 bg-accion-primaria" style={{ width: `${fill}%` }} />
            </span>
            <span className={`truncate text-[12px] ${index === current ? "font-bold" : "text-texto-secundario"}`}>
              {STAGE_NAMES()[key]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * El suelo (HU-185): el estimado del municipio del lote (`GET /catalogs/municipalities/{id}/soil`), con su rango y qué
 * significa cada dato. Sin el suelo publicado no se inventa nada (R1); siempre dice que es de la zona (R10).
 */
function Soil({ municipalityId, town }: { municipalityId: string; town: string }) {
  useTranslation();
  const soil = useMunicipalitySoil(municipalityId);
  return (
    <Section title={t("pages.farm.LotPage.soilInTheArea")}>
      {soil.isPending ? (
        <p role="status" className="text-texto-secundario">
          {t("pages.farm.LotPage.loadingSoilDataFor")} {town}…
        </p>
      ) : soil.data ? (
        <SoilFacts soil={soil.data} place={town} />
      ) : (
        <>
          <p className="font-bold">
            {t("pages.farm.LotPage.noSoilDataFor")} {town}.
          </p>
          <p className="text-[14px] text-texto-secundario">{t("pages.farm.LotPage.toLearnAboutYourPlotsSoilGet")}</p>
        </>
      )}
    </Section>
  );
}
