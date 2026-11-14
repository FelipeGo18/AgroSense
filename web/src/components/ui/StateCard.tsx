import type { ReactNode } from "react";
import { Plate } from "./Plate";
import { Button } from "./Button";
import { Mascot, type MascotMood } from "@/components/mascot/Mascot";

export interface StateCardAction {
  label: string;
  variant?: "primary" | "secondary";
  onClick: () => void;
}

export interface StateCardProps {
  title: string;
  description: ReactNode;
  /** Expresión de la mascota Sputnik: reposo (idle), guía (guide) o sin datos (no_data). */
  mood?: MascotMood;
  /** Borde punteado: para municipios sin cobertura (R1: no hay datos, no es un error de fallo). */
  dashed?: boolean;
  /** Código para rastrear el fallo en soporte técnico (el request_id de la API). */
  code?: string | null;
  /** Botones para que el usuario sepa qué hacer (Reintentar, Cambiar fecha, etc.). */
  actions?: StateCardAction[];
  className?: string;
}

/**
 * Tarjeta de estado para cuando algo carga, falla o no tiene datos (HU-094; W6).
 * Sigue el diseño oficial de `design/pantallas/estados_resultado.py` y `transversal.py:state_card`.
 */
export function StateCard({
  title,
  description,
  mood = "idle",
  dashed = false,
  code,
  actions = [],
  className = "",
}: Readonly<StateCardProps>) {
  const getActionVariant = (action: StateCardAction, index: number) => {
    return action.variant ?? (index === 0 ? "primary" : "secondary");
  };

  return (
    <div role={dashed ? "status" : "alert"} className={`relative block px-6 pt-5 pb-8 ${className}`}>
      {/* Fondo biselado del estilo diorama (Plate). Si es dashed, dibuja borde punteado. */}
      <Plate
        c={16}
        fill="var(--color-superficie-panel)"
        depth={8}
        bottom={8}
        side="var(--color-superficie-borde)"
        stroke={dashed ? "var(--color-oscuro-cielo)" : undefined}
        strokeWidth={dashed ? 2 : undefined}
        dash={dashed ? "6 5" : undefined}
      />
      <div className="relative flex flex-col gap-3">
        {/* Encabezado: Título y la mascota en la esquina derecha */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="font-titulos text-[20px] leading-tight font-semibold text-texto-principal sm:text-[22px]">{title}</h3>
          <Mascot mood={mood} size={76} decorative className="-mt-2 -mr-1 shrink-0" />
        </div>
        {/* Explicación en texto claro */}
        <div className="max-w-[520px] text-[15px] leading-relaxed text-texto-secundario">{description}</div>
        {/* Código de soporte técnico si existió un error del servidor */}
        {code && (
          <div className="relative mt-1 inline-flex items-center self-start px-3.5 py-1.5 text-[14px] font-bold text-texto-principal">
            <Plate c={6} fill="var(--color-paleta-niebla)" />
            <span className="relative">
              Código para soporte: <span className="font-mono">{code}</span>
            </span>
          </div>
        )}
        {/* Botones de acción */}
        {actions.length > 0 && (
          <div className="mt-2 flex flex-col flex-wrap gap-3 sm:flex-row">
            {actions.map((act, index) => (
              <Button key={act.label} variant={getActionVariant(act, index)} onClick={act.onClick} className="w-full sm:w-auto">
                {act.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
