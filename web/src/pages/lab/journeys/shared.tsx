import type { ReactNode } from "react";
import { Card as BaseCard } from "@/components/ui/Card";
import { ExampleLabel } from "@/components/ui/Labels";

import { useAnimated } from "@/hooks/useLightMode";

/** El laboratorio lo llama «reducir movimiento»: es el modo ligero (HU-158). */
export const useReducedMotion = () => !useAnimated();
export { useSmoothScroll } from "@/hooks/useSmoothScroll";
export { followScroll } from "@/lib/followScroll";

/** Panel de interfaz sobre la escena: el dato va en HTML, encima del paisaje (principio 1 de diseño). */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <BaseCard className={`flex max-w-[min(92vw,30rem)] flex-col ${className}`}>{children}</BaseCard>;
}

const ROUTES = [
  { href: "/recorrido/1", label: "1 · Del satélite al lote" },
  { href: "/recorrido/2", label: "2 · El año del cultivo" },
  { href: "/recorrido/3", label: "3 · Travesía por la cordillera" },
  { href: "/kit", label: "Kit" },
];

/** Barra para saltar entre los tres recorridos de prueba. */
export function JourneyNav({ current }: { current: string }) {
  return (
    <nav
      aria-label="Recorridos de prueba"
      className="fixed inset-x-0 top-0 z-30 flex flex-wrap items-center gap-x-4 gap-y-1 bg-paleta-noche/85 px-4 py-2 text-sm text-texto-sobre-oscuro"
    >
      {ROUTES.map((r) => (
        <a
          key={r.href}
          href={r.href}
          aria-current={r.href === current ? "page" : undefined}
          className={`rounded-sm px-2 py-1 focus-visible:outline-white ${r.href === current ? "bg-white font-bold text-texto-principal" : "underline"}`}
        >
          {r.label}
        </a>
      ))}
      <span className="ml-auto hidden sm:block">
        <ExampleLabel>prototipo con datos de muestra</ExampleLabel>
      </span>
    </nav>
  );
}

export function ScrollHint() {
  return (
    <p className="pointer-events-none absolute inset-x-0 bottom-5 z-20 text-center font-bold text-texto-sobre-oscuro [text-shadow:0_2px_0_rgb(30_42_58/0.7)]">
      Baje con el scroll <span aria-hidden="true">↓</span>
    </p>
  );
}
