import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "../components/Button";
import { Combobox, type Option } from "../components/Combobox";
import { ExampleLabel } from "../components/Labels";
import { Mascot, type MascotMood } from "../components/Mascot";
import { TrafficLightBadge } from "../components/TrafficLightBadge";
import { DEPTH, Scene, type SceneId } from "./scenes";
import { Card, JourneyNav, ScrollHint, useReducedMotion, useSmoothScroll } from "./shared";

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
  /** Las paradas con interfaz se quedan más tiempo; las de tránsito solo se atraviesan. */
  ui: boolean;
  mood: MascotMood;
  /** Posición de la mascota: izquierda y arriba en % de la pantalla, y su escala. */
  mascot: { left: number; top: number; scale: number };
  /** Punto hacia el que baja la cámara, en % de la escena. */
  focus: string;
  /**
   * Cómo se pasa a la siguiente escena:
   * - «zoom»: es el mismo lugar más de cerca; la cámara se acerca y una se funde en la otra.
   * - un color: cambia el lugar; se atraviesa una capa de nubes o niebla de ese color, que tapa el corte.
   */
  exit: "zoom" | `#${string}`;
}

const CLOUD = "#FFFFFF";
const FOG = "#EEF4F7";

const STOPS: Stop[] = [
  { scene: "a1", title: "Órbita", ui: true, mood: "guide", mascot: { left: 66, top: 26, scale: 1 }, focus: "49% 80%", exit: "zoom" },
  { scene: "a1b", title: "Sobre el altiplano", ui: false, mood: "flying", mascot: { left: 62, top: 22, scale: 0.96 }, focus: "49% 70%", exit: CLOUD },
  { scene: "a2", title: "Atmósfera", ui: false, mood: "flying", mascot: { left: 46, top: 34, scale: 0.92 }, focus: "50% 100%", exit: CLOUD },
  { scene: "a3", title: "Región", ui: true, mood: "guide", mascot: { left: 68, top: 20, scale: 0.84 }, focus: "50% 82%", exit: "zoom" },
  { scene: "a3b", title: "Entre los cerros", ui: false, mood: "flying", mascot: { left: 60, top: 24, scale: 0.82 }, focus: "50% 80%", exit: FOG },
  { scene: "a4", title: "Valle", ui: false, mood: "flying", mascot: { left: 50, top: 24, scale: 0.8 }, focus: "50% 72%", exit: "zoom" },
  { scene: "a5", title: "Municipio", ui: true, mood: "guide", mascot: { left: 58, top: 30, scale: 0.74 }, focus: "42% 68%", exit: "zoom" },
  { scene: "a5b", title: "Las parcelas", ui: false, mood: "flying", mascot: { left: 54, top: 30, scale: 0.74 }, focus: "44% 72%", exit: "zoom" },
  { scene: "a6", title: "Vereda", ui: false, mood: "guide", mascot: { left: 40, top: 34, scale: 0.74 }, focus: "44% 86%", exit: "zoom" },
  { scene: "a7", title: "Lote", ui: true, mood: "idle", mascot: { left: 68, top: 46, scale: 0.8 }, focus: "50% 60%", exit: "zoom" },
];

const MOVE = 1; // duración de cada paso, en unidades de la línea de tiempo
const hold = (s: Stop) => (s.ui ? 1 : 0.4);

/** Inicio de cada parada y duración total: de aquí salen el alto del scroll y la parada actual. */
const STARTS = STOPS.reduce<number[]>((acc, _, i) => [...acc, i === 0 ? 0 : acc[i - 1] + hold(STOPS[i - 1]) + MOVE], []);
const TOTAL = STARTS[STOPS.length - 1] + hold(STOPS[STOPS.length - 1]);

function Chip({ children }: { children: ReactNode }) {
  return (
    <Card>
      <p className="font-titulos text-xl font-titulo">{children}</p>
    </Card>
  );
}

