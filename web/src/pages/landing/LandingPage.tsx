import { Footer } from "@/components/layout/Footer";
import { SmoothScroll } from "@/components/layout/SmoothScroll";
import { TopBar } from "@/components/layout/TopBar";
import { MascotFlyer, MascotGuide, MascotSlot } from "@/components/mascot/MascotGuide";
import { useActiveSection } from "@/hooks/useActiveSection";
import { useEffect, useRef } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { playSound } from "@/lib/sound";
import { SectionNav } from "./SectionNav";
import { STOP_IDS, type StopId } from "./content";
import { Hero } from "./sections/Hero";
import { Preview } from "./sections/Preview";
import { Questions } from "./sections/Questions";
import { Sources } from "./sections/Sources";

/**
 * Inicio (HU-173). Es un recorrido de arriba abajo: la Tierra gira en la portada y la mascota va guiando de
 * parada en parada. La página solo compone: cada sección está en `sections/` y lo reutilizable en `components/`.
 * Con «reducir movimiento» no hay scroll suave, giro ni vuelo: todo aparece ya colocado.
 */
export function LandingPage() {
  const animated = !useReducedMotion();
  const active = useActiveSection(STOP_IDS) as StopId;
  // Al pasar a otra parada suena una nota, si el sonido está prendido. La primera pintura no cuenta.
  const heard = useRef(active);
  useEffect(() => {
    if (heard.current === active) return;
    heard.current = active;
    playSound("stop");
  }, [active]);
  return (
    <SmoothScroll enabled={animated}>
      <MascotGuide active={active} flying={animated}>
        <title>AgroSense · ¿Qué sembrar y en qué orden?</title>
        <TopBar />
        <main>
          <Hero animated={animated} />
          <Questions animated={animated} />
          <Preview animated={animated} />
          <Sources animated={animated} />
        </main>
        <Footer aside={<MascotSlot id="pie" mood="idle" className="w-[84px]" />} />
        <SectionNav active={active} />
        <MascotFlyer />
      </MascotGuide>
    </SmoothScroll>
  );
}
