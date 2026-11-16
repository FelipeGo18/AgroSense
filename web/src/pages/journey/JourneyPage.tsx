import { useTranslation } from "react-i18next";
import { Component, lazy, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import a1 from "../../../../design/paisaje/svg/a1-orbita.svg?url";
import a3 from "../../../../design/paisaje/svg/a3-region.svg?url";
import a5 from "../../../../design/paisaje/svg/a5-municipio.svg?url";
import a7 from "../../../../design/paisaje/svg/a7-lote.svg?url";
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
const levels = (
  t: ReturnType<typeof useTranslation>["t"],
): {
  id: string;
  label: string;
  title: string;
  text: string;
  say: string;
  mood: MascotMood;
  scene: string;
}[] => [
  {
    id: "orbita",
    label: t("journey.orbit.label"),
    title: t("journey.orbit.title"),
    text: t("journey.orbit.body"),
    say: t("journey.orbit.say"),
    mood: "flying",
    scene: a1,
  },
  {
    id: "region",
    label: t("journey.region.label"),
    title: t("journey.region.title"),
    text: t("journey.region.body"),
    say: t("journey.region.say"),
    mood: "guide",
    scene: a3,
  },
  {
    id: "municipio",
    label: t("journey.municipality.label"),
    title: t("journey.municipality.title"),
    text: t("journey.municipality.body"),
    say: t("journey.municipality.say"),
    mood: "guide",
    scene: a5,
  },
  {
    id: "finca",
    label: t("journey.farm.label"),
    title: t("journey.farm.title"),
    text: t("journey.farm.body"),
    say: t("journey.farm.say"),
    mood: "celebrate",
    scene: a7,
  },
];

/** La ilustración 2D del guion (`design/paisaje/`), como imagen: no se descarga hasta que se ve, y no repite ids. */
function Scene2D({ src }: { src: string }) {
  return <img data-scene src={src} alt="" aria-hidden="true" loading="lazy" className="absolute inset-0 size-full object-cover" />;
}

/**
 * Si la escena 3D falla (sin WebGL, se pierde el contexto o no baja el paquete), la página pasa a las ilustraciones 2D,
 * como en modo ligero, en vez de caerse: `Canvas` vuelve a lanzar los errores de la escena.
 */
class Fallback3D extends Component<{ onFail: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFail();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export function JourneyPage() {
  const { t } = useTranslation();
  const LEVELS = levels(t);
  const levelCount = LEVELS.length;
  const animated = useAnimated();
  const [failed, setFailed] = useState(false);
  // La escena 3D solo con movimiento y si no falló; si no, las ilustraciones 2D quietas.
  const threeD = animated && !failed;
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
        else if (i > 0 && box.top < middle) value = i - 1 + (middle - box.top) / (box.height / 2 + 1e-6);
      });
      progress.current = Math.min(levelCount - 1, Math.max(0, value));
      setActive(Math.round(progress.current));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [levelCount]);

  const go = (i: number) => {
    sections.current[i]?.scrollIntoView({ behavior: threeD ? "smooth" : "auto", block: "center" });
    sections.current[i]?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
  };

  return (
    <div className="relative min-h-svh bg-[#0B1226]">
      <title>{t("journey.title")} · AgroSense</title>
      <TopBar />
      {threeD && (
        <div className="fixed inset-0">
          <Fallback3D onFail={() => setFailed(true)}>
            <Suspense fallback={null}>
              <JourneyCanvas progress={progress} />
            </Suspense>
          </Fallback3D>
        </div>
      )}
      <main className="relative">
        <nav
          aria-label={t("journey.navigation")}
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
            {!threeD && <Scene2D src={level.scene} />}
            <div className="relative container-page flex w-full flex-col items-start gap-4 py-16 md:flex-row md:items-center">
              <Card className="w-full max-w-[520px]">
                <p className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase">
                  {t("journey.level", { current: i + 1, total: LEVELS.length })} · {level.label}
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
                    {t("journey.next", { level: LEVELS[i + 1].label })} ↓
                  </button>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    <ButtonLink to={PATHS.consult}>{t("journey.consult")}</ButtonLink>
                    <ButtonLink to={PATHS.howItWorks} variant="secondary">
                      {t("journey.how")}
                    </ButtonLink>
                  </div>
                )}
              </Card>
              {/* La mascota dice lo suyo al lado (nunca es la única señal). Con movimiento, su versión 3D vuela en la escena. */}
              <div className="flex items-center gap-3 rounded-sm bg-superficie-panel/90 px-4 py-3 shadow-md">
                {!threeD && <Mascot mood={level.mood} size={72} decorative />}
                <p className="font-bold">{level.say}</p>
              </div>
            </div>
          </section>
        ))}
        <p className="relative container-page pb-10 text-[13px] text-[#C9D6E0]">{t("journey.illustration")}</p>
      </main>
      <Footer />
    </div>
  );
}
