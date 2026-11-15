import { useEffect, useRef, useState } from "react";
import { Cow, Hen, RunningDog, type FarmAnchors, type Pt } from "./FarmLife";

/**
 * Los animales de la finca en el lote vivo (HU-187), con reglas: cada uno vive en su zona y nunca sale de ella.
 *
 * - Las vacas, en el potrero cercado (`anchors.pasture`): caminan despacio a un punto del potrero, se paran a pastar y
 *   eligen otro.
 * - Las gallinas, en el patio frente a la casa (`anchors.yard`): caminan, picotean y cambian de sitio.
 * - El perro duerme en su sitio (`anchors.dog`) y de vez en cuando sale detrás de una gallina del patio; la gallina huye
 *   dentro del patio y, al rato, el perro vuelve a dormir.
 *
 * Las zonas son cuadriláteros del dibujo (las esquinas en coordenadas del lote): un punto adentro se arma con dos números
 * de 0 a 1, así que ningún animal pisa la casa, los árboles, el estanque ni la cerca. Cada animal mira hacia donde
 * camina. Con la pestaña oculta no se mueve nada; en modo ligero (`animated` falso) quedan quietos en su sitio.
 */

type Zone = [Pt, Pt, Pt, Pt];
interface Walker {
  x: number;
  y: number;
  tx: number;
  ty: number;
  /** Segundos que le quedan quieto (pastando o picoteando) antes de elegir otro sitio. */
  rest: number;
  /** Hacia dónde mira: 1 a la derecha, -1 a la izquierda. */
  face: 1 | -1;
}
interface Dog extends Walker {
  mode: "sleeping" | "chasing" | "returning";
  /** Segundos hasta la próxima carrera, o los que le quedan de carrera. */
  timer: number;
  prey: number;
}

/** Un punto del cuadrilátero con `u`, `v` de 0 a 1 (la proyección isométrica conserva los paralelogramos). */
function inside([p0, p1, p2, p3]: Zone, u: number, v: number): Pt {
  const top = [p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u];
  const bottom = [p3[0] + (p2[0] - p3[0]) * u, p3[1] + (p2[1] - p3[1]) * u];
  return [top[0] + (bottom[0] - top[0]) * v, top[1] + (bottom[1] - top[1]) * v];
}
/** Un punto al azar adentro, con un margen para que el animal no quede encima de la cerca. */
const somewhere = (zone: Zone, margin = 0.15): Pt =>
  inside(zone, margin + Math.random() * (1 - 2 * margin), margin + Math.random() * (1 - 2 * margin));

function walker(zone: Zone, u: number, v: number): Walker {
  const [x, y] = inside(zone, u, v);
  return { x, y, tx: x, ty: y, rest: 1 + Math.random() * 4, face: 1 };
}

/** Avanza `w` hacia su destino a `speed` unidades por segundo; devuelve si llegó. */
function step(w: Walker, speed: number, dt: number): boolean {
  const dx = w.tx - w.x;
  const dy = w.ty - w.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 1) return true;
  const move = Math.min(distance, speed * dt);
  w.x += (dx / distance) * move;
  w.y += (dy / distance) * move;
  if (Math.abs(dx) > 0.5) w.face = dx > 0 ? 1 : -1;
  return false;
}

/** Camina, descansa y elige otro sitio de su zona. */
function wander(w: Walker, zone: Zone, speed: number, restMin: number, restMax: number, dt: number) {
  if (w.rest > 0) {
    w.rest -= dt;
    if (w.rest <= 0) [w.tx, w.ty] = somewhere(zone);
    return;
  }
  if (step(w, speed, dt)) w.rest = restMin + Math.random() * (restMax - restMin);
}

/**
 * Cada cuánto se repinta el dibujo de los animales: en el celular, a unos 30 cuadros por segundo (uno de cada dos a 60);
 * si no, en cada cuadro. El margen de 2 ms evita saltarse un cuadro por los decimales del reloj.
 */
export const paintEvery = (few: boolean) => (few ? 1000 / 30 - 2 : 0);
export const shouldPaint = (now: number, painted: number, few: boolean) => now - painted >= paintEvery(few);

