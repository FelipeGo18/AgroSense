import { useState } from "react";
import { Mascot } from "@/components/mascot/Mascot";
import type { TimeOfDay } from "./cells";

/**
 * La vida de la finca en el lote vivo (HU-187): todo lo que se mueve y no es un dato. Solo se dibuja con movimiento
 * (`LiveLot` no la monta en modo ligero, HU-158), así que nada de lo que dice el lote depende de ella.
 *
 * Los animales de la finca (vacas, gallinas y el perro) están en `Animals.tsx`, con sus reglas. Las animaciones largas
 * (el pájaro, las mariposas, la mascota) van con SMIL
 * (`animateMotion`), que `LiveLot` pausa cuando la pestaña no se ve; los bucles cortos (humo, picoteo, cola, alas), con
 * CSS (`farm-*` en `styles/index.css`). Las coordenadas son las del lote (`anchors` de `design/finca/exportar_web.py`).
 */

export type Pt = [number, number];
export interface FarmAnchors {
  chimney: Pt;
  window: Pt;
  porch: Pt;
  garden: Pt;
  dog: Pt;
  fence: Pt;
  lanterns: Pt[];
  path: Pt[];
  hens: Pt[];
  meadow: Pt[];
  field: Pt[];
  pasture: Pt[];
  yard: Pt[];
}

const INK = "#2A1E16";

/** Una gallina low-poly mirando a la derecha; `pecking` baja la cabeza a picotear. */
export function Hen({
  x,
  y,
  scale = 1,
  pecking = true,
  delay = 0,
}: {
  x: number;
  y: number;
  scale?: number;
  pecking?: boolean;
  delay?: number;
}) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx={0} cy={2} rx={11} ry={3} fill="#000" fillOpacity={0.15} />
      <polygon points="-11,-6 -4,-15 8,-13 11,-5 6,0 -8,0" fill="#F4EDE0" />
      <polygon points="-11,-6 -16,-14 -9,-11" fill="#E6DCCB" />
      <polygon points="-4,-11 4,-12 2,-6 -6,-6" fill="#E6DCCB" />
      <line x1={-2} y1={0} x2={-3} y2={5} stroke="#E0A030" strokeWidth={1.6} />
      <line x1={3} y1={0} x2={3} y2={5} stroke="#E0A030" strokeWidth={1.6} />
      <g className={pecking ? "farm-peck" : undefined} style={{ animationDelay: `${delay}s` }}>
        <polygon points="6,-13 13,-19 17,-14 12,-9" fill="#F4EDE0" />
        <polygon points="12,-20 15,-23 17,-19" fill="#D9473A" />
        <polygon points="17,-15 21,-14 17,-12" fill="#E0A030" />
        <circle cx={14} cy={-16} r={1} fill={INK} />
      </g>
    </g>
  );
}

/** El perro corriendo, de perfil. Las patas se alternan con CSS. */
export function RunningDog() {
  return (
    <g transform="scale(1.1)">
      <ellipse cx={0} cy={4} rx={22} ry={4} fill="#000" fillOpacity={0.15} />
      <g className="farm-legs">
        <polygon points="-14,-2 -10,-2 -16,6 -19,5" fill="#8E5A2C" />
        <polygon points="10,-2 14,-2 18,6 15,6" fill="#8E5A2C" />
      </g>
      <g className="farm-legs farm-legs-alt">
        <polygon points="-8,-2 -4,-2 -2,6 -6,6" fill="#A86E38" />
        <polygon points="4,-2 8,-2 6,6 2,6" fill="#A86E38" />
      </g>
      <polygon points="-18,-4 -14,-14 12,-14 20,-6 16,-2 -16,-2" fill="#B97A3E" />
      <polygon points="-18,-10 -26,-16 -24,-8" fill="#8E5A2C" className="farm-tail" />
      <polygon points="12,-14 22,-20 30,-14 28,-8 18,-8" fill="#B97A3E" />
      <polygon points="28,-14 35,-12 34,-9 28,-9" fill="#D9A06A" />
      <polygon points="18,-20 21,-27 24,-19" fill="#8E5A2C" />
      <circle cx={26} cy={-15} r={1.3} fill={INK} />
    </g>
  );
}

