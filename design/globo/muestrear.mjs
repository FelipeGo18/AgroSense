// Reduce la imagen Blue Marble (NASA Earth Observatory) a una malla RGB cruda de 720 × 360 (medio grado por píxel),
// para que build_globo.py tome el color de cada faceta sin depender de librerías de imagen.
//   node design/globo/muestrear.mjs     (usa playwright-core de web/)
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const { chromium } = require("playwright-core");

const dir = new URL("./fuente/", import.meta.url);
const jpg = readFileSync(new URL("blue-marble-200412.jpg", dir)).toString("base64");
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
const rgb = await page.evaluate(async (src) => {
  const img = new Image();
  img.src = src;
  await img.decode();
  const c = new OffscreenCanvas(720, 360);
  const g = c.getContext("2d");
  g.imageSmoothingQuality = "high";
  g.drawImage(img, 0, 0, 720, 360);
  const d = g.getImageData(0, 0, 720, 360).data;
  const out = [];
  for (let i = 0; i < d.length; i += 4) out.push(d[i], d[i + 1], d[i + 2]);
  return out;
}, `data:image/jpeg;base64,${jpg}`);
await browser.close();
writeFileSync(new URL("blue-marble-720x360.rgb", dir), Buffer.from(rgb));
console.log("blue-marble-720x360.rgb", rgb.length, "bytes");
