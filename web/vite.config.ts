/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },
  // Para generar el HTML de las páginas públicas en el build (scripts/prerender.mjs): estas librerías se empaquetan,
  // porque Node no las carga bien sueltas.
  ssr: { noExternal: ["gsap", "@gsap/react", "lenis"] },
  // El manifiesto dice qué archivos necesita cada página: con él se piden por adelantado en el HTML.
  build: { manifest: true },
  // Los tokens viven en design/tokens, fuera de web/ (HU-152).
  server: {
    fs: { allow: [".."] },
    // La API corre aparte en desarrollo (docker compose up app). Con este puente la web y la API comparten origen,
    // como en la demo: la cookie de sesión viaja sin CORS.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
