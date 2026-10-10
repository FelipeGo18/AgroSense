import { Plate, Stake } from "./Plate";
import { Spinner } from "./Spinner";
import { StatusIcon, TONE_STYLE } from "./StatusMark";

/** Valores de `overall.light` del contrato (specs/01-reglas.md). */
export type Light = "green" | "yellow" | "red" | "not_evaluable";

export const LIGHT_LABEL: Record<Light, string> = {
  green: "Verde · Buen momento",
  yellow: "Amarillo · Con cuidado",
  red: "Rojo · Mejor no ahora",
  not_evaluable: "No evaluable · Faltan datos",
};

export interface TrafficLightBadgeProps {
  light?: Light;
  loading?: boolean;
  className?: string;
}

/** El semáforo como letrero clavado en la parcela. Cada luz tiene silueta, ícono y texto propios. */
export function TrafficLightBadge({ light, loading = false, className = "" }: TrafficLightBadgeProps) {
  const pending = loading || !light;
  const style = pending ? null : TONE_STYLE[light];
  return (
    <span className={`inline-flex flex-col items-center ${className}`}>
      {pending || !style ? (
        <span role="status" className="relative inline-flex h-14 items-center gap-2.5 px-5 font-bold text-texto-secundario">
          <Plate fill="var(--color-superficie-panel-suave)" stroke="var(--color-superficie-borde)" />
          <Spinner className="relative" />
          <span className="relative">Calculando semáforo…</span>
        </span>
      ) : (
        <span data-light={light} className={`relative inline-flex h-14 items-center gap-2.5 font-bold ${style.ink} ${light === "green" ? "px-8" : "px-5"}`}>
          <Plate {...style.plate} />
          <span className="relative flex items-center gap-2.5">
            <StatusIcon icon={style.icon} />
            {LIGHT_LABEL[light]}
          </span>
        </span>
      )}
      <Stake ghost={light === "not_evaluable" && !pending} className="-mt-1" />
    </span>
  );
}
