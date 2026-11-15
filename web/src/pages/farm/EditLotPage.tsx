import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router";
import { Link, useNavigate, useSearchParams } from "@/components/layout/LanguageLink";
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
import { Eyebrow } from "@/components/ui/Eyebrow";
import { AREA_ERROR, DrawSteps, DrawnArea, IRRIGATION, IRRIGATION_HINT, NAME_ERROR, OutsideWarning, placeName } from "./common";

/**
 * Editar lote (HU-164). Figma: «D1 · Editar lote» y «confirmar borrar». El contorno se corrige moviendo sus puntos en
 * el mapa; un lote sin dibujar se puede dibujar (con `?dibujar` el mapa abre listo para eso) o seguir con el área
 * escrita. Cambia el nombre, el contorno o el área y el riego (PATCH /lots/{id}); «Borrar este lote» pide confirmar.
 */
export function EditLotPage() {
  useTranslation();
  return <RequireSession>{() => <EditLotLoader />}</RequireSession>;
}

function EditLotLoader() {
  useTranslation();
  const { lotId = "" } = useParams();
  const lot = useLot(lotId);
  if (lot.isPending || lot.isError) {
    return (
      <FormScene scene="region" mood={lot.isError ? "no_data" : "idle"}>
        <title>{t("pages.farm.EditLotPage.editPlotAgrosense")}</title>
        {lot.isPending ? (
          <p role="status">{t("pages.farm.LotPage.loadingThePlot")}</p>
        ) : (
          <>
            <Alert>
              {lot.error instanceof ApiError && lot.error.status === 404
                ? t("pages.farm.LotPage.thatPlotDoesNotExistOrIs")
                : t("pages.farm.LotPage.weCouldNotLoadThePlotTry")}
            </Alert>
            <Link to={PATHS.farm} className={`${LINK} min-h-11 self-start py-2`}>
              {t("pages.farm.EditLotPage.backToMyFarm")}
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
  useTranslation();
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
  const town = place?.name ?? t("pages.farm.FarmPage.yourMunicipality");
  const outside = Boolean(geometry && boundary.data && pointsOutside(geometry, boundary.data.geometry).length > 0);
  // Un lote dibujado sigue dibujado: si se borra el dibujo, hay que volver a dibujarlo antes de guardar.
  const errors = {
    area: !geometry && parseHa(area) === null ? AREA_ERROR() : undefined,
    name: name.trim() ? undefined : NAME_ERROR(),
    drawing: saved && !geometry ? t("pages.farm.EditLotPage.drawThePlotBoundaryAgain") : undefined,
  };
  const sown = lot.current_seasons.reduce((sum, season) => sum + season.area_ha, 0);
  const crops = lot.current_seasons.length;
  const summary = `${placeName(place, lot.municipality_id)} · ${crops === 0 ? t("pages.farm.FarmPage.noPlantingInProgress") : crops === 1 ? t("pages.farm.EditLotPage.1PlantingInProgress") : t("pages.farm.EditLotPage.plantingsInProgress", { v0: crops })}`;

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
      { onSuccess: () => void navigate(PATHS.lot(lot.lot_id), { state: { notice: t("pages.farm.EditLotPage.changesSaved") } }) },
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
      <title>{t("pages.farm.EditLotPage.editAgrosense", { v0: lot.name })}</title>
      <header>
        <Eyebrow>{t("pages.farm.LotPage.editPlot")}</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.name}</h1>
        <p className="text-[15px] text-texto-secundario">{summary}</p>
      </header>
      {mode === "draw" && <DrawSteps steps={DRAW_STEPS()} />}
      {update.isError && (
        <Alert>{update.error instanceof ApiError ? update.error.message : t("pages.account.PrioritiesCard.couldNotSaveTryAgain")}</Alert>
      )}
      <form onSubmit={save} noValidate className="flex flex-col gap-4">
        {outside ? (
          <OutsideWarning place={town} />
        ) : geometry ? (
          <>
            <DrawnArea ha={formatHa(areaHa(geometry))} m2={formatM2(areaM2(geometry))} />
            <p className="-mt-2 text-[14px] text-texto-secundario">
              {t("pages.farm.EditLotPage.moveThePointsOnTheMapTo")}
              {sown > 0 && t("pages.farm.EditLotPage.itCannotBeSmallerThanThePlanted", { v0: formatHa(sown) })}
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
                label={t("pages.farm.AddLotPage.plotAreaHa")}
                name="area_ha"
                inputMode="decimal"
                autoComplete="off"
                value={area}
                onChange={(event) => setArea(event.target.value)}
                hint={
                  sown > 0
                    ? t("pages.farm.EditLotPage.itCannotBeSmallerThanThePlanted2", { v0: formatHa(sown) })
                    : t("pages.farm.EditLotPage.enteredManuallyYouCanAlsoDrawThe")
                }
                error={tried ? errors.area : undefined}
              />
            )}
          </>
        )}
        <TextField
          label={t("pages.farm.AddLotPage.plotName")}
          name="name"
          maxLength={60}
          autoComplete="off"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={tried ? errors.name : undefined}
        />
        <ChoiceGroup
          legend={t("farm.irrigationQuestion")}
          choices={IRRIGATION()}
          value={irrigated}
          onChange={setIrrigated}
          hint={IRRIGATION_HINT()}
        />
        <p className="bg-[#EEF2E6] px-4 py-3 text-[14px] leading-snug">
          {t("pages.farm.EditLotPage.changingIrrigationRecalculatesThisPlotsDiagnosisStrategies")}
        </p>
        <Button type="submit" disabled={outside} loading={update.isPending} loadingText={t("pages.account.AccountPage.saving")}>
          {t("pages.farm.EditLotPage.saveChanges")}
        </Button>
        <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-center py-2`}>
          {t("pages.account.AccountPage.cancel")}
        </Link>
      </form>
      <section aria-labelledby="borrar" className="flex flex-col gap-2 border-t-2 border-superficie-borde pt-4">
        <h2 id="borrar" className="text-[18px]">
          {t("pages.farm.EditLotPage.deleteThisPlot")}
        </h2>
        <p className="text-[14px] text-texto-secundario">{t("pages.farm.EditLotPage.thePlotItsPlantingsAndHistoryWill")}</p>
        <Button variant="danger" className="w-full sm:w-[220px]" onClick={() => setConfirming(true)}>
          {t("pages.farm.EditLotPage.deleteThisPlot")}
        </Button>
      </section>
      <ConfirmDialog
        open={confirming}
        onOpenChange={(next) => {
          setConfirming(next);
          if (!next) remove.reset();
        }}
        title={t("pages.farm.EditLotPage.delete", { v0: lot.name })}
        cancelLabel={t("pages.account.AccountPage.noGoBack")}
        confirmLabel={t("pages.farm.EditLotPage.yesDeleteThePlot")}
        busy={remove.isPending}
        busyLabel={t("common.deleting")}
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => void navigate(PATHS.farm, { replace: true }) })}
      >
        <ul className="flex flex-col gap-2">
          {[
            crops > 0
              ? t("pages.farm.EditLotPage.hiddenFromMyFarmAlongWithIts", {
                  v0: crops === 1 ? t("farm.activePlanting") : t("pages.farm.EditLotPage.plantingsInProgress", { v0: crops }),
                })
              : t("pages.farm.EditLotPage.hiddenFromMyFarmAlongWithIts2"),
          ].map((item) => (
            <li key={item} className="flex gap-3">
              <span aria-hidden="true" className="mt-1.5 block size-3.5 shrink-0 bg-oscuro-rojo" />
              {item}
            </li>
          ))}
        </ul>
        {remove.error && (
          <Alert>{remove.error instanceof ApiError ? remove.error.message : t("pages.auth.LoginPage.somethingWentWrongTryAgain")}</Alert>
        )}
      </ConfirmDialog>
    </MapScene>
  );
}
