import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@/components/layout/LanguageLink";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { MapScene, PANEL_WIDTH } from "@/components/layout/MapScene";
import { LotMap, type DrawMode } from "@/components/map/LotMap";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { TextField } from "@/components/ui/TextField";
import { areaHa, areaM2, formatM2, pointsOutside, type LotPolygon } from "@/features/farm/geo";
import { byId, formatHa, parseHa, useBoundary, useCreateLot, useLots, useMunicipalities, type Municipality } from "@/features/farm/lots";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import {
  AREA_ERROR,
  AREA_HINT,
  DrawSteps,
  DrawnArea,
  IRRIGATION,
  IRRIGATION_HINT,
  NAME_ERROR,
  OutsideWarning,
  WithoutDrawing,
  placeName,
} from "./common";
import { ZoneChoice } from "./ZoneChoice";
import { useSearchParams } from "@/components/layout/LanguageLink";
import { clearGuestConsult, readGuestConsult } from "@/features/strategies/entry";
import { cropNames, useCrops } from "@/features/farm/seasons";

const OTHER = "otro";
const option = (m: Municipality): Option => ({ id: m.municipality_id, label: m.name, hint: m.department });
export const DRAW_STEPS = () => [
  t("pages.farm.AddLotPage.zoomInUntilYouCanSeeYour"),
  t("pages.farm.AddLotPage.tapEachCornerOfThePlot"),
  t("pages.farm.AddLotPage.tapTheFirstPointToCloseThe"),
];
const NO_DRAWING = () => t("pages.farm.AddLotPage.drawYourPlotOnTheMapOr");

/**
 * Agregar lote (HU-164, HU-169). Figma: «D0 · Agregar lote o zona», «Dibuje su lote» y «Lote sin dibujar».
 * Paso 1: dónde está (una zona donde ya tiene lotes u otro municipio). Paso 2: dibujarlo en el mapa, dentro del límite
 * de su municipio; o, si no puede o no quiere, escribir el área a mano (el lote queda sin ubicación).
 */
export function AddLotPage() {
  useTranslation();
  return <RequireSession>{() => <AddLot />}</RequireSession>;
}

