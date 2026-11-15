import { useRef, type ReactNode } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { RAIN_EVENT } from "@/components/layout/SceneAmbient";
import { playSound } from "@/lib/sound";
import { useMotionEffect } from "@/hooks/useMotionEffect";
import { gsap } from "@/lib/motion";

/**
 * Vida alrededor de la mascota: de vez en cuando pasa una mariposa o sopla el viento, y la mascota reacciona.
 *
 * Envuelve un trozo de escena que contenga una `Mascot`; quien lo usa le da la posición (`relative` o `absolute`).
 * Lo que pasa:
 * - **Mariposa:** cruza con vuelo ondulado; la mascota la sigue con la mirada y se inclina hacia ella. Una de cada
 *   tres veces se le posa en el brote unos segundos.
 * - **Llovizna** (la del paisaje, `SceneAmbient`): mientras llueve la mascota se moja: le escurren gotas, se le cae
 *   el brote y entrecierra los ojos. Cuando para, se sacude el agua como un perro y las gotas salen volando.
 * - **Viento:** pasan unos trazos de aire; el brote se dobla, las raíces se van hacia atrás, entrecierra los ojos y
 *   los letreros marcados con `data-sway` se mecen. Después todo vuelve con un rebote.
 *
 * Es decoración: no recibe el puntero ni la leen los lectores de pantalla. No ocurre mientras se escribe en un
 * campo, con la pestaña en segundo plano, con «reducir movimiento» ni con el modo ligero.
 */
