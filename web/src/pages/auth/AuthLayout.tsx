import type { ReactNode } from "react";
import vereda from "../../../../design/paisaje/svg/a6-vereda.svg?raw";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot, type MascotMood } from "@/components/mascot/Mascot";
import { Card } from "@/components/ui/Card";

// El paisaje es nuestro (design/paisaje/build_paisaje.py): se inserta tal cual y se recorta para cubrir la pantalla.
const BACKDROP = vereda.replace("<svg ", '<svg preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block" ');

export interface AuthLayoutProps {
  children: ReactNode;
  /** Gesto de la mascota que acompaña el formulario. */
  mood: MascotMood;
  /** Letreros junto a la mascota, en pantallas anchas. */
  signs: string[];
  /** Tarjeta ancha, de dos columnas: para el formulario largo de crear cuenta. */
  wide?: boolean;
}

/**
 * Entrar y crear cuenta: el paisaje de la vereda, la tarjeta del formulario y, al lado, la mascota.
 * El formulario cabe entero en la primera pantalla, sin hacer scroll; el pie de página queda debajo.
 */
export function AuthLayout({ children, mood, signs, wide = false }: AuthLayoutProps) {
  return (
    <>
      <TopBar />
      <div aria-hidden="true" className="fixed inset-0 -z-10" dangerouslySetInnerHTML={{ __html: BACKDROP }} />
      {/* El espacio de abajo es para los cerros del pie de página, que suben sobre el paisaje. */}
      <main className="mx-auto flex min-h-svh max-w-[1440px] items-start gap-8 px-3 pt-[104px] pb-36 md:px-12 md:pt-[104px] md:pb-40 lg:px-24">
        <div className={`relative w-full ${wide ? "lg:max-w-[880px]" : "md:max-w-[480px]"}`}>
          {/* En pantallas angostas la mascota se asoma por el borde de la tarjeta: no le quita alto al formulario. */}
          <Mascot mood={mood} lively decorative className="absolute -top-[30px] right-4 z-10 h-auto w-[64px] md:hidden" />
          <Card bodyClassName="gap-3 md:px-3 md:pt-1">{children}</Card>
        </div>
        <div className={`hidden flex-1 flex-col items-center gap-2 pt-6 ${wide ? "lg:flex" : "md:flex"}`}>
          {signs.map((sign) => (
            <Sign key={sign}>{sign}</Sign>
          ))}
          <Mascot mood={mood} lively decorative className={`h-auto ${wide ? "w-[min(22vw,300px)]" : "w-[min(30vw,400px)]"}`} />
        </div>
      </main>
      <Footer />
    </>
  );
}

/** Letrero clavado, como los del kit. */
function Sign({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center">
      <span className="border-[3px] border-oscuro-trigo bg-paleta-trigo px-5 py-2 font-bold [clip-path:polygon(10px_0,calc(100%-10px)_0,100%_10px,100%_calc(100%-10px),calc(100%-10px)_100%,10px_100%,0_calc(100%-10px),0_10px)]">
        {children}
      </span>
      <svg aria-hidden="true" width="16" height="26" viewBox="0 0 16 26" className="-mt-1">
        <polygon points="0,0 16,0 16,18 8,26 0,18" fill="var(--color-paleta-tierra)" />
      </svg>
    </div>
  );
}
