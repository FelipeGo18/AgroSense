import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SeedRow } from "@/components/ui/PriorityControl";
import { useUpdateProfile, type Profile } from "@/features/auth/session";
import { PRIORITY_SIGNALS as SIGNALS } from "@/features/diagnosis/priorities";
import { useVersion } from "@/features/version";
import { LINK } from "./AccountShell";

type Weights = Record<string, number>;

/**
 * «Sus prioridades» (HU-160, HU-202): el peso de 0 a 5 que la persona le da a cada señal. Se guardan en su perfil al
 * tocar las semillas (PATCH /me) y cambian el semáforo y el orden de las fechas de sus consultas.
 *
 * Al lado va siempre el criterio de AgroSense (los pesos por defecto, GET /version), para comparar y poder volver a
 * él. Un riesgo grave de agua, heladas o calor cuenta siempre, aunque su peso sea 0: se dice en cada una.
 */
export function PrioritiesCard({ user }: { user: Profile }) {
  useTranslation();
  const version = useVersion();
  const update = useUpdateProfile();
  // Lo que la persona acaba de tocar, mientras se guarda (o si lo dejó todo en 0, que no se puede guardar).
  const [draft, setDraft] = useState<Weights | null>(null);

  const title = <h2 className="text-[24px]">{t("pages.account.PrioritiesCard.yourPriorities")}</h2>;
  if (version.isPending) {
    return (
      <Card>
        {title}
        <p role="status">{t("pages.account.PrioritiesCard.loadingAgrosensePriorities")}</p>
      </Card>
    );
  }
  if (version.isError) {
    return (
      <Card>
        {title}
        <Alert>{t("pages.account.PrioritiesCard.weCouldNotLoadAgrosensePrioritiesYour")}</Alert>
        <Button variant="secondary" className="self-start" onClick={() => void version.refetch()}>
          {t("pages.account.PrioritiesCard.tryAgain")}
        </Button>
      </Card>
    );
  }

  const defaults: Weights = version.data.default_weights;
  const own = user.priorities as Weights | null;
  const value: Weights = draft ?? { ...defaults, ...own };
  const allZero = SIGNALS().every(({ key }) => value[key] === 0);

  const change = (key: string, weight: number) => {
    const next = Object.fromEntries(SIGNALS().map((signal) => [signal.key, signal.key === key ? weight : value[signal.key]]));
    setDraft(next);
    // Con todo en 0 no hay nada que comparar: no se envía y se pide subir al menos una.
    if (Object.values(next).every((w) => w === 0)) return;
    update.mutate({ priorities: next }, { onSettled: () => setDraft(null) });
  };

  return (
    <Card bodyClassName="gap-4">
      {title}
      <p className="text-[15px] text-texto-secundario">{t("pages.account.PrioritiesCard.howMuchEachSignalMattersWhenChoosing")}</p>
      <p className="font-bold">
        {own
          ? t("pages.account.PrioritiesCard.youAreUsingYourOwnPriorities")
          : t("pages.account.PrioritiesCard.youAreUsingAgrosensePriorities")}
      </p>
      {/* En pantallas muy angostas las seis casillas necesitan todo el ancho de la tarjeta. */}
      <div className="-mx-2 flex flex-col gap-4 sm:mx-0">
        {SIGNALS().map((signal) => (
          <SeedRow
            key={signal.key}
            label={signal.label}
            hint={signal.hint}
            note={signal.climate ? t("pages.account.PrioritiesCard.severeRiskAlwaysCounts") : undefined}
            value={value[signal.key]}
            disabled={false}
            onChange={(weight) => change(signal.key, weight)}
          />
        ))}
      </div>
      {allZero && (
        <p role="alert" className="font-bold text-oscuro-rojo">
          <span aria-hidden="true">▲ </span>
          {t("pages.account.PrioritiesCard.increaseAtLeastOnePriorityAllzeroPriorities")}
        </p>
      )}
      {update.isError && (
        <Alert>{update.error instanceof ApiError ? update.error.message : t("pages.account.PrioritiesCard.couldNotSaveTryAgain")}</Alert>
      )}
      {update.isSuccess && !draft && (
        <p role="status" className="text-[15px] font-bold text-oscuro-oliva">
          {t("pages.account.PrioritiesCard.saved")}
        </p>
      )}
      <p className="border-t-2 border-superficie-borde pt-3 text-[15px] text-texto-secundario">
        {t("pages.account.PrioritiesCard.agrosensePriorities")}{" "}
        {SIGNALS()
          .map((signal) => `${signal.label.toLowerCase()} ${defaults[signal.key]}`)
          .join(" · ")}
        .
      </p>
      {own && (
        <button type="button" onClick={() => update.mutate({ priorities: null })} className={`${LINK} min-h-11 self-start`}>
          {t("pages.account.PrioritiesCard.resetToAgrosensePriorities")}
        </button>
      )}
    </Card>
  );
}
