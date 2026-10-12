import { useSyncExternalStore } from "react";
import { lightModeEnabled, setLightMode, subscribeLightMode } from "@/lib/lightMode";
import { useMediaQuery } from "./useMediaQuery";

/** Si el modo ligero está prendido en este dispositivo, y cómo cambiarlo (lib/lightMode.ts). */
export function useLightMode() {
  const enabled = useSyncExternalStore(subscribeLightMode, lightModeEnabled, () => false);
  return [enabled, setLightMode] as const;
}

/**
 * Verdadero si no debe haber movimiento: porque el sistema pide reducirlo o porque la persona prendió el modo ligero.
 * Entonces nada viaja ni gira, no hay scroll suave y todo aparece ya colocado.
 */
export function useReducedMotion() {
  const system = useMediaQuery("(prefers-reduced-motion: reduce)");
  const [light] = useLightMode();
  return system || light;
}
