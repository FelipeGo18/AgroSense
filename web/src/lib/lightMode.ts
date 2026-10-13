/**
 * Modo ligero (HU-158): la misma información, sin scroll suave, sin recorrido animado y sin movimiento.
 * Es el único interruptor de movimiento de la web: todo lo que se mueve (GSAP, Lenis, la Tierra que gira, la mascota
 * que vuela, animaciones y transiciones de CSS) mira este valor y se apaga con él. Ver `web/CLAUDE.md`.
 *
 * La preferencia es «on» (ligero), «off» (con movimiento) o «auto» (la que pide el equipo: `prefers-reduced-motion` o
 * ahorro de datos). Se guarda en este navegador. El valor efectivo se refleja en `<html data-light>`, y con eso el CSS
 * apaga toda animación y transición (`styles/index.css`) y Tailwind ofrece las variantes `light:` y `animated:`.
 */

export type LightPref = "on" | "off" | "auto";

const KEY = "agrosense:modo-ligero";
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const listeners = new Set<() => void>();

const hasWindow = () => typeof window !== "undefined";

const readPref = (): LightPref => {
  try {
    const stored = localStorage.getItem(KEY);
    return stored === "on" || stored === "off" ? stored : "auto";
  } catch {
    return "auto"; // sin almacenamiento (modo privado): se sigue al equipo
  }
};

/** Lo que pide el equipo: reducir movimiento o ahorrar datos. */
const systemWantsLight = () => {
  if (!hasWindow()) return false;
  const reduced = typeof matchMedia === "function" && matchMedia(REDUCED_MOTION).matches;
  const saveData = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData === true;
  return reduced || saveData;
};

const resolve = (pref: LightPref) => (pref === "auto" ? systemWantsLight() : pref === "on");

let pref: LightPref = hasWindow() ? readPref() : "auto";
let light = resolve(pref);

const apply = () => {
  if (hasWindow()) document.documentElement.toggleAttribute("data-light", light);
};

const refresh = () => {
  const next = resolve(pref);
  if (next === light) return;
  light = next;
  apply();
  listeners.forEach((listener) => listener());
};

/** Aplica la preferencia a `<html>` y sigue los cambios del equipo. Se llama una vez, antes de pintar la web. */
export function initLightMode() {
  if (!hasWindow()) return;
  pref = readPref();
  light = resolve(pref);
  apply();
  if (typeof matchMedia === "function") matchMedia(REDUCED_MOTION).addEventListener("change", refresh);
}

export const lightModeOn = () => light;
export const lightModePref = () => pref;

export function subscribeLightMode(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Elige modo ligero (`true`) o con movimiento (`false`) y lo recuerda. */
export function setLightMode(next: boolean) {
  pref = next ? "on" : "off";
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    /* sin almacenamiento: vale solo mientras la página esté abierta */
  }
  light = next;
  apply();
  listeners.forEach((listener) => listener());
}

/** Vuelve a seguir lo que pide el equipo. */
export function resetLightMode() {
  pref = "auto";
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ver arriba */
  }
  light = resolve(pref);
  apply();
  listeners.forEach((listener) => listener());
}
