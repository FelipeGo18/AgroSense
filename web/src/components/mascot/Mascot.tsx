import type { ReactNode } from "react";

/**
 * Semilla Sputnik, la mascota de AgroSense (HU-171): una semilla germinando dibujada como
 * caricatura de los años 60. Las raíces son las antenas, el brote es la antena de señal y las
 * hojas son los paneles. Misma geometría que design/mascota/semilla_sputnik.py.
 *
 * La identidad está en la cara, los brazos, las raíces y el brote; la semilla puede cambiar
 * según el contexto (por ejemplo, el cultivo consultado).
 * Cada parte animable lleva su clase: mascot-roots, mascot-arm-left, mascot-arm-right,
 * mascot-sprout, mascot-body, mascot-eyes, mascot-mouth.
 */

export type MascotMood = "idle" | "guide" | "celebrate" | "no_data" | "flying";
export type MascotSeed = "sprouted" | "bean" | "maize";

const INK = "#1D1D1B";
const CREAM = "#FFF6E0";
const RED = "#E76F51";

const SEEDS: Record<MascotSeed, { d: string; fill: string; light: string; label: string }> = {
  sprouted: {
    d: "M158 58 C196 62 216 98 212 132 C208 168 184 188 156 188 C126 188 104 166 102 134 C100 98 122 60 158 58Z",
    fill: "#C8873A",
    light: "#E3AE68",
    label: "semilla germinada",
  },
  bean: {
    d: "M126 76 C156 50 208 70 212 118 C216 162 184 190 150 186 C114 182 96 154 108 130 C114 118 130 120 130 108 C130 96 114 94 126 76Z",
    fill: "#A8463A",
    light: "#CC6B58",
    label: "frijol",
  },
  maize: {
    d: "M124 64 C140 54 178 54 194 64 C214 78 212 120 200 152 C190 178 172 190 158 190 C144 190 126 178 116 152 C104 120 104 78 124 64Z",
    fill: "#F2C230",
    light: "#FBE08A",
    label: "grano de maíz",
  },
};

type Arm = "down" | "up" | "point" | "tuck" | "back";
type Eyes = "pie" | "happy" | "hollow";
type Mouth = "smile" | "open" | "big" | "flat";

interface Pose {
  label: string;
  eyes: Eyes;
  mouth: Mouth;
  arms: [Arm, Arm];
  look?: number;
  waves?: number;
  transform?: string;
  droop?: boolean;
  sparkles?: boolean;
  speed?: boolean;
  mist?: boolean;
}

const POSES: Record<MascotMood, Pose> = {
  idle: { label: "en reposo", eyes: "pie", mouth: "smile", arms: ["down", "down"] },
  guide: { label: "señalando", eyes: "pie", look: 4, mouth: "open", arms: ["down", "point"], waves: 2 },
  celebrate: { label: "celebrando", eyes: "happy", mouth: "big", arms: ["up", "up"], transform: "translate(0 -8)", sparkles: true },
  // Sin datos: se encoge entre niebla con los ojos vacíos. No está triste ni preocupada (R1).
  no_data: {
    label: "sin datos",
    eyes: "hollow",
    mouth: "flat",
    arms: ["tuck", "tuck"],
    transform: "translate(16 22) scale(0.9)",
    droop: true,
    mist: true,
  },
  flying: {
    label: "volando",
    eyes: "pie",
    look: 5,
    mouth: "open",
    arms: ["back", "point"],
    waves: 1,
    transform: "rotate(-16 158 124)",
    speed: true,
  },
};

const stroke = { fill: "none", stroke: INK, strokeLinecap: "round", strokeLinejoin: "round" } as const;

function Roots({ droop }: { droop: boolean }) {
  const ends = droop
    ? [
        [70, 214],
        [92, 226],
        [116, 234],
        [140, 238],
      ]
    : [
        [30, 190],
        [52, 220],
        [86, 238],
        [120, 242],
      ];
  return (
    <g className="mascot-roots">
      {ends.map(([x, y], i) => (
        <g key={i}>
          <path d={`M128 166 Q${(128 + x) / 2 + 6} ${(166 + y) / 2 + (14 - i * 6)} ${x} ${y}`} {...stroke} strokeWidth={4} />
          <circle cx={x} cy={y} r={5.5} fill={RED} stroke={INK} strokeWidth={3} />
        </g>
      ))}
    </g>
  );
}

