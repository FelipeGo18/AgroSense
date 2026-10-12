/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },
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
