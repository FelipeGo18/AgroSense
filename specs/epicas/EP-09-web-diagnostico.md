---
id: EP-09
titulo: "Diagnóstico usable en la web"
prioridad: P0
fase: [Evento]
rol: "Web"
agentes: [web]
subsistemas: [W1, W2, W3, W6, W10]
depende_de: [HU-012, HU-013, EP-07]
reglas: [R1, R2, R3, R5, R8, R9, R10]
estado: pendiente
---

# EP-09 · Diagnóstico usable en la web

**Resultado esperado:** Un agricultor elige desde el celular su municipio, su cultivo y cuándo quiere sembrar, ajusta si quiere lo que más le importa, y entiende sin ayuda si el cultivo se da en su zona, cómo sale esa ventana de siembra con su criterio y con el de AgroSense, qué dice cada fuente y, si no conviene, cuáles ventanas han sido mejores o qué otros cultivos salen mejor. Todo es informativo: decide el agricultor.

Arranca contra las respuestas simuladas (HU-013) y se integra con EP-07.

**En el MVP, el resultado del diagnóstico es también la pantalla «Ciclo de una estrategia» (HU-215, EP-10):** los mismos componentes muestran cada ciclo. La web del MVP es 2D (modo ligero por defecto, HU-158). Desde el resultado se llega a «Qué cambió en su zona» (HU-219). Los cultivos alternativos (HU-197) pasaron a P1 el 11 de octubre de 2026: con «rotar», la web lleva a las estrategias de rotación.

## Historias de usuario

### HU-091 · Elegir municipio, cultivo y cuándo sembrar

- **Historia:** Como agricultor, quiero elegir municipio, cultivo y cuándo sembrar entre opciones válidas, para no equivocarme.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Buscador de municipios con autocompletado
  - [x] Solo opciones del catálogo; para el diagnóstico, solo cultivos con `kind = crop`
  - [x] «Cuándo sembrar» se elige por mes entre los próximos doce; la web envía `sowing_date`. Es el único selector de tiempo de la consulta. La semana dentro del mes llega con HU-193 (P1)
  - [x] Pregunta «¿Tiene riego?» con «Sí», «No» y «No sé» (`irrigated` verdadero, falso o nulo); con un lote, el valor sale del lote
  - [x] Validación inmediata en pantalla
- **Contrato que toca:** cuerpo de `POST /api/v1/diagnostics`
- **Notas:** En el MVP el municipio se busca en un buscador 2D; el descenso del satélite (HU-155) pasó a P1 el 11 de octubre de 2026. La web envía el día 1 del mes elegido; con semanas (P1), su lunes. El mes en curso se acepta aunque su día 1 ya haya pasado (`specs/02-contratos.md`, «Fechas» de `/calendar`).
- **Hecho (10 nov):** pantalla en `/diagnostico` (`web/src/pages/diagnosis/`), con la lógica en `web/src/features/diagnosis/consult.ts`. No va en `/consultar`, que desde la decisión 12 es la entrada a las estrategias (HU-214); se llega desde el pie de página. La consulta vive en la dirección (`?municipio=15646&cultivo=papa&siembra=2026-12&riego=no`, o `?lote=` con sesión): se puede compartir, y una dirección completa se abre ya calculada. Cada campo se valida apenas se usa (al elegir, o al salir del buscador sin escoger un municipio de la lista), sin esperar a enviar; al intentar enviar, o si la dirección trae una consulta inválida, se marcan todos. El error queda enlazado a su campo (`aria-invalid` y `aria-describedby`) y se va al corregirlo. Si el catálogo no carga, no hay formulario y se dice el motivo que da la API. Con sesión y lotes, «¿Para cuál terreno?» deja elegir un lote: el municipio y el riego salen de él y se envía `lot_id`; un lote ajeno o sin sesión no se consulta y se dice. Sin sesión no se piden los lotes. Mientras HU-092 no exista, el resultado muestra solo la acción, la luz, la ventana y el rótulo de ejemplo. El buscador (`Combobox`) ahora muestra un valor que llega de afuera cuando el catálogo termina de cargar. Los doce meses se cuentan en la hora de la región (`America/Bogota`, UTC−5), la misma con que la API valida las fechas (`specs/02-contratos.md`, «Fechas»; decidido el 10 de noviembre de 2026): el mes que ofrece la web siempre lo acepta la API, aunque el navegador esté en otra zona.

