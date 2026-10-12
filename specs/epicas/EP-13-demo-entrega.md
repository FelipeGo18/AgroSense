---
id: EP-13
titulo: "Demo y entrega"
prioridad: P0
fase: [Hora 0, Evento]
rol: "Producto y agro"
agentes: [producto-agro]
subsistemas: [S4]
depende_de: [Todas las épicas P0]
reglas: [R5, R8]
estado: pendiente
---

# EP-13 · Demo y entrega

**Resultado esperado:** Una entrega completa que muestra el problema, cómo cubre AgroSense cada parte del enunciado del reto (`specs/00-vision.md`), el uso de los datos de la NASA y dos casos reales, sin prometer más de lo que hace el producto.

El guion se escribe desde la hora 0; el video y la entrega se cierran a partir de la hora 42.

## Historias de usuario

### HU-131 · Dos casos reales para la demo

- **Historia:** Como jurado, quiero ver dos casos reales en pocos minutos, para entender el valor rápido.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El guion sigue el flujo del MVP: lote (o municipio y área) → estrategias de rotación de 3 ciclos con su salud del suelo → un ciclo con su diagnóstico → agua del plan → «Qué cambió en su zona»
  - [ ] El guion nombra en pantalla cada producto NASA que se usa y para qué (POWER, NASADEM, IMERG, MODIS NDVI, SMAP y la capa GIBS del mapa), y dice que POWER es un reanálisis
  - [ ] El guion abre con la rotación, el suelo, los datos de la NASA y «Qué cambió»; la oferta va al final, como valor agregado («además, le avisamos si hay mucha papa sembrada en su zona»)
  - [ ] Dos casos: uno favorable, con una estrategia que cuida el suelo, y uno con una estrategia excluida por un ciclo de alto riesgo de clima. Ninguno de los dos tiene la sobreoferta como historia principal
  - [ ] El guion muestra una ventana que no conviene con sus mejores ventanas (`other_window`) y, si el tiempo alcanza, un cultivo que no es apto para la zona
  - [ ] El guion habla de «ventana de siembra», presenta el orden de ventanas y «Qué cambió» como historia de la zona, nunca como pronóstico, y dice que las estrategias se comparan por reglas, sin predecir cuánto mejora el suelo
  - [ ] Si el tiempo alcanza, el guion muestra las dos luces (con las prioridades del agricultor y con el criterio de AgroSense) y dice que la decisión es del agricultor
  - [ ] El guion dice que la región es un piloto y qué fuentes son propias de ella (decisión 11)
  - [ ] La oferta se muestra en un ciclo como una señal más, con su fuente y su fecha
  - [ ] Usuario de demo con lotes e historial, rotulado como ejemplo, y recorrido sin cuenta como respaldo
  - [ ] Ensayado al menos una vez
- **Reglas que aplican:** R5, R8
- **Notas:** Cambiado el 11 de octubre de 2026 (decisión 12): la oferta (`supply`) es valor agregado, no protagonista. Sigue siendo una de las seis señales, con su peso, y en las estrategias entra solo por el criterio de ingreso.

### HU-132 · Video y descripción de la entrega

- **Historia:** Como jurado, quiero el video y la descripción según la guía de entrega, para evaluar el proyecto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cumple la guía publicada el 13 de noviembre
  - [ ] Cita todas las fuentes de datos, con cada producto NASA por su nombre
  - [ ] La descripción incluye la tabla de cómo cubre el MVP cada parte del enunciado (`specs/00-vision.md`)

### HU-133 · Impacto económico, social y ambiental

- **Historia:** Como jurado, quiero entender el impacto económico, social y ambiental y sus límites, para valorar el alcance.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Impacto presentado como potencial
  - [ ] Límites dichos con claridad
