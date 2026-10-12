import type { ButtonHTMLAttributes } from "react";
import { Plate } from "./Plate";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** Muestra un indicador y bloquea el botón mientras se espera una respuesta. */
  loading?: boolean;
  loadingText?: string;
}

const VARIANTS: Record<Variant, { fill: string; side: string; ink: string }> = {
  primary: { fill: "var(--color-accion-primaria)", side: "var(--color-accion-primaria-borde)", ink: "text-texto-sobre-oscuro" },
  secondary: { fill: "var(--color-accion-secundaria)", side: "var(--color-accion-secundaria-borde)", ink: "text-texto-principal" },
};

/** Un bloque del diorama: cara triangulada y canto inferior. Al presionar, el bloque se hunde. */
export function Button({
  variant = "primary",
  loading = false,
  loadingText = "Cargando…",
  disabled,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  const v = VARIANTS[variant];
  // Deshabilitado es un bloque plano, sin canto. En carga conserva su color: sigue siendo la acción en curso.
  const flat = disabled && !loading;
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`plate-button relative inline-flex h-[58px] min-w-tactil-minimo items-start justify-center px-6 font-bold outline-none disabled:cursor-not-allowed ${
        flat ? "text-texto-secundario" : v.ink
      } ${className}`}
      {...rest}
    >
      {flat ? (
        <Plate fill="var(--color-superficie-panel-suave)" top={6} />
      ) : (
        <Plate fill={v.fill} side={v.side} depth={6} bottom={6} faceted ring="focus" />
      )}
      <span className={`plate-content relative flex h-[52px] items-center gap-2 ${flat ? "translate-y-[6px]" : ""}`}>
        {loading && <Spinner />}
        {loading ? loadingText : children}
      </span>
    </button>
  );
}
