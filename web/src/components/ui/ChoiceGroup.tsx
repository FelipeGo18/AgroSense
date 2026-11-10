import { useId } from "react";
import { Plate } from "./Plate";

export interface Choice<T> {
  value: T;
  label: string;
}

export interface ChoiceGroupProps<T> {
  /** La pregunta, como «¿Este lote tiene riego?». */
  legend: string;
  choices: Choice<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Ayuda bajo las opciones. */
  hint?: string;
  /** Error bajo las opciones, enlazado a la pregunta (`aria-describedby`). */
  error?: string;
}

/**
 * Una pregunta con pocas respuestas, todas a la vista (radios nativos: se recorren con las flechas del teclado).
 * Cada opción mide al menos 44 px de alto; en 320 px se apilan si no caben.
 */
export function ChoiceGroup<T extends string | number | boolean | null>({
  legend,
  choices,
  value,
  onChange,
  hint,
  error,
}: ChoiceGroupProps<T>) {
  const name = useId();
  const described = [error && `${name}-error`, hint && `${name}-hint`].filter(Boolean).join(" ");
  return (
    <fieldset className="flex min-w-0 flex-col gap-2" aria-describedby={described || undefined}>
      <legend className="mb-2 text-[18px] font-bold">{legend}</legend>
      <div className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-3">
        {choices.map((choice) => {
          const checked = choice.value === value;
          return (
            <label
              key={String(choice.value)}
              className="relative flex min-h-12 cursor-pointer items-center justify-center px-3 text-center"
            >
              {/* Lo elegido va relleno en verde oliva, como en Figma («¿Este lote tiene riego?», Editar lote). */}
              <Plate
                c={10}
                fill={checked ? "var(--color-accion-primaria)" : "var(--color-superficie-panel)"}
                stroke={checked ? "var(--color-accion-primaria-borde)" : "var(--color-superficie-borde)"}
              />
              <input
                type="radio"
                name={name}
                checked={checked}
                onChange={() => onChange(choice.value)}
                className="peer absolute inset-0 cursor-pointer opacity-0"
              />
              <span className={`pointer-events-none relative font-bold ${checked ? "text-texto-sobre-oscuro" : ""}`}>{choice.label}</span>
              {/* El foco del teclado se ve en la opción, no en el radio escondido. */}
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 peer-focus-visible:outline-3 peer-focus-visible:outline-accion-foco"
              />
            </label>
          );
        })}
      </div>
      {error && (
        <p id={`${name}-error`} role="alert" className="text-[15px] leading-snug font-bold text-oscuro-rojo">
          {error}
        </p>
      )}
      {hint && (
        <p id={`${name}-hint`} className="text-[15px] leading-snug text-texto-secundario">
          {hint}
        </p>
      )}
    </fieldset>
  );
}
