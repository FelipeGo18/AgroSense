/**
 * Preferencia «Reducir movimiento» de este dispositivo. Se suma a la del sistema: si el equipo ya pide reducir
 * movimiento, se respeta siempre; esta preferencia solo sirve para pedirlo aunque el equipo no lo haga.
 * Se guarda en este navegador. La clase `reduce-motion` en `<html>` apaga también las animaciones hechas con CSS.
 */

const KEY = "agrosense:reducir-movimiento";
const listeners = new Set<() => void>();

const read = () => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
};

let reduced = typeof localStorage === "undefined" ? false : read();
const apply = () => typeof document !== "undefined" && document.documentElement.classList.toggle("reduce-motion", reduced);
apply();

export const motionReduced = () => reduced;

export function subscribeMotion(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setMotionReduced(next: boolean) {
  reduced = next;
  try {
    localStorage.setItem(KEY, next ? "1" : "0");
  } catch {
    // sin almacenamiento, la preferencia dura lo que dure la página
  }
  apply();
  listeners.forEach((listener) => listener());
}
