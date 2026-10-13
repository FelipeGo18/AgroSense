import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { resetLightMode } from "@/lib/lightMode";

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
