import type { ActivityItem } from "@/features/auth/session";

/**
 * Cómo se le cuenta a la persona cada evento de «Mi actividad» (specs/02-contratos.md, «Trazabilidad»).
 * La API manda el nombre técnico de la acción; aquí se pasa a palabras. Nunca hay valores: solo qué campos cambiaron.
 */

export type Outcome = "ok" | "denied" | "failed";

export const OUTCOME_LABEL: Record<Outcome, string> = { ok: "Hecho", denied: "Rechazado", failed: "Falló" };

/** Qué pasó, por acción. Lo que no esté aquí (acciones que lleguen después) se muestra con un texto general. */
const ACTIONS: Record<string, string> = {
  "auth.registered": "Creó su cuenta",
  "consent.accepted": "Aceptó el tratamiento de datos",
  "auth.login": "Entró a su cuenta",
  "auth.logout": "Cerró sesión",
  "auth.login_failed": "Intento de entrar a su cuenta",
  "auth.password_changed": "Cambió su contraseña",
  "profile.updated": "Editó sus datos",
  "lot.created": "Agregó un lote",
  "lot.updated": "Editó un lote",
  "lot.deleted": "Borró un lote",
  "lot.restored": "Restauró un lote",
  "season.created": "Registró una siembra",
  "season.updated": "Editó una siembra",
  "season.deleted": "Borró una siembra",
  "season.restored": "Restauró una siembra",
  "ticket.opened": "Reportó un problema",
  "admin.user_viewed": "Vio su cuenta para resolver un reporte",
  "admin.lot_deleted": "Borró uno de sus lotes para resolver un reporte",
  "admin.lot_restored": "Restauró uno de sus lotes",
  "admin.season_deleted": "Borró una de sus siembras para resolver un reporte",
  "admin.season_restored": "Restauró una de sus siembras",
  "admin.ticket_updated": "Actualizó uno de sus reportes",
  "admin.user_blocked": "Bloqueó su cuenta",
  "admin.user_unblocked": "Desbloqueó su cuenta",
};

/** Lo que no salió bien se dice distinto: «Cambió su contraseña» que falló es «Intentó cambiar la contraseña». */
const ATTEMPTS: Record<string, string> = {
  "auth.password_changed": "Intentó cambiar la contraseña",
};

const FIELDS: Record<string, string> = {
  display_name: "nombre",
  username: "usuario",
  priorities: "prioridades",
  name: "nombre",
  geometry: "contorno en el mapa",
  area_ha: "área",
  irrigated: "riego",
  municipality_id: "municipio",
  crop_id: "cultivo",
  sowing_date: "fecha de siembra",
  harvest_date: "fecha de cosecha",
};

export function describe(item: ActivityItem): { what: string; detail: string | null } {
  const outcome = item.outcome as Outcome;
  const what = (outcome !== "ok" && ATTEMPTS[item.action]) || ACTIONS[item.action] || "Hubo actividad en su cuenta";
  const fields = (item.details as { fields?: string[] } | null)?.fields ?? [];
  let detail: string | null = fields.length ? `Cambió: ${fields.map((field) => FIELDS[field] ?? field).join(", ")}` : null;
  if (item.action === "auth.login_failed") {
    detail = outcome === "denied" ? "Se rechazó: demasiados intentos o cuenta bloqueada" : "La contraseña no era correcta";
  } else if (item.action === "auth.password_changed" && outcome !== "ok") {
    detail = outcome === "denied" ? "Demasiados intentos fallidos" : "La contraseña actual no era correcta";
  }
  return { what, detail };
}

/** Quién lo hizo. Al agricultor nunca se le dice quién es la persona de soporte: solo que fue soporte. */
export const who = (item: ActivityItem) => (item.actor_role === "admin" || item.actor_role === "developer" ? "Soporte" : "Usted");

const PARTS = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric" });

/** «9 oct», o «9 oct 2025» si no es de este año. */
function shortDay(at: Date, withYear: boolean): string {
  const parts = Object.fromEntries(PARTS.formatToParts(at).map((part) => [part.type, part.value]));
  const day = `${parts.day} ${parts.month.replace(".", "")}`;
  return withYear ? `${day} ${parts.year}` : day;
}

const HOUR = new Intl.DateTimeFormat("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false });

/** «Hoy, 10:42», «Ayer, 17:50» o «9 oct, 16:20»; con el año si no es de este. */
export function when(iso: string, now: Date = new Date()): string {
  const at = new Date(iso);
  const days = Math.round((new Date(now).setHours(0, 0, 0, 0) - new Date(at).setHours(0, 0, 0, 0)) / 86_400_000);
  const day = days === 0 ? "Hoy" : days === 1 ? "Ayer" : shortDay(at, at.getFullYear() !== now.getFullYear());
  return `${day}, ${HOUR.format(at)}`;
}

/** Los eventos se conservan 180 días: lo anterior a esta fecha ya se borró. */
export function keptSince(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(now.getTime() - 180 * 86_400_000),
  );
}
