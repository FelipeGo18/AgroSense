// El motor del movimiento: GSAP, ScrollTrigger y Lenis. Solo se llega aquí con `import()` desde `lib/motion.ts`, para que
// en modo ligero no se descargue (HU-158). Nunca se importa directo desde una página o un componente.
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import "lenis/dist/lenis.css";

gsap.registerPlugin(ScrollTrigger);

export { gsap, ScrollTrigger, Lenis };
