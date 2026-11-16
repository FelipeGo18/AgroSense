import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router";
import { isLanguage, languagePath, rememberLanguage } from "@/lib/i18n";

export function LanguageSelector({ className = "" }: { className?: string }) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <select
      aria-label={t("language.label")}
      value={i18n.resolvedLanguage}
      onChange={(event) => {
        const language = event.target.value;
        if (!isLanguage(language)) return;
        void i18n.changeLanguage(language);
        rememberLanguage(language);
        void navigate(languagePath(`${location.pathname}${location.search}${location.hash}`, language), {
          replace: true,
          preventScrollReset: true,
        });
      }}
      className={`min-h-11 max-w-full min-w-11 bg-superficie-panel-suave px-2 text-sm font-bold text-texto-principal ${className}`}
    >
      <option value="es" lang="es">
        {t("components.layout.LanguageSelector.espaol")}
      </option>
      <option value="en" lang="en">
        {t("components.layout.LanguageSelector.english")}
      </option>
    </select>
  );
}
