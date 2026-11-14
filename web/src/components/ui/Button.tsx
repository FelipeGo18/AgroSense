import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { Plate } from "./Plate";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** Muestra un indicador y bloquea el botón mientras se espera una respuesta. */
  loading?: boolean;
  loadingText?: string;
}

const VARIANTS: Record<Variant, { fill: string; side: string; ink: string }> = {
  primary: { fill: "var(--color-accion-primaria)", side: "var(--color-accion-primaria-borde)", ink: "text-texto-sobre-oscuro" },
  secondary: { fill: "var(--color-accion-secundaria)", side: "var(--color-accion-secundaria-borde)", ink: "text-texto-principal" },
  // Para lo que no se puede deshacer, como borrar la cuenta.
  danger: { fill: "var(--color-paleta-rojo)", side: "var(--color-semaforo-rojo-borde)", ink: "text-texto-sobre-oscuro" },
};

// Alto mínimo, no fijo: si el texto no cabe en una línea (por ejemplo «Ver estrategias de rotación» a 360 px), el bloque
// crece y el texto se parte en dos líneas centradas en vez de salirse. La placa se mide sola (`Plate`, ResizeObserver).
const BLOCK = "plate-button relative inline-flex min-h-[58px] min-w-tactil-minimo lg:min-h-[50px] items-start justify-center px-6 font-bold outline-none";

/** La cara del bloque con su canto y su contenido: la comparten el botón y el enlace con forma de botón. */
function Block({ variant, children }: { variant: Variant; children: ReactNode }) {
  const v = VARIANTS[variant];
  return (
    <>
      <Plate fill={v.fill} side={v.side} depth={6} bottom={6} faceted ring="focus" />
      <span className="plate-content relative flex min-h-[52px] items-center gap-2 py-1.5 lg:min-h-11 text-center leading-tight">{children}</span>
    </>
  );
}

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
  // Deshabilitado es un bloque plano, sin canto. En carga conserva su color: sigue siendo la acción en curso.
  const flat = disabled && !loading;
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${BLOCK} disabled:cursor-not-allowed ${flat ? "text-texto-secundario" : VARIANTS[variant].ink} ${className}`}
      {...rest}
    >
      {flat ? (
        <>
          <Plate fill="var(--color-superficie-panel-suave)" top={6} />
          <span className="plate-content relative flex min-h-[52px] translate-y-[6px] items-center gap-2 py-1.5 lg:min-h-11 text-center leading-tight">
            {children}
          </span>
        </>
      ) : (
        <Block variant={variant}>
          {loading && <Spinner />}
          {loading ? loadingText : children}
        </Block>
      )}
    </button>
  );
}

export interface ButtonLinkProps extends LinkProps {
  variant?: Variant;
}

/** El mismo bloque cuando la acción es ir a otra página: es un enlace, no un botón. */
export function ButtonLink({ variant = "primary", className = "", children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={`${BLOCK} ${VARIANTS[variant].ink} ${className}`} {...rest}>
      <Block variant={variant}>{children}</Block>
    </Link>
  );
}
