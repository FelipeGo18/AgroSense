// Pruebas de estrés del scroll de los recorridos (GSAP + Lenis) en un Chrome real, sin ventana.
// Intentan romper la navegación: scroll lento, normal, brusco, con reversa, con saltos, teclado,
// cambio de tamaño, táctil y «reducir movimiento». Miden qué ve el usuario cuadro a cuadro.
//
//   npm run dev -- --port 5190 --strictPort        (en otra terminal)
//   node e2e/scroll-stress.mjs                      (escribe e2e/results/report.json y capturas)
//
// Usa el Chrome instalado en el equipo (playwright-core, canal «chrome»): no descarga navegadores.

import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright-core";

const BASE = process.env.BASE ?? "http://127.0.0.1:5190";
const OUT = process.env.OUT ?? "e2e/results";
const ROUTES = (process.env.ROUTES ?? "1,2,3").split(",");
const DESKTOP = { width: 1440, height: 810 };
const MOBILE = { width: 390, height: 780 };

mkdirSync(OUT, { recursive: true });
const sleep = (page, ms) => page.waitForTimeout(ms);

/** Graba, cuadro a cuadro, el estado de la animación y qué escena se ve. */
async function installRecorder(page) {
  await page.evaluate(() => {
    window.__rec = { on: false, rows: [] };
    let last = performance.now();
    const loop = (now) => {
      const j = window.__journey;
      if (window.__rec.on && j) {
        let maxAlpha = 0;
        let visible = -1;
        document.querySelectorAll("[data-scene]").forEach((el, i) => {
          const cs = getComputedStyle(el);
          const alpha = cs.visibility === "hidden" ? 0 : parseFloat(cs.opacity);
          if (alpha >= maxAlpha) {
            maxAlpha = alpha;
            visible = i;
          }
        });
        const wipe = document.querySelector(".journey-wipe");
        let covered = 0;
        if (wipe) {
          const r = wipe.children[1].getBoundingClientRect();
          covered = r.top <= 0 && r.bottom >= innerHeight ? 1 : 0;
        }
        window.__rec.rows.push([now, now - last, j.time(), j.target(), scrollY, maxAlpha, visible, covered]);
      }
      last = now;
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  });
}

/** ¿Lo que se ve al detenerse es una escena completa? Detecta fondos a medias y escenas corridas. */
const coverage = (page) =>
  page.evaluate(() => {
    const inScene = (x, y) => document.elementsFromPoint(x, y).some((el) => el.closest("[data-scene]"));
    const points = [
      [4, innerHeight * 0.3],
      [innerWidth - 4, innerHeight * 0.3],
      [innerWidth / 2, innerHeight * 0.6],
      [4, innerHeight - 4],
      [innerWidth - 4, innerHeight - 4],
    ];
    const lefts = [...document.querySelectorAll(".travesia-track > section")].map((s) => Math.abs(s.getBoundingClientRect().left));
    return {
      cubreLaPantalla: points.every(([x, y]) => inScene(x, y)),
      desalineadaPx: lefts.length ? Math.round(Math.min(...lefts)) : 0,
    };
  });

const record = (page) => page.evaluate(() => ((window.__rec.rows = []), (window.__rec.on = true), performance.now()));
const stop = (page) => page.evaluate(() => ((window.__rec.on = false), window.__rec.rows));
const now = (page) => page.evaluate(() => performance.now());

function analyze(rows, info, lastInputAt) {
  if (rows.length < 5) return { error: "sin cuadros grabados" };
  const dts = rows.slice(1).map((r) => r[1]);
  const sorted = [...dts].sort((a, b) => a - b);
  // Velocidad de la animación en ventanas de ~500 ms: más cortas solo miden el ruido de los cuadros (unidades de línea de tiempo por segundo).
  let maxRate = 0;
  for (let i = 0, j = 0; i < rows.length; i++) {
    while (rows[i][0] - rows[j][0] > 500) j++;
    const span = (rows[i][0] - rows[j][0]) / 1000;
    if (span > 0.4) maxRate = Math.max(maxRate, Math.abs(rows[i][2] - rows[j][2]) / span);
  }
  // Cuadros sin ninguna escena opaca y sin nubes que tapen: se vería el fondo.
  const blank = rows.filter((r) => r[5] < 0.9 && !r[7]).length;
  // Cuánto tarda en alcanzar al scroll tras la última entrada.
  let settledAt = null;
  for (let i = rows.length - 1; i >= 0; i--) {
    if (Math.abs(rows[i][2] - rows[i][3]) > 0.01) break;
    settledAt = rows[i][0];
  }
  const last = rows[rows.length - 1];
  // Tiempo en pantalla de cada escena.
  const dwell = {};
  for (const r of rows.slice(1)) dwell[r[6]] = (dwell[r[6]] ?? 0) + r[1];
  // Retrocesos: la animación va contra el destino (rebote).
  let wrongWay = 0;
  for (let i = 1; i < rows.length; i++) {
    const move = rows[i][2] - rows[i - 1][2];
    const want = rows[i][3] - rows[i - 1][2];
    if (Math.abs(move) > 1e-4 && Math.sign(move) !== Math.sign(want)) wrongWay++;
  }
  return {
    cuadros: rows.length,
    fps: +(1000 / (dts.reduce((a, b) => a + b, 0) / dts.length)).toFixed(1),
    cuadroP95ms: +sorted[Math.floor(sorted.length * 0.95)].toFixed(1),
    cuadroMaxMs: +sorted[sorted.length - 1].toFixed(1),
    cuadrosLentosPct: +((dts.filter((d) => d > 34).length / dts.length) * 100).toFixed(1),
    velocidadMax: +maxRate.toFixed(2),
    topeVelocidad: info.maxRate,
    cuadrosEnBlanco: blank,
    cuadrosContraDestino: wrongWay,
    asentadoMs: settledAt === null ? null : Math.max(0, Math.round(settledAt - lastInputAt)),
    desfaseFinal: +Math.abs(last[2] - last[3]).toFixed(4),
    terminaEnParada: info.rests ? info.rests.some(([a, b]) => last[2] >= a - 0.005 && last[2] <= b + 0.005) : null,
    tiempoFinal: +last[2].toFixed(2),
    tiempoPorEscenaMs: Object.fromEntries(Object.entries(dwell).map(([k, v]) => [k, Math.round(v)])),
  };
}

// ---------- Escenarios: cada uno devuelve el momento de su última entrada ----------

async function wheel(page, deltas, gapMs) {
  for (const d of deltas) {
    await page.mouse.wheel(0, d);
    if (gapMs) await sleep(page, gapMs);
  }
  return now(page);
}

const SCENARIOS = {
  // Trackpad suave: pasos pequeños y seguidos.
  lento: async (page) => {
    const t = await wheel(page, Array(140).fill(28), 40);
    await sleep(page, 2500);
    return t;
  },
  // Rueda de ratón normal: un golpe de 100 px cada 110 ms.
  normal: async (page) => {
    const t = await wheel(page, Array(70).fill(100), 110);
    await sleep(page, 3000);
    return t;
  },
  // Golpe brusco: mucha distancia en un instante.
  brusco: async (page) => {
    const t = await wheel(page, Array(30).fill(900), 6);
    await sleep(page, 9000);
    return t;
  },
  // Brusco hacia abajo y, sin esperar, brusco hacia arriba.
  reversa: async (page) => {
    await wheel(page, Array(24).fill(900), 6);
    await sleep(page, 700);
    const t = await wheel(page, Array(24).fill(-900), 6);
    await sleep(page, 7000);
    return t;
  },
  // Temblor: arriba y abajo sin parar.
  temblor: async (page) => {
    const deltas = Array.from({ length: 60 }, (_, i) => (i % 2 ? -260 : 300));
    const t = await wheel(page, deltas, 45);
    await sleep(page, 3500);
    return t;
  },
  // Arrastrar la barra de scroll hasta el final, y luego al principio.
  salto: async (page) => {
    await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
    await sleep(page, 2500);
    await page.evaluate(() => scrollTo(0, 0));
    const t = await now(page);
    await sleep(page, 14000);
    return t;
  },
  // Teclado: Fin, Inicio, avanzar página y barra espaciadora.
  teclado: async (page) => {
    await page.keyboard.press("End");
    await sleep(page, 1200);
    await page.keyboard.press("Home");
    await sleep(page, 1200);
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press(i % 2 ? "Space" : "PageDown");
      await sleep(page, 350);
    }
    const t = await now(page);
    await sleep(page, 7000);
    return t;
  },
  // Cambiar el tamaño de la ventana en pleno viaje (girar el móvil, encoger la ventana).
  redimension: async (page) => {
    await wheel(page, Array(20).fill(700), 8);
    await sleep(page, 500);
    await page.setViewportSize(MOBILE);
    await sleep(page, 900);
    await page.setViewportSize({ width: 900, height: 500 });
    await sleep(page, 900);
    await page.setViewportSize(DESKTOP);
    const t = await now(page);
    await sleep(page, 8000);
    return t;
  },
};

