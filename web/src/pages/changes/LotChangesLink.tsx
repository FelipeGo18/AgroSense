import { cropName as cropLabel } from "@/features/farm/seasons";
import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { changesLink } from "@/features/changes/changes";
import { useCrops } from "@/features/farm/seasons";

/** Un lote puede tener varios cultivos: la persona elige cuál comparar. */
export function LotChangesLink({ municipalityId, irrigated }: { municipalityId: string; irrigated: boolean | null }) {
  useTranslation();
  const crops = useCrops();
  const [cropId, setCropId] = useState("");
  const selected = crops.data?.find((crop) => crop.crop_id === cropId && crop.kind === "crop");
  return (
    <section aria-label={t("pages.changes.LotChangesLink.whatHasChangedInYourArea")} className="flex min-w-0 flex-col gap-3">
      <h2 className="text-[20px]">{t("pages.changes.LotChangesLink.whatHasChangedInYourArea")}</h2>
      <p>{t("pages.changes.LotChangesLink.compareTwoHistoricalPeriodsForACrop")}</p>
      {crops.isError ? (
        <p role="alert">
          {t("pages.changes.LotChangesLink.weCouldNotLoadTheCrops")} {crops.error.message}
        </p>
      ) : (
        <>
          <SelectField
            label={t("pages.changes.LotChangesLink.cropForComparingTheAreasHistory")}
            value={cropId}
            disabled={crops.isPending}
            onChange={(event) => setCropId(event.target.value)}
            options={[
              {
                value: "",
                label: crops.isPending ? t("pages.changes.LotChangesLink.loadingCrops") : t("pages.changes.LotChangesLink.chooseACrop"),
              },
              ...(crops.data ?? []).filter((crop) => crop.kind === "crop").map((crop) => ({ value: crop.crop_id, label: cropLabel(crop) })),
            ]}
          />
          {selected && (
            <ButtonLink
              to={changesLink(municipalityId, selected.crop_id, irrigated)}
              variant="secondary"
              className="w-full sm:w-auto sm:self-start"
            >
              {t("pages.changes.LotChangesLink.seeWhatHasChangedInYourArea")}
            </ButtonLink>
          )}
        </>
      )}
    </section>
  );
}
