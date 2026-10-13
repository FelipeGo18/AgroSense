/**
 * Sonido de la web: efectos de interfaz y música de fondo. Arranca apagado y la web se entiende igual sin él
 * (specs/05-frontend.md). Un solo control lo prende y lo quita todo; la preferencia se guarda en este navegador.
 *
 * Los efectos se sintetizan con Web Audio. La música sale de un archivo si `VITE_MUSIC_URL` lo indica
 * (por ejemplo `/audio/tema.mp3`, puesto en `web/public/audio/`); si no, suena una melodía generada aquí mismo.
 */

export type SoundEffect =
  "on" | "stop" | "flutter" | "land" | "wind" | "drizzle" | "giggle" | "cheer" | "nope" | "yawn" | "chirp" | "shake";

const KEY = "agrosense:sonido";
const listeners = new Set<() => void>();
let context: AudioContext | undefined;
// Todo lo que suena pasa por esta salida. Al quitar el sonido se desconecta: así callan de inmediato también las notas
// que ya estaban programadas (la música se programa con un segundo de ventaja y su bajo dura tres).
let output: GainNode | undefined;

/** La salida de un contexto de audio; se crea de nuevo después de cada silencio. */
function out(ctx: AudioContext) {
  if (!output) {
    output = ctx.createGain();
    output.connect(ctx.destination);
  }
  return output;
}

/** Calla ya todo lo que esté sonando o por sonar. */
function silence() {
  output?.disconnect();
  output = undefined;
}

const read = () => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false; // sin almacenamiento (modo privado): apagado
  }
};
let enabled = typeof localStorage === "undefined" ? false : read();

export const soundEnabled = () => enabled;

