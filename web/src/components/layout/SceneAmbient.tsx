import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef, type CSSProperties } from "react";
import { useDayPhase } from "@/hooks/useDayPhase";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import type { DayPhase } from "@/lib/dayPhase";
import { playSound } from "@/lib/sound";

gsap.registerPlugin(useGSAP);

/** Aviso de que empezó (`detail: true`) o paró (`false`) la llovizna del paisaje. */
export const RAIN_EVENT = "agrosense:lluvia";

/** Con qué se tiñe el paisaje a cada hora. Se multiplica sobre el dibujo: de día no hay tinte. */
const TINT: Record<DayPhase, string | null> = {
  dawn: "linear-gradient(#F7C9D3, #FFE9CF)",
  day: null,
  dusk: "linear-gradient(#FFC3A0, #FFE6C2)",
  night: "linear-gradient(#1A2850, #3A4C86)",
};

// Posiciones fijas (en % de la pantalla): el cielo de noche es siempre el mismo, no cambia en cada visita.
const STARS = [
  [6, 9], [14, 22], [23, 6], [31, 17], [38, 28], [47, 8], [55, 20], [63, 5], [71, 26], [79, 12], [88, 21], [95, 7],
  [10, 34], [44, 36], [84, 33],
]; // prettier-ignore
const FIREFLIES = [
  [8, 62], [19, 78], [33, 68], [46, 84], [58, 64], [69, 80], [81, 70], [92, 86],
]; // prettier-ignore

/**
 * Ambiente de un paisaje. Va detrás de todo: nunca tapa el contenido ni recibe el puntero. Por defecto cubre la
 * pantalla, detrás de la página (los formularios); con `contained` llena solo la caja que lo contiene (la franja de
 * Mi cuenta), y va justo después del dibujo del paisaje.
 *
 * - **Hora del día** (según el reloj del dispositivo): amanecer, día, atardecer o noche, con estrellas y luna. Esto
 *   no es movimiento y se ve siempre.
 * - **Con movimiento permitido:** sombras de nubes que cruzan el campo, unos pájaros de vez en cuando, luciérnagas de
 *   noche y, cada tanto, una llovizna que dura de unos segundos a casi medio minuto.
 *
 * Es decoración, no un dato: la llovizna y la hora no dicen cómo está el clima de ninguna zona (eso es HU-176, con su
 * rótulo y su fuente) y nada de esto entra a un cálculo (decisión 7).
 */