function Sprout({ waves }: { waves: number }) {
  return (
    <g className="mascot-sprout">
      <path d="M158 62 C160 48 158 40 154 30" {...stroke} strokeWidth={5} />
      <path d="M154 32 C136 32 124 18 128 6 C144 8 156 18 154 32Z" fill="#5FA052" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
      <path d="M156 34 C172 36 188 26 188 12 C172 10 158 20 156 34Z" fill="#8CC56A" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
      {/* Nervaduras en cuadrícula: las hojas son los paneles solares. */}
      <path d="M150 28 C142 24 136 18 132 10 M146 16 L136 22 M178 14 C172 22 166 28 158 32 M172 28 L166 16" {...stroke} strokeWidth={1.8} />
      {Array.from({ length: waves }, (_, i) => {
        const r = 14 + i * 10;
        return (
          <path
            key={i}
            d={`M${196 + r * 0.5} ${10 - r * 0.5} Q${200 + r} 14 ${196 + r * 0.5} ${20 + r * 0.6}`}
            {...stroke}
            stroke={RED}
            strokeWidth={3.5}
          />
        );
      })}
    </g>
  );
}

function ArmShape({ kind, side }: { kind: Arm; side: -1 | 1 }) {
  const sx = 158 + side * 50;
  const arms: Record<Arm, { d: string; hand: [number, number] }> = {
    down: { d: `M${sx} 138 C${sx + side * 26} 148 ${sx + side * 32} 166 ${sx + side * 28} 184`, hand: [sx + side * 28, 188] },
    up: { d: `M${sx} 126 C${sx + side * 30} 112 ${sx + side * 42} 88 ${sx + side * 40} 62`, hand: [sx + side * 40, 58] },
    point: { d: `M${sx} 130 C${sx + side * 22} 124 ${sx + side * 44} 118 ${sx + side * 64} 112`, hand: [sx + side * 68, 111] },
    tuck: { d: `M${sx} 140 C${sx + side * 16} 150 ${sx + side * 10} 166 ${sx - side * 6} 168`, hand: [sx - side * 8, 168] },
    back: { d: `M${sx} 140 C${sx + side * 18} 156 ${sx + side * 34} 162 ${sx + side * 54} 170`, hand: [sx + side * 58, 172] },
  };
  const { d, hand } = arms[kind];
  const finger = `M${hand[0] + side * 8} ${hand[1] - 2} l${side * 16} -3`;
  return (
    <g className={side < 0 ? "mascot-arm-left" : "mascot-arm-right"}>
      <path d={d} {...stroke} strokeWidth={9} />
      <circle cx={hand[0]} cy={hand[1]} r={13} fill={CREAM} stroke={INK} strokeWidth={4} />
      {kind === "point" && (
        <>
          <path d={finger} {...stroke} strokeWidth={7} />
          <path d={finger} {...stroke} stroke={CREAM} strokeWidth={3} />
        </>
      )}
    </g>
  );
}

function EyesShape({ kind, look }: { kind: Eyes; look: number }) {
  return (
    <g className="mascot-eyes">
      {[140, 182].map((x) =>
        kind === "happy" ? (
          <path key={x} d={`M${x - 14} 122 Q${x} 100 ${x + 14} 122`} {...stroke} strokeWidth={5} />
        ) : kind === "hollow" ? (
          <ellipse key={x} cx={x} cy={116} rx={15} ry={20} fill={CREAM} stroke={INK} strokeWidth={3.5} strokeDasharray="5 5" />
        ) : (
          <g key={x}>
            <ellipse cx={x} cy={116} rx={15} ry={20} fill={CREAM} stroke={INK} strokeWidth={4} />
            <path d={`M${x + look} 120 m0 -10 a10 10 0 1 1 -9 6 l9 4Z`} fill={INK} />
          </g>
        ),
      )}
    </g>
  );
}

