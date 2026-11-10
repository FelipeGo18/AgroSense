// Revisa que ninguna pantalla se rompa al cambiar de tamaño ni de modo (HU-096, HU-158). Abre cada ruta en un Chrome real,
// en cada ancho y alto de la lista, con movimiento y en modo ligero, y falla si encuentra:
//   · desplazamiento horizontal de la página o piezas que se salen del ancho;
//   · la barra superior con contenido fuera de su caja;
//   · botones o enlaces más chicos que 44 px (objetivo táctil, `specs/05-frontend.md`);
//   · en modo ligero: algo que siga animado (CSS) o escondido esperando una animación.
// Las reglas que comprueba están en `web/CLAUDE.md`. Al crear una pantalla nueva, súmela a ROUTES.
//
//   npm run dev -- --port 5190 --strictPort        (en otra terminal)
//   npm run test:responsive                         (o: BASE=http://127.0.0.1:5190 node e2e/responsive-check.mjs)
//
// Usa el Chrome instalado en el equipo (playwright-core, canal «chrome»): no descarga navegadores.
//
// Las páginas con sesión (Mi finca, Mi cuenta) se revisan con el token de una cuenta de prueba:
//   SESSION=<valor de la cookie agrosense_session> ROUTES=/mi-finca,/mi-finca/agregar npm run test:responsive

import { chromium } from "playwright-core";

const BASE = process.env.BASE ?? "http://127.0.0.1:5190";
// El diagnóstico con una consulta completa usa el mes en curso: siempre está entre los doce que se pueden elegir.
const THIS_MONTH = new Date().toISOString().slice(0, 7);
/** Rutas de la app. Una vista nueva se agrega aquí. */
const ROUTES = (
  process.env.ROUTES ??
  `/,/entrar,/crear-cuenta,/consultar,/diagnostico,/diagnostico?municipio=15646&cultivo=papa&siembra=${THIS_MONTH}&riego=no,/mi-finca,/como-funciona,/politica-de-datos,/precios,/precios?producto=papa-negra,/ruta-que-no-existe`
).split(",");
/** Anchos de los que hay que cuidarse: teléfono chico, teléfonos comunes, tablet, portátiles y pantalla grande. Con altos bajos a propósito. */
const SIZES = [
  [320, 568],
  [360, 640],
  [390, 844],
  [412, 915],
  [568, 320],
  [768, 1024],
  [1024, 600],
  [1024, 768],
  [1280, 720],
  [1440, 900],
  [1920, 1080],
];
/** Objetivo táctil mínimo: 44 px donde hay pantalla táctil (menos de 1024 px) y 24 px (WCAG 2.2 AA) en escritorio. */
const minTargetFor = (width) => (width < 1024 ? 44 : 24);
const KEY = "agrosense:modo-ligero";

