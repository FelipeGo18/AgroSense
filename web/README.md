# Web de AgroSense

React 19 + TypeScript + Vite. Estilo y decisiones en `specs/05-frontend.md`; las pantallas se diseñan y aprueban en Figma antes de programarlas (`design/pantallas/`).

```bash
npm install
npm run dev          # http://localhost:5173
npm test             # Vitest
npm run typecheck && npm run lint && npm run format:check
npm run build        # empaqueta y además dibuja el HTML de las páginas públicas (ver «Rendimiento»)
npm run perf         # auditoría de rendimiento sobre el build; falla si algo baja de su presupuesto
```

## Rendimiento

**Se mide con `npm run perf`, nunca sobre `npm run dev`.** El servidor de desarrollo entrega el código sin empaquetar y da notas muy bajas que no dicen nada del producto. `npm run perf` hace el build, lo sirve comprimido y corre Lighthouse tres veces por caso (Inicio y Entrar, en escritorio y en móvil, con y sin movimiento); cuenta la mediana y termina con error si un caso baja de su presupuesto (`e2e/perf.mjs`). El «móvil» es un teléfono de gama media con 4G lento, simulado: antes del evento hay que probar también en un teléfono de verdad.

Lo que sostiene esas notas:

- **Las páginas públicas llegan ya dibujadas.** Después de empaquetar, `scripts/prerender.mjs` genera el HTML del inicio y de «Entrar» (`src/app/entry-server.tsx`). El navegador las pinta con el HTML y los estilos; la aplicación se trae y arranca después del primer pintado, sobre ese mismo HTML (`src/app/boot.ts`, `src/app/main.tsx`). Lo que la persona escriba antes de que arranque no se pierde.
- **Una página nueva solo se agrega a `PAGES` de `scripts/prerender.mjs` si se ve igual para todos** (no depende de la sesión) **y no cambia de estructura según el ancho de la pantalla** con `useMediaQuery`: en el build no hay pantalla. Lo que dependa del navegador (hora, preferencias, ancho) debe empezar igual que en el build y cambiar después, como `useDayPhase` o `useMediaQuery`.
- **Cada página carga solo lo suyo** (todas las rutas son `lazy`) y los paisajes van como imagen, no dentro del JavaScript.

**Qué debe hacer el alojamiento:** servir `dist/` comprimido (gzip o brotli) y con caché larga para `/assets`; entregar `index.html` para `/` y `entrar/index.html` para `/entrar`; y para cualquier otra ruta de la aplicación, **`app.html`** (el cascarón vacío), no `index.html`. Si entrega el HTML de otra ruta no se rompe nada (la aplicación lo nota y dibuja de cero), pero se pierde la ventaja.

## Variables de entorno

Copie `.env.example` como `.env`. Las variables `VITE_*` quedan a la vista en el navegador: no son para secretos.

| Variable                                                                                     | Para qué                                                                                                                               |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_SOCIAL_GITHUB`, `VITE_SOCIAL_INSTAGRAM`, `VITE_SOCIAL_LINKEDIN`, `VITE_SOCIAL_YOUTUBE` | Redes del pie de página. Una red sin dirección no se dibuja                                                                            |
| `VITE_MUSIC_URL`                                                                             | Archivo de la música de fondo (por ejemplo `/audio/tema.mp3`, puesto en `public/audio/`). Vacío: suena una melodía generada por la web |

Se leen en un solo lugar, `src/app/config.ts`. Ninguna dirección externa se escribe en el código.

## Carpetas

```
src/
├── app/             # arranque: boot.ts y main.tsx, rutas (routes.tsx), direcciones (paths.ts), configuración (config.ts)
│                    #   y entry-server.tsx (dibuja las páginas públicas en el build)
├── pages/           # una carpeta por página. Una página solo compone; no tiene piezas reutilizables
│   ├── landing/     #   LandingPage.tsx, sections/ (una por tramo), content.ts (textos y datos de muestra)
│   ├── pending/     #   a dónde llevan los enlaces de pantallas diseñadas que aún no se programan; y el 404
│   └── lab/         #   pruebas de la fase 0 (kit y recorridos): solo se entra por la dirección
├── components/      # lo reutilizable entre páginas
│   ├── ui/          #   el kit: Button, Card, Plate, Logo, StatusTag, SignalIcon, TrafficLightBadge…
│   ├── layout/      #   TopBar, Footer, SmoothScroll, SoundToggle
│   ├── mascot/      #   Mascot y MascotGuide (la mascota que guía una página larga)
│   └── globe/       #   Earth (la Tierra que gira)
├── hooks/           # useReducedMotion, useMediaQuery, useSmoothScroll, useActiveSection, useReveal
├── lib/             # funciones sin React: followScroll, globe
├── assets/          # archivos generados o estáticos (globe.json sale de design/globo/build_globo.py)
└── styles/          # index.css: Tailwind y los tokens de design/tokens
```

Carpetas que se crean cuando haga falta su primera pieza, no antes:

- `src/api/`: el cliente (`client.ts`) y los tipos del contrato (`schema.d.ts`), que se generan con `npm run api:types` con la API arriba; nunca se escriben a mano. Faltan las respuestas simuladas de MSW (HU-013).
- `src/features/<dominio>/` (`auth` ya existe; `lots`, `strategies`… cuando lleguen): lo que es de un solo dominio y lo usan varias páginas: sus hooks de datos, su estado y sus componentes.

Para entrar y crear cuenta hace falta la API: `docker compose up app` en la raíz. Vite le pasa lo que llegue a `/api`, así la web y la API comparten origen. La web debe abrirse en `http://localhost:5173` (el origen que la API acepta, `WEB_ORIGINS`).

