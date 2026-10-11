import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef, useState } from "react";
import { ExampleLabel } from "../components/Labels";
import { Mascot, type MascotMood } from "../components/Mascot";
import { Scene, type SceneId } from "./scenes";
import { Card, JourneyNav, ScrollHint, useReducedMotion, useSmoothScroll } from "./shared";

gsap.registerPlugin(ScrollTrigger);

interface Place {
  scene: SceneId;
  title: string;
  text: string;
  mood: MascotMood;
}

/** Del páramo a la finca, de lado: el camino que hace el agua. */
const PLACES: Place[] = [
  { scene: "c1", title: "Páramo", text: "Aquí nace el agua: frailejones, niebla y lagunas.", mood: "idle" },
  { scene: "c2", title: "Ladera", text: "La quebrada baja por el bosque hacia el valle.", mood: "flying" },
  { scene: "a5", title: "Mosaico de parcelas", text: "El agua llega a los cultivos. Cada parcela, una decisión.", mood: "guide" },
  { scene: "c4", title: "El pueblo", text: "Su municipio: aquí se cruzan el clima, la oferta y el mercado.", mood: "guide" },
  { scene: "a6", title: "Su finca", text: "Y aquí su lote. AgroSense le dice si es buen semestre para sembrar.", mood: "celebrate" },
];

function PlaceCard({ place, index }: { place: Place; index: number }) {
  return (
    <Card>
      <p className="text-sm font-bold tracking-wide text-texto-secundario uppercase">
        {index + 1} de {PLACES.length}
      </p>
      <h2 className="text-2xl">{place.title}</h2>
      <p>{place.text}</p>
      {index === PLACES.length - 1 && <ExampleLabel />}
    </Card>
  );
}

export function Journey3() {
  const root = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  useSmoothScroll(!reduced);
  const [index, setIndex] = useState(0);
  const [moving, setMoving] = useState(false);

  useLayoutEffect(() => {
    if (reduced || !root.current) return;
    const ctx = gsap.context(() => {
      const last = PLACES.length - 1;
      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom bottom",
          scrub: true,
          onUpdate: (self) => {
            const p = self.progress * last;
            setIndex(Math.round(p));
            setMoving(Math.abs(p - Math.round(p)) > 0.18);
          },
        },
      });
      // El scroll vertical mueve la tira hacia la izquierda; las capas lejanas se quedan atrás.
      tl.to(".travesia-track", { xPercent: (-100 * last) / PLACES.length, duration: last }, 0);
      tl.to(".travesia-track #lejano", { x: 260, duration: last }, 0);
      tl.to(".travesia-track #medio", { x: 130, duration: last }, 0);
      tl.to(".travesia-track #niebla, .travesia-track #niebla-alta", { x: -90, duration: last }, 0);
    }, root);
    return () => ctx.revert();
  }, [reduced]);

  if (reduced) {
    return (
      <>
        <JourneyNav current="/recorrido/3" />
        <main>
          {PLACES.map((p, i) => (
            <section key={p.scene} aria-label={p.title} className="relative flex min-h-screen items-start overflow-hidden px-[4vw] pt-[14vh]">
              <Scene id={p.scene} />
              <div className="relative z-10">
                <PlaceCard place={p} index={i} />
              </div>
              <Mascot mood={p.mood} size={220} decorative className="absolute right-[6vw] bottom-[10vh]" />
            </section>
          ))}
        </main>
      </>
    );
  }

  return (
    <>
      <JourneyNav current="/recorrido/3" />
      <main ref={root} style={{ height: `${PLACES.length * 100}vh` }}>
        <div className="sticky top-0 h-screen overflow-hidden bg-paleta-cielo">
          <div className="travesia-track flex h-full will-change-transform" style={{ width: `${PLACES.length * 100}vw` }}>
            {PLACES.map((p, i) => (
              <section key={p.scene} aria-label={p.title} className="relative h-full w-screen shrink-0 overflow-hidden">
                <Scene id={p.scene} />
                <div className="absolute top-[14vh] left-[4vw] z-20">
                  <PlaceCard place={p} index={i} />
                </div>
              </section>
            ))}
          </div>
          <div className="pointer-events-none absolute top-[38vh] left-[58vw] z-10 w-[clamp(150px,22vw,300px)]">
            <Mascot mood={moving ? "flying" : PLACES[index].mood} size={300} decorative className="mascot-float h-auto w-full" />
          </div>
          <div aria-hidden="true" className="absolute inset-x-[4vw] bottom-6 z-20 h-2 bg-white/60">
            <div className="h-full bg-paleta-calabaza transition-[width] duration-200" style={{ width: `${((index + 1) / PLACES.length) * 100}%` }} />
          </div>
          {index === 0 && !moving && <ScrollHint />}
        </div>
      </main>
    </>
  );
}
