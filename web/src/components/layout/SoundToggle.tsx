import { Plate } from "@/components/ui/Plate";
import { useSound } from "@/hooks/useSound";

/** Prende y apaga el sonido de la interfaz. Arranca apagado; el altavoz tachado dice que está en silencio. */
export function SoundToggle({ className = "" }: { className?: string }) {
  const [enabled, setEnabled] = useSound();
  return (
    <button
      type="button"
      aria-pressed={enabled}
      aria-label="Sonido"
      title={enabled ? "Quitar el sonido" : "Poner el sonido"}
      onClick={() => setEnabled(!enabled)}
      className={`relative flex size-11 shrink-0 items-center justify-center outline-none ${className}`}
    >
      <Plate c={9} fill="var(--color-superficie-panel-suave)" ring="focus" />
      <svg aria-hidden="true" viewBox="0 0 44 44" className="relative size-11">
        <polygon points="11,18 17,18 25,11 25,33 17,26 11,26" fill="var(--color-paleta-noche)" />
        {enabled ? (
          <path
            d="M29 17 Q33 22 29 27 M32.5 13 Q39 22 32.5 31"
            fill="none"
            stroke="var(--color-paleta-noche)"
            strokeWidth="3"
            strokeLinecap="round"
          />
        ) : (
          <path d="M30 16 L38 28 M38 16 L30 28" stroke="var(--color-paleta-noche)" strokeWidth="3" strokeLinecap="round" />
        )}
      </svg>
    </button>
  );
}
