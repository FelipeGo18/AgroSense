import { useEffect, useState } from "react";

/**
 * De una lista de secciones, cuál cruza la línea del medio de la pantalla. Entre dos secciones se queda en la última.
 * `ids` debe ser una lista estable (una constante del módulo).
 */
export function useActiveSection(ids: readonly string[]) {
  const [active, setActive] = useState(ids[0]);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = [...entries].reverse().find((e) => e.isIntersecting);
        if (entry) setActive(entry.target.id);
      },
      { rootMargin: "-50% 0px -50% 0px" },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [ids]);
  return active;
}