async function runRoute(browser, route, report) {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));

  for (const [name, scenario] of Object.entries(SCENARIOS)) {
    await page.setViewportSize(DESKTOP);
    await page.goto(`${BASE}/recorrido/${route}`, { waitUntil: "networkidle" });
    await sleep(page, 600);
    await installRecorder(page);
    const info = await page.evaluate(() => ({
      maxRate: window.__journey.maxRate,
      total: window.__journey.total,
      rests: window.__journey.rests,
      triggers: window.__journey.triggers(),
    }));
    await page.mouse.move(700, 420);
    await record(page);
    if (name === "brusco") {
      // Capturas durante el golpe: lo que de verdad ve el usuario.
      const shots = (async () => {
        for (const ms of [250, 900, 2200, 5000]) {
          await sleep(page, ms === 250 ? 250 : ms - [250, 900, 2200, 5000][[250, 900, 2200, 5000].indexOf(ms) - 1]);
          await page.screenshot({ path: `${OUT}/r${route}-brusco-${ms}ms.jpg`, type: "jpeg", quality: 55 });
        }
      })();
      const lastInputAt = await scenario(page);
      await shots;
      report[`r${route}`][name] = { ...analyze(await stop(page), info, lastInputAt), ...(await coverage(page)), triggers: info.triggers };
    } else {
      const lastInputAt = await scenario(page);
      report[`r${route}`][name] = { ...analyze(await stop(page), info, lastInputAt), ...(await coverage(page)), triggers: info.triggers };
    }
  }
  report[`r${route}`].erroresConsola = errors;
  await context.close();
}

