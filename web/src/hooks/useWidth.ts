import { useCallback, useRef, useState } from "react";

/**
 * El ancho en píxeles de un elemento, al día cuando cambia (ResizeObserver). Las gráficas lo usan para dibujarse a su
 * tamaño real: con un `viewBox` fijo el SVG escalaría el texto, que en el celular quedaría ilegible y en el escritorio,
 * enorme. Mientras no hay medida (o sin ResizeObserver, como en las pruebas) devuelve `fallback`.
 */
export function useWidth<T extends HTMLElement>(fallback: number) {
  const [width, setWidth] = useState(0);
  const observer = useRef<ResizeObserver | null>(null);
  const ref = useCallback((element: T | null) => {
    observer.current?.disconnect();
    observer.current = null;
    if (!element) return;
    const measure = () => setWidth(element.clientWidth);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    observer.current = new ResizeObserver(measure);
    observer.current.observe(element);
  }, []);
  return [ref, width || fallback] as const;
}