export function Cow() {
  return (
    <g>
      <ellipse cx={0} cy={4} rx={30} ry={5} fill="#000" fillOpacity={0.14} />
      {[-16, -8, 10, 18].map((x) => (
        <rect key={x} x={x - 2} y={-6} width={4} height={10} fill="#3A2E28" />
      ))}
      <polygon points="-24,-8 -20,-26 20,-26 24,-8 20,-4 -20,-4" fill="#F4EDE0" />
      <polygon points="-14,-24 -2,-24 -6,-12 -16,-12" fill="#2E2622" />
      <polygon points="6,-20 16,-20 14,-8 4,-10" fill="#2E2622" />
      <g className="farm-graze">
        <polygon points="20,-24 34,-20 36,-8 24,-8" fill="#F4EDE0" />
        <polygon points="30,-12 38,-10 37,-5 30,-6" fill="#E8A0A8" />
        <polygon points="22,-26 20,-31 26,-25" fill="#D9C79A" />
        <circle cx={29} cy={-17} r={1.4} fill={INK} />
      </g>
      <polygon points="-24,-20 -30,-10 -27,-9" fill="#3A2E28" className="farm-tail" />
    </g>
  );
}

function Butterfly({ color }: { color: string }) {
  return (
    <g>
      <g className="farm-flap">
        <polygon points="0,0 -9,-8 -10,2" fill={color} />
        <polygon points="0,0 9,-8 10,2" fill={color} />
      </g>
      <line x1={0} y1={-4} x2={0} y2={4} stroke={INK} strokeWidth={1.4} />
    </g>
  );
}

function Bird() {
  return (
    <g>
      <polygon points="-7,-2 3,-6 8,-2 3,2" fill="#3F6E9A" />
      <polygon points="8,-3 12,-2 8,-1" fill="#E0A030" />
      <g className="farm-flap">
        <polygon points="-2,-4 -8,-12 2,-5" fill="#5A86B0" />
      </g>
      <circle cx={5} cy={-3.5} r={0.9} fill="#FFF" />
    </g>
  );
}

/** Un trayecto que se repite, con pausas: `keyPoints` y `keyTimes` como en SMIL. */
function Motion({
  path,
  dur,
  keyPoints,
  keyTimes,
  begin = "0s",
}: {
  path: string;
  dur: string;
  keyPoints?: string;
  keyTimes?: string;
  begin?: string;
}) {
  return (
    <animateMotion
      dur={dur}
      begin={begin}
      repeatCount="indefinite"
      path={path}
      calcMode="linear"
      {...(keyPoints && keyTimes ? { keyPoints, keyTimes } : {})}
    />
  );
}