function StopContent({ index, municipality, onMunicipality }: { index: number; municipality: Option | null; onMunicipality: (o: Option) => void }) {
  const place = municipality?.label ?? "Samacá";
  switch (STOPS[index].scene) {
    case "a1":
      return (
        <div className="flex max-w-[min(92vw,34rem)] flex-col gap-4 text-texto-sobre-oscuro">
          <h1 className="text-[clamp(3rem,9vw,5.5rem)] leading-none">AgroSense</h1>
          <p className="text-lg sm:text-2xl">¿Es buen semestre para sembrar? Se lo decimos con datos del satélite y reglas que se pueden explicar.</p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => scrollBy({ top: innerHeight * 1.6, behavior: "smooth" })}>Consultar sin cuenta</Button>
            <Button variant="secondary">Entrar</Button>
          </div>
        </div>
      );
    case "a2":
      return <Chip>Entrando a la atmósfera</Chip>;
    case "a3":
      return (
        <Card>
          <h2 className="text-2xl">¿Dónde está su finca?</h2>
          <Combobox label="Municipio" placeholder="Escriba su municipio" options={MUNICIPALITIES} value={municipality} onChange={onMunicipality} />
        </Card>
      );
    case "a4":
      return <Chip>Bajando a {place}</Chip>;
    case "a5":
      return (
        <Card>
          <h2 className="text-2xl">{place}, Boyacá</h2>
          <p className="text-texto-secundario">Elija cultivo y semestre</p>
          <Button variant="secondary">Papa · semestre B</Button>
          <Button onClick={() => scrollBy({ top: innerHeight * 1.6, behavior: "smooth" })}>Ver diagnóstico</Button>
        </Card>
      );
    case "a6":
      return <Chip>Llegando a su lote</Chip>;
    case "a7":
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
    default:
      return null;
  }
}

/** Capa de nubes o niebla que cruza la pantalla de abajo hacia arriba y tapa el cambio de escena. */
function Wipe() {
  const edge = "0,900 0,640 100,560 220,650 340,470 470,600 600,390 730,520 860,300 990,560 1120,430 1250,610 1360,500 1440,590 1440,900";
  const haze = "0,900 0,520 140,420 280,540 420,330 560,480 700,250 840,420 980,200 1120,440 1260,300 1440,460 1440,900";
  const clouds = (
    <>
      <polygon points={haze} fill="currentColor" opacity={0.55} />
      <polygon points={edge} fill="currentColor" />
    </>
  );
  return (
    <div aria-hidden="true" className="journey-wipe pointer-events-none absolute inset-x-0 top-0 z-[8] h-[300vh] text-white will-change-transform">
      <svg className="block h-screen w-full" viewBox="0 0 1440 900" preserveAspectRatio="none">
        {clouds}
      </svg>
      <div className="-my-px h-screen bg-current" />
      <svg className="block h-screen w-full -scale-y-100" viewBox="0 0 1440 900" preserveAspectRatio="none">
        {clouds}
      </svg>
    </div>
  );
}