/** Se ejecuta dentro de la página: devuelve la lista de problemas de esa pantalla. */
function inspect({ light, minTarget }) {
  const problems = [];
  const root = document.documentElement;
  const cw = root.clientWidth;
  if (root.scrollWidth > cw + 1) problems.push(`la página se desplaza en horizontal (${root.scrollWidth} > ${cw})`);

  const label = (el) =>
    `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""}${el.className && typeof el.className === "string" ? `.${el.className.split(" ").slice(0, 2).join(".")}` : ""}`;
  // Piezas que se salen del ancho. Se ignoran las que entran animadas desde afuera (data-reveal) y los dibujos internos.
  const seen = new Set();
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest("svg, canvas, [data-reveal], [aria-hidden='true'].absolute")) continue;
    // Decoración dentro de una capa escondida que recorta lo que se sale (las nubes del paisaje): no se ve fuera de la
    // capa ni hace desplazar la página. El desplazamiento horizontal real se mide arriba, con scrollWidth.
    const deco = el.closest("[aria-hidden='true']");
    if (deco && ["hidden", "clip"].includes(getComputedStyle(deco).overflowX)) continue;
    const box = el.getBoundingClientRect();
    if (!box.width || !box.height || (box.right <= cw + 1 && box.left >= -1)) continue;
    // Si un ancestro recorta (overflow hidden/clip) y la pieza queda fuera, el visitante no la ve: es un fallo igual.
    const key = label(el);
    if (seen.has(key) || seen.size >= 4) continue;
    seen.add(key);
    problems.push(`${key} se sale del ancho (${Math.round(box.left)}–${Math.round(box.right)} de ${cw})`);
  }

  const bar = document.querySelector("header > div");
  if (bar) {
    const outer = bar.getBoundingClientRect();
    for (const child of bar.querySelectorAll(":scope > div")) {
      const box = child.getBoundingClientRect();
      if (box.right > outer.right + 1 || box.left < outer.left - 1) problems.push("el contenido de la barra superior se sale de su caja");
    }
  }

  const small = [...document.querySelectorAll("a[href], button, input, select, textarea, [role='switch']")].filter((el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (
      !box.width ||
      !box.height ||
      style.visibility === "hidden" ||
      el.closest("[aria-hidden='true']") ||
      el.matches(".sr-only, .sr-only *")
    )
      return false;
    // Enlaces dentro de un párrafo de texto corrido no cuentan: el texto es el objetivo.
    if (el.tagName === "A" && el.closest("p, li") && style.display === "inline") return false;
    // Una casilla con etiqueta se toca por toda la etiqueta: cuenta la etiqueta, no la casilla sola.
    const reach =
      el.matches("input[type=checkbox], input[type=radio]") && el.labels?.length
        ? [...el.labels].map((l) => l.getBoundingClientRect())
        : [box];
    return !reach.some((b) => b.width >= minTarget - 1 && b.height >= minTarget - 1);
  });
  if (small.length) problems.push(`${small.length} control(es) menores de ${minTarget} px: ${small.slice(0, 3).map(label).join(", ")}`);

  if (light) {
    if (!root.hasAttribute("data-light")) problems.push("el modo ligero no marcó <html data-light>");
    const animated = [...document.querySelectorAll("body *")].filter((el) => {
      const s = getComputedStyle(el);
      return (
        (s.animationName !== "none" && s.animationDuration !== "0s") || (s.transitionDuration !== "0s" && s.transitionProperty !== "none")
      );
    });
    if (animated.length) problems.push(`en modo ligero siguen animados: ${animated.slice(0, 3).map(label).join(", ")}`);
    if (root.classList.contains("lenis")) problems.push("en modo ligero sigue activo el scroll suave (Lenis)");
    const hidden = [...document.querySelectorAll("[data-reveal]")].filter(
      (el) => getComputedStyle(el).opacity === "0" || getComputedStyle(el).visibility === "hidden",
    );
    if (hidden.length) problems.push(`en modo ligero ${hidden.length} pieza(s) siguen escondidas esperando una animación`);
  }
  return problems;
}

const launch = () => chromium.launch({ channel: "chrome", headless: true });
let browser = await launch();
let failures = 0;
let checked = 0;

/** Revisa una ruta en un tamaño y modo. Si Chrome se cae a media prueba, lo vuelve a abrir y reintenta. */
async function check(context, route, width, light) {
  const page = await context.newPage();
  try {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    return [...(await page.evaluate(inspect, { light, minTarget: minTargetFor(width) })), ...errors.map((e) => `error de la página: ${e}`)];
  } finally {
    await page.close().catch(() => {});
  }
}

for (const light of [false, true]) {
  for (const [width, height] of SIZES) {
    for (const route of ROUTES) {
      let problems;
      for (let attempt = 1; attempt <= 3 && !problems; attempt++) {
        const context = await browser.newContext({ viewport: { width, height }, hasTouch: width < 768, isMobile: width < 768 });
        await context.addInitScript(([key, value]) => localStorage.setItem(key, value), [KEY, light ? "on" : "off"]);
        if (process.env.SESSION) await context.addCookies([{ name: "agrosense_session", value: process.env.SESSION, url: BASE }]);
        try {
          problems = await check(context, route, width, light);
        } catch (error) {
          if (attempt === 3) problems = [`no se pudo revisar: ${error.message.split("\n")[0]}`];
          else {
            await browser.close().catch(() => {});
            browser = await launch();
          }
        } finally {
          await context.close().catch(() => {});
        }
      }
      checked++;
      if (problems.length) {
        failures++;
        console.log(`✗ ${route}  ${width}x${height}  ${light ? "modo ligero" : "con movimiento"}`);
        for (const problem of problems) console.log(`    - ${problem}`);
      }
    }
  }
}
await browser.close();
console.log(`
${checked - failures} de ${checked} combinaciones sin problemas.`);
process.exit(failures ? 1 : 0);
