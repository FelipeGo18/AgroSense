import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import type { Choice } from "@/components/ui/ChoiceGroup";
import type { Municipality } from "@/features/farm/lots";

/** «¿Este lote tiene riego?» (`irrigated`): sí, no, o nulo si todavía no lo sabe (HU-164). */
export const IRRIGATION = (): Choice<boolean | null>[] => [
  { value: true, label: t("features.diagnosis.consult.yes") },
  { value: false, label: t("features.diagnosis.consult.no") },
  { value: null, label: t("pages.farm.common.iDontKnowYet") },
];

export const IRRIGATION_HINT = () => t("pages.farm.common.withIrrigationRainfallShortagesDoNotCount");

export const irrigationText = (irrigated: boolean | null | undefined) =>
  irrigated === true
    ? t("pages.farm.common.withIrrigation")
    : irrigated === false
      ? t("pages.farm.common.withoutIrrigation")
      : t("pages.farm.common.irrigationNotSpecifiedYet");

export const AREA_HINT = () => t("pages.farm.common.inHectaresOneHectareIs10000M");
export const AREA_ERROR = () => t("features.strategies.entry.enterAnAreaInHectaresGreaterThan");
export const NAME_ERROR = () => t("pages.farm.common.enterANameForThePlot");

/** «Samacá, Boyacá». Sin catálogo, el código: nunca se inventa un nombre. */
export const placeName = (municipality: Municipality | undefined, id: string) =>
  municipality ? `${municipality.name}, ${municipality.department}` : t("pages.farm.common.municipality", { v0: id });

/** Lo que cambia sin dibujo, dicho antes de guardar y en el lote (Figma: «Lote sin dibujar / Área a mano»). */
export function WithoutDrawing({ place }: { place: string }) {
  useTranslation();
  return (
    <div className="border-2 border-oscuro-cielo/60 bg-[#E6F0F5] px-4 py-3 text-[14px] leading-snug">
      <p className="font-bold">{t("pages.farm.common.withoutABoundaryYourPlotHasNo")}</p>
      <ul className="flex list-['·_'] flex-col pl-3">
        <li>{t("pages.farm.common.itDoesNotAppearOnYourFarm")}</li>
        <li>
          {t("pages.farm.common.soilAndAltitudeDataComeFrom")} {place}
          {t("pages.farm.common.ratherThanMeasurementsOfYourPlot")}
        </li>
      </ul>
      <p className="font-bold">{t("pages.farm.common.youCanDrawItLaterWheneverYou")}</p>
    </div>
  );
}

/** «Área calculada con su dibujo» (Figma: «Dibuje su lote»). Es la del navegador; la que se guarda la calcula la API. */
export function DrawnArea({ ha, m2 }: { ha: string; m2: string }) {
  useTranslation();
  return (
    <div className="border-[2.5px] border-paleta-calabaza bg-[#FFF1DF] px-5 py-3">
      <p className="text-[15px] font-bold text-oscuro-calabaza">{t("pages.farm.common.areaCalculatedFromYourBoundary")}</p>
      <p className="flex flex-wrap items-baseline justify-between gap-x-4">
        <span className="font-titulos text-[30px] leading-tight font-semibold">{ha}</span>
        <span className="text-texto-secundario">{m2}</span>
      </p>
    </div>
  );
}

/** El dibujo se sale del municipio (Figma: «se sale del municipio»). No se puede guardar así. */
export function OutsideWarning({ place }: { place: string }) {
  useTranslation();
  return (
    <div role="alert" className="border-2 border-oscuro-rojo bg-[#F9E3DF] px-4 py-3 text-[15px] leading-snug">
      <p className="font-bold text-oscuro-rojo">
        <span aria-hidden="true">▲ </span>
        {t("pages.farm.common.yourPlotExtendsBeyond")} {place}
      </p>
      <p>{t("pages.farm.common.moveThePointsInsideThePurpleDotted")}</p>
    </div>
  );
}

/** Los pasos para dibujar, con el rombo del kit. */
export function DrawSteps({ steps }: { steps: string[] }) {
  useTranslation();
  return (
    <ol className="flex flex-col gap-1.5">
      {steps.map((step) => (
        <li key={step} className="flex items-center gap-3">
          <svg aria-hidden="true" viewBox="0 0 20 20" className="size-4 shrink-0">
            <polygon points="10,1 19,10 10,19 1,10" fill="var(--color-accion-primaria)" />
          </svg>
          {step}
        </li>
      ))}
    </ol>
  );
}
