import { cropName as cropLabel } from "@/features/farm/seasons";
import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "@/components/layout/LanguageLink";
import { Combobox } from "@/components/ui/Combobox";
import { SelectField } from "@/components/ui/SelectField";
import { useMunicipalities } from "@/features/farm/lots";
import { useCrops } from "@/features/farm/seasons";

export function useChangesContext() {
  const [params, setParams] = useSearchParams();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  const municipalityId = params.get("municipio") ?? "";
  const cropId = params.get("cultivo") ?? "";
  const irrigation = params.get("riego") ?? "nose";
  const municipality = municipalities.data?.find((item) => item.municipality_id === municipalityId);
  const crop = crops.data?.find((item) => item.crop_id === cropId && item.kind === "crop");
  const ready = municipalities.isSuccess && crops.isSuccess;
  const irrigationValid = ["si", "no", "nose"].includes(irrigation);
  return {
    municipalityId,
    cropId,
    irrigation,
    municipality,
    crop,
    municipalities,
    crops,
    ready,
    error: municipalities.error ?? crops.error,
    irrigationValid,
    valid: Boolean(ready && municipality && crop && irrigationValid),
    change(name: string, value: string) {
      const next = new URLSearchParams(params);
      if (value) next.set(name, value);
      else next.delete(name);
      setParams(next, { preventScrollReset: true });
    },
  };
}

export function ChangesContext({ context }: { context: ReturnType<typeof useChangesContext> }) {
  useTranslation();
  const { municipality, municipalities, crops, ready, error, change } = context;
  if (error)
    return (
      <p role="alert">
        {t("pages.changes.ChangesContext.weCouldNotLoadMunicipalitiesAndCrops")} {error.message}
      </p>
    );
  return (
    <div className="flex min-w-0 flex-col gap-5" aria-label={t("pages.changes.ChangesContext.historicalComparisonInputs")}>
      <Combobox
        label={t("pages.farm.AddLotPage.municipality")}
        placeholder={t("pages.changes.ChangesContext.findYourMunicipality")}
        loading={municipalities.isPending}
        options={(municipalities.data ?? []).map((item) => ({ id: item.municipality_id, label: item.name, hint: item.department }))}
        value={municipality ? { id: municipality.municipality_id, label: municipality.name, hint: municipality.department } : null}
        onChange={(option) => change("municipio", option.id)}
        error={
          ready && context.municipalityId && !municipality ? t("pages.changes.ChangesContext.chooseAMunicipalityFromTheCatalog") : undefined
        }
      />
      <SelectField
        label={t("pages.farm.SeasonFormPage.crop")}
        value={context.cropId}
        disabled={crops.isPending}
        onChange={(event) => change("cultivo", event.target.value)}
        options={[
          { value: "", label: t("pages.changes.LotChangesLink.chooseACrop") },
          ...(crops.data ?? []).filter((item) => item.kind === "crop").map((item) => ({ value: item.crop_id, label: cropLabel(item) })),
        ]}
        error={ready && context.cropId && !context.crop ? t("pages.changes.ChangesContext.chooseACropFromTheCatalog") : undefined}
      />
      <SelectField
        label={t("pages.changes.ChangesContext.doYouHaveIrrigation")}
        value={context.irrigationValid ? context.irrigation : ""}
        onChange={(event) => change("riego", event.target.value)}
        options={[
          { value: "", label: t("pages.changes.ChangesContext.chooseAnOption") },
          { value: "si", label: t("features.diagnosis.consult.yes") },
          { value: "no", label: t("features.diagnosis.consult.no") },
          { value: "nose", label: t("features.diagnosis.consult.iDontKnow") },
        ]}
        error={context.irrigationValid ? undefined : t("pages.changes.ChangesContext.chooseAnIrrigationOption")}
        hint={t("pages.changes.ChangesContext.ifUnsureTheComparisonAssumesNoIrrigation")}
      />
      {context.valid && (
        <p className="font-bold">
          {cropLabel(context.crop)} · {municipality?.name}, {municipality?.department}
        </p>
      )}
      <p className="text-sm text-texto-secundario">{t("pages.changes.ChangesContext.theDataDescribesTheMunicipalityIncludingWhen")}</p>
    </div>
  );
}
