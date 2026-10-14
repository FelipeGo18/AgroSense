import { useSyncExternalStore } from "react";
import { dayPhase, type DayPhase } from "@/lib/dayPhase";

const now = () => dayPhase(new Date().getHours());
const everyMinute = (onChange: () => void) => {
  const timer = setInterval(onChange, 60_000);
  return () => clearInterval(timer);
};

/**
 * El momento del día según el reloj de este dispositivo; se revisa cada minuto (lib/dayPhase.ts).
 * En el HTML que se genera en el build siempre es «día»: la hora de quien mira se sabe al arrancar en su navegador.
 */
export function useDayPhase(): DayPhase {
  return useSyncExternalStore(everyMinute, now, () => "day");
}
