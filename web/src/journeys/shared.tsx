import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { useEffect, useRef, useState, type ReactNode } from "react";
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

/** Mayor avance, en píxeles, que se acepta de un solo golpe de rueda. Un gesto brusco no salta varias paradas. */
const MAX_WHEEL_STEP = 110;

/** Inercia del scroll: fracción de la distancia que se recorre por cuadro. Más bajo, más suave y más lento. */
const LERP = 0.09;

/**
 * Scroll con inercia (Lenis), sincronizado con ScrollTrigger: la rueda del ratón deja de avanzar a saltos
 * y las líneas de tiempo atadas al scroll se mueven de forma continua. Integración recomendada por Lenis:
 * un solo ciclo (el de GSAP) y sin suavizado de retraso. Devuelve la instancia, o null si está apagado.
 */
export function useSmoothScroll(enabled: boolean) {
  const ref = useRef<Lenis | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const lenis = new Lenis({
      lerp: LERP,
      wheelMultiplier: 1,
      virtualScroll: (data) => {
        data.deltaY = Math.max(-MAX_WHEEL_STEP, Math.min(MAX_WHEEL_STEP, data.deltaY));
        return true;
      },
    });
    ref.current = lenis;
    lenis.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      ref.current = null;
      gsap.ticker.remove(tick);
      lenis.destroy();
    };
  }, [enabled]);
  return ref;
}

/**
 * Un paso de la persecución: acerca `current` a `target` con suavizado, pero nunca más rápido que
 * `maxRate` unidades de línea de tiempo por segundo. Todo va en avance de 0 a 1.
 */
export function stepToward(current: number, target: number, deltaMs: number, total: number, maxRate: number) {
  const diff = target - current;
  const maxStep = (maxRate * deltaMs) / 1000 / total;
  const eased = diff * Math.min(1, deltaMs / 110);
  const step = Math.max(-maxStep, Math.min(maxStep, eased));
  return Math.abs(diff) < 0.00002 ? target : current + step;
}

/**
 * Velocidad permitida según cuánto falta por recorrer. El tope protege del scroll brusco con rueda o dedo.
 * Pero si el usuario salta lejos a propósito (arrastra la barra, pulsa Inicio o Fin), no debe esperar a que
 * se reproduzca todo el viaje: a partir de 2 unidades de distancia se acelera, hasta 4 veces.
 */
export function rateFor(gapUnits: number, maxRate: number, jump: boolean) {
  return jump ? maxRate * Math.max(1, Math.min(4, 1 + (gapUnits - 2) * 0.75)) : maxRate;
}

/** Tras un gesto de rueda o dedo, el scroll sigue moviéndose por inercia este tiempo: aún cuenta como gesto. */
const GESTURE_MS = 1500;

/** Tramo de la línea de tiempo donde está bien quedarse quieto: una parada con contenido. */
export type Rest = readonly [start: number, end: number];

/** Margen con el que se entra a una parada al llegar por imán, para que su contenido ya esté a la vista. */
const REST_EDGE = 0.06;

/**
 * Si el scroll se detuvo en `time`, ¿a dónde hay que llevarlo? Dentro de una parada, a ningún lado (null).
 * En medio de una transición (escenas de relleno), a la parada más cercana en el sentido en que se venía.
 */
export function restTarget(time: number, direction: number, rests: readonly Rest[]): number | null {
  if (rests.length === 0 || rests.some(([a, b]) => time >= a && time <= b)) return null;
  const ahead = rests.find(([a]) => a > time);
  const behind = [...rests].reverse().find(([, b]) => b < time);
  const pick = direction >= 0 ? (ahead ?? behind) : (behind ?? ahead);
  if (!pick) return null;
  return pick === ahead ? pick[0] + REST_EDGE : pick[1] - REST_EDGE;
}

/** Tiempo sin entradas, en ms, tras el que se considera que el usuario dejó de hacer scroll. */
const IDLE_MS = 180;

const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

export interface FollowOptions {
  /** Tope de velocidad, en unidades de línea de tiempo por segundo. */
  maxRate: number;
  /** Paradas con contenido. Si el scroll se detiene fuera de ellas, se lleva solo a la más cercana. */
  rests?: readonly Rest[];
  lenis?: () => Lenis | null;
  /** Tiempo desde el que arrancar; por defecto, el que corresponde al scroll. Sirve al reconstruir la animación. */
  startAt?: number;
  onTime: (time: number) => void;
}

