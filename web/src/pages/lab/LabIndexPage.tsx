import { Link } from "@/components/layout/LanguageLink";
import { useTranslation } from "react-i18next";
import { ExampleLabel } from "@/components/ui/Labels";
import { Mascot } from "@/components/mascot/Mascot";
import { Plate } from "@/components/ui/Plate";

const PAGES = [
  { href: "/kit", title: "lab.index.kit.title", text: "lab.index.kit.body" },
  { href: "/recorrido/1", title: "lab.index.orbit.title", text: "lab.index.orbit.body" },
  {
    href: "/recorrido/2",
    title: "lab.index.year.title",
    text: "lab.index.year.body",
  },
  { href: "/recorrido/3", title: "lab.index.range.title", text: "lab.index.range.body" },
];

/** Índice de las pruebas de la fase 0. No se enlaza desde la app: se entra por /pruebas. */
export function LabIndexPage() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-10 sm:px-8">
      <title>{t("lab.index.title")}</title>
      <header className="flex flex-wrap items-center gap-6">
        <Mascot mood="guide" size={170} decorative className="mascot-float" />
        <div className="flex min-w-64 flex-1 flex-col gap-3">
          <h1 className="text-3xl">{t("lab.index.title")}</h1>
          <p>{t("lab.index.intro")}</p>
          <ExampleLabel />
        </div>
      </header>
      <ul className="flex flex-col gap-5">
        {PAGES.map((page) => (
          <li key={page.href}>
            <Link to={page.href} className="relative block px-7 pt-5 pb-8 outline-none">
              <Plate c={16} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" ring="focus" />
              <span className="relative block font-titulos text-xl font-titulo">{t(page.title)}</span>
              <span className="relative block text-texto-secundario">{t(page.text)}</span>
              <span className="relative block text-sm font-bold underline">{page.href}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