export function subscribeSound(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Una nota suave: sube rápido y se apaga sola. */
function note(ctx: AudioContext, type: OscillatorType, hz: number, at: number, length: number, volume: number) {
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = type;
  oscillator.frequency.value = hz;
  gain.gain.setValueAtTime(0, at);
  gain.gain.linearRampToValueAtTime(volume, at + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  oscillator.connect(gain).connect(out(ctx));
  oscillator.start(at);
  oscillator.stop(at + length + 0.02);
}

// ---------- Efectos ----------

/** Notas de cada efecto: frecuencia en Hz, cuándo empieza y cuánto dura, en segundos. */
const EFFECTS: Record<
  Exclude<SoundEffect, "wind" | "drizzle">,
  { type: OscillatorType; notes: [hz: number, at: number, length: number][]; volume?: number }
> = {
  // Al prender el sonido: tres notas que suben.
  on: {
    type: "triangle",
    notes: [
      [523.25, 0, 0.14],
      [659.25, 0.09, 0.14],
      [783.99, 0.18, 0.22],
    ],
  },
  // Al pasar a otra parada del recorrido: una gota.
  stop: {
    type: "sine",
    notes: [
      [392, 0, 0.1],
      [587.33, 0.07, 0.2],
    ],
  },
  // Pasa una mariposa: unas notas altas y muy bajitas, como un aleteo.
  flutter: {
    type: "triangle",
    volume: 0.025,
    notes: [
      [1568, 0, 0.05],
      [1760, 0.08, 0.05],
      [1568, 0.16, 0.05],
      [1976, 0.24, 0.09],
    ],
  },
  // La mariposa se posa en el brote.
  land: {
    type: "sine",
    volume: 0.04,
    notes: [
      [880, 0, 0.08],
      [1174.66, 0.07, 0.16],
    ],
  },
  // Le hacen cosquillas a la mascota: una risa corta.
  giggle: {
    type: "triangle",
    volume: 0.05,
    notes: [
      [987.77, 0, 0.07],
      [1318.51, 0.08, 0.07],
      [987.77, 0.16, 0.07],
      [1318.51, 0.24, 0.07],
      [1567.98, 0.32, 0.12],
    ],
  },
  // Entró o creó su cuenta: una fanfarria chiquita.
  cheer: {
    type: "triangle",
    notes: [
      [523.25, 0, 0.1],
      [659.25, 0.08, 0.1],
      [783.99, 0.16, 0.1],
      [1046.5, 0.26, 0.3],
    ],
  },
  // La mascota dice que no: dos notas que bajan.
  nope: {
    type: "sine",
    volume: 0.06,
    notes: [
      [311.13, 0, 0.14],
      [233.08, 0.16, 0.24],
    ],
  },
  // Bosteza: una escalera lenta hacia abajo.
  yawn: {
    type: "sine",
    volume: 0.04,
    notes: [
      [523.25, 0, 0.4],
      [440, 0.3, 0.4],
      [349.23, 0.6, 0.5],
      [261.63, 0.95, 0.8],
    ],
  },
  // Pasan unos pájaros a lo lejos.
  // La mascota se sacude el agua, como un perro: un traqueteo corto.
  shake: {
    type: "triangle",
    volume: 0.04,
    notes: [
      [330, 0, 0.05],
      [415, 0.07, 0.05],
      [330, 0.14, 0.05],
      [415, 0.21, 0.05],
      [330, 0.28, 0.05],
      [494, 0.36, 0.14],
    ],
  },
  chirp: {
    type: "sine",
    volume: 0.022,
    notes: [
      [2637, 0, 0.05],
      [3136, 0.06, 0.06],
      [2637, 0.5, 0.05],
      [3520, 0.56, 0.07],
    ],
  },
};

const EFFECT_VOLUME = 0.07;

/** Ruido filtrado que sube y baja, sin notas: un soplo de viento o, más agudo y largo, una llovizna. */
function gust(ctx: AudioContext, at: number, length: number, volume: number, [low, peak, end] = [350, 900, 420]) {
  const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * length), ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  const filter = ctx.createBiquadFilter();
  filter.type = "bandpass";
  filter.Q.value = 0.7;
  filter.frequency.setValueAtTime(low, at);
  filter.frequency.linearRampToValueAtTime(peak, at + length * 0.45);
  filter.frequency.linearRampToValueAtTime(end, at + length);
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(volume, at + length * 0.4);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  source.connect(filter).connect(gain).connect(out(ctx));
  source.start(at);
  source.stop(at + length);
}

/** Suena un efecto (`seconds` es cuánto dura la llovizna), si el sonido está prendido y el navegador ya lo permite (hace falta un gesto del usuario). */
export function playSound(effect: SoundEffect, seconds = 7) {
  if (!enabled || typeof AudioContext === "undefined") return;
  context ??= new AudioContext();
  if (context.state === "suspended") void context.resume().catch(() => {});
  if (context.state !== "running") return;
  const now = context.currentTime;
  if (effect === "wind") return gust(context, now, 1.7, 0.05);
  if (effect === "drizzle") return gust(context, now, seconds, 0.018, [2600, 3400, 2800]);
  const { type, notes, volume = EFFECT_VOLUME } = EFFECTS[effect];
  for (const [hz, at, length] of notes) note(context, type, hz, now + at, length, volume);
}

// ---------- Música ----------

const MUSIC_URL = typeof import.meta.env.VITE_MUSIC_URL === "string" ? import.meta.env.VITE_MUSIC_URL.trim() : "";
const FILE_VOLUME = 0.25;
const TUNE_VOLUME = 0.028;
/** Segundos por paso de la melodía generada: lenta, para acompañar sin distraer. */
const STEP = 0.42;

// Do mayor pentatónica. Cada compás: un bajo largo y una frase de ocho pasos (0 = silencio).
const C3 = 130.81;
const F3 = 174.61;
const G3 = 196;
const A2 = 110;
const [C4, D4, E4, G4, A4, C5, D5, E5] = [261.63, 293.66, 329.63, 392, 440, 523.25, 587.33, 659.25];
const BARS: { bass: number; melody: number[] }[] = [
  { bass: C3, melody: [E4, 0, G4, 0, C5, 0, G4, E4] },
  { bass: A2, melody: [A4, 0, C5, 0, E5, 0, C5, A4] },
  { bass: F3, melody: [C5, 0, A4, 0, G4, 0, A4, C5] },
  { bass: G3, melody: [D5, 0, G4, 0, D4, E4, G4, 0] },
  { bass: C3, melody: [E4, G4, C5, 0, E5, 0, D5, C5] },
  { bass: A2, melody: [A4, 0, E4, 0, C4, 0, E4, A4] },
  { bass: F3, melody: [C4, 0, A4, 0, C5, 0, A4, G4] },
  { bass: G3, melody: [G4, 0, D4, 0, G4, 0, 0, 0] },
];

let file: HTMLAudioElement | undefined;
let timer: ReturnType<typeof setInterval> | undefined;
let nextBar = 0;
let nextBarAt = 0;

function scheduleBars() {
  if (!context || context.state !== "running") return;
  // Se programa con un segundo de ventaja para que un cuadro lento no deje huecos.
  while (nextBarAt < context.currentTime + 1) {
    const { bass, melody } = BARS[nextBar % BARS.length];
    note(context, "sine", bass, nextBarAt, STEP * 7.5, TUNE_VOLUME * 1.3);
    melody.forEach((hz, i) => {
      if (hz) note(context!, "triangle", hz, nextBarAt + i * STEP, STEP * 2.4, TUNE_VOLUME);
    });
    nextBar++;
    nextBarAt += STEP * melody.length;
  }
}

function startMusic() {
  if (MUSIC_URL) {
    if (typeof Audio === "undefined") return;
    file ??= Object.assign(new Audio(MUSIC_URL), { loop: true, volume: FILE_VOLUME });
    void file.play().catch(() => {}); // sin gesto del usuario el navegador no deja: sonará con el siguiente clic
    return;
  }
  if (!context || timer !== undefined) return;
  nextBarAt = context.currentTime + 0.7; // después del efecto de prender
  timer = setInterval(scheduleBars, 250);
}

function stopMusic() {
  file?.pause();
  if (timer !== undefined) clearInterval(timer);
  timer = undefined;
  silence();
}

/** Con la pestaña escondida la música se calla; vuelve al regresar. */
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (!enabled) return;
    if (document.hidden) stopMusic();
    else startMusic();
  });
  // Si quedó prendido de una visita anterior, el navegador pide un gesto antes de dejar sonar.
  const wake = () => {
    if (!enabled || typeof AudioContext === "undefined") return;
    context ??= new AudioContext();
    void context
      .resume()
      .then(startMusic)
      .catch(() => {});
  };
  document.addEventListener("pointerdown", wake, { once: true });
  document.addEventListener("keydown", wake, { once: true });
}

export function setSoundEnabled(next: boolean) {
  enabled = next;
  try {
    localStorage.setItem(KEY, next ? "1" : "0");
  } catch {
    // sin almacenamiento, la preferencia dura lo que dure la página
  }
  if (!next) {
    stopMusic();
  } else if (typeof AudioContext !== "undefined") {
    // El clic que lo prende es el gesto que el navegador pide para dejar sonar.
    context ??= new AudioContext();
    void context
      .resume()
      .then(() => {
        playSound("on");
        startMusic();
      })
      .catch(() => {});
  }
  listeners.forEach((listener) => listener());
}