### HU-092 · Semáforo con señales, razones y limitaciones

- **Historia:** Como agricultor, quiero ver el semáforo con sus señales, razones y limitaciones, para entender el resultado.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] «Desfavorable» y «no evaluable» se distinguen con forma y texto, no solo con color
  - [x] La acción sugerida es lo primero que se lee
  - [x] Se ve la ventana evaluada: fecha de siembra y cosecha estimada, con el rótulo de cómo se estimó la cosecha según `harvest_basis`: con `calendar` (el MVP, HU-220), «Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico»; con `normal_year` (P1), «Estimación con un año normal, no es pronóstico». Corregido el 10 de noviembre de 2026: el rótulo anterior citaba un año normal que el motor del MVP no evalúa (R5)
  - [x] Las seis señales (agua, heladas, calor, suelo, oferta y mercado); «No aplica» se ve distinto de «datos insuficientes». Las señales del P1 se muestran solo si vienen en la respuesta
  - [x] La señal de agua dice si se evaluó con riego o sin riego
  - [x] La señal de oferta dice de qué año y semestre de EVA es el dato y si es preliminar
  - [x] Cada señal muestra su calificación de 0 a 100 (`score`) junto al nivel en texto; sin calificación, no se dibuja una barra en cero (R1)
  - [x] La señal que más limita la ventana (`limiting_signal`) se marca «Lo que más limita» con forma y texto
  - [x] Cuando una señal trae `sources`, se ven todas juntas, cada una con su valor, su origen y su fecha, y se marca cuál calculó la señal («Usada para la luz»); las demás llevan «Para contrastar». Nunca se muestra un valor combinado
  - [x] El suelo lleva su rango y el rótulo de estimación (R10)
- **Reglas que aplican:** R1, R5, R8, R10
- **Contrato que toca:** `signals` (con `score`, `counts` y `sources`) y `limiting_signal` de la respuesta de diagnóstico
- **Hecho (10 nov):** en `/diagnostico`, debajo de la consulta y del resumen (`web/src/pages/diagnosis/SignalList.tsx`, lógica en `web/src/features/diagnosis/signals.ts`). El resumen dice primero la acción, después la luz (forma y texto: «Desfavorable» es un cuadrado; «No evaluable», un anillo punteado) y sus razones (`overall.reasons`). Cada señal: estado con forma y texto (y «riesgo grave» solo en las que por regla pueden ser críticas), calificación con su barra (sin calificación, nada), «Lo que más limita» con un banderín, razones y, con `sources`, cada fuente con su valor, su origen (de `GET /version`, o el nombre del producto de `docs/fuentes.md` si su fila aún no está publicada), su periodo y «Usada para la luz» o «Para contrastar»; POWER dice que es un reanálisis y la humedad del suelo, que es de la zona y su resolución. Con riego, el agua lleva el rótulo de estimación del riego (R10). El suelo muestra el rango de pH del municipio (`GET /catalogs/municipalities/{id}/soil`, p05 a p95) y el rótulo de estimación; el del lote llega con HU-182. Los campos nulos que la respuesta omite se tratan como nulos (R1). Las limitaciones van al final. Pendientes de otras HU: la luz con las prioridades frente a la de AgroSense y «No cuenta para la luz» (HU-203), y no dibujar el semáforo de un cultivo no apto (HU-194).

### HU-194 · Cultivo no apto y mejores ventanas

