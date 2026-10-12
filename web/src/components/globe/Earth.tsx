import gsap from "gsap";
import { useEffect, useRef } from "react";
import globeUrl from "@/assets/globe.json?url";
import { lerpLon, lightFactor, parseHex, rotateInto, rotation, seeded, shade, type GlobeData, type Rgb } from "@/lib/globe";

export interface EarthFrame {
  cx: number;
  cy: number;
  r: number;
}

export interface EarthProps {
  /**
   * Avance del descenso, de 0 a 1. Es una referencia y no estado: cambia en cada cuadro del scroll y no debe
   * volver a pintar React. En 0 la Tierra gira libre; en 1 queda quieta con la región piloto al frente.
   */
  progress?: { readonly current: number };
  /** Dónde va la Tierra dentro del lienzo, según su tamaño y el avance. */
  frame?: (width: number, height: number, progress: number) => EarthFrame;
  /** Sin giro propio: se dibuja con la región piloto al frente y solo se mueve si la arrastran. */
  still?: boolean;
  className?: string;
}

/** Grados por segundo. La Tierra gira de oeste a este: la longitud que queda al frente baja con el tiempo. */
const SPIN = 4.5;
/** Longitud al frente al cargar: el Atlántico, para que la región piloto llegue a los pocos segundos. */
const START_LON = -30;
const TILT = 5;
/** Hasta dónde se puede inclinar al arrastrarla hacia arriba o hacia abajo, en grados. */
const MAX_TILT = 60;
/** Tras soltarla, el giro propio vuelve poco a poco en este tiempo, en ms. */
const RESUME_MS = 1400;
const FRAME_MS = 33;
const OCEAN_JITTER = [-0.02, 0, 0.02];
const LAND_JITTER = [-0.03, 0, 0.025, 0.01];

const centered: NonNullable<EarthProps["frame"]> = (w, h) => ({ cx: w / 2, cy: h / 2, r: Math.min(w, h) * 0.4 });
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

interface Prepared {
  data: GlobeData;
  oceanRgb: Rgb;
  landRgb: Rgb[];
  ocean: Float32Array[];
  land: { normal: Float32Array; points: Float32Array }[];
  outline: Float32Array[];
  pilot: Float32Array;
}

function prepare(data: GlobeData): Prepared {
  const unit = (values: number[]) => Float32Array.from(values, (v) => v / data.scale);
  return {
    data,
    oceanRgb: parseHex(data.ocean_color),
    landRgb: data.land.map(([color]) => parseHex(data.colors[color])),
    ocean: data.ocean.map(unit),
    land: data.land.map(([, normal, points]) => ({ normal: unit(normal), points: unit(points) })),
    outline: data.outline.map(unit),
    pilot: unit(data.pilot.vec),
  };
}

let cache: Promise<Prepared> | undefined;
/** La malla pesa unos 330 KB: se pide una sola vez, después de la primera pintura. */
function loadGlobe() {
  cache ??= fetch(globeUrl)
    .then((res) => res.json() as Promise<GlobeData>)
    .then(prepare);
  return cache;
}

