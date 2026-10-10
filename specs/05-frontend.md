# Frontend: visión, estilo y stack

Cómo se ve, se siente y se construye la web de AgroSense. Complementa `03-sistemas.md` (qué hace cada subsistema W) y `04-stack.md` (resumen de tecnologías).

> **Estado:** dirección inicial de la fase 0. Todo lo de este documento se puede ajustar mientras se prototipa; las reglas R1–R10 y el contrato de la API no.

## Dónde se hace qué

| Momento | Qué se hace | Dónde |
|---|---|---|
| Fase 0 (10 oct – 13 nov) | Identidad visual, animaciones, audio, assets 3D y un prototipo navegable del frontend contra datos de ejemplo (EP-15) | Este repositorio, carpeta `web/` y Figma |
| Evento (14 y 15 nov) | La aplicación de la demo, integrada con la API real | Un repositorio nuevo, creado en el evento |

El prototipo sirve para decidir y ensayar el estilo. Qué se puede reutilizar en el evento depende de los términos de Space Apps 2026 (HU-004): hasta confirmarlo, se asume que el código se reescribe y que lo reutilizable son decisiones, diseños en Figma, guías y assets con licencia.

## Visión

La web parece un juego, pero es una herramienta real: cada pantalla responde una pregunta del agricultor con datos y reglas explicables. El juego aporta la sensación (tacto, ritmo, satisfacción de ver un resultado), no la mecánica.

### Inspiración, no copia

Las referencias son de **estilo**. No se traslada su estructura ni sus elementos.

| Referencia | Qué tomamos | Qué no tomamos |
|---|---|---|
| *The Farmer Was Replaced* | Low-poly con sombreado plano; paleta cálida y terrosa sobre un fondo frío y suave; luz difusa de diorama; botones gruesos y táctiles | Parcela flotante, ventanas de código, barra de recursos, dron, mecánica de programar |
| Web de *Grand Theft Auto VI* | Navegación narrativa guiada por scroll; transiciones de cámara y máscaras; ritmo cinematográfico | Su contenido, composición y tipografía |

Si una idea se reconoce como «una pieza del juego», se descarta.

### Concepto: del satélite al lote

- **Paisaje con suelo y horizonte.** Un paisaje andino continuo: montañas, niebla en los valles y el mosaico de parcelas en ladera del altiplano. Nada flota.
- **La navegación es un descenso.** La cámara baja del satélite (los datos de NASA) a la región, al municipio y a la finca. Cada nivel es una sección de la app; el scroll o los toques mueven la cámara.
- **El paisaje acompaña al dato.** Las parcelas del cultivo consultado se resaltan; el cielo refleja el clima de la ventana (nubes, lluvia, sequía). El paisaje refuerza, nunca reemplaza, el resultado escrito.

## Principios de diseño

1. **El dato manda.** Semáforo, acción, razones, limitaciones y cifras van en HTML legible por encima del canvas, nunca dibujados dentro de la escena 3D.
2. **El 3D es una mejora.** Sin WebGL, en modo ligero o con «reducir movimiento», la app funciona completa en 2D.
3. **Las reglas también son de diseño:**
   - R1: «datos insuficientes» y «no evaluable» se ven distintos de «desfavorable» (forma, patrón y texto; nunca rojo). En el paisaje se representan como niebla o trazo punteado, no como daño.
   - R5: los datos de ejemplo llevan rótulo visible en pantalla.
   - R9: la finca no sale del dispositivo.
   - R10: todo resultado de riego lleva «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote» y se muestra en rangos.
   - W2: el estado nunca depende solo del color.
4. **Cada acción tiene respuesta.** Tocar, elegir y cambiar prioridades produce un cambio visible inmediato.
5. **Español claro, sin jerga.** La jerga técnica vive en el glosario y en el detalle a pedido.

## Accesibilidad y rendimiento

Metas iniciales; se validan y ajustan con el prototipo.

| Tema | Meta |
|---|---|
| Ancho mínimo | 360 px sin desplazamiento horizontal (HU-096) |
| Accesibilidad | WCAG 2.2 AA; contraste de texto ≥ 4,5:1; foco visible; objetivos táctiles ≥ 44 px |
| Movimiento | Respeta `prefers-reduced-motion`; ninguna información depende de una animación |
| Audio | Apagado por defecto, con control visible; la app se entiende sin sonido |
| JS inicial | ≤ 200 KB comprimido, sin contar la escena 3D |
| Escena 3D | Se carga después de la primera pintura; ≤ 3 MB transferidos en total; modelos comprimidos |
| Carga | LCP ≤ 2,5 s en 4G lento simulado |
| Fluidez | ≥ 30 fps en un Android de gama media; si no se alcanza, pasa sola a modo ligero |

