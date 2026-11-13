// Revisa en el build que el motor del movimiento (GSAP, ScrollTrigger y Lenis) se cargue aparte (HU-158):
//   · sin movimiento (lo pide el equipo o la persona eligió «Modo ligero») no se descarga, ni al abrir cada página ni al
//     navegar dentro de la web;
//   · con movimiento sí llega: el scroll suave se activa, la portada se mueve con el scroll y «Entrar» termina su entrada;
//   · al apagar el modo ligero sin recargar se pide en ese momento, y al prenderlo otra vez se quita el scroll suave;
//   · ninguna página se rompe: la barra superior y el título están a la vista y no hay errores en la consola.
// Se mide el build y no el servidor de desarrollo: las páginas públicas llegan dibujadas desde el build y la web arranca
// sobre ese HTML como si hubiera movimiento; ese primer dibujo no puede tocar el motor si no vino (`src/lib/motion.ts`).
//
//   npm run test:motion                    (hace el build y lo revisa)
//   npm run test:motion -- --sin-build     (usa el dist/ que ya hay)
//
// Usa el Chrome instalado en el equipo (playwright-core, canal «chrome»): no descarga navegadores.

import { execSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { chromium } from "playwright-core";

const args = process.argv.slice(2);
const DIST = "dist";
const PORT = 4181;
const BASE = `http://localhost:${PORT}`;

if (!args.includes("--sin-build")) execSync("npm run build", { stdio: "inherit" });

// Los archivos del motor salen del manifiesto del build: el trozo de `lib/motionEngine.ts` y los que importa.
const manifest = JSON.parse(readFileSync(join(DIST, ".vite", "manifest.json"), "utf8"));
const engine = manifest["src/lib/motionEngine.ts"];
const ENGINE_FILES = new Set([engine.file, ...(engine.imports ?? []).map((key) => manifest[key].file)].map((file) => `/${file}`));
/** El trozo de la aplicación: hasta que llega y corre, una página del build es solo el HTML pintado. */
const APP_FILE = `/${manifest["src/app/main.tsx"].file}`;

// Como el alojamiento: la página dibujada en el build si existe; si no, el cascarón vacío de la app (web/README.md).
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".woff2": "font/woff2",
};
const server = createServer((request, response) => {
  const path = normalize(decodeURIComponent(new URL(request.url, "http://x").pathname)).replace(/^[\\/]+/, "");
  let file = join(DIST, path);
  if (file.startsWith(DIST) && existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!file.startsWith(DIST) || !existsSync(file)) file = join(DIST, "app.html");
  response.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" });
  response.end(readFileSync(file));
});
await new Promise((ready) => server.listen(PORT, ready));

const browser = await chromium.launch({ channel: "chrome", headless: true });
const failures = [];
const check = (ok, what) => {
  console.log(`  ${ok ? "ok " : "MAL"}  ${what}`);
  if (!ok) failures.push(what);
};

/** Una pestaña nueva: con «reducir movimiento» del equipo o sin él, y con la preferencia de la persona si la hay. */
async function open({ reduced = false, pref } = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: reduced ? "reduce" : "no-preference" });
  if (pref) await context.addInitScript((value) => localStorage.setItem("agrosense:modo-ligero", value), pref);
  const page = await context.newPage();
  const scripts = [];
  const errors = [];
  let lastScript = Date.now();
  page.on("request", (request) => {
    if (request.resourceType() !== "script") return;
    scripts.push(new URL(request.url()).pathname);
    lastScript = Date.now();
  });
  page.on("pageerror", (error) => errors.push(error.message.split("\n")[0]));
  page.on("console", (message) => message.type() === "error" && errors.push(message.text().split("\n")[0]));
  const toggle = () => page.locator('button[aria-label="Modo ligero"]:visible');
  /**
   * Espera a que la web haya arrancado: sobre el HTML del build, la aplicación se trae después del primer pintado (hasta
   * 2,5 s después, `src/app/boot.ts`), así que «la red quieta» no alcanza. Cuenta cuando llegó la aplicación y pasó
   * un segundo sin pedir otro script.
   */
  const settle = async () => {
    const start = Date.now();
    while (Date.now() - start < 15_000 && (!scripts.includes(APP_FILE) || Date.now() - lastScript < 1000)) await page.waitForTimeout(100);
    if (!scripts.includes(APP_FILE)) errors.push("la aplicación no arrancó en 15 s");
  };
  return { context, page, errors, toggle, settle, engine: () => scripts.some((script) => ENGINE_FILES.has(script)) };
}