- **Historia:** Como agricultor, quiero que la pantalla me diga cuando mi cultivo no se da en mi zona y, cuando la fecha no conviene, cuáles ventanas han sido mejores, para saber qué hacer en lugar de quedarme con un «no».
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Con `suitability.level = not_suitable`: la pantalla dice «Este cultivo no se da en su zona» y muestra la nota de aptitud de 0 a 100 (`suitability.score`), la escala de cinco semillas, la razón con el dato de la ficha y su fuente, y las alternativas cuando vienen (HU-203, P1); ofrece «Elegir otro cultivo» y «Ver estrategias de rotación» (HU-214). No dibuja semáforo, señales ni ventanas
  - [x] La nota de aptitud (`suitability.score`) se muestra con su número y en la escala de cinco semillas. Es informativa: no es una señal ni cambia la luz; solo la temperatura media anual fuera del rango absoluto da «no se da en su zona» (decisión 13; decía «la altitud», el criterio anterior)
  - [x] Sin nota (`score` nulo), no se dibujan semillas en cero (R1)
  - [x] Con `suitability.level = insufficient_data`: el resultado se muestra normal y la limitación lo dice; no se pinta como riesgo (R1)
  - [x] Con acción `other_window`: lista de `best_windows` con fecha de siembra, cosecha estimada, la nota del factor que más limita (número principal) y el promedio con sus prioridades (secundario); tocar una consulta el diagnóstico de esa fecha
  - [x] Con `other_window` y `best_windows` vacío: mensaje «En los próximos doce meses no hay una ventana sin riesgo alto» y enlace a las estrategias de rotación
  - [x] Las ventanas llevan el rótulo «Según la historia de la zona. No es un pronóstico»
  - [x] Cada botón tiene una acción o una navegación definida
- **Reglas que aplican:** R1, R3, R5
- **Contrato que toca:** `suitability` (con `score`), `alternatives` y `best_windows` de la respuesta de diagnóstico
- **Notas:** El orden completo de las ventanas, con prioridades y detalle por semanas, está en la lectura «Planear una siembra» del calendario (HU-180, P1). Los cultivos alternativos de la acción `rotate` son HU-203 (en P1, con HU-197). Agregada el 11 de octubre de 2026.
- **Hecho (10 nov):** en el resumen de `/diagnostico` (`web/src/pages/diagnosis/Suitability.tsx`, lógica en `web/src/features/diagnosis/windows.ts`). Con `not_suitable`, un letrero propio («Este cultivo no se da en su zona», con un brote tachado), sin semáforo, señales ni ventana: la nota de aptitud con su número y cinco semillas (una por cada 20 puntos), el dato con que se decidió («Temperatura media anual de 26,3 °C a 300 m de altitud, la del municipio») y las razones de `suitability.reasons`, que citan la ficha y su fuente; «Elegir otro cultivo» deja la misma consulta sin cultivo y «Ver estrategias de rotación» va a HU-214. Con un cultivo apto, la nota y sus semillas van en el resumen como dato informativo; sin nota no hay semillas (R1), y con `insufficient_data` el resultado es normal y lo dice la limitación de la API. Con `other_window` en cualquiera de las dos luces, «Mejores fechas de los próximos doce meses» con «Según la historia de la zona. No es un pronóstico»: cada una con su siembra, su cosecha, lo que más la limita (número principal) y el promedio con sus prioridades (secundario); tocar una consulta esa fecha y el formulario la muestra (el formulario sigue a la dirección cuando cambia desde afuera). Sin ventanas, «En los próximos doce meses no hay una ventana sin riesgo alto» y el enlace a las estrategias, que no se repite si la otra luz ya dice «rotar». Las alternativas (P1) quedan con HU-197. El botón del kit pasó de alto fijo a alto mínimo: «Ver estrategias de rotación» no cabía en una línea a 360 px y ahora crece a dos.

### HU-202 · Ajustar mis prioridades al consultar

- **Historia:** Como agricultor, quiero decir qué me importa más de cada señal al consultar, para que el semáforo y el orden de las ventanas reflejen mi criterio.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Seis controles, uno por señal (agua, heladas, calor, suelo, oferta y mercado), de 0 a 5, con el control de prioridad del kit (cinco semillas y un «0»)
  - [x] Empiezan en los pesos por defecto de AgroSense, tomados de `default_weights` de `GET /api/v1/version`, antes de consultar; un botón «Volver al criterio de AgroSense» los restablece
  - [x] Al cambiar uno, la web vuelve a pedir el diagnóstico con `priorities`
  - [x] Con todos en 0, la web no envía la petición y pide subir al menos uno
  - [x] Junto a los controles, un texto corto: «0: no cambia la luz, salvo un riesgo grave de clima. 4 o 5: un resultado medio cuenta como desfavorable»
  - [x] Las mismas prioridades se envían como `signal_priorities` a las estrategias de rotación (HU-214) durante la misma visita y, en P1, se usan en «Planear una siembra» (HU-180). Lo del P0 hecho el 11 de noviembre con HU-214; lo de HU-180 llega con ella
  - [x] Sin cuenta, las prioridades se guardan en el navegador; con cuenta, en el perfil (`PATCH /me`, `priorities`, de HU-160), el mismo lugar que «Sus prioridades» de Mi cuenta. Siempre se puede volver al criterio de AgroSense. Corregido el 10 de noviembre de 2026: decía «en el navegador, con o sin cuenta, hasta que exista HU-160»; HU-160 ya guarda las prioridades en el perfil y `specs/05-frontend.md` («Dónde se ajustan») ya lo decía así
  - [x] Cada control tiene una función; nada decorativo
