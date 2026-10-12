import { useId } from "react";

export interface ToggleProps {
  label: string;
  /** Qué hace, en una línea, bajo el nombre. */
  note?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

/** Interruptor del kit: una semilla que corre por un riel biselado. Dice su estado con forma y posición, no solo con color. */
export function Toggle({ label, note, checked, onChange, disabled = false }: ToggleProps) {
  const id = useId();
  const x = checked ? 44 : 20;
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p id={`${id}-label`} className="font-bold">
          {label}
        </p>
        {note && (
          <p id={`${id}-note`} className="text-[15px] leading-snug text-texto-secundario">
            {note}
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={`${id}-label`}
        aria-describedby={note ? `${id}-note` : undefined}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className="shrink-0 p-1 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg aria-hidden="true" viewBox="0 0 64 40" className="h-10 w-16 overflow-visible">
          <polygon
            points="10,6 54,6 64,16 64,24 54,34 10,34 0,24 0,16"
            fill={checked ? "var(--color-oscuro-oliva)" : "var(--color-paleta-niebla)"}
            stroke={checked ? "var(--color-oscuro-oliva)" : "var(--color-superficie-borde)"}
            strokeWidth="2.5"
          />
          <polygon
            points={`${x},2 ${x + 13},12 ${x + 13},28 ${x},38 ${x - 13},28 ${x - 13},12`}
            fill={checked ? "var(--color-paleta-brote)" : "var(--color-superficie-panel)"}
            stroke={checked ? "var(--color-oscuro-brote)" : "var(--color-oscuro-cielo)"}
            strokeWidth="2.5"
          />
        </svg>
      </button>
    </div>
  );
}
