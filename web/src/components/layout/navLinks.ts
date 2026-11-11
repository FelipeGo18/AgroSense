import { PATHS } from "@/app/paths";

/**
 * Enlaces de la barra y del menú: los de todos, los de quien entró y los de quien no. `wide`: en la barra solo cabe
 * desde 1280 px (a 1024 px, cuatro enlaces no entran junto al logo y los botones); siempre está en el menú del celular
 * y en el pie de página.
 */
export const NAV: { to: string; label: string; wide?: true }[] = [
  { to: PATHS.consult, label: "Consultar" },
  { to: PATHS.farm, label: "Mi finca" },
  { to: PATHS.prices, label: "Precios", wide: true },
  { to: PATHS.howItWorks, label: "Cómo funciona" },
];

export const MEMBER = [
  { to: PATHS.account, label: "Mi cuenta" },
  { to: PATHS.activity, label: "Mi actividad" },
];

export const GUEST = [
  { to: PATHS.login, label: "Entrar" },
  { to: PATHS.signup, label: "Crear cuenta" },
];