Dónde va cada cosa:

| Si es…                                         | Va en                                                    |
| ---------------------------------------------- | -------------------------------------------------------- |
| Una pantalla con dirección propia              | `pages/<página>/`, y su ruta en `app/routes.tsx`         |
| Un tramo o una pieza que solo usa esa pantalla | Dentro de la carpeta de la página                        |
| Algo que usan dos páginas o más                | `components/` (o `features/` si es de un dominio)        |
| Lógica sin JSX                                 | `hooks/` si usa React; `lib/` si no                      |
| Un texto o un dato de muestra                  | El `content.ts` de la página, rotulado como ejemplo (R5) |

## Rutas

Todas salen de `app/paths.ts`: los enlaces se arman con `PATHS`, nunca con texto suelto.

| Dirección                                                          | Qué es                                                                      |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `/`                                                                | Inicio (HU-173)                                                             |
| `/entrar`, `/crear-cuenta`                                         | Entrar y crear cuenta (HU-162, HU-163)                                      |
| `/mi-cuenta`, `/mi-cuenta/contrasena`, `/mi-cuenta/actividad`      | Mi cuenta, cambiar contraseña y mi actividad (HU-160, HU-178). Piden sesión |
| `/consultar`, `/mi-finca`, `/como-funciona`, `/politica-de-datos`  | Diseñadas, aún sin programar: muestran una página que lo dice               |
| `/pruebas`, `/kit`, `/recorrido/1`, `/recorrido/2`, `/recorrido/3` | Pruebas de la fase 0. No se enlazan desde la app                            |

## Reglas de React de este proyecto

Las reglas largas están en `.claude/skills/vercel-react-best-practices` y `.claude/skills/vercel-composition-patterns` (de Vercel, licencia MIT). Esta web es una SPA con Vite: de la primera **no aplican** las reglas `server-*` ni las de Next.js. Lo que sí se exige aquí:

1. **Ningún control sin función.** Un botón hace algo y un enlace lleva a un lugar que existe. Si su destino no existe todavía, no se dibuja.
2. **Enlace para ir, botón para hacer.** Navegar es `<Link>` o `ButtonLink`; `Button` es para acciones.
3. **Componer en vez de sumar banderas.** Antes de agregar un `boolean` a un componente, pruebe con `children` o con una variante explícita.
4. **Estado derivado se calcula al pintar**, no se copia con `useEffect`. Los efectos son para sincronizar con algo de fuera (el navegador, GSAP, un lienzo).
5. **Lo que cambia en cada cuadro va en una referencia, no en estado.** El avance del scroll y la posición de la mascota no vuelven a pintar React.
6. **Las animaciones se crean con `useGSAP`** (limpia sola) y se apagan con «reducir movimiento»: el contenido debe quedar ya colocado sin ellas.
7. **Cada página se carga aparte** (`lazy` en `routes.tsx`), salvo el inicio. Lo pesado (la malla de la Tierra) se pide después de la primera pintura.
8. **Importe directo del archivo** con el alias `@/`. Sin archivos `index.ts` que reexporten carpetas.
9. **El dato va en HTML.** La mascota, la Tierra y el paisaje son decoración (`aria-hidden`); lo que dicen se escribe al lado.
10. **Nunca solo color.** Un estado lleva silueta, ícono y texto; «sin datos» no se pinta como riesgo (R1).
11. **Sin lógica de decisión en el cliente.** El semáforo y el orden vienen de la API.
12. **Cada pieza con su prueba** de lo que promete (Vitest y Testing Library, por rol y por texto).

## Pruebas de scroll

`npm run test:scroll` (con el servidor de desarrollo arriba) estresa los recorridos de `/recorrido/*` en un Chrome real. Solo en la fase 0, fuera de Docker y de CI.
