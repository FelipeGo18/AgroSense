import { HttpResponse, delay, http, type HttpHandler } from "msw";
import examples from "./examples.json";

/**
 * Respuestas simuladas de la API (HU-013). Salen de `examples.json`, que se genera con `npm run api:examples` a partir
 * del OpenAPI: nada se escribe aquí a mano. Las de cálculo son de ejemplo (`versions.dataset = "ejemplo"`, R5).
 *
 * Responden los endpoints de cálculo, el suelo del municipio, los catálogos y las versiones. Las cuentas, los lotes y
 * las temporadas siguen yendo a la API real: simularlas es HU-014 (P1).
 *
 * Cada estado se fuerza con `?estado=` en la dirección de la página (o de la petición), por ejemplo
 * `/consultar?estado=no_apto`. Ver `SIMULATION_STATES`.
 */

type Route = { ok: Record<string, unknown>; errors: Record<string, unknown> };
const ROUTES = examples.routes as Record<string, Route>;

/** El nombre del estado en el contrato, para quien lo busque así (`?estado=insufficient_data`). */
const ALIASES: Record<string, string> = {
  not_suitable: "no_apto",
  insufficient_data: "sin_agua",
  not_evaluable: "sin_agua",
  not_applicable: "no_aplica",
};

/** Los errores, por su `code` del contrato además de su número (`?estado=dataset_unavailable` o `?estado=503`). */
const ERROR_CODES: Record<string, string> = {
  unauthorized: "401",
  not_found: "404",
  invalid_input: "422",
  not_implemented: "501",
  dataset_unavailable: "503",
};

/** Estados que valen para cualquier ruta simulada. */
const NETWORK_STATES = {
  cargando: "La respuesta nunca llega: la pantalla se queda cargando",
  sin_conexion: "Falla la red, como sin conexión",
} as const;

/** Todo lo que se puede pedir con `?estado=`, por ruta, para la documentación y las pruebas. */
export const SIMULATION_STATES: Record<string, string[]> = {
  ...Object.fromEntries(
    Object.entries(ROUTES).map(([route, { ok, errors }]) => [
      route,
      [
        ...Object.keys(ok),
        ...Object.keys(errors).flatMap((status) => [status, ...Object.keys(ERROR_CODES).filter((code) => ERROR_CODES[code] === status)]),
      ],
    ]),
  ),
  todas: Object.keys(NETWORK_STATES),
};

/** El estado pedido: primero el de la petición (pruebas), después el de la página abierta (desarrollo). */
function requestedState(request: Request): string | null {
  const fromRequest = new URL(request.url).searchParams.get("estado");
  if (fromRequest) return fromRequest;
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("estado");
}

function warnUnknown(route: string, state: string) {
  console.warn(
    `[simulación] ${route} no tiene el estado «${state}»; responde el de siempre. Estados: ${SIMULATION_STATES[route]?.join(", ")}`,
  );
}

function respond(route: string, { ok, errors }: Route): Parameters<typeof http.get>[1] {
  const [first] = Object.keys(ok);
  return async ({ request }) => {
    const raw = requestedState(request);
    const state = raw ? (ALIASES[raw] ?? raw) : null;

    if (state === "cargando") {
      await delay("infinite");
    }
    if (state === "sin_conexion") return HttpResponse.error();

    // Una espera corta y variable, como la de una red real: deja ver los estados de carga.
    await delay();

    const status = state ? (ERROR_CODES[state] ?? state) : null;
    if (status && errors[status]) return HttpResponse.json(errors[status] as object, { status: Number(status) });
    if (state && ok[state]) return HttpResponse.json(ok[state] as object);
    if (state) warnUnknown(route, raw!);
    return HttpResponse.json(ok[first] as object);
  };
}

const methods = { GET: http.get, POST: http.post } as const;

/** `GET /catalogs/municipalities/{municipality_id}/soil` → `/api/v1/catalogs/municipalities/:municipality_id/soil`. */
const toPath = (path: string) => `/api/v1${path.replace(/\{(\w+)\}/g, ":$1")}`;

const routeHandlers = Object.entries(ROUTES).map(([route, value]) => {
  const [method, path] = route.split(" ") as [keyof typeof methods, string];
  return methods[method](toPath(path), respond(route, value));
});

const { municipalities, crops, version } = examples.catalogs;

/** Los catálogos y las versiones son los del dataset publicado: responden igual que la API, sin estados. */
const catalogHandlers = [
  http.get("/api/v1/catalogs/municipalities", async () => {
    await delay();
    return HttpResponse.json(municipalities);
  }),
  http.get("/api/v1/catalogs/crops", async () => {
    await delay();
    return HttpResponse.json(crops);
  }),
  http.get("/api/v1/version", async () => {
    await delay();
    return HttpResponse.json(version);
  }),
];

export const handlers: HttpHandler[] = [...routeHandlers, ...catalogHandlers];
