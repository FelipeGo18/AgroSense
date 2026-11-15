// Genera las respuestas simuladas de la web (HU-013) a partir de la API, como `npm run api:types` genera los tipos.
//
//   docker compose up app            # en la raíz
//   npm run api:examples             # escribe src/mocks/examples.json
//
// De cada ruta toma los ejemplos de su OpenAPI (backend/api/calc_examples.py): son de ejemplo y lo dicen (R5). Los
// catálogos (municipios y cultivos) y las versiones se piden a la API tal como responden: son datos reales del dataset
// publicado, no inventados. Nunca se escriben a mano: si el contrato cambia, se vuelve a generar.
import { writeFile } from "node:fs/promises";

const API = process.env.API_URL ?? "http://127.0.0.1:8000";
const OUT = new URL("../src/mocks/examples.json", import.meta.url);

async function get(path) {
  const response = await fetch(`${API}${path}`);
  if (!response.ok) throw new Error(`${path} respondió ${response.status}. ¿Está arriba la API? (docker compose up app)`);
  return response.json();
}

const openapi = await get("/api/openapi.json");

/** De cada ruta: los ejemplos de su respuesta correcta (por nombre) y los de sus errores (por código HTTP). */
const routes = {};
for (const [path, methods] of Object.entries(openapi.paths)) {
  for (const [method, operation] of Object.entries(methods)) {
    const ok = {};
    const errors = {};
    for (const [status, response] of Object.entries(operation.responses ?? {})) {
      const content = response.content?.["application/json"];
      if (!content) continue;
      const named = content.examples
        ? Object.fromEntries(Object.entries(content.examples).map(([name, example]) => [name, example.value]))
        : content.example !== undefined
          ? { ejemplo: content.example }
          : {};
      if (Object.keys(named).length === 0) continue;
      if (status.startsWith("2")) Object.assign(ok, named);
      else errors[status] = Object.values(named)[0];
    }
    // Solo las rutas que traen una respuesta correcta de ejemplo: las de cuentas siguen yendo a la API real (HU-014).
    if (Object.keys(ok).length === 0) continue;
    routes[`${method.toUpperCase()} ${path.replace(/^\/api\/v1/, "")}`] = { ok, errors };
  }
}

const version = await get("/api/v1/version");
const examples = {
  _aviso:
    "Generado con `npm run api:examples`; no se edita a mano. Las respuestas de cálculo y de suelo son de ejemplo, " +
    "con cifras inventadas (R5). Los catálogos y las versiones son los del dataset publicado.",
  routes,
  catalogs: {
    municipalities: await get("/api/v1/catalogs/municipalities"),
    crops: await get("/api/v1/catalogs/crops"),
    version,
  },
};

await writeFile(OUT, `${JSON.stringify(examples, null, 2)}\n`);
const names = Object.entries(routes).map(([route, { ok }]) => `${route} (${Object.keys(ok).join(", ")})`);
console.log(`Escrito src/mocks/examples.json con ${names.length} rutas:\n  ${names.join("\n  ")}`);
