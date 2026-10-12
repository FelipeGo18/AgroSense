import { Link } from "react-router";
import { PATHS } from "@/app/paths";
import { Card } from "@/components/ui/Card";
import { useReveal } from "@/hooks/useReveal";
import { SectionHeader } from "../SectionHeader";
import { SOURCES } from "../content";

/** Tercera parada: de dónde salen los datos y qué no hace AgroSense. */
export function Sources({ animated }: { animated: boolean }) {
  const scope = useReveal<HTMLElement>(animated, "pop");
  return (
    <section id="fuentes" ref={scope} aria-labelledby="fuentes-titulo" className="relative z-10 bg-paleta-cielo">
      {/* El espacio de abajo es para los cerros del pie de página, que suben sobre esta sección. */}
      <div className="mx-auto max-w-[1440px] px-5 pt-28 pb-44 md:px-12 md:pb-52 lg:px-24">
        <SectionHeader stop="fuentes" title="De dónde salen los datos">
          Datos abiertos y reglas que se pueden leer. Cada respuesta dice de dónde sale y qué versión de los datos usó.
        </SectionHeader>
        <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {SOURCES.map((source) => (
            <li key={source.kind} data-reveal className="flex">
              <Card className="grow">
                <p className="text-xs font-bold tracking-wide text-texto-secundario uppercase">{source.kind}</p>
                <h3 className="text-[24px]">{source.name}</h3>
                {source.full && <p className="-mt-2 text-xs text-texto-secundario">{source.full}</p>}
                <p className="text-sm">{source.text}</p>
              </Card>
            </li>
          ))}
        </ul>
        <div data-reveal className="mt-10 border-l-8 border-paleta-calabaza pl-5">
          <p className="max-w-[60rem] font-bold">
            AgroSense no adivina el futuro: le muestra el riesgo histórico de su zona con reglas que puede leer. No es un pronóstico.
          </p>
          <Link to={PATHS.howItWorks} className="mt-2 inline-block font-bold underline decoration-2 underline-offset-4">
            ¿Cómo funciona y de dónde sale esto?
          </Link>
        </div>
      </div>
    </section>
  );
}
