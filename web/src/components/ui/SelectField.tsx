import { useId, useState, type SelectHTMLAttributes } from "react";
import { Plate } from "./Plate";

export interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "id" | "className"> {
  label: string;
  options: { value: string; label: string }[];
  hint?: string;
  error?: string;
  className?: string;
}

/** Lista desplegable del kit, para pocas opciones (por ejemplo, los cultivos del catálogo). El select es nativo. */
export function SelectField({ label, options, hint, error, className = "", ...rest }: SelectFieldProps) {
  const id = useId();
  const [focused, setFocused] = useState(false);
  const note = error ?? hint;
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className="font-bold">
        {label}
      </label>
      <div className="relative flex h-12 items-center">
        <Plate
          c={10}
          fill="var(--color-superficie-panel)"
          stroke={error ? "var(--color-oscuro-rojo)" : focused ? "var(--color-accion-foco)" : "var(--color-superficie-borde)"}
        />
        <select
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? `${id}-note` : undefined}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="relative h-full min-w-0 flex-1 cursor-pointer appearance-none bg-transparent px-5 pr-10 outline-none"
          {...rest}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <svg aria-hidden="true" viewBox="0 0 12 8" className="pointer-events-none absolute right-5 size-3">
          <path d="M1 1 L6 6 L11 1" fill="none" stroke="var(--color-oscuro-oliva)" strokeWidth="2" />
        </svg>
      </div>
      {note && (
        <p id={`${id}-note`} className={`text-[15px] leading-snug ${error ? "font-bold text-oscuro-rojo" : "text-texto-secundario"}`}>
          {note}
        </p>
      )}
    </div>
  );
}
