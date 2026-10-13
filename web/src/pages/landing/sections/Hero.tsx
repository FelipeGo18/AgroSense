import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useCallback, useRef } from "react";
import { PATHS } from "@/app/paths";
import { Earth, type EarthFrame } from "@/components/globe/Earth";
import { useScroll } from "@/components/layout/SmoothScroll";
import { MascotSlot } from "@/components/mascot/MascotGuide";
import { ButtonLink } from "@/components/ui/Button";
import { GLOBE_CREDIT } from "../content";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/**
 * Dónde va la Tierra: a la derecha en pantallas anchas y asomando por abajo en las angostas. Al bajar, se acerca.
 * En las angostas `copyBottom` es donde termina el texto con sus botones: la Tierra nunca empieza antes, así no pasa
 * por debajo de los botones aunque la pantalla sea baja o el texto ocupe más líneas.
 */
function earthFrame(w: number, h: number, p: number, copyBottom: number): EarthFrame {
  const near = p * p * (3 - 2 * p);
  if (w < 768) {
    const r = Math.min(w * 0.525, h * 0.3);
    const top = Math.max(h * 0.87 - r, copyBottom + 20);
    return { cx: w / 2, cy: top + r - h * 0.05 * near, r: r * (1 + 0.2 * near) };
  }
  return { cx: w * (0.736 - 0.02 * near), cy: h * 0.556, r: Math.min(h * 0.367, w * 0.25) * (1 + 0.28 * near) };
}

/**
 * Portada: la Tierra gira en el espacio. Al bajar, la pantalla se queda quieta un tramo mientras el giro frena
 * con la región piloto al frente y la cámara se acerca; después sigue el resto de la página.
 */
export function Hero({ animated }: { animated: boolean }) {
  const root = useRef<HTMLElement>(null);
  const copy = useRef<HTMLDivElement>(null);
  const progress = useRef(0);
  // `offsetTop` y `offsetHeight` no cambian con la animación (solo se mueve con transform): dan el borde de abajo del texto.
  const frame = useCallback(
    (w: number, h: number, p: number) => earthFrame(w, h, p, copy.current ? copy.current.offsetTop + copy.current.offsetHeight : 0),
    [],
  );
  const { scrollTo } = useScroll();

  useGSAP(
    () => {
      if (!animated || !root.current) return;
      // Entrada: el nombre, la frase y los botones aparecen uno tras otro, de izquierda a derecha.
      gsap.from("[data-hero-in]", { x: -28, autoAlpha: 0, duration: 0.7, ease: "power2.out", stagger: 0.12, delay: 0.1 });
      gsap
        .timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: root.current,
            start: "top top",
            end: "bottom bottom",
            scrub: true,
            onUpdate: (self) => {
              progress.current = self.progress;
            },
          },
        })
        .to("[data-hero-hint]", { autoAlpha: 0, duration: 0.3 }, 0)
        .to("[data-hero-copy]", { y: -28, duration: 1 }, 0);
    },
    { scope: root, dependencies: [animated], revertOnUpdate: true },
  );

  return (
    <section
      id="inicio"
      ref={root}
      aria-labelledby="inicio-titulo"
      className={animated ? "relative h-[max(160svh,calc(680px+60svh))]" : "relative"}
    >
      <div className="sticky top-0 min-h-svh overflow-hidden bg-linear-to-b from-[#0B1226] to-[#1B3358] text-texto-sobre-oscuro md:h-svh md:min-h-[680px]">
        <Earth progress={progress} frame={frame} still={!animated} className="absolute inset-0" />
        {/* Esta capa no recibe el puntero: así se puede agarrar la Tierra, que está debajo. Solo el texto y los botones lo reciben. */}
        <div className="pointer-events-none relative container-page flex h-full min-h-svh flex-col pt-[clamp(104px,21vh,200px)] pb-28 md:min-h-0 md:pb-0">
          <div ref={copy} data-hero-copy className="pointer-events-auto flex w-full flex-col items-start sm:w-auto sm:self-start">
            <h1
              id="inicio-titulo"
              tabIndex={-1}
              data-section-title
              data-hero-in
              className="text-[clamp(2.75rem,14.5vw,3.5rem)] leading-none outline-none md:text-[clamp(3.5rem,8.4vw,7.5rem)]"
            >
              AgroSense
            </h1>
            <p
              data-hero-in
              className="mt-5 max-w-[37rem] text-[clamp(1.25rem,2.1vw,1.875rem)] leading-[1.4] [text-shadow:0_2px_0_rgb(11_18_38/0.6)]"
            >
              ¿Qué sembrar y en qué orden? Le mostramos estrategias de rotación con datos del satélite y reglas que se pueden explicar.
              Usted decide.
            </p>
            <div data-hero-in className="mt-8 flex w-full flex-col gap-4 sm:w-auto sm:flex-row sm:gap-6">
              <ButtonLink to={PATHS.consult} className="sm:w-[300px]">
                Consultar sin cuenta
              </ButtonLink>
              <ButtonLink to={PATHS.login} variant="secondary" className="sm:w-[180px]">
                Entrar
              </ButtonLink>
            </div>
          </div>
          <MascotSlot
            id="inicio"
            mood="guide"
            className="mt-5 w-[clamp(96px,30vw,120px)] self-end md:absolute md:top-[12.2%] md:left-[54%] md:mt-0 md:w-[clamp(160px,16.7vw,240px)]"
          />
        </div>
        <a
          data-hero-hint
          href="#preguntas"
          onClick={(event) => {
            event.preventDefault();
            scrollTo("preguntas");
          }}
          className="absolute bottom-9 left-5 w-44 py-2 text-left text-sm font-bold [text-shadow:0_2px_0_rgb(11_18_38/0.7)] focus-visible:outline-white md:bottom-6 md:left-[34%] md:flex md:min-h-11 md:w-auto md:-translate-x-1/2 md:items-center md:justify-center md:px-3 md:text-center md:whitespace-nowrap lg:left-[39%]"
        >
          Baje para empezar el recorrido <span aria-hidden="true">↓</span>
        </a>
        <p className="absolute inset-x-0 bottom-2 text-center text-[12px] text-[#C9D6E0] md:inset-x-auto md:right-8 md:bottom-3 md:text-xs">
          {GLOBE_CREDIT}
        </p>
      </div>
    </section>
  );
}
