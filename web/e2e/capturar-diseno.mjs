// Captura las láminas y pantallas de design/ con las fuentes reales, para revisarlas antes de mandarlas a Figma.
//
//   python -m http.server 8780 --directory design/pantallas      (en otra terminal)
//   node web/e2e/capturar-diseno.mjs <carpeta-de-salida> <zoom> <grupo1> [grupo2 ...]
//
// Cada grupo es una lista de pantallas separadas por comas; sale una imagen por grupo.

import { chromium } from "playwright-core";

const [out, zoom, ...groups] = process.argv.slice(2);
const BASE = process.env.BASE ?? "http://127.0.0.1:8780";

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await (await browser.newContext({ viewport: { width: 1600, height: 900 } })).newPage();
for (const [i, group] of groups.entries()) {
  await page.goto(`${BASE}/ver.html?z=${zoom}&f=${group}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/captura-${String(i + 1).padStart(2, "0")}.jpg`, type: "jpeg", quality: 70, fullPage: true });
}
await browser.close();
console.log(`${groups.length} capturas en ${out}`);
