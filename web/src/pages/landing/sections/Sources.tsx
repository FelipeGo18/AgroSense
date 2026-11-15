import { useTranslation } from "react-i18next";
import { Link } from "@/components/layout/LanguageLink";
import { PATHS } from "@/app/paths";
import { Card } from "@/components/ui/Card";
import { useReveal } from "@/hooks/useReveal";
import { SectionHeader } from "../SectionHeader";
import { SOURCES } from "../content";

/** Tercera parada: de dónde salen los datos y qué no hace AgroSense. */
export function Sources({ animated }: { animated: boolean }) {
  const { t } = useTranslation();
  const scope = useReveal<HTMLElement>(animated, "pop");
  return (
    <section id="fuentes" ref={scope} aria-labelledby="fuentes-titulo" className="relative z-10 bg-paleta-cielo">
      {/* El espacio de abajo es para los cerros del pie de página, que suben sobre esta sección. */}
      <div className="container-page pt-28 pb-44 md:pb-52">
        <SectionHeader stop="fuentes" title={t("landing.sourcesTitle")}>
          {t("landing.sourcesIntro")}
        </SectionHeader>
        <ul className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {SOURCES.map((source) => (
            <li key={t(source.kind)} data-reveal className="flex">
              <Card className="grow">
                <p className="text-xs font-bold tracking-wide text-texto-secundario uppercase">{t(source.kind)}</p>
                <h3 className="text-[24px]">{source.name}</h3>
                {source.full && <p className="-mt-2 text-xs text-texto-secundario">{t(source.full)}</p>}
                <p className="text-sm">{t(source.text)}</p>
              </Card>
            </li>
          ))}
        </ul>
        <div data-reveal className="mt-10 border-l-8 border-paleta-calabaza pl-5">
          <p className="max-w-[60rem] font-bold">{t("landing.disclaimer")}</p>
          <Link
            to={PATHS.howItWorks}
            className="mt-2 inline-flex min-h-11 items-center font-bold underline decoration-2 underline-offset-4"
          >
            {t("landing.learn")}
          </Link>
        </div>
      </div>
    </section>
  );
}
