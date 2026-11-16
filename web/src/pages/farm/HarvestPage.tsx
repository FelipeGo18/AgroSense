import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router";
import { Link, useNavigate } from "@/components/layout/LanguageLink";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/TextField";
import { formatHa, useLot, type LotDetail } from "@/features/farm/lots";
import { cropNames, formatDate, todayIso, useCrops, useSeasons, useUpdateSeason, type Season } from "@/features/farm/seasons";
import { AccountShell, LINK } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Shell } from "./SeasonFormPage";
import { LotBar, type Part } from "./SeasonParts";

/**
 * Registrar la cosecha (HU-165). Figma: «Registrar la cosecha». La fecha va entre la siembra y hoy; al guardar, ese
 * terreno queda libre. «Guardar cosecha y registrar la siembra» lleva a la siembra con esta cosecha ya marcada.
 */
export function HarvestPage() {
  useTranslation();
  const { lotId = "", seasonId = "" } = useParams();
  const lot = useLot(lotId);
  const seasons = useSeasons(lotId);
  const crops = useCrops();
  const season = seasons.data?.find((s) => s.season_id === seasonId);
  const missing = seasons.isSuccess && (!season || !!season.harvest_date);
  return (
    <AccountShell>
      {() =>
        lot.isError || seasons.isError || crops.isError || missing ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <Alert>
              {lot.error instanceof ApiError && lot.error.status === 404
                ? t("pages.farm.LotPage.thatPlotDoesNotExistOrIs")
                : missing
                  ? season
                    ? t("pages.farm.HarvestPage.thisPlantingAlreadyHasAHarvestRecorded")
                    : t("pages.farm.SeasonFormPage.thatPlantingDoesNotExistOrIs")
                  : t("pages.farm.SeasonFormPage.weCouldNotLoadTheDataTry")}
            </Alert>
          </Shell>
        ) : lot.isPending || seasons.isPending || crops.isPending || !season ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <p role="status">{t("pages.account.AccountShell.loading")}</p>
          </Shell>
        ) : (
          <HarvestForm lot={lot.data} season={season} names={cropNames(crops.data)} />
        )
      }
    </AccountShell>
  );
}

function HarvestForm({ lot, season, names }: { lot: LotDetail; season: Season; names: Map<string, string> }) {
  useTranslation();
  const navigate = useNavigate();
  const update = useUpdateSeason(lot.lot_id, season.season_id);
  const [date, setDate] = useState(todayIso() < season.sowing_date ? season.sowing_date : todayIso());
  const [tried, setTried] = useState(false);
  const name = names.get(season.crop_id) ?? season.crop_id;

  const error = !date
    ? t("pages.farm.HarvestPage.enterTheHarvestDate")
    : date < season.sowing_date
      ? t("pages.farm.HarvestPage.harvestCannotBeBeforePlanting")
      : date > todayIso()
        ? t("pages.farm.HarvestPage.theHarvestDateCannotBeInThe")
        : undefined;
  const save = (thenSow: boolean) => (event?: FormEvent) => {
    event?.preventDefault();
    setTried(true);
    if (error) return;
    update.mutate(
      { harvest_date: date },
      {
        onSuccess: () =>
          void navigate(thenSow ? PATHS.sow(lot.lot_id, season.season_id) : PATHS.lot(lot.lot_id), {
            state: { notice: t("pages.farm.HarvestPage.harvestOfRecordedThatLandIsNow", { v0: name.toLowerCase() }) },
          }),
      },
    );
  };

  // Después de cosechar, el terreno de esta siembra queda libre; las demás siguen como están.
  const others = lot.current_seasons.filter((s) => s.season_id !== season.season_id);
  const parts: Part[] = others.map((s) => ({ key: s.season_id, label: names.get(s.crop_id) ?? s.crop_id, ha: s.area_ha }));
  const free = lot.area_ha - parts.reduce((total, part) => total + part.ha, 0);
  if (free > 0.0001) parts.push({ key: "libre", label: t("pages.farm.SeasonFormPage.available"), ha: free, free: true });

  return (
    <Shell
      lotId={lot.lot_id}
      lotName={lot.name}
      aside={
        <Card bodyClassName="gap-3">
          <Eyebrow>{t("pages.farm.SeasonFormPage.theResultingPlot")}</Eyebrow>
          <h2 className="text-[22px]">{t("pages.farm.HarvestPage.afterHarvesting")}</h2>
          <LotBar parts={parts} total={lot.area_ha} />
          <p className="text-[15px] text-texto-secundario">
            {formatHa(season.area_ha)} {t("pages.farm.HarvestPage.of")} {name.toLowerCase()}{" "}
            {t("pages.farm.HarvestPage.isAvailableForTheNextPlanting")}
          </p>
        </Card>
      }
    >
      <title>{t("pages.farm.HarvestPage.recordHarvestAgrosense", { v0: lot.name })}</title>
      <header>
        <Eyebrow>{t("nav.farm")}</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.farm.HarvestPage.recordTheHarvest")}</h1>
        <p className="text-texto-secundario">
          {name} · {formatHa(season.area_ha)} {t("pages.farm.HarvestPage.plantedOn")} {formatDate(season.sowing_date)}
        </p>
      </header>
      {update.isError && (
        <Alert>{update.error instanceof ApiError ? update.error.message : t("pages.account.PrioritiesCard.couldNotSaveTryAgain")}</Alert>
      )}
      <form onSubmit={save(false)} noValidate className="flex flex-col gap-5">
        <TextField
          label={t("pages.farm.HarvestPage.whenDidYouHarvest")}
          name="harvest_date"
          type="date"
          min={season.sowing_date}
          max={todayIso()}
          value={date}
          onChange={(event) => setDate(event.target.value)}
          hint={
            season.harvest_estimate
              ? t("pages.farm.HarvestPage.theEstimatedHarvestDateWasBasedOn", { v0: formatDate(season.harvest_estimate) })
              : undefined
          }
          error={tried ? error : undefined}
        />
        <Button type="button" loading={update.isPending} loadingText={t("pages.account.AccountPage.saving")} onClick={() => save(true)()}>
          {t("pages.farm.HarvestPage.saveHarvestAndRecordPlanting")}
        </Button>
        <Button type="submit" variant="secondary" disabled={update.isPending}>
          {t("pages.farm.HarvestPage.saveOnlyTheHarvest")}
        </Button>
        <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-end py-2`}>
          {t("pages.account.AccountPage.cancel")}
        </Link>
      </form>
    </Shell>
  );
}
