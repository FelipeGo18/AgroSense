---
id: EP-09
titulo: "Diagnóstico usable en la web"
prioridad: P0
fase: [Evento]
rol: "Web"
agentes: [web]
subsistemas: [W1, W2, W3, W6]
depende_de: [HU-012, HU-013, EP-07]
reglas: [R1, R2, R3, R5, R8, R9, R10]
estado: pendiente
---

# EP-09 · Diagnóstico usable en la web

**Resultado esperado:** Un agricultor elige desde el celular su municipio, su cultivo y cuándo quiere sembrar, ajusta si quiere lo que más le importa, y entiende sin ayuda si el cultivo se da en su zona, cómo sale esa ventana de siembra con su criterio y con el de AgroSense, qué dice cada fuente y, si no conviene, cuáles ventanas han sido mejores o qué otros cultivos salen mejor. Todo es informativo: decide el agricultor.

Arranca contra las respuestas simuladas (HU-013) y se integra con EP-07.

## Historias de usuario

### HU-091 · Elegir municipio, cultivo y cuándo sembrar

- **Historia:** Como agricultor, quiero elegir municipio, cultivo y cuándo sembrar entre opciones válidas, para no equivocarme.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Buscador de municipios con autocompletado
  - [ ] Solo opciones del catálogo; para el diagnóstico, solo cultivos con `kind = crop`
  - [ ] «Cuándo sembrar» se elige por mes entre los próximos doce y, si el agricultor quiere, por una semana de ese mes; la web envía `sowing_date`. Es el único selector de tiempo de la consulta
  - [ ] Pregunta «¿Tiene riego?» con «Sí», «No» y «No sé» (`irrigated` verdadero, falso o nulo); con un lote, el valor sale del lote
  - [ ] Validación inmediata en pantalla
- **Contrato que toca:** cuerpo de `POST /api/v1/diagnostics`
- **Notas:** El municipio se busca en el nivel «satélite» del descenso (`specs/05-frontend.md`). Supuesto por confirmar con el contrato: qué fecha se envía cuando el agricultor elige solo el mes.

### HU-092 · Semáforo con señales, razones y limitaciones

- **Historia:** Como agricultor, quiero ver el semáforo con sus señales, razones y limitaciones, para entender el resultado.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] «Desfavorable» y «no evaluable» se distinguen con forma y texto, no solo con color
  - [ ] La acción sugerida es lo primero que se lee
  - [ ] Se ve la ventana evaluada: fecha de siembra y cosecha estimada, con el rótulo «Estimación con un año normal, no es pronóstico»
  - [ ] Las seis señales (agua, heladas, calor, suelo, oferta y mercado); «No aplica» se ve distinto de «datos insuficientes». Las señales del P1 se muestran solo si vienen en la respuesta
  - [ ] La señal de agua dice si se evaluó con riego o sin riego
  - [ ] La señal de oferta dice de qué año y semestre de EVA es el dato y si es preliminar
  - [ ] Cada señal muestra su calificación de 0 a 100 (`score`) junto al nivel en texto; sin calificación, no se dibuja una barra en cero (R1)
  - [ ] La señal que más limita la ventana (`limiting_signal`) se marca «Lo que más limita» con forma y texto
  - [ ] Cuando una señal trae `sources`, se ven todas juntas, cada una con su valor, su origen y su fecha, y se marca cuál calculó la señal («Usada para la luz»); las demás llevan «Para contrastar». Nunca se muestra un valor combinado
  - [ ] El suelo lleva su rango y el rótulo de estimación (R10)
- **Reglas que aplican:** R1, R5, R8, R10
- **Contrato que toca:** `signals` (con `score`, `counts` y `sources`) y `limiting_signal` de la respuesta de diagnóstico

### HU-194 · Cultivo no apto y mejores ventanas

- **Historia:** Como agricultor, quiero que la pantalla me diga cuando mi cultivo no se da en mi zona y, cuando la fecha no conviene, cuáles ventanas han sido mejores, para saber qué hacer en lugar de quedarme con un «no».
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Con `suitability.level = not_suitable`: la pantalla dice «Este cultivo no se da en su zona», muestra la razón con el dato de la ficha y su fuente, y ofrece «Elegir otro cultivo» y «Ver qué sembrar» (rotaciones). No dibuja señales ni ventanas
  - [ ] Con `suitability.level = insufficient_data`: el resultado se muestra normal y la limitación lo dice; no se pinta como riesgo (R1)
  - [ ] Con acción `other_window`: lista de `best_windows` con fecha de siembra, cosecha estimada, la nota del factor que más limita (número principal) y el promedio con sus prioridades (secundario); tocar una consulta el diagnóstico de esa fecha
  - [ ] Con `other_window` y `best_windows` vacío: mensaje «En los próximos doce meses no hay una ventana sin riesgo alto» y enlace a rotaciones
  - [ ] Las ventanas llevan el rótulo «Según la historia de la zona. No es un pronóstico»
  - [ ] Cada botón tiene una acción o una navegación definida
- **Reglas que aplican:** R1, R3, R5
- **Contrato que toca:** `suitability` y `best_windows` de la respuesta de diagnóstico
- **Notas:** El orden completo de las ventanas, con prioridades y detalle por semanas, está en la lectura «Planear una siembra» del calendario (HU-180). Los cultivos alternativos de la acción `rotate` son HU-203. Agregada el 11 de octubre de 2026.

### HU-202 · Ajustar mis prioridades al consultar

