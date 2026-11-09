/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SOCIAL_GITHUB?: string;
  readonly VITE_SOCIAL_INSTAGRAM?: string;
  readonly VITE_SOCIAL_LINKEDIN?: string;
  readonly VITE_SOCIAL_YOUTUBE?: string;
  readonly VITE_MUSIC_URL?: string;
  /** `true` en `npm run dev`: la web responde con los ejemplos de `src/mocks` (HU-013). */
  readonly VITE_SIMULATION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
