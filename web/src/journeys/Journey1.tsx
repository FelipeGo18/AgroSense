import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "../components/Button";
import { Combobox, type Option } from "../components/Combobox";
import { ExampleLabel } from "../components/Labels";
import { Mascot, type MascotMood } from "../components/Mascot";
import { TrafficLightBadge } from "../components/TrafficLightBadge";
import { DEPTH, Scene, type SceneId } from "./scenes";
import { Card, JourneyNav, ScrollHint, useReducedMotion } from "./shared";

gsap.registerPlugin(ScrollTrigger);

// Datos de muestra (R5): se rotulan en pantalla.
const MUNICIPALITIES: Option[] = [
  { id: "15646", label: "Samacá", hint: "Boyacá" },
  { id: "15001", label: "Tunja", hint: "Boyacá" },
  { id: "15861", label: "Ventaquemada", hint: "Boyacá" },
  { id: "15814", label: "Toca", hint: "Boyacá" },
];

interface Stop {
  scene: SceneId;
  title: string;
  mood: MascotMood;
  /** Posición de la mascota: izquierda y arriba en % de la pantalla, y su escala. */
  mascot: { left: number; top: number; scale: number };
  /** Punto hacia el que se acerca la cámara al salir, en % de la escena. */
  focus: string;
}

const STOPS: Stop[] = [
  { scene: "a1", title: "Órbita", mood: "guide", mascot: { left: 66, top: 26, scale: 1 }, focus: "49% 78%" },
  { scene: "a2", title: "Atmósfera", mood: "flying", mascot: { left: 46, top: 34, scale: 0.92 }, focus: "50% 100%" },
  { scene: "a3", title: "Región", mood: "guide", mascot: { left: 68, top: 20, scale: 0.84 }, focus: "50% 86%" },
  { scene: "a4", title: "Valle", mood: "flying", mascot: { left: 50, top: 24, scale: 0.8 }, focus: "50% 74%" },
  { scene: "a5", title: "Municipio", mood: "guide", mascot: { left: 58, top: 30, scale: 0.74 }, focus: "40% 66%" },
  { scene: "a6", title: "Vereda", mood: "guide", mascot: { left: 40, top: 34, scale: 0.74 }, focus: "44% 86%" },
  { scene: "a7", title: "Lote", mood: "idle", mascot: { left: 68, top: 46, scale: 0.8 }, focus: "50% 50%" },
];

const HOLD = 1; // cuánto se queda la pantalla en cada parada
const MOVE = 1; // cuánto dura el paso a la siguiente
const SPAN = HOLD + MOVE;

function Overlay({ index, children, className = "" }: { index: number; children: ReactNode; className?: string }) {
  return (
    <div data-overlay={index} className={`absolute top-[14vh] left-[4vw] z-20 ${className}`}>
      {children}
    </div>
  );
}

function Chip({ children }: { children: ReactNode }) {
  return (
    <Card>
      <p className="font-titulos text-xl font-titulo">{children}</p>
    </Card>
  );
}

function StopContent({ index, municipality, onMunicipality }: { index: number; municipality: Option | null; onMunicipality: (o: Option) => void }) {
  const place = municipality?.label ?? "Samacá";
  switch (index) {
    case 0:
      return (
        <div className="flex max-w-[min(92vw,34rem)] flex-col gap-4 text-texto-sobre-oscuro">
          <h1 className="text-[clamp(3rem,9vw,5.5rem)] leading-none">AgroSense</h1>
          <p className="text-lg sm:text-2xl">¿Es buen semestre para sembrar? Se lo decimos con datos del satélite y reglas que se pueden explicar.</p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => scrollBy({ top: innerHeight * 1.2, behavior: "smooth" })}>Consultar sin cuenta</Button>
            <Button variant="secondary">Entrar</Button>
          </div>
        </div>
      );
    case 1:
      return <Chip>Entrando a la atmósfera</Chip>;
    case 2:
      return (
        <Card>
          <h2 className="text-2xl">¿Dónde está su finca?</h2>
          <Combobox label="Municipio" placeholder="Escriba su municipio" options={MUNICIPALITIES} value={municipality} onChange={onMunicipality} />
        </Card>
      );
    case 3:
      return <Chip>Bajando a {place}</Chip>;
    case 4:
      return (
        <Card>
          <h2 className="text-2xl">{place}, Boyacá</h2>
          <p className="text-texto-secundario">Elija cultivo y semestre</p>
          <Button variant="secondary">Papa · semestre B</Button>
          <Button onClick={() => scrollBy({ top: innerHeight * 1.2, behavior: "smooth" })}>Ver diagnóstico</Button>
        </Card>
      );
    case 5:
      return <Chip>Llegando a su lote</Chip>;
    default:
      return (
        <Card>
          <h2 className="text-xl">Papa en {place} · semestre B</h2>
          <TrafficLightBadge light="yellow" className="self-start" />
          <p>
            <strong>Sugerencia: esperar otro semestre.</strong> El clima acompaña, pero hay más área sembrada que en años anteriores.
          </p>
          <ExampleLabel />
        </Card>
      );
  }
}

