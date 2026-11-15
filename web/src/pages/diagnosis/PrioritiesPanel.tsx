import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { SeedRow } from "@/components/ui/PriorityControl";
import {
  PRIORITIES_HINT,
  PRIORITY_CONTROLS,
  priorityNote,
  UNRATED_PRIORITIES_NOTE,
  type useSignalPriorities,
} from "@/features/diagnosis/priorities";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/**
 * «Criterio de AgroSense · Ajustar» (HU-202; `specs/05-frontend.md`, «Dónde se ajustan»): un resumen plegado que abre
 * los controles de cinco semillas (la oferta no: decisión 17; el mercado solo ordena, HU-240). Al cambiar uno, la consulta
 * se vuelve a pedir con esos pesos. Es un `details` nativo: se abre y se cierra sin animación, igual en modo ligero. Los controles se dibujan solo abierto: son 36 botones
 * con su dibujo que la página no necesita mientras nadie los mira.
 */
export function PrioritiesPanel({ priorities }: { priorities: ReturnType<typeof useSignalPriorities> }) {
  useTranslation();
  const { value, defaults, ready, isOwn } = priorities;
  const [open, setOpen] = useState(false);
  const title = isOwn
    ? t("pages.diagnosis.PrioritiesPanel.yourPrioritiesAdjust")
    : t("pages.diagnosis.PrioritiesPanel.agrosensePrioritiesAdjust");

  if (!ready) {
    return (
      <p role="status" className="text-[15px] text-texto-secundario">
        {t("pages.account.PrioritiesCard.loadingAgrosensePriorities")}
      </p>
    );
  }
  if (!value || !defaults) {
    return (
      <p className="text-[15px] text-texto-secundario">{t("pages.diagnosis.PrioritiesPanel.weCouldNotLoadAgrosensePrioritiesThis")}</p>
    );
  }

  return (
    <details
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="group -mx-6 flex min-w-0 flex-col border-2 border-superficie-borde bg-superficie-panel-suave px-2 py-2 sm:mx-0 sm:px-4"
    >
      <summary className="flex min-h-11 cursor-pointer items-center font-bold">{title}</summary>
      {open && (
        <div className="flex min-w-0 flex-col gap-4 pt-2 pb-3">
          <p className="text-[15px] leading-snug">{t("pages.diagnosis.PrioritiesPanel.howMuchEachSignalMattersChangesThe")}</p>
          <p className="text-[15px] leading-snug text-texto-secundario">{PRIORITIES_HINT()}</p>
          {/* Las seis casillas miden 44 px (el mínimo táctil): 264 px. A 320 px solo caben si el panel ocupa todo el ancho
              de la tarjeta, por eso en el celular el panel no tiene el margen de la tarjeta (-mx-6). */}
          <div className="flex flex-col gap-4">
            {PRIORITY_CONTROLS().map((signal) => (
              <SeedRow
                key={signal.key}
                label={signal.label}
                hint={signal.hint}
                note={priorityNote(signal)}
                value={value[signal.key]}
                disabled={false}
                onChange={(weight) => priorities.set({ ...value, [signal.key]: weight })}
              />
            ))}
          </div>
          <p className="text-[15px] leading-snug text-texto-secundario">{UNRATED_PRIORITIES_NOTE()}</p>
          {priorities.allZero && (
            <p role="alert" className="font-bold text-oscuro-rojo">
              <span aria-hidden="true">▲ </span>
              {t("pages.diagnosis.PrioritiesPanel.increaseAtLeastOnePriorityAllzeroPriorities")}
            </p>
          )}
          {priorities.error && (
            <Alert>
              {priorities.error instanceof ApiError
                ? priorities.error.message
                : t("pages.diagnosis.PrioritiesPanel.yourPrioritiesCouldNotBeSavedTry")}
            </Alert>
          )}
          <p className="text-[15px] text-texto-secundario">
            {priorities.savesInProfile
              ? t("pages.diagnosis.PrioritiesPanel.savedToYourProfileAsInMy")
              : t("pages.diagnosis.PrioritiesPanel.rememberedOnThisDeviceWithoutAnAccount")}
          </p>
          <p className="border-t-2 border-superficie-borde pt-3 text-[15px] text-texto-secundario">
            {t("pages.account.PrioritiesCard.agrosensePriorities")}{" "}
            {PRIORITY_CONTROLS()
              .map((signal) => `${signal.label.toLowerCase()} ${defaults[signal.key]}`)
              .join(" · ")}
            .
          </p>
          {(isOwn || priorities.allZero) && (
            <button type="button" onClick={priorities.reset} className={`${LINK} min-h-11 self-start`}>
              {t("pages.account.PrioritiesCard.resetToAgrosensePriorities")}
            </button>
          )}
        </div>
      )}
    </details>
  );
}