function drawStars(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const random = seeded(7);
  ctx.fillStyle = "#FFFFFF";
  for (let i = Math.floor((w * h) / 9000); i > 0; i--) {
    const x = random() * w;
    const y = random() * h;
    const r = [0.8, 1.1, 1.6][Math.floor(random() * 3)];
    ctx.globalAlpha = 0.35 + random() * 0.55;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function drawGlobe(ctx: CanvasRenderingContext2D, globe: Prepared, { cx, cy, r }: EarthFrame, lon0: number, lat0: number, pulse: number) {
  const rot = rotation(lon0, lat0);
  const [lx, ly, lz] = globe.data.light;
  const p = [0, 0, 0];

  const halo = ctx.createRadialGradient(cx, cy, r * 0.99, cx, cy, r * 1.16);
  halo.addColorStop(0, "rgb(159 211 255 / 0.5)");
  halo.addColorStop(1, "rgb(159 211 255 / 0)");
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(cx, cy, r * 1.16, 0, Math.PI * 2);
  ctx.fill();

  // Base: tapa las rendijas entre facetas.
  ctx.fillStyle = shade(globe.oceanRgb, -0.12);
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();

  ctx.lineJoin = "round";
  ctx.lineWidth = 0.6;
  globe.ocean.forEach((tri, i) => {
    let nx = 0;
    let ny = 0;
    let nz = 0;
    let back = false;
    ctx.beginPath();
    for (let k = 0; k < 9; k += 3) {
      rotateInto(p, tri, k, rot);
      if (p[2] < -0.05) back = true;
      nx += p[0];
      ny += p[1];
      nz += p[2];
      if (k === 0) ctx.moveTo(cx + r * p[0], cy - r * p[1]);
      else ctx.lineTo(cx + r * p[0], cy - r * p[1]);
    }
    if (back) return;
    const len = Math.hypot(nx, ny, nz);
    const color = shade(globe.oceanRgb, lightFactor((nx * lx + ny * ly + nz * lz) / len, OCEAN_JITTER[i % 3]));
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.fill();
    ctx.stroke();
  });

  globe.land.forEach(({ normal, points }, i) => {
    rotateInto(p, normal, 0, rot);
    if (p[2] < 0.02) return;
    ctx.fillStyle = shade(globe.landRgb[i], lightFactor(p[0] * lx + p[1] * ly + p[2] * lz, LAND_JITTER[i % 4]));
    ctx.beginPath();
    for (let k = 0; k < points.length; k += 3) {
      rotateInto(p, points, k, rot);
      if (k === 0) ctx.moveTo(cx + r * p[0], cy - r * p[1]);
      else ctx.lineTo(cx + r * p[0], cy - r * p[1]);
    }
    ctx.fill();
  });

  // El contorno de la región piloto, para que se lea a dónde vamos a bajar.
  ctx.strokeStyle = "rgb(255 255 255 / 0.9)";
  ctx.lineWidth = Math.max(1.5, r / 160);
  globe.outline.forEach((ring) => {
    let depth = 0;
    ctx.beginPath();
    for (let k = 0; k < ring.length; k += 3) {
      rotateInto(p, ring, k, rot);
      depth += p[2];
      if (k === 0) ctx.moveTo(cx + r * p[0], cy - r * p[1]);
      else ctx.lineTo(cx + r * p[0], cy - r * p[1]);
    }
    if (depth / (ring.length / 3) <= 0.1) return;
    ctx.closePath();
    ctx.stroke();
  });

  // Sombra de la noche y borde de luz de la atmósfera.
  const night = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy - r + r * 0.6);
  night.addColorStop(0.55, "rgb(11 18 38 / 0)");
  night.addColorStop(1, "rgb(11 18 38 / 0.55)");
  ctx.fillStyle = night;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgb(191 227 255 / 0.55)";
  ctx.lineWidth = r * 0.012;
  ctx.stroke();

  rotateInto(p, globe.pilot, 0, rot);
  if (p[2] > 0.2) {
    const k = r / 300;
    const x = cx + r * p[0];
    const y = cy - r * p[1];
    ctx.fillStyle = "rgb(240 145 58 / 0.3)";
    ctx.beginPath();
    ctx.arc(x, y, (22 + 8 * pulse) * k, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#F0913A";
    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 3 * k;
    ctx.beginPath();
    ctx.arc(x, y, 8 * k, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

/**
 * La Tierra real en el estilo del kit, girando en el espacio. Es decoración: lo que dice la pantalla va en HTML.
 * Se dibuja en un lienzo 2D con la misma malla del diseño; no usa three.js.
 * Se puede girar arrastrándola con el ratón o con el dedo; al soltarla sigue girando sola.
 */
export function Earth({ progress, frame = centered, still = false, className = "" }: EarthProps) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;

    let globe: Prepared | undefined;
    let visible = true;
    let disposed = false;
    let width = 0;
    let height = 0;
    let lon = START_LON;
    let tilt = TILT;
    let shown: EarthFrame = { cx: 0, cy: 0, r: 0 };
    let drag: { id: number; x: number; y: number } | null = null;
    let releasedAt = -Infinity;
    let lastDraw = -Infinity;
    let lastTick = performance.now();
    let dirty = true;

    const draw = (now: number) => {
      const p = still ? 0 : Math.max(0, Math.min(1, progress?.current ?? 0));
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, el.width, el.height);
      const ratio = el.width / Math.max(1, width);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      drawStars(ctx, width, height);
      if (!globe) return;
      const front = still ? lon : lerpLon(lon, globe.data.pilot.lon, easeInOut(p));
      shown = frame(width, height, p);
      drawGlobe(ctx, globe, shown, front, tilt, still ? 0 : (Math.sin(now / 450) + 1) / 2);
    };

    const resize = () => {
      const rect = el.getBoundingClientRect();
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      width = rect.width;
      height = rect.height;
      el.width = Math.round(width * ratio);
      el.height = Math.round(height * ratio);
      dirty = true;
      if (still) draw(performance.now());
    };
    resize();
    const sizes = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    sizes?.observe(el);

    // Fuera de la pantalla no se dibuja: el giro no gasta batería mientras se lee el resto de la página.
    const seen =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(([entry]) => {
            visible = entry.isIntersecting;
            lastTick = performance.now();
          });
    seen?.observe(el);

    const tick = () => {
      const now = performance.now();
      const elapsed = Math.min(now - lastTick, 100);
      lastTick = now;
      if (!visible) return;
      // Mientras la arrastran no gira sola; al soltarla retoma su giro poco a poco.
      if (!drag) lon -= (SPIN * elapsed * Math.min(1, (now - releasedAt) / RESUME_MS)) / 1000;
      if (now - lastDraw < FRAME_MS && !dirty) return;
      lastDraw = now;
      dirty = false;
      draw(now);
    };
    if (!still) gsap.ticker.add(tick);

    loadGlobe()
      .then((loaded) => {
        if (disposed) return;
        globe = loaded;
        if (still) lon = loaded.data.pilot.lon;
        dirty = true;
        if (still) draw(performance.now());
      })
      .catch(() => {
        // Sin la malla quedan el cielo y las estrellas: la portada se lee igual.
      });

    // Girarla con el ratón o con el dedo: solo si se agarra sobre el disco, para no estorbar al resto de la portada.
    const onGlobe = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      return Math.hypot(event.clientX - rect.left - shown.cx, event.clientY - rect.top - shown.cy) <= shown.r;
    };
    const onDown = (event: PointerEvent) => {
      if (!globe || !onGlobe(event) || (event.pointerType === "mouse" && event.button !== 0)) return;
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
      el.setPointerCapture(event.pointerId);
      el.style.cursor = "grabbing";
      event.preventDefault();
    };
    const onMove = (event: PointerEvent) => {
      if (!drag || drag.id !== event.pointerId) {
        if (event.pointerType === "mouse") el.style.cursor = globe && onGlobe(event) ? "grab" : "";
        return;
      }
      // La superficie sigue al puntero: un radio de arrastre es un radián de giro.
      const degrees = 180 / Math.PI / Math.max(1, shown.r);
      lon -= (event.clientX - drag.x) * degrees;
      tilt = Math.max(-MAX_TILT, Math.min(MAX_TILT, tilt + (event.clientY - drag.y) * degrees));
      drag.x = event.clientX;
      drag.y = event.clientY;
      dirty = true;
      if (still) draw(performance.now());
    };
    const onUp = (event: PointerEvent) => {
      if (!drag || drag.id !== event.pointerId) return;
      drag = null;
      releasedAt = performance.now();
      el.style.cursor = event.type === "pointerup" && onGlobe(event) ? "grab" : "";
    };
    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);

    return () => {
      disposed = true;
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
      gsap.ticker.remove(tick);
      sizes?.disconnect();
      seen?.disconnect();
    };
  }, [frame, progress, still]);

  // En pantallas táctiles el arrastre vertical sigue haciendo scroll; el horizontal gira la Tierra.
  return <canvas ref={canvas} aria-hidden="true" className={`block size-full touch-pan-y ${className}`} />;
}
