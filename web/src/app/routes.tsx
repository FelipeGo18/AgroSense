import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Outlet, ScrollRestoration, createBrowserRouter, useLocation, type RouteObject } from "react-router";
import { SimulationStrip } from "@/components/layout/SimulationStrip";
import { SIMULATION } from "./config";
import { PATHS } from "./paths";

function Root() {
  // Un cliente por aplicación montada: guarda en memoria lo que responde la API (por ejemplo, quién tiene la sesión).
  const [client] = useState(() => new QueryClient());
  const { pathname } = useLocation();
  const [start] = useState(pathname);
  const [moved, setMoved] = useState(false);
  if (!moved && pathname !== start) setMoved(true);
  return (
    <QueryClientProvider client={client}>
      {/* Cada página entra con un fundido corto (styles/index.css), salvo la primera: esa ya viene pintada. */}
      <div key={pathname} className={moved ? "page-fade" : undefined}>
        <Outlet />
      </div>
      <ScrollRestoration />
      {SIMULATION && <SimulationStrip />}
    </QueryClientProvider>
  );
}

function Loading() {
  return (
    <p role="status" className="p-8">
      Cargando…
    </p>
  );
}

/** Pantallas ya diseñadas en Figma que todavía no están programadas: cada enlace lleva a un lugar que lo dice. */
const PENDING: { path: string; title: string }[] = [
  { path: PATHS.consult, title: "Consultar" },
  { path: PATHS.howItWorks, title: "¿Cómo funciona?" },
];

const pending = ({ path, title }: (typeof PENDING)[number]): RouteObject => ({
  path,
  lazy: async () => {
    const { PendingPage } = await import("@/pages/pending/PendingPage");
    return { element: <PendingPage title={title} /> };
  },
});

export const routes: RouteObject[] = [
  {
    element: <Root />,
    HydrateFallback: Loading,
    children: [
      // Cada página se carga aparte, también el inicio: quien abre «Entrar» no descarga el recorrido de la portada.
      { path: PATHS.home, lazy: async () => ({ Component: (await import("@/pages/landing/LandingPage")).LandingPage }) },
      { path: PATHS.login, lazy: async () => ({ Component: (await import("@/pages/auth/LoginPage")).LoginPage }) },
      { path: PATHS.signup, lazy: async () => ({ Component: (await import("@/pages/auth/SignupPage")).SignupPage }) },
      { path: PATHS.account, lazy: async () => ({ Component: (await import("@/pages/account/AccountPage")).AccountPage }) },
      { path: PATHS.password, lazy: async () => ({ Component: (await import("@/pages/account/PasswordPage")).PasswordPage }) },
      { path: PATHS.activity, lazy: async () => ({ Component: (await import("@/pages/account/ActivityPage")).ActivityPage }) },
      { path: PATHS.farm, lazy: async () => ({ Component: (await import("@/pages/farm/FarmPage")).FarmPage }) },
      { path: PATHS.addLot, lazy: async () => ({ Component: (await import("@/pages/farm/AddLotPage")).AddLotPage }) },
      { path: PATHS.lot(":lotId"), lazy: async () => ({ Component: (await import("@/pages/farm/LotPage")).LotPage }) },
      { path: PATHS.editLot(":lotId"), lazy: async () => ({ Component: (await import("@/pages/farm/EditLotPage")).EditLotPage }) },
      { path: PATHS.sow(":lotId"), lazy: async () => ({ Component: (await import("@/pages/farm/SeasonFormPage")).SowPage }) },
      {
        path: PATHS.editSeason(":lotId", ":seasonId"),
        lazy: async () => ({ Component: (await import("@/pages/farm/SeasonFormPage")).EditSeasonPage }),
      },
      {
        path: PATHS.harvest(":lotId", ":seasonId"),
        lazy: async () => ({ Component: (await import("@/pages/farm/HarvestPage")).HarvestPage }),
      },
      { path: PATHS.dataPolicy, lazy: async () => ({ Component: (await import("@/pages/policy/PolicyPage")).PolicyPage }) },
      { path: PATHS.prices, lazy: async () => ({ Component: (await import("@/pages/prices/PricesPage")).PricesPage }) },
      ...PENDING.map(pending),
      // Pruebas de la fase 0. Cada recorrido se carga aparte: trae sus propias escenas.
      { path: PATHS.lab, lazy: async () => ({ Component: (await import("@/pages/lab/LabIndexPage")).LabIndexPage }) },
      { path: PATHS.kit, lazy: async () => ({ Component: (await import("@/pages/lab/KitPage")).KitPage }) },
      { path: PATHS.journey(1), lazy: async () => ({ Component: (await import("@/pages/lab/journeys/Journey1")).Journey1 }) },
      { path: PATHS.journey(2), lazy: async () => ({ Component: (await import("@/pages/lab/journeys/Journey2")).Journey2 }) },
      { path: PATHS.journey(3), lazy: async () => ({ Component: (await import("@/pages/lab/journeys/Journey3")).Journey3 }) },
      {
        path: "*",
        lazy: async () => ({ Component: (await import("@/pages/pending/NotFoundPage")).NotFoundPage }),
      },
    ],
  },
];

export const createRouter = () => createBrowserRouter(routes);
