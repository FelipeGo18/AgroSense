import { useState } from "react";
import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { SeedRow } from "@/components/ui/PriorityControl";
import { PRIORITIES_HINT, PRIORITY_SIGNALS, type useSignalPriorities } from "@/features/diagnosis/priorities";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/**
 * «Criterio de AgroSense · Ajustar» (HU-202; `specs/05-frontend.md`, «Dónde se ajustan»): un resumen plegado que abre
 * los seis controles de cinco semillas. Al cambiar uno, la consulta se vuelve a pedir con esos pesos. Es un `details`
 * nativo: se abre y se cierra sin animación, igual en modo ligero. Los controles se dibujan solo abierto: son 36 botones
 * con su dibujo que la página no necesita mientras nadie los mira.
 */
export function PrioritiesPanel({ priorities }: { priorities: ReturnType<typeof useSignalPriorities> }) {
  const { value, defaults, ready, isOwn } = priorities;
  const [open, setOpen] = useState(false);
  const title = isOwn ? "Sus prioridades · Ajustar" : "Criterio de AgroSense · Ajustar";

  if (!ready) {
    return (
      <p role="status" className="text-[15px] text-texto-secundario">
        Cargando el criterio de AgroSense…
      </p>
    );
  }
  if (!value || !defaults) {
    return (
      <p className="text-[15px] text-texto-secundario">
        No pudimos cargar el criterio de AgroSense: la consulta usa los pesos por defecto de la API y por ahora no se pueden ajustar.
      </p>
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
          <p className="text-[15px] leading-snug">
            Cuánto le importa cada señal. Cambia la luz y el orden de las fechas, pero no esconde un riesgo grave.
          </p>
          <p className="text-[15px] leading-snug text-texto-secundario">{PRIORITIES_HINT}</p>
          {/* Las seis casillas miden 44 px (el mínimo táctil): 264 px. A 320 px solo caben si el panel ocupa todo el ancho
              de la tarjeta, por eso en el celular el panel no tiene el margen de la tarjeta (-mx-6). */}
          <div className="flex flex-col gap-4">
            {PRIORITY_SIGNALS.map((signal) => (
              <SeedRow
                key={signal.key}
                label={signal.label}
                hint={signal.hint}
                note={signal.climate ? "Un riesgo grave cuenta siempre" : undefined}
                value={value[signal.key]}
                disabled={false}
                onChange={(weight) => priorities.set({ ...value, [signal.key]: weight })}
              />
            ))}
          </div>
          {priorities.allZero && (
            <p role="alert" className="font-bold text-oscuro-rojo">
              <span aria-hidden="true">▲ </span>Suba al menos una prioridad: con todas en 0 no hay nada que pesar y no se consulta.
            </p>
          )}
          {priorities.error && (
            <Alert>
              {priorities.error instanceof ApiError
                ? priorities.error.message
                : "No se pudieron guardar sus prioridades. Intente de nuevo."}
            </Alert>
          )}
          <p className="text-[15px] text-texto-secundario">
            {priorities.savesInProfile ? "Se guardan en su perfil, como en «Mi cuenta»." : "Se recuerdan en este dispositivo, sin cuenta."}
          </p>
          <p className="border-t-2 border-superficie-borde pt-3 text-[15px] text-texto-secundario">
            Criterio de AgroSense: {PRIORITY_SIGNALS.map((signal) => `${signal.label.toLowerCase()} ${defaults[signal.key]}`).join(" · ")}.
          </p>
          {(isOwn || priorities.allZero) && (
            <button type="button" onClick={priorities.reset} className={`${LINK} min-h-11 self-start`}>
              Volver al criterio de AgroSense
            </button>
          )}
        </div>
      )}
    </details>
  );
}
