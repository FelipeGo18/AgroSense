import { useSyncExternalStore } from "react";
import { lightModeOn, lightModePref, resetLightMode, setLightMode, subscribeLightMode } from "@/lib/lightMode";
import { motionLoaded, subscribeMotion } from "@/lib/motion";

/** Si la web está en modo ligero y cómo cambiarlo. Todos los controles y pantallas ven el mismo valor. */
export function useLightMode() {
  const light = useSyncExternalStore(subscribeLightMode, lightModeOn, () => false);
  const pref = useSyncExternalStore(subscribeLightMode, lightModePref, () => "auto" as const);
  return { light, pref, setLight: setLightMode, reset: resetLightMode };
}

/**
 * Verdadero si se puede usar movimiento (GSAP, scroll suave, animaciones). Todo componente animado lo consulta y, si es
 * falso, se dibuja ya colocado y quieto con la misma información. Es lo contrario del modo ligero, y además espera a que
 * llegue el motor del movimiento (`lib/motion.ts`), que se carga aparte: donde es verdadero, `gsap` ya existe.
 * Excepción: el build supone movimiento, y el primer dibujo sobre su HTML (Inicio, Entrar, la política) también, aunque
 * la persona esté en modo ligero y el motor no venga. Un efecto que use `gsap` o `Lenis` fuera de `useMotionEffect`
 * pregunta además `motionLoaded()`.
 */
export function useAnimated() {
  const loaded = useSyncExternalStore(subscribeMotion, motionLoaded, () => true);
  return !useLightMode().light && loaded;
}
