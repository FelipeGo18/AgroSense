import { PATHS } from "@/app/paths";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ExampleLabel } from "@/components/ui/Labels";
import { Plate } from "@/components/ui/Plate";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { StatusTag } from "@/components/ui/StatusTag";
import { TrafficLightBadge } from "@/components/ui/TrafficLightBadge";
import { useReveal } from "@/hooks/useReveal";
import { SectionHeader } from "../SectionHeader";
import { PREVIEW } from "../content";

/** Segunda parada: un resultado de muestra, con la acción primero y las seis señales después. */
export function Preview({ animated }: { animated: boolean }) {
  const scope = useReveal<HTMLElement>(animated, "slide");
  return (
    <section id="ejemplo" ref={scope} aria-labelledby="ejemplo-titulo" className="relative z-10 overflow-x-clip bg-seccion-ejemplo">
      <div className="container-page pt-28 pb-20">
        <SectionHeader stop="ejemplo" title="Así se revisa un ciclo">
          {PREVIEW.summary}
        </SectionHeader>
        <div className="mt-10">
          <Card bodyClassName="gap-8 xl:flex-row xl:items-start">
            <div data-reveal="left" className="flex flex-col items-start gap-4 xl:flex-1">
              <ExampleLabel>cifras de muestra</ExampleLabel>
              <TrafficLightBadge light="yellow" />
              <h3 className="text-[clamp(1.75rem,2.5vw,2.125rem)]">{PREVIEW.action}</h3>
              <p className="max-w-[30rem]">{PREVIEW.reason}</p>
              <ButtonLink to={PATHS.consult} className="w-full sm:w-[340px]">
                Pruébelo con su municipio
              </ButtonLink>
            </div>
            <ul aria-label="Las seis señales del ejemplo" className="flex flex-col gap-2.5 xl:w-[560px] xl:shrink-0">
              {PREVIEW.signals.map((signal) => {
                const missing = signal.tone === "insufficient_data";
                return (
                  <li key={signal.key} data-reveal="right" className="relative flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-1.5">
                    <Plate
                      c={10}
                      fill={missing ? "var(--color-superficie-panel)" : "var(--color-fila-senal)"}
                      stroke={missing ? "var(--color-oscuro-cielo)" : "var(--color-superficie-borde)"}
                      strokeWidth={1.5}
                      dash={missing ? "3 5" : undefined}
                    />
                    <SignalIcon signal={signal.key} className="relative" />
                    <span className="relative flex min-w-40 flex-1 flex-col leading-tight">
                      <strong>{signal.name}</strong>
                      <span className="text-xs text-texto-secundario">{signal.detail}</span>
                    </span>
                    <StatusTag tone={signal.tone} className="w-[168px]" />
                  </li>
                );
              })}
            </ul>
          </Card>
        </div>
      </div>
    </section>
  );
}
