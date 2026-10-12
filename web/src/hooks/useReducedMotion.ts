import { useMediaQuery } from "./useMediaQuery";

/** Verdadero si el sistema pide reducir movimiento: entonces nada viaja ni gira; todo aparece ya colocado. */
export function useReducedMotion() {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}
