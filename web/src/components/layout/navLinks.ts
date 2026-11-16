import { PATHS } from "@/app/paths";

/**
 * Enlaces de la barra y del menú: los de todos, los de quien entró y los de quien no. `wide`: en la barra solo cabe
 * desde 1280 px (a 1024 px, cuatro enlaces no entran junto al logo y los botones); siempre está en el menú del celular
 * y en el pie de página.
 */
export const NAV: { to: string; label: string; wide?: true }[] = [
  { to: PATHS.consult, label: "nav.consult" },
  { to: PATHS.farm, label: "nav.farm" },
  { to: PATHS.prices, label: "nav.prices", wide: true },
  { to: PATHS.howItWorks, label: "nav.how" },
];

export const MEMBER = [
  { to: PATHS.account, label: "nav.account" },
  { to: PATHS.activity, label: "nav.activity" },
];

export const GUEST = [
  { to: PATHS.login, label: "nav.login" },
  { to: PATHS.signup, label: "nav.signup" },
];