const COW_START: [number, number][] = [
  [0.25, 0.3],
  [0.7, 0.55],
  [0.4, 0.8],
];
const HEN_START: [number, number][] = [
  [0.3, 0.3],
  [0.65, 0.4],
  [0.4, 0.7],
  [0.8, 0.75],
];

export function FarmAnimals({
  anchors,
  dogMarkup,
  animated,
  few = false,
}: {
  anchors: FarmAnchors;
  dogMarkup: string;
  animated: boolean;
  /** En el celular, el dibujo se repinta a unos 30 cuadros por segundo en vez de 60: el movimiento es el mismo. */
  few?: boolean;
}) {
  const pasture = anchors.pasture as Zone;
  const yard = anchors.yard as Zone;
  const cows = useRef(COW_START.map(([u, v]) => walker(pasture, u, v)));
  const hens = useRef(HEN_START.map(([u, v]) => walker(yard, u, v)));
  const dog = useRef<Dog>({
    x: anchors.dog[0],
    y: anchors.dog[1],
    tx: anchors.dog[0],
    ty: anchors.dog[1],
    rest: 0,
    face: 1,
    mode: "sleeping",
    timer: 8 + Math.random() * 10,
    prey: 0,
  });
  const [, setFrame] = useState(0);

  useEffect(() => {
    if (!animated) return;
    let last = performance.now();
    let painted = 0;
    let id = requestAnimationFrame(function tick(now) {
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      if (document.visibilityState !== "hidden") {
        for (const cow of cows.current) wander(cow, pasture, 9, 4, 10, dt);
        const d = dog.current;
        hens.current.forEach((hen, index) => {
          if (d.mode === "chasing" && index === d.prey) {
            // La gallina perseguida huye: al punto del patio más lejos del perro, más rápido.
            if (step(hen, 70, dt) || Math.hypot(hen.x - d.x, hen.y - d.y) < 60) {
              const options = [0, 1, 2, 3].map(() => somewhere(yard, 0.08));
              [hen.tx, hen.ty] = options.reduce((best, p) =>
                Math.hypot(p[0] - d.x, p[1] - d.y) > Math.hypot(best[0] - d.x, best[1] - d.y) ? p : best,
              );
            }
          } else {
            wander(hen, yard, 22, 1.5, 4, dt);
          }
        });
        d.timer -= dt;
        if (d.mode === "sleeping" && d.timer <= 0) {
          d.mode = "chasing";
          d.timer = 6 + Math.random() * 3;
          d.prey = Math.floor(Math.random() * hens.current.length);
        }
        if (d.mode === "chasing") {
          const hen = hens.current[d.prey];
          [d.tx, d.ty] = [hen.x, hen.y];
          step(d, 85, dt);
          if (d.timer <= 0) {
            d.mode = "returning";
            [d.tx, d.ty] = anchors.dog;
          }
        } else if (d.mode === "returning" && step(d, 60, dt)) {
          d.mode = "sleeping";
          d.face = 1;
          d.timer = 20 + Math.random() * 20;
        }
        if (shouldPaint(now, painted, few)) {
          painted = now;
          setFrame((n) => (n + 1) % 1_000_000);
        }
      }
      id = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(id);
  }, [animated, few, pasture, yard, anchors.dog]);

  const d = dog.current;
  // De atrás hacia adelante: el que está más abajo en la pantalla tapa al de atrás.
  const animals = [
    ...cows.current.map((w, i) => ({ key: `vaca-${i}`, w, node: <Cow /> })),
    ...hens.current.map((w, i) => ({ key: `gallina-${i}`, w, node: <Hen x={0} y={0} pecking={w.rest > 0} delay={i * 0.5} /> })),
    ...(d.mode === "sleeping" ? [] : [{ key: "perro", w: d as Walker, node: <RunningDog /> }]),
  ].sort((a, b) => a.w.y - b.w.y);

  return (
    <g aria-hidden="true">
      {d.mode === "sleeping" && (
        <g transform={`translate(${anchors.dog[0]} ${anchors.dog[1]})`} dangerouslySetInnerHTML={{ __html: dogMarkup }} />
      )}
      {animals.map(({ key, w, node }) => (
        <g key={key} transform={`translate(${w.x.toFixed(1)} ${w.y.toFixed(1)}) scale(${w.face} 1)`}>
          {node}
        </g>
      ))}
    </g>
  );
}
