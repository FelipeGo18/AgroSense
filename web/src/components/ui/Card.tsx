import type { ReactNode } from "react";
import { Plate } from "./Plate";

/** Tarjeta del diorama: una tabla blanca biselada con su canto. El contenido va en HTML encima. */
export function Card({
  children,
  className = "",
  bodyClassName = "",
}: {
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <div className={`relative px-6 pt-5 pb-8 ${className}`}>
      <Plate c={16} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" />
      <div className={`relative flex flex-col gap-3 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
