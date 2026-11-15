# Semilla Sputnik · la mascota de AgroSense (HU-171)

Una semilla germinando dibujada como caricatura de los años 60: tinta gruesa, ojos de pastel y brazos de manguera.
Las raíces son las antenas, el brote es la antena de señal y las hojas son los paneles.

## Dónde vive cada versión

| Versión | Archivo | Para qué |
|---|---|---|
| Bocetos y conceptos | `conceptos.py`, `conceptos_estilos.py`, `conceptos*.svg` y Figma (tres rondas) | Historia del diseño; las propuestas descartadas se conservan |
| 2D por capas (la final) | `semilla_sputnik.py` → `semilla-sputnik.svg`; en la web, `web/src/components/mascot/Mascot.tsx` | Toda la web: estados de ánimo, guía de los recorridos, modo ligero |
| 3D low-poly | `web/src/components/mascot/Mascot3D.tsx` (three.js con React Three Fiber) | El recorrido del satélite a la finca (HU-155), solo con movimiento |

Decidido por Felipe el 14 de noviembre de 2026: la versión final por capas vive en el código, no en Figma.

## Partes y puntos de giro

Cada parte animable tiene su clase en la versión 2D y su grupo en la 3D. El punto de giro es el mismo en las dos.

| Parte | Clase 2D | Grupo 3D | Punto de giro | Qué hace |
|---|---|---|---|---|
| Semilla | `mascot-body` | `body` | El centro de la semilla | Flota arriba y abajo |
| Brote y hojas | `mascot-sprout` | `sprout` | La punta de la semilla, donde nace el brote | Se mece |
| Brazo izquierdo | `mascot-arm-left` | `arm-left` | El hombro (en 2D, `108px 138px` del lienzo de 300 × 250) | Saluda de vez en cuando |
| Brazo derecho | `mascot-arm-right` | `arm-right` | El hombro | Señala o saluda |
| Raíces | `mascot-roots` | `roots` | Bajo la semilla, donde salen | Se barren hacia atrás al volar |
| Ojos | `mascot-eyes` | `eyes` | El centro de los ojos | Parpadean (escala en Y) |
| Mirada | `mascot-gaze`, `mascot-pupil` | — | El centro de cada ojo | Las pupilas siguen lo que mira |
| Boca | `mascot-mouth` | (sonrisa fija) | — | Cambia según el estado de ánimo |

## Colores

Tinta `#1D1D1B`, crema `#FFF6E0`, semilla `#C8873A` (clara `#E3AE68`), hojas `#5FA052` y `#8CC56A`, manguera `#E76F51`.
La semilla puede cambiar según el contexto (`sprouted`, `bean`, `maize`): solo cambia la forma y el color de la semilla.

## Modo ligero

La versión 3D no se descarga en modo ligero (HU-158): la página usa la 2D quieta, con los mismos textos.
