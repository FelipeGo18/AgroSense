import { useSyncExternalStore } from "react";
import { setSoundEnabled, soundEnabled, subscribeSound } from "@/lib/sound";

/** Si el sonido está prendido y cómo cambiarlo. Todos los controles de la página ven el mismo valor. */
export function useSound() {
  const enabled = useSyncExternalStore(subscribeSound, soundEnabled, () => false);
  return [enabled, setSoundEnabled] as const;
}
