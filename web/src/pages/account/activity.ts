import { t, locale } from "@/lib/i18n";
import type { ActivityItem } from "@/features/auth/session";

/**
 * Cómo se le cuenta a la persona cada evento de «Mi actividad» (specs/02-contratos.md, «Trazabilidad»).
 * La API manda el nombre técnico de la acción; aquí se pasa a palabras. Nunca hay valores: solo qué campos cambiaron.
 */

export type Outcome = "ok" | "denied" | "failed";

export const OUTCOME_LABEL = (): Record<Outcome, string> => ({
  ok: t("pages.account.activity.done"),
  denied: t("pages.account.activity.denied"),
  failed: t("pages.account.activity.failed"),
});

/** Qué pasó, por acción. Lo que no esté aquí (acciones que lleguen después) se muestra con un texto general. */
const ACTIONS = (): Record<string, string> => ({
  "auth.registered": t("pages.account.activity.createdYourAccount"),
  "consent.accepted": t("pages.account.activity.agreedToDataProcessing"),
  "auth.login": t("pages.account.activity.signedInToYourAccount"),
  "auth.logout": t("pages.account.activity.signedOut"),
  "auth.login_failed": t("pages.account.activity.attemptedToSignInToYourAccount"),
  "auth.password_changed": t("pages.account.activity.changedYourPassword"),
  "profile.updated": t("pages.account.activity.editedYourDetails"),
  "lot.created": t("pages.account.activity.addedAPlot"),
  "lot.updated": t("pages.account.activity.editedAPlot"),
  "lot.deleted": t("pages.account.activity.deletedAPlot"),
  "lot.restored": t("pages.account.activity.restoredAPlot"),
  "season.created": t("pages.account.activity.recordedAPlanting"),
  "season.updated": t("pages.account.activity.editedAPlanting"),
  "season.deleted": t("pages.account.activity.deletedAPlanting"),
  "season.restored": t("pages.account.activity.restoredAPlanting"),
  "ticket.opened": t("pages.account.activity.reportedAProblem"),
  "admin.user_viewed": t("pages.account.activity.viewedYourAccountToResolveAReport"),
  "admin.lot_deleted": t("pages.account.activity.deletedOneOfYourPlotsToResolve"),
  "admin.lot_restored": t("pages.account.activity.restoredOneOfYourPlots"),
  "admin.season_deleted": t("pages.account.activity.deletedOneOfYourPlantingsToResolve"),
  "admin.season_restored": t("pages.account.activity.restoredOneOfYourPlantings"),
  "admin.ticket_updated": t("pages.account.activity.updatedOneOfYourReports"),
  "admin.user_blocked": t("pages.account.activity.blockedYourAccount"),
  "admin.user_unblocked": t("pages.account.activity.unblockedYourAccount"),
});

/** Lo que no salió bien se dice distinto: «Cambió su contraseña» que falló es «Intentó cambiar la contraseña». */
const ATTEMPTS = (): Record<string, string> => ({
  "auth.password_changed": t("pages.account.activity.attemptedToChangeThePassword"),
});

const FIELDS = (): Record<string, string> => ({
  display_name: t("pages.account.activity.name"),
  username: t("pages.account.activity.username"),
  priorities: t("pages.account.activity.priorities"),
  name: t("pages.account.activity.name"),
  geometry: t("pages.account.activity.mapBoundary"),
  area_ha: t("pages.account.activity.area"),
  irrigated: t("activity.field.irrigation"),
  municipality_id: t("activity.field.municipality"),
  crop_id: t("activity.field.crop"),
  sowing_date: t("pages.account.activity.plantingDate"),
  harvest_date: t("pages.account.activity.harvestDate"),
});

export function describe(item: ActivityItem): { what: string; detail: string | null } {
  const outcome = item.outcome as Outcome;
  const what =
    (outcome !== "ok" && ATTEMPTS()[item.action]) || ACTIONS()[item.action] || t("pages.account.activity.thereWasActivityOnYourAccount");
  const fields = (item.details as { fields?: string[] } | null)?.fields ?? [];
  let detail: string | null = fields.length
    ? t("pages.account.activity.changed", { v0: fields.map((field) => FIELDS()[field] ?? field).join(", ") })
    : null;
  if (item.action === "auth.login_failed") {
    detail =
      outcome === "denied"
        ? t("pages.account.activity.deniedTooManyAttemptsOrAccountBlocked")
        : t("pages.account.activity.thePasswordWasIncorrect");
  } else if (item.action === "auth.password_changed" && outcome !== "ok") {
    detail =
      outcome === "denied" ? t("pages.account.activity.tooManyFailedAttempts") : t("pages.account.activity.theCurrentPasswordWasIncorrect");
  }
  return { what, detail };
}

/** Quién lo hizo. Al agricultor nunca se le dice quién es la persona de soporte: solo que fue soporte. */
export const who = (item: ActivityItem) =>
  item.actor_role === "admin" || item.actor_role === "developer" ? t("pages.account.activity.support") : t("pages.account.activity.you");

const PARTS = () => new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: "numeric" });

/** «9 oct», o «9 oct 2025» si no es de este año. */
function shortDay(at: Date, withYear: boolean): string {
  const parts = Object.fromEntries(
    PARTS()
      .formatToParts(at)
      .map((part) => [part.type, part.value]),
  );
  const day = `${parts.day} ${parts.month.replace(".", "")}`;
  return withYear ? `${day} ${parts.year}` : day;
}

const HOUR = () => new Intl.DateTimeFormat(locale(), { hour: "2-digit", minute: "2-digit", hour12: false });

/** «Hoy, 10:42», «Ayer, 17:50» o «9 oct, 16:20»; con el año si no es de este. */
export function when(iso: string, now: Date = new Date()): string {
  const at = new Date(iso);
  const days = Math.round((new Date(now).setHours(0, 0, 0, 0) - new Date(at).setHours(0, 0, 0, 0)) / 86_400_000);
  const day =
    days === 0
      ? t("pages.account.activity.today")
      : days === 1
        ? t("pages.account.activity.yesterday")
        : shortDay(at, at.getFullYear() !== now.getFullYear());
  return `${day}, ${HOUR().format(at)}`;
}

/** Los eventos se conservan 180 días: lo anterior a esta fecha ya se borró. */
export function keptSince(now: Date = new Date()): string {
  return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(now.getTime() - 180 * 86_400_000),
  );
}
