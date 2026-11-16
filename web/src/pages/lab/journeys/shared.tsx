import { Link } from "@/components/layout/LanguageLink";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { Card as BaseCard } from "@/components/ui/Card";
import { ExampleLabel } from "@/components/ui/Labels";

import { useAnimated } from "@/hooks/useLightMode";

/** El laboratorio lo llama «reducir movimiento»: es el modo ligero (HU-158). */
export const useReducedMotion = () => !useAnimated();
export { useSmoothScroll } from "@/hooks/useSmoothScroll";
export { followScroll } from "@/lib/followScroll";

/** Panel de interfaz sobre la escena: el dato va en HTML, encima del paisaje (principio 1 de diseño). */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <BaseCard className={`flex max-w-[min(92vw,30rem)] flex-col ${className}`}>{children}</BaseCard>;
}

const ROUTES = [
  { href: "/recorrido/1", label: "lab.nav.orbit" },
  { href: "/recorrido/2", label: "lab.nav.year" },
  { href: "/recorrido/3", label: "lab.nav.range" },
  { href: "/kit", label: "lab.nav.kit" },
];

/** Barra para saltar entre los tres recorridos de prueba. */
export function JourneyNav({ current }: { current: string }) {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("lab.nav.label")}
      className="fixed inset-x-0 top-0 z-30 flex flex-wrap items-center gap-x-4 gap-y-1 bg-paleta-noche/85 px-4 py-2 text-sm text-texto-sobre-oscuro"
    >
      {ROUTES.map((r) => (
        <Link
          key={r.href}
          to={r.href}
          aria-current={r.href === current ? "page" : undefined}
          className={`rounded-sm px-2 py-1 focus-visible:outline-white ${r.href === current ? "bg-white font-bold text-texto-principal" : "underline"}`}
        >
          {t(r.label)}
        </Link>
      ))}
      <span className="ml-auto hidden sm:block">
        <ExampleLabel>{t("lab.nav.example")}</ExampleLabel>
      </span>
    </nav>
  );
}

export function ScrollHint() {
  const { t } = useTranslation();
  return (
    <p className="pointer-events-none absolute inset-x-0 bottom-5 z-20 text-center font-bold text-texto-sobre-oscuro [text-shadow:0_2px_0_rgb(30_42_58/0.7)]">
      {t("lab.nav.scroll")}
      <span aria-hidden="true">↓</span>
    </p>
  );
}
