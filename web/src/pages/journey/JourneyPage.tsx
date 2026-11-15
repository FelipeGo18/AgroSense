import { lazy, Suspense, useEffect, useRef, useState } from "react";
import a1 from "../../../../design/paisaje/svg/a1-orbita.svg?raw";
import a3 from "../../../../design/paisaje/svg/a3-region.svg?raw";
import a5 from "../../../../design/paisaje/svg/a5-municipio.svg?raw";
import a7 from "../../../../design/paisaje/svg/a7-lote.svg?raw";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot, type MascotMood } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAnimated } from "@/hooks/useLightMode";

// three.js se descarga solo aquí y solo con movimiento (HU-158).
const JourneyCanvas = lazy(() => import("./JourneyCanvas"));

/**
 * Del satélite a su finca (HU-155): el recorrido A, en una página propia. Cuatro niveles (la órbita, la región, el
 * municipio y la finca) que se recorren con el scroll o tocando cada nivel; la mascota guía.
 *
 * Con movimiento, una escena 3D low-poly (`JourneyCanvas`) sigue el scroll con la cámara. En modo ligero no hay
 * cámara ni 3D: cada nivel muestra su ilustración 2D quieta del guion (`design/paisaje/`), con los mismos textos.
 */
const LEVELS: {
  id: string;
  label: string;
  title: string;
  text: string;
  say: string;
  mood: MascotMood;
  scene: string;
}[] = [
  {
    id: "orbita",
    label: "Satélite",
    title: "Desde la órbita",
    text: "Los satélites de la NASA miden la Tierra todos los días: la lluvia (GPM IMERG), la temperatura y las heladas (NASA POWER, un reanálisis) y la altura del terreno (NASADEM).",
    say: "Desde aquí arriba empieza todo.",
    mood: "flying",
    scene: a1,
  },
  {
    id: "region",
    label: "Región",
    title: "Boyacá y Cundinamarca",
    text: "AgroSense toma esos datos para la región piloto, municipio por municipio: décadas de historia del clima y el suelo de cada zona.",
    say: "Bajamos al altiplano.",
    mood: "guide",
    scene: a3,
  },
  {
    id: "municipio",
    label: "Municipio",
    title: "Su municipio",
    text: "Para su municipio se ve cuántas veces heló, cuánta agua faltó y cuánto calor hizo en cada mes. Es historia de la zona, no un pronóstico.",
    say: "Aquí está su zona.",
    mood: "guide",
    scene: a5,
  },
  {
    id: "finca",
    label: "Finca",
    title: "Su finca",
    text: "Con eso, AgroSense le muestra estrategias de rotación para su lote y revisa cada siembra con un semáforo. La decisión siempre es suya.",
    say: "Y llegamos a su lote.",
    mood: "celebrate",
    scene: a7,
  },
];

function Scene2D({ markup }: { markup: string }) {
  const svg = markup.replace("<svg ", '<svg preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block" ');
  return <div aria-hidden="true" className="absolute inset-0" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export function JourneyPage() {
  const animated = useAnimated();
  const progress = useRef(0);
  const sections = useRef<(HTMLElement | null)[]>([]);
  const [active, setActive] = useState(0);

  // El avance (de 0 a 3) sale de qué tanto se ha pasado cada nivel: la escena 3D lo sigue.
  useEffect(() => {
    const update = () => {
      const middle = window.innerHeight / 2;
      let value = 0;
      sections.current.forEach((section, i) => {
        if (!section) return;
        const box = section.getBoundingClientRect();
        const center = box.top + box.height / 2;
        if (center <= middle) value = i;
        else if (i > 0 && box.top < middle) value = i - 1 + (middle - box.top) / (box.height / 2 + 1e-6) / 2;
      });
      progress.current = Math.min(LEVELS.length - 1, Math.max(0, value));
      setActive(Math.round(progress.current));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  const go = (i: number) => {
    sections.current[i]?.scrollIntoView({ behavior: animated ? "smooth" : "auto", block: "center" });
    sections.current[i]?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
  };

  return (
    <div className="relative min-h-svh bg-[#0B1226]">
      <title>Del satélite a su finca · AgroSense</title>
      <TopBar />
      {animated && (
        <div className="fixed inset-0">
          <Suspense fallback={null}>
            <JourneyCanvas progress={progress} />
          </Suspense>
        </div>
      )}
      <main className="relative">
        <nav
          aria-label="Niveles del recorrido"
          className="relative z-20 container-page flex flex-wrap gap-2 pt-[104px] md:sticky md:top-[100px] md:pt-[120px]"
        >
          {LEVELS.map((level, i) => (
            <button
              key={level.id}
              type="button"
              onClick={() => go(i)}
              aria-current={active === i ? "step" : undefined}
              className={`min-h-11 rounded-full px-4 text-[15px] font-bold shadow-md ${
                active === i ? "bg-oscuro-oliva text-texto-sobre-oscuro" : "bg-superficie-panel text-texto-principal"
              }`}
            >
              {i + 1}. {level.label}
            </button>
          ))}
        </nav>
        {LEVELS.map((level, i) => (
          <section
            key={level.id}
            id={level.id}
            ref={(el) => {
              sections.current[i] = el;
            }}
            aria-labelledby={`${level.id}-titulo`}
            className="relative flex min-h-svh items-center"
          >
            {!animated && <Scene2D markup={level.scene} />}
            <div className="relative container-page flex w-full flex-col items-start gap-4 py-16 md:flex-row md:items-center">
              <Card className="w-full max-w-[520px]">
                <p className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase">
                  Nivel {i + 1} de {LEVELS.length} · {level.label}
                </p>
                <h2 id={`${level.id}-titulo`} tabIndex={-1} className="text-[clamp(1.5rem,3vw,2.25rem)] outline-none">
                  {level.title}
                </h2>
                <p>{level.text}</p>
                {i < LEVELS.length - 1 ? (
                  <button
                    type="button"
                    onClick={() => go(i + 1)}
                    className="min-h-11 self-start font-bold text-oscuro-oliva underline decoration-2 underline-offset-4"
                  >
                    Bajar a: {LEVELS[i + 1].label} ↓
                  </button>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    <ButtonLink to={PATHS.consult}>Consultar sin cuenta</ButtonLink>
                    <ButtonLink to={PATHS.howItWorks} variant="secondary">
                      ¿Cómo funciona?
                    </ButtonLink>
                  </div>
                )}
              </Card>
              {/* La mascota dice lo suyo al lado (nunca es la única señal). Con movimiento, su versión 3D vuela en la escena. */}
              <div className="flex items-center gap-3 rounded-sm bg-superficie-panel/90 px-4 py-3 shadow-md">
                {!animated && <Mascot mood={level.mood} size={72} decorative />}
                <p className="font-bold">{level.say}</p>
              </div>
            </div>
          </section>
        ))}
        <p className="relative container-page pb-10 text-[13px] text-[#C9D6E0]">
          Ilustración: el relieve y la finca son dibujos, no el terreno real. Los datos de cada nivel son los que usa AgroSense.
        </p>
      </main>
      <Footer />
    </div>
  );
}
