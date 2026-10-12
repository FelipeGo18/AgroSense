import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { useEffect, useRef } from "react";

/** Mayor avance, en píxeles, que se acepta de un solo golpe de rueda. Un gesto brusco no salta varias paradas. */
const MAX_WHEEL_STEP = 110;

/** Inercia del scroll: fracción de la distancia que se recorre por cuadro. Más bajo, más suave y más lento. */
const LERP = 0.09;

/**
 * Scroll con inercia (Lenis), sincronizado con ScrollTrigger: la rueda del ratón deja de avanzar a saltos
 * y las líneas de tiempo atadas al scroll se mueven de forma continua. Integración recomendada por Lenis:
 * un solo ciclo (el de GSAP) y sin suavizado de retraso. Devuelve la instancia, o null si está apagado.
 */
export function useSmoothScroll(enabled: boolean) {
  const ref = useRef<Lenis | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const lenis = new Lenis({
      lerp: LERP,
      wheelMultiplier: 1,
      virtualScroll: (data) => {
        data.deltaY = Math.max(-MAX_WHEEL_STEP, Math.min(MAX_WHEEL_STEP, data.deltaY));
        return true;
      },
    });
    ref.current = lenis;
    lenis.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      ref.current = null;
      gsap.ticker.remove(tick);
      lenis.destroy();
    };
  }, [enabled]);
  return ref;
}
