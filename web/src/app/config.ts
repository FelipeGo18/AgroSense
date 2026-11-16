import type { Brand } from "@/components/layout/brandIcons";

/**
 * Lo que cambia entre entornos sale de las variables `VITE_*` (`web/.env`; ejemplo en `web/.env.example`).
 * Las redes del equipo son públicas y tienen su dirección por defecto aquí: la imagen de producción no recibe ningún
 * `.env` (`.dockerignore`), y sin ella el pie de página quedaba sin redes. Una variable `VITE_SOCIAL_*` las cambia.
 */

const env = (key: string) => {
  const value: unknown = import.meta.env[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
};

const SOCIAL_ENV: { brand: Brand; label: string; key: string; fallback: string | null }[] = [
  { brand: "github", label: "GitHub", key: "VITE_SOCIAL_GITHUB", fallback: "https://github.com/FelipeGo18" },
  { brand: "instagram", label: "Instagram", key: "VITE_SOCIAL_INSTAGRAM", fallback: "https://www.instagram.com/felipego_23/" },
  {
    brand: "linkedin",
    label: "LinkedIn",
    key: "VITE_SOCIAL_LINKEDIN",
    fallback: "https://www.linkedin.com/in/andres-felipe-gonzalez-garzon-1623a128b/",
  },
  { brand: "youtube", label: "YouTube", key: "VITE_SOCIAL_YOUTUBE", fallback: null },
];

/**
 * La hora de la región piloto (Colombia): UTC−5 todo el año. «Hoy» y «el mes en curso» de las fechas de siembra se
 * cuentan con ella, igual que en la API (`specs/02-contratos.md`, «Fechas»), aunque el navegador esté en otra zona.
 */
export const REGION_TIME_ZONE = "America/Bogota";

/** WMTS público de NASA GIBS, sin clave. HU-211. */
export const GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
export const GIBS_LEGEND_URL = "https://gibs.earthdata.nasa.gov/legends/MODIS_NDVI_H.svg";

/** Respuestas simuladas activas (HU-013): solo en `npm run dev` con `VITE_SIMULATION=true`. */
export const SIMULATION = import.meta.env.VITE_SIMULATION === "true" && import.meta.env.DEV;

/** Redes del equipo que tienen dirección. Una red sin dirección no aparece: no se dibuja un enlace sin destino. */
export const SOCIAL_LINKS = SOCIAL_ENV.flatMap(({ brand, label, key, fallback }) => {
  const href = env(key) ?? fallback;
  return href ? [{ brand, label, href }] : [];
});
