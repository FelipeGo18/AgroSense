// HU-233: portada, persistencia, menú móvil y arranque sobre HTML prerenderizado.
// BASE=http://localhost:5190 node e2e/language-check.mjs (también contra vite preview).
import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const base = process.env.BASE ?? "http://localhost:5190";
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1024, height: 768 }, reducedMotion: "reduce" });
  await context.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/me") {
      await route.fulfill({
        json: {
          user_id: "hu233",
          username: "ejemplo",
          display_name: "Nombre largo de prueba",
          role: "farmer",
          consent_version: 3,
          priorities: null,
        },
      });
    } else await route.fulfill({ status: 503, json: { detail: "Sin datos" } });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && /hydrat|mismatch/i.test(message.text())) errors.push(message.text());
  });
  await page.goto(`${base}/?lang=en`);
  await page.getByRole("link", { name: "Explore without an account", exact: true }).waitFor();
  assert.equal(await page.locator("html").getAttribute("lang"), "en");
  assert.match(await page.title(), /What to plant/);
  assert.equal(
    await page.getByRole("link", { name: "Explore without an account", exact: true }).getAttribute("href"),
    "/consultar?lang=en",
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  for (const width of [1024, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 768 });
    const overlap = await page.locator("header > div").evaluate((bar) => {
      const right = bar.querySelector(":scope > div:last-child").getBoundingClientRect();
      return [...bar.querySelectorAll("nav a")].some((link) => {
        const box = link.getBoundingClientRect();
        return box.width > 0 && box.right > right.left;
      });
    });
    assert.equal(overlap, false, `La navegación con sesión se superpone a ${width}px`);
  }
  await page.reload();
  await page.getByRole("link", { name: "Explore without an account", exact: true }).waitFor();
  await page.goto(`${base}/`);
  await page.getByRole("link", { name: "Explore without an account", exact: true }).waitFor();
  await page.setViewportSize({ width: 320, height: 568 });
  await page.getByRole("button", { name: "Open menu" }).click();
  const menu = page.getByRole("dialog");
  const selector = menu.getByRole("combobox", { name: "Language" });
  const box = await selector.boundingBox();
  assert.ok(box.width >= 44 && box.height >= 44);
  await selector.selectOption("es");
  await menu.getByRole("button", { name: "Cerrar el menú" }).click();
  await page.getByRole("link", { name: "Consultar sin cuenta", exact: true }).waitFor();
  assert.equal(await page.locator("html").getAttribute("lang"), "es");
  assert.equal(await page.evaluate(() => localStorage.getItem("agrosense:language")), "es");
  assert.equal(new URL(page.url()).searchParams.has("lang"), false);
  assert.deepEqual(errors, []);
  await context.close();
  console.log("HU-233: portada, sesión, persistencia y menú móvil sin problemas.");
} finally {
  await browser.close();
}
