import { useId, type ReactNode } from "react";
import { Plate } from "@/components/ui/Plate";
import { formatHa } from "@/features/farm/lots";

/** Una parte del lote en la barra «Cómo queda el lote». */
export interface Part {
  key: string;
  label: string;
  ha: number;
  /** Lo que se está registrando: va en naranja, como en el diseño. */
  highlight?: boolean;
  /** Terreno libre: borde punteado. */
  free?: boolean;
}

/**
 * «Cómo queda el lote» (Figma: «Registrar la siembra», «Registrar la cosecha»): el lote como una barra partida en lo
 * que ocupa cada siembra y lo libre. Las partes son de área, no de forma: no se dibujan en el mapa (HU-165).
 */
export function LotBar({ parts, total }: { parts: Part[]; total: number }) {
  const shown = parts.filter((part) => part.ha > 0.0001);
  return (
    <figure className="flex flex-col gap-2">
      <div className="flex w-full gap-1" role="img" aria-label={shown.map((p) => `${p.label}: ${formatHa(p.ha)}`).join(", ")}>
        {shown.map((part) => (
          <div key={part.key} className="flex min-w-0 flex-col items-center gap-1" style={{ flexGrow: part.ha / total, flexBasis: 0 }}>
            <span
              className={`flex h-11 w-full min-w-0 items-center justify-center truncate px-1 text-[14px] font-bold ${
                part.highlight
                  ? "border-2 border-paleta-noche bg-paleta-calabaza"
                  : part.free
                    ? "border-2 border-dashed border-superficie-borde bg-superficie-panel"
                    : "border border-superficie-borde bg-[#E3EDCF]"
              }`}
            >
              {part.label}
            </span>
            <span className="text-[13px] text-texto-secundario">{formatHa(part.ha)}</span>
          </div>
        ))}
      </div>
    </figure>
  );
}

export interface Previous {
  id: string;
  title: string;
  note: string;
}

/**
 * «¿Qué había antes en este terreno?»: una o varias siembras cosechadas, o «Nada: es la primera siembra aquí».
 * Casillas nativas: con varias marcadas se juntan terrenos (HU-165).
 */
export function PreviousChoice({
  options,
  value,
  onChange,
}: {
  options: Previous[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const name = useId();
  const toggle = (id: string) => onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);
  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-1 text-[18px] font-bold">¿Qué había antes en este terreno?</legend>
      <p className="-mt-1 mb-1 text-[15px] text-texto-secundario">Marque una o varias. Si junta terrenos, márquelos todos.</p>
      {options.map((option) => (
        <Box
          key={option.id}
          name={name}
          checked={value.includes(option.id)}
          onChange={() => toggle(option.id)}
          title={option.title}
          note={option.note}
        />
      ))}
      <Box
        name={name}
        checked={value.length === 0}
        onChange={() => onChange([])}
        title="Nada: es la primera siembra aquí"
        note="Tierra del lote que no había sembrado"
      />
    </fieldset>
  );
}

function Box({
  name,
  checked,
  onChange,
  title,
  note,
}: {
  name: string;
  checked: boolean;
  onChange: () => void;
  title: string;
  note: ReactNode;
}) {
  return (
    <label className="relative flex min-h-16 cursor-pointer items-center gap-4 px-4 py-3">
      <Plate
        c={12}
        fill={checked ? "#FFF6EA" : "var(--color-superficie-panel)"}
        stroke={checked ? "var(--color-paleta-calabaza)" : "var(--color-superficie-borde)"}
        strokeWidth={checked ? 3 : 2}
      />
      <input type="checkbox" name={name} checked={checked} onChange={onChange} className="peer absolute inset-0 cursor-pointer opacity-0" />
      <span
        aria-hidden="true"
        className={`pointer-events-none relative grid size-7 shrink-0 place-items-center border-2 border-paleta-noche ${checked ? "bg-accion-primaria" : "bg-superficie-panel"}`}
      >
        {checked && (
          <svg viewBox="0 0 16 16" className="size-4">
            <path d="M3 8.5 L6.5 12 L13 4.5" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        )}
      </span>
      <span className="pointer-events-none relative flex min-w-0 flex-col">
        <span className="font-bold">{title}</span>
        <span className="text-[14px] text-texto-secundario">{note}</span>
      </span>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 peer-focus-visible:outline-3 peer-focus-visible:outline-accion-foco"
      />
    </label>
  );
}
