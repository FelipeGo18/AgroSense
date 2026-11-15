import { useEffect, useId, useRef, useState } from "react";
import { useMotionEffect } from "@/hooks/useMotionEffect";
import { gsap } from "@/lib/motion";
import { allocateCells, drawStage, timeOfDay, DRAWN_CROPS, type LiveSeason } from "./cells";
import { FarmAnimals } from "./Animals";
import { FarmFireflies, FarmLifeSky, FarmLifeWorld, type FarmAnchors } from "./FarmLife";

/** Las piezas que exporta el diseño (`design/finca/exportar_web.py`): se descargan solo al abrir el lote vivo. */
interface DioramaBase {
  width: number;
  height: number;
  horizon: number;
  lot: { x: number; y: number; scale: number };
  sky: Record<string, string>;
  tint: Record<string, string>;
  free: string;
  layouts: Record<
    string,
    {
      cells: { i: number; j: number; x: number; y: number }[];
      ground: string;
      back: string;
      front: string;
      dog: string;
      top: number;
      anchors: FarmAnchors;
    }
  >;
}
type CropStages = Record<string, string>;

const cropFiles = import.meta.glob<CropStages>("./diorama/crops/*.json", { import: "default" });
const loadBase = () => import("./diorama/base.json").then((m) => m.default as unknown as DioramaBase);
/** Ancho del rótulo según su texto, como `tag` de escena.py. */
const labelWidth = (label: { title: string; sub: string }) => Math.max(label.title.length * 8.6, label.sub.length * 7) + 22;
const isDrawn = (cropId: string) => (DRAWN_CROPS as readonly string[]).includes(cropId);

/** Un fragmento de SVG del diseño. Viene del propio repositorio (el exportador del diseño), nunca de quien usa la web. */
function Svg({ markup, ...props }: { markup: string } & React.SVGProps<SVGGElement>) {
  return <g {...props} dangerouslySetInnerHTML={{ __html: markup }} />;
}

/**
 * El lote vivo (HU-187): el diorama del lote con la finca alrededor (casa, cerca, huerta, árbol y el perro) y cada
 * siembra en curso ocupando tantos cubos como su parte del área, dibujada en su etapa (por calendario, HU-220). El cielo
 * sigue la hora local. Es una ilustración: no mide nada del lote (R5, R10).
 *
 * Con movimiento, las plantas se mecen con el viento; en modo ligero el dibujo es el mismo, quieto (HU-158).
 */
