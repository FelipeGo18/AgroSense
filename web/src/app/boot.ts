// Los estilos van aquí, y no en main.tsx, para que salgan como hoja de estilos en el HTML: el contenido que ya viene
// dibujado desde el build (scripts/prerender.mjs) se pinta con ellos antes de que corra la aplicación.
import "@fontsource/fredoka/600.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "@/styles/index.css";
import { initLightMode } from "@/lib/lightMode";

// El modo ligero se fija antes de pintar: así nada se anima si la persona pidió quietud.
initLightMode();

/**
 * Arranque. Si la página ya viene dibujada, primero se deja que el navegador la pinte y después se trae y se corre
 * la aplicación: en un teléfono lento, lo que la persona vino a ver no espera al JavaScript ni comparte con él la
 * conexión. Lo que se escriba en un campo antes de que arranque la aplicación no se pierde (lib/firstLoad.ts, `rememberTyped`).
 */
const start = () => void import("./main");

/** Corre `run` cuando el navegador ya pintó el contenido; de inmediato si no hay cómo saberlo o la pestaña no se ve. */
function afterFirstPaint(run: () => void) {
  let done = false;
  const go = () => {
    if (done) return;
    done = true;
    run();
  };
  if (document.visibilityState === "hidden" || typeof PerformanceObserver === "undefined") return go();
  try {
    new PerformanceObserver((list, observer) => {
      if (list.getEntriesByName("first-contentful-paint").length === 0) return;
      observer.disconnect();
      go();
    }).observe({ type: "paint", buffered: true });
  } catch {
    return go();
  }
  setTimeout(go, 2500); // por si el aviso del pintado nunca llega
}

if (document.getElementById("root")?.dataset.prerendered) afterFirstPaint(start);
else start();