export function Journey1() {
  const root = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  useSmoothScroll(!reduced);
  const [stop, setStop] = useState(0);
  const [moving, setMoving] = useState(false);
  const [municipality, setMunicipality] = useState<Option | null>(null);

  useLayoutEffect(() => {
    if (reduced || !root.current) return;
    const ctx = gsap.context(() => {
      const scenes = gsap.utils.toArray<HTMLElement>("[data-scene]");
      const overlays = gsap.utils.toArray<HTMLElement>("[data-overlay]");
      scenes.forEach((scene, i) => gsap.set(scene, { transformOrigin: STOPS[i].focus, autoAlpha: i === 0 ? 1 : 0 }));
      gsap.set(overlays.slice(1), { autoAlpha: 0, y: 30 });
      gsap.set(".journey-wipe", { y: "100vh" });

      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom bottom",
          scrub: true, // la inercia la pone Lenis
          onUpdate: (self) => {
            const t = self.progress * TOTAL;
            let i = STOPS.length - 1;
            while (i > 0 && t < STARTS[i]) i--;
            setStop(i);
            setMoving(i < STOPS.length - 1 && t > STARTS[i] + hold(STOPS[i]) + 0.02);
          },
        },
      });

      STOPS.forEach((s, i) => {
        const at = STARTS[i];
        const stay = hold(s);
        const scene = scenes[i];
        const last = i === STOPS.length - 1;
        // La cámara nunca se detiene: mientras se lee la parada, sigue bajando despacio.
        tl.to(scene, { scale: 1.1, duration: stay }, at);
        // Paralaje: las capas lejanas se mueven menos que las cercanas.
        Object.entries(DEPTH).forEach(([layer, depth]) => {
          const el = scene.querySelector(`#${layer}`);
          if (el) tl.fromTo(el, { yPercent: 3 * depth }, { yPercent: -4 * depth, duration: stay + MOVE * 1.5 }, Math.max(0, at - MOVE * 0.5));
        });
        if (last) return;

        const next = scenes[i + 1];
        const target = STOPS[i + 1].mascot;
        const go = at + stay;
        tl.to(overlays[i], { autoAlpha: 0, y: -30, duration: MOVE * 0.2 }, go);
        tl.to(".journey-mascot", { left: `${target.left}%`, top: `${target.top}%`, scale: target.scale, duration: MOVE, ease: "sine.inOut" }, go);
        if (s.exit === "zoom") {
          // Mismo lugar, más cerca: la escena crece y la siguiente aparece encima, sin corte.
          tl.to(scene, { scale: 2.3, duration: MOVE, ease: "power1.in" }, go);
          tl.to(next, { autoAlpha: 1, duration: MOVE * 0.55 }, go + MOVE * 0.4);
          tl.set(scene, { autoAlpha: 0 }, go + MOVE);
        } else {
          // Cambia el lugar: se atraviesa una capa de nubes o niebla que tapa el cambio.
          tl.to(scene, { scale: 1.5, duration: MOVE }, go);
          tl.set(".journey-wipe", { color: s.exit }, go);
          tl.fromTo(".journey-wipe", { y: "100vh" }, { y: "-300vh", duration: MOVE, immediateRender: false }, go);
          tl.set(next, { autoAlpha: 1 }, go + MOVE * 0.5);
          tl.set(scene, { autoAlpha: 0 }, go + MOVE * 0.5);
        }
        tl.to(overlays[i + 1], { autoAlpha: 1, y: 0, duration: MOVE * 0.2 }, go + MOVE * 0.85);
      });
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
            s.ui ? (
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
      <main ref={root} style={{ height: `${TOTAL * 95 + 100}vh` }}>
        <div className="sticky top-0 h-screen overflow-hidden bg-paleta-noche">
          {STOPS.map((s) => (
            <Scene key={s.scene} id={s.scene} className="will-change-transform" />
          ))}
          <Wipe />
          {STOPS.map((s, i) => (
            <div key={s.scene} data-overlay={i} className="absolute top-[14vh] left-[4vw] z-20">
              <StopContent index={i} municipality={municipality} onMunicipality={setMunicipality} />
            </div>
          ))}
          <div className="journey-mascot pointer-events-none absolute z-10 w-[clamp(150px,24vw,330px)] -translate-x-1/2" style={{ left: `${STOPS[0].mascot.left}%`, top: `${STOPS[0].mascot.top}%` }}>
            <Mascot mood={moving ? "flying" : STOPS[stop].mood} size={330} decorative className="mascot-float h-auto w-full" />
          </div>
          <ol aria-label="Paradas del recorrido" className="absolute right-4 bottom-1/2 z-20 flex translate-y-1/2 flex-col gap-2">
            {STOPS.map((s, i) => (
              <li key={s.scene} aria-current={i === stop ? "step" : undefined} title={s.title} className={`rotate-45 border-2 border-white ${s.ui ? "size-3" : "size-2"} ${i === stop ? "bg-paleta-calabaza" : i < stop ? "bg-white" : "bg-transparent"}`}>
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