/** Móvil con pantalla táctil: deslizamientos rápidos de verdad (gesto sintetizado por el navegador). */
async function runTouch(browser, route, report) {
  const context = await browser.newContext({ viewport: MOBILE, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const page = await context.newPage();
  await page.goto(`${BASE}/recorrido/${route}`, { waitUntil: "networkidle" });
  await sleep(page, 600);
  await installRecorder(page);
  const info = await page.evaluate(() => ({ maxRate: window.__journey.maxRate, rests: window.__journey.rests }));
  const cdp = await context.newCDPSession(page);
  // Simula un móvil de gama media: procesador 4 veces más lento que este equipo.
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await record(page);
  // Cinco deslizamientos rápidos con eventos táctiles reales: 440 px en unos 70 ms cada uno.
  for (let i = 0; i < 5; i++) {
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 195, y: 640 }] });
    for (let y = 640; y >= 200; y -= 88) {
      await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: 195, y }] });
      await sleep(page, 12);
    }
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await sleep(page, 220);
  }
  const lastInputAt = await now(page);
  await sleep(page, 9000);
  const rows = await stop(page);
  await page.screenshot({ path: `${OUT}/r${route}-movil.jpg`, type: "jpeg", quality: 60 });
  // ¿Algo se sale de la pantalla o se tapa en móvil?
  const layout = await page.evaluate(() => {
    const vw = innerWidth;
    const overflowX = document.documentElement.scrollWidth > vw + 1;
    const cards = [...document.querySelectorAll("[data-overlay], [data-card]")].filter(
      (el) => getComputedStyle(el).visibility !== "hidden" && +getComputedStyle(el).opacity > 0.5,
    );
    const mascot = document.querySelector(".mascot")?.getBoundingClientRect();
    return {
      desbordeHorizontal: overflowX,
      tarjetas: cards.map((el) => {
        const r = el.getBoundingClientRect();
        const overlap = mascot
          ? Math.max(0, Math.min(r.right, mascot.right) - Math.max(r.left, mascot.left)) *
            Math.max(0, Math.min(r.bottom, mascot.bottom) - Math.max(r.top, mascot.top))
          : 0;
        return {
          fueraDePantalla: r.right > vw + 1 || r.left < -1,
          solapeConMascotaPct: Math.round((overlap / (r.width * r.height || 1)) * 100),
        };
      }),
    };
  });
  report[`r${route}`].tactil = { ...analyze(rows, info, lastInputAt), ...(await coverage(page)), ...layout };
  await context.close();
}