/** Lo que vive dentro del lote y su finca (en coordenadas del lote). */
export function FarmLifeWorld({
  anchors,
  time,
  flowering,
}: {
  anchors: FarmAnchors;
  time: TimeOfDay;
  /** Los centros de los cubos con cultivos en flor (etapa media o final), para las abejas. */
  flowering: Pt[];
}) {
  const day = time !== "noche";
  const [f0, f1] = anchors.field;
  const fieldW = Math.abs(anchors.path[2][0] - anchors.path[0][0]);
  return (
    <g aria-hidden="true">
      {/* 11. Sombras de nubes que pasan sobre el campo. */}
      {day && (
        <g opacity={0.12}>
          <ellipse cx={0} cy={(f0[1] + f1[1]) / 2} rx={150} ry={60} fill="#1E2A3A">
            <animateTransform
              attributeName="transform"
              type="translate"
              from={`${-fieldW} -60`}
              to={`${fieldW} 60`}
              dur="26s"
              repeatCount="indefinite"
            />
          </ellipse>
        </g>
      )}

      {/* 3. Humo de la chimenea, en bocanadas que se deshacen. */}
      <g transform={`translate(${anchors.chimney[0]} ${anchors.chimney[1]})`}>
        {[0, 1.4, 2.8].map((delay) => (
          <circle key={delay} r={9} fill="#FFFFFF" className="farm-smoke" style={{ animationDelay: `${delay}s` }} />
        ))}
      </g>

      {/* 8. De noche: la ventana con luz y los faroles de la cerca encendidos. */}
      {!day && (
        <>
          <circle cx={anchors.window[0]} cy={anchors.window[1]} r={26} fill="#FFD27A" className="farm-glow" />
          {anchors.lanterns.map(([x, y]) => (
            <circle
              key={`${x}-${y}`}
              cx={x}
              cy={y}
              r={20}
              fill="#FFE29A"
              className="farm-glow"
              style={{ animationDelay: `${(x + y) % 3}s` }}
            />
          ))}
        </>
      )}

      {/* 15. El gato en el porche, moviendo la cola. */}
      <g transform={`translate(${anchors.porch[0]} ${anchors.porch[1]})`}>
        <polygon points="-8,0 -6,-10 6,-10 8,0" fill="#5A4A3A" />
        <polygon points="2,-10 6,-19 10,-10" fill="#5A4A3A" />
        <polygon points="-2,-10 0,-17 4,-10" fill="#5A4A3A" />
        <circle cx={3} cy={-12} r={0.9} fill="#F2C232" />
        <circle cx={7} cy={-12} r={0.9} fill="#F2C232" />
        <path d="M-8 -2 q-10 -2 -8 -14" stroke="#5A4A3A" strokeWidth={3} fill="none" strokeLinecap="round" className="farm-cat-tail" />
      </g>

      {/* 12. Abejas sobre los cultivos en flor. */}
      {day &&
        flowering.slice(0, 3).map(([x, y], i) => (
          <g key={`${x}-${y}`} transform={`translate(${x} ${y - 40})`}>
            {[0, 1].map((n) => (
              <circle key={n} r={2.2} fill="#F2C232" stroke={INK} strokeWidth={0.8}>
                <animateMotion
                  dur={`${3 + n + i * 0.5}s`}
                  repeatCount="indefinite"
                  path={n ? "M-20 0 q10 -16 20 0 t20 0 q-10 14 -20 0 t-20 0" : "M15 -8 q-12 10 -24 0 t-10 12 q14 4 34 -12"}
                />
              </circle>
            ))}
          </g>
        ))}

      {/* 13. El colibrí en la huerta de flores. */}
      {day && (
        <g transform={`translate(${anchors.garden[0]} ${anchors.garden[1] - 26})`}>
          <g className="farm-hover">
            <polygon points="-6,0 4,-3 8,0 4,3" fill="#2E9A6A" />
            <line x1={8} y1={0} x2={15} y2={1} stroke={INK} strokeWidth={1} />
            <g className="farm-buzz">
              <polygon points="0,-1 -4,-10 3,-2" fill="#9ED8C0" fillOpacity={0.8} />
            </g>
          </g>
          <animateTransform
            attributeName="transform"
            type="translate"
            additive="sum"
            values="0 0;30 -6;30 -6;-10 4;0 0"
            keyTimes="0;0.2;0.5;0.7;1"
            dur="9s"
            repeatCount="indefinite"
          />
        </g>
      )}

      {/* 9. Un pájaro llega a la cerca, se queda un rato y sale volando. */}
      {day && (
        <g>
          <Bird />
          <Motion
            path={`M${anchors.fence[0] - 260} ${anchors.fence[1] - 200} Q${anchors.fence[0] - 60} ${anchors.fence[1] - 120} ${anchors.fence[0]} ${anchors.fence[1] - 4} Q${anchors.fence[0] + 80} ${anchors.fence[1] - 140} ${anchors.fence[0] + 320} ${anchors.fence[1] - 260}`}
            dur="22s"
            keyPoints="0;0.5;0.5;1;1"
            keyTimes="0;0.15;0.55;0.75;1"
          />
        </g>
      )}

      {/* 4. La mascota pasa volando sobre la finca de vez en cuando y saluda. */}
      <g>
        <svg x={-42} y={-60} width={84} height={70} viewBox="0 0 300 250" overflow="visible">
          <Mascot mood="flying" decorative />
        </svg>
        <Motion
          path={`M${anchors.path[0][0] - 260} ${anchors.path[0][1] - 230} Q${anchors.path[3][0]} ${anchors.path[3][1] - 120} ${anchors.path[2][0] + 260} ${anchors.path[2][1] - 260}`}
          dur="40s"
          keyPoints="0;0;1;1"
          keyTimes="0;0.7;0.95;1"
        />
      </g>
    </g>
  );
}