- **Reglas que aplican:** R2, R9
- **Contrato que toca:** `priorities` del cuerpo de `POST /api/v1/diagnostics` y de `POST /api/v1/calendar`; `weights` de la respuesta; `default_weights` de `GET /api/v1/version`; `priorities` de `PATCH /api/v1/me`
- **Notas:** Decisión 10. Son distintas de las cuatro prioridades de las rotaciones (HU-101). El perfil como lugar para recordarlas depende de `PATCH /me` (HU-160), que pasó a P1 el 11 de octubre de 2026: en el MVP se recuerdan en el navegador. Los controles van en un resumen plegado, «Criterio de AgroSense · Ajustar» (`specs/05-frontend.md`, «Dónde se ajustan»).
- **Hecho (10 nov; el envío a las estrategias, el 11 nov con HU-214):** en `/diagnostico`, dentro de la consulta, el resumen plegado «Criterio de AgroSense · Ajustar» (o «Sus prioridades · Ajustar») con los seis `SeedRow` del kit; sus controles se dibujan solo abierto. La lógica está en `web/src/features/diagnosis/priorities.ts` (`useSignalPriorities`), que también usa HU-214 para enviar `signal_priorities`. La consulta espera el primer intento de `GET /version` para no pedir dos veces; si `/version` falla, consulta sin `priorities` (la API usa sus pesos) y no lo vuelve a pedir en bucle (`useVersion` con `retryOnMount: false`). Con todas en 0 no se consulta ni se guarda, y el resultado lo dice. En el celular el panel ocupa todo el ancho de la tarjeta: las seis casillas de 44 px no caben de otro modo a 320 px. «Volver al criterio de AgroSense» solo aparece cuando hay a qué volver. «Sus prioridades» de Mi cuenta usa la misma lista de señales.

### HU-203 · Dos luces y cultivos alternativos

- **Historia:** Como agricultor, quiero ver la luz con mis prioridades y la de AgroSense cuando no coinciden, y qué otros cultivos salen mejor cuando conviene cambiar, para decidir yo con toda la información.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Si `overall.light` y `overall_default.light` son iguales, se ve una sola luz
  - [x] Si difieren, se ven las dos con su acción: «Con sus prioridades: verde · Con el criterio de AgroSense: amarillo», cada una con forma y texto, no solo color. La de sus prioridades va primero
  - [x] Una señal con `counts = false` se sigue viendo, con el rótulo «No cuenta para la luz con sus prioridades»
  - [x] Un riesgo grave de clima con peso 0 lleva el rótulo «Cuenta siempre: riesgo grave»
  - [x] Con la acción `rotate` en cualquiera de las dos luces, el botón «Ver estrategias de rotación» lleva a HU-214 con el municipio, la fecha y el cultivo consultado como anterior
  - [ ] P1 (con HU-197): con `alternatives`, una lista «Otros cultivos que en esta ventana salen bien en clima y tienen mejor oferta», cada uno con su nombre y sus razones; tocar uno consulta el diagnóstico de ese cultivo en la misma fecha. Con `alternatives` vacío, el mensaje «No encontramos otro cultivo apto que salga mejor en esta ventana» y el enlace a las estrategias
  - [x] Rótulo visible: «Es información para decidir. La decisión es suya»
  - [x] Cada botón tiene una acción o una navegación definida