export function LiveLot({
  seasons,
  lotAreaHa,
  cropName,
  animated,
  now,
}: {
  seasons: LiveSeason[];
  lotAreaHa: number;
  cropName: (cropId: string) => string;
  animated: boolean;
  now?: Date;
}) {
  const clip = useId();
  const root = useRef<SVGSVGElement>(null);
  const [base, setBase] = useState<DioramaBase | null>(null);
  const [crops, setCrops] = useState<Record<string, CropStages>>({});
  // La hora se vuelve a mirar cada minuto: el lote se hace de tarde y de noche solo, sin recargar.
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => {
    if (now) return;
    const id = window.setInterval(() => setClock(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, [now]);
  const drawn = [...new Set(seasons.map((s) => s.cropId).filter(isDrawn))].sort();

  useEffect(() => {
    let alive = true;
    void loadBase().then((data) => alive && setBase(data));
    return () => {
      alive = false;
    };
  }, []);
  const key = drawn.join(",");
  useEffect(() => {
    let alive = true;
    void Promise.all(drawn.map(async (id) => [id, await cropFiles[`./diorama/crops/${id}.json`]()] as const)).then(
      (pairs) => alive && setCrops(Object.fromEntries(pairs)),
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` resume la lista de cultivos del lote
  }, [key]);

  // Con la pestaña oculta, todo se queda quieto: SMIL se pausa y el CSS también (`farm-paused`).
  useEffect(() => {
    const svg = root.current;
    if (!svg || !animated) return;
    const sync = () => {
      const hidden = document.visibilityState === "hidden";
      if (hidden) svg.pauseAnimations?.();
      else svg.unpauseAnimations?.();
      svg.classList.toggle("farm-paused", hidden);
    };
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, [animated, base]);

  // 10. Al llegar a su finca, las camas suben desde el suelo una tras otra (solo con movimiento).
  useMotionEffect(
    () => {
      if (!animated || !base) return;
      gsap.from("[data-bed]", { y: 36, opacity: 0, duration: 0.6, ease: "back.out(1.6)", stagger: 0.12, clearProps: "opacity,transform" });
    },
    { scope: root, dependencies: [animated, Boolean(base)] },
  );

  if (!base) {
    return (
      <div role="status" className="flex size-full items-center justify-center bg-paleta-niebla text-texto-secundario">
        Dibujando su lote…
      </div>
    );
  }
  const time = timeOfDay(now ?? clock);
  const { layout, cells } = allocateCells(seasons, lotAreaHa);
  const shape = base.layouts[layout];
  const place = `translate(${base.lot.x} ${base.lot.y}) scale(${base.lot.scale})`;
  // Los cubos se dibujan de atrás hacia adelante, como en el diseño.
  const order = shape.cells.map((cell, index) => ({ ...cell, index })).sort((a, b) => a.i + a.j - (b.i + b.j) || a.i - b.i);
  const xs = shape.cells.map((cell) => cell.x);
  const minX = Math.min(...xs);
  const spanX = Math.max(Math.max(...xs) - minX, 1);
  // Los cubos con cultivos en flor (etapa media o final), donde zumban las abejas.
  const flowering = shape.cells
    .filter((_, index) => {
      const stage = cells[index].season?.stage;
      return stage === "mid" || stage === "late";
    })
    .map((cell) => [cell.x, cell.y] as [number, number]);
  // Un rótulo por siembra, sobre su primer cubo.
  const labelled = new Set<string>();
  const labels: { x: number; y: number; title: string; sub: string }[] = [];
  shape.cells.forEach((cell, index) => {
    const season = cells[index].season;
    const id = season?.seasonId ?? "libre";
    if (labelled.has(id)) return;
    labelled.add(id);
    const free = Math.max(lotAreaHa - seasons.reduce((sum, s) => sum + s.areaHa, 0), 0);
    labels.push({
      x: base.lot.x + cell.x * base.lot.scale,
      y: base.lot.y + (cell.y + shape.top) * base.lot.scale,
      title: season ? cropName(season.cropId) : "Libre",
      sub: `${(season ? season.areaHa : free).toLocaleString("es-CO", { maximumFractionDigits: 2 })} ha`,
    });
  });

  return (
    <div className="relative size-full">
      <svg
        ref={root}
        viewBox={`0 0 ${base.width} ${base.height}`}
        preserveAspectRatio="xMidYMid slice"
        className="size-full"
        role="img"
        aria-label={`Ilustración de su lote: ${labels.map((l) => `${l.title}, ${l.sub}`).join("; ")}`}
      >
        <Svg markup={base.sky[time]} />
        <defs>
          <clipPath id={clip}>
            <rect y={base.horizon} width={base.width} height={base.height} />
          </clipPath>
        </defs>
        <g clipPath={`url(#${clip})`}>
          <Svg markup={shape.ground} transform={place} />
        </g>
        <g>
          <Svg markup={shape.back} transform={place} />
          <g transform={place}>
            {order.map(({ x, y, index }) => {
              const season = cells[index].season;
              const markup = season && isDrawn(season.cropId) ? crops[season.cropId]?.[String(drawStage(season.stage))] : base.free;
              return (
                <g key={index} transform={`translate(${x} ${y})`}>
                  <g data-bed>
                    {/* 5. La ola de viento cruza las camas de izquierda a derecha: cada cama se inclina un poco después. */}
                    <Svg
                      markup={markup ?? base.free}
                      className={animated && season ? "live-sway" : undefined}
                      style={{ animationDelay: `${((x - minX) / spanX) * 1.2}s` }}
                    />
                  </g>
                </g>
              );
            })}
          </g>
          {/* Los animales van delante de las camas y detrás de las cercas del frente y del potrero. */}
          <g transform={place}>
            <FarmAnimals anchors={shape.anchors} dogMarkup={shape.dog} animated={animated} />
          </g>
          <Svg markup={shape.front} transform={place} />
          {animated && (
            <g transform={place}>
              <FarmLifeWorld anchors={shape.anchors} time={time} flowering={flowering} />
            </g>
          )}
        </g>
        {/* Las mariposas y el viento cruzan por encima de la finca (el pasto llena toda la vista). */}
        {animated && <FarmLifeSky width={base.width} height={base.height} time={time} />}
        {base.tint[time] && <Svg markup={base.tint[time]} />}
        {animated && time === "noche" && (
          <g transform={place}>
            <FarmFireflies anchors={shape.anchors} />
          </g>
        )}
        {labels.map((label) => (
          <g key={`${label.title}-${label.x}`} transform={`translate(${label.x} ${label.y})`} aria-hidden="true">
            <rect
              x={-labelWidth(label) / 2}
              y={-46}
              width={labelWidth(label)}
              height={40}
              rx={6}
              fill="#FFFFFF"
              stroke="#1E2A3A"
              strokeWidth={1.5}
            />
            <polygon points="-6,-6 6,-6 0,2" fill="#1E2A3A" />
            <text y={-29} textAnchor="middle" fontSize={14} fontWeight={700} fill="#1E2A3A">
              {label.title}
            </text>
            <text y={-13} textAnchor="middle" fontSize={12} fill="#4A5868">
              {label.sub}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