/**
 * 8. Las luciérnagas de noche, al azar por toda la finca (en coordenadas del lote): cada una en su sitio, con su propio
 * vuelo errático y su propio ritmo de encenderse y apagarse. Van encima del tono de la noche, para que brillen.
 */
export function FarmFireflies({ anchors }: { anchors: FarmAnchors }) {
  const [flies] = useState(() => {
    const xs = anchors.path.map((p) => p[0]);
    const ys = anchors.path.map((p) => p[1]);
    const [x0, x1] = [Math.min(...xs) - 140, Math.max(...xs) + 140];
    const [y0, y1] = [Math.min(...ys) - 80, Math.max(...ys) + 180];
    const r = (a: number, b: number) => a + Math.random() * (b - a);
    return Array.from({ length: 24 }, () => {
      const hops = Array.from({ length: 4 }, () => `${r(-45, 45).toFixed(0)} ${r(-30, 30).toFixed(0)}`);
      return {
        x: r(x0, x1),
        y: r(y0, y1),
        path: `M0 0 Q${hops[0]} ${hops[1]} T${hops[2]} T${hops[3]} T0 0`,
        fly: `${r(7, 16).toFixed(1)}s`,
        blink: `${r(2.5, 6).toFixed(1)}s`,
        delay: `${r(0, 6).toFixed(1)}s`,
        size: r(2.5, 4),
      };
    });
  });
  return (
    <g aria-hidden="true">
      {flies.map((f, i) => (
        <g key={i} transform={`translate(${f.x.toFixed(0)} ${f.y.toFixed(0)})`}>
          <g className="farm-firefly" style={{ animationDuration: f.blink, animationDelay: f.delay }}>
            <circle r={f.size * 2.6} fill="#F7F28A" opacity={0.25} />
            <circle r={f.size} fill="#FBF7B0" />
            <animateMotion dur={f.fly} begin={`-${f.delay}`} repeatCount="indefinite" path={f.path} />
          </g>
        </g>
      ))}
    </g>
  );
}

/** Lo que cruza la vista por encima de la finca (en coordenadas de la vista: `width` × `height`). */
export function FarmLifeSky({ width, height, time }: { width: number; height: number; time: TimeOfDay }) {
  const day = time !== "noche";
  return (
    <g aria-hidden="true">
      {/* 7. Mariposas que cruzan de día. */}
      {day &&
        [
          { color: "#F2C232", y: height * 0.55, dur: "16s", begin: "0s" },
          { color: "#E8A0C0", y: height * 0.68, dur: "21s", begin: "-8s" },
        ].map(({ color, y, dur, begin }) => (
          <g key={color}>
            <Butterfly color={color} />
            <animateMotion
              dur={dur}
              begin={begin}
              repeatCount="indefinite"
              path={`M${-30} ${y} q80 -60 160 0 t160 0 t160 0 t160 0 t160 0 t160 0 t160 0`}
            />
          </g>
        ))}

      {/* 5. Ráfagas de viento: unas hojas que cruzan con la ola de viento. */}
      {day &&
        [0, 0.6, 1.2].map((delay, i) => (
          <polygon key={delay} points="0,-4 8,0 0,4 -3,0" fill={["#6FA03C", "#9CC152", "#C9A86A"][i]}>
            <animateMotion
              dur="9s"
              begin={`${delay}s`}
              repeatCount="indefinite"
              keyPoints="0;0;1;1"
              keyTimes="0;0.55;0.8;1"
              path={`M-20 ${height * 0.42 + i * 18} q${width / 3} -40 ${width / 2} 0 t${width / 2 + 40} 10`}
              rotate="auto"
            />
          </polygon>
        ))}
    </g>
  );
}