function MouthShape({ kind }: { kind: Mouth }) {
  const shapes: Record<Mouth, ReactNode> = {
    smile: <path d="M146 150 Q160 164 176 150" {...stroke} strokeWidth={4} />,
    open: <path d="M138 148 Q160 172 184 148Z" {...stroke} fill={CREAM} strokeWidth={4} />,
    big: (
      <>
        <path d="M132 144 Q160 186 190 144Z" {...stroke} fill={CREAM} strokeWidth={4} />
        <path d="M146 162 Q160 172 176 162" fill={RED} />
      </>
    ),
    flat: <path d="M150 154 H172" {...stroke} strokeWidth={4} />,
  };
  return <g className="mascot-mouth">{shapes[kind]}</g>;
}

const sparkle = (x: number, y: number, r: number) =>
  `M${x} ${y - r} Q${x} ${y} ${x + r} ${y} Q${x} ${y} ${x} ${y + r} Q${x} ${y} ${x - r} ${y} Q${x} ${y} ${x} ${y - r}Z`;

export interface MascotProps {
  mood?: MascotMood;
  seed?: MascotSeed;
  /** Ancho en píxeles; el alto guarda la proporción 300:250. */
  size?: number;
  /** De vez en cuando saluda con la mano. Para la mascota que guía o acompaña, no para las pequeñas de una lista. */
  lively?: boolean;
  /** Decorativa cuando el texto de al lado ya dice lo mismo; la expresión nunca es la única señal. */
  decorative?: boolean;
  className?: string;
}

export function Mascot({ mood = "idle", seed = "sprouted", size = 240, lively = false, decorative = false, className = "" }: MascotProps) {
  const pose = POSES[mood];
  const s = SEEDS[seed];
  return (
    <svg
      viewBox="0 0 300 250"
      width={size}
      height={(size * 250) / 300}
      className={`mascot shrink-0 ${lively ? "mascot-lively" : ""} ${className}`}
      data-mood={mood}
      data-seed={seed}
      {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": `Mascota de AgroSense, ${s.label}, ${pose.label}` })}
    >
      <g transform={pose.transform}>
        <Roots droop={pose.droop ?? false} />
        <ArmShape kind={pose.arms[0]} side={-1} />
        <Sprout waves={pose.waves ?? 0} />
        <g className="mascot-body">
          <path d={s.d} fill={s.fill} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
          {seed === "maize" && <path d="M140 184 C148 192 168 192 176 184 C170 172 146 172 140 184Z" fill="#FFF4CC" />}
          <path d="M124 92 A46 46 0 0 1 164 70" {...stroke} stroke={s.light} strokeWidth={8} />
          <path d="M116 128 C114 150 124 168 140 178" {...stroke} strokeWidth={2.5} opacity={0.35} />
          {/* La cáscara se abre: de ahí sale el brote. */}
          <path d="M146 66 Q158 78 170 64" {...stroke} strokeWidth={3.5} />
          <ellipse cx={124} cy={142} rx={9} ry={5} fill={RED} opacity={0.55} />
          <ellipse cx={196} cy={142} rx={9} ry={5} fill={RED} opacity={0.55} />
        </g>
        <EyesShape kind={pose.eyes} look={pose.look ?? 0} />
        <MouthShape kind={pose.mouth} />
        <ArmShape kind={pose.arms[1]} side={1} />
      </g>
      {pose.sparkles && (
        <g className="mascot-sparkles">
          <path d={sparkle(46, 60, 12)} fill={RED} />
          <path d={sparkle(262, 96, 9)} fill={RED} />
          <path d={sparkle(238, 214, 8)} fill={RED} />
          <path d={sparkle(74, 26, 6)} fill="#2A9D8F" />
        </g>
      )}
      {pose.speed &&
        [
          [70, 20, 70],
          [104, 6, 50],
          [140, 14, 44],
        ].map(([y, x1, x2]) => <path key={y} d={`M${x1} ${y} L${x2} ${y - 12}`} {...stroke} strokeWidth={3.5} />)}
      {pose.mist &&
        [
          [84, 1],
          [214, 0.8],
        ].map(([x, k]) => (
          <path
            key={x}
            d={`M${x - 44 * k} 232 q${14 * k} ${-22 * k} ${34 * k} ${-10 * k} q${16 * k} ${-18 * k} ${32 * k} 0 q${22 * k} ${-6 * k} ${22 * k} 10Z`}
            fill="#FFFFFF"
            stroke={INK}
            strokeWidth={3}
            strokeLinejoin="round"
            opacity={0.9}
          />
        ))}
    </svg>
  );
}
