// Auditoría de rendimiento confiable: mide el build de producción, nunca el servidor de desarrollo.
//
//   npm run perf                     (hace el build, lo sirve comprimido y corre Lighthouse)
//   npm run perf -- --sin-build      (usa el dist/ que ya hay)
//   npm run perf -- --pasadas=5      (más pasadas por caso; por defecto 3)
//
// Cada caso (página × dispositivo × con o sin movimiento) se mide varias veces y cuenta la mediana: una sola pasada
// engaña. El «móvil» es el de Lighthouse: un teléfono de gama media con 4G lento, simulado. Si algún caso baja de su
// presupuesto, el comando termina con error. Escribe e2e/results/perf.json.
//
// El servidor de aquí comprime con gzip, como cualquier alojamiento. Sin compresión los números salen peores de lo
// que verá la gente: `vite preview` no comprime y `npm run dev` sirve el código sin empaquetar.

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { gzipSync } from "node:zlib";
import * as chromeLauncher from "chrome-launcher";
import lighthouse from "lighthouse";
import desktopConfig from "lighthouse/core/config/desktop-config.js";

const args = process.argv.slice(2);
const RUNS = Number(args.find((a) => a.startsWith("--pasadas="))?.split("=")[1] ?? 3);
const PORT = 4179;
const DIST = "dist";

const PAGES = { Inicio: "/", Entrar: "/entrar" };
/** Nota mínima de Lighthouse y bloqueo máximo (ms) por dispositivo. Súbalos cuando el producto mejore; no los baje para pasar. */
const BUDGET = { movil: { score: 95, tbt: 200 }, escritorio: { score: 95, tbt: 150 } };
/** Tope del JavaScript que se descarga al abrir una página, comprimido (kB). */
const JS_BUDGET_KB = 200; // la meta de specs/05-frontend.md

if (!args.includes("--sin-build")) execSync("npm run build", { stdio: "inherit" });

// ---------- Servidor de dist/: gzip, caché larga para /assets y el cascarón para las rutas sin HTML propio ----------
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
};
const cache = new Map();
const server = createServer((request, response) => {
  const path = normalize(decodeURIComponent(new URL(request.url, "http://x").pathname)).replace(/^[\\/]+/, "");
  let file = join(DIST, path);
  // Como debe hacerlo el alojamiento: la página dibujada en el build si existe; si no, el cascarón vacío de la app.
  if (file.startsWith(DIST) && existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!file.startsWith(DIST) || !existsSync(file)) file = join(DIST, "app.html");
  const type = TYPES[extname(file)] ?? "application/octet-stream";
  const compress = !/woff/.test(type) && /gzip/.test(request.headers["accept-encoding"] ?? "");
  const key = file + compress;
  if (!cache.has(key)) cache.set(key, compress ? gzipSync(readFileSync(file)) : readFileSync(file));
  response.writeHead(200, {
    "Content-Type": type,
    "Cache-Control": file.includes("assets") ? "public, max-age=31536000, immutable" : "no-cache",
    ...(compress ? { "Content-Encoding": "gzip" } : {}),
  });
  response.end(cache.get(key));
});
await new Promise((ready) => server.listen(PORT, ready));

// ---------- Lighthouse ----------
const median = (values) => values.slice().sort((a, b) => a - b)[Math.floor(values.length / 2)];

async function measure(url, device, motion) {
  const flags = ["--headless=new", ...(motion ? [] : ["--force-prefers-reduced-motion"])];
  const runs = [];
  for (let i = 0; i < RUNS; i++) {
    const chrome = await chromeLauncher.launch({ chromeFlags: flags });
    try {
      const result = await lighthouse(
        url,
        { port: chrome.port, onlyCategories: ["performance"], logLevel: "error" },
        device === "escritorio" ? desktopConfig : undefined,
      );
      const audits = result.lhr.audits;
      const js = audits["network-requests"].details.items
        .filter((item) => item.resourceType === "Script")
        .reduce((sum, item) => sum + item.transferSize, 0);
      runs.push({
        score: Math.round(result.lhr.categories.performance.score * 100),
        fcp: audits["first-contentful-paint"].numericValue,
        lcp: audits["largest-contentful-paint"].numericValue,
        tbt: audits["total-blocking-time"].numericValue,
        cls: audits["cumulative-layout-shift"].numericValue,
        js,
      });
    } finally {
      await chrome.kill();
    }
  }
  const pick = (key) => median(runs.map((run) => run[key]));
  return {
    scores: runs.map((run) => run.score),
    score: pick("score"),
    fcp: pick("fcp"),
    lcp: pick("lcp"),
    tbt: pick("tbt"),
    cls: pick("cls"),
    js: pick("js"),
  };
}

const rows = [];
const failures = [];
for (const device of ["escritorio", "movil"]) {
  for (const motion of [true, false]) {
    for (const [page, path] of Object.entries(PAGES)) {
      const m = await measure(`http://localhost:${PORT}${path}`, device, motion);
      const label = `${device} · ${page} · ${motion ? "con" : "sin"} movimiento`;
      rows.push({
        caso: label,
        nota: m.score,
        pasadas: m.scores.join("/"),
        "primer pintado (s)": (m.fcp / 1000).toFixed(1),
        "contenido principal (s)": (m.lcp / 1000).toFixed(1),
        "bloqueo (ms)": Math.round(m.tbt),
        CLS: m.cls.toFixed(3),
        "JS (kB)": Math.round(m.js / 1024),
      });
      const budget = BUDGET[device];
      if (m.score < budget.score) failures.push(`${label}: nota ${m.score}, mínimo ${budget.score}`);
      if (m.tbt > budget.tbt) failures.push(`${label}: bloqueo ${Math.round(m.tbt)} ms, máximo ${budget.tbt}`);
      if (m.js / 1024 > JS_BUDGET_KB) failures.push(`${label}: JavaScript ${Math.round(m.js / 1024)} kB, máximo ${JS_BUDGET_KB}`);
    }
  }
}
server.close();

console.table(rows);
mkdirSync("e2e/results", { recursive: true });
writeFileSync(
  "e2e/results/perf.json",
  JSON.stringify({ fecha: new Date().toISOString(), pasadas: RUNS, presupuesto: { ...BUDGET, jsKB: JS_BUDGET_KB }, casos: rows }, null, 2),
);
if (failures.length) {
  console.error("\nFuera de presupuesto:\n" + failures.map((line) => "  - " + line).join("\n"));
  process.exit(1);
}
console.log("\nTodo dentro del presupuesto.");
