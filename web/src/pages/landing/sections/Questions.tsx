import { Mascot } from "@/components/mascot/Mascot";
import { Card } from "@/components/ui/Card";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { TrafficLightBadge } from "@/components/ui/TrafficLightBadge";
import { useReveal } from "@/hooks/useReveal";
import { CloudEdge, SectionHeader } from "../SectionHeader";
import { QUESTIONS } from "../content";

const SEED = "M16 9c9 .6 13 9 12 17-.8 8-7 12-13 12S3 34 2 26C1 17 7 9 16 9z";

/** Dibujo de cada pregunta, hecho con piezas del kit. Es decoración: la pregunta ya está escrita al lado. */
function QuestionIcon({ icon }: { icon: (typeof QUESTIONS)[number]["icon"] }) {
  if (icon === "light") return <TrafficLightBadge light="green" />;
  if (icon === "frost") return <SignalIcon signal="frost" className="size-14" />;
  if (icon === "priority")
    return (
      <svg aria-hidden="true" viewBox="0 0 170 40" className="h-10 w-[170px]">
        {[0, 1, 2, 3, 4].map((i) => (
          <path
            key={i}
            d={SEED}
            transform={`translate(${i * 34} 0)`}
            fill={i < 3 ? "#C8873A" : "var(--color-superficie-panel)"}
            stroke={i < 3 ? "#1D1D1B" : "var(--color-oscuro-cielo)"}
            strokeWidth="2.5"
            strokeDasharray={i < 3 ? undefined : "4 3"}
          />
        ))}
      </svg>
    );
  return (
    <svg aria-hidden="true" viewBox="0 0 24 28" className="h-14 w-12">
      <polygon
        points="12,1 22,17 18,27 6,27 2,17"
        fill="var(--color-paleta-cielo)"
        stroke="var(--color-oscuro-cielo)"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <polygon points="12,1 22,17 18,27 12,27" fill="var(--color-oscuro-cielo)" />
    </svg>
  );
}

/** Primera parada: las cuatro preguntas que responde AgroSense. */
export function Questions({ animated }: { animated: boolean }) {
  const scope = useReveal<HTMLElement>(animated, "rise");
  return (
    <section id="preguntas" ref={scope} aria-labelledby="preguntas-titulo" className="relative z-10 bg-paleta-niebla">
      {/* Sin recorrido la portada no se queda quieta: las nubes taparían su parte de abajo. */}
      {animated && <CloudEdge className="text-paleta-niebla" />}
      <div className="mx-auto max-w-[1440px] px-5 pt-28 pb-20 md:px-12 lg:px-24">
        <SectionHeader stop="preguntas" title="Cuatro preguntas, cuatro respuestas claras">
          Para su lote o, sin cuenta, para su municipio.
        </SectionHeader>
        <ol className="mt-10 grid gap-6 md:grid-cols-2">
          {QUESTIONS.map((question, i) => (
            <li key={question.title} data-reveal className="flex">
              <Card className="flex min-h-[280px] grow flex-col" bodyClassName="grow">
                <h3 className="flex items-baseline gap-3 text-[clamp(1.25rem,1.7vw,1.5rem)]">
                  <span aria-hidden="true" className="text-[34px] leading-none text-paleta-calabaza">
                    {i + 1}
                  </span>
                  {question.title}
                </h3>
                <p className="text-sm">{question.text}</p>
                <div className="mt-auto flex items-end justify-between gap-4 pt-4">
                  <QuestionIcon icon={question.icon} />
                  <Mascot mood="idle" seed={question.seed} size={104} decorative />
                </div>
              </Card>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
