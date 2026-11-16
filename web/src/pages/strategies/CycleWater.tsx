import { ApiLanguageNotice } from "@/components/ui/ApiLanguageNotice";
import { locale, t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { EstimateLabel } from "@/components/ui/Labels";
import { sourceName, sourceNote } from "@/features/diagnosis/signals";
import { formatHa } from "@/features/farm/lots";
import {
  formatRange,
  noShortfall,
  shortfallWords,
  type SoilMoisture,
  type WaterMonth,
  type useWaterPlan,
} from "@/features/strategies/cycle";
import type { Version } from "@/features/version";

type Year = "normal" | "dry";
const MONTH = () => new Intl.DateTimeFormat(locale(), { month: "short", year: "numeric", timeZone: "UTC" });
/** «Oct. de 2027» con mayúscula solo al comienzo: `capitalize` de CSS pondría «Oct De 2027». */
const monthLabel = (year: number, month: number) => {
  const text = MONTH().format(new Date(Date.UTC(year, month - 1, 1)));
  return text.charAt(0).toUpperCase() + text.slice(1);
};
const SHORT_MONTH = () => new Intl.DateTimeFormat(locale(), { month: "short", timeZone: "UTC" });
const NUMBER = () => new Intl.NumberFormat(locale(), { maximumFractionDigits: 2 });

/**
 * El agua del ciclo (HU-215): por mes, cuánto le faltaría al cultivo en rangos, en mm y en m³, en un año normal o en uno
 * seco, con el rótulo de estimación (R10). Sin riego se dice que el cultivo pasaría sed, no «riego probable». Al lado, la
 * humedad del suelo de la zona según cada fuente, para contrastar: nunca un valor combinado (decisión 11).
 */
export function CycleWater({
  water,
  cropName,
  areaHa,
  irrigated,
  version,
}: {
  water: ReturnType<typeof useWaterPlan>;
  cropName: string;
  areaHa: number | null;
  irrigated: boolean | null | undefined;
  version: Version | undefined;
}) {
  useTranslation();
  const [year, setYear] = useState<Year>("normal");
  return (
    <>
      <section aria-labelledby="agua" className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="agua" className="text-[clamp(1.25rem,3vw,1.75rem)]">
            {t("pages.strategies.CycleWater.waterForThisCycle")}
          </h2>
          <p className="max-w-[880px] text-texto-secundario">
            {areaHa
              ? t("pages.strategies.CycleWater.estimatedMonthlyWaterShortfallsForInShown", {
                  v0: formatHa(areaHa),
                  v1: cropName.toLowerCase(),
                })
              : t("pages.strategies.CycleWater.waterNeedsCannotBeCalculatedWithoutThe")}
          </p>
        </div>
        {!areaHa ? null : water.isPending ? (
          <p role="status">{t("pages.strategies.CycleWater.calculatingWaterNeeds")}</p>
        ) : water.isError ? (
          <Alert>
            {water.error instanceof ApiError && water.error.status === 501
              ? t("pages.strategies.CycleWater.theWaterCalculationIsNotAvailableOn")
              : water.error.message}
          </Alert>
        ) : (
          <WaterTable data={water.data} year={year} onYear={setYear} irrigated={irrigated} version={version} />
        )}
      </section>
      {water.data && water.data.soil_moisture.length > 0 && <Moisture rows={water.data.soil_moisture} version={version} />}
    </>
  );
}

function WaterTable({
  data,
  year,
  onYear,
  irrigated,
  version,
}: {
  data: NonNullable<ReturnType<typeof useWaterPlan>["data"]>;
  year: Year;
  onYear: (year: Year) => void;
  irrigated: boolean | null | undefined;
  version: Version | undefined;
}) {
  useTranslation();
  const crop = data.crops[0];
  const total = formatRange(crop?.total_volume_m3[year], "m³");
  const sources = [
    data.sources.rain && t("pages.strategies.CycleWater.rainfall", { v0: sourceName(data.sources.rain, version) }),
    data.sources.et0 && t("pages.strategies.CycleWater.evapotranspiration", { v0: sourceName(data.sources.et0, version) }),
    data.sources.soil && t("pages.strategies.CycleWater.soil", { v0: sourceName(data.sources.soil, version) }),
  ].filter(Boolean);
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <ApiLanguageNotice />
      <EstimateLabel />
      <p className="max-w-[880px] text-[15px]">
        {irrigated === true
          ? t("pages.strategies.CycleWater.rainfallIsInsufficientInTheMarkedMonths")
          : t("pages.strategies.CycleWater.rainfallIsInsufficientInTheMarkedMonths2")}
      </p>
      <ChoiceGroup<Year>
        legend={t("water.year")}
        choices={[
          { value: "normal", label: t("pages.strategies.CycleWater.normalYear") },
          { value: "dry", label: t("pages.strategies.CycleWater.dryYear") },
        ]}
        value={year}
        onChange={onYear}
        hint={t("pages.strategies.CycleWater.aDryYearUsesRainfallExceededIn")}
      />
      {!crop || crop.months.length === 0 ? (
        <p className="text-texto-secundario">{t("pages.strategies.CycleWater.insufficientDataToCalculateWaterNeedsFor")}</p>
      ) : (
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {crop.months.map((month) => (
            <MonthBox key={`${month.year}-${month.month}`} month={month} year={year} irrigated={irrigated} />
          ))}
        </ul>
      )}
      {total && (
        <p className="font-bold">
          {t("pages.strategies.CycleWater.theCycleWouldNeedAnAdditional")} {total}
          {year === "dry" ? t("pages.strategies.CycleWater.inADryYear") : ""}
          {t("pages.strategies.CycleWater.a1000literTankHolds1M")}
        </p>
      )}
      {sources.length > 0 && (
        <p className="text-[14px] text-texto-secundario">
          {t("pages.strategies.CycleWater.sources")} {sources.join(" · ")}.
        </p>
      )}
      {data.limitations.length > 0 && (
        <ul className="flex list-disc flex-col gap-1 pl-5 text-[15px] text-texto-secundario">
          {data.limitations.map((limitation) => (
            <li lang="es" key={limitation}>
              {limitation}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Un mes: si la lluvia alcanza (círculo vacío) o cuánto falta (gota), en mm y en m³. Sin dato, «Sin datos suficientes» (R1). */
function MonthBox({ month, year, irrigated }: { month: WaterMonth; year: Year; irrigated: boolean | null | undefined }) {
  useTranslation();
  const label = monthLabel(month.year, month.month);
  const deficit = month.deficit_mm[year];
  const missing = month.status !== "available" || !deficit;
  const enough = !missing && noShortfall(deficit);
  return (
    <li
      aria-label={label}
      className={`flex min-w-0 flex-col gap-1 border-2 px-3 py-3 text-[15px] leading-snug ${
        missing
          ? "border-dashed border-superficie-borde bg-superficie-panel"
          : enough
            ? "border-superficie-borde bg-superficie-panel"
            : "border-oscuro-cielo bg-[#E6F0F5]"
      }`}
    >
      <p className="font-bold">{label}</p>
      {missing ? (
        <p className="text-texto-secundario">
          <span aria-hidden="true">? </span>
          {t("features.strategies.strategies.insufficientData")}
        </p>
      ) : enough ? (
        <p className="flex items-center gap-2">
          <svg aria-hidden="true" viewBox="0 0 14 14" className="size-3.5 shrink-0">
            <circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </svg>
          {t("pages.strategies.CycleWater.enoughRainfall")}
        </p>
      ) : (
        <>
          <p className="flex items-center gap-2 font-bold">
            <svg aria-hidden="true" viewBox="0 0 14 18" className="h-[18px] w-3.5 shrink-0 text-oscuro-cielo">
              <path d="M7 1 C9 6 13 9 13 12 A6 6 0 0 1 1 12 C1 9 5 6 7 1 Z" fill="currentColor" />
            </svg>
            {formatRange(deficit, "mm")}
          </p>
          <p>{formatRange(month.volume_m3[year], "m³")}</p>
          <p className="text-[14px] text-texto-secundario">{shortfallWords(irrigated)}</p>
        </>
      )}
    </li>
  );
}

/**
 * La humedad del suelo de la zona, por fuente y por mes, cada una en su unidad: la de NASA POWER (modelo) y, si existe,
 * la de SMAP (satélite). Son de la zona, no del lote, y no cambian el cálculo del agua (R10, decisión 11).
 */
function Moisture({ rows, version }: { rows: SoilMoisture[]; version: Version | undefined }) {
  useTranslation();
  const bySource = new Map<string, SoilMoisture[]>();
  for (const row of rows) bySource.set(row.source_id, [...(bySource.get(row.source_id) ?? []), row]);
  return (
    <section aria-labelledby="humedad" className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id="humedad" className="text-[clamp(1.25rem,3vw,1.75rem)]">
          {t("pages.strategies.CycleWater.soilMoistureInTheArea")}
        </h2>
        <p className="max-w-[880px] text-texto-secundario">{t("pages.strategies.CycleWater.normalConditionsInThoseMonthsAccordingTo")}</p>
      </div>
      <ul className="flex flex-col gap-3">
        {[...bySource.entries()].map(([sourceId, months]) => {
          const note = sourceNote(sourceId);
          return (
            <li key={sourceId} className="flex min-w-0 flex-col gap-2 border-2 border-superficie-borde bg-superficie-panel px-4 py-3">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <p className="font-bold">{sourceName(sourceId, version)}</p>
                <p className="text-[14px] font-bold text-oscuro-cielo">{t("pages.diagnosis.SignalList.forComparison")}</p>
              </div>
              {note && <p className="text-[14px] text-texto-secundario">{note}</p>}
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-5">
                {[...months]
                  .sort((a, b) => a.month - b.month)
                  .map((row) => (
                    <div key={row.month} className="flex flex-col">
                      <dt className="text-[14px] text-texto-secundario capitalize">
                        {SHORT_MONTH().format(new Date(Date.UTC(2000, row.month - 1, 1)))}
                      </dt>
                      <dd className="font-bold">
                        {row.value === null ? t("features.diagnosis.signals.noData") : `${NUMBER().format(row.value)} ${row.unit}`}
                      </dd>
                    </div>
                  ))}
              </dl>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