## Stack

Fijar versiones exactas al crear `web/`.

| Capa | Elección | Por qué |
|---|---|---|
| Base | React, TypeScript y Vite | FastAPI sirve el build estático en una sola imagen; no hace falta servidor Node |
| 3D | three.js con React Three Fiber y drei | Low-poly con sombreado plano es barato de renderizar y es la estética buscada |
| Animación | GSAP (ScrollTrigger, SplitText, Flip) con `@gsap/react` | Línea de tiempo precisa para cámara, scroll y UI; GSAP es gratuito con todos sus plugins |
| Scroll | Lenis | Scroll suave que se integra con R3F y ScrollTrigger |
| Estado | Zustand (escena y cámara) y TanStack Query (API) | Zustand comparte estado entre DOM y canvas sin re-render de todo el árbol |
| UI | Tailwind y primitivas de Radix con estilo propio | Accesibilidad de Radix sin el aspecto genérico de shadcn |
| Gráficas | SVG propio animado con GSAP | Pocas gráficas (lluvia, área sembrada, calendario de agua) y control total del estilo |
| Audio | Howler.js | Ambiente y efectos de interfaz con control de volumen y silencio |
| Datos | `openapi-typescript` y MSW | Igual que el resto del proyecto: tipos del contrato y respuestas simuladas |
| Assets 3D | glTF comprimido con `gltf-transform` | Un solo formato liviano |
| Diseño | Figma (conectado por el MCP TalkToFigma) | Moodboard, tokens, componentes y pantallas |
| Calidad | ESLint, Prettier y Vitest | Configuración mínima |

**Descartado por ahora:** Recharts (cuesta adaptarlo al estilo), MapLibre (el descenso 3D cubre la vista regional de HU-095; se retoma solo si la escena no alcanza), Next.js y Astro (no hay servidor Node en el despliegue).

## Assets y licencias

En el espíritu de R8, cada asset tiene autor, licencia y enlace en `web/public/assets/CREDITS.md`.

| Fuente | Qué aporta | Licencia | Nota |
|---|---|---|---|
| Quaternius LowPoly Crops | Cultivos en 5 etapas de crecimiento | CC0 | Viene en FBX/OBJ; se convierte a glTF |
| Kenney Nature Kit | Árboles, rocas, terreno, plantas | CC0 | — |
| Generados en código | Terreno, parcelas, cielo, efectos | Propios | Procedurales con three.js |

Solo se usan assets con licencia que permita uso y modificación. Si un asset se genera con un servicio de IA, se registra el servicio y sus términos.

## Método de motion

Adaptado de las técnicas para animaciones con Claude Opus 5.5 que circulan en X.

1. **Storyboard antes de animar.** Una tabla por secuencia: tiempo, qué se ve, para qué, cómo sale y qué objeto pasa a la siguiente toma.
2. **Primero lo compartido.** Colores, tipografías, modelos y posiciones de enlace entre escenas; luego cada escena como componente con su página de prueba.
3. **Crítico fresco.** Quien construye no juzga su obra: otro agente, sin contexto de la construcción, revisa capturas y devuelve problemas ordenados.
4. **Animación determinista.** Todo valor animado es función del tiempo de la línea de tiempo de GSAP; nada de temporizadores ni aleatoriedad sin semilla. Así la misma secuencia se puede renderizar como video de respaldo (HU-132).
5. **Reglas de escena:** cámara entre 35° y 55°; luz principal suave lateral y luz de contorno; etiquetas en HTML posicionadas desde la escena; 3D solo donde explica algo espacial.

## Skills y agentes

| Skill | Uso | Estado |
|---|---|---|
| [`greensock/gsap-skills`](https://github.com/greensock/gsap-skills) | Oficial de GSAP: core, timeline, ScrollTrigger, plugins, React, rendimiento | Por instalar |
| Una skill de React Three Fiber (candidatas: `anthemflynn/ccmp`, `Impertio-Studio/Three.js-Claude-Skill-Package`) | R3F, drei, rendimiento | Por evaluar |
| [`majidmanzarpour/threejs-game-skills`](https://github.com/majidmanzarpour/threejs-game-skills) | Ideas de UI de juego, QA y audio | Solo referencia (three.js sin R3F) |
| `agrosense-motion` | El método de motion de esta página como skill del proyecto | Por crear |
| `frontend-design`, `web-animations`, `ui-ux-pro-max` | Fundamentos de diseño y animación | Instaladas |

Toda skill de terceros se lee antes de instalarla: son instrucciones que se ejecutan con los permisos de quien la usa.

## Decisiones abiertas

Ver `docs/decisiones-abiertas.md`: intro narrativa con scroll, audio en P0 o P1, tipografías y paleta definitivas.
