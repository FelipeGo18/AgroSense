import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const KEY = "agrosense:modo-ligero";

/** Carga el módulo de cero, con o sin «reducir movimiento» en el equipo, para probar el arranque. */
async function load({ reduced = false, saveData = false }: { reduced?: boolean; saveData?: boolean } = {}) {
  vi.resetModules();
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduced && query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.stubGlobal("navigator", { connection: { saveData } });
  const mod = await import("./lightMode");
  mod.initLightMode();
  return mod;
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-light");
});
afterEach(() => vi.unstubAllGlobals());

describe("modo ligero (HU-158)", () => {
  it("sin preferencia y sin pedido del equipo, la web va con movimiento", async () => {
    const { lightModeOn, lightModePref } = await load();
    expect(lightModePref()).toBe("auto");
    expect(lightModeOn()).toBe(false);
    expect(document.documentElement).not.toHaveAttribute("data-light");
  });

  it("en automático sigue a «reducir movimiento» y al ahorro de datos", async () => {
    expect((await load({ reduced: true })).lightModeOn()).toBe(true);
    expect(document.documentElement).toHaveAttribute("data-light");
    expect((await load({ saveData: true })).lightModeOn()).toBe(true);
  });

  it("activarlo lo recuerda y marca <html>; desactivarlo gana a lo que pida el equipo", async () => {
    const { setLightMode, lightModeOn } = await load({ reduced: true });
    setLightMode(false);
    expect(lightModeOn()).toBe(false);
    expect(localStorage.getItem(KEY)).toBe("off");
    expect(document.documentElement).not.toHaveAttribute("data-light");
    setLightMode(true);
    expect(localStorage.getItem(KEY)).toBe("on");
    expect(document.documentElement).toHaveAttribute("data-light");
  });

  it("al volver a abrir la web respeta lo que se eligió", async () => {
    localStorage.setItem(KEY, "on");
    expect((await load()).lightModeOn()).toBe(true);
    localStorage.setItem(KEY, "off");
    expect((await load({ reduced: true })).lightModeOn()).toBe(false);
  });

  it("restablecer vuelve a seguir al equipo", async () => {
    const { setLightMode, resetLightMode, lightModePref, lightModeOn } = await load({ reduced: true });
    setLightMode(false);
    resetLightMode();
    expect(lightModePref()).toBe("auto");
    expect(localStorage.getItem(KEY)).toBeNull();
    expect(lightModeOn()).toBe(true);
  });

  it("avisa a quien escucha cuando cambia", async () => {
    const { setLightMode, subscribeLightMode } = await load();
    const listener = vi.fn();
    const stop = subscribeLightMode(listener);
    setLightMode(true);
    expect(listener).toHaveBeenCalledTimes(1);
    stop();
    setLightMode(false);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
