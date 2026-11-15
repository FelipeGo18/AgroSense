import { ApiError, type Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useChanges, type ChangesResponse } from "@/features/changes/changes";
import { SIGNAL_NAME } from "@/features/diagnosis/signals";
import { ChangesContext, useChangesContext } from "./ChangesContext";

type Period = Schemas["Period"];
type Periods = Schemas["Periods"];

type Indicator = "frost_freq_pct" | "precip_normal_mm" | "tmax_p90_c";

const NOTICE = "Así fue en la historia de su zona. No es un pronóstico";

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

const NUMBER = new Intl.NumberFormat("es-CO", {
  maximumFractionDigits: 1,
});

const INDICATORS: {
  key: Indicator;
  title: string;
  unit: string;
  differenceUnit: string;
}[] = [
  {
    key: "frost_freq_pct",
    title: "Heladas",
    unit: "%",
    differenceUnit: "puntos porcentuales",
  },
  {
    key: "precip_normal_mm",
    title: "Lluvia normal",
    unit: "mm",
    differenceUnit: "mm",
  },
  {
    key: "tmax_p90_c",
    title: "Temperatura máxima · percentil 90",
    unit: "°C",
    differenceUnit: "°C",
  },
];

function periodLabel(period: Period) {
  return `Entre ${period.start_year} y ${period.end_year}`;
}

function sourceLabel(sourceId: string) {
  if (sourceId === "nasa_power") return "NASA POWER";
  if (/imerg/i.test(sourceId)) return "GPM IMERG";
  return sourceId;
}

function Missing() {
  return (
    <span className="inline-flex items-start gap-2">
      <span aria-hidden="true">◇</span>
      <span>Sin datos suficientes</span>
    </span>
  );
}

function PeriodValue({
  label,
  value,
  unit,
  minimum,
  maximum,
  before,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  minimum: number;
  maximum: number;
  before: boolean;
}) {
  const known = value != null;
  const width = known ? ((value - minimum) / (maximum - minimum)) * 100 : 0;

  return (
    <div className="min-w-0">
      <p className="text-sm text-texto-secundario">{label}</p>

      {known ? (
        <>
          <p className="font-bold">
            {NUMBER.format(value)} {unit}
          </p>
          <div aria-hidden="true" className="mt-1 h-3 border border-current">
            <div
              className="h-full"
              style={{
                width: `${Math.max(0, Math.min(100, width))}%`,
                background: before ? "repeating-linear-gradient(135deg, currentColor 0 2px, transparent 2px 5px)" : "currentColor",
              }}
            />
          </div>
        </>
      ) : (
        <div className="mt-1 border-2 border-dashed p-2 text-sm">
          <Missing />
        </div>
      )}
    </div>
  );
}

