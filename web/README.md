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

## Idiomas (HU-233)

La configuración vive en `src/lib/i18n.ts`, con `i18next` y `react-i18next`. Los textos están en
`src/locales/es.json` y `en.json`: diccionarios planos con las mismas claves, agrupadas por prefijos
(`nav.*`, `footer.*`, `landing.*`). Español es el predeterminado; `?lang=en` tiene prioridad sobre la preferencia
de `localStorage`. El selector está en la barra de escritorio y en el menú del celular.

Para seguir traduciendo una pantalla, agregue la misma clave en ambos diccionarios y use
`const { t } = useTranslation()` y `t("prefijo.clave")`. Las variables se escriben como `{{name}}` en el diccionario
y se pasan con `t("prefijo.clave", { name })`. Las fechas y los números se formatean con `Intl` según
`i18n.resolvedLanguage`. Los enlaces de `components/layout/LanguageLink.tsx` y `ButtonLink` conservan el idioma,
los parámetros y los fragmentos. No traduzca valores del contrato ni las razones o errores que manda la API.

Las pantallas de cuenta, finca y formularios, consulta, estrategias y ciclos, diagnóstico, cambios históricos, precios,
Cómo funciona, política de datos y estados usan los diccionarios, además de la portada y la navegación.
Los helpers sin React usan `t` y `locale()` de `src/lib/i18n.ts`; sus componentes se suscriben con `useTranslation()`.
En código nuevo de React use `const { t } = useTranslation()`: el `t` global se reserva para funciones fuera de React
y no suscribe al componente a los cambios de idioma. Nunca traduzca constantes al cargar un módulo;
obtenga las etiquetas dentro de una función al usarlas (por ejemplo, `SIGNAL_NAME()`). Para claves nuevas prefiera
el propósito del texto, como `how.step1.body`, en lugar de copiar la frase en inglés.
Las listas de etiquetas y los formatos se obtienen al usarlos (por ejemplo, `SIGNAL_NAME()`), para actualizarse al cambiar
de idioma. Los nombres visibles de cultivos se resuelven con `cropName()`, conservando `crop_id` y el catálogo original.
Las razones, limitaciones y errores recibidos de la API se conservan en español, con el aviso de `ApiLanguageNotice`.

El HTML prerenderizado permanece en español: al abrir en inglés, `main.tsx`
lo dibuja de nuevo con el idioma elegido, conservando los campos que se hubieran escrito y evitando diferencias de hidratación.
Pruebas de idiomas en `src/lib/i18n.test.tsx`; la revisión adaptable incluye `/?lang=en`.
`npm run test:i18n` revisa la portada, la persistencia, el menú móvil y la barra con sesión en Chrome.
Acepta `BASE` para probar también el build servido con `npm run preview`.
`npm run test:i18n:pages` recorre las pantallas públicas y con sesión usando datos de ejemplo locales, en los dos idiomas,
cuatro tamaños y los dos modos de movimiento. No crea cuentas ni usa la base de datos. Permite filtrar con
`TEST_LANGUAGE`, `WIDTHS` y `ROUTES`. Para la revisión adaptable completa en inglés, use
`TEST_LANGUAGE=en npm run test:responsive` (en PowerShell, `$env:TEST_LANGUAGE='en'`).

Cada página o texto que entre después debe incluir sus traducciones en el mismo PR. Agregue las rutas nuevas
a `e2e/language-pages.mjs`, con respuestas locales si requieren sesión, y compruebe los dos idiomas.
Esta revisión incluye Mensajes y el recorrido «Del satélite a su finca». Los mensajes escritos por usuarios y las
respuestas del responsable conservan su texto original; solo se traducen los rótulos, estados y fechas de la interfaz.

También se traducen el laboratorio (`/pruebas`, `/kit` y `/recorrido/1` a `/recorrido/3`) y sus ejemplos locales.
`src/lib/i18n-audit.test.ts` recorre los archivos de interfaz y detecta textos fijos en JSX, atributos accesibles,
constantes de etiquetas, objetos y plantillas, además de llamadas a claves inexistentes. Incluye regresiones con
`LAYER_NAME`, `STATUS_TEXT` y «Fecha de la imagen». Las excepciones de nombres propios y valores de protocolo son explícitas;
la comparación del error de fecha se comprueba contra el código del backend. La auditoría no sustituye la revisión
de los datos recibidos de la API: Precios usa
`marketProductName`, `marketGroupName` y `matchesMarketProduct` para mostrar nombres traducidos y buscar en ambos idiomas,
conservando los identificadores y las citas del DANE. Los 36 productos del catálogo publicado tienen traducción;
si el catálogo incorpora otro producto, agregue su clave `market.products.<product_id>` en ambos diccionarios.
Un producto desconocido conserva su nombre original, sin inventar una traducción. La revisión de páginas incluye
30 casos de navegación: 480 combinaciones de idioma, ancho y movimiento.

