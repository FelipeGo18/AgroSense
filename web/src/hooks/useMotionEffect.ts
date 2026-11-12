import { useLayoutEffect, useRef, type RefObject } from "react";
import { gsap, motionLoaded } from "@/lib/motion";

type ContextSafe = <T extends (...args: never[]) => unknown>(func: T) => T;
type MotionCallback = (context: gsap.Context, contextSafe?: ContextSafe) => unknown;

interface MotionConfig {
  /** Dentro de qué elemento buscan los selectores de texto. */
  scope?: RefObject<Element | null>;
  dependencies?: unknown[];
  /** Deshacer lo animado cada vez que cambia una dependencia, no solo al desmontar. */
  revertOnUpdate?: boolean;
}

const NONE: unknown[] = [];

/**
 * Lo mismo que `useGSAP` de `@gsap/react` (misma limpieza, mismo `contextSafe`), pero con el GSAP que se carga aparte
 * (`lib/motion.ts`): `useGSAP` lo traería en el paquete inicial, también en modo ligero. Sin el motor no corre nada; los
 * componentes ya se dibujan quietos cuando `useAnimated()` es falso.
 */
export function useMotionEffect(callback: MotionCallback, { scope, dependencies = NONE, revertOnUpdate = false }: MotionConfig = {}) {
  const context = useRef<gsap.Context | null>(null);
  const mounted = useRef(false);
  // Con dependencias y sin `revertOnUpdate`, lo animado se deshace al desmontar, no en cada cambio (como en useGSAP).
  const deferCleanup = dependencies.length > 0 && !revertOnUpdate;

  useLayoutEffect(() => {
    if (!deferCleanup) return;
    mounted.current = true;
    return () => context.current?.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al montar y desmontar, como en useGSAP
  }, []);

  useLayoutEffect(() => {
    if (motionLoaded()) {
      context.current ??= gsap.context(() => {}, scope);
      context.current.add(callback as (...args: unknown[]) => unknown, scope);
    }
    if (!deferCleanup || !mounted.current) return () => context.current?.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- las dependencias las dice quien llama, como en useGSAP
  }, dependencies);
}
