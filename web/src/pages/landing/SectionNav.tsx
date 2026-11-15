import { useScroll } from "@/components/layout/SmoothScroll";
import { STOPS, type StopId } from "./content";

/** Las paradas del recorrido, al borde de la pantalla: dice en cuál va y lleva a cualquiera. Solo en pantallas anchas. */
export function SectionNav({ active }: { active: StopId }) {
  const { scrollTo } = useScroll();
  const current = STOPS.findIndex((stop) => stop.id === active);
  return (
    <nav aria-label="Paradas del recorrido" className="fixed top-1/2 right-5 z-30 hidden -translate-y-1/2 lg:block">
      <ol className="flex flex-col gap-1">
        {STOPS.map((stop, i) => (
          <li key={stop.id}>
            <a
              href={`#${stop.id}`}
              aria-current={i === current ? "step" : undefined}
              onClick={(event) => {
                event.preventDefault();
                scrollTo(stop.id);
              }}
              className="group relative flex size-8 items-center justify-center"
            >
              <span
                aria-hidden="true"
                className={`block size-3 rotate-45 border-2 border-paleta-noche shadow-[0_0_0_2px_rgb(255_255_255/0.75)] transition-transform group-hover:scale-125 motion-reduce:transition-none ${
                  i === current ? "bg-paleta-calabaza" : i < current ? "bg-paleta-noche" : "bg-white"
                }`}
              />
              <span className="pointer-events-none absolute right-9 rounded-sm bg-paleta-noche px-2 py-1 text-xs whitespace-nowrap text-texto-sobre-oscuro opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100">
                {stop.label}
              </span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