ESLint impide importar `Link`, `NavLink`, `Navigate`, `useNavigate` y `useSearchParams` directamente de `react-router`
en la aplicación: use `components/layout/LanguageLink`. Solo su implementación y el selector necesitan el router original.
El responsive abre también el detalle del suelo y sus explicaciones en inglés. Para incluir las rutas privadas,
use `SESSION` y `LOT` de una cuenta de la base local; las respuestas simuladas de cálculo no reemplazan la revisión
manual con `VITE_SIMULATION` desactivado, la API y PostgreSQL reales.

## Rendimiento

**Se mide con `npm run perf`, nunca sobre `npm run dev`.** El servidor de desarrollo entrega el código sin empaquetar y da notas muy bajas que no dicen nada del producto. `npm run perf` hace el build, lo sirve comprimido y corre Lighthouse tres veces por caso (Inicio y Entrar, en escritorio y en móvil, con y sin movimiento); cuenta la mediana y termina con error si un caso baja de su presupuesto (`e2e/perf.mjs`). El «móvil» es un teléfono de gama media con 4G lento, simulado: antes del evento hay que probar también en un teléfono de verdad.

Lo que sostiene esas notas:

- **Las páginas públicas llegan ya dibujadas.** Después de empaquetar, `scripts/prerender.mjs` genera el HTML del inicio, de «Entrar» y de la política de datos (`src/app/entry-server.tsx`). El navegador las pinta con el HTML y los estilos; la aplicación se trae y arranca después del primer pintado, sobre ese mismo HTML (`src/app/boot.ts`, `src/app/main.tsx`). Lo que la persona escriba antes de que arranque no se pierde.
- **Una página nueva solo se agrega a `PAGES` de `scripts/prerender.mjs` si se ve igual para todos** (no depende de la sesión) **y no cambia de estructura según el ancho de la pantalla** con `useMediaQuery`: en el build no hay pantalla. Lo que dependa del navegador (hora, preferencias, ancho) debe empezar igual que en el build y cambiar después, como `useDayPhase` o `useMediaQuery`.
- **Cada página carga solo lo suyo** (todas las rutas son `lazy`) y los paisajes van como imagen, no dentro del JavaScript.
- **El movimiento se carga aparte** (HU-158): GSAP, ScrollTrigger y Lenis (unos 48 kB comprimidos) están en su propio trozo (`src/lib/motion.ts`). En modo ligero no se descargan; con movimiento se piden junto con la aplicación. `npm run test:motion` lo comprueba sobre el build.

**Qué debe hacer el alojamiento:** servir `dist/` comprimido (gzip o brotli) y con caché larga para `/assets`; entregar `index.html` para `/`, y `entrar/index.html` y `politica-de-datos/index.html` para sus rutas; y para cualquier otra ruta de la aplicación, **`app.html`** (el cascarón vacío), no `index.html`. Si entrega el HTML de otra ruta no se rompe nada (la aplicación lo nota y dibuja de cero), pero se pierde la ventaja.

## Variables de entorno

Copie `.env.example` como `.env`. Las variables `VITE_*` quedan a la vista en el navegador: no son para secretos.

| Variable                                                                                     | Para qué                                                                                                                               |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_SOCIAL_GITHUB`, `VITE_SOCIAL_INSTAGRAM`, `VITE_SOCIAL_LINKEDIN`, `VITE_SOCIAL_YOUTUBE` | Redes del pie de página. Una red sin dirección no se dibuja                                                                            |
| `VITE_MUSIC_URL`                                                                             | Archivo de la música de fondo (por ejemplo `/audio/tema.mp3`, puesto en `public/audio/`). Vacío: suena una melodía generada por la web |
| `VITE_SIMULATION`                                                                            | `true` en `npm run dev`: respuestas simuladas, sin el motor (ver «Respuestas simuladas»). Nunca en producción                          |

Se leen en un solo lugar, `src/app/config.ts`. Ninguna dirección externa se escribe en el código.

## Respuestas simuladas (HU-013)

Con `VITE_SIMULATION=true` en `.env`, `npm run dev` responde con ejemplos el diagnóstico, las estrategias, el plan de agua, «Qué cambió», las tendencias, el suelo y los catálogos (`src/mocks/`). Una franja al pie lo rotula como ejemplo (R5). Las cuentas, los lotes y las temporadas siguen yendo a la API real. El build no incluye MSW.

- **Forzar un estado:** `?estado=` en la dirección de la página. Vale el nombre del ejemplo (`no_apto`, `sin_agua`, `no_aplica`) o el del contrato (`not_suitable`, `insufficient_data`, `not_applicable`); un error de la ruta por su número o su código (`503`, `dataset_unavailable`, `unauthorized`…); y en cualquier ruta `cargando` (no responde nunca) o `sin_conexion`. Un estado que la ruta no tiene responde el de siempre y lo avisa en la consola. La lista está en `SIMULATION_STATES` (`src/mocks/handlers.ts`).
- **De dónde salen:** de los ejemplos del OpenAPI (`backend/api/calc_examples.py`). Con la API arriba, `npm run api:examples` regenera `src/mocks/examples.json`; nunca se edita a mano.

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

- `src/api/`: el cliente (`client.ts`) y los tipos del contrato (`schema.d.ts`), que se generan con `npm run api:types` con la API arriba; nunca se escriben a mano.
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
