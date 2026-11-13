# Reglas de la web (valen para todo lo nuevo)

Se aplican a toda pantalla, vista o componente que se cree en `web/`, sin que nadie lo pida. Si una regla estorba, se cambia aquí y en `specs/05-frontend.md`; no se salta. Contexto: HU-158 (modo ligero) y HU-096 (uso desde el celular).

## 1. Modo ligero: todo lo que se mueve debe poder quedarse quieto

El modo ligero es la misma información sin scroll suave, sin recorrido animado y sin movimiento. Hay **un solo interruptor** (`src/lib/lightMode.ts`). Lo enciende la persona con el botón «Modo ligero» de la barra superior, o el equipo con «reducir movimiento» o el ahorro de datos (modo automático). Se refleja en `<html data-light>`.

**Qué hacer al crear algo animado:**

1. **JS:** pregunte `useAnimated()` (`@/hooks/useLightMode`). Si es falso, dibuje el componente ya colocado y quieto, con los mismos textos, botones y datos. El patrón de la portada: la página decide `animated` una vez y se lo pasa a sus secciones (`<Hero animated={animated} />`).
2. **CSS:** las animaciones y transiciones van con la variante `animated:` (`animated:transition-transform`). El CSS global (`styles/index.css`) apaga igual toda `animation` y `transition` que se escriba fuera de ella: es la red de seguridad, no la regla.
3. **Lienzos y bucles** (`canvas`, `gsap.ticker`, `requestAnimationFrame`): en modo ligero dibujan una vez y no corren (como `Earth` con `still`).
4. **GSAP y Lenis se cargan aparte** (`src/lib/motion.ts`): en modo ligero no se descargan.
   - Se importan de `@/lib/motion` (`gsap`, `ScrollTrigger`, `Lenis`), nunca de `gsap` ni de `lenis`. Los efectos se escriben con `useMotionEffect` (`@/hooks/useMotionEffect`), que es `useGSAP` sin traer GSAP al paquete. El lint lo hace cumplir.
   - Donde `useAnimated()` es verdadero, el motor ya llegó. Excepción: el primer dibujo sobre el HTML del build (Inicio, Entrar, la política) se hace como con movimiento. Por eso un efecto que use `gsap.ticker` o `Lenis` por fuera de `useMotionEffect` pregunta también `motionLoaded()`.
5. **Scroll:** nada secuestra el scroll ni pega («pin») una sección en modo ligero. El contenido tiene su altura natural y los enlaces internos saltan sin animar (`scrollTo` de `SmoothScroll` ya lo hace).
6. **La información no puede depender de una animación.** Nada empieza escondido (`opacity-0`, `autoAlpha: 0`, fuera de pantalla) si algo que solo corre con movimiento lo tiene que mostrar. Si una pieza entra animada, en modo ligero ya está a la vista.

`useReducedMotion()` (`@/hooks/useReducedMotion`) sigue existiendo por compatibilidad y es `!useAnimated()`; en código nuevo se usa `useAnimated()`.

**Prohibido:** leer `prefers-reduced-motion` o `matchMedia` por su cuenta para decidir movimiento (eso es de `lightMode.ts`), crear otro interruptor de movimiento, usar GSAP, Lenis o ScrollTrigger fuera de un componente que reciba `animated`, o importarlos directo (`gsap`, `gsap/*`, `lenis`, `@gsap/react`): solo el laboratorio lo hace.

**Pantalla nueva, lista cuando:** se ve completa y sin tocar nada en modo ligero (una prueba con `setLightMode(true)`), y está en `ROUTES` de `e2e/responsive-check.mjs`.

## 2. Diseño adaptable: reglas globales, no arreglos pantalla por pantalla

Mobile-first. Lo base es la pantalla de 320 px de ancho; `sm`, `md`, `lg` y `xl` (los de Tailwind: 640, 768, 1024 y 1280 px) solo agregan. No se inventan otros cortes, salvo un `min-[Npx]` o `max-[Npx]` justificado por una medición.

- **Márgenes laterales:** `container-page` (`styles/index.css`). No se repite `px-5 md:px-12 lg:px-24`.
- **Cuadrículas:** siempre con columnas explícitas desde la base: `grid grid-cols-1 sm:grid-cols-2`. Un `grid` sin `grid-cols-*` crea una columna que se ensancha con su contenido y rompe el ancho.
- **Filas con varias piezas (`flex`):** `flex-wrap`, salvo que quepan juntas a 320 px. Los hijos con texto largo llevan `min-w-0`.
- **Anchos fijos:** nunca sin su versión angosta: `w-full sm:w-[300px]`. Un ancho fijo no puede pasar de 280 px en la base, ni usarse en un contenedor que a 320 px mida menos.
- **Alturas:** `min-h-svh`, no `h-svh`, para contenido. Nada depende de que la pantalla sea alta: se prueba con alturas bajas (320, 568 y 600 px).
- **Posición absoluta:** solo dentro de una caja con tamaño propio. En el celular, lo que esté al lado de otra cosa va en el flujo normal (una columna), no encima.
- **Tipografía:** títulos grandes con `clamp()`, y que el título más largo quepa a 320 px.
- **Objetivos táctiles:** ≥ 44 px de alto y de ancho. Ojo: en esta web `1rem` son 18 px, así que `size-11` mide unos 50 px.
- **Una sola columna a 360 px** y **sin scroll horizontal** en ningún ancho (HU-096).
- **Nada se corta en silencio:** `overflow-hidden` o `overflow-x-clip` no arregla un desborde, lo esconde. Si algo se sale, se corrige.

**Pantalla nueva, lista cuando** `npm run test:responsive` pasa con su ruta agregada y se ve bien a 320, 360, 768, 1024 y 1440 px.

## 3. Comandos

```bash
npm run dev -- --port 5190 --strictPort    # en una terminal
npm run test:responsive                    # en otra: desborde, tamaños, modo ligero (BASE=http://localhost:5190)
npm run test:motion                        # sobre el build: GSAP y Lenis no se descargan en modo ligero y nada se rompe
npm test                                   # vitest
npm run typecheck && npm run lint
```

- Si la API no está en el 8000: `API_PROXY=http://127.0.0.1:8001 npm run dev`.
- Páginas con sesión (Mi finca, el lote, sembrar, Mi cuenta): `SESSION=<cookie agrosense_session> LOT=<lot_id> npm run test:responsive`, con una cuenta de prueba de la base **local** (nunca la de la nube) que tenga un lote; las rutas se suman solas. Borre la cuenta de prueba al terminar.
- Las estrategias, sus ciclos y el diagnóstico completo se ven con la web en simulación (`VITE_SIMULATION=true npm run dev -- --port 5190 --strictPort`): el script pone el área de la consulta en la pestaña.
