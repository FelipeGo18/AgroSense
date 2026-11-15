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
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] El guion sigue el flujo del MVP: lote (o municipio y área) → estrategias de rotación de 3 ciclos con su salud del suelo → un ciclo con su diagnóstico → agua del plan → «Qué cambió en su zona»
  - [x] El guion nombra en pantalla cada producto NASA que se usa y para qué (POWER, NASADEM, IMERG, MODIS NDVI, SMAP y la capa GIBS del mapa), y dice que POWER es un reanálisis
  - [x] El guion abre con la rotación, el suelo, los datos de la NASA y «Qué cambió»; la oferta va al final, como valor agregado («además, le avisamos si hay mucha papa sembrada en su zona»)
  - [ ] Dos casos: uno favorable, con una estrategia que cuida el suelo, y uno con una estrategia excluida por un ciclo de alto riesgo de clima. Ninguno de los dos tiene la sobreoferta como historia principal
  - [x] El guion muestra una ventana que no conviene con sus mejores ventanas (`other_window`) y, si el tiempo alcanza, un cultivo que no es apto para la zona
  - [x] El guion habla de «ventana de siembra», presenta el orden de ventanas y «Qué cambió» como historia de la zona, nunca como pronóstico, y dice que las estrategias se comparan por reglas, sin predecir cuánto mejora el suelo
  - [x] Si el tiempo alcanza, el guion muestra las dos luces (con las prioridades del agricultor y con el criterio de AgroSense) y dice que la decisión es del agricultor
  - [x] El guion dice que la región es un piloto y qué fuentes son propias de ella (decisión 11)
  - [ ] La oferta se muestra en un ciclo como una señal más, con su fuente y su fecha
  - [ ] Usuario de demo con lotes e historial, rotulado como ejemplo, y recorrido sin cuenta como respaldo
  - [ ] Ensayado al menos una vez
- **Reglas que aplican:** R5, R8
- **Notas:** Cambiado el 11 de octubre de 2026 (decisión 12): la oferta (`supply`) es valor agregado, no protagonista. Sigue siendo una de las seis señales, con su peso, y en las estrategias entra solo por el criterio de ingreso.
- **En curso (14 nov):** el guion está en `docs/guion-demo.md`. Los dos casos están elegidos con los datos publicados (dataset `2026.11.18`): **Duitama**, la sede, con la rotación de Agrosavia (papa, avena y arveja) adaptada al catálogo, donde la avena es avena con vicia, y empezando después de la papa (avena con vicia → arveja → papa), y **Güicán de la Sierra**, donde una papa sembrada en diciembre cae en una ventana con helada en unos 2 de cada 3 años del periodo normal y queda excluida por alto riesgo de clima. Si alcanza, la papa en Puerto Salgar como cultivo no apto, ya confirmada con el motor (el diagnóstico responde desde el #102). **Faltan:** confirmar los resultados de los dos casos con el motor (HU-071, HU-183, HU-084, HU-146, HU-216, HU-218 y HU-219, el agua para cerrar HU-076, y `climate_normal` en el manifiesto publicado, que llega con el #96); la oferta con su fuente y su fecha, que hoy sale «datos insuficientes» (HU-031, HU-072); el usuario de demo y el recorrido sin cuenta; y el ensayo.

### HU-132 · Video y descripción de la entrega

- **Historia:** Como jurado, quiero el video y la descripción según la guía de entrega, para evaluar el proyecto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Cumple la guía publicada el 13 de noviembre
  - [ ] Cita todas las fuentes de datos, con cada producto NASA por su nombre
  - [ ] La descripción incluye la tabla de cómo cubre el MVP cada parte del enunciado (`specs/00-vision.md`)
  - [x] Explica por qué AgroSense usa reglas con fuente y no aprendizaje automático (decisión 4 y 14): el reto sugiere la IA como opción, y las reglas dan lo que pide para cada estrategia (por qué, evidencia, beneficios, vacíos y riesgos a revisar)
  - [x] Muestra la comparación contra la rotación actual, que el reto pide de forma explícita (HU-223)
- **En curso (14 nov):** el borrador está en `docs/entrega.md`, según la *Project Submission Guide* (<https://www.spaceappschallenge.org/resources/project-submission-guide/>): plazo hasta el domingo 15 de noviembre a las 11:59 p. m. del evento local, todo en inglés (un video en español necesita subtítulos en inglés), demo de 30 segundos o menos o de hasta 7 diapositivas, y los campos de la página con su texto en inglés, más el guion del video. El campo de uso de IA lo responde Haider directamente en el formulario (decidido el 14 de noviembre de 2026). **Faltan:** ajustar los textos a lo que funcione al enviar y sumar la tabla de cobertura con esas filas; volver a generar `docs/licencias.md` (39 fuentes frente a 41 en el dataset); decidir el inglés de lo que se enlace del repositorio, que está en español; grabar y subir el video, y enviar.

### HU-133 · Impacto económico, social y ambiental

- **Historia:** Como jurado, quiero entender el impacto económico, social y ambiental y sus límites, para valorar el alcance.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Impacto presentado como potencial
  - [x] Límites dichos con claridad
- **Hecho (14 nov):** `docs/impacto.md`. Abre con «impacto potencial, no garantizado» y con dos cifras de contexto citadas: el 40 % del territorio con algún grado de erosión (IDEAM) y el 63 % de la papa del país en Cundinamarca y Boyacá (Fedepapa). El impacto ambiental, social y económico va atado a lo que hace el producto y a la fuente de cada regla, o a que es criterio del equipo; la oferta y el mercado se dicen como valor agregado que hoy sale «datos insuficientes». Trae una propuesta de cómo medirlo después del reto y los límites: no es pronóstico, la salud del suelo es una comparación, varias reglas son criterio del equipo sin validar por un agrónomo, los datos son de la zona y no del lote (R10), POWER es un reanálisis, es un MVP de hackatón y es una región piloto. Lo usan la descripción de la entrega (HU-132) y el cierre del guion (HU-131).

### HU-230 · Licencias del proyecto y de lo que usa

- **Historia:** Como equipo, quiero que el código tenga licencia y que la entrega diga la licencia de cada dato y librería de terceros, para que NASA acepte la solución.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] `LICENSE` en la raíz con Apache 2.0, la misma que NASA aplicaría si no se elige ninguna (10 de noviembre de 2026, aprobado por Felipe)
  - [x] La documentación de la entrega lista la licencia de cada material de terceros: los datos (de la tabla `sources`) y las librerías (las de Python de `uv.lock` y las de la web de `web/package-lock.json`)
  - [x] Cada material de terceros es libre o tiene una licencia OSI; si alguno no, se reemplaza o se documenta su permiso (GSAP: «Standard no-charge license», permiso documentado; decidido por Felipe el 14 de noviembre de 2026)
  - [x] Lo que sale de DIVIPOLA del DANE (CC BY-SA 4.0), como la tabla `municipalities`, se publica con esa misma licencia y la entrega lo dice
- **Reglas que aplican:** R8
- **Notas:** Lo piden los términos 2026 de Space Apps (https://www.spaceappschallenge.org/legal/, 7 de agosto de 2026; ver HU-004): el contenido original debe ser libre o tener licencia OSI; NASA no acepta una solución sin la documentación de las licencias de terceros, y puede quitar premios si no se citan todas las fuentes (HU-132). Agregada el 10 de noviembre de 2026.
