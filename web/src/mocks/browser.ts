import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

/**
 * Arranca las respuestas simuladas en el navegador (HU-013). Solo con `VITE_SIMULATION=true` y en `npm run dev`:
 * `app/boot.ts` lo importa detrás de esa variable y el build no lo incluye. El worker lo sirve el plugin de MSW en
 * `vite.config.ts`.
 *
 * Lo que no está simulado (cuentas, lotes, temporadas) pasa a la API real sin aviso.
 */
export async function startSimulation() {
  await setupWorker(...handlers).start({ onUnhandledFrame: "bypass", quiet: true });
}
