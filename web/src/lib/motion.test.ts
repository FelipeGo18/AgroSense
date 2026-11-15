import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/** Un motor de mentira: cuenta cuántas veces se pidió, sin traer GSAP ni Lenis. */
const engine = { gsap: { name: "gsap" }, ScrollTrigger: { name: "ScrollTrigger" }, Lenis: { name: "Lenis" } };
let requested = 0;

/** Carga de cero el modo ligero y el motor, con el modo ligero prendido o apagado por la persona. */
async function load({ light, fails = false }: { light: boolean; fails?: boolean }) {
  vi.resetModules();
  requested = 0;
  vi.doMock("./motionEngine", () => {
    requested += 1;
    if (fails) throw new Error("sin conexión");
    return engine;
  });
  const lightMode = await import("./lightMode");
  lightMode.initLightMode();
  lightMode.setLightMode(light);
  return { ...lightMode, ...(await import("./motion")) };
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.doUnmock("./motionEngine"));

describe("el motor del movimiento se carga aparte (HU-158)", () => {
  it("en modo ligero GSAP y Lenis no se descargan: ni al arrancar ni al abrir una página", async () => {
    const { initMotion, motionReady, motionLoaded } = await load({ light: true });
    initMotion();
    await motionReady();
    expect(requested).toBe(0);
    expect(motionLoaded()).toBe(false);
  });

  it("con movimiento, cada página espera al motor y lo encuentra listo", async () => {
    const { motionReady, motionLoaded, gsap } = await load({ light: false });
    expect(gsap).toBeUndefined();
    await motionReady();
    expect(motionLoaded()).toBe(true);
    const fresh = await import("./motion");
    expect(fresh.gsap).toBe(engine.gsap);
    expect(fresh.ScrollTrigger).toBe(engine.ScrollTrigger);
    expect(fresh.Lenis).toBe(engine.Lenis);
  });

  it("al apagar el modo ligero sin recargar se pide en ese momento, una sola vez", async () => {
    const { initMotion, motionLoaded, setLightMode, loadMotion } = await load({ light: true });
    initMotion();
    expect(requested).toBe(0);
    setLightMode(false);
    await loadMotion();
    setLightMode(true);
    setLightMode(false);
    await loadMotion();
    expect(requested).toBe(1);
    expect(motionLoaded()).toBe(true);
  });

  it("si el motor no llega (sin conexión), la página abre igual, quieta, y se puede volver a pedir", async () => {
    const { motionReady, motionLoaded, loadMotion } = await load({ light: false, fails: true });
    await expect(motionReady()).resolves.toBeUndefined();
    expect(motionLoaded()).toBe(false);
    await expect(loadMotion()).rejects.toThrow();
    expect(requested).toBe(2);
  });

  it("useAnimated() no se enciende hasta que el motor llegó: donde es verdadero, gsap ya existe", async () => {
    const { loadMotion } = await load({ light: false });
    const { renderHook, act } = await import("@testing-library/react");
    const { useAnimated } = await import("@/hooks/useLightMode");
    const { result } = renderHook(() => useAnimated());
    expect(result.current).toBe(false);
    await act(() => loadMotion());
    expect(result.current).toBe(true);
  });
});
