import { useEffect, type ReactNode } from "react";
import region from "../../../../design/paisaje/svg/a3-region.svg?raw";
import vereda from "../../../../design/paisaje/svg/a6-vereda.svg?raw";
import { Footer } from "@/components/layout/Footer";
import { SceneAmbient } from "@/components/layout/SceneAmbient";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot, type MascotMood } from "@/components/mascot/Mascot";
import { SceneLife } from "@/components/mascot/SceneLife";
import { useMascotReactions } from "@/components/mascot/reactions";
import { Card } from "@/components/ui/Card";
import { shake, useEntrance } from "@/hooks/useEntrance";
import { useReducedMotion } from "@/hooks/useReducedMotion";

// Los paisajes son nuestros (design/paisaje/build_paisaje.py): se insertan tal cual y se recortan para cubrir la pantalla.
const cover = (svg: string) =>
  svg.replace("<svg ", '<svg preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block" ');
const SCENES = { vereda: cover(vereda), region: cover(region) };

export interface FormSceneProps {
  children: ReactNode;
  /** El paisaje de fondo: la vereda (entrar y crear cuenta) o la región (la cuenta). */
  scene?: keyof typeof SCENES;
  /** Gesto de la mascota que acompaña el formulario. */
  mood: MascotMood;
  /** Letreros junto a la mascota, en pantallas anchas. */
  signs?: string[];
  /** Tarjeta ancha, de dos columnas: para el formulario largo de crear cuenta. */
  wide?: boolean;
  /** El error que devolvió la API, si lo hubo: cada error nuevo sacude la tarjeta. */
  rejected?: unknown;
}

/**
 * Un formulario de una sola tarea (entrar, crear cuenta, cambiar la contraseña): un paisaje de fondo, la tarjeta del
 * formulario y, al lado, la mascota.
 * El formulario cabe entero en la primera pantalla, sin hacer scroll; el pie de página queda debajo.
 *
 * Alrededor de la mascota hay vida (`SceneLife`): pasa una mariposa, sopla el viento. Nunca sobre la tarjeta.
 * La mascota reacciona a lo que hace la persona (`useMascotReactions`) y el paisaje tiene su ambiente y su hora
 * del día (`SceneAmbient`).
 */
export function FormScene({ children, scene = "vereda", mood, signs = [], wide = false, rejected }: FormSceneProps) {
  const stage = useEntrance<HTMLElement>();
  const animated = !useReducedMotion();
  const { act, poke } = useMascotReactions(stage, rejected);
  useEffect(() => {
    if (rejected && animated) shake(stage.current?.querySelector("[data-card]") ?? null);
  }, [rejected, animated, stage]);
  return (
    <>
      <TopBar />
      <div aria-hidden="true" className="fixed inset-0 -z-10" dangerouslySetInnerHTML={{ __html: SCENES[scene] }} />
      <SceneAmbient />
      {/* El espacio de abajo es para los cerros del pie de página, que suben sobre el paisaje. */}
      {/* En pantallas angostas la tarjeta baja un poco: queda una franja de paisaje donde vive la mascota. */}
      <main
        ref={stage}
        className="mx-auto flex min-h-svh max-w-[1440px] items-start gap-8 px-3 pt-[136px] pb-36 md:px-12 md:pt-[104px] md:pb-40 lg:px-24"
      >
        <div className={`relative w-full ${wide ? "lg:max-w-[880px]" : "md:max-w-[480px]"}`}>
          {/* En pantallas angostas la mascota se para en el borde de la tarjeta, en la franja de paisaje. */}
          <SceneLife className="absolute inset-x-0 -top-[56px] z-10 h-[56px] md:hidden">
            <div data-enter="pop" onPointerDown={poke} className="absolute right-4 -bottom-[9px]">
              <Mascot mood={act ?? mood} lively decorative className="block h-auto w-[76px]" />
            </div>
          </SceneLife>
          <div data-card data-enter>
            <Card bodyClassName="gap-3 md:px-3 md:pt-1">{children}</Card>
          </div>
        </div>
        <SceneLife className={`relative hidden flex-1 flex-col items-center gap-2 pt-6 ${wide ? "lg:flex" : "md:flex"}`}>
          {signs.map((sign) => (
            <Sign key={sign}>{sign}</Sign>
          ))}
          <div data-enter="pop" onPointerDown={poke}>
            <Mascot
              mood={act ?? mood}
              lively
              decorative
              className={`block h-auto ${wide ? "w-[min(22vw,300px)]" : "w-[min(30vw,400px)]"}`}
            />
          </div>
        </SceneLife>
      </main>
      <Footer />
    </>
  );
}

/** Letrero clavado, como los del kit. */
function Sign({ children }: { children: ReactNode }) {
  return (
    <div data-enter="pop" data-sway className="flex flex-col items-center">
      <span className="border-[3px] border-oscuro-trigo bg-paleta-trigo px-5 py-2 font-bold [clip-path:polygon(10px_0,calc(100%-10px)_0,100%_10px,100%_calc(100%-10px),calc(100%-10px)_100%,10px_100%,0_calc(100%-10px),0_10px)]">
        {children}
      </span>
      <svg aria-hidden="true" width="16" height="26" viewBox="0 0 16 26" className="-mt-1">
        <polygon points="0,0 16,0 16,18 8,26 0,18" fill="var(--color-paleta-tierra)" />
      </svg>
    </div>
  );
}
