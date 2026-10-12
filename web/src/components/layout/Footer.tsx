import type { ReactNode } from "react";
import { Link } from "react-router";
import { SOCIAL_LINKS } from "@/app/config";
import { PATHS } from "@/app/paths";
import { Logo } from "@/components/ui/Logo";
import { pts, tone, type Pt } from "@/components/ui/Plate";
import { BRAND_ICONS } from "./brandIcons";

const TEAM = "RealE4Life";

const COLUMNS = [
  {
    title: "Explorar",
    links: [
      { to: PATHS.consult, label: "Consultar" },
      { to: PATHS.farm, label: "Mi finca" },
      { to: PATHS.howItWorks, label: "Cómo funciona" },
    ],
  },
  {
    title: "Datos y cuenta",
    // «Reportar un problema» es P1 (HU-170): no se dibuja hasta que exista.
    links: [
      { to: `${PATHS.howItWorks}#fuentes`, label: "Fuentes y versión de los datos" },
      { to: PATHS.dataPolicy, label: "Política de tratamiento de datos" },
    ],
  },
];

// Cerros del paisaje, en cuatro capas de lejos a cerca. Misma geometría que `ridges` de design/kit/sheet.py.
const RIDGE_W = 1440;
const RIDGE_H = 130;
const RIDGES = [
  { depth: 0, color: tone("var(--color-paleta-oliva)", 0.35), n: 7 },
  { depth: 0.35, color: "var(--color-paleta-oliva)", n: 9 },
  { depth: 0.62, color: "var(--color-paleta-brote)", n: 6 },
  { depth: 0.84, color: "var(--color-paleta-tierra)", n: 11 },
].flatMap(({ depth, color, n }) => {
  const base = RIDGE_H * depth;
  const step = RIDGE_W / n;
  return Array.from({ length: n }, (_, i) => {
    const peak = base - RIDGE_H * (0.42 - depth * 0.3) * (0.55 + (0.45 * ((i * 7 + Math.floor(depth * 10)) % 5)) / 4);
    const x0 = i * step;
    const x1 = x0 + step;
    const mid = x0 + step * (0.35 + (0.3 * ((i * 3) % 4)) / 3);
    return [
      {
        points: [
          [x0, base],
          [mid, peak],
          [mid, RIDGE_H],
          [x0, RIDGE_H],
        ] as Pt[],
        fill: tone(color, 0.07),
      },
      {
        points: [
          [mid, peak],
          [x1, base],
          [x1, RIDGE_H],
          [mid, RIDGE_H],
        ] as Pt[],
        fill: tone(color, -0.08),
      },
    ];
  }).flat();
});

// Tierra facetada: tiras de triángulos en tonos muy cercanos, para que el texto se lea encima.
const BAND_TONES = [0.04, -0.03, 0.02, -0.05, 0.05, -0.02];
const BAND = Array.from({ length: 12 }, (_, i) => {
  const x0 = i * 120;
  const x1 = x0 + 120;
  const mid = x0 + 120 * (0.4 + (0.2 * (i % 3)) / 2);
  return [
    {
      points: [
        [x0, 0],
        [x1, 0],
        [mid, 55],
      ] as Pt[],
      fill: tone("var(--color-pie-tierra)", BAND_TONES[i % 6]),
    },
    {
      points: [
        [mid, 55],
        [x1, 100],
        [x0, 100],
      ] as Pt[],
      fill: tone("var(--color-pie-tierra)", BAND_TONES[(i + 3) % 6]),
    },
  ];
}).flat();

const LINK = "font-bold underline decoration-paleta-trigo decoration-2 underline-offset-[6px] focus-visible:outline-white";

/**
 * Pie de página común: los cerros del paisaje y la tierra donde se lee el contenido. Va en las vistas largas.
 * Los cerros suben sobre la sección de arriba, que debe dejarles espacio al final.
 * `aside` es un lugar junto a la marca, por ejemplo para la mascota que guía la página.
 */
export function Footer({ aside }: { aside?: ReactNode }) {
  return (
    <footer className="relative z-10 bg-pie-tierra text-pie-tinta">
      <svg
        aria-hidden="true"
        viewBox={`0 0 ${RIDGE_W} ${RIDGE_H}`}
        preserveAspectRatio="none"
        className="absolute inset-x-0 bottom-full block h-24 w-full md:h-[130px]"
      >
        {RIDGES.map((ridge, i) => (
          <polygon key={i} points={pts(ridge.points)} fill={ridge.fill} />
        ))}
      </svg>
      <svg aria-hidden="true" viewBox="0 0 1440 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
        {BAND.map((facet, i) => (
          <polygon key={i} points={pts(facet.points)} fill={facet.fill} />
        ))}
      </svg>
      <div className="relative mx-auto flex max-w-[1440px] flex-col gap-10 px-5 pt-10 pb-8 md:px-12 lg:px-24">
        <div className="flex flex-col gap-10 md:flex-row md:flex-wrap md:justify-between">
          <div className="flex max-w-sm items-end gap-3">
            <div>
              <Logo />
              <p className="mt-4 text-sm text-pie-suave">Datos de la NASA y reglas que se pueden leer, para sembrar mejor.</p>
            </div>
            {aside}
          </div>
          {COLUMNS.map((column) => (
            <nav key={column.title} aria-label={column.title}>
              <h2 className="font-texto text-[13px] font-bold tracking-wide text-pie-suave uppercase">{column.title}</h2>
              <ul className="mt-3 flex flex-col gap-2 text-sm">
                {column.links.map((link) => (
                  <li key={link.to}>
                    <Link to={link.to} className={LINK}>
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
          {SOCIAL_LINKS.length > 0 && (
            <div>
              <h2 className="font-texto text-[13px] font-bold tracking-wide text-pie-suave uppercase">Síganos</h2>
              <ul className="mt-3 flex gap-3">
                {SOCIAL_LINKS.map((social) => (
                  <li key={social.label}>
                    <a
                      href={social.href}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`${social.label} del equipo (se abre en otra pestaña)`}
                      className="flex size-11 items-center justify-center bg-white shadow-[0_4px_0_rgb(0_0_0/0.35)] focus-visible:outline-white"
                      style={{ color: BRAND_ICONS[social.brand].color }}
                    >
                      <svg aria-hidden="true" viewBox={BRAND_ICONS[social.brand].viewBox} className="size-[28px]">
                        <path d={BRAND_ICONS[social.brand].path} fill="currentColor" />
                      </svg>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 border-t border-pie-suave/35 pt-6 text-xs text-pie-suave md:flex-row md:justify-between">
          <p>© 2026 {TEAM}. Todos los derechos reservados.</p>
          <p>Hecho para el NASA Space Apps Challenge 2026</p>
        </div>
      </div>
    </footer>
  );
}
