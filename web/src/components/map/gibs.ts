import { GIBS_URL } from "@/app/config";
import source from "../../../../catalog/gibs.json";

export const GIBS_SOURCE = source;
export const GIBS_LAYERS = {
  color: { product: "MODIS_Terra_CorrectedReflectance_TrueColor", extension: "jpeg", format: "image/jpeg" },
  ndvi: { product: "MODIS_Terra_NDVI_8Day", extension: "png", format: "image/png" },
} as const;
export type GibsLayer = keyof typeof GIBS_LAYERS;
export type GibsStatus = "off" | "loading" | "ready" | "error" | "empty";
export type GibsSelection = Record<GibsLayer, boolean>;
export type GibsDates = Record<GibsLayer, string>;
const WMTS = "http://www.opengis.net/wmts/1.0";
const OWS = "http://www.opengis.net/ows/1.1";

/** Fechas explícitas publicadas por NASA; nunca se supone que haya imagen de hoy. */
export function parseGibsDates(xml: string): GibsDates {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("Invalid GIBS XML");
  const layers = Array.from(doc.getElementsByTagNameNS(WMTS, "Layer"));
  const date = (key: GibsLayer) => {
    const spec = GIBS_LAYERS[key];
    const layer = layers.find((item) => item.getElementsByTagNameNS(OWS, "Identifier")[0]?.textContent === spec.product);
    const dimension = Array.from(layer?.getElementsByTagNameNS(WMTS, "Dimension") ?? []).find(
      (item) => item.getElementsByTagNameNS(OWS, "Identifier")[0]?.textContent === "Time",
    );
    const value = dimension?.getElementsByTagNameNS(WMTS, "Default")[0]?.textContent?.trim();
    const matrix = layer?.getElementsByTagNameNS(WMTS, "TileMatrixSet")[0]?.textContent;
    const formats = Array.from(layer?.getElementsByTagNameNS(WMTS, "Format") ?? []).map((item) => item.textContent);
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value) || matrix !== "GoogleMapsCompatible_Level9" || !formats.includes(spec.format)) {
      throw new Error("GIBS metadata changed");
    }
    return value;
  };
  return { color: date("color"), ndvi: date("ndvi") };
}

/** La primera fecha con imagen de cada producto, de los `<Value>` de su dimensión Time («inicio/fin/periodo»). Sale del
 * servicio, como la última: si GIBS recorta su historial, el selector lo sigue. Sin el dato, no se pone mínimo. */
export function parseGibsEarliest(xml: string): Partial<GibsDates> {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const layers = Array.from(doc.getElementsByTagNameNS(WMTS, "Layer"));
  const earliest: Partial<GibsDates> = {};
  for (const key of Object.keys(GIBS_LAYERS) as GibsLayer[]) {
    const layer = layers.find((item) => item.getElementsByTagNameNS(OWS, "Identifier")[0]?.textContent === GIBS_LAYERS[key].product);
    const starts = Array.from(layer?.getElementsByTagNameNS(WMTS, "Value") ?? [])
      .map((item) => item.textContent?.trim().split("/")[0] ?? "")
      .filter((value) => /^\d{4}-\d{2}-\d{2}$/.test(value))
      .sort();
    if (starts.length) earliest[key] = starts[0];
  }
  return earliest;
}

export type GibsCatalog = { dates: GibsDates; earliest: Partial<GibsDates> };

export async function fetchGibsDates(signal: AbortSignal): Promise<GibsCatalog> {
  const response = await fetch(`${GIBS_URL}/1.0.0/WMTSCapabilities.xml`, { signal });
  if (!response.ok) throw new Error("GIBS unavailable");
  const xml = await response.text();
  return { dates: parseGibsDates(xml), earliest: parseGibsEarliest(xml) };
}

export function gibsTiles(layer: GibsLayer, date: string): string {
  const spec = GIBS_LAYERS[layer];
  return `${GIBS_URL}/${spec.product}/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.${spec.extension}`;
}

/** Ubicación de la zona visible dentro de la tesela original, sin usar los píxeles ampliados del mapa. */
export function gibsSample(lng: number, lat: number) {
  const x = (((lng + 180) / 360) * 512 + 512) % 512;
  const radians = (Math.max(-85.05112878, Math.min(85.05112878, lat)) * Math.PI) / 180;
  const y = Math.max(0, Math.min(511.999999, ((1 - Math.asinh(Math.tan(radians)) / Math.PI) / 2) * 512));
  return { x: Math.floor(x), y: Math.floor(y), px: Math.floor((x % 1) * 256), py: Math.floor((y % 1) * 256) };
}

// El JPEG deja ruido de 1 a 3 en una zona negra: por debajo de este valor no hay imagen (revisión del PR #144).
export const BLACK_NOISE = 10;

/** Los píxeles negros del JPEG de color real son zonas sin imagen; no se presentan como terreno observado. */
export function hasVisiblePixels(pixels: Uint8ClampedArray) {
  return pixels.some((value, index) => index % 4 !== 3 && value > BLACK_NOISE);
}

export async function hasGibsObservation(date: string, lng: number, lat: number, signal: AbortSignal) {
  const sample = gibsSample(lng, lat);
  const url = gibsTiles("color", date).replace("{z}", "9").replace("{x}", String(sample.x)).replace("{y}", String(sample.y));
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error("GIBS unavailable");
  const bitmap = await createImageBitmap(await response.blob());
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 3;
    canvas.height = 3;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) throw new Error("Canvas unavailable");
    context.drawImage(bitmap, Math.min(253, Math.max(0, sample.px - 1)), Math.min(253, Math.max(0, sample.py - 1)), 3, 3, 0, 0, 3, 3);
    return hasVisiblePixels(context.getImageData(0, 0, 3, 3).data);
  } finally {
    bitmap.close();
  }
}
