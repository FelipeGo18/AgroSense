import * as Dialog from "@radix-ui/react-dialog";
import type { CSSProperties, RefObject } from "react";
import { NavLink } from "react-router";
import { useLogout, useSession } from "@/features/auth/session";
import { GUEST, MEMBER, NAV } from "./navLinks";

/**
 * El menú a pantalla completa de las pantallas angostas. Se carga aparte, la primera vez que se abre: así el diálogo
 * no pesa en la carga de ninguna página.
 */
export function MobileMenuPanel({
  open,
  onOpenChange,
  returnFocus,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  returnFocus: RefObject<HTMLButtonElement | null>;
}) {
  const { user } = useSession();
  const logout = useLogout();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Content
          aria-describedby={undefined}
          // El foco vuelve al botón que abrió el menú.
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            returnFocus.current?.focus();
          }}
          data-lenis-prevent
          className="menu-curtain fixed inset-0 z-50 flex flex-col overflow-y-auto bg-paleta-noche px-7 pt-6 pb-10 text-texto-sobre-oscuro outline-none lg:hidden"
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
            {[...NAV, ...(user ? MEMBER : GUEST)].map((item, i) => (
              <NavLink
                key={item.to}
                style={{ "--i": i } as CSSProperties}
                to={item.to}
                end
                onClick={() => onOpenChange(false)}
                className="menu-item py-3 font-titulos text-[26px] font-titulo focus-visible:outline-white aria-[current=page]:text-paleta-trigo"
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
                  onOpenChange(false);
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
