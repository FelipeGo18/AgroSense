import { useTranslation } from "react-i18next";

/** La API todavía entrega razones, limitaciones y errores en español (HU-233). */
export function ApiLanguageNotice() {
  const { t, i18n } = useTranslation();
  if (i18n.resolvedLanguage !== "en") return null;
  return (
    <p role="note" className="text-sm text-texto-secundario">
      {t("api.languageNotice")}
    </p>
  );
}
