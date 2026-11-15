import { useTranslation } from "react-i18next";
import { GIBS_LEGEND_URL } from "@/app/config";
import { GIBS_LAYERS, GIBS_SOURCE, type GibsLayer } from "./gibs";
import type { useGibs } from "./useGibs";

export function GibsPanel({ gibs }: { gibs: ReturnType<typeof useGibs> }) {
  const { t } = useTranslation();
  const active = (Object.keys(GIBS_LAYERS) as GibsLayer[]).filter((key) => gibs.selected[key]);
  const failed = active.some((key) => gibs.status[key] === "error");
  return (
    <details className="border-borde w-[min(280px,calc(100vw-100px))] rounded-xl border bg-white p-3 text-sm text-texto-principal shadow-md md:w-[min(280px,calc(100vw-560px))]">
      <summary className="min-h-11 cursor-pointer content-center font-bold focus-visible:outline-2">{t("map.gibs.title")}</summary>
      <div className="max-h-[max(100px,calc(55svh-190px))] overflow-y-auto overscroll-contain pt-2 md:max-h-[calc(100svh-220px)]">
        {(Object.keys(GIBS_LAYERS) as GibsLayer[]).map((key) => (
          <div key={key} className="mb-3">
            <label className="flex min-h-11 cursor-pointer items-center gap-3 font-bold">
              <input type="checkbox" className="size-5" checked={gibs.selected[key]} onChange={() => gibs.toggle(key)} />
              {t(`map.gibs.${key}`)}
            </label>
            <p className="text-xs break-words">{t(`map.gibs.product.${key}`)}</p>
            <p>{t("map.gibs.resolution")}</p>
            <p>{gibs.dates ? t(`map.gibs.date.${key}`, { date: gibs.dates[key] }) : t("map.gibs.datePending")}</p>
            {gibs.dates && (
              <label className="mt-2 block">
                {t("map.gibs.chooseDate", { layer: t(`map.gibs.${key}`) })}
                <input
                  type="date"
                  className="mt-1 min-h-11 w-full rounded border p-2"
                  value={gibs.dates[key]}
                  min={gibs.earliestDates[key]}
                  max={gibs.latestDates?.[key]}
                  onChange={(event) => gibs.chooseDate(key, event.target.value)}
                />
              </label>
            )}
            {gibs.selected[key] && <p role="status">{t(`map.gibs.status.${gibs.status[key]}`)}</p>}
          </div>
        ))}
        {failed && (
          <div role="status">
            <p>{t("map.gibs.failure")}</p>
            <button type="button" className="min-h-11 underline" onClick={gibs.retry}>
              {t("map.gibs.retry")}
            </button>
          </div>
        )}
        <p>{t("map.gibs.limits")}</p>
        <p className="mt-2">{t("map.gibs.visualOnly")}</p>
        {gibs.selected.ndvi && gibs.status.ndvi === "ready" && (
          <img src={GIBS_LEGEND_URL} alt={t("map.gibs.legend")} className="mt-2 w-full" />
        )}
        <p className="mt-2 text-xs">{t("map.gibs.credit")}</p>
        <a href={GIBS_SOURCE.url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center underline">
          {t("map.gibs.source")}
        </a>
      </div>
    </details>
  );
}