function Comparison({
  data,
  indicator,
  title,
  unit,
  differenceUnit,
}: {
  data: ChangesResponse;
  indicator: Indicator;
  title: string;
  unit: string;
  differenceUnit: string;
}) {
  const periods = indicator === "precip_normal_mm" ? (data.precip_periods ?? data.periods) : data.periods;

  const sameSource = periods.before.source_id === periods.after.source_id;

  // La escala incluye ambos periodos y los doce meses.
  // Un valor nulo nunca participa como cero.
  const values = data.months.flatMap((month) => {
    const metric = month[indicator];
    return [metric.before, metric.after].filter((value): value is number => value != null);
  });

  const minimum = Math.min(0, ...values);
  const maximum = Math.max(minimum + 1, ...values);

  const imerg = /imerg/i.test(periods.before.source_id);
  const power = periods.before.source_id === "nasa_power";

  return (
    <Card>
      <h2 className="text-xl">{title}</h2>
      <p>
        {periodLabel(periods.before)} · {periodLabel(periods.after)}
      </p>

      {!sameSource ? (
        <p role="alert">No se pueden comparar estos periodos porque sus fuentes son distintas.</p>
      ) : (
        <>
          <p className="text-sm text-texto-secundario">
            Fuente: {sourceLabel(periods.before.source_id)}. Unidades: {unit}.
          </p>

          {power && <p className="text-sm">NASA POWER es un reanálisis, un modelo con observaciones; no es una observación directa.</p>}

          {imerg && <p className="text-sm">Los datos de IMERG empiezan en 2000; por eso sus periodos pueden ser más cortos.</p>}

          <p className="text-sm">Antes: barras rayadas. Después: barras llenas. Todas usan la misma escala dentro de esta comparación.</p>

          <ol className="flex flex-col gap-5">
            {MONTHS.map((monthName, index) => {
              const metric = data.months.find((month) => month.month === index + 1)?.[indicator];

              const comparable = metric?.status === "available" && metric.before != null && metric.after != null && metric.change != null;

              return (
                <li key={monthName} className="border-t border-superficie-borde pt-3">
                  <h3 className="font-bold">{monthName}</h3>

                  <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <PeriodValue
                      label={periodLabel(periods.before)}
                      value={metric?.before}
                      unit={unit}
                      minimum={minimum}
                      maximum={maximum}
                      before
                    />
                    <PeriodValue
                      label={periodLabel(periods.after)}
                      value={metric?.after}
                      unit={unit}
                      minimum={minimum}
                      maximum={maximum}
                      before={false}
                    />
                  </div>

                  <div className="mt-2 text-sm">
                    {comparable ? (
                      <p>
                        Cambio, después menos antes: {metric.change! > 0 ? "+" : ""}
                        {NUMBER.format(metric.change!)} {differenceUnit}.
                      </p>
                    ) : (
                      <>
                        <p>Cambio entre periodos:</p>
                        <Missing />
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Card>
  );
}

function Windows({ periods, windows }: { periods: Periods; windows: ChangesResponse["best_windows"] }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-2xl">Las mejores fechas de siembra, antes y después</h2>

      <p>Con los pesos de AgroSense. Solo cambia el clima: la oferta, el mercado y el suelo son los mismos en ambos periodos.</p>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {(["before", "after"] as const).map((side) => (
          <Card key={side}>
            <h3 className="text-xl">{periodLabel(periods[side])}</h3>

            {windows[side].length === 0 ? (
              <p>La respuesta no incluye mejores ventanas para este periodo. Revise las limitaciones.</p>
            ) : (
              <ol className="flex list-decimal flex-col gap-4 pl-6">
                {windows[side].map((window) => (
                  <li key={window.month}>
                    <p className="font-bold">Sembrar en {MONTHS[window.month - 1]?.toLowerCase()}</p>

                    {window.limiting_score != null ? (
                      <p>
                        Factor limitante: {NUMBER.format(window.limiting_score)}/100
                        {window.limiting_signal ? ` · ${SIGNAL_NAME[window.limiting_signal]}` : ""}
                      </p>
                    ) : (
                      <Missing />
                    )}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}

export function ChangesPage() {
  const context = useChangesContext();
  const { municipalityId, cropId, irrigation } = context;

  const irrigated = irrigation === "si" ? true : irrigation === "no" ? false : null;

  const complete = context.valid;
  const query = useChanges(complete ? municipalityId : null, complete ? cropId : null, irrigated);
  const data = query.data;

  const diagnosisParams = new URLSearchParams();
  if (municipalityId) diagnosisParams.set("municipio", municipalityId);
  if (cropId) diagnosisParams.set("cultivo", cropId);
  if (irrigation === "si" || irrigation === "no") {
    diagnosisParams.set("riego", irrigation);
  }

  const diagnosisUrl = `${PATHS.diagnosis}?${diagnosisParams.toString()}`;

  return (
    <>
      <TopBar />

      <main className="container-page flex min-h-svh flex-col gap-7 pt-28 pb-40">
        <title>Qué cambió en su zona · AgroSense</title>
        <Card>
          <h1 className="text-[clamp(1.75rem,5vw,3rem)]">¿Qué cambió en su zona?</h1>

          <p className="border-2 border-current p-3 font-bold">{NOTICE}</p>

          <p>Dos periodos de la historia del municipio: heladas, lluvia, calor y mejores fechas de siembra.</p>
          <ChangesContext context={context} />

          <ButtonLink to={diagnosisUrl} variant="secondary" className="self-start">
            Ir al diagnóstico de una siembra
          </ButtonLink>
        </Card>

        {!context.ready && !context.error && <p role="status">Cargando municipios y cultivos…</p>}
        {context.ready && !complete && (
          <Card>
            <p>Elija un municipio, un cultivo y una opción de riego para comparar su historia.</p>
          </Card>
        )}

        {complete && query.isPending && <p role="status">Cargando la comparación histórica…</p>}

        {complete && query.isError && (
          <Card>
            <p role="alert">
              {query.error instanceof ApiError && query.error.status === 501
                ? "La comparación histórica todavía no está disponible para este cultivo y municipio."
                : query.error.message}
            </p>

            <Button onClick={() => void query.refetch()} className="self-start">
              Volver a intentar
            </Button>
          </Card>
        )}

        {complete && data && (
          <>
            {data.versions.dataset === "ejemplo" && (
              <p className="border-2 border-dashed p-3 font-bold">Datos de ejemplo. No representan observaciones reales.</p>
            )}

            {data.suitability.level === "not_suitable" ? (
              <Card>
                <h2 className="text-xl">Este cultivo no se da en su zona</h2>
                {data.suitability.reasons.map((reason, index) => (
                  <p key={index}>{reason}</p>
                ))}
                <p>Mostramos únicamente el clima de la zona; no hay ventanas del cultivo que comparar.</p>
                <Button variant="secondary" className="self-start" onClick={() => context.change("cultivo", "")}>
                  Elegir otro cultivo
                </Button>
              </Card>
            ) : (
              <>
                {data.suitability.level === "insufficient_data" && (
                  <p className="border-2 border-dashed p-3">
                    No hay datos suficientes para confirmar la aptitud del cultivo. Esto no significa que sea desfavorable.
                  </p>
                )}

                <Windows periods={data.periods} windows={data.best_windows} />
              </>
            )}

            <section aria-label="Comparaciones mensuales del clima" className="flex flex-col gap-6">
              {INDICATORS.map((indicator) => (
                <Comparison
                  key={indicator.key}
                  data={data}
                  indicator={indicator.key}
                  title={indicator.title}
                  unit={indicator.unit}
                  differenceUnit={indicator.differenceUnit}
                />
              ))}
            </section>

            <Card>
              <h2 className="text-xl">Lo que dicen los datos</h2>
              {data.reasons.length > 0 ? (
                data.reasons.map((reason, index) => <p key={index}>{reason}</p>)
              ) : (
                <p>La respuesta no incluye explicaciones adicionales.</p>
              )}

              <h2 className="text-xl">Limitaciones</h2>
              {data.limitations.length > 0 ? (
                <ul className="list-disc space-y-2 pl-6">
                  {data.limitations.map((limitation, index) => (
                    <li key={index}>{limitation}</li>
                  ))}
                </ul>
              ) : (
                <p>La respuesta no declara limitaciones adicionales.</p>
              )}

              <p className="text-sm text-texto-secundario">
                Dataset: {data.versions.dataset} · Reglas: {data.versions.rules}
              </p>
            </Card>
          </>
        )}
      </main>

      <Footer />
    </>
  );
}