function AddLot() {
  useTranslation();
  const navigate = useNavigate();
  const municipalities = useMunicipalities();
  const lots = useLots();
  const create = useCreateLot();
  const places = byId(municipalities.data);
  const [search, setSearch] = useSearchParams();
  const crops = useCrops();
  const [guestConsult] = useState(() => readGuestConsult());
  const fromConsult = search.get("desde") === "consulta" && guestConsult !== null;
  const guestMunicipality = guestConsult?.municipalityId ?? "";
  const guestArea = guestConsult?.areaText ?? "";
  const guestIrrigation = guestConsult?.irrigation;

  const names = cropNames(crops.data);
  const previousCrops = fromConsult ? (guestConsult?.previousCrops ?? []) : [];

  // Las zonas donde ya tiene lotes, con cuántos lotes tiene en cada una, en el orden en que las agregó.
  const counts = new Map<string, number>();
  for (const lot of lots.data ?? [])
    if (places.has(lot.municipality_id)) counts.set(lot.municipality_id, (counts.get(lot.municipality_id) ?? 0) + 1);
  const zones = [...counts.keys()];

  const [step, setStep] = useState<1 | 2>(fromConsult && guestMunicipality ? 2 : 1);
  const [manual, setManual] = useState(fromConsult);
  const [zone, setZone] = useState<string | null>(fromConsult ? guestMunicipality : null);
  const [other, setOther] = useState<Option | null>(() => {
    if (!fromConsult || !guestMunicipality) return null;
    const place = places.get(guestMunicipality);
    return place ? { id: guestMunicipality, label: place.name, hint: place.department } : null;
  });
  const [area, setArea] = useState(fromConsult ? guestArea : "");
  const [name, setName] = useState("");
  const [irrigated, setIrrigated] = useState<boolean | null>(() => {
    if (!fromConsult || !guestIrrigation) return null;
    if (guestIrrigation === "si") return true;
    if (guestIrrigation === "no") return false;
    return null; // "nose" → null
  });
  const [geometry, setGeometry] = useState<LotPolygon | null>(null);
  const [mode, setMode] = useState<DrawMode>("draw");
  const [tried, setTried] = useState(false);

  const chosenZone = zone ?? zones[0] ?? OTHER;
  const municipalityId = chosenZone === OTHER ? (other?.id ?? null) : chosenZone;
  const municipality = municipalityId ? places.get(municipalityId) : undefined;
  const town = municipality?.name ?? t("pages.farm.FarmPage.yourMunicipality");
  const boundary = useBoundary(step === 2 ? municipalityId : null);
  const outside = Boolean(geometry && boundary.data && pointsOutside(geometry, boundary.data.geometry).length > 0);
  const errors = {
    area: parseHa(area) === null ? AREA_ERROR() : undefined,
    name: name.trim() ? undefined : NAME_ERROR(),
    drawing: geometry ? undefined : NO_DRAWING(),
  };
  const done = (lot: { lot_id: string }) => {
    clearGuestConsult();
    void navigate(PATHS.lot(lot.lot_id), { state: { notice: t("pages.farm.AddLotPage.plotSaved") } });
  };

  const saveManual = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    const areaHa = parseHa(area);
    if (!municipalityId || areaHa === null || errors.name) return;
    create.mutate({ name: name.trim(), municipality_id: municipalityId, area_ha: areaHa, irrigated }, { onSuccess: done });
  };
  const saveDrawn = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!municipalityId || !geometry || outside || errors.name) return;
    create.mutate({ name: name.trim(), municipality_id: municipalityId, geometry: { ...geometry }, irrigated }, { onSuccess: done });
  };

  const cancel = (
    <Link
      to={PATHS.farm}
      onClick={() => {
        if (fromConsult) clearGuestConsult();
      }}
      className={`${LINK} min-h-11 self-center py-2`}
    >
      {t("pages.account.AccountPage.cancel")}
    </Link>
  );
  const back = (
    <button type="button" onClick={() => setStep(1)} className={`${LINK} min-h-11 self-start`}>
      ‹ {placeName(municipality, municipalityId ?? "")}
    </button>
  );
  const failed = create.isError && (
    <Alert>{create.error instanceof ApiError ? create.error.message : t("pages.account.PrioritiesCard.couldNotSaveTryAgain")}</Alert>
  );
  const nameField = (
    <TextField
      label={t("pages.farm.AddLotPage.plotName")}
      name="name"
      maxLength={60}
      autoComplete="off"
      placeholder={t("pages.farm.AddLotPage.laEsperanza")}
      value={name}
      onChange={(event) => setName(event.target.value)}
      error={tried ? errors.name : undefined}
    />
  );
  const irrigation = (
    <ChoiceGroup
      legend={t("farm.irrigationQuestion")}
      choices={IRRIGATION()}
      value={irrigated}
      onChange={setIrrigated}
      hint={IRRIGATION_HINT()}
    />
  );

  if (step === 2 && !manual) {
    const toManual = (
      <button type="button" onClick={() => setManual(true)} className={`${LINK} min-h-11 self-start`}>
        {t("pages.farm.AddLotPage.enterTheAreaManually")}
      </button>
    );
    return (
      <MapScene
        map={
          <LotMap
            boundary={boundary.data?.geometry ?? null}
            panelWidth={PANEL_WIDTH}
            fallback={toManual}
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
        <title>{t("pages.farm.AddLotPage.drawYourPlotAgrosense")}</title>
        {back}
        <header>
          <Eyebrow>{t("pages.farm.AddLotPage.step2Of2")}</Eyebrow>
          <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.farm.AddLotPage.drawYourPlot")}</h1>
        </header>
        <DrawSteps steps={DRAW_STEPS()} />
        {boundary.isError && (
          <Alert>
            {t("pages.farm.AddLotPage.weCouldNotLoadTheBoundaryOf")} {town}
            {t("pages.farm.AddLotPage.youCanEnterTheAreaManually")}
          </Alert>
        )}
        {outside ? (
          <OutsideWarning place={town} />
        ) : geometry ? (
          <DrawnArea ha={formatHa(areaHa(geometry))} m2={formatM2(areaM2(geometry))} />
        ) : (
          tried && (
            <p role="alert" className="font-bold text-oscuro-rojo">
              {NO_DRAWING()}
            </p>
          )
        )}
        {failed}
        <form onSubmit={saveDrawn} noValidate className="flex flex-col gap-4">
          {nameField}
          {irrigation}
          <Button type="submit" disabled={outside} loading={create.isPending} loadingText={t("pages.account.AccountPage.saving")}>
            {t("pages.farm.AddLotPage.savePlot")}
          </Button>
        </form>
        <div className="flex flex-wrap items-center justify-between gap-x-6">
          {toManual}
          {cancel}
        </div>
      </MapScene>
    );
  }

  return (
    <FormScene scene="region" mood={step === 2 ? "idle" : "guide"} wide={step === 2} rejected={create.error}>
      <title>{t("pages.farm.AddLotPage.addPlotAgrosense")}</title>
      {municipalities.isPending ? (
        <p role="status">{t("pages.farm.AddLotPage.loadingMunicipalities")}</p>
      ) : municipalities.isError ? (
        <>
          <Alert>
            {municipalities.error instanceof ApiError && municipalities.error.status === 503
              ? municipalities.error.message
              : t("pages.farm.AddLotPage.weCouldNotLoadMunicipalitiesTryAgain")}
          </Alert>
          <Button variant="secondary" className="self-start" onClick={() => void municipalities.refetch()}>
            {t("pages.account.PrioritiesCard.tryAgain")}
          </Button>
          {cancel}
        </>
      ) : step === 1 ? (
        <>
          <header>
            <Eyebrow>{t("pages.farm.FarmPage.addPlot")}</Eyebrow>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.farm.AddLotPage.whereIsTheNewPlot")}</h1>
          </header>
          {zones.length > 0 && (
            <ZoneChoice
              legend={t("farm.existingZone")}
              choices={[
                ...zones.map((id) => ({
                  value: id,
                  title: placeName(places.get(id), id),
                  note: counts.get(id) === 1 ? t("farm.onePlot") : t("pages.farm.AddLotPage.plots", { v0: counts.get(id) }),
                })),
                { value: OTHER, title: t("pages.farm.AddLotPage.inAnotherMunicipality"), note: t("pages.farm.AddLotPage.addedAsANewArea") },
              ]}
              value={chosenZone}
              onChange={setZone}
            />
          )}
          {chosenZone === OTHER && (
            <div className="flex flex-col gap-1">
              <Combobox
                label={t("pages.farm.AddLotPage.municipality")}
                options={municipalities.data.map(option)}
                value={other}
                onChange={setOther}
                placeholder={t("pages.farm.AddLotPage.enterTheMunicipalityName")}
                emptyText={t("farm.outsidePilot")}
              />
              <p className="text-[15px] text-texto-secundario">{t("pages.farm.AddLotPage.onlyMunicipalitiesWithDataInThePilot")}</p>
            </div>
          )}
          {tried && !municipalityId && (
            <p role="alert" className="font-bold text-oscuro-rojo">
              {t("pages.farm.AddLotPage.chooseYourPlotsMunicipality")}
            </p>
          )}
          <Button
            className="mt-1"
            onClick={() => {
              setTried(!municipalityId);
              if (municipalityId) setStep(2);
            }}
          >
            {t("pages.farm.AddLotPage.continueDrawThePlot")}
          </Button>
          {cancel}
        </>
      ) : (
        <>
          {back}
          <header>
            <Eyebrow>{t("pages.farm.AddLotPage.step2Of2")}</Eyebrow>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.farm.AddLotPage.yourPlotWithoutABoundary")}</h1>
          </header>
          {fromConsult && (
            <div role="status" className="flex flex-col gap-2 border-2 border-superficie-borde bg-superficie-panel-suave p-4">
              <p className="font-bold">
                {t("pages.farm.AddLotPage.youAlreadyExploredOptionsFor")} {town}
                {t("pages.farm.AddLotPage.saveThisAsYourFirstPlot")}
              </p>
              {previousCrops.length > 0 && (
                <p>
                  {t("pages.farm.AddLotPage.previousCrops")} {previousCrops.map((id) => names.get(id) ?? id).join(", ")}.
                </p>
              )}
              <p>{t("pages.farm.AddLotPage.justAddANameYouCanDraw")}</p>
              <p>{t("pages.farm.AddLotPage.previousCropsAreAReferenceTheyAre")}</p>
            </div>
          )}
          {fromConsult && (
            <button
              type="button"
              onClick={() => {
                clearGuestConsult();
                setSearch({}, { replace: true });
                setStep(1);
                setManual(false);
                setZone(null);
                setOther(null);
                setArea("");
                setName("");
                setIrrigated(null);
                setGeometry(null);
                setMode("draw");
                setTried(false);
              }}
              className={`${LINK} min-h-11`}
            >
              {t("pages.farm.AddLotPage.noStartFromScratch")}
            </button>
          )}
          {failed}
          <form onSubmit={saveManual} noValidate className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
              <div className="flex flex-col gap-4">
                <TextField
                  label={t("pages.farm.AddLotPage.plotAreaHa")}
                  name="area_ha"
                  inputMode="decimal"
                  autoComplete="off"
                  placeholder={t("numbers.example")}
                  value={area}
                  onChange={(event) => setArea(event.target.value)}
                  hint={AREA_HINT()}
                  error={tried ? errors.area : undefined}
                />
                {nameField}
              </div>
              <div className="flex flex-col gap-4">
                <WithoutDrawing place={town} />
                {irrigation}
              </div>
            </div>
            <div className="grid grid-cols-1 items-center gap-2 lg:grid-cols-2 lg:gap-8">
              <Button type="submit" loading={create.isPending} loadingText={t("pages.account.AccountPage.saving")}>
                {t("pages.farm.AddLotPage.savePlot")}
              </Button>
              {cancel}
            </div>
          </form>
          <button
            type="button"
            onClick={() => {
              setManual(false);
              setTried(false);
            }}
            className={`${LINK} min-h-11 self-start`}
          >
            {t("pages.farm.FarmPage.drawOnTheMap")}
          </button>
        </>
      )}
    </FormScene>
  );
}
