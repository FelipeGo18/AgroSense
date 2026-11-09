/** Rutas de la web, en un solo lugar. Los enlaces se arman con esto, nunca con texto suelto. */
export const PATHS = {
  home: "/",
  consult: "/consultar",
  farm: "/mi-finca",
  addLot: "/mi-finca/agregar",
  lot: (lotId: string) => `/mi-finca/lotes/${lotId}` as const,
  editLot: (lotId: string) => `/mi-finca/lotes/${lotId}/editar` as const,
  /** Editar lote con el mapa listo para dibujar: desde «Dibujar en el mapa» de un lote sin dibujar. */
  drawLot: (lotId: string) => `/mi-finca/lotes/${lotId}/editar?dibujar` as const,
  /** Registrar una siembra; con `after`, viene de registrar esa cosecha y la marca como «lo que había antes». */
  sow: (lotId: string, after?: string) => (after ? `/mi-finca/lotes/${lotId}/sembrar?despues=${after}` : `/mi-finca/lotes/${lotId}/sembrar`),
  harvest: (lotId: string, seasonId: string) => `/mi-finca/lotes/${lotId}/siembras/${seasonId}/cosechar` as const,
  editSeason: (lotId: string, seasonId: string) => `/mi-finca/lotes/${lotId}/siembras/${seasonId}/editar` as const,
  howItWorks: "/como-funciona",
  login: "/entrar",
  signup: "/crear-cuenta",
  account: "/mi-cuenta",
  password: "/mi-cuenta/contrasena",
  activity: "/mi-cuenta/actividad",
  dataPolicy: "/politica-de-datos",
  prices: "/precios",
  // Páginas de prueba de la fase 0: no se enlazan desde la app; se entra escribiendo la dirección.
  lab: "/pruebas",
  kit: "/kit",
  journey: (n: 1 | 2 | 3) => `/recorrido/${n}` as const,
} as const;
