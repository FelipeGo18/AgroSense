import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { useEffect, useState, type ReactNode } from "react";
import { ExampleLabel } from "../components/Labels";
import { Plate } from "../components/Plate";

/** Verdadero si el sistema pide reducir movimiento: entonces el recorrido se muestra sin viaje. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

/**
 * Scroll con inercia (Lenis), sincronizado con ScrollTrigger: la rueda del ratón deja de avanzar a saltos
 * y las líneas de tiempo atadas al scroll se mueven de forma continua.
 */
export function useSmoothScroll(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;
    const lenis = new Lenis({ lerp: 0.085, wheelMultiplier: 0.9 });
    lenis.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(tick);
      lenis.destroy();
    };
  }, [enabled]);
}

/** Panel de interfaz sobre la escena: el dato va en HTML, encima del paisaje (principio 1 de diseño). */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`relative flex max-w-[min(92vw,30rem)] flex-col gap-3 px-6 pt-5 pb-8 ${className}`}>
      <Plate c={16} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" />
      <div className="relative flex flex-col gap-3">{children}</div>
    </div>
  );
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
    <nav aria-label="Recorridos de prueba" className="fixed inset-x-0 top-0 z-30 flex flex-wrap items-center gap-x-4 gap-y-1 bg-paleta-noche/85 px-4 py-2 text-sm text-texto-sobre-oscuro">
      {ROUTES.map((r) => (
        <a key={r.href} href={r.href} aria-current={r.href === current ? "page" : undefined} className={`rounded-sm px-2 py-1 focus-visible:outline-white ${r.href === current ? "bg-white font-bold text-texto-principal" : "underline"}`}>
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
