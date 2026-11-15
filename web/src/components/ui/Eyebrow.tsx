import type { ReactNode } from "react";

/** El rótulo pequeño en mayúsculas que va sobre los títulos («MI FINCA», «PRECIOS MAYORISTAS»). */
export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">{children}</p>;
}
