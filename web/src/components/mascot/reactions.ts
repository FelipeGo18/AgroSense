import { useCallback, useEffect, useState, type RefObject } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { playSound } from "@/lib/sound";
import type { MascotMood } from "./Mascot";
import { gsap } from "@/lib/motion";

/**
 * La mascota de un formulario reacciona a lo que hace la persona (HU-172):
 * - mira el campo donde se escribe y sigue el texto con las pupilas;
 * - se tapa los ojos en un campo de contraseña y espía con un ojo cuando la contraseña está a la vista;
 * - dice que no cuando la API rechaza lo enviado;
 * - celebra con un salto al entrar o crear la cuenta, justo antes de pasar a la finca (`celebrateThen`);
 * - brinca y se ríe si la tocan;
 * - bosteza y se duerme tras un rato sin actividad, y despierta cuando la persona vuelve.
 *
 * Es compañía: el gesto nunca es la única señal, lo que pasó lo dice siempre el texto. Sin movimiento (el sistema lo
 * pide o está el modo ligero) no reacciona.
 */

type Field = "watch" | "shy" | "peek" | null;
type Flash = "celebrate" | "deny" | "giggle" | null;
type Drowsy = "yawn" | "asleep" | null;

/** Cuánto se queda la página para que se vea la celebración antes de irse. */
const CHEER_MS = 750;
/** Tras cuánto rato sin tocar nada bosteza. */
const DROWSY_MS = 45_000;
const YAWN_MS = 2_400;

const cheerers = new Set<() => void>();

/**
 * Para lo que sale bien y cambia de página: si hay una mascota que pueda celebrar, celebra y después sigue `then`;
 * si no (sin movimiento, o no hay mascota), `then` corre de inmediato.
 */
export function celebrateThen(then: () => void) {
  if (cheerers.size === 0) return then();
  cheerers.forEach((cheer) => cheer());
  setTimeout(then, CHEER_MS);
}

/** Las mascotas de la escena que se ven ahora (la de pantallas angostas o la de anchas). */
const visibleMascots = (stage: HTMLElement | null) =>
  Array.from(stage?.querySelectorAll<SVGSVGElement>(".mascot") ?? []).filter((mascot) => mascot.getClientRects().length > 0);

/** Qué campo tiene el foco: uno de contraseña (escondida o a la vista), uno de texto, o ninguno. */
function readField(stage: HTMLElement | null): { kind: Field; input: HTMLInputElement | null } {
  const active = document.activeElement;
  const field = active instanceof HTMLElement && stage?.contains(active) ? active.closest<HTMLElement>("[data-field]") : null;
  if (!field) return { kind: null, input: null };
  const input = field.querySelector("input");
  const toggle = field.querySelector("button[aria-pressed]");
  if (toggle) return { kind: toggle.getAttribute("aria-pressed") === "true" ? "peek" : "shy", input };
  return { kind: active instanceof HTMLInputElement ? "watch" : null, input };
}

/** Las pupilas apuntan a donde va el texto del campo; sin campo, vuelven al centro. */
function aim(stage: HTMLElement | null, input: HTMLInputElement | null) {
  for (const mascot of visibleMascots(stage)) {
    const pupils = mascot.querySelectorAll(".mascot-pupil");
    if (pupils.length === 0) continue;
    if (!input) {
      gsap.to(pupils, { x: 0, y: 0, duration: 0.3, ease: "power2.out", overwrite: "auto" });
      continue;
    }
    const box = mascot.getBoundingClientRect();
    const eyes = { x: box.left + (161 / 300) * box.width, y: box.top + (116 / 250) * box.height };
    const at = input.getBoundingClientRect();
    // Más o menos donde va el cursor: avanza con lo escrito, sin salirse del campo.
    const caret = { x: at.left + 20 + Math.min(at.width - 40, input.value.length * 9), y: at.top + at.height / 2 };
    const angle = Math.atan2(caret.y - eyes.y, caret.x - eyes.x);
    gsap.to(pupils, { x: Math.cos(angle) * 5, y: Math.sin(angle) * 6, duration: 0.25, ease: "power2.out", overwrite: "auto" });
  }
}

