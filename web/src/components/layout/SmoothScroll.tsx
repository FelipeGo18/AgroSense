import { createContext, use, useMemo, type ReactNode } from "react";
import { useSmoothScroll } from "@/hooks/useSmoothScroll";

interface ScrollApi {
  /** Lleva a la sección con ese `id` y deja el foco en su título, para quien navega con teclado o lector. */
  scrollTo: (id: string) => void;
  /** Detiene el scroll mientras hay algo abierto encima (un menú, un diálogo). */
  setLocked: (locked: boolean) => void;
}

const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

const focusTitle = (section: HTMLElement) => section.querySelector<HTMLElement>("[data-section-title]")?.focus({ preventScroll: true });

/** Sin scroll suave (o fuera del proveedor) se salta directo: es lo que pide «reducir movimiento». */
const NATIVE: ScrollApi = {
  scrollTo: (id) => {
    const section = document.getElementById(id);
    if (!section) return;
    section.scrollIntoView({ block: "start" });
    focusTitle(section);
  },
  setLocked: () => {},
};

const ScrollContext = createContext<ScrollApi>(NATIVE);

/** Scroll con inercia (Lenis) para la página que envuelve, y navegación entre sus secciones. */
export function SmoothScroll({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const lenis = useSmoothScroll(enabled);
  const api = useMemo<ScrollApi>(
    () => ({
      scrollTo: (id) => {
        const section = document.getElementById(id);
        const engine = lenis.current;
        if (!section || !engine) return NATIVE.scrollTo(id);
        const distance = Math.abs(section.getBoundingClientRect().top);
        engine.scrollTo(section, {
          duration: Math.max(0.8, Math.min(2.4, distance / 900)),
          easing: easeInOut,
          onComplete: () => focusTitle(section),
        });
      },
      setLocked: (locked) => {
        if (locked) lenis.current?.stop();
        else lenis.current?.start();
      },
    }),
    [lenis],
  );
  return <ScrollContext value={api}>{children}</ScrollContext>;
}

export function useScroll() {
  return use(ScrollContext);
}
