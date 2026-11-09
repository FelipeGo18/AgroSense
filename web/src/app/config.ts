import type { Brand } from "@/components/layout/brandIcons";

/**
 * Lo que cambia entre entornos sale de las variables `VITE_*` (`web/.env`; ejemplo en `web/.env.example`).
 * Ninguna dirección externa se escribe en el código.
 */

const env = (key: string) => {
  const value: unknown = import.meta.env[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
};

const SOCIAL_ENV: { brand: Brand; label: string; key: string }[] = [
  { brand: "github", label: "GitHub", key: "VITE_SOCIAL_GITHUB" },
  { brand: "instagram", label: "Instagram", key: "VITE_SOCIAL_INSTAGRAM" },
  { brand: "linkedin", label: "LinkedIn", key: "VITE_SOCIAL_LINKEDIN" },
  { brand: "youtube", label: "YouTube", key: "VITE_SOCIAL_YOUTUBE" },
];

/** Respuestas simuladas activas (HU-013): solo en `npm run dev` con `VITE_SIMULATION=true`. */
export const SIMULATION = import.meta.env.VITE_SIMULATION === "true" && import.meta.env.DEV;

/** Redes del equipo que tienen dirección. Una red sin dirección no aparece: no se dibuja un enlace sin destino. */
export const SOCIAL_LINKS = SOCIAL_ENV.flatMap(({ brand, label, key }) => {
  const href = env(key);
  return href ? [{ brand, label, href }] : [];
});