- **Historia:** Como agricultor, quiero decir qué me importa más de cada señal al consultar, para que el semáforo y el orden de las ventanas reflejen mi criterio.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Seis controles, uno por señal (agua, heladas, calor, suelo, oferta y mercado), de 0 a 5, con el control de prioridad del kit (cinco semillas y un «0»)
  - [ ] Empiezan en los pesos por defecto de AgroSense, tomados de `weights` de una respuesta sin `priorities`; un botón «Volver al criterio de AgroSense» los restablece
  - [ ] Al cambiar uno, la web vuelve a pedir el diagnóstico con `priorities`
  - [ ] Con todos en 0, la web no envía la petición y pide subir al menos uno
  - [ ] Junto a los controles, un texto corto: «0: no cambia la luz, salvo un riesgo grave de clima. 4 o 5: un resultado medio cuenta como desfavorable»
  - [ ] Las mismas prioridades se usan en «Planear una siembra» (HU-180) durante la misma visita
  - [ ] Con cuenta, las prioridades se guardan en el perfil (`PATCH /me`, `priorities`); sin cuenta, en el navegador. Siempre se puede volver al criterio de AgroSense
  - [ ] Cada control tiene una función; nada decorativo
- **Reglas que aplican:** R2, R9
- **Contrato que toca:** `priorities` del cuerpo de `POST /api/v1/diagnostics` y de `POST /api/v1/calendar`; `weights` de la respuesta
- **Notas:** Decisión 10. Son distintas de las cuatro prioridades de las rotaciones (HU-101). Supuestos por confirmar: si las prioridades se recuerdan en el dispositivo entre visitas o, con cuenta, en el perfil (el contrato no tiene dónde guardarlas); si los controles están a la vista o en un panel «Mis prioridades».

### HU-203 · Dos luces y cultivos alternativos

- **Historia:** Como agricultor, quiero ver la luz con mis prioridades y la de AgroSense cuando no coinciden, y qué otros cultivos salen mejor cuando conviene cambiar, para decidir yo con toda la información.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Si `overall.light` y `overall_default.light` son iguales, se ve una sola luz
  - [ ] Si difieren, se ven las dos con su acción: «Con sus prioridades: verde · Con el criterio de AgroSense: amarillo», cada una con forma y texto, no solo color. La de sus prioridades va primero
  - [ ] Una señal con `counts = false` se sigue viendo, con el rótulo «No cuenta para la luz con sus prioridades»
  - [ ] Un riesgo grave de clima con peso 0 lleva el rótulo «Cuenta siempre: riesgo grave»
  - [ ] Con `alternatives`, una lista «Otros cultivos que en esta ventana salen bien en clima y tienen mejor oferta», cada uno con su nombre y sus razones; tocar uno consulta el diagnóstico de ese cultivo en la misma fecha
  - [ ] Con `alternatives` vacío, el mensaje «No encontramos otro cultivo apto que salga mejor en esta ventana» y el enlace a «Qué sembrar después» (rotaciones)
  - [ ] Rótulo visible: «Es información para decidir. La decisión es suya»
  - [ ] Cada botón tiene una acción o una navegación definida
- **Reglas que aplican:** R1, R2, R5
- **Contrato que toca:** `overall`, `overall_default`, `weights`, `signals.*.counts` y `alternatives` de la respuesta de diagnóstico
- **Notas:** Decisión 10. Depende de HU-074 y HU-197 (o de sus respuestas simuladas). Supuesto por confirmar: si las alternativas se muestran cuando solo `overall_default` pide rotar.

### HU-093 · Gráficas de agua y área sembrada

- **Historia:** Como agricultor, quiero ver año por año la lluvia de mi ventana frente a lo que el cultivo necesita, y el área sembrada en el tiempo, para ver la tendencia con mis ojos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Dos gráficas con unidades y periodo visibles: `water` (lluvia y necesidad del cultivo, en mm) y `supply` (área sembrada, en ha)
  - [ ] Cada gráfica dice qué periodo muestra: los meses de la ventana en la de agua y el semestre de EVA en la de área
  - [ ] Los años preliminares de EVA se marcan
  - [ ] Una serie con `insufficient_data` muestra su estado vacío, no una gráfica en cero (R1)
- **Reglas que aplican:** R1, R5
- **Contrato que toca:** `GET /api/v1/trends`

### HU-094 · Estados de carga, vacío y error

- **Historia:** Como usuario, quiero mensajes claros cuando algo carga, falla o no tiene datos, para saber qué hacer.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Estados de carga, vacío, sin cobertura y error
  - [ ] Los datos de ejemplo se rotulan

### HU-095 · Mapa regional por semáforo

- **Historia:** Como agricultor, quiero ver la región en un mapa coloreado por semáforo, para comparar mi zona con las vecinas.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] GeoJSON propio de la región, sin mapa base externo
  - [ ] Clic en un municipio lo selecciona
  - [ ] El color de cada municipio es el del diagnóstico del cultivo y la fecha de siembra elegidos, con las prioridades de la consulta; un municipio donde el cultivo no es apto se distingue con forma y texto
- **Notas:** Se dibuja en el nivel «región» de la escena 3D (`specs/05-frontend.md`). En modo ligero, una lista de municipios con su estado en forma y texto.

### HU-096 · Uso desde el celular

- **Historia:** Como agricultor, quiero usar la herramienta desde el celular, porque es lo que tengo en el campo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usable a 360 px de ancho sin desplazamiento horizontal
