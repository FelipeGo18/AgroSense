import "@testing-library/jest-dom/vitest";

// jsdom no trae `matchMedia` y ScrollTrigger lo usa al registrarse. Por defecto ninguna consulta se cumple;
// la prueba que necesite otra cosa (por ejemplo «reducir movimiento») lo cambia con `vi.stubGlobal`.
if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
