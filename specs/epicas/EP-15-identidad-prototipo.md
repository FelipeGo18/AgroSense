---
id: EP-15
titulo: "Identidad visual y prototipo del frontend"
prioridad: P0
fase: [Fase 0]
rol: "Web"
agentes: [web]
subsistemas: [W1, W2, W3, W4, W6, W7, W8, W9]
depende_de: []
reglas: [R1, R5, R9, R10]
estado: en curso
---

# EP-15 · Identidad visual y prototipo del frontend

**Resultado esperado:** El equipo llega al evento con la identidad visual, el sistema de animación, los assets y un prototipo navegable decididos y probados, para construir la demo sin improvisar el diseño.

Guía de estilo, stack y método: `specs/05-frontend.md`. El prototipo vive en `web/` de este repositorio; la app del evento va en un repositorio nuevo (ver HU-004).

**Recorte del MVP (11 de octubre de 2026):** quedan en P0 el kit visual y los tokens (HU-151 a HU-153, hechos) y el modo ligero 2D (HU-158), que es el modo por defecto de la web del MVP. La escena 3D, el descenso de cámara, el sistema de motion y el prototipo navegable (HU-154, HU-155, HU-156 y HU-159) pasaron a P1.

## Historias de usuario

### HU-151 · Moodboard y dirección visual

- **Historia:** Como equipo, quiero un moodboard con la dirección visual, para acordar el estilo antes de construir.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Página de Figma con referencias, paleta tentativa y ejemplos de paisaje
  - [x] Cada referencia dice qué se toma y qué no (inspiración, no copia)
  - [x] Dirección aprobada por el equipo
- **Notas:** Concepto inicial «del satélite al lote» en `specs/05-frontend.md`. Moodboard en el frame «HU-151 · Moodboard AgroSense» de Figma; imágenes y créditos en `design/moodboard/FUENTES.md`. Dirección aprobada el 10 de octubre de 2026.

### HU-152 · Tokens de diseño

- **Historia:** Como desarrollador web, quiero tokens de color, tipografía, espaciado, radios y sombras, para que Figma y el código usen los mismos valores.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Tokens definidos en Figma (frame de muestras con el nombre de cada token) y exportados a CSS y Tailwind
  - [x] Colores del semáforo con su forma e icono; contraste de texto ≥ 4,5:1 comprobado
  - [x] «No evaluable» y «datos insuficientes» tienen estilo propio, distinto de rojo (R1)
- **Reglas que aplican:** R1
- **Notas:** Fuente de verdad en `design/tokens/tokens.json`; `python design/tokens/build_tokens.py` comprueba el contraste y genera `tokens.css`, `tailwind-theme.css` y `tokens-studio.json` (`--check` para CI). Lámina visual en `design/tokens/tokens.svg` (la genera `design/kit/tokens_sheet.py`) y en el frame «HU-152 · Tokens de diseño» de Figma. Con HU-153 los tokens pasaron de radios y sombras a bisel, canto, facetas y trazos. Sin variables de Figma: Tokens Studio exige plan de pago para crearlas y el MCP de Figma no puede; `tokens-studio.json` queda listo por si se retoma.

### HU-153 · Kit de componentes con estilo de juego

- **Historia:** Como desarrollador web, quiero componentes base con estilo de juego y accesibles, para armar pantallas rápido.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Botón, selector con autocompletado, control de prioridad, tarjeta de señal, insignia de semáforo, rótulo de ejemplo y rótulo de estimación
  - [x] Cada componente en Figma y en código, con estados de foco, deshabilitado y carga
  - [x] Objetivos táctiles ≥ 44 px y navegación por teclado
- **Reglas que aplican:** R1, R5, R10
- **Notas:** Estilo «diorama low-poly»: esquinas biseladas, caras trianguladas con luz desde la izquierda y canto inferior en lugar de sombra; el semáforo y las tarjetas son letreros clavados con estaca; la prioridad se elige tocando semillas (0 a 5), no con un deslizador. Diseño primero en Figma (frame «HU-153 · Kit de componentes»), generado desde `design/kit/` (`build_kit_svg.py`, `sheet.py`). Código en `web/src/components/` sobre la pieza base `Plate.tsx`; muestra en `npm --prefix web run dev`, ruta `/kit`; pruebas con `npm --prefix web test`. La insignia de semáforo y los rótulos no son interactivos: no tienen foco ni estado deshabilitado.

### HU-154 · Escena 3D del paisaje andino

- **Historia:** Como agricultor, quiero reconocer un paisaje como el mío, para sentir que la herramienta habla de mi zona.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Terreno low-poly continuo con montañas, niebla y mosaico de parcelas; nada flota
  - [ ] Cultivos con etapas de crecimiento a partir de assets CC0 o propios
  - [ ] Todos los assets listados en `web/public/assets/CREDITS.md` con licencia
  - [ ] Cumple el presupuesto de la escena de `specs/05-frontend.md`