/** Recargar a mitad del recorrido: el navegador restaura el scroll y la escena debe coincidir de inmediato. */
async function runReload(browser, route, report) {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await page.goto(`${BASE}/recorrido/${route}`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__journey);
  await page.evaluate(() => scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * 0.55));
  await sleep(page, 6000);
  const before = await page.evaluate(() => +window.__journey.time().toFixed(2));
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__journey);
  await sleep(page, 400);
  const after = await page.evaluate(() => ({
    tiempo: +window.__journey.time().toFixed(2),
    desfase: +Math.abs(window.__journey.time() - window.__journey.target()).toFixed(3),
  }));
  await page.screenshot({ path: `${OUT}/r${route}-recarga.jpg`, type: "jpeg", quality: 55 });
  report[`r${route}`].recarga = { tiempoAntes: before, ...after };
  await context.close();
}

/** «Reducir movimiento»: sin viaje, todo el contenido debe seguir disponible. */
async function runReduced(browser, route, report) {
  const context = await browser.newContext({ viewport: DESKTOP, reducedMotion: "reduce" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${BASE}/recorrido/${route}`, { waitUntil: "networkidle" });
  await sleep(page, 500);
  report[`r${route}`].movimientoReducido = await page.evaluate(() => ({
    sinAnimacion: !window.__journey,
    secciones: document.querySelectorAll("main > section").length,
    lenisSuaviza: document.documentElement.classList.contains("lenis-smooth"),
    desbordeHorizontal: document.documentElement.scrollWidth > innerWidth + 1,
    altoPaginaVh: +(document.documentElement.scrollHeight / innerHeight).toFixed(1),
  }));
  report[`r${route}`].movimientoReducido.errores = errors;
  await page.screenshot({ path: `${OUT}/r${route}-reducido.jpg`, type: "jpeg", quality: 55 });
  await context.close();
}

// ---------- Como usuario: el flujo real de consulta, paso a paso ----------

/** Espera a que la animación alcance al scroll y se quede quieta. Devuelve cuánto tardó. */
async function settle(page, maxMs = 20000) {
  const t0 = Date.now();
  let calm = 0;
  while (Date.now() - t0 < maxMs) {
    const d = await page.evaluate(() => (window.__journey ? Math.abs(window.__journey.time() - window.__journey.target()) : 0));
    calm = d < 0.01 ? calm + 1 : 0;
    if (calm >= 4) return Date.now() - t0;
    await page.waitForTimeout(80);
  }
  return null;
}

const whereAmI = (page) =>
  page.evaluate(() => {
    const visible = (el) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return (
        cs.visibility !== "hidden" &&
        +cs.opacity > 0.6 &&
        r.width > 0 &&
        r.bottom > 0 &&
        r.top < innerHeight &&
        r.right > 0 &&
        r.left < innerWidth
      );
    };
    const card = [...document.querySelectorAll("[data-overlay]")].find(visible);
    const f = document.activeElement;
    return {
      parada: document.querySelector("[aria-current=step] .sr-only")?.textContent ?? null,
      tarjetaVisible: card ? card.innerText.split("\n")[0].slice(0, 40) : null,
      focoEn:
        f && f !== document.body
          ? `${f.tagName.toLowerCase()} «${(f.innerText || f.getAttribute("aria-label") || f.getAttribute("placeholder") || "").slice(0, 30)}»`
          : null,
      focoVisible: f && f !== document.body ? visible(f) : null,
      scrollPct: Math.round((scrollY / (document.documentElement.scrollHeight - innerHeight)) * 100),
    };
  });

async function runUserFlow(browser, report, viewport, tag, mobile = false) {
  const context = await browser.newContext({ viewport, ...(mobile ? { hasTouch: true, isMobile: true, deviceScaleFactor: 2 } : {}) });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const steps = [];
  const step = async (name, extra = {}) => {
    const state = await whereAmI(page);
    steps.push({ paso: name, ...state, ...extra });
    await page.screenshot({ path: `${OUT}/flujo-${tag}-${String(steps.length).padStart(2, "0")}.jpg`, type: "jpeg", quality: 60 });
  };
  const click = (locator) => (mobile ? locator.tap() : locator.click());

  const t0 = Date.now();
  await page.goto(`${BASE}/recorrido/1`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__journey);
  await step("1. Llega a la página", { cargaMs: Date.now() - t0 });

  // 2. El botón principal debe llevar a la siguiente parada con contenido, no dejar al usuario en un fondo vacío.
  await click(page.getByRole("button", { name: "Consultar sin cuenta" }));
  await step("2. Pulsa «Consultar sin cuenta»", { asentadoMs: await settle(page) });

  // 3. Si el botón no bastó, el usuario sigue bajando hasta ver el buscador.
  let extraScroll = 0;
  while (!(await page.getByRole("combobox", { name: "Municipio" }).isVisible()) && extraScroll < 60) {
    await page.mouse.wheel(0, 100);
    await page.waitForTimeout(110);
    extraScroll++;
  }
  await settle(page);
  await step("3. Ve el buscador de municipio", { golpesDeRuedaExtra: extraScroll });

  // 4. Escribe sin tildes y elige con Enter.
  const box = page.getByRole("combobox", { name: "Municipio" });
  let typed;
  try {
    await click(box);
    await page.keyboard.type("venta", { delay: 60 });
    await page.keyboard.press("Enter");
    typed = await box.inputValue();
    await settle(page);
  } catch (e) {
    typed = `error: ${String(e).slice(0, 80)}`;
  }
  await step("4. Escribe «venta» y elige: la cámara baja sola", { valorElegido: typed });

  // 5. Baja con la rueda hasta la parada del municipio.
  let wheels = 0;
  while (!(await page.getByRole("button", { name: "Ver diagnóstico" }).isVisible()) && wheels < 80) {
    await page.mouse.wheel(0, 100);
    await page.waitForTimeout(110);
    wheels++;
  }
  await settle(page);
  await step("5. Baja hasta su municipio", {
    golpesDeRueda: wheels,
    muestraSuEleccion: await page.getByRole("heading", { name: /Ventaquemada/ }).isVisible(),
  });

  // 6. Pide el diagnóstico: debe llegar al resultado.
  await click(page.getByRole("button", { name: "Ver diagnóstico" }));
  const settled = await settle(page);
  const result = page.getByText("Sugerencia: esperar otro semestre.");
  let more = 0;
  while (!(await result.isVisible()) && more < 60) {
    await page.mouse.wheel(0, 100);
    await page.waitForTimeout(110);
    more++;
  }
  await settle(page);
  await step("6. Pulsa «Ver diagnóstico»", { asentadoMs: settled, golpesDeRuedaExtra: more, veElResultado: await result.isVisible() });

  // 7. Se arrepiente y vuelve arriba de un golpe.
  await page.evaluate(() => scrollTo(0, 0));
  await step("7. Vuelve al inicio", { asentadoMs: await settle(page), conservaMunicipio: typed });

  report[`flujo-${tag}`] = { pasos: steps, errores: errors };
  await context.close();
}

/** Solo teclado: ¿se puede hacer la consulta sin ratón, y el foco siempre se ve? */
async function runKeyboardFlow(browser, report) {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await page.goto(`${BASE}/recorrido/1`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__journey);
  const trail = [];
  let invisible = 0;
  for (let i = 0; i < 14; i++) {
    await page.keyboard.press("Tab");
    await page.waitForTimeout(350);
    const w = await whereAmI(page);
    if (w.focoVisible === false) invisible++;
    trail.push(`${w.focoEn} ${w.focoVisible ? "" : "(NO VISIBLE)"} · ${w.parada}`);
    if (w.focoEn?.includes("Consultar sin cuenta")) {
      await page.keyboard.press("Enter");
      await settle(page);
      trail.push(`→ Enter · ahora en ${(await whereAmI(page)).parada}, tarjeta: ${(await whereAmI(page)).tarjetaVisible}`);
    }
  }
  await page.screenshot({ path: `${OUT}/flujo-teclado.jpg`, type: "jpeg", quality: 60 });
  report["flujo-teclado"] = { recorridoDelFoco: trail, focosInvisibles: invisible };
  await context.close();
}

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--disable-renderer-backgrounding", "--disable-background-timer-throttling"],
});
const report = {};
for (const route of ROUTES) {
  report[`r${route}`] = {};
  await runRoute(browser, route, report);
  await runTouch(browser, route, report);
  await runReduced(browser, route, report);
  await runReload(browser, route, report);
  console.log(`recorrido ${route}: listo`);
}
if (!process.env.SKIP_FLOWS) {
  await runUserFlow(browser, report, DESKTOP, "escritorio");
  await runUserFlow(browser, report, MOBILE, "movil", true);
  await runKeyboardFlow(browser, report);
  console.log("flujos de usuario: listo");
}
await browser.close();
writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
console.log(`Informe en ${OUT}/report.json`);