export function SceneLife({ children, className = "relative" }: { children: ReactNode; className?: string }) {
  const stage = useRef<HTMLDivElement>(null);
  const animated = !useReducedMotion();

  useMotionEffect(
    (_context, contextSafe) => {
      const root = stage.current;
      const mascot = root?.querySelector<SVGSVGElement>(".mascot");
      if (!animated || !root || !mascot || !contextSafe) return;
      const butterfly = root.querySelector<HTMLElement>("[data-butterfly]")!;
      const streaks = gsap.utils.toArray<HTMLElement>("[data-streak]", root);
      const gaze = mascot.querySelector(".mascot-gaze");
      const sprout = mascot.querySelector(".mascot-sprout");
      const roots = mascot.querySelector(".mascot-roots");
      let busy = false;
      let wet = false;
      let dripping: gsap.core.Tween[] = [];
      const drips = gsap.utils.toArray<HTMLElement>("[data-drip]", root);
      const splashes = gsap.utils.toArray<HTMLElement>("[data-splash]", root);
      const hidden = () => mascot.getClientRects().length === 0;

      /** Dónde está un punto de la mascota (en sus unidades de dibujo, 300 × 250) dentro de la escena, en píxeles. */
      const spot = (ux: number, uy: number) => {
        const box = mascot.getBoundingClientRect();
        const frame = root.getBoundingClientRect();
        return { x: box.left - frame.left + (ux / 300) * box.width, y: box.top - frame.top + (uy / 250) * box.height, size: box.width };
      };

      /** La mascota mira hacia la mariposa mientras vuela. */
      const follow = () => {
        if (mascot.hasAttribute("data-acting")) return;
        const eyes = spot(161, 116);
        const dx = gsap.getProperty(butterfly, "x") as number;
        const dy = gsap.getProperty(butterfly, "y") as number;
        const angle = Math.atan2(dy - eyes.y, dx - eyes.x);
        gsap.set(gaze, { x: Math.cos(angle) * 5, y: Math.sin(angle) * 4 });
        gsap.set(mascot, { rotation: Math.cos(angle) * 2.5 });
      };
      const settle = () => {
        gsap.to(gaze, { x: 0, y: 0, duration: 0.4, ease: "power2.out" });
        gsap.to(mascot, { rotation: 0, duration: 0.5, ease: "power2.out" });
      };

      const flyButterfly = contextSafe(() => {
        const width = root.clientWidth;
        const top = spot(158, 6);
        const lands = Math.random() < 1 / 3;
        const fromLeft = Math.random() < 0.5;
        const [startX, endX] = fromLeft ? [-40, width + 40] : [width + 40, -40];
        const cruise = Math.max(12, top.y - top.size * 0.12);
        busy = true;
        playSound("flutter");
        gsap.set(butterfly, { x: startX, y: cruise, autoAlpha: 1, scaleX: fromLeft ? 1 : -1 });
        // El aleteo y el sube y baja van aparte, todo el vuelo.
        const flap = gsap.to(butterfly.querySelectorAll("[data-wing]"), {
          scaleX: 0.25,
          duration: 0.11,
          yoyo: true,
          repeat: -1,
          ease: "sine.inOut",
        });
        const bob = gsap.to(butterfly, { yPercent: 70, duration: 0.55, yoyo: true, repeat: -1, ease: "sine.inOut" });
        const timeline = gsap.timeline({
          onUpdate: follow,
          onComplete: () => {
            flap.kill();
            bob.kill();
            gsap.set(butterfly, { autoAlpha: 0, yPercent: 0 });
            settle();
            busy = false;
          },
        });
        if (lands) {
          // Se posa en el brote: la mascota se queda quieta, contenta, y la mariposa aletea despacio.
          timeline
            .to(butterfly, { x: top.x - 14, y: top.y - 16, duration: 3.2, ease: "power1.inOut" })
            .call(() => {
              bob.pause();
              gsap.to(butterfly, { yPercent: 0, duration: 0.2 });
              flap.timeScale(0.25);
              playSound("land");
              gsap.to(mascot, { y: -5, duration: 0.22, yoyo: true, repeat: 1, ease: "power1.out" });
            })
            .to({}, { duration: 2.6 })
            .call(() => {
              flap.timeScale(1);
              bob.resume();
            })
            .to(butterfly, { x: endX, y: cruise - 30, duration: 3, ease: "power1.in" });
        } else {
          timeline.to(butterfly, { x: endX, duration: 7, ease: "none" });
        }
      });

      const blowWind = contextSafe(() => {
        const width = root.clientWidth;
        busy = true;
        playSound("wind");
        streaks.forEach((streak, i) => {
          gsap.fromTo(
            streak,
            { x: -160, autoAlpha: 0 },
            { x: width + 60, duration: 1.15, delay: i * 0.13, ease: "power1.in", keyframes: { autoAlpha: [0, 0.75, 0.75, 0] } },
          );
        });
        // El brote se dobla, las raíces se van hacia atrás, entrecierra los ojos y se inclina; luego vuelve con rebote.
        gsap
          .timeline({ delay: 0.25, onComplete: () => (busy = false) })
          .to(sprout, { rotation: 22, svgOrigin: "158 62", duration: 0.35, ease: "power2.out" }, 0)
          .to(roots, { rotation: -12, svgOrigin: "128 166", duration: 0.4, ease: "power2.out" }, 0)
          .to(gaze, { scaleY: 0.45, svgOrigin: "161 116", duration: 0.25 }, 0)
          .to(mascot, { rotation: 4, x: 5, duration: 0.4, ease: "power2.out" }, 0)
          .to(
            root.querySelectorAll("[data-sway]"),
            { rotation: 5, transformOrigin: "50% 100%", duration: 0.4, stagger: 0.06, ease: "power2.out" },
            0,
          )
          .to(sprout, { rotation: 0, duration: 1.4, ease: "elastic.out(1, 0.35)" }, 1.1)
          .to(roots, { rotation: 0, duration: 1.2, ease: "elastic.out(1, 0.4)" }, 1.1)
          .to(gaze, { scaleY: 1, duration: 0.3 }, 1.1)
          .to(mascot, { rotation: 0, x: 0, duration: 1.1, ease: "elastic.out(1, 0.45)" }, 1.1)
          .to(root.querySelectorAll("[data-sway]"), { rotation: 0, duration: 1.4, stagger: 0.06, ease: "elastic.out(1, 0.3)" }, 1.1);
      });

      /** Empieza a llover: le escurren gotas por los lados, el brote se le cae y entrecierra los ojos. */
      const getWet = contextSafe(() => {
        if (wet || hidden()) return;
        wet = true;
        gsap.to(sprout, { rotation: 20, svgOrigin: "158 62", duration: 1.2, ease: "power2.out", overwrite: "auto" });
        gsap.to(gaze, { scaleY: 0.6, svgOrigin: "161 116", duration: 0.6, overwrite: "auto" });
        dripping = drips.map((drip, i) => {
          const from = spot(96 + i * 38, 70 + (i % 2) * 26);
          const to = spot(92 + i * 40, 226);
          return gsap.fromTo(
            drip,
            { x: from.x, y: from.y, autoAlpha: 0 },
            {
              keyframes: { y: [from.y, to.y], autoAlpha: [0, 0.9, 0.9, 0] },
              x: to.x,
              duration: 1.1,
              delay: 0.8 + i * 0.37,
              repeat: -1,
              repeatDelay: 0.5,
              ease: "power1.in",
            },
          );
        });
      });

      /** Paró de llover: se sacude como un perro, las gotas salen volando y vuelve a lo suyo. */
      const shakeOff = contextSafe(() => {
        if (!wet) return;
        wet = false;
        dripping.forEach((tween) => tween.kill());
        dripping = [];
        gsap.set(drips, { autoAlpha: 0 });
        if (hidden()) return;
        busy = true;
        playSound("shake");
        const center = spot(158, 125);
        splashes.forEach((splash, i) => {
          const angle = (Math.PI * 2 * i) / splashes.length - Math.PI / 2;
          const reach = center.size * gsap.utils.random(0.45, 0.75);
          gsap.fromTo(
            splash,
            { x: center.x, y: center.y, autoAlpha: 1, scale: 1 },
            {
              x: center.x + Math.cos(angle) * reach,
              y: center.y + Math.sin(angle) * reach * 0.8,
              autoAlpha: 0,
              scale: 0.4,
              duration: 0.7,
              delay: 0.15 + (i % 3) * 0.12,
              ease: "power2.out",
            },
          );
        });
        gsap
          .timeline({ onComplete: () => (busy = false) })
          .to(
            mascot,
            {
              keyframes: { rotation: [0, -13, 13, -12, 12, -9, 9, -5, 0], x: [0, -4, 4, -4, 4, -3, 3, 0, 0] },
              duration: 0.95,
              ease: "none",
              transformOrigin: "50% 80%",
            },
            0,
          )
          .to(sprout, { keyframes: { rotation: [20, -24, 24, -18, 14, 0] }, svgOrigin: "158 62", duration: 1.1, ease: "none" }, 0)
          .to(gaze, { scaleY: 1, duration: 0.3 }, 0.9)
          .to(mascot, { y: -8, duration: 0.16, yoyo: true, repeat: 1, ease: "power1.out" }, 1.0);
      });

      const onRain = (event: Event) => ((event as CustomEvent<boolean>).detail ? getWet() : shakeOff());
      document.addEventListener(RAIN_EVENT, onRain);

      /** Quien está escribiendo no se interrumpe; tampoco se anima con la pestaña escondida ni la escena que no se ve. */
      const quiet = () =>
        document.hidden ||
        mascot.getClientRects().length === 0 ||
        mascot.hasAttribute("data-acting") ||
        document.activeElement?.matches("input, textarea, select") === true;

      // Se alternan, con una espera al azar entre uno y otro. La primera llega pronto, para que se note que hay vida.
      let next: "butterfly" | "wind" = Math.random() < 0.5 ? "butterfly" : "wind";
      const schedule = contextSafe((seconds: number) => {
        gsap.delayedCall(seconds, () => {
          if (busy || wet || quiet()) return schedule(4); // con lluvia no vuela la mariposa ni sopla el viento
          (next === "butterfly" ? flyButterfly : blowWind)();
          next = next === "butterfly" ? "wind" : "butterfly";
          schedule(gsap.utils.random(18, 34));
        });
      });
      schedule(gsap.utils.random(5, 9));
      return () => document.removeEventListener(RAIN_EVENT, onRain);
    },
    { scope: stage, dependencies: [animated], revertOnUpdate: true },
  );

  return (
    <div ref={stage} className={className}>
      {children}
      {animated && (
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-x-clip">
          <svg data-butterfly viewBox="0 0 32 24" className="invisible absolute top-0 left-0 h-6 w-8 overflow-visible">
            <polygon
              data-wing
              points="16,12 2,1 5,21"
              fill="var(--color-paleta-calabaza)"
              stroke="#1D1D1B"
              strokeWidth="1.5"
              strokeLinejoin="round"
              style={{ transformOrigin: "16px 12px" }}
            />
            <polygon
              data-wing
              points="16,12 30,1 27,21"
              fill="var(--color-paleta-trigo)"
              stroke="#1D1D1B"
              strokeWidth="1.5"
              strokeLinejoin="round"
              style={{ transformOrigin: "16px 12px" }}
            />
            <path d="M16 5v14" stroke="#1D1D1B" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          {[0, 1, 2, 3].map((drip) => (
            <span
              key={`gota-${drip}`}
              data-drip
              className="invisible absolute top-0 left-0 h-3.5 w-1.5 rounded-full border border-[#3E7FA6] bg-[#A9DBF5]"
            />
          ))}
          {[0, 1, 2, 3, 4, 5, 6, 7].map((splash) => (
            <span
              key={`salpico-${splash}`}
              data-splash
              className="invisible absolute top-0 left-0 size-3 rounded-full border border-[#3E7FA6] bg-[#A9DBF5]"
            />
          ))}
          {[18, 34, 52, 70].map((top, i) => (
            <span
              key={top}
              data-streak
              className="invisible absolute left-0 h-[3px] rounded-full bg-white"
              style={{ top: `${top}%`, width: `${[90, 130, 70, 110][i]}px` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
