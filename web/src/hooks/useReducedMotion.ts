import { useLightMode as useLightModeState, useAnimated } from "./useLightMode";

/** Si el modo ligero está prendido en este dispositivo, y cómo cambiarlo (lib/lightMode.ts). */
export function useLightMode() {
  const { light, setLight } = useLightModeState();
  return [light, setLight] as const;
}

/**
 * Verdadero si no debe haber movimiento: porque el equipo pide reducirlo, hay ahorro de datos o la persona prendió el
 * modo ligero. Es lo contrario de `useAnimated()`; las piezas nuevas usan ese.
 */
export function useReducedMotion() {
  return !useAnimated();
}
