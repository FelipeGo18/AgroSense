import { useId } from "react";
import { Plate } from "@/components/ui/Plate";

export interface Zone {
  value: string;
  title: string;
  note: string;
}

/**
 * Las zonas donde ya tiene lotes y «En otro municipio» (Figma: «D0 · Agregar lote o zona»): tarjetas con un rombo
 * que se rellena al elegir. Radios nativos: se recorren con las flechas del teclado.
 */
export function ZoneChoice({
  legend,
  choices,
  value,
  onChange,
}: {
  legend: string;
  choices: Zone[];
  value: string;
  onChange: (value: string) => void;
}) {
  const name = useId();
  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-2 text-[15px] font-bold text-texto-secundario">{legend}</legend>
      {choices.map((choice) => {
        const checked = choice.value === value;
        return (
          <label key={choice.value} className="relative flex min-h-16 cursor-pointer items-center gap-4 px-5 py-3">
            <Plate
              c={12}
              fill={checked ? "#FFF6EA" : "var(--color-superficie-panel)"}
              stroke={checked ? "var(--color-paleta-calabaza)" : "var(--color-superficie-borde)"}
              strokeWidth={checked ? 3 : 2}
            />
            <input
              type="radio"
              name={name}
              checked={checked}
              onChange={() => onChange(choice.value)}
              className="peer absolute inset-0 cursor-pointer opacity-0"
            />
            <svg aria-hidden="true" viewBox="0 0 24 24" className="relative size-6 shrink-0">
              <polygon
                points="12,1 23,12 12,23 1,12"
                fill={checked ? "var(--color-paleta-calabaza)" : "var(--color-superficie-panel)"}
                stroke="var(--color-paleta-noche)"
                strokeWidth="2"
              />
            </svg>
            <span className="relative flex min-w-0 flex-col">
              <span className="font-bold">{choice.title}</span>
              <span className="text-[14px] text-texto-secundario">{choice.note}</span>
            </span>
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 peer-focus-visible:outline-3 peer-focus-visible:outline-accion-foco"
            />
          </label>
        );
      })}
    </fieldset>
  );
}
