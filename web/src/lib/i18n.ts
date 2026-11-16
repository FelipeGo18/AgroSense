import { createInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import es from "@/locales/es.json";
import en from "@/locales/en.json";

export type Language = "es" | "en";
export const LANGUAGE_KEY = "agrosense:language";
export const isLanguage = (value: unknown): value is Language => value === "es" || value === "en";

export function detectLanguage(search: string, stored: unknown): Language {
  const requested = new URLSearchParams(search).get("lang");
  return isLanguage(requested) ? requested : isLanguage(stored) ? stored : "es";
}

export const i18n = createInstance();
void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: "es",
  fallbackLng: "es",
  supportedLngs: ["es", "en"],
  initAsync: false,
  keySeparator: false,
  interpolation: { escapeValue: false },
});

/** Para helpers sin React; los componentes se suscriben con useTranslation(). */
export const t = (key: string, values: Record<string, unknown> = {}): string => i18n.t(key, values);
export const locale = () => (i18n.resolvedLanguage === "en" ? "en-US" : "es-CO");

/** Solo se recuerda la preferencia local; no se envía a la API. */
export function rememberLanguage(language: Language) {
  try {
    localStorage.setItem(LANGUAGE_KEY, language);
  } catch {
    /* Navegación privada o almacenamiento bloqueado. */
  }
  document.documentElement.lang = language;
}

export function initLanguage() {
  let stored: unknown;
  try {
    stored = localStorage.getItem(LANGUAGE_KEY);
  } catch {
    /* La URL y el español siguen funcionando. */
  }
  const language = detectLanguage(window.location.search, stored);
  void i18n.changeLanguage(language);
  rememberLanguage(language);
}

/** Conserva consulta y fragmento; no cambia los identificadores del contrato. */
export function languagePath(path: string, language: string): string {
  const url = new URL(path, "https://agrosense.local");
  // No volver a serializar otros parámetros: ?dibujar es una bandera y conserva su forma.
  const parts = url.search
    .slice(1)
    .split("&")
    .filter((part) => part && !new URLSearchParams(part).has("lang"));
  if (language === "en") parts.push("lang=en");
  return `${url.pathname}${parts.length ? `?${parts.join("&")}` : ""}${url.hash}`;
}
