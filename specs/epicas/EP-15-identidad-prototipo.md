---
id: EP-15
titulo: "Identidad visual y prototipo del frontend"
prioridad: "P0"
fase: "Fase 0"
rol: "Web"
agente: web
subsistemas: "W1–W7"
depende_de: "Ninguna (usa datos de ejemplo)"
reglas: "R1, R5, R9, R10"
estado: en curso
---

# EP-15 · Identidad visual y prototipo del frontend

**Resultado esperado:** El equipo llega al evento con la identidad visual, el sistema de animación, los assets y un prototipo navegable decididos y probados, para construir la demo sin improvisar el diseño.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Fase 0 |
| Rol responsable | Web |
| Agente sugerido | `web` (ver `.claude/agents/`) |
| Subsistemas | W1–W7 (ver `specs/03-sistemas.md`) |
| Depende de | Ninguna (usa datos de ejemplo) |
| Reglas de diseño que aplican | R1, R5, R9, R10 (ver `specs/01-reglas.md`) |

Guía de estilo, stack y método: `specs/05-frontend.md`. El prototipo vive en `web/` de este repositorio; la app del evento va en un repositorio nuevo (ver HU-004).

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-151 · Moodboard y dirección visual

- **Historia:** Como equipo, quiero un moodboard con la dirección visual, para acordar el estilo antes de construir.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Página de Figma con referencias, paleta tentativa y ejemplos de paisaje
  - [ ] Cada referencia dice qué se toma y qué no (inspiración, no copia)
  - [ ] Dirección aprobada por el equipo
- **Reglas que aplican:** —
- **Notas:** Concepto inicial «del satélite al lote» en `specs/05-frontend.md`.

### HU-152 · Tokens de diseño

- **Historia:** Como desarrollador web, quiero tokens de color, tipografía, espaciado, radios y sombras, para que Figma y el código usen los mismos valores.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tokens definidos en Figma y exportados a CSS o Tailwind
  - [ ] Colores del semáforo con su forma e icono; contraste de texto ≥ 4,5:1 comprobado
  - [ ] «No evaluable» y «datos insuficientes» tienen estilo propio, distinto de rojo (R1)
- **Reglas que aplican:** R1

### HU-153 · Kit de componentes con estilo de juego

- **Historia:** Como desarrollador web, quiero componentes base con estilo de juego y accesibles, para armar pantallas rápido.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Botón, selector con autocompletado, control de prioridad, tarjeta de señal, insignia de semáforo, rótulo de ejemplo y rótulo de estimación
  - [ ] Cada componente en Figma y en código, con estados de foco, deshabilitado y carga
  - [ ] Objetivos táctiles ≥ 44 px y navegación por teclado
- **Reglas que aplican:** R1, R5, R10

### HU-154 · Escena 3D del paisaje andino

- **Historia:** Como agricultor, quiero reconocer un paisaje como el mío, para sentir que la herramienta habla de mi zona.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Terreno low-poly continuo con montañas, niebla y mosaico de parcelas; nada flota
  - [ ] Cultivos con etapas de crecimiento a partir de assets CC0 o propios
  - [ ] Todos los assets listados en `web/public/assets/CREDITS.md` con licencia
  - [ ] Cumple el presupuesto de la escena de `specs/05-frontend.md`
- **Reglas que aplican:** R5

### HU-155 · Descenso de cámara del satélite al lote

- **Historia:** Como jurado, quiero recorrer del satélite a la finca, para entender en segundos cómo los datos de NASA llegan a una decisión.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cuatro niveles (satélite, región, municipio, finca) navegables con scroll y con toques
  - [ ] Storyboard escrito antes de animar
  - [ ] Con `prefers-reduced-motion`, los niveles cambian sin recorrido de cámara
- **Reglas que aplican:** —

### HU-156 · Sistema de motion

- **Historia:** Como equipo, quiero un sistema de animación con duraciones, curvas y patrones definidos, para que todo se mueva con el mismo ritmo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tokens de duración y curva documentados y usados en código
  - [ ] Patrones de entrada, salida, respuesta al toque y cambio de estado
  - [ ] Animaciones deterministas (función del tiempo de la línea de tiempo)
  - [ ] Revisión por un crítico distinto de quien construyó
- **Reglas que aplican:** —

### HU-157 · Audio de ambiente e interfaz

- **Historia:** Como usuario, quiero sonidos suaves de ambiente y de interfaz, para que la experiencia se sienta viva.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Apagado por defecto, con control visible y volumen
  - [ ] La app se entiende igual sin sonido
  - [ ] Licencia de cada sonido registrada
- **Reglas que aplican:** —
- **Notas:** P0 o P1 por decidir (ver `docs/decisiones-abiertas.md`).

### HU-158 · Modo ligero y movimiento reducido

- **Historia:** Como agricultor con un celular sencillo o poca señal, quiero que la app funcione rápido aunque no muestre el paisaje 3D, para usarla en el campo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Sin WebGL o con fps bajo, pasa sola a una versión 2D con la misma información
  - [ ] Interruptor manual de modo ligero
  - [ ] Cumple el JS inicial y el LCP de `specs/05-frontend.md`
- **Reglas que aplican:** —

### HU-159 · Prototipo navegable con datos de ejemplo

- **Historia:** Como equipo, quiero un prototipo navegable de diagnóstico, rotaciones y finca, para probar el estilo con el flujo real.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Recorre contexto, diagnóstico, rotaciones y plan de agua con respuestas simuladas del contrato
  - [ ] Muestra los cuatro estados del semáforo, «datos insuficientes» y error
  - [ ] Datos de ejemplo rotulados en pantalla; rótulo de estimación en el riego; la finca no sale del dispositivo
  - [ ] Usable a 360 px
- **Reglas que aplican:** R1, R5, R9, R10
- **Contrato que toca:** respuestas de ejemplo de `specs/02-contratos.md` (sin cambiarlo)
