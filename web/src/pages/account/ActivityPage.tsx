import { Link } from "react-router";
import { PATHS } from "@/app/paths";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useActivity, type ActivityItem } from "@/features/auth/session";
import { useEntrance, useRowsEntrance } from "@/hooks/useEntrance";
import { AccountShell, LINK } from "./AccountShell";
import { OUTCOME_LABEL, describe, keptSince, when, who, type Outcome } from "./activity";

const OUTCOME_STYLE: Record<Outcome, { ink: string; fill: string; stroke: string }> = {
  ok: { ink: "text-oscuro-oliva", fill: "#E9F2D8", stroke: "var(--color-oscuro-oliva)" },
  denied: { ink: "text-oscuro-rojo", fill: "#FBE6E2", stroke: "var(--color-oscuro-rojo)" },
  failed: { ink: "text-oscuro-calabaza", fill: "#FCEBD6", stroke: "var(--color-oscuro-calabaza)" },
};

/** El resultado de un evento con forma y texto, nunca solo color: visto bueno, equis o signo de admiración. */
function OutcomeMark({ outcome }: { outcome: Outcome }) {
  const { fill, stroke } = OUTCOME_STYLE[outcome];
  return (
    <svg aria-hidden="true" viewBox="0 0 22 22" className="size-[22px] shrink-0">
      <rect x="1" y="1" width="20" height="20" rx={outcome === "ok" ? 4 : 0} fill={fill} stroke={stroke} strokeWidth="2" />
      {outcome === "ok" && <polyline points="5,11 9,16 17,6" fill="none" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />}
      {outcome === "denied" && <path d="M6 6l10 10M16 6L6 16" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />}
      {outcome === "failed" && (
        <>
          <rect x="9.5" y="5" width="3" height="8" fill={stroke} />
          <rect x="9.5" y="15" width="3" height="3" fill={stroke} />
        </>
      )}
    </svg>
  );
}

function Event({ item }: { item: ActivityItem }) {
  const outcome = item.outcome as Outcome;
  const { what, detail } = describe(item);
  const support = who(item) === "Soporte";
  return (
    <li className="flex gap-4 border-b border-superficie-borde py-3">
      <span className="mt-0.5">
        <OutcomeMark outcome={outcome} />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-x-6 gap-y-0.5 md:flex-row md:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-bold">{what}</p>
          {detail && <p className="text-[13px] text-texto-secundario">{detail}</p>}
        </div>
        <div className="flex shrink-0 gap-x-3 text-[13px] md:flex-col md:items-end md:text-xs">
          <span className={support ? "font-bold text-oscuro-cielo" : "text-texto-secundario"}>
            {who(item)} · <time dateTime={item.occurred_at}>{when(item.occurred_at)}</time>
          </span>
          <span className={`font-bold ${OUTCOME_STYLE[outcome].ink}`}>{OUTCOME_LABEL[outcome]}</span>
        </div>
      </div>
    </li>
  );
}

/** Mi actividad (HU-178). Diseño: design/pantallas/actividad.py. */
export function ActivityPage() {
  return <AccountShell>{() => <Activity />}</AccountShell>;
}

function Activity() {
  const activity = useActivity();
  const items = activity.data?.pages.flatMap((page) => page.items) ?? [];
  const page = useEntrance<HTMLDivElement>();
  const rows = useRowsEntrance<HTMLOListElement>(items.length);
  return (
    <div ref={page} className="mx-auto max-w-[1008px] px-3 pt-[104px] md:px-6">
      <div data-enter>
        <title>Mi actividad · AgroSense</title>
        <Card bodyClassName="gap-3 md:px-4 md:pt-2">
          <Link to={PATHS.account} className={`${LINK} self-start text-[15px]`}>
            <span aria-hidden="true">‹ </span>Mi cuenta
          </Link>
          <h1 className="text-[clamp(1.875rem,3vw,2.375rem)]">Mi actividad</h1>
          <p className="text-[15px] text-texto-secundario">
            Lo que se hizo con su cuenta y sus lotes, también lo que hizo soporte. Se guarda 180 días y no muestra lo que escribió.
          </p>
          <ul aria-label="Qué significa cada marca" className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
            {(Object.keys(OUTCOME_LABEL) as Outcome[]).map((outcome) => (
              <li key={outcome} className="flex items-center gap-2">
                <OutcomeMark outcome={outcome} />
                {OUTCOME_LABEL[outcome]}
              </li>
            ))}
          </ul>
          {activity.isPending && <p role="status">Cargando su actividad…</p>}
          {activity.isError && <Alert>No pudimos cargar su actividad. Intente de nuevo en un momento.</Alert>}
          {activity.isSuccess && items.length === 0 && <p>Todavía no hay actividad en su cuenta.</p>}
          {items.length > 0 && (
            <ol ref={rows} aria-label="Actividad, de lo más reciente a lo más antiguo">
              {items.map((item) => (
                <Event key={item.event_id} item={item} />
              ))}
            </ol>
          )}
          {activity.hasNextPage && (
            <Button
              variant="secondary"
              className="self-start sm:w-[280px]"
              loading={activity.isFetchingNextPage}
              loadingText="Cargando…"
              onClick={() => void activity.fetchNextPage()}
            >
              Ver más antiguos
            </Button>
          )}
          <p className="text-[13px] text-texto-secundario">Lo anterior al {keptSince()} ya se borró.</p>
          <p className="text-[15px]">
            ¿Ve algo que no hizo?{" "}
            <Link to={PATHS.password} className={LINK}>
              Cambie su contraseña
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
