import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/fredoka/600.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "./styles/index.css";
import { Home } from "./Home";

// Rutas del prototipo: /kit es el kit de componentes; /recorrido/1, /2 y /3, los recorridos de prueba; el resto, el índice.
// Cada recorrido se carga aparte: trae sus propias escenas y GSAP.
const ROUTES = {
  "/kit": lazy(() => import("./kit/KitPage").then((m) => ({ default: m.KitPage }))),
  "/recorrido/1": lazy(() => import("./journeys/Journey1").then((m) => ({ default: m.Journey1 }))),
  "/recorrido/2": lazy(() => import("./journeys/Journey2").then((m) => ({ default: m.Journey2 }))),
  "/recorrido/3": lazy(() => import("./journeys/Journey3").then((m) => ({ default: m.Journey3 }))),
} as const;
const path = location.pathname.replace(/\/$/, "") as keyof typeof ROUTES;
const Page = ROUTES[path] ?? Home;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Suspense fallback={<p className="p-8">Cargando…</p>}>
      <Page />
    </Suspense>
  </StrictMode>,
);
