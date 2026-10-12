import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Outlet, ScrollRestoration, createBrowserRouter, type RouteObject } from "react-router";
import { LandingPage } from "@/pages/landing/LandingPage";
import { PATHS } from "./paths";

function Root() {
  // Un cliente por aplicación montada: guarda en memoria lo que responde la API (por ejemplo, quién tiene la sesión).
  const [client] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <Outlet />
      <ScrollRestoration />
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
  { path: PATHS.farm, title: "Mi finca" },
  { path: PATHS.howItWorks, title: "¿Cómo funciona?" },
  { path: PATHS.dataPolicy, title: "Política de tratamiento de datos" },
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
      { path: PATHS.home, element: <LandingPage /> },
      { path: PATHS.login, lazy: async () => ({ Component: (await import("@/pages/auth/LoginPage")).LoginPage }) },
      { path: PATHS.signup, lazy: async () => ({ Component: (await import("@/pages/auth/SignupPage")).SignupPage }) },
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
