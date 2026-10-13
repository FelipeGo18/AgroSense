import { useSyncExternalStore } from "react";
import { lightModeOn, lightModePref, resetLightMode, setLightMode, subscribeLightMode } from "@/lib/lightMode";

/** Si la web está en modo ligero y cómo cambiarlo. Todos los controles y pantallas ven el mismo valor. */
export function useLightMode() {
  const light = useSyncExternalStore(subscribeLightMode, lightModeOn, () => false);
  const pref = useSyncExternalStore(subscribeLightMode, lightModePref, () => "auto" as const);
  return { light, pref, setLight: setLightMode, reset: resetLightMode };
}

/**
 * Verdadero si se puede usar movimiento (GSAP, scroll suave, animaciones). Todo componente animado lo consulta y, si es
 * falso, se dibuja ya colocado y quieto con la misma información. Es lo contrario del modo ligero.
 */
export function useAnimated() {
  return !useLightMode().light;
}