- **Reglas que aplican:** R1, R2, R5
- **Contrato que toca:** `overall`, `overall_default`, `weights`, `signals.*.counts` y `alternatives` de la respuesta de diagnóstico
- **Notas:** Decisión 10. Depende de HU-074 (o de su respuesta simulada). Las alternativas se muestran si cualquiera de las dos luces da `rotate`, también cuando el cultivo consultado no es apto (`specs/01-reglas.md`, «Agregación del semáforo»); su lista es P1 desde el 11 de octubre de 2026, junto con HU-197. Los mismos componentes muestran cada ciclo de una estrategia (HU-215).
- **Hecho (10 nov), la parte del P0:** en el resumen de `/diagnostico`. Con las luces iguales, una sola. Si difieren, «Con sus prioridades: <acción>» primero y más grande y «Con el criterio de AgroSense: <acción>» debajo, cada una con su luz (forma y texto), «Lo que más limita» y sus razones, y una línea que dice por qué difieren con los pesos que cambió la persona frente a los de AgroSense («Usted puso la oferta en 0 (AgroSense: 2)»), como pide `specs/05-frontend.md` («Dos luces»). En las señales, «No cuenta para la luz con sus prioridades» (`counts = false`, anillo vacío) y «Cuenta siempre: riesgo grave» (agua, heladas, calor o exceso de lluvia críticos con peso 0, rombo lleno; la oferta y el mercado no). Con `rotate` en cualquiera de las dos luces, «Ver estrategias de rotación» lleva a `/consultar?municipio=&siembra=&anterior=&riego=` (o `?lote=&siembra=&anterior=`): HU-214 los toma ya elegidos. Lógica en `web/src/features/diagnosis/lights.ts`. Las alternativas (P1) quedan con HU-197.

### HU-093 · Gráfica de la lluvia de la ventana

- **Historia:** Como agricultor, quiero ver año por año la lluvia de mi ventana frente a lo que el cultivo necesita, para ver la tendencia con mis ojos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Una gráfica de la serie `water`: lluvia de los meses de la ventana y necesidad del cultivo, por año, en mm, con unidades y periodo visibles
  - [ ] Dice de qué fuente es la lluvia (IMERG o POWER, la que calculó la señal)
  - [ ] Una serie con `insufficient_data` muestra su estado vacío, no una gráfica en cero (R1)
- **Reglas que aplican:** R1, R5, R8
- **Contrato que toca:** `GET /api/v1/trends` (serie `water`)
- **Notas:** Reducida el 11 de octubre de 2026 a una sola gráfica (recorte del MVP); pasó de M a S. La gráfica del área sembrada (serie `supply`) queda para P1; la oferta sigue en su señal. La serie `ndvi` se muestra en el ciclo de una estrategia (HU-215).

### HU-094 · Estados de carga, vacío y error

- **Historia:** Como usuario, quiero mensajes claros cuando algo carga, falla o no tiene datos, para saber qué hacer.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Estados de carga, vacío, sin cobertura y error
  - [ ] Los datos de ejemplo se rotulan

### HU-219 · Pantalla «Qué cambió en su zona»

- **Historia:** Como agricultor, quiero ver qué cambió en las heladas, la lluvia y el calor de mi zona, y cómo se movieron las mejores fechas de siembra de mi cultivo, para adaptar mi finca a condiciones que cambian.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Se llega desde el resultado del diagnóstico, desde el ciclo de una estrategia (HU-215) y desde el lote, con el municipio y el cultivo ya elegidos. El ciclo ya enlaza a `/que-cambio?municipio=&cultivo=` (`PATHS.changes`), que hoy dice que está pendiente: esta HU pone ahí la pantalla
  - [ ] Por mes, tres comparaciones (heladas, lluvia y temperatura máxima) entre los dos periodos, cada una con su unidad, los años de cada periodo y la fuente
  - [ ] Las mejores ventanas de cada periodo, lado a lado («Entre 1981 y 2000: …» · «Entre 2005 y 2024: …»)
  - [ ] Rótulo fijo y visible: «Así fue en la historia de su zona. No es un pronóstico»
  - [ ] Un valor `insufficient_data` se ve como «Sin datos suficientes» con forma y texto, nunca como un cambio de cero (R1)
  - [ ] Si la lluvia sale de IMERG, la pantalla dice que esos datos empiezan en 2000
  - [ ] Si el cultivo no es apto para la zona, lo dice con su razón y muestra solo el clima
  - [ ] Usable a 360 px; cada control tiene una función
- **Reglas que aplican:** R1, R4, R5, R8
- **Contrato que toca:** `GET /api/v1/changes`
- **Notas:** Decisión 12. Se diseña en Figma antes de programarla (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»). Depende de HU-218 o de su respuesta simulada. Agregada el 11 de octubre de 2026.

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
