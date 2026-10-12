/** Rutas de la web, en un solo lugar. Los enlaces se arman con esto, nunca con texto suelto. */
export const PATHS = {
  home: "/",
  consult: "/consultar",
  farm: "/mi-finca",
  howItWorks: "/como-funciona",
  login: "/entrar",
  signup: "/crear-cuenta",
  account: "/mi-cuenta",
  password: "/mi-cuenta/contrasena",
  activity: "/mi-cuenta/actividad",
  dataPolicy: "/politica-de-datos",
  // Páginas de prueba de la fase 0: no se enlazan desde la app; se entra escribiendo la dirección.
  lab: "/pruebas",
  kit: "/kit",
  journey: (n: 1 | 2 | 3) => `/recorrido/${n}` as const,
} as const;
