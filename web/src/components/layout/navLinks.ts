import { PATHS } from "@/app/paths";

/** Enlaces de la barra y del menú: los de todos, los de quien entró y los de quien no. */
export const NAV = [
  { to: PATHS.consult, label: "Consultar" },
  { to: PATHS.farm, label: "Mi finca" },
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
