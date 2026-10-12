import { Plate } from "./Plate";
import { StatusIcon, TONE_STYLE, type Tone } from "./StatusMark";

/** Nombre de cada estado de una señal. «Sin datos» nunca se dice ni se pinta como riesgo (R1). */
export const TONE_LABEL: Record<Exclude<Tone, "not_evaluable">, string> = {
  green: "Favorable",
  yellow: "Moderado",
  red: "Desfavorable",
  insufficient_data: "Sin datos",
  not_applicable: "No aplica",
};

/** Banderín compacto con el estado de una señal: silueta, ícono y texto, nunca solo color (W2). */
export function StatusTag({ tone, className = "" }: { tone: keyof typeof TONE_LABEL; className?: string }) {
  const style = TONE_STYLE[tone];
  return (
    <span
      data-tone={tone}
      className={`relative inline-flex h-[34px] items-center gap-2 px-3 text-sm font-bold whitespace-nowrap ${style.ink} ${className}`}
    >
      <Plate {...style.plate} c={Math.min(style.plate.c ?? 8, 8)} strokeWidth={2.5} />
      <span className="relative flex items-center gap-2">
        <StatusIcon icon={style.icon} />
        {TONE_LABEL[tone]}
      </span>
    </span>
  );
}
