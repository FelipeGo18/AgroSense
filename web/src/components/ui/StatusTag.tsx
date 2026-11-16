import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { Plate } from "./Plate";
import { StatusIcon, TONE_STYLE, type Tone } from "./StatusMark";

/** Nombre de cada estado de una señal. «Sin datos» nunca se dice ni se pinta como riesgo (R1). */
export const TONE_LABEL = (): Record<Exclude<Tone, "not_evaluable">, string> => ({
  unrated: t("status.unrated"),
  green: t("status.green"),
  yellow: t("status.yellow"),
  red: t("status.red"),
  insufficient_data: t("status.insufficient_data"),
  not_applicable: t("status.not_applicable"),
});

/** Banderín compacto con el estado de una señal: silueta, ícono y texto, nunca solo color (W2). */
export function StatusTag({ tone, className = "" }: { tone: keyof ReturnType<typeof TONE_LABEL>; className?: string }) {
  const { t } = useTranslation();
  const style = TONE_STYLE[tone];
  return (
    <span
      data-tone={tone}
      className={`relative inline-flex h-[34px] items-center gap-2 px-3 text-sm font-bold whitespace-nowrap ${style.ink} ${className}`}
    >
      <Plate {...style.plate} c={Math.min(style.plate.c ?? 8, 8)} strokeWidth={2.5} />
      <span className="relative flex items-center gap-2">
        <StatusIcon icon={style.icon} />
        {t(`status.${tone}`)}
      </span>
    </span>
  );
}
