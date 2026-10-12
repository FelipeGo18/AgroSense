import gsap from "gsap";
import { createContext, use, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Mascot, type MascotMood } from "./Mascot";

/**
 * La mascota como guía de una página larga. Cada sección reserva un lugar para ella (`MascotSlot`) y una sola
 * mascota (`MascotFlyer`) vuela del lugar de una sección al de la siguiente a medida que se baja. Si el lugar de
 * la sección activa no está a la vista, va al lugar que sí se vea; si no hay ninguno, espera en una esquina.
 *
 * Con «reducir movimiento» no hay vuelo: cada lugar muestra su propia mascota, quieta.
 */

interface Slot {
  el: HTMLElement;
  mood: MascotMood;
}

interface Guide {
  slots: Map<string, Slot>;
  active: string;
  flying: boolean;
}

const GuideContext = createContext<Guide | null>(null);

export interface MascotGuideProps {
  /** Lugar en el que debe estar la mascota ahora: el `id` de un `MascotSlot`. */
  active: string;
  /** Falso con «reducir movimiento»: cada lugar dibuja su mascota y nada vuela. */
  flying: boolean;
  children: ReactNode;
}

export function MascotGuide({ active, flying, children }: MascotGuideProps) {
  const [slots] = useState(() => new Map<string, Slot>());
  const guide = useMemo(() => ({ slots, active, flying }), [slots, active, flying]);
  return <GuideContext value={guide}>{children}</GuideContext>;
}

export interface MascotSlotProps {
  id: string;
  /** Gesto de la mascota cuando llega a este lugar. */
  mood?: MascotMood;
  /** El tamaño lo da el ancho de esta caja; el alto guarda la proporción de la mascota. */
  className?: string;
}

/** Lugar reservado para la mascota dentro de una sección. Ocupa su espacio aunque la mascota aún no haya llegado. */
export function MascotSlot({ id, mood = "idle", className = "" }: MascotSlotProps) {
  const guide = use(GuideContext);
  const el = useRef<HTMLDivElement>(null);
  const slots = guide?.slots;
  useEffect(() => {
    if (!slots || !el.current) return;
    slots.set(id, { el: el.current, mood });
    return () => {
      slots.delete(id);
    };
  }, [slots, id, mood]);
  return (
    <div ref={el} data-mascot-slot={id} aria-hidden="true" className={`pointer-events-none aspect-[300/250] shrink-0 ${className}`}>
      {(!guide || !guide.flying) && <Mascot mood={mood} lively decorative className="size-full" />}
    </div>
  );
}

/** Ancho con el que se dibuja la mascota que vuela; su tamaño en pantalla se ajusta con una escala. */
const BASE = 300;
/** Un lugar cuenta como «a la vista» si asoma entre la barra superior y el borde de abajo. */
const TOP_EDGE = 84;
const BOTTOM_EDGE = 24;
/** Milisegundos que tarda en recorrer casi dos tercios de lo que le falta: da el vuelo suave. */
const EASE_MS = 150;

/** La mascota que vuela. Va una sola vez, dentro de `MascotGuide`. */
export function MascotFlyer() {
  const guide = use(GuideContext);
  const el = useRef<HTMLDivElement>(null);
  const [pose, setPose] = useState<{ mood: MascotMood; docked: boolean }>({ mood: "idle", docked: false });
  const active = useRef(guide?.active);
  useEffect(() => {
    active.current = guide?.active;
  }, [guide?.active]);

  const slots = guide?.slots;
  const flying = guide?.flying ?? false;
  useEffect(() => {
    const node = el.current;
    if (!node || !slots || !flying) return;
    let x = 0;
    let y = 0;
    let w = 0;
    let placed = false;
    let moving = false;
    let last = performance.now();
    let shown = "";

    const tick = () => {
      const now = performance.now();
      const dt = Math.min(now - last, 64);
      last = now;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      // Primero el lugar de la sección activa; si no se ve, el que esté a la vista más cerca del centro.
      let slot: Slot | undefined;
      let rect: DOMRect | undefined;
      let best = Infinity;
      for (const [id, candidate] of slots) {
        const box = candidate.el.getBoundingClientRect();
        if (box.width === 0 || box.bottom < TOP_EDGE || box.top > vh - BOTTOM_EDGE) continue;
        const score = id === active.current ? -1 : Math.abs((box.top + box.bottom) / 2 - vh / 2);
        if (score < best) [best, slot, rect] = [score, candidate, box];
      }
      const inView = !!rect;
      // Sin lugar a la vista espera en la esquina de abajo, pequeña, sin tapar el contenido.
      const dockW = vw < 768 ? 72 : 104;
      const margin = vw < 768 ? 10 : 24;
      const tx = rect ? rect.left : vw - dockW - margin;
      const ty = rect ? rect.top : vh - (dockW * 250) / 300 - margin;
      const tw = rect ? rect.width : dockW;
      if (!placed) {
        [x, y, w, placed] = [tx, ty, tw, true];
      } else {
        const k = 1 - Math.exp(-dt / EASE_MS);
        x += (tx - x) * k;
        y += (ty - y) * k;
        w += (tw - w) * k;
      }
      const gap = Math.hypot(tx - x, ty - y);
      moving = moving ? gap > 8 : gap > 44;
      node.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) scale(${(w / BASE).toFixed(4)})`;
      node.style.visibility = "visible";
      const mood: MascotMood = moving ? "flying" : inView ? (slot?.mood ?? "idle") : "idle";
      const key = `${mood}|${!inView}`;
      if (key !== shown) {
        shown = key;
        setPose({ mood, docked: !inView && !moving });
      }
    };
    gsap.ticker.add(tick);
    return () => gsap.ticker.remove(tick);
  }, [slots, flying]);

  if (!flying) return null;
  return (
    <div
      ref={el}
      data-mascot-flyer
      aria-hidden="true"
      className="pointer-events-none invisible fixed top-0 left-0 z-30 origin-top-left will-change-transform"
      style={{ width: BASE }}
    >
      <div className={pose.mood === "flying" ? "" : "mascot-float"}>
        <Mascot
          mood={pose.mood}
          size={BASE}
          lively
          decorative
          className={`h-auto w-full ${pose.docked ? "drop-shadow-[0_4px_0_rgb(30_42_58/0.25)]" : ""}`}
        />
      </div>
    </div>
  );
}
