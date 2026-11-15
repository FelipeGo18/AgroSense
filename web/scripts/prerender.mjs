// Genera el HTML de las páginas públicas después del build, para que se pinten sin esperar al JavaScript.
//
//   dist/index.html            el inicio, ya dibujado
//   dist/entrar/index.html     «Entrar», ya dibujado
//   dist/politica-de-datos/index.html   la política de tratamiento de datos, ya dibujada
//   dist/app.html              el cascarón vacío: lo que el servidor debe entregar para cualquier otra ruta de la app
//
// Las páginas dibujadas no piden el JavaScript por adelantado: primero se pintan, con todo el ancho de banda para el
// HTML, los estilos y las fuentes, y después src/app/boot.ts trae la aplicación. El cascarón vacío sí lo pide por
// adelantado (`modulepreload`), porque sin la aplicación no tiene nada que mostrar.
//
// Si un servidor entrega el HTML de otra ruta (por ejemplo el del inicio para /mi-cuenta), no pasa nada: main.tsx
// compara `data-prerendered` con la dirección y, si no coinciden, dibuja de cero.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";

/** Páginas que se ven igual para todos y que no cambian de estructura según el ancho de la pantalla. */
const PAGES = ["/", "/entrar", "/politica-de-datos"];
const MAIN = "src/app/main.tsx";
const EMPTY_ROOT = '<div id="root"></div>';

const { render } = await import(pathToFileURL("node_modules/.agrosense-ssr/entry-server.js").href);
const manifest = JSON.parse(readFileSync("dist/.vite/manifest.json", "utf8"));
const shell = readFileSync("dist/index.html", "utf8");
if (!shell.includes(EMPTY_ROOT)) throw new Error("dist/index.html no tiene la raíz vacía: corra antes `vite build`.");

/** Los archivos de JavaScript de un módulo y de todo lo que importa de entrada (no lo que carga después a pedido). */
function files(entry, seen = new Set()) {
  if (seen.has(entry)) return seen;
  seen.add(entry);
  for (const dep of manifest[entry]?.imports ?? []) files(dep, seen);
  return seen;
}
const preloads = (...entries) => {
  const all = new Set(entries.flatMap((entry) => [...files(entry)]));
  return [...all].map((key) => `<link rel="modulepreload" crossorigin href="/${manifest[key].file}">`).join("\n    ");
};
const withPreloads = (html, ...entries) => html.replace("</head>", `  ${preloads(...entries)}\n  </head>`);

writeFileSync("dist/app.html", withPreloads(shell, MAIN));

for (const path of PAGES) {
  let body = await render(path);
  // El título de la página sale junto al contenido: va en la cabecera.
  const title = body.match(/<title>[^<]*<\/title>/)?.[0];
  if (title) body = body.replace(title, "");
  let page = shell.replace(EMPTY_ROOT, `<div id="root" data-prerendered="${path}">${body}</div>`);
  if (title) page = page.replace(/<title>[^<]*<\/title>/, title);
  const file = path === "/" ? "dist/index.html" : `dist${path}/index.html`;
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, page);
  console.log(`prerender ${path} -> ${file} (${Math.round(page.length / 1024)} kB)`);
}
