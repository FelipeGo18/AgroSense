import { useScroll } from "@/components/layout/SmoothScroll";
import { MascotSlot } from "@/components/mascot/MascotGuide";
import { Plate } from "@/components/ui/Plate";
import { GUIDE, type StopId } from "./content";

/**
 * La mascota en una parada: su lugar y lo que dice, con el enlace a la parada siguiente.
 * El texto va en HTML: la mascota es decoración y nunca es la única forma de decirlo.
 */
export function GuideNote({ stop, className = "" }: { stop: Exclude<StopId, "inicio">; className?: string }) {
  const { scrollTo } = useScroll();
  const { say, mood, next, nextLabel } = GUIDE[stop];
  const target = next ?? "inicio";
  return (
    <div data-reveal="right" className={`flex items-end gap-2 ${className}`}>
      <MascotSlot id={stop} mood={mood} className="w-[92px] md:w-[132px]" />
      <div className="relative mb-3 max-w-[19rem] px-4 pt-3 pb-4 text-sm">
        <Plate c={12} fill="var(--color-superficie-panel)" stroke="var(--color-paleta-noche)" strokeWidth={2.5} />
        <p className="relative">{say}</p>
        <a
          href={`#${target}`}
          onClick={(event) => {
            event.preventDefault();
            scrollTo(target);
          }}
          className="relative mt-1 inline-flex min-h-11 items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4"
        >
          {nextLabel} <span aria-hidden="true">{next ? "↓" : "↑"}</span>
        </a>
      </div>
    </div>
  );
}
