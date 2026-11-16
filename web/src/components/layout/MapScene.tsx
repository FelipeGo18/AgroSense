import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { Footer } from "@/components/layout/Footer";
import { Card } from "@/components/ui/Card";
import { useEntrance } from "@/hooks/useEntrance";

/** Ancho del panel en escritorio: el mapa encuadra a su lado. */
export const PANEL_WIDTH = 440;

/**
 * Una pantalla de la finca con mapa (Figma: «Dibuje su lote», «Mis lotes», «Editar lote»). En escritorio el mapa
 * ocupa todo el fondo y el panel va a la izquierda, con su propio scroll si no cabe. En el celular el mapa va arriba
 * y el panel debajo, en el flujo de la página. El panel entra con la animación de las páginas (`useEntrance`), que en
 * modo ligero no se mueve.
 */
export function MapScene({
  map,
  children,
  panelOpen = true,
  onTogglePanel,
}: {
  map: ReactNode;
  children: ReactNode;
  /** En escritorio, el panel se puede ocultar para ver solo el mapa o la finca (`onTogglePanel`). En el celular el panel
   * va debajo, en el flujo de la página, y siempre se ve. */
  panelOpen?: boolean;
  onTogglePanel?: () => void;
}) {
  const { t } = useTranslation();
  const panel = useEntrance<HTMLDivElement>();
  const toggle =
    "hidden min-h-11 items-center gap-2 rounded-md bg-superficie-panel px-4 font-bold text-oscuro-oliva shadow-md md:inline-flex";
  return (
    <>
      <TopBar />
      <main className="relative min-h-svh bg-paleta-niebla">
        <div className="relative h-[55svh] min-h-[300px] md:fixed md:inset-0 md:h-auto">{map}</div>
        <div
          ref={panel}
          data-lenis-prevent
          className={`relative z-10 -mt-4 px-3 pb-10 md:absolute md:top-[104px] md:left-8 md:mt-0 md:max-h-[calc(100svh-124px)] md:w-[440px] md:overflow-y-auto md:px-0 md:pb-2 ${
            panelOpen ? "" : "md:hidden"
          }`}
        >
          <div data-enter>
            <Card bodyClassName="gap-3 md:px-1">
              {onTogglePanel && (
                <button type="button" onClick={onTogglePanel} className={`${toggle} self-end shadow-none`} aria-expanded={panelOpen}>
                  <span aria-hidden="true">‹</span> {t("lot.panel.hide")}
                </button>
              )}
              {children}
            </Card>
          </div>
        </div>
        {onTogglePanel && !panelOpen && (
          <button type="button" onClick={onTogglePanel} aria-expanded={false} className={`${toggle} absolute top-[104px] left-8 z-10`}>
            {t("lot.panel.show")} <span aria-hidden="true">›</span>
          </button>
        )}
      </main>
      <Footer />
    </>
  );
}
