import { useId, useState, type InputHTMLAttributes } from "react";
import { Plate } from "./Plate";

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "className"> {
  label: string;
  /** Ayuda bajo el campo. */
  hint?: string;
  /** Mensaje de error: reemplaza la ayuda y marca el campo. Nunca solo color: va escrito. */
  error?: string;
  className?: string;
}

/** Campo de texto del kit: etiqueta encima y un campo hundido con borde biselado. */
export function TextField({ label, hint, error, type = "text", className = "", ...rest }: TextFieldProps) {
  const id = useId();
  const [focused, setFocused] = useState(false);
  const [shown, setShown] = useState(false);
  const secret = type === "password";
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
        <input
          id={id}
          type={secret && shown ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? `${id}-note` : undefined}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="relative h-full min-w-0 flex-1 bg-transparent px-5 outline-none placeholder:text-texto-secundario"
          {...rest}
        />
        {secret && (
          <button
            type="button"
            aria-pressed={shown}
            onClick={() => setShown(!shown)}
            className="relative mr-3 min-h-11 px-2 text-sm font-bold text-oscuro-oliva"
          >
            {shown ? "Ocultar" : "Mostrar"}
            <span className="sr-only"> la contraseña</span>
          </button>
        )}
      </div>
      {note && (
        <p id={`${id}-note`} className={`text-[15px] leading-snug ${error ? "font-bold text-oscuro-rojo" : "text-texto-secundario"}`}>
          {note}
        </p>
      )}
    </div>
  );
}
