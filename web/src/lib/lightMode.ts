/**
 * Modo ligero de este dispositivo: sin animaciones, recorridos, GSAP ni Lenis. Para equipos lentos, datos escasos o
 * quien prefiere la página quieta. Se guarda en este navegador.
 *
 * Este módulo es solo el interruptor: dice si el modo está prendido y avisa cuando cambia. Qué se apaga lo decide
 * cada pieza a través de `useReducedMotion` (hooks/useReducedMotion.ts) y, para lo hecho con CSS, la clase
 * `modo-ligero` en `<html>`. Lo que el modo ligero apague de más (la escena 3D, imágenes pesadas) se engancha aquí.
 */

const KEY = "agrosense:modo-ligero";
const listeners = new Set<() => void>();

const read = () => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false; // sin almacenamiento (modo privado): apagado
  }
};

let enabled = typeof localStorage === "undefined" ? false : read();
const apply = () => typeof document !== "undefined" && document.documentElement.classList.toggle("modo-ligero", enabled);
apply();

export const lightModeEnabled = () => enabled;

export function subscribeLightMode(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setLightMode(next: boolean) {
  enabled = next;
  try {
    localStorage.setItem(KEY, next ? "1" : "0");
  } catch {
    // sin almacenamiento, la preferencia dura lo que dure la página
  }
  apply();
  listeners.forEach((listener) => listener());
}
