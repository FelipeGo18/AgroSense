import { t } from "@/lib/i18n";
import { useState } from "react";
import type { Schemas } from "@/api/client";
import { useSession, useUpdateProfile } from "@/features/auth/session";
import { useVersion } from "@/features/version";

export type SignalWeights = Schemas["SignalWeights"];

/**
 * Las prioridades de las señales (HU-202, decisión 10): un peso de 0 a 5 por señal, distinto de las cuatro prioridades
 * de las rotaciones (HU-101). Las seis del P0, en el orden del diagnóstico, y qué significa darle peso a cada una. Las
 * de clima llevan su nota: un riesgo grave cuenta siempre, aunque su peso sea 0 (`specs/01-reglas.md`).
 */
export const PRIORITY_SIGNALS = () =>
  [
    {
      key: "water",
      label: t("landing.signal.water"),
      hint: t("features.diagnosis.priorities.enoughRainfall"),
      climate: true,
      control: true,
      light: true,
    },
    {
      key: "frost",
      label: t("landing.signal.frost"),
      hint: t("features.diagnosis.priorities.noFrostDuringSensitiveStages"),
      climate: true,
      control: true,
      light: true,
    },
    {
      key: "heat",
      label: t("landing.signal.heat"),
      hint: t("features.diagnosis.priorities.temperaturesWithinTheCropsTolerance"),
      climate: true,
      control: true,
      light: true,
    },
    {
      key: "soil",
      label: t("landing.signal.soil"),
      hint: t("features.diagnosis.priorities.suitablePh"),
      climate: false,
      control: true,
      light: true,
    },
    {
      key: "supply",
      label: t("landing.signal.supply"),
      hint: t("features.diagnosis.priorities.avoidingExcessivePlantedArea"),
      climate: false,
      control: false,
      light: false,
    },
    {
      key: "market",
      label: t("landing.signal.market"),
      hint: t("priorities.market.hint"),
      climate: false,
      control: true,
      light: false,
    },
  ] as const;
export type PriorityKey = ReturnType<typeof PRIORITY_SIGNALS>[number]["key"];

/**
 * Las señales que tienen control de prioridad. La oferta se muestra sin calificar (decisión 17, HU-072): su peso no tiene
 * ningún efecto y un control sin función no se dibuja. El mercado tampoco cambia la luz, pero con 4 o 5 ordena las
 * ventanas dentro de su decena (HU-240): por eso tiene control, con su nota.
 */
export const PRIORITY_CONTROLS = () => PRIORITY_SIGNALS().filter((signal) => signal.control);

/** Las señales cuyo peso puede cambiar la luz. La oferta y el mercado no (decisión 17). */
export const LIGHT_PRIORITY_SIGNALS = () => PRIORITY_SIGNALS().filter((signal) => signal.light);

/** La nota bajo el nombre de cada control: lo que su peso no puede cambiar. */
export function priorityNote(signal: ReturnType<typeof PRIORITY_SIGNALS>[number]): string | undefined {
  if (signal.climate) return t("priorities.climate.note");
  if (signal.key === "market") return MARKET_PRIORITY_NOTE();
  return undefined;
}

export const MARKET_PRIORITY_NOTE = () => t("priorities.market.note");

/**
 * Los pesos que se envían a los cálculos (`/diagnostics` y `signal_priorities` de `/rotations`): los de la persona en
 * las señales con control y, en la oferta, siempre el de AgroSense mientras no tenga control (revisión de Haider del
 * #175). Lo guardado no cambia: un peso viejo de la oferta se conserva en el perfil o el navegador, pero no llega al
 * cálculo. Sin el criterio de AgroSense no hay con qué reemplazarlo y se envía como está.
 */
export function forCalculation(weights: SignalWeights | null, defaults: SignalWeights | null): SignalWeights | null {
  if (!weights || !defaults) return weights;
  const hidden = PRIORITY_SIGNALS()
    .filter((signal) => !signal.control)
    .map(({ key }) => [key, defaults[key]]);
  return { ...weights, ...Object.fromEntries(hidden) } as SignalWeights;
}

export const UNRATED_PRIORITIES_NOTE = () => t("priorities.supply.note");

export const PRIORITIES_HINT = () => t("priorities.hint");