- **Reglas que aplican:** R5
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP.

### HU-155 · Descenso de cámara del satélite al lote

- **Historia:** Como jurado, quiero recorrer del satélite a la finca, para entender en segundos cómo los datos de NASA llegan a una decisión.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Cuatro niveles (satélite, región, municipio, finca) navegables con scroll y con toques
  - [ ] Storyboard escrito antes de animar
  - [ ] La mascota satélite guía el recorrido (HU-172)
  - [ ] Con `prefers-reduced-motion`, los niveles cambian sin recorrido de cámara
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP, la NASA se ve en pantalla con la capa satelital GIBS del mapa del lote (HU-211) y con las fuentes nombradas en cada resultado. Guion en Figma («HU-155 · Recorrido A» y «Recorridos B y C»), generado desde `design/paisaje/`. Recorrido A aprobado: del satélite al lote en siete paradas, cuatro con interfaz y tres de tránsito. Dos alternativas en evaluación: B, el año del cultivo (el scroll avanza en el tiempo), y C, la travesía por la cordillera (el scroll avanza de lado). Los fondos son capas SVG generadas por código (`build_paisaje.py`), no imágenes ni video. Prototipos para probarlos: `npm --prefix web run dev` y abrir `/recorrido/1`, `/recorrido/2` y `/recorrido/3` (GSAP ScrollTrigger con scroll suave de Lenis; con «reducir movimiento» las paradas aparecen colocadas, sin viaje). El índice está en `/` y el kit en `/kit`. El recorrido 1 tiene diez escenas: entre versiones del mismo lugar la cámara se acerca y se funden; donde cambia el lugar se atraviesa una capa de nubes o niebla que tapa el corte. Falta elegir recorrido, la versión 3D y la prueba en móvil de gama media.

### HU-156 · Sistema de motion

- **Historia:** Como equipo, quiero un sistema de animación con duraciones, curvas y patrones definidos, para que todo se mueva con el mismo ritmo.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tokens de duración y curva documentados y usados en código
  - [ ] Patrones de entrada, salida, respuesta al toque y cambio de estado
  - [ ] Animaciones deterministas (función del tiempo de la línea de tiempo)
  - [ ] Revisión por un crítico distinto de quien construyó
  - [ ] Skill del proyecto `agrosense-motion` creada con este método
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP, las transiciones de la web 2D usan solo cambios de estado simples.

### HU-157 · Audio de ambiente e interfaz

- **Historia:** Como usuario, quiero sonidos suaves de ambiente y de interfaz, para que la experiencia se sienta viva.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Apagado por defecto, con control visible y volumen
  - [ ] La app se entiende igual sin sonido
  - [ ] Licencia de cada sonido registrada

### HU-158 · Modo ligero y movimiento reducido

- **Historia:** Como agricultor con un celular sencillo o poca señal, quiero que la app funcione rápido aunque no muestre el paisaje 3D, para usarla en el campo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] **En el MVP la web es 2D por defecto:** todas las pantallas del flujo (inicio, entrada, estrategias, ciclo, qué cambió, lote y cuenta) funcionan completas sin WebGL
  - [ ] Cuando exista la escena 3D (P1), sin WebGL o con fps bajo pasa sola a la versión 2D con la misma información, y hay un interruptor manual
  - [ ] Respeta «reducir movimiento»
  - [ ] Cumple el JS inicial y el LCP de `specs/05-frontend.md`
- **Notas:** Desde el 11 de octubre de 2026 el modo ligero 2D es el modo por defecto de la web del MVP (decisión 12).

### HU-159 · Prototipo navegable con datos de ejemplo

- **Historia:** Como equipo, quiero un prototipo navegable de diagnóstico, rotaciones y finca, para probar el estilo con el flujo real.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Recorre inicio, descenso, consulta y Mi finca con respuestas simuladas del contrato (modo simulación, HU-014)
  - [ ] Funciona como invitado y como usuario simulado con varios lotes
  - [ ] Muestra los cuatro estados del semáforo, «datos insuficientes» y error
  - [ ] Muestra «cultivo no apto para la zona», la acción `other_window` con sus mejores ventanas y una ventana de alto riesgo en el calendario
  - [ ] Datos de ejemplo rotulados en pantalla; rótulo de estimación en el riego; sin cuenta, la finca no se guarda en el servidor
  - [ ] Usable a 360 px
- **Reglas que aplican:** R1, R5, R9, R10
- **Contrato que toca:** respuestas de ejemplo de `specs/02-contratos.md` (sin cambiarlo)
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Las pantallas del MVP se diseñan y aprueban en Figma (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»).
