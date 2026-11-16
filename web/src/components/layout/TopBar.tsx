import { useTranslation } from "react-i18next";
import { LanguageSelector } from "./LanguageSelector";
import { Suspense, lazy, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import { Link, NavLink } from "./LanguageLink";
import { PATHS } from "@/app/paths";
import { Mascot } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import { Plate } from "@/components/ui/Plate";
import { useLogout, useSession } from "@/features/auth/session";
import { LightModeToggle } from "./LightModeToggle";
import { useScroll } from "./SmoothScroll";
import { SoundToggle } from "./SoundToggle";
import { NAV } from "./navLinks";

const MobileMenuPanel = lazy(() => import("./MobileMenuPanel").then((module) => ({ default: module.MobileMenuPanel })));

/** Botón del menú de pantallas angostas. El menú mismo (MobileMenuPanel) se trae la primera vez que se abre. */
function MobileMenu() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [asked, setAsked] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const { setLocked } = useScroll();
  const change = (next: boolean) => {
    if (next) setAsked(true);
    setOpen(next);
    setLocked(next);
  };
  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-label={t("nav.open")}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => change(true)}
        className="relative flex size-11 flex-col items-center justify-center gap-[5px] lg:hidden"
      >
        {[0, 1, 2].map((bar) => (
          <span key={bar} aria-hidden="true" className="block h-[5px] w-[30px] rounded-[2px] bg-paleta-noche" />
        ))}
      </button>
      {asked && (
        <Suspense fallback={null}>
          <MobileMenuPanel open={open} onOpenChange={change} returnFocus={trigger} />
        </Suspense>
      )}
    </>
  );
}

/** Dónde quedó la raya naranja en la página anterior: cada página monta su barra, y la raya sale de ahí. */
let lastMark: { left: number; width: number } | null = null;

/** Enlaces principales de pantallas anchas. Una raya naranja marca la página actual y se desliza de un enlace al otro. */
function MainNav() {
  const { t, i18n } = useTranslation();
  const nav = useRef<HTMLElement>(null);
  const mark = useRef<HTMLSpanElement>(null);
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    const place = (from: typeof lastMark) => {
      const bar = mark.current;
      const current = nav.current?.querySelector<HTMLElement>('[aria-current="page"]');
      if (!bar) return;
      if (!current || current.offsetWidth === 0) {
        bar.style.opacity = "0";
        lastMark = null;
        return;
      }
      const to = { left: current.offsetLeft, width: current.offsetWidth };
      // Sale de donde estaba: se pone ahí sin transición y, ya pintada, viaja a su sitio.
      bar.style.transition = "none";
      Object.assign(bar.style, { left: `${(from ?? to).left}px`, width: `${(from ?? to).width}px`, opacity: "1" });
      void bar.offsetWidth;
      bar.style.transition = "";
      Object.assign(bar.style, { left: `${to.left}px`, width: `${to.width}px` });
      lastMark = to;
    };
    place(lastMark);
    const onResize = () => place(null);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [pathname, i18n.resolvedLanguage]);
  return (
    <nav ref={nav} aria-label={t("nav.primary")} className="relative hidden items-center gap-4 lg:flex xl:gap-6">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={`border-b-[5px] border-transparent pt-[5px] whitespace-nowrap aria-[current=page]:font-bold ${item.wide ? "hidden xl:inline" : ""}`}
        >
          {t(item.label)}
        </NavLink>
      ))}
      <span ref={mark} aria-hidden="true" className="nav-mark pointer-events-none absolute bottom-0 h-[5px] bg-paleta-calabaza opacity-0" />
    </nav>
  );
}

/** Barra superior: una tabla biselada que flota sobre el paisaje. */
export function TopBar() {
  const { t } = useTranslation();
  const { user } = useSession();
  const logout = useLogout();
  return (
    <header className="pointer-events-none fixed inset-x-3 top-3 z-40 md:inset-x-8 md:top-5">
      <div className="pointer-events-auto relative mx-auto flex h-[62px] max-w-[1376px] items-start justify-between gap-3 pr-2 pl-4 sm:gap-6 md:h-[70px] md:pr-6 md:pl-6">
        <Plate c={14} fill="var(--color-superficie-panel)" depth={6} bottom={6} side="var(--color-superficie-borde)" />
        <div className="relative flex h-[56px] min-w-0 items-center gap-4 md:h-16 xl:gap-6">
          <Link to={PATHS.home} aria-label={t("nav.home")} className="text-texto-principal">
            <Logo className="max-[339px]:text-[22px]" />
          </Link>
          <MainNav />
        </div>
        <div className="relative flex h-[56px] shrink-0 items-center gap-2 md:h-16 md:gap-2">
          <LanguageSelector className="hidden lg:block" />
          <SoundToggle className="max-[399px]:hidden" />
          <LightModeToggle />
          {user ? (
            <div className="hidden items-center gap-4 lg:flex">
              <Link
                to={PATHS.account}
                aria-label={t("nav.accountName", { name: user.display_name })}
                title={t("nav.accountName", { name: user.display_name })}
                className="flex h-11 items-center gap-2 bg-superficie-panel-suave px-3 font-bold [clip-path:polygon(10px_0,calc(100%-10px)_0,100%_10px,100%_calc(100%-10px),calc(100%-10px)_100%,10px_100%,0_calc(100%-10px),0_10px)] 2xl:max-w-56"
              >
                <Mascot mood="idle" size={44} decorative />
                {/* Con sesión la barra lleva la cuenta y «Cerrar sesión»: el nombre solo cabe junto al menú desde 1536 px
                    (medido con nombres largos). Más angosto, la mascota es el enlace y el nombre va en su aviso. */}
                <span className="hidden truncate 2xl:inline">{user.display_name}</span>
              </Link>
              <button
                type="button"
                onClick={() => logout.mutate()}
                className="min-h-11 font-bold text-oscuro-oliva underline decoration-2 underline-offset-4"
              >
                {t("nav.logout")}
              </button>
            </div>
          ) : (
            <div className="hidden lg:block">
              <ButtonLink to={PATHS.login} variant="secondary" className="w-[140px]">
                {t("nav.login")}
              </ButtonLink>
            </div>
          )}
          <MobileMenu />
        </div>
      </div>
    </header>
  );
}
