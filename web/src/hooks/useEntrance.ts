import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import { isFirstLoad } from "@/lib/firstLoad";
import { useReducedMotion } from "./useReducedMotion";

gsap.registerPlugin(useGSAP);

/**
 * Entrada de una página: las piezas marcadas con `data-enter` suben y aparecen una tras otra; las marcadas
 * `data-enter="pop"` (la mascota, los letreros) llegan después, creciendo con un rebote.
 *
 * Con `bold` la entrada se nota más: es la de los formularios (entrar, crear cuenta, cambiar contraseña), que son una
 * sola tarjeta sobre un paisaje. En las páginas largas es un acento corto.
 *
 * Sin movimiento (modo ligero) no toca nada: el contenido ya está en su sitio. Usa `opacity`, no `visibility`: lo que
 * entra se puede leer y enfocar desde el primer instante. Sobre HTML que ya venía pintado no se esconde nada: las
 * piezas solo se acomodan, sin desaparecer.
 */
export function useEntrance<T extends HTMLElement>({ bold = false }: { bold?: boolean } = {}) {
  const scope = useRef<T>(null);
  const animated = !useReducedMotion();
  useGSAP(
    () => {
      if (!animated || !scope.current) return;
      // Lo que la persona ya está viendo no se esconde para volver a mostrarlo: en ese caso solo hay movimiento.
      const fade = isFirstLoad() ? {} : { opacity: 0 };
      const all = gsap.utils.toArray<HTMLElement>("[data-enter]", scope.current);
      const pops = all.filter((el) => el.dataset.enter === "pop");
      const rises = all.filter((el) => el.dataset.enter !== "pop");
      const timeline = gsap.timeline();
      if (rises.length) {
        timeline.from(
          rises,
          bold
            ? { y: 46, scale: 0.96, ...fade, duration: 0.6, ease: "back.out(1.5)", stagger: 0.07, clearProps: "transform,opacity" }
            : { y: 16, ...fade, duration: 0.4, ease: "power2.out", stagger: 0.05, clearProps: "transform,opacity" },
        );
      }
      if (pops.length) {
        timeline.from(
          pops,
          bold
            ? {
                scale: 0.25,
                rotation: -14,
                y: 26,
                ...fade,
                duration: 0.9,
                ease: "elastic.out(1, 0.5)",
                stagger: 0.14,
                transformOrigin: "50% 100%",
                clearProps: "transform,opacity",
              }
            : {
                scale: 0.6,
                ...fade,
                duration: 0.45,
                ease: "back.out(1.8)",
                stagger: 0.08,
                transformOrigin: "50% 100%",
                clearProps: "transform,opacity",
              },
          bold ? 0.3 : 0.2,
        );
      }
    },
    { scope, dependencies: [animated] },
  );
  return scope;
}

/**
 * Una lista que crece (por ejemplo con «Ver más antiguos»): las filas entran en cascada, y cuando llegan más solo
 * entran las nuevas. `count` es cuántas filas hay ahora.
 */
export function useRowsEntrance<T extends HTMLElement>(count: number) {
  const list = useRef<T>(null);
  const seen = useRef(0);
  const animated = !useReducedMotion();
  useGSAP(
    () => {
      const rows = list.current ? Array.from(list.current.children).slice(seen.current) : [];
      seen.current = count;
      if (!animated || rows.length === 0) return;
      gsap.from(rows, { y: 12, opacity: 0, duration: 0.35, ease: "power2.out", stagger: 0.04, clearProps: "transform,opacity" });
    },
    { dependencies: [count, animated] },
  );
  return list;
}

/** Sacudida corta de lado a lado: la tarjeta dice que no, por ejemplo cuando la API rechaza lo enviado. */
export function shake(target: Element | null) {
  if (!target) return;
  gsap.fromTo(
    target,
    { x: 0 },
    { keyframes: { x: [0, -16, 14, -10, 7, -3, 0] }, duration: 0.55, ease: "power1.inOut", overwrite: true, clearProps: "transform" },
  );
}