/** Dónde se recuerdan sin cuenta: solo en este navegador (R9). Con cuenta, en el perfil (`PATCH /me`, HU-160). */
export const STORAGE_KEY = "agrosense.prioridades";

const isWeight = (value: unknown) => Number.isInteger(value) && (value as number) >= 0 && (value as number) <= 5;

/** Seis pesos enteros de 0 a 5. Lo demás (un dato viejo o tocado a mano) no se usa. */
export function asWeights(value: unknown): SignalWeights | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (!PRIORITY_SIGNALS().every(({ key }) => isWeight(record[key]))) return null;
  return Object.fromEntries(PRIORITY_SIGNALS().map(({ key }) => [key, record[key]])) as SignalWeights;
}

/** Con todas en 0 no hay nada que pesar: no se consulta ni se guarda (`specs/02-contratos.md`: 422). */
export const allZero = (weights: SignalWeights) => PRIORITY_SIGNALS().every(({ key }) => weights[key] === 0);

export const sameWeights = (a: SignalWeights, b: SignalWeights) => PRIORITY_SIGNALS().every(({ key }) => a[key] === b[key]);

/** Lo guardado en el navegador. Si el almacenamiento no está (modo privado, bloqueado), no hay nada guardado. */
export function readStored(): SignalWeights | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const weights = raw ? asWeights(JSON.parse(raw)) : null;
    return weights && !allZero(weights) ? weights : null;
  } catch {
    return null;
  }
}

export function writeStored(weights: SignalWeights | null) {
  try {
    if (weights) localStorage.setItem(STORAGE_KEY, JSON.stringify(weights));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Sin almacenamiento, las prioridades valen solo mientras dure la visita.
  }
}

/**
 * Las prioridades de quien consulta. Empiezan en las suyas (del perfil con cuenta, del navegador sin ella) o, si no
 * tiene, en el criterio de AgroSense (`default_weights` de `GET /version`). Las comparten la consulta del diagnóstico y,
 * con HU-214, las estrategias (`signal_priorities`). `ready` dice cuándo ya se sabe con qué pesos consultar.
 */
export function useSignalPriorities() {
  const version = useVersion();
  const { user, loading } = useSession();
  const update = useUpdateProfile();
  const [stored, setStored] = useState<SignalWeights | null>(() => readStored());
  // Lo que la persona acaba de tocar: mientras se guarda en el perfil, o si lo dejó todo en 0 (que no se guarda).
  const [draft, setDraft] = useState<SignalWeights | null>(null);

  const defaults = version.data ? asWeights(version.data.default_weights) : null;
  const own = user ? asWeights(user.priorities) : stored;
  const value = draft ?? own ?? defaults;
  // Listo después del primer intento de `GET /version`, haya salido bien o mal. `isFetched` no vuelve atrás mientras la
  // consulta se reintenta: si se usara el estado («pendiente» de nuevo al reintentar sin datos), la consulta del
  // diagnóstico se cancelaría y se volvería a pedir en bucle.
  const ready = !loading && version.isFetched;

  const save = (next: SignalWeights | null) => {
    if (user) {
      update.mutate({ priorities: next }, { onSettled: () => setDraft(null) });
    } else {
      writeStored(next);
      setStored(next);
      setDraft(null);
    }
  };

  return {
    /** Los pesos de la persona (o los de AgroSense), los que muestran los controles y se guardan. */
    value,
    /** Los pesos con que se consulta: `value` con la oferta del criterio de AgroSense. Nulos si no cargó (la API usa los suyos). */
    request: forCalculation(value, defaults),
    defaults,
    ready,
    /** Si son las de la persona y no las de AgroSense. */
    isOwn: Boolean(value && defaults && !sameWeights(value, defaults)),
    allZero: Boolean(value && allZero(value)),
    savesInProfile: Boolean(user),
    saving: update.isPending,
    error: update.error,
    versionError: version.isError,
    set(next: SignalWeights) {
      setDraft(next);
      if (!allZero(next)) save(next);
    },
    /** «Volver al criterio de AgroSense»: borra las suyas y vuelve a los pesos por defecto. */
    reset() {
      setDraft(null);
      save(null);
    },
  };
}
