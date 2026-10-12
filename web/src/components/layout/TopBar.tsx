import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { Link, NavLink } from "react-router";
import { PATHS } from "@/app/paths";
import { Mascot } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import { Plate } from "@/components/ui/Plate";
import { useLogout, useSession } from "@/features/auth/session";
import { useScroll } from "./SmoothScroll";
import { SoundToggle } from "./SoundToggle";

const NAV = [
  { to: PATHS.consult, label: "Consultar" },
  { to: PATHS.farm, label: "Mi finca" },
  { to: PATHS.howItWorks, label: "Cómo funciona" },
];

const GUEST = [
  { to: PATHS.login, label: "Entrar" },
  { to: PATHS.signup, label: "Crear cuenta" },
];

/** Menú a pantalla completa para pantallas angostas. */
function MobileMenu() {
  const [open, setOpen] = useState(false);
  const { user } = useSession();
  const logout = useLogout();
  const { setLocked } = useScroll();
  const change = (next: boolean) => {
    setOpen(next);
    setLocked(next);
  };
  return (
    <Dialog.Root open={open} onOpenChange={change}>
      <Dialog.Trigger
        aria-label="Abrir el menú"
        className="relative flex size-11 flex-col items-center justify-center gap-[5px] outline-none md:hidden"
      >
        {[0, 1, 2].map((bar) => (
          <span key={bar} aria-hidden="true" className="block h-[5px] w-[30px] rounded-[2px] bg-paleta-noche" />
        ))}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Content
          aria-describedby={undefined}
          data-lenis-prevent
          className="fixed inset-0 z-50 flex flex-col overflow-y-auto bg-paleta-noche px-7 pt-6 pb-10 text-texto-sobre-oscuro outline-none md:hidden"
        >
          <div className="flex items-center justify-between">
            <Dialog.Title className="font-titulos text-base font-titulo tracking-wide uppercase">Menú</Dialog.Title>
            <Dialog.Close aria-label="Cerrar el menú" className="flex size-11 items-center justify-center focus-visible:outline-white">
              <svg aria-hidden="true" viewBox="0 0 30 30" className="size-7">
                <path d="M4 4l22 22M26 4L4 26" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
            </Dialog.Close>
          </div>
          <nav aria-label="Principal" className="mt-6 flex flex-col">
            {[...NAV, ...(user ? [] : GUEST)].map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => change(false)}
                className="py-3 font-titulos text-[26px] font-titulo focus-visible:outline-white aria-[current=page]:text-paleta-trigo"
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          {user ? (
            <div className="mt-6 flex flex-col items-start gap-3 border-t border-white/25 pt-6">
              <p className="text-sm text-paleta-niebla">Entró como {user.username}</p>
              <button
                type="button"
                onClick={() => {
                  change(false);
                  logout.mutate();
                }}
                className="min-h-11 font-bold text-paleta-trigo underline decoration-2 underline-offset-4 focus-visible:outline-white"
              >
                Cerrar sesión
              </button>
            </div>
          ) : (
            <p className="mt-6 border-t border-white/25 pt-6 text-sm text-paleta-niebla">Sin cuenta, lo que consulta no se guarda.</p>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Barra superior: una tabla biselada que flota sobre el paisaje. */
export function TopBar() {
  const { user } = useSession();
  const logout = useLogout();
  return (
    <header className="pointer-events-none fixed inset-x-3 top-3 z-40 md:inset-x-8 md:top-5">
      <div className="pointer-events-auto relative mx-auto flex h-[62px] max-w-[1376px] items-start justify-between gap-6 pr-2 pl-4 md:h-[70px] md:pr-6 md:pl-6">
        <Plate c={14} fill="var(--color-superficie-panel)" depth={6} bottom={6} side="var(--color-superficie-borde)" />
        <div className="relative flex h-[56px] items-center gap-10 md:h-16">
          <Link to={PATHS.home} aria-label="AgroSense, inicio" className="text-texto-principal">
            <Logo />
          </Link>
          <nav aria-label="Principal" className="hidden items-center gap-10 md:flex">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className="border-b-[5px] border-transparent pt-[5px] aria-[current=page]:border-paleta-calabaza aria-[current=page]:font-bold"
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="relative flex h-[56px] items-center gap-2 md:h-16 md:gap-5">
          <SoundToggle />
          {user ? (
            <div className="hidden items-center gap-4 md:flex">
              <span className="flex h-11 max-w-56 items-center gap-2 bg-superficie-panel-suave px-3 font-bold [clip-path:polygon(10px_0,calc(100%-10px)_0,100%_10px,100%_calc(100%-10px),calc(100%-10px)_100%,10px_100%,0_calc(100%-10px),0_10px)]">
                <Mascot mood="idle" size={44} decorative />
                <span className="truncate">{user.display_name}</span>
              </span>
              <button
                type="button"
                onClick={() => logout.mutate()}
                className="min-h-11 font-bold text-oscuro-oliva underline decoration-2 underline-offset-4"
              >
                Cerrar sesión
              </button>
            </div>
          ) : (
            <div className="hidden md:block">
              <ButtonLink to={PATHS.login} variant="secondary" className="w-[140px]">
                Entrar
              </ButtonLink>
            </div>
          )}
          <MobileMenu />
        </div>
      </div>
    </header>
  );
}
