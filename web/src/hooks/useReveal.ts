import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef } from "react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/** De qué lado entra una pieza en la variante de lado: `data-reveal="right"` por la derecha; las demás, por la izquierda. */
const side = (_: number, el: Element) => ((el as HTMLElement).dataset.reveal === "right" ? 1 : -1);

/**
 * Cada sección entra y sale a su manera, siempre con poco recorrido: es un acento, no un espectáculo.
 * `from` es cómo espera la pieza antes de entrar; `out`, cómo se va cuando sale por arriba.
 */
const VARIANTS = {
  /** Sube y crece un poco; se va hacia arriba. */
  rise: {
    from: { y: 36, scale: 0.97, autoAlpha: 0 },
    out: { y: -22, autoAlpha: 0 },
    ease: "power2.out",
    stagger: 0.09,
  },
  /** Llega de lado, cada pieza desde el suyo, y se va por donde vino. */
  slide: {
    from: { x: (i: number, el: Element) => 44 * side(i, el), autoAlpha: 0 },
    out: { x: (i: number, el: Element) => 26 * side(i, el), autoAlpha: 0 },
    ease: "power3.out",
    stagger: 0.06,
  },
  /** Aparece creciendo con un giro mínimo, como una ficha que se pone en la mesa; se va hundiéndose. */
  pop: {
    from: { scale: 0.9, rotation: (i: number) => (i % 2 ? 1.6 : -1.6), autoAlpha: 0 },
    out: { scale: 0.96, y: 18, autoAlpha: 0 },
    ease: "back.out(1.5)",
    stagger: 0.08,
  },
} as const;

export type RevealVariant = keyof typeof VARIANTS;

const REST = { x: 0, y: 0, scale: 1, rotation: 0, autoAlpha: 1 };

/**
 * Anima la entrada y la salida de las piezas marcadas con `data-reveal` dentro de la sección, una tras otra,
 * a medida que cada una entra o sale de la pantalla. Apagado (con «reducir movimiento») no toca nada: el
 * contenido ya está en su sitio.
 */
export function useReveal<T extends HTMLElement>(enabled: boolean, variant: RevealVariant = "rise") {
  const scope = useRef<T>(null);
  useGSAP(
    () => {
      if (!enabled || !scope.current) return;
      const items = gsap.utils.toArray<HTMLElement>("[data-reveal]", scope.current);
      if (items.length === 0) return;
      const { from, out, ease, stagger } = VARIANTS[variant];
      const enter = (batch: Element[]) => gsap.to(batch, { ...REST, duration: 0.6, ease, stagger, overwrite: true });
      gsap.set(items, from);
      ScrollTrigger.batch(items, {
        start: "top 90%",
        end: "bottom 13%",
        onEnter: enter,
        onEnterBack: enter,
        onLeave: (batch) => gsap.to(batch, { ...out, duration: 0.35, ease: "power1.in", stagger: 0.04, overwrite: true }),
        onLeaveBack: (batch) => gsap.to(batch, { ...from, duration: 0.35, ease: "power1.in", stagger: 0.04, overwrite: true }),
      });
    },
    { scope, dependencies: [enabled, variant], revertOnUpdate: true },
  );
  return scope;
}
