import { useCallback, useSyncExternalStore } from "react";

/** Verdadero mientras la pantalla cumple la consulta de medios. Sin `matchMedia` (pruebas), falso. */
export function useMediaQuery(query: string) {
  const subscribe = useCallback(
    (onChange: () => void) => {
      if (typeof matchMedia !== "function") return () => {};
      const mq = matchMedia(query);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    [query],
  );
  return useSyncExternalStore(
    subscribe,
    () => typeof matchMedia === "function" && matchMedia(query).matches,
    () => false,
  );
}
