import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// Cada página se carga aparte: la primera prueba de un archivo la trae por primera vez y eso puede pasar de un segundo.
configure({ asyncUtilTimeout: 5000 });
import { afterEach } from "vitest";
import { resetLightMode } from "@/lib/lightMode";
import { loadMotion } from "@/lib/motion";

// jsdom no trae `matchMedia` y ScrollTrigger lo usa al registrarse. Por defecto las pruebas corren como en un equipo
// que pide «reducir movimiento»: sin animaciones, lo que se busca en pantalla está ahí de inmediato. La prueba que
// necesite otra cosa (movimiento, pantalla angosta) lo cambia con `vi.stubGlobal`.
if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string) =>
    ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

// jsdom no trae `ResizeObserver`, que usan los avisos de Radix (tooltip del botón «Modo ligero»).
if (typeof window.ResizeObserver !== "function") {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

// El modo ligero se guarda en el navegador: cada prueba arranca otra vez en automático, sin la preferencia de la anterior.
afterEach(() => resetLightMode());

// El motor del movimiento (GSAP y Lenis) se carga aparte en la web (lib/motion.ts). En las pruebas se trae de una vez,
// así una prueba con movimiento lo encuentra listo, como una página que ya lo esperó al cargarse. Va al final: ScrollTrigger
// usa `matchMedia` al registrarse.
await loadMotion();
