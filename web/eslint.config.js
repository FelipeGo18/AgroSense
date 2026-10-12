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
    files: ["**/*.test.{ts,tsx}", "src/test-setup.ts"],
    languageOptions: { globals: { ...globals.vitest } },
  },
  {
    // Pruebas de navegador: el guion corre en Node y parte de su código se ejecuta dentro de la página.
    files: ["e2e/**/*.mjs"],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
  // Prettier decide el formato: se apagan las reglas de estilo que chocarían con él.
  prettier,
);
