/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { msw } from "msw/vite";

export default defineConfig(({ command }) => ({
  // MSW (HU-013) sirve su worker solo en desarrollo: el build nunca lo trae, así no hay simulación en producción.
  plugins: [react(), tailwindcss(), ...(command === "serve" ? [msw({ mode: "worker-only" })] : [])],
  resolve: { alias: { "@": "/src" } },
  // Para generar el HTML de las páginas públicas en el build (scripts/prerender.mjs): estas librerías se empaquetan,
  // porque Node no las carga bien sueltas.
  ssr: { noExternal: ["gsap", "@gsap/react", "lenis"] },
  // El manifiesto dice qué archivos necesita cada página: con él se piden por adelantado en el HTML.
  build: { manifest: true },
  // El worker de MapLibre es un módulo (import/export): se empaqueta como módulo.
  worker: { format: "es" },
  // Los tokens viven en design/tokens, fuera de web/ (HU-152).
  server: {
    fs: { allow: [".."] },
    // La API corre aparte en desarrollo (docker compose up app). Con este puente la web y la API comparten origen,
    // como en la demo: la cookie de sesión viaja sin CORS. `API_PROXY` la cambia si la API está en otro puerto.
    proxy: { "/api": process.env.API_PROXY ?? "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // Muchas pruebas recorren páginas que se cargan aparte (la primera de cada archivo, en frío): solas tardan de 2 a 3 s
    // y con todos los archivos en paralelo pasaban del límite de 5 s de Vitest y fallaban sin que nada estuviera mal.
    // 15 s deja margen para una máquina ocupada; una prueba que de verdad se cuelga sigue fallando.
    testTimeout: 15_000,
  },
}));
