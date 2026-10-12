import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef, useState } from "react";
import { ExampleLabel } from "@/components/ui/Labels";
import { Mascot, type MascotMood } from "@/components/mascot/Mascot";
import { Scene, type SceneId } from "./scenes";
import { Card, JourneyNav, ScrollHint, followScroll, useReducedMotion, useSmoothScroll } from "./shared";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/** Tope de velocidad de la animación, en unidades de línea de tiempo por segundo: pasar de un lugar a otro dura al menos 1,25 s. */
const MAX_RATE = 0.8;

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
  const lenis = useSmoothScroll(!reduced);
  const [index, setIndex] = useState(0);
  const [moving, setMoving] = useState(false);

  // useGSAP limpia las animaciones y los ScrollTrigger al desmontar o cuando cambia «reducir movimiento».
  useGSAP(
    () => {
      if (reduced || !root.current) return;
      const last = PLACES.length - 1;
      const tl = gsap.timeline({ defaults: { ease: "none" }, paused: true });
      // El scroll vertical mueve la tira hacia la izquierda; las capas lejanas se quedan atrás.
      tl.to(".travesia-track", { xPercent: (-100 * last) / PLACES.length, duration: last }, 0);
      tl.to(".travesia-track #lejano", { x: 260, duration: last }, 0);
      tl.to(".travesia-track #medio", { x: 130, duration: last }, 0);
      tl.to(".travesia-track #niebla, .travesia-track #niebla-alta", { x: -90, duration: last }, 0);

      // El scroll marca el destino; la animación lo sigue con tope de velocidad (ver followScroll).
      // Paradas: cada lugar, centrado en pantalla. Fuera de ellas el imán termina de llegar.
      const rests = PLACES.map((_, i) => [Math.max(0, i - 0.06), Math.min(last, i + 0.06)] as const);
      return followScroll(tl, root.current, {
        maxRate: MAX_RATE,
        rests,
        lenis: () => lenis.current,
        onTime: (t) => {
          setIndex(Math.min(PLACES.length - 1, Math.round(t)));
          setMoving(Math.abs(t - Math.round(t)) > 0.18);
        },
      }).dispose;
    },
    { scope: root, dependencies: [reduced], revertOnUpdate: true },
  );

  if (reduced) {
    return (
      <>
        <JourneyNav current="/recorrido/3" />
        <main>
          {PLACES.map((p, i) => (
            <section
              key={p.scene}
              aria-label={p.title}
              className="relative flex min-h-screen items-start overflow-hidden px-[4vw] pt-[14vh]"
            >
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
      <main ref={root} style={{ height: `${PLACES.length * 120}vh` }}>
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
            <div
              className="h-full bg-paleta-calabaza transition-[width] duration-200"
              style={{ width: `${((index + 1) / PLACES.length) * 100}%` }}
            />
          </div>
          {index === 0 && !moving && <ScrollHint />}
        </div>
      </main>
    </>
  );
}
