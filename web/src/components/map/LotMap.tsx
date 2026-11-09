import { Suspense, lazy, useState, type ReactNode } from "react";
import { Plate } from "@/components/ui/Plate";
import type { Boundary, LotPolygon } from "@/features/farm/geo";
import { useAnimated } from "@/hooks/useLightMode";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import type { DrawMode, Editing, MapControls, MapLot } from "./MapCanvas";

// MapLibre pesa: se descarga solo en las páginas que muestran el mapa.
const MapCanvas = lazy(() => import("./MapCanvas"));

export type { DrawMode, MapLot };

export interface LotDrawing {
  geometry: LotPolygon | null;
  onChange: (geometry: LotPolygon | null) => void;
  mode: DrawMode;
  onModeChange: (mode: DrawMode) => void;
  areaLabel?: string;
  outside?: boolean;
}

export interface LotMapProps {
  boundary: Boundary | null;
  focus?: LotPolygon | null;
  lots?: MapLot[];
  onLotClick?: (id: string) => void;
  /** Con esto el mapa dibuja: barra de Dibujar, Mover puntos, Deshacer y Borrar. */
  drawing?: LotDrawing;
  /** Lo que se muestra si el navegador no puede con el mapa (por ejemplo, el enlace a escribir el área a mano). */
  fallback?: ReactNode;
  /** Espacio que tapa el panel en escritorio, para encuadrar a su lado. */
  panelWidth?: number;
}

/**
 * El mapa del lote con sus controles (Figma: «Dibuje su lote», «Mis lotes», «Editar lote»). Guarda el historial del
 * dibujo para «Deshacer». Si el navegador no puede mostrar el mapa, lo dice y deja seguir sin él.
 */
export function LotMap({ boundary, focus = null, lots, onLotClick, drawing, fallback, panelWidth = 0 }: LotMapProps) {
  const animated = useAnimated();
  // En escritorio el panel tapa la izquierda del mapa; en el celular va debajo y el mapa es todo visible.
  const wide = useMediaQuery("(min-width: 768px)");
  const [failed, setFailed] = useState(false);
  const [controls, setControls] = useState<MapControls | null>(null);
  // Lo que se dibujó antes de cada cambio, para «Deshacer».
  const [history, setHistory] = useState<(LotPolygon | null)[]>([]);

  const change = (geometry: LotPolygon | null) => {
    if (!drawing) return;
    setHistory((past) => [...past, drawing.geometry]);
    drawing.onChange(geometry);
  };
  const undo = () => {
    if (!drawing || history.length === 0) return;
    const previous = history[history.length - 1];
    setHistory(history.slice(0, -1));
    drawing.onChange(previous);
    drawing.onModeChange(previous ? "move" : "draw");
  };
  const editing: Editing | undefined = drawing && { ...drawing, onChange: change };

  if (failed) {
    return (
      <div className="absolute inset-0 grid place-items-center bg-paleta-niebla p-6">
        <div role="status" className="max-w-[360px] text-center">
          <p className="font-bold">Su navegador no puede mostrar el mapa.</p>
          {fallback}
        </div>
      </div>
    );
  }
  return (
    <div className="absolute inset-0 bg-[#E9EEE2]">
      <Suspense
        fallback={
          <p role="status" className="absolute inset-0 grid place-items-center font-bold text-texto-secundario">
            Cargando el mapa…
          </p>
        }
      >
        <MapCanvas
          animated={animated}
          boundary={boundary}
          focus={focus}
          lots={lots}
          onLotClick={onLotClick}
          editing={editing}
          padding={
            wide
              ? { top: 120, bottom: drawing ? 140 : 60, left: panelWidth + 40, right: 90 }
              : { top: 90, bottom: drawing ? 110 : 30, left: 24, right: 72 }
          }
          onReady={setControls}
          onFail={() => setFailed(true)}
        />
      </Suspense>
      {controls && (
        <div className="absolute top-[104px] right-3 z-10 flex flex-col gap-2 md:right-6">
          <MapButton label="Acercar" onClick={controls.zoomIn}>
            <path d="M12 5v14M5 12h14" />
          </MapButton>
          <MapButton label="Alejar" onClick={controls.zoomOut}>
            <path d="M5 12h14" />
          </MapButton>
        </div>
      )}
      {controls && drawing && (
        <div
          role="toolbar"
          aria-label="Dibujo del lote"
          className="absolute inset-x-3 bottom-8 z-10 mx-auto flex max-w-[420px] justify-around px-2 py-2 md:left-[480px]"
        >
          <Plate c={12} fill="var(--color-superficie-panel)" depth={6} bottom={6} side="var(--color-superficie-borde)" />
          <Tool
            label="Dibujar"
            active={drawing.mode === "draw"}
            onClick={() => {
              if (drawing.geometry) change(null);
              drawing.onModeChange("draw");
            }}
          >
            <path d="M5 7 L17 5 L19 17 L7 19 Z" />
          </Tool>
          <Tool
            label="Mover puntos"
            active={drawing.mode === "move"}
            disabled={!drawing.geometry}
            onClick={() => drawing.onModeChange("move")}
          >
            <path d="M12 3v18M3 12h18M12 3l-3 3M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3" />
          </Tool>
          <Tool label="Deshacer" disabled={history.length === 0} onClick={undo}>
            <path d="M9 7 L4 12 L9 17 M4 12 h10 a5 5 0 0 1 0 10 h-3" />
          </Tool>
          <Tool
            label="Borrar"
            disabled={!drawing.geometry}
            onClick={() => {
              change(null);
              drawing.onModeChange("draw");
            }}
          >
            <path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13" />
          </Tool>
        </div>
      )}
    </div>
  );
}

function MapButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} className="relative grid size-12 place-items-center">
      <Plate c={8} fill="var(--color-superficie-panel)" depth={5} bottom={5} side="var(--color-superficie-borde)" />
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="relative size-6"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      >
        {children}
      </svg>
    </button>
  );
}

function Tool({
  label,
  active = false,
  disabled = false,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className="relative flex min-h-11 min-w-16 flex-col items-center gap-1 px-1 py-1 text-[13px] disabled:opacity-40"
    >
      <span className={`grid size-10 place-items-center ${active ? "bg-paleta-noche text-texto-sobre-oscuro" : ""}`}>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="size-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {children}
        </svg>
      </span>
      <span className={active ? "font-bold" : ""}>{label}</span>
    </button>
  );
}