export function SceneAmbient({ contained = false }: { contained?: boolean }) {
  const place = contained ? "absolute inset-0" : "fixed inset-0 -z-10";
  const layer = useRef<HTMLDivElement>(null);
  const animated = !useReducedMotion();
  const phase = useDayPhase();
  const night = phase === "night";
  const tint = TINT[phase];

  useGSAP(
    (_context, contextSafe) => {
      const root = layer.current;
      if (!animated || !root || !contextSafe) return;
      const quiet = () => document.hidden || document.activeElement?.matches("input, textarea, select") === true;

      const birds = gsap.utils.toArray<HTMLElement>("[data-bird]", root);
      const flyBirds = contextSafe(() => {
        const fromLeft = Math.random() < 0.5;
        const width = root.clientWidth;
        const top = gsap.utils.random(0.14, 0.3) * root.clientHeight;
        playSound("chirp");
        birds.forEach((bird, i) => {
          const lag = i * 26;
          gsap.set(bird, { autoAlpha: 1, y: top + (i % 2 ? 14 : 0), scaleX: fromLeft ? 1 : -1 });
          gsap.fromTo(
            bird,
            { x: fromLeft ? -60 - lag : width + 60 + lag },
            { x: fromLeft ? width + 60 : -60, duration: 11, ease: "none", onComplete: () => gsap.set(bird, { autoAlpha: 0 }) },
          );
          gsap.fromTo(bird, { scaleY: 1 }, { scaleY: 0.35, duration: 0.28, yoyo: true, repeat: 39, ease: "sine.inOut" });
        });
      });

      const drizzle = root.querySelector("[data-drizzle]");
      // Cada llovizna dura distinto: a veces pasa rápido, a veces se queda un rato. Avisa cuándo empieza y cuándo
      // para (`RAIN_EVENT`), para que la mascota se moje y después se sacuda (SceneLife).
      const tell = (raining: boolean) => document.dispatchEvent(new CustomEvent(RAIN_EVENT, { detail: raining }));
      let raining = false;
      const rain = contextSafe(() => {
        const seconds = gsap.utils.random(9, 28);
        playSound("drizzle", seconds);
        raining = true;
        tell(true);
        gsap
          .timeline({
            onComplete: () => {
              raining = false;
              tell(false);
            },
          })
          .fromTo(drizzle, { autoAlpha: 0 }, { autoAlpha: 0.6, duration: 1.5, ease: "none" })
          .to(drizzle, { autoAlpha: 0, duration: 2, ease: "none" }, seconds - 2);
      });

      const every = contextSafe((first: number, [min, max]: [number, number], run: () => void) => {
        const again = contextSafe((seconds: number) => {
          gsap.delayedCall(seconds, () => {
            if (quiet()) return again(5);
            run();
            again(gsap.utils.random(min, max));
          });
        });
        again(first);
      });
      // De noche los pájaros duermen.
      if (!night) every(gsap.utils.random(12, 20), [35, 70], flyBirds);
      every(gsap.utils.random(45, 75), [90, 150], rain);
      // Si la capa se desmonta lloviendo, la lluvia también para para quien la escucha.
      return () => {
        if (raining) tell(false);
      };
    },
    { scope: layer, dependencies: [animated, night], revertOnUpdate: true },
  );

  return (
    <>
      {/* El tinte se multiplica sobre el paisaje: por eso es una capa aparte, hermana suya, y no va dentro de la del ambiente. */}
      {tint && <div aria-hidden="true" className={`pointer-events-none mix-blend-multiply ${place}`} style={{ backgroundImage: tint }} />}
      <div ref={layer} aria-hidden="true" data-phase={phase} className={`pointer-events-none overflow-hidden ${place}`}>
        {night && (
          <>
            {STARS.map(([x, y], i) => (
              <span
                key={i}
                className={`absolute size-[3px] rounded-full bg-white ${animated ? "star-twinkle" : ""}`}
                style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${(i % 5) * 0.7}s` }}
              />
            ))}
            <span className="absolute top-[18%] right-[6%] size-12 rounded-full bg-[#FFF6D8] shadow-[0_0_40px_10px_rgb(255_246_216/0.35)]" />
          </>
        )}
        {animated && (
          <>
            {!night &&
              [
                { top: "52%", width: "42vw", delay: "-20s", time: "80s" },
                { top: "70%", width: "56vw", delay: "-62s", time: "105s" },
              ].map((cloud) => (
                <span
                  key={cloud.top}
                  className="cloud-shadow absolute left-0 h-[16vh] rounded-[50%] bg-paleta-noche/15 blur-2xl"
                  style={{ top: cloud.top, width: cloud.width, animationDelay: cloud.delay, animationDuration: cloud.time }}
                />
              ))}
            {night &&
              FIREFLIES.map(([x, y], i) => (
                <span
                  key={i}
                  className="firefly absolute size-[5px] rounded-full bg-[#F4F79A] shadow-[0_0_8px_3px_rgb(244_247_154/0.7)]"
                  style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${i * 0.9}s` } as CSSProperties}
                />
              ))}
            {[0, 1, 2].map((bird) => (
              <svg key={bird} data-bird viewBox="0 0 24 10" className="invisible absolute top-0 left-0 h-[10px] w-6 overflow-visible">
                <path d="M1 8 Q7 0 12 7 Q17 0 23 8" fill="none" stroke="#1D1D1B" strokeWidth="2.2" strokeLinecap="round" />
              </svg>
            ))}
            <div data-drizzle className="drizzle invisible absolute inset-0" />
          </>
        )}
      </div>
    </>
  );
}
