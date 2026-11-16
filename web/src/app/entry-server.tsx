import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import { StaticRouterProvider, createStaticHandler, createStaticRouter } from "react-router";
import { routes } from "./routes";
import { i18n } from "@/lib/i18n";

/**
 * Dibuja una página pública como HTML, en el build (scripts/prerender.mjs). Así el navegador pinta el contenido en
 * cuanto llegan el HTML y la hoja de estilos, sin esperar al JavaScript; después main.tsx arranca sobre él.
 *
 * Se dibuja como la ve quien no ha entrado y con el reloj en «día»: nada de aquí depende de la persona.
 */
export async function render(path: string) {
  await i18n.changeLanguage("es");
  const handler = createStaticHandler(routes);
  const context = await handler.query(new Request(`http://agrosense.local${path}`));
  if (context instanceof Response) throw new Error(`${path} redirige: no se puede dibujar en el build`);
  const router = createStaticRouter(handler.dataRoutes, context);
  return renderToString(
    <StrictMode>
      <StaticRouterProvider router={router} context={context} hydrate={false} />
    </StrictMode>,
  );
}
