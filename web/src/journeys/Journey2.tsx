import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef, useState } from "react";
import { EstimateLabel, ExampleLabel } from "../components/Labels";
import { Mascot, type MascotMood, type MascotSeed } from "../components/Mascot";
import { TrafficLightBadge } from "../components/TrafficLightBadge";
import { Scene, type SceneId } from "./scenes";
import { Card, JourneyNav, ScrollHint, useReducedMotion } from "./shared";

gsap.registerPlugin(ScrollTrigger);

interface Season {
  scene: SceneId;
  month: string;
  title: string;
  text: string;
  mood: MascotMood;
  seed: MascotSeed;
  extra?: "light" | "water";
}

/** El mismo lote a lo largo del año. Cada estación responde una pregunta de AgroSense. */
const SEASONS: Season[] = [
  { scene: "b1", month: "Antes de sembrar", title: "La tierra está lista", text: "Antes de sembrar hay una decisión: ¿es buen semestre para este cultivo, aquí?", mood: "idle", seed: "sprouted" },
  { scene: "b2", month: "Siembra", title: "¿Es buen semestre?", text: "AgroSense revisa el clima de la zona y cuánta área se sembró en años anteriores.", mood: "guide", seed: "sprouted", extra: "light" },
  { scene: "b3", month: "Crecimiento", title: "¿Cuánta agua va a necesitar?", text: "Un plan de riego mes a mes, en rangos.", mood: "flying", seed: "sprouted", extra: "water" },
  { scene: "b4", month: "Cosecha", title: "Llegó la cosecha", text: "Se registra la temporada y el lote guarda su historia.", mood: "celebrate", seed: "maize" },
  { scene: "b5", month: "Después", title: "¿Qué sembrar después?", text: "Rotaciones válidas para cuidar el suelo: aquí, una leguminosa.", mood: "guide", seed: "bean" },
];

function SeasonCard({ season }: { season: Season }) {
  return (
    <Card>
      <p className="text-sm font-bold tracking-wide text-texto-secundario uppercase">{season.month}</p>
      <h2 className="text-2xl">{season.title}</h2>
      <p>{season.text}</p>
      {season.extra === "light" && <TrafficLightBadge light="green" className="self-start" />}
      {season.extra === "water" && <EstimateLabel />}
      <ExampleLabel />
    </Card>
  );
}

export function Journey2() {
  const root = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const [index, setIndex] = useState(0);

  useLayoutEffect(() => {
    if (reduced || !root.current) return;
    const ctx = gsap.context(() => {
      const scenes = gsap.utils.toArray<HTMLElement>("[data-scene]");
      const cards = gsap.utils.toArray<HTMLElement>("[data-card]");
      gsap.set(scenes.slice(1), { autoAlpha: 0 });
      gsap.set(cards.slice(1), { autoAlpha: 0, y: 30 });
      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.6,
          onUpdate: (self) => setIndex(Math.min(SEASONS.length - 1, Math.round(self.progress * (SEASONS.length - 1)))),
        },
      });
      // La cámara no se mueve: las estaciones se funden una en otra y el sol cruza el cielo.
      tl.fromTo(".year-sun", { left: "8%", top: "34%" }, { left: "88%", top: "30%", duration: SEASONS.length - 1 }, 0);
      tl.to(".year-sun", { top: "12%", duration: (SEASONS.length - 1) / 2, ease: "sine.out" }, 0);
      tl.to(".year-sun", { top: "30%", duration: (SEASONS.length - 1) / 2, ease: "sine.in" }, (SEASONS.length - 1) / 2);
      for (let i = 0; i < SEASONS.length - 1; i++) {
        tl.to(scenes[i + 1], { autoAlpha: 1, duration: 0.5 }, i + 0.25);
        tl.to(cards[i], { autoAlpha: 0, y: -30, duration: 0.2 }, i + 0.25);
        tl.to(cards[i + 1], { autoAlpha: 1, y: 0, duration: 0.2 }, i + 0.6);
      }
      tl.to({}, { duration: 0.4 });
    }, root);
    return () => ctx.revert();
  }, [reduced]);

  if (reduced) {
    return (
      <>
        <JourneyNav current="/recorrido/2" />
        <main>
          {SEASONS.map((s) => (
            <section key={s.scene} aria-label={s.month} className="relative flex min-h-screen items-start overflow-hidden px-[4vw] pt-[14vh]">
              <Scene id={s.scene} />
              <div className="relative z-10">
                <SeasonCard season={s} />
              </div>
              <Mascot mood={s.mood} seed={s.seed} size={220} decorative className="absolute right-[6vw] bottom-[10vh]" />
            </section>
          ))}
        </main>
      </>
    );
  }

  const season = SEASONS[index];
  return (
    <>
      <JourneyNav current="/recorrido/2" />
      <main ref={root} style={{ height: `${SEASONS.length * 90 + 100}vh` }}>
        <div className="sticky top-0 h-screen overflow-hidden bg-paleta-cielo">
          {SEASONS.map((s) => (
            <Scene key={s.scene} id={s.scene} />
          ))}
          <div aria-hidden="true" className="year-sun absolute z-[5] size-[clamp(56px,7vw,100px)] -translate-x-1/2 rotate-[22deg] bg-[#FFF1C9] opacity-90 [clip-path:polygon(30%_0,70%_0,100%_30%,100%_70%,70%_100%,30%_100%,0_70%,0_30%)]" />
          {SEASONS.map((s, i) => (
            <div key={s.scene} data-card={i} className="absolute top-[14vh] left-[4vw] z-20">
              <SeasonCard season={s} />
            </div>
          ))}
          <div className="pointer-events-none absolute right-[8vw] bottom-[12vh] z-10 w-[clamp(150px,24vw,320px)]">
            <Mascot mood={season.mood} seed={season.seed} size={320} decorative className="mascot-float h-auto w-full" />
          </div>
          <ol aria-label="Etapas del año" className="absolute inset-x-0 bottom-6 z-20 flex justify-center gap-2 px-4">
            {SEASONS.map((s, i) => (
              <li key={s.scene} aria-current={i === index ? "step" : undefined} className={`px-3 py-1 text-sm font-bold ${i === index ? "bg-paleta-calabaza text-texto-principal" : "bg-white/80 text-texto-secundario"}`}>
                {s.month}
              </li>
            ))}
          </ol>
          {index === 0 && <ScrollHint />}
        </div>
      </main>
    </>
  );
}
