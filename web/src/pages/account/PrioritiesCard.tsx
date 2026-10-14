import { useState } from "react";
import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SeedRow } from "@/components/ui/PriorityControl";
import { useUpdateProfile, type Profile } from "@/features/auth/session";
import { useVersion } from "@/features/version";
import { LINK } from "./AccountShell";

/** Las seis señales del P0, en el orden del diagnóstico, y qué significa darle peso a cada una. */
const SIGNALS = [
  { key: "water", label: "Agua", hint: "que la lluvia alcance", climate: true },
  { key: "frost", label: "Heladas", hint: "que no hiele en lo sensible", climate: true },
  { key: "heat", label: "Calor", hint: "que no haga más calor del que aguanta", climate: true },
  { key: "soil", label: "Suelo", hint: "que el pH le sirva", climate: false },
  { key: "supply", label: "Oferta", hint: "que no haya demasiado sembrado", climate: false },
  { key: "market", label: "Mercado", hint: "que el precio suela estar bien", climate: false },
] as const;

type Weights = Record<string, number>;

/**
 * «Sus prioridades» (HU-160, HU-202): el peso de 0 a 5 que la persona le da a cada señal. Se guardan en su perfil al
 * tocar las semillas (PATCH /me) y cambian el semáforo y el orden de las fechas de sus consultas.
 *
 * Al lado va siempre el criterio de AgroSense (los pesos por defecto, GET /version), para comparar y poder volver a
 * él. Un riesgo grave de agua, heladas o calor cuenta siempre, aunque su peso sea 0: se dice en cada una.
 */
export function PrioritiesCard({ user }: { user: Profile }) {
  const version = useVersion();
  const update = useUpdateProfile();
  // Lo que la persona acaba de tocar, mientras se guarda (o si lo dejó todo en 0, que no se puede guardar).
  const [draft, setDraft] = useState<Weights | null>(null);

  const title = <h2 className="text-[24px]">Sus prioridades</h2>;
  if (version.isPending) {
    return (
      <Card>
        {title}
        <p role="status">Cargando el criterio de AgroSense…</p>
      </Card>
    );
  }
  if (version.isError) {
    return (
      <Card>
        {title}
        <Alert>No pudimos cargar el criterio de AgroSense. Sus prioridades guardadas no cambian.</Alert>
        <Button variant="secondary" className="self-start" onClick={() => void version.refetch()}>
          Volver a intentar
        </Button>
      </Card>
    );
  }

  const defaults: Weights = version.data.default_weights;
  const own = user.priorities as Weights | null;
  const value: Weights = draft ?? { ...defaults, ...own };
  const allZero = SIGNALS.every(({ key }) => value[key] === 0);

  const change = (key: string, weight: number) => {
    const next = Object.fromEntries(SIGNALS.map((signal) => [signal.key, signal.key === key ? weight : value[signal.key]]));
    setDraft(next);
    // Con todo en 0 no hay nada que comparar: no se envía y se pide subir al menos una.
    if (Object.values(next).every((w) => w === 0)) return;
    update.mutate({ priorities: next }, { onSettled: () => setDraft(null) });
  };

  return (
    <Card bodyClassName="gap-4">
      {title}
      <p className="text-[15px] text-texto-secundario">
        Cuánto le importa cada señal al elegir la fecha de siembra. Se guardan en su perfil al tocar las semillas.
      </p>
      <p className="font-bold">{own ? "Está usando sus prioridades." : "Está usando el criterio de AgroSense."}</p>
      {/* En pantallas muy angostas las seis casillas necesitan todo el ancho de la tarjeta. */}
      <div className="-mx-2 flex flex-col gap-4 sm:mx-0">
        {SIGNALS.map((signal) => (
          <SeedRow
            key={signal.key}
            label={signal.label}
            hint={signal.hint}
            note={signal.climate ? "Un riesgo grave cuenta siempre" : undefined}
            value={value[signal.key]}
            disabled={false}
            onChange={(weight) => change(signal.key, weight)}
          />
        ))}
      </div>
      {allZero && (
        <p role="alert" className="font-bold text-oscuro-rojo">
          <span aria-hidden="true">▲ </span>Suba al menos una prioridad: con todas en 0 no se guardan.
        </p>
      )}
      {update.isError && <Alert>{update.error instanceof ApiError ? update.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>}
      {update.isSuccess && !draft && (
        <p role="status" className="text-[15px] font-bold text-oscuro-oliva">
          Guardado.
        </p>
      )}
      <p className="border-t-2 border-superficie-borde pt-3 text-[15px] text-texto-secundario">
        Criterio de AgroSense: {SIGNALS.map((signal) => `${signal.label.toLowerCase()} ${defaults[signal.key]}`).join(" · ")}.
      </p>
      {own && (
        <button type="button" onClick={() => update.mutate({ priorities: null })} className={`${LINK} min-h-11 self-start`}>
          Volver al criterio de AgroSense
        </button>
      )}
    </Card>
  );
}