const FLASHES: Record<Exclude<Flash, null>, { sound: Parameters<typeof playSound>[0]; ms: number; move: gsap.TweenVars }> = {
  celebrate: { sound: "cheer", ms: 900, move: { keyframes: { y: [0, -28, 0, -12, 0] }, duration: 0.7, ease: "power1.out" } },
  deny: {
    sound: "nope",
    ms: 1200,
    move: { keyframes: { rotation: [0, -8, 8, -7, 7, -3, 0] }, duration: 0.9, ease: "power1.inOut", transformOrigin: "50% 85%" },
  },
  giggle: {
    sound: "giggle",
    ms: 800,
    move: { keyframes: { y: [0, -16, 0], rotation: [0, -5, 5, 0] }, duration: 0.55, ease: "power1.out" },
  },
};

/**
 * `stage` es la escena que contiene el formulario y la mascota; `rejected`, el error que devolvió la API, si lo hubo.
 * Devuelve el gesto que la mascota debe hacer ahora en vez del suyo (`act`, nulo si ninguno) y qué hacer cuando la tocan.
 */
export function useMascotReactions(stage: RefObject<HTMLElement | null>, rejected: unknown) {
  const animated = !useReducedMotion();
  const [field, setField] = useState<Field>(null);
  const [flash, setFlash] = useState<Flash>(null);
  const [drowsy, setDrowsy] = useState<Drowsy>(null);

  // Cada error nuevo de la API es un «no».
  const [seen, setSeen] = useState(rejected);
  if (rejected !== seen) {
    setSeen(rejected);
    if (rejected && animated) setFlash("deny");
  }

  // El campo que tiene el foco, y por dónde va lo escrito.
  useEffect(() => {
    if (!animated) return;
    const update = () => {
      const { kind, input } = readField(stage.current);
      setField(kind);
      aim(stage.current, kind === "watch" || kind === "peek" ? input : null);
    };
    // El foco y el botón de «Mostrar» cambian después del evento: se lee en el cuadro siguiente.
    const later = () => requestAnimationFrame(update);
    const events = ["focusin", "focusout", "click", "input"] as const;
    events.forEach((name) => document.addEventListener(name, later));
    return () => {
      events.forEach((name) => document.removeEventListener(name, later));
      setField(null);
    };
  }, [animated, stage]);

  // Gestos de un momento: el salto, el «no», la risa. Pasan y la mascota vuelve a lo suyo.
  useEffect(() => {
    if (!flash) return;
    const { sound, ms, move } = FLASHES[flash];
    const mascots = visibleMascots(stage.current);
    playSound(sound);
    gsap.to(mascots, { ...move, overwrite: "auto", clearProps: "transform" });
    const timer = setTimeout(() => setFlash(null), ms);
    return () => clearTimeout(timer);
  }, [flash, stage]);

  // Lo que sale bien y cambia de página (entrar, crear la cuenta) se celebra antes de irse.
  useEffect(() => {
    if (!animated) return;
    const cheer = () => setFlash("celebrate");
    cheerers.add(cheer);
    return () => {
      cheerers.delete(cheer);
    };
  }, [animated]);

  // Sin actividad un buen rato, bosteza y se duerme; despierta en cuanto la persona vuelve.
  useEffect(() => {
    if (!animated) return;
    let last = Date.now();
    let asleep = false;
    let yawning: ReturnType<typeof setTimeout> | undefined;
    const wake = () => {
      last = Date.now();
      if (!asleep) return;
      asleep = false;
      clearTimeout(yawning);
      setDrowsy(null);
    };
    const check = setInterval(() => {
      if (asleep || document.hidden || Date.now() - last < DROWSY_MS) return;
      asleep = true;
      setDrowsy("yawn");
      playSound("yawn");
      yawning = setTimeout(() => setDrowsy("asleep"), YAWN_MS);
    }, 5_000);
    const events = ["pointermove", "pointerdown", "keydown", "wheel", "touchstart"] as const;
    events.forEach((name) => window.addEventListener(name, wake, { passive: true }));
    return () => {
      clearInterval(check);
      clearTimeout(yawning);
      events.forEach((name) => window.removeEventListener(name, wake));
      setDrowsy(null);
    };
  }, [animated]);

  const act: MascotMood | null = flash === "deny" ? "deny" : flash ? "celebrate" : (field ?? drowsy);

  // Mientras hace un gesto propio, la mariposa y el viento (SceneLife) no le mueven la mirada.
  useEffect(() => {
    const mascots = Array.from(stage.current?.querySelectorAll(".mascot") ?? []);
    mascots.forEach((mascot) => mascot.toggleAttribute("data-acting", act !== null));
  }, [act, stage]);

  /** La tocaron: brinca y se ríe. */
  const poke = useCallback(() => {
    if (animated) setFlash((now) => now ?? "giggle");
  }, [animated]);

  return { act, poke };
}
