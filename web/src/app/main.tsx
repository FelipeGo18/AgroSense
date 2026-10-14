import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import { matchRoutes } from "react-router";
import { RouterProvider } from "react-router/dom";
import { markFirstLoad, rememberTyped } from "@/lib/firstLoad";
import { createRouter, routes } from "./routes";

const root = document.getElementById("root")!;
const here = window.location.pathname.replace(/\/+$/, "") || "/";
const app = () => (
  <StrictMode>
    <RouterProvider router={createRouter()} />
  </StrictMode>
);

if (root.dataset.prerendered === here) {
  // El HTML de esta página vino dibujado desde el build (scripts/prerender.mjs): se arranca sobre él, sin borrarlo.
  // Antes hay que traer el código de la página, que se carga aparte: el primer dibujo tiene que coincidir con el HTML.
  await Promise.all(
    (matchRoutes(routes, here) ?? []).map(async ({ route }) => {
      if (typeof route.lazy !== "function") return;
      Object.assign(route, await route.lazy(), { lazy: undefined });
    }),
  );
  markFirstLoad(true);
  rememberTyped(root);
  hydrateRoot(root, app());
  // Dos cuadros después ya corrieron los efectos del arranque: lo que se monte desde aquí sí anima su entrada.
  requestAnimationFrame(() => requestAnimationFrame(() => markFirstLoad(false)));
} else {
  // Sin HTML de esta página (en desarrollo, o un servidor que entregó el de otra ruta): se dibuja de cero.
  root.replaceChildren();
  createRoot(root).render(app());
}