export function Journey1() {
  const root = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const [stop, setStop] = useState(0);
  const [moving, setMoving] = useState(false);
  const [municipality, setMunicipality] = useState<Option | null>(null);

  useLayoutEffect(() => {
    if (reduced || !root.current) return;
    const ctx = gsap.context(() => {
      const scenes = gsap.utils.toArray<HTMLElement>("[data-scene]");
      const overlays = gsap.utils.toArray<HTMLElement>("[data-overlay]");
      gsap.set(scenes.slice(1), { autoAlpha: 0 });
      gsap.set(overlays.slice(1), { autoAlpha: 0, y: 30 });

      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.6,
          onUpdate: (self) => {
            const t = self.progress * tl.duration();
            setStop(Math.min(STOPS.length - 1, Math.floor(t / SPAN)));
            setMoving(t % SPAN > HOLD && t < tl.duration() - 0.01);
          },
        },
      });

      STOPS.forEach((s, i) => {
        const at = i * SPAN;
        const scene = scenes[i];
        // Paralaje dentro de la escena: las capas lejanas se mueven menos.
        Object.entries(DEPTH).forEach(([layer, depth]) => {
          const el = scene.querySelector(`#${layer}`);
          if (el) tl.fromTo(el, { yPercent: 2.5 * depth }, { yPercent: -3.5 * depth, duration: SPAN }, at);
        });
        tl.to(".journey-mascot", { left: `${s.mascot.left}%`, top: `${s.mascot.top}%`, scale: s.mascot.scale, duration: MOVE, ease: "power1.inOut" }, Math.max(0, at - MOVE));
        if (i === STOPS.length - 1) return;
        const next = scenes[i + 1];
        const go = at + HOLD;
        tl.to(overlays[i], { autoAlpha: 0, y: -30, duration: MOVE * 0.3 }, go);
        // Bajar es acercarse: la escena crece hacia su punto de interés y deja ver la siguiente.
        tl.to(scene, { scale: 2.6, transformOrigin: s.focus, duration: MOVE, ease: "power1.in" }, go);
        tl.to(scene, { autoAlpha: 0, duration: MOVE * 0.45 }, go + MOVE * 0.55);
        tl.fromTo(next, { autoAlpha: 0, scale: 1.35 }, { autoAlpha: 1, scale: 1, duration: MOVE * 0.6, ease: "power1.out" }, go + MOVE * 0.4);
        tl.to(overlays[i + 1], { autoAlpha: 1, y: 0, duration: MOVE * 0.3 }, go + MOVE * 0.8);
      });
      tl.to({}, { duration: HOLD }); // la última parada también se queda
    }, root);
    return () => ctx.revert();
  }, [reduced]);

  if (reduced) {
    // Sin viaje: cada parada con interfaz aparece ya colocada, una debajo de otra.
    return (
      <>
        <JourneyNav current="/recorrido/1" />
        <main>
          {STOPS.map((s, i) =>
            i % 2 === 0 ? (
              <section key={s.scene} aria-label={s.title} className="relative flex min-h-screen items-start overflow-hidden px-[4vw] pt-[14vh]">
                <Scene id={s.scene} />
                <div className="relative z-10">
                  <StopContent index={i} municipality={municipality} onMunicipality={setMunicipality} />
                </div>
                <Mascot mood={s.mood} size={220} decorative className="absolute right-[6vw] bottom-[10vh]" />
              </section>
            ) : null,
          )}
        </main>
      </>
    );
  }

  return (
    <>
      <JourneyNav current="/recorrido/1" />
      <main ref={root} style={{ height: `${(STOPS.length * SPAN - MOVE) * 85 + 100}vh` }}>
        <div className="sticky top-0 h-screen overflow-hidden bg-paleta-noche">
          {STOPS.map((s) => (
            <Scene key={s.scene} id={s.scene} className="will-change-transform" />
          ))}
          {STOPS.map((s, i) => (
            <Overlay key={s.scene} index={i}>
              <StopContent index={i} municipality={municipality} onMunicipality={setMunicipality} />
            </Overlay>
          ))}
          <div className="journey-mascot pointer-events-none absolute z-10 w-[clamp(150px,24vw,330px)] -translate-x-1/2" style={{ left: `${STOPS[0].mascot.left}%`, top: `${STOPS[0].mascot.top}%` }}>
            <Mascot mood={moving ? "flying" : STOPS[stop].mood} size={330} decorative className="mascot-float h-auto w-full" />
          </div>
          <ol aria-label="Paradas del recorrido" className="absolute right-4 bottom-1/2 z-20 flex translate-y-1/2 flex-col gap-2">
            {STOPS.map((s, i) => (
              <li key={s.scene} aria-current={i === stop ? "step" : undefined} title={s.title} className={`size-3 rotate-45 border-2 border-white ${i === stop ? "bg-paleta-calabaza" : i < stop ? "bg-white" : "bg-transparent"}`}>
                <span className="sr-only">{s.title}</span>
              </li>
            ))}
          </ol>
          {stop === 0 && !moving && <ScrollHint />}
        </div>
      </main>
    </>
  );
}