/**
 * Ata una línea de tiempo al scroll con tope de velocidad. El scroll solo fija a dónde hay que llegar;
 * la animación va hacia allá sin pasar de `maxRate` unidades por segundo. Así un scroll brusco no
 * reproduce todo el recorrido en un instante.
 *
 * Además funciona como imán: nunca deja al usuario detenido en una escena de relleno. Y ofrece `goTo`
 * para que los botones lleven a una parada exacta.
 */
export function followScroll(tl: gsap.core.Timeline, trigger: Element, { maxRate, rests = [], lenis, startAt, onTime }: FollowOptions) {
  tl.pause();
  const total = tl.duration();
  let target = 0;
  let direction = 1;
  let lastScrollAt = 0;
  let lastInputAt = 0;
  let lastGestureAt = -Infinity;
  let touching = false;
  let auto = false; // el scroll lo está moviendo goTo, no el usuario
  let jump = false; // el último movimiento del scroll fue un salto (barra, Inicio/Fin), no un gesto

  const st = ScrollTrigger.create({
    trigger,
    start: "top top",
    end: "bottom bottom",
    onUpdate: (self) => {
      target = self.progress;
      direction = self.direction;
      lastScrollAt = performance.now();
      jump = !auto && lastScrollAt - lastGestureAt > GESTURE_MS;
    },
  });

  const goTo = (time: number, onArrive?: () => void) => {
    const y = st.start + (Math.max(0, Math.min(total, time)) / total) * (st.end - st.start);
    const engine = lenis?.();
    if (!engine) {
      window.scrollTo(0, y);
      onArrive?.();
      return;
    }
    // Se viaja a la velocidad tope: la animación llega a la vez que el scroll, sin quedarse atrás.
    const units = Math.abs(time - target * total);
    auto = true;
    engine.scrollTo(y, {
      duration: Math.max(0.5, Math.min(6, units / maxRate)),
      easing: easeInOut,
      onComplete: () => {
        auto = false;
        onArrive?.();
      },
    });
  };

  // Cualquier entrada del usuario cancela el viaje automático y reinicia la espera del imán.
  const onInput = () => {
    lastInputAt = performance.now();
    auto = false;
  };
  const onGesture = () => {
    lastGestureAt = performance.now();
    onInput();
  };
  const onTouchStart = () => {
    touching = true;
    onGesture();
  };
  const onTouchEnd = () => {
    touching = false;
    onGesture();
  };
  window.addEventListener("wheel", onGesture, { passive: true });
  window.addEventListener("touchmove", onGesture, { passive: true });
  window.addEventListener("keydown", onInput);
  window.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("touchend", onTouchEnd, { passive: true });
  window.addEventListener("touchcancel", onTouchEnd, { passive: true });

  // Al cargar (o recargar a mitad de página) la animación arranca ya en su sitio, sin recorrerlo todo.
  target = st.progress;
  tl.progress(startAt === undefined ? target : startAt / total);
  onTime(tl.time());

  let last = performance.now();
  const tick = () => {
    const now = performance.now();
    const deltaMs = Math.min(now - last, 64);
    last = now;
    const current = tl.progress();
    if (current !== target) {
      const gap = Math.abs(target - current) * total;
      tl.progress(stepToward(current, target, deltaMs, total, rateFor(gap, maxRate, jump)));
      onTime(tl.time());
    }
    // Imán: si el usuario soltó el scroll en plena transición, se termina de llegar a una parada.
    if (!auto && !touching && now - lastScrollAt > IDLE_MS && now - lastInputAt > IDLE_MS) {
      const rest = restTarget(target * total, direction, rests);
      if (rest !== null) goTo(rest);
    }
  };
  gsap.ticker.add(tick);

  // Solo en desarrollo: las pruebas de scroll (e2e/scroll-stress.mjs) leen de aquí el estado real de la animación.
  if (import.meta.env.DEV) {
    Object.assign(window, {
      __journey: {
        time: () => tl.time(),
        total,
        target: () => target * total,
        maxRate,
        rests,
        triggers: () => ScrollTrigger.getAll().length,
      },
    });
  }
  return {
    goTo,
    dispose: () => {
      gsap.ticker.remove(tick);
      st.kill();
      window.removeEventListener("wheel", onGesture);
      window.removeEventListener("touchmove", onGesture);
      window.removeEventListener("keydown", onInput);
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("touchcancel", onTouchEnd);
    },
  };
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
