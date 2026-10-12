import { useSyncExternalStore } from "react";
import { motionReduced, setMotionReduced, subscribeMotion } from "@/lib/motion";
import { useMediaQuery } from "./useMediaQuery";

/**
 * Verdadero si hay que reducir movimiento: porque lo pide el sistema o porque la persona lo eligió en Mi cuenta.
 * Entonces nada viaja ni gira; todo aparece ya colocado.
 */
export function useReducedMotion() {
  const system = useMediaQuery("(prefers-reduced-motion: reduce)");
  const chosen = useSyncExternalStore(subscribeMotion, motionReduced, () => false);
  return system || chosen;
}

/** Para el control de la preferencia: qué pide el sistema, qué eligió la persona y cómo cambiarlo. */
export function useMotionPreference() {
  const system = useMediaQuery("(prefers-reduced-motion: reduce)");
  const chosen = useSyncExternalStore(subscribeMotion, motionReduced, () => false);
  return { system, chosen, setChosen: setMotionReduced };
}
