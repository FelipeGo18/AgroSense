import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { Button } from "./Button";
import { Plate } from "./Plate";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Qué va a pasar, en palabras claras. */
  children: ReactNode;
  /** El botón que sigue adelante; va en rojo: es para lo que no se puede deshacer. */
  confirmLabel: string;
  /** El botón que no hace nada; es el que queda con el foco al abrir. */
  cancelLabel: string;
  onConfirm: () => void;
  busy?: boolean;
  busyLabel?: string;
}

/** Diálogo para confirmar algo que no se puede deshacer. Se cierra con Escape y el foco no se sale de él. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  children,
  confirmLabel,
  cancelLabel,
  onConfirm,
  busy = false,
  busyLabel,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay fixed inset-0 z-50 bg-paleta-noche/60" />
        <Dialog.Content
          data-lenis-prevent
          aria-describedby={undefined}
          className="dialog-card fixed top-1/2 left-1/2 z-50 max-h-[calc(100svh-24px)] w-[min(620px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto px-6 pt-6 pb-9 outline-none md:px-10 md:pt-8"
        >
          <Plate c={18} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" />
          <div className="relative flex flex-col gap-4">
            <Dialog.Title className="text-[clamp(1.5rem,3vw,2.25rem)]">{title}</Dialog.Title>
            {children}
            <div className="mt-1 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
              <Dialog.Close asChild>
                <Button autoFocus disabled={busy} className="sm:w-[250px]">
                  {cancelLabel}
                </Button>
              </Dialog.Close>
              <Button variant="danger" onClick={onConfirm} loading={busy} loadingText={busyLabel} className="sm:w-[250px]">
                {confirmLabel}
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
