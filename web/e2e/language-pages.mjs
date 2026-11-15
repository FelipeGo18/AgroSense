// HU-233: pantallas bilingües con respuestas de ejemplo, sin tocar cuentas ni bases de datos reales.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const base = process.env.BASE ?? "http://localhost:5190";
const examples = JSON.parse(readFileSync(new URL("../src/mocks/examples.json", import.meta.url), "utf8"));
const yearMonth = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota", year: "numeric", month: "2-digit" }).format(new Date());
const profile = {
  user_id: "hu233",
  username: "example",
  display_name: "Example",
  role: "farmer",
  consent_version: 3,
  consent_at: "2026-10-11T12:00:00Z",
  created_at: "2026-10-11T12:00:00Z",
  priorities: null,
};
const lot = {
  lot_id: "a1",
  municipality_id: "15646",
  name: "Example plot",
  geometry: null,
  area_ha: 2.5,
  irrigated: false,
  created_at: "2026-10-11T12:00:00Z",
  updated_at: "2026-10-11T12:00:00Z",
};
const season = {
  season_id: "s1",
  lot_id: "a1",
  crop_id: "papa",
  area_ha: 1.5,
  follows_season_ids: [],
  sowing_date: "2026-08-01",
  harvest_date: null,
  diagnosis_light: null,
  diagnosis_light_default: null,
  diagnosis_action: null,
  diagnosis_weights: null,
  diagnosis_irrigated: null,
  dataset_version: null,
  rules_version: null,
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
  days_since_sowing: 60,
  stage: "development",
  stage_progress_pct: 50,
  stage_method: "calendar",
  harvest_estimate: "2027-01-01",
  harvest_basis: "calendar",
  harvest_due: false,
};
const strategyPath = `/consultar?municipio=15646&siembra=${yearMonth}&anterior=papa&riego=no&ciclos=3`;
const allCases = [
  [false, "/entrar"],
  [false, "/crear-cuenta"],
  [false, "/consultar"],
  [false, strategyPath],
  [false, `${strategyPath}&estrategia=avena_vicia-arveja-papa&ciclo=2`],
  [false, `/diagnostico?municipio=15646&cultivo=papa&siembra=${yearMonth}&riego=no`],
  [false, "/que-cambio?municipio=15646&cultivo=papa"],
  [false, "/precios"],
  [false, "/como-funciona"],
  [false, "/politica-de-datos"],
  [false, "/ruta-que-no-existe"],
  [true, "/mi-cuenta"],
  [true, "/mi-cuenta/contrasena"],
  [true, "/mi-cuenta/actividad"],
  [true, "/mi-finca"],
  [true, "/mi-finca/agregar"],
  [true, "/mi-finca/lotes/a1"],
  [true, "/mi-finca/lotes/a1/editar"],
  [true, "/mi-finca/lotes/a1/sembrar"],
  [true, "/mi-finca/lotes/a1/siembras/s1/editar"],
  [true, "/mi-finca/lotes/a1/siembras/s1/cosechar"],
];
const cases = process.env.ROUTES ? allCases.filter(([, path]) => process.env.ROUTES.split(",").includes(path)) : allCases;
const browser = await chromium.launch({ channel: "chrome", headless: true });
let checked = 0;
try {
  for (const language of process.env.TEST_LANGUAGE ? [process.env.TEST_LANGUAGE] : ["es", "en"]) {
    for (const reducedMotion of ["reduce", "no-preference"]) {
      const context = await browser.newContext({ reducedMotion });
      await context.addInitScript(
        ({ examples, profile, lot, season, language }) => {
          localStorage.setItem("agrosense:language", language);
          sessionStorage.setItem("agrosense.area", "1,26");
          const original = window.fetch.bind(window);
          window.fetch = async (input, init) => {
            const url = new URL(input instanceof Request ? input.url : String(input), location.href);
            if (!url.pathname.startsWith("/api/v1/")) return original(input, init);
            const path = url.pathname.slice(7);
            let data;
            if (path === "/me") {
              if (!sessionStorage.getItem("hu233:signedIn"))
                return Response.json({ error: { code: "unauthorized", message: "Inicie sesión para continuar." } }, { status: 401 });
              data = profile;
            } else if (path === "/me/activity") data = { items: [], next_before: null };
            else if (path === "/lots") data = [{ ...lot, current_crop_ids: ["papa"] }];
            else if (path === "/lots/a1") data = { ...lot, soil: null, current_seasons: [season] };
            else if (path === "/lots/a1/seasons") data = [season];
            else if (path === "/catalogs/municipalities") data = examples.catalogs.municipalities;
            else if (path === "/catalogs/crops") data = examples.catalogs.crops;
            else if (path === "/version") data = examples.catalogs.version;
            else if (path.endsWith("/soil")) data = examples.routes["GET /catalogs/municipalities/{municipality_id}/soil"].ok.ejemplo;
            else if (path === "/diagnostics") data = examples.routes["POST /diagnostics"].ok.favorable;
            else if (path === "/rotations") data = examples.routes["POST /rotations"].ok.estrategias;
            else if (path === "/water-plans") data = examples.routes["POST /water-plans"].ok.plan;
            else if (path === "/changes") data = examples.routes["GET /changes"].ok.cambios;
            else if (path === "/trends") data = examples.routes["GET /trends"].ok.series;
            else if (path === "/market/prices")
              data = {
                version: "example",
                updated_at: "2026-10-11T12:00:00Z",
                market: { market_id: "1", name: "Example market" },
                markets: [{ market_id: "1", name: "Example market" }],
                date: "2026-10-11",
                source_id: "example",
                citation: null,
                products: [],
              };
            else return Response.json({ error: { code: "dataset_unavailable", message: "Sin datos de ejemplo" } }, { status: 503 });
            return Response.json(data);
          };
        },
        { examples, profile, lot, season, language },
      );
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      for (const width of process.env.WIDTHS ? process.env.WIDTHS.split(",").map(Number) : [320, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 800 });
        for (const [signedIn, path] of cases) {
          await page.goto(`${base}/`);
          await page.evaluate((signedIn) => {
            if (signedIn) sessionStorage.setItem("hu233:signedIn", "yes");
            else sessionStorage.removeItem("hu233:signedIn");
          }, signedIn);
          const url = new URL(path, base);
          url.searchParams.set("lang", language);
          await page.goto(url.href);
          await page.getByRole("heading", { level: 1 }).first().waitFor();
          await page.evaluate(() => document.fonts.ready);
          await page.waitForTimeout(500);
          const text = await page.locator("body").innerText();
          assert.doesNotMatch(text, /Unexpected Application Error|Application error/i, `${path}: error de renderizado`);
          assert.doesNotMatch(text, /\b(?:pages|features|components|pending)\.[A-Za-z]/, `${path}: clave sin traducir`);
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
          if (overflow) {
            mkdirSync(new URL("results/", import.meta.url), { recursive: true });
            await page.screenshot({
              path: new URL("results/language-overflow.png", import.meta.url).pathname.replace(/^\/(\w:)/, "$1"),
              fullPage: true,
            });
            console.log(
              await page.evaluate(() => ({
                viewport: innerWidth,
                client: document.documentElement.clientWidth,
                scroll: document.documentElement.scrollWidth,
                elements: [...document.querySelectorAll("body *")]
                  .filter((el) => {
                    const b = el.getBoundingClientRect();
                    return b.width && (b.left < -1 || b.right > document.documentElement.clientWidth + 1);
                  })
                  .slice(0, 8)
                  .map((el) => ({
                    tag: el.tagName,
                    class: el.className,
                    text: el.textContent?.slice(0, 70),
                    width: el.getBoundingClientRect().width,
                  })),
              })),
            );
          }
          assert.equal(overflow, false, `${path}, ${language}, ${width}px: desborde horizontal`);
          assert.equal(await page.locator("html").getAttribute("lang"), language);
          assert.deepEqual(errors, [], `${path}: errores de página`);
          if (path === "/consultar" && language === "en" && reducedMotion === "reduce" && width === 1024) {
            const area = page.getByLabel("Land area, in hectares", { exact: true });
            await area.fill("2.5");
            await page.getByRole("combobox", { name: "Language", exact: true }).selectOption("es");
            assert.equal(await page.getByLabel("Área del terreno, en hectáreas", { exact: true }).inputValue(), "2.5");
            await page.getByRole("combobox", { name: "Idioma", exact: true }).selectOption("en");
            assert.equal(await area.inputValue(), "2.5");
          }
          checked++;
        }
      }
      await context.close();
      console.log(`${language}, ${reducedMotion}: pantallas comprobadas (${checked} combinaciones acumuladas).`);
    }
  }
  console.log(`HU-233: ${checked} combinaciones de pantallas, idioma, tamaño y movimiento sin errores.`);
} finally {
  await browser.close();
}
