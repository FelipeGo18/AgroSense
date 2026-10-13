import { useEffect, useId, useRef, useState } from "react";
import { Plate } from "@/components/ui/Plate";
import { PreferenceSwitch } from "@/components/ui/PreferenceSwitch";
import { useLightMode } from "@/hooks/useLightMode";

/** Qué hace el modo ligero, en una frase: lo leen el aviso de la barra y el interruptor del menú. */
export const LIGHT_MODE_WHAT = "Quita las animaciones y el scroll suave. La información es la misma.";

/** Cuánto se queda abierto el aviso después de tocar el botón (en la pantalla táctil no hay «pasar el cursor»). */
const PIN_MS = 8000;

/**
 * Botón «Modo ligero» de la barra superior. Al pasar el cursor, enfocarlo con el teclado o tocarlo, un aviso dice qué es
 * y qué desactiva. Tocar el botón cambia el modo y deja el aviso abierto unos segundos; Escape lo cierra.
 */
export function LightModeToggle({ className = "" }: { className?: string }) {
  const { light, pref, setLight } = useLightMode();
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const panelId = useId();
  const root = useRef<HTMLDivElement>(null);
  const visible = hover || focus || pinned;

  useEffect(() => {
    if (!visible) return;
    const close = () => {
      setHover(false);
      setFocus(false);
      setPinned(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    const onDown = (event: PointerEvent) => !root.current?.contains(event.target as Node) && setPinned(false);
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [visible]);

  useEffect(() => {
    if (!pinned) return;
    const timer = setTimeout(() => setPinned(false), PIN_MS);
    return () => clearTimeout(timer);
  }, [pinned]);

  return (
    <div ref={root} className={className} onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}>
      <button
        type="button"
        aria-pressed={light}
        aria-label="Modo ligero"
        aria-describedby={visible ? panelId : undefined}
        onClick={() => {
          setLight(!light);
          setPinned(true);
          setAnnouncement(`Modo ligero ${light ? "desactivado" : "activado"}`);
        }}
        onFocus={(event) => setFocus(event.currentTarget.matches(":focus-visible"))}
        onBlur={() => setFocus(false)}
        className={`relative flex h-11 min-w-11 shrink-0 items-center justify-center gap-2 outline-none xl:pr-3 xl:pl-2 ${
          light ? "text-texto-sobre-oscuro" : "text-paleta-noche"
        }`}
      >
        <Plate c={9} fill={light ? "var(--color-accion-primaria)" : "var(--color-superficie-panel-suave)"} ring="focus" />
        <svg aria-hidden="true" viewBox="0 0 44 44" className="relative size-11 xl:-mr-1 xl:size-8">
          {/* Una pluma: llena cuando el modo está activo, solo el contorno cuando no. */}
          <path
            d="M31 11C21 11 14 17 12 27l-1 5 5-1c10-2 16-9 15-20z"
            fill={light ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="3"
            strokeLinejoin="round"
          />
          <path d="M12 32 25 19" stroke={light ? "var(--color-accion-primaria)" : "currentColor"} strokeWidth="3" strokeLinecap="round" />
        </svg>
        <span className="relative hidden text-sm font-bold xl:inline">Modo ligero</span>
      </button>
      <span aria-live="polite" className="sr-only">
        {announcement}
      </span>
      {visible && (
        <div className="absolute top-full right-0 z-10 pt-3">
          <div
            id={panelId}
            role="tooltip"
            className="relative w-[min(16rem,calc(100vw-1.5rem))] px-5 pt-4 pb-7 text-left text-texto-principal"
          >
            <Plate c={12} fill="var(--color-superficie-panel)" depth={6} bottom={6} side="var(--color-superficie-borde)" />
            <div className="relative flex flex-col gap-1.5 text-sm leading-snug">
              <p className="font-titulos text-base font-titulo">Modo ligero: {light ? "activado" : "desactivado"}</p>
              <p>{LIGHT_MODE_WHAT}</p>
              <p className="text-texto-secundario">
                {light && pref === "auto"
                  ? "Su equipo pide menos movimiento. Toque para cambiarlo."
                  : `Toque para ${light ? "desactivarlo" : "activarlo"}.`}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** El mismo interruptor, con su explicación a la vista, para el menú del celular. */
export function LightModeSwitch({ onDark = false }: { onDark?: boolean }) {
  const { light, setLight } = useLightMode();
  return (
    <PreferenceSwitch
      label="Modo ligero"
      hint={`${LIGHT_MODE_WHAT} Rinde mejor en celulares básicos.`}
      checked={light}
      onChange={setLight}
      onDark={onDark}
    />
  );
}
