import { GIBS_LEGEND_URL } from "@/app/config";
import { GIBS_LAYERS, GIBS_SOURCE, type GibsLayer, type GibsStatus } from "./gibs";
import type { useGibs } from "./useGibs";

/** Los textos del panel de las capas de NASA GIBS (HU-211). */
const LAYER_NAME: Record<GibsLayer, string> = { color: "Imagen satelital", ndvi: "Verdor (NDVI)" };
const PRODUCT: Record<GibsLayer, string> = {
  color: "MODIS Terra · Color real",
  ndvi: "MODIS Terra · NDVI móvil de 8 días",
};
const DATE_TEXT: Record<GibsLayer, (date: string) => string> = {
  color: (date) => `Fecha de la imagen: ${date}`,
  ndvi: (date) => `Compuesto móvil de 8 días · fecha GIBS: ${date}`,
};
const STATUS_TEXT: Record<GibsStatus, string> = {
  loading: "Cargando imágenes de la NASA…",
  ready: "Capa cargada. Puede haber zonas sin observación.",
  error: "Capa no disponible.",
  off: "Apagada",
  empty:
    "No hay imagen para el centro de esta zona en la fecha elegida. Mostramos el mapa base. Pruebe una fecha anterior o mueva el mapa.",
};

export function GibsPanel({ gibs }: { gibs: ReturnType<typeof useGibs> }) {
  const active = (Object.keys(GIBS_LAYERS) as GibsLayer[]).filter((key) => gibs.selected[key]);
  const failed = active.some((key) => gibs.status[key] === "error");
  return (
    <details className="border-borde w-[min(280px,calc(100vw-100px))] rounded-xl border bg-white p-3 text-sm text-texto-principal shadow-md md:w-[min(280px,calc(100vw-560px))]">
      <summary className="min-h-11 cursor-pointer content-center font-bold focus-visible:outline-2">Capas de la NASA</summary>
      <div className="max-h-[max(100px,calc(55svh-190px))] overflow-y-auto overscroll-contain pt-2 md:max-h-[calc(100svh-220px)]">
        {(Object.keys(GIBS_LAYERS) as GibsLayer[]).map((key) => (
          <div key={key} className="mb-3">
            <label className="flex min-h-11 cursor-pointer items-center gap-3 font-bold">
              <input type="checkbox" className="size-5" checked={gibs.selected[key]} onChange={() => gibs.toggle(key)} />
              {LAYER_NAME[key]}
            </label>
            <p className="text-xs break-words">{PRODUCT[key]}</p>
            <p>MODIS Terra · resolución nominal 250 m. Acercar no añade detalle.</p>
            <p>{gibs.dates ? DATE_TEXT[key](gibs.dates[key]) : "Active una capa para consultar su fecha disponible."}</p>
            {gibs.dates && (
              <label className="mt-2 block">
                Fecha · {LAYER_NAME[key]}
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
            {gibs.selected[key] && <p role="status">{STATUS_TEXT[gibs.status[key]]}</p>}
          </div>
        ))}
        {failed && (
          <div role="status">
            <p>GIBS no responde o no pudo cargar la capa. Sigue disponible el mapa de OpenStreetMap para ver y dibujar su lote.</p>
            <button type="button" className="min-h-11 underline" onClick={gibs.retry}>
              Reintentar
            </button>
          </div>
        )}
        <p>
          La imagen corresponde a la fecha indicada; no es una vista en vivo ni necesariamente de hoy. Puede mostrar nubes. El verdor es de
          la zona a la resolución del producto, no una medición de su lote.
        </p>
        <p className="mt-2">Estas capas solo sirven para ver: no cambian los resultados de AgroSense.</p>
        {gibs.selected.ndvi && gibs.status.ndvi === "ready" && (
          <img
            src={GIBS_LEGEND_URL}
            alt="Leyenda oficial del verdor MODIS NDVI: colores y valores del índice, con zonas sin datos."
            className="mt-2 w-full"
          />
        )}
        <p className="mt-2 text-xs">
          Reconocemos el uso de imágenes proporcionadas por NASA Global Imagery Browse Services (GIBS), parte del sistema de datos e
          información de ciencias de la Tierra de la NASA (ESDIS).
        </p>
        <a href={GIBS_SOURCE.url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center underline">
          Fuente y condiciones de uso · NASA GIBS
        </a>
      </div>
    </details>
  );
}
