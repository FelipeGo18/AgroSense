import type { ReactNode } from "react";
import { Plate } from "./Plate";

/** Aviso de error: borde rojo, un cuadrado y texto. Nunca solo color. Se anuncia a los lectores de pantalla. */
export function Alert({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div role="alert" className={`relative flex gap-3 px-4 py-3 font-bold text-oscuro-rojo ${className}`}>
      <Plate c={8} fill="var(--color-superficie-panel)" stroke="var(--color-oscuro-rojo)" />
      <span aria-hidden="true" className="relative mt-1.5 block size-3.5 shrink-0 bg-oscuro-rojo" />
      <div className="relative text-sm">{children}</div>
    </div>
  );
}