/** Navega dentro de la web, sin recargar, como un enlace. */
const navigate = (page, path) =>
  page.evaluate((to) => {
    history.pushState({}, "", to);
    dispatchEvent(new PopStateEvent("popstate"));
  }, path);

const PAGES = ["/", "/entrar", "/consultar", "/diagnostico", "/politica-de-datos"];

console.log("Modo ligero elegido, al abrir cada página");
for (const path of PAGES) {
  const tab = await open({ pref: "on" });
  await tab.page.goto(BASE + path);
  await tab.settle();
  const whole = (await tab.toggle().count()) === 1 && (await tab.page.getByRole("heading").first().isVisible());
  check(
    !tab.engine() && whole && tab.errors.length === 0,
    `${path}: sin motor, con la barra y el título, sin errores ${tab.errors.join(" | ")}`,
  );
  await tab.context.close();
}

console.log("\n«Reducir movimiento» del equipo, navegando dentro de la web");
{
  const tab = await open({ reduced: true });
  await tab.page.goto(BASE + "/");
  await tab.settle();
  for (const path of PAGES.slice(1)) {
    await navigate(tab.page, path);
    await tab.settle();
  }
  check(!tab.engine(), `ninguna de ${PAGES.length} páginas descarga el motor`);
  check(tab.errors.length === 0, `sin errores en la consola ${tab.errors.join(" | ")}`);
  await tab.context.close();
}

console.log("\nCon movimiento");
{
  const tab = await open();
  await tab.page.goto(BASE + "/");
  await tab.settle();
  check(tab.engine(), "Inicio trae el motor");
  check((await tab.page.locator("html.lenis").count()) === 1, "el scroll suave está activo");
  const copy = tab.page.locator("[data-hero-copy]").first();
  const before = await copy.evaluate((el) => getComputedStyle(el).transform);
  await tab.page.mouse.wheel(0, 900);
  await tab.page.waitForTimeout(1200);
  check((await copy.evaluate((el) => getComputedStyle(el).transform)) !== before, "la portada se mueve con el scroll");
  await navigate(tab.page, "/entrar");
  await tab.settle();
  await tab.page.waitForTimeout(1000);
  check(
    (await tab.page
      .locator("[data-enter]")
      .first()
      .evaluate((el) => getComputedStyle(el).opacity)) === "1",
    "«Entrar» termina su entrada a la vista",
  );
  check(tab.errors.length === 0, `sin errores en la consola ${tab.errors.join(" | ")}`);
  await tab.context.close();
}

console.log("\nModo ligero apagado y prendido sin recargar");
{
  const tab = await open({ pref: "on" });
  await tab.page.goto(BASE + "/");
  await tab.settle();
  await tab.toggle().click();
  await tab.page.waitForTimeout(1500);
  check(tab.engine(), "al apagarlo se pide el motor");
  check((await tab.page.locator("html.lenis").count()) === 1, "y empieza el scroll suave");
  await tab.toggle().click();
  await tab.page.waitForTimeout(500);
  check((await tab.page.locator("html.lenis").count()) === 0, "al prenderlo otra vez se quita");
  check(tab.errors.length === 0, `sin errores en la consola ${tab.errors.join(" | ")}`);
  await tab.context.close();
}

await browser.close();
server.close();
if (failures.length) {
  console.error(`\n${failures.length} problema(s).`);
  process.exit(1);
}
console.log("\nTodo bien.");
