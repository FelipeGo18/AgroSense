import { Plate } from "./Plate";

export interface PreferenceSwitchProps {
  label: string;
  /** Qué hace, en una frase. */
  hint: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  /** Sobre fondo oscuro (el menú del celular) el texto es claro. */
  onDark?: boolean;
}

const KNOB = "polygon(5px 0,calc(100% - 5px) 0,100% 5px,100% calc(100% - 5px),calc(100% - 5px) 100%,5px 100%,0 calc(100% - 5px),0 5px)";

/**
 * Interruptor de una preferencia, con su nombre y lo que hace. El estado se dice con texto («Activado») y con la
 * posición de la perilla, nunca solo con el color.
 */
export function PreferenceSwitch({ label, hint, checked, onChange, onDark = false }: PreferenceSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`flex min-h-tactil-minimo w-full items-start gap-4 py-3 text-left outline-none focus-visible:outline-3 focus-visible:outline-offset-4 ${
        onDark ? "text-texto-sobre-oscuro focus-visible:outline-white" : "text-texto-principal"
      }`}
    >
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <strong>{label}</strong>
        <span className={`text-sm leading-snug ${onDark ? "text-paleta-niebla" : "text-texto-secundario"}`}>{hint}</span>
      </span>
      <span className="flex shrink-0 flex-col items-center gap-1">
        <span aria-hidden="true" className="relative block h-8 w-14">
          <Plate c={8} fill={checked ? "var(--color-accion-primaria)" : "var(--color-superficie-panel-suave)"} depth={4} bottom={4} />
          <span
            style={{ clipPath: KNOB }}
            className={`absolute top-[3px] size-[22px] ${checked ? "left-[31px] bg-texto-sobre-oscuro" : "left-[4px] bg-paleta-noche"}`}
          />
        </span>
        <span className="text-xs font-bold">{checked ? "Activado" : "Desactivado"}</span>
      </span>
    </button>
  );
}
