import type { components } from "./schema";

/** Tipos del contrato, generados del OpenAPI de la API (`npm run api:types`). No se escriben a mano. */
export type Schemas = components["schemas"];

/** Un error que la API explicó: `{"error": {"code", "message", "request_id"}}` (specs/02-contratos.md). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** Código para soporte: con él se rastrea la petición en los logs. */
  readonly requestId: string;

  constructor(status: number, code: string, message: string, requestId: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

const OFFLINE = "No pudimos conectarnos. Revise su conexión e intente de nuevo.";

/**
 * Llama a la API. La web y la API comparten origen, así que la cookie de sesión viaja sola: aquí nunca se lee
 * ni se guarda un token. Responde el JSON, o nada si la respuesta viene vacía (204).
 */
export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: options.method ?? (options.body === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(0, "offline", OFFLINE, "");
  }
  if (response.ok) return (response.status === 204 ? undefined : await response.json()) as T;
  const requestId = response.headers.get("X-Request-ID") ?? "";
  const payload: unknown = await response.json().catch(() => null);
  const error = (payload as { error?: { code?: string; message?: string } } | null)?.error;
  throw new ApiError(response.status, error?.code ?? "error", error?.message ?? OFFLINE, requestId);
}
