/**
 * El motor del movimiento (GSAP, ScrollTrigger y Lenis), cargado aparte (HU-158): en modo ligero no se descarga.
 *
 * `gsap`, `ScrollTrigger` y `Lenis` son enlaces vivos: no valen nada hasta que el motor llega.
 * - Los efectos con GSAP se escriben con `useMotionEffect` (`@/hooks/useMotionEffect`), que no corre sin el motor. No con
 *   `useGSAP`, que trae GSAP en el paquete inicial, ni importando `gsap` o `lenis` directo.
 * - Un efecto que los use por fuera de `useMotionEffect` (un `ticker`, Lenis) pregunta `motionLoaded()` además de
 *   `useAnimated()`. `useAnimated()` no se enciende hasta que el motor está, salvo en un caso: el primer dibujo sobre el
 *   HTML del build se hace como en el build, con movimiento, aunque la persona esté en modo ligero y el motor no venga.
 * - En un manejador de eventos, detrás de `useAnimated()` (ya pasó el primer dibujo) o de `motionLoaded()`.
 *
 * Con movimiento, el motor se pide al arrancar, en paralelo con la aplicación (`initMotion`), y cada página lo espera antes
 * de montarse (`motionReady`, en `app/routes.tsx`): así lo encuentra listo y su entrada no parpadea. Si la persona apaga
 * el modo ligero sin recargar, el motor se pide en ese momento y el movimiento empieza cuando llega.
 */
import type GsapCore from "gsap";
import type { ScrollTrigger as ScrollTriggerCore } from "gsap/ScrollTrigger";
import type LenisCore from "lenis";
import { lightModeOn, subscribeLightMode } from "./lightMode";

export let gsap = undefined as unknown as typeof GsapCore;
export let ScrollTrigger = undefined as unknown as typeof ScrollTriggerCore;
export let Lenis = undefined as unknown as typeof LenisCore;

let engine: Promise<void> | null = null;
let loaded = false;
const listeners = new Set<() => void>();

/** Trae el motor (una sola vez). Si falla (sin conexión), se puede volver a pedir: mientras tanto, la web sigue quieta. */
export function loadMotion(): Promise<void> {
  engine ??= import("./motionEngine").then(
    (core) => {
      gsap = core.gsap;
      ScrollTrigger = core.ScrollTrigger;
      Lenis = core.Lenis;
      loaded = true;
      listeners.forEach((listener) => listener());
    },
    (error: unknown) => {
      engine = null;
      throw error;
    },
  );
  return engine;
}

/** Verdadero cuando el motor ya llegó. */
export const motionLoaded = () => loaded;

export function subscribeMotion(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Lo que una página espera antes de montarse: nada en modo ligero (ni en el build); con movimiento, que llegue el motor. */
export function motionReady(): Promise<void> {
  if (typeof window === "undefined" || lightModeOn()) return Promise.resolve();
  return loadMotion().catch(() => {});
}

/** Pide el motor en cuanto hay movimiento: al arrancar y cada vez que se apaga el modo ligero. Se llama una vez. */
export function initMotion() {
  const wanted = () => {
    if (!lightModeOn()) void loadMotion().catch(() => {});
  };
  wanted();
  subscribeLightMode(wanted);
}
