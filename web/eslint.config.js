import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "e2e/results"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  reactHooks.configs.flat["recommended-latest"],
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
  },
  {
    // GSAP y Lenis se cargan aparte, solo con movimiento (HU-158): se usan desde `@/lib/motion` y `useMotionEffect`.
    // Un import directo los metería en el paquete de la página, también en modo ligero. El laboratorio (pruebas de la
    // fase 0) y su `followScroll` quedan fuera: se cargan aparte y solo por su dirección.
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/lib/motionEngine.ts", "src/lib/followScroll.ts", "src/pages/lab/**", "**/*.test.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "gsap",
              message: "Use `gsap` de `@/lib/motion`: GSAP se carga aparte, solo con movimiento (HU-158).",
              allowTypeImports: true,
            },
            {
              name: "lenis",
              message: "Use `Lenis` de `@/lib/motion`: se carga aparte, solo con movimiento (HU-158).",
              allowTypeImports: true,
            },
            { name: "@gsap/react", message: "Use `useMotionEffect` de `@/hooks/useMotionEffect` (HU-158)." },
          ],
          patterns: [
            {
              group: ["gsap/*"],
              message: "Use `@/lib/motion`: GSAP se carga aparte, solo con movimiento (HU-158).",
              allowTypeImports: true,
            },
          ],
        },
      ],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test-setup.ts"],
    languageOptions: { globals: { ...globals.vitest } },
  },
  {
    // Pruebas de navegador: el guion corre en Node y parte de su código se ejecuta dentro de la página.
    files: ["e2e/**/*.mjs", "scripts/**/*.mjs"],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
  // Prettier decide el formato: se apagan las reglas de estilo que chocarían con él.
  prettier,
);
