---
id: EP-07
titulo: "Diagnóstico de la ventana explicable"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M1, M2, M4, M6, M7, M10]
depende_de: [HU-011, HU-012, EP-03, EP-04, HU-061, HU-063, HU-142, HU-143, HU-144, HU-150, HU-186, HU-181, HU-198, HU-199]
reglas: [R1, R2, R3, R4, R5, R6, R8, R10]
estado: pendiente
---

# EP-07 · Diagnóstico de la ventana explicable

**Resultado esperado:** Dado un municipio, un cultivo, una fecha de siembra y, si quiere, sus prioridades, el sistema dice primero si el cultivo es apto para la zona y, si lo es, responde un semáforo para esa ventana de siembra con sus seis señales calificadas de 0 a 100, razones, acción y limitaciones. Cuando las prioridades del agricultor dan otra luz que las de AgroSense, responde las dos. Cuando la acción es buscar otra ventana, trae las mejores de los próximos doce meses; cuando es rotar, sugiere cultivos alternativos. Todo es informativo: decide el agricultor.

Arranca con los datos de ejemplo de HU-011 y HU-012, y pasa a los datos reales de EP-03 y EP-04 en la integración.

La ventana va de `sowing_date` a la cosecha estimada de ese cultivo (`specs/01-reglas.md`, «La ventana de siembra»). No hay semestres en la decisión: el semestre solo se usa para leer la oferta de EVA (HU-072). Todo es historia de la zona, nunca pronóstico.

**Método (decisión 10 de `docs/decisiones.md`):** cada señal se califica de 0 a 100 con una curva por cultivo al estilo EcoCrop de la FAO (HU-196); el nivel sale de la calificación. El semáforo se decide por reglas con los pesos de quien consulta (HU-074). Las ventanas se ordenan primero por el factor que más limita y después por el promedio ponderado por las prioridades (HU-192). El riesgo grave de clima siempre cuenta.

Orden dentro de la épica: aptitud (HU-191) → calificación (HU-196) → señales (HU-071, HU-077, HU-190, HU-183 de EP-18, HU-072, HU-073) → orden de las ventanas (HU-192) → semáforo, dos luces y acción (HU-074) → alternativas (HU-197) → endpoint (HU-076). La señal de agua necesita el balance hídrico (HU-143 y HU-144) y las etapas (HU-142); la duración de la ventana sale del cálculo de etapas (HU-150 y HU-186). Por eso esas HU de EP-14 van antes.

## Historias de usuario

### HU-071 · Señal de agua

- **Historia:** Como agricultor, quiero saber si la lluvia que suele caer en mi ventana cubre lo que mi cultivo necesita, según cuánta agua retiene mi suelo y si tengo riego, para decidir si siembro.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal `water` con `status`, `level`, `critical`, `score`, `counts`, `indicators` (`water_deficit_mm`) y `reasons`, según el contrato
  - [ ] Usa el balance hídrico de M7 (HU-144) por etapa del cultivo (HU-142) sobre los meses de la ventana, con `climate_month`: no hay un segundo cálculo de agua
  - [ ] El balance tiene en cuenta cuánta agua retiene el suelo según su textura (HU-144): del lote si viene `lot_id` con polígono, si no del municipio. Prueba: la misma ventana con un suelo arenoso da un déficit mayor o igual que con uno arcilloso
  - [ ] Sin riego (`irrigated = false`): `score` sale de la curva de HU-196 y el nivel, de la calificación; grado crítico en `thresholds.yaml`
  - [ ] Con riego (`irrigated = true`): nunca es `unfavorable` ni crítica por falta de lluvia; la razón dice cuánto riego haría falta, como rango y con el rótulo de estimación (R10)
  - [ ] `irrigated` nulo se trata como sin riego y se agrega a las limitaciones
  - [ ] La razón dice siempre el periodo que se evaluó (por ejemplo, «en 7 de los últimos 10 años»): es historia, no pronóstico (R5, decisión 4)
  - [ ] Sin `climate_month` para el municipio o sin etapas con Kc para el cultivo: `insufficient_data`, nivel y `score` nulos (R1)
  - [ ] Caso de referencia: la misma ventana con déficit alto da `unfavorable` sin riego y no da `unfavorable` con riego
- **Reglas que aplican:** R1, R2, R4, R5, R6, R10
- **Contrato que toca:** `signals.water` de la respuesta de diagnóstico; `climate_month`, `crop_stages`, `soil_grid`, `soil_municipality`
- **Notas:** Reemplaza a la señal anterior, que solo miraba la lluvia frente a lo normal; cambió el 11 de octubre de 2026. El mismo día sumó la textura del suelo (decisión 10). Depende de HU-142, HU-143, HU-144 y HU-196. Supuestos por confirmar: qué nivel toma la señal con riego cuando el déficit es alto (`favorable` o `moderate`); la regla de agregación lo trata como `favorable`. Qué pasa si no hay textura del suelo: ver la nota de HU-144.

### HU-072 · Señal de oferta

- **Historia:** Como agricultor, quiero saber si en mi zona se está sembrando mucho o poco de mi cultivo, y ver qué dice cada fuente, para evitar la sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `score` según la variación del área sembrada (`planted_change_pct`), con la curva de HU-196; el nivel sale de la calificación
  - [ ] La señal se calcula con la fuente que define `sources.yaml` para la región (en la región piloto, EVA) y la respuesta dice cuál fue
  - [ ] Con EVA: lee `supply_semester` con el semestre en que cae `sowing_date` (A: enero a junio; B: julio a diciembre) y usa el último año con dato de ese semestre
  - [ ] La respuesta dice qué dato se usó en `window.supply_semester` (`year`, `semester`, `preliminary`), y la razón lo nombra y dice si es preliminar
  - [ ] Cuando hay más de una fuente para el indicador, `signals.supply.sources` las trae todas, cada una con su valor, y `used` dice cuál calculó la señal. Nunca se mezclan ni se promedian (R1, R8)
  - [ ] La oferta cambia el semáforo como cualquier otra señal (reglas 2 a 4) cuando su peso es mayor que 0
  - [ ] Con poca siembra y sin mercado, la razón dice «posible oportunidad, sin confirmar precio»
  - [ ] Sin dato de la fuente que calcula la señal para ese cultivo y municipio: `insufficient_data` (R1). Otra fuente de contraste no la reemplaza
- **Reglas que aplican:** R1, R2, R5, R7, R8
- **Contrato que toca:** `signals.supply` (con `sources`) y `window.supply_semester`; tablas `supply_semester` y `sources`
- **Notas:** Es el único punto de la decisión donde se usa el semestre, porque EVA lo publica así. EVA y el semestre A/B son supuestos de la región piloto en Colombia (decisión 11). En el P0 solo hay una fuente (EVA) y `sources` no viene; las fuentes de contraste llegan en P1 (HU-200 y HU-201). La sugerencia de cultivos con mejor oferta es HU-197.

### HU-073 · Señal de mercado sin datos

- **Historia:** Como agricultor, quiero saber cuándo no hay datos de mercado, para no confiar en una señal que no existe.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Sin datos: `insufficient_data`, nivel y `score` nulos y razón explícita
  - [ ] Con EP-05: `score` según el índice estacional (`seasonal_index`) del mes en que saldría la cosecha (`harvest_estimate`), con la curva de HU-196; nunca un precio futuro
- **Reglas que aplican:** R1, R5

### HU-196 · Calificación de las señales con curvas por cultivo

- **Historia:** Como motor, quiero calificar cada señal de 0 a 100 con una curva por cultivo, para que el nivel, el factor limitante y el orden de las ventanas salgan de la misma cuenta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Una sola función de curva: 100 dentro del rango óptimo, 0 fuera de los límites absolutos y una recta entre ambos (`specs/01-reglas.md`, «Cómo se califica cada señal»)
  - [ ] El nivel sale de la calificación con los cortes de `thresholds.yaml` (hoy 70 a 100 `favorable`, 40 a 69 `moderate`, 0 a 39 `unfavorable`)
  - [ ] Una señal es crítica cuando su calificación baja del umbral crítico de esa señal en `thresholds.yaml`; `soil` no tiene umbral crítico (R10)
  - [ ] Los límites que dependen del cultivo salen de su ficha con fuente (HU-061, HU-063, HU-199); los que no dependen del cultivo (por ejemplo, la variación del área sembrada) viven en `thresholds.yaml`
  - [ ] Sin el límite de la ficha con fuente, o sin el dato de la zona: `insufficient_data`, nivel y `score` nulos (R1, R8). Nunca se usa un límite «típico»
  - [ ] Pruebas: un valor dentro del óptimo da 100; un valor en el límite absoluto o fuera da 0; el punto medio entre el óptimo y el límite da 50; mismo valor, misma calificación (R4)
  - [ ] Es una función pura del motor: recibe el valor y los límites, no lee archivos (R6)
- **Reglas que aplican:** R1, R4, R6, R8, R10
- **Contrato que toca:** `score` y `level` de cada señal en `/diagnostics` y en las ventanas de `/calendar`; `crops`; `thresholds.yaml`
- **Notas:** Decisión 10. Reemplaza el supuesto de HU-192 sobre cómo se convierte cada señal en puntaje. Supuestos por confirmar, uno por señal: `water` califica la parte de la necesidad que cubre la lluvia en la ventana (cortes en `thresholds.yaml`, porque los límites de lluvia de EcoCrop, si son anuales, no describen una ventana); `heat` compara `tmax_p90_c` con el óptimo y el máximo de temperatura de la ficha; `frost` califica `frost_freq_pct` en las semanas sensibles (cortes en `thresholds.yaml`); `soil` usa `ph_opt_min`–`ph_opt_max` y `ph_min`–`ph_max`; `supply` y `market` usan cortes de `thresholds.yaml`, iguales para todos los cultivos. **Hueco del contrato:** `crops` no tiene el óptimo de temperatura ni los límites de lluvia (ver HU-199).

### HU-074 · Semáforo con prioridades, dos luces y acción

- **Historia:** Como agricultor, quiero un semáforo con una acción sugerida que tenga en cuenta lo que más me importa, y ver también el criterio de AgroSense cuando no coinciden, para decidir rápido y con las dos lecturas.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Implementa, en orden, las reglas 0 a 5 de «Agregación del semáforo» y la tabla de acciones de `specs/01-reglas.md`, sobre una ventana
  - [ ] Regla 0: si el cultivo no es apto para la zona (HU-191), la luz es `red`, la acción es `rotate` y no se evalúa nada más
  - [ ] Aplica las reglas dos veces: con los pesos de quien consulta (`overall`, `weights_basis = farmer`) y con los de `weights.yaml` (`overall_default`, `weights_basis = default`). Sin `priorities`, las dos son iguales y `overall.weights_basis` es `default`
  - [ ] La respuesta trae `weights` (los pesos usados en `overall`) y, por señal, `counts`: si cuenta para la luz con esos pesos
  - [ ] Peso 0: la señal se muestra con `counts = false` y no cambia la luz, salvo un riesgo grave de clima (`water`, `frost` o `heat` críticos), que siempre cuenta
  - [ ] Peso 4 o 5: un `moderate` en esa señal cuenta como `unfavorable` para la luz
  - [ ] La acción usa `other_window` y `rotate` según la tabla: en amarillo, `rotate` si `soil`, `supply` o `market` son `unfavorable`; en rojo, `other_window` si todas las desfavorables son de clima (`water`, `frost`, `heat`) y `rotate` si alguna es `soil`, `supply` o `market`
  - [ ] Con `other_window`, la respuesta trae `best_windows` (HU-192): de 0 a 3 ventanas de los próximos doce meses, ninguna de alto riesgo. En cualquier otra acción, `best_windows` no viene
  - [ ] Con `rotate` en `overall` o en `overall_default`, la respuesta trae el campo `alternatives`; lo llena HU-197, que va después de esta HU
  - [ ] `limiting_signal` es la señal con la calificación más baja entre las que cuentan (HU-192)
  - [ ] `high_risk` es verdadero cuando alguna señal que cuenta es `unfavorable` y crítica
  - [ ] Prueba: una señal desfavorable crítica nunca da verde
  - [ ] Prueba: con la oferta desfavorable y peso 0 en `supply`, `overall` puede dar verde mientras `overall_default` da amarillo
  - [ ] Prueba: una helada crítica con peso 0 en `frost` sigue dando rojo
  - [ ] Prueba: sin `water` o sin `supply`, la luz es `not_evaluable` y la acción `review_data`
  - [ ] Prueba: `frost`, `heat`, `soil` o `market` sin datos no cambian la luz y aparecen en las limitaciones; `not_applicable` tampoco la cambia
- **Reglas que aplican:** R1, R2, R3, R4, R5
- **Contrato que toca:** `overall`, `overall_default`, `weights`, `limiting_signal`, `counts`, `best_windows`, `alternatives` y `limitations` de la respuesta de diagnóstico
- **Notas:** El 11 de octubre de 2026 las señales pasaron a seis por ventana de siembra y la acción `other_window` reemplazó a la anterior (decisión 9). El mismo día entraron las prioridades del agricultor y las dos luces (decisión 10): la HU pasó de M a L. Las señales del P1 (HU-195) entran a las mismas reglas cuando existan. Supuestos por confirmar: (1) la tabla de acciones mira solo las señales que cuentan, y un `moderate` con peso 4 o 5 cuenta como `unfavorable` también para elegir la acción; (2) qué pasa con la regla 1 si el agricultor pone peso 0 en `supply` y no hay datos de oferta (la regla no lo excluye: sigue siendo `not_evaluable`); (3) con peso 0 en `water`, la regla 3 sigue pidiendo `water` `favorable` para dar verde.

### HU-197 · Cultivos alternativos con mejor oferta

- **Historia:** Como agricultor, quiero que, cuando conviene cambiar de cultivo, la app me sugiera cultivos que en esa misma ventana salen bien en clima y tienen mejor oferta, para tener por dónde empezar.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Solo se calcula cuando la acción es `rotate` en `overall` o en `overall_default`
  - [ ] Candidatos: cultivos del catálogo con `kind = crop`, distintos del consultado y con aptitud `suitable` para la zona (HU-191). Nunca uno `not_suitable`
  - [ ] Cada candidato se evalúa en su propia ventana desde la misma `sowing_date`, con el mismo cálculo de señales del diagnóstico
  - [ ] Entra solo si sale bien en clima: `water`, `frost` y `heat` sin ningún `unfavorable` ni crítico, y `water` disponible
  - [ ] Entra solo si su oferta es mejor: `supply` disponible y con calificación mayor que la del cultivo consultado
  - [ ] Hasta tres, en orden determinista (R4); cada uno con `crop_id` y razones que citan las señales evaluadas (R5)
  - [ ] Sin candidatos que cumplan, `alternatives` viene como lista vacía
  - [ ] Caso de referencia: un cultivo apto con helada crítica en esa ventana nunca aparece como alternativa, aunque su oferta sea la mejor
- **Reglas que aplican:** R1, R2, R3, R4, R5, R6
- **Contrato que toca:** `alternatives` de la respuesta de diagnóstico
- **Notas:** Decisión 10. Es una sugerencia informativa: no revisa las reglas de rotación con el historial del lote (eso es EP-08). Depende de HU-074 (la acción), HU-191, HU-196 y de las señales de clima y oferta. Supuestos por confirmar: el orden (propuesta: mayor calificación de oferta, luego mayor factor limitante, luego `crop_id`); qué hacer con un candidato de aptitud `insufficient_data` (propuesta: no entra); qué responder cuando el cultivo consultado no es apto, porque no hay oferta suya con qué comparar (propuesta: cultivos aptos que salen bien en clima, sin exigir la comparación de oferta); si la web muestra alternativas cuando solo `overall_default` es `rotate`.

### HU-077 · Señal de heladas

- **Historia:** Como agricultor, quiero saber qué tan seguido ha helado en las semanas en que mi cultivo es sensible, para no perder la siembra por una helada.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Evalúa las semanas de la ventana en que el cultivo está en una etapa con `frost_sensitive`, con `frost_freq_pct` de `climate_risk_week` (HU-193); las etapas de cada semana salen del cálculo de HU-150 y HU-186
  - [ ] `score` con la curva de HU-196; el nivel sale de la calificación
  - [ ] La razón nombra la fecha de siembra, la etapa y el mes («Sembrando en agosto, heló en el llenado (diciembre) 12 de cada 100 años»)
  - [ ] `not_applicable` si ninguna etapa es sensible; `insufficient_data` si falta `climate_risk_week` o la ficha no dice la sensibilidad con fuente
  - [ ] Grado crítico en `thresholds.yaml`. Una helada crítica cuenta siempre, aunque el agricultor le ponga peso 0
  - [ ] Caso de referencia: helada crítica con agua y oferta favorables da rojo y la acción es `other_window`
  - [ ] El bloque `frost` de «Mi cultivo» en el calendario (HU-179) sale de este mismo cálculo
- **Reglas que aplican:** R1, R2, R4, R5
- **Contrato que toca:** `signals.frost`; `climate_risk_week`, `crop_stages`
- **Notas:** Depende de HU-193 (riesgo por semana), HU-063 (etapas sensibles), HU-150 y HU-186 (etapas de la ventana) y HU-196. Ya no depende del «mejor mes» ni de HU-179: es HU-179 la que reutiliza esta señal. Cambiada el 11 de octubre de 2026.

### HU-190 · Señal de calor

- **Historia:** Como agricultor, quiero saber si en mi ventana suele hacer más calor del que mi cultivo aguanta, para no sembrar cuando el calor lo daña.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal `heat` con `status`, `level`, `critical`, `score`, `counts`, `indicators` (`tmax_p90_c`) y `reasons`, según el contrato
  - [ ] Compara `tmax_p90_c` de las semanas de la ventana (`climate_risk_week`) con los límites de temperatura de la ficha (`heat_max_c` y, cuando exista, el óptimo de HU-199) mediante la curva de HU-196
  - [ ] La razón dice el periodo, la temperatura de la zona y la que aguanta el cultivo («De agosto a diciembre, la máxima rara vez pasa de 22 °C; la papa aguanta hasta 28 °C»)
  - [ ] Grado crítico en `thresholds.yaml`. Un calor crítico cuenta siempre, aunque el agricultor le ponga peso 0
  - [ ] Sin `heat_max_c` con fuente o sin `tmax_p90_c`: `insufficient_data`, nivel y `score` nulos y a las limitaciones; no cambia la luz (R1, R8)
  - [ ] `not_applicable` cuando la ficha dice que ninguna etapa es sensible al calor
  - [ ] Caso de referencia: calor crítico con agua y oferta favorables da rojo y la acción es `other_window`
  - [ ] El bloque `heat` de «Mi cultivo» en el calendario (HU-179) sale de este mismo cálculo
- **Reglas que aplican:** R1, R2, R4, R5, R8
- **Contrato que toca:** `signals.heat`; `climate_risk_week.tmax_p90_c`, `climate_risk_month.tmax_p90_c`, `crops.heat_max_c`, `crop_stages.heat_sensitive`
- **Notas:** Depende de HU-193, HU-045, HU-061 y HU-196. Las etapas sensibles al calor salen de `crop_stages.heat_sensitive`. Agregada el 11 de octubre de 2026.

### HU-191 · Aptitud del cultivo en la zona

- **Historia:** Como agricultor, quiero saber de entrada si mi cultivo se da en mi municipio, para no planear una siembra que no va a prosperar.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Antes de evaluar señales, el motor compara `altitude_m` del municipio con `altitude_min_m`–`altitude_max_m` de la ficha
  - [ ] Fuera del rango: `suitability.level = not_suitable`, luz `red`, acción `rotate`, `window` y `signals` nulos, y la razón cita el dato de la ficha y su fuente. No se evalúa ninguna ventana
  - [ ] Dentro del rango, incluidos los dos límites: `suitable`, y la razón dice la altitud del municipio y el rango del cultivo
  - [ ] Si la ficha no tiene el rango con fuente, o el municipio no tiene `altitude_m`: `insufficient_data`; no bloquea y se agrega a las limitaciones (R1, R8)
  - [ ] Es un filtro, no una señal: no se califica ni entra al orden de las ventanas (R3)
  - [ ] El calendario (HU-179), las rotaciones (HU-081) y las alternativas (HU-197) usan esta misma función
  - [ ] Caso de referencia: un cultivo de clima frío en un municipio a nivel del mar da `not_suitable` sin ventanas
- **Reglas que aplican:** R1, R3, R4, R5, R8
- **Contrato que toca:** `suitability` en las respuestas de `/diagnostics` y `/calendar`; `crops.altitude_min_m`, `crops.altitude_max_m`, `municipalities.altitude_m`
- **Notas:** Depende de HU-044 (altitud del municipio) y HU-061 (rango de altitud con fuente). Agregada el 11 de octubre de 2026.

### HU-192 · Orden de las ventanas por factor limitante y prioridades

- **Historia:** Como agricultor, quiero comparar las ventanas de siembra de los próximos doce meses según lo que más me importa, sin que un factor muy malo quede escondido detrás de un buen promedio, para elegir cuándo sembrar sabiendo qué gano y qué sacrifico.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Genera doce ventanas, una por mes de siembra (`granularity = month`), o las semanas de un mes (`granularity = week`), cada una con `sowing_start`, `harvest_estimate` y las mismas señales del diagnóstico, cada una con su `score` (HU-196)
  - [ ] Una señal sin datos o que no aplica tiene `score` nulo, no califica, sale del orden y va a las limitaciones (R1)
  - [ ] **Primero el factor que más limita:** cada ventana vale lo que vale su señal con la calificación más baja entre las que cuentan (ley del mínimo). Una ventana con un factor muy malo nunca queda arriba, por altos que sean los demás
  - [ ] **Después, las prioridades:** entre ventanas cuyo factor limitante cae en la misma decena, ordena `weighted_score`, el promedio de las calificaciones ponderado por los pesos (un entero de 0 a 5 por señal: `water`, `frost`, `heat`, `soil`, `supply`, `market`). Sin `priorities`, usa los pesos por defecto de `weights.yaml` (HU-198)
  - [ ] Una ventana con alguna señal que cuenta `unfavorable` y crítica lleva `high_risk = true`: va después de todas las demás y nunca entra en `best_windows` (R2)
  - [ ] En empate gana la ventana más temprana (R4); `rank` refleja el orden final
  - [ ] Cada ventana dice cuál es su factor limitante
  - [ ] `best_windows` trae de 0 a 3 ventanas, las primeras del orden que no son de alto riesgo; puede venir vacío
  - [ ] Prueba: una ventana del orden y el diagnóstico de esa misma fecha dan las mismas señales y calificaciones
  - [ ] La fecha desde la que se cuentan los doce meses entra al motor como parámetro: el motor no lee el reloj (R4, R6)
  - [ ] Caso de referencia: una ventana de alto riesgo con el balance más alto no queda primera ni entra en `best_windows`
  - [ ] Caso de referencia: una ventana con una señal en 15 y el promedio más alto queda detrás de una con todas sus señales en 60 o más
- **Reglas que aplican:** R1, R2, R4, R5, R6
- **Contrato que toca:** `windows` y `best_windows` de `/calendar`; `best_windows` y `limiting_signal` de `/diagnostics`
- **Notas:** Método de la FAO para aptitud de cultivos (decisión 10). El orden sirve para comparar ventanas; no decide el semáforo (R2). Es historia de la zona, no un pronóstico. Depende de las señales (HU-071, HU-077, HU-190, HU-183, HU-072, HU-073), de HU-191 y de HU-196. **Hueco del contrato:** las ventanas de `/calendar` no tienen un campo para el factor limitante ni dicen qué pesos se usaron. Supuestos por confirmar: cómo se agrupan las ventanas «parecidas», porque comparar de a pares «dentro de 10 puntos» no es transitivo (propuesta: ordenar por el factor limitante redondeado hacia abajo a la decena y, dentro de la misma decena, por `balance`); qué vale `balance` si ninguna señal califica. Agregada el 11 de octubre de 2026 y cambiada el mismo día al método de factor limitante.

### HU-075 · Umbrales y pesos versionados

- **Historia:** Como equipo, quiero umbrales y pesos versionados en configuración, para ajustarlos sin tocar código y explicar qué versión se usó.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Archivos YAML con número de versión
  - [ ] `thresholds.yaml` fija los cortes de calificación a nivel (70 y 40), el umbral crítico de cada señal y los límites de las curvas que no dependen del cultivo (HU-196); la señal de suelo no tiene umbral crítico (R10)
  - [ ] `weights.yaml` fija el peso por defecto de 0 a 5 de cada señal del P0; su contenido y su porqué salen de HU-198
  - [ ] El motor recibe la configuración ya leída: no abre los archivos (R6)
  - [ ] Si falta una señal en `weights.yaml` o un peso está fuera de 0 a 5, la API no arranca y dice por qué
  - [ ] La respuesta incluye la versión del dataset y de las reglas, y los pesos usados (`weights`)
- **Reglas que aplican:** R4, R6, R10

### HU-076 · Endpoint de diagnóstico con errores claros

- **Historia:** Como desarrollador web, quiero el endpoint de diagnóstico con errores claros, para distinguir una entrada inválida de una sin datos y de un cultivo que no es apto.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /api/v1/diagnostics` recibe `municipality_id`, `crop_id`, `sowing_date`, `irrigated`, `priorities` y `lot_id`, según el contrato
  - [ ] 422 para entradas fuera del catálogo, un cultivo con `kind` distinto de `crop`, un `sowing_date` con formato inválido, o `priorities` con un peso fuera de 0 a 5 o todos en 0
  - [ ] Sin `priorities`, usa los pesos por defecto y `overall` coincide con `overall_default`
  - [ ] 200 con `insufficient_data` para entradas válidas sin datos
  - [ ] 200 con `suitability.level = not_suitable`, luz `red` y acción `rotate` para un cultivo que no es apto; no es un error
  - [ ] Con `lot_id`, el suelo y `irrigated` se toman del lote; 401 con `lot_id` y sin sesión; 404 con un lote ajeno
  - [ ] No guarda nada, tampoco las prioridades (R9)
- **Reglas que aplican:** R1, R3, R4, R9
- **Contrato que toca:** `POST /api/v1/diagnostics` y la tabla de errores

### HU-078 · Endpoints de catálogo y tendencias

- **Historia:** Como desarrollador web, quiero los endpoints de municipios, cultivos, límites, suelo del municipio y tendencias, para armar la consulta y las gráficas.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /catalogs/municipalities`, `/catalogs/crops`, `/catalogs/municipalities/{id}/boundary`, `/catalogs/municipalities/{id}/soil` y `/trends` según el contrato
  - [ ] `/trends` recibe `sowing_date` y devuelve dos series: `water` (por año, `precip_mm` de los meses de la ventana y `need_mm` del cultivo) y `supply` (por año, `planted_ha` y `preliminary` del semestre de EVA en que cae la fecha)
  - [ ] Solo leen el dataset publicado; sin datos, la serie viene vacía con `insufficient_data` (R1)
- **Reglas que aplican:** R1, R4, R7

### HU-195 · Señales de exceso de lluvia, enfermedad y cosecha

- **Historia:** Como agricultor, quiero saber si en mi ventana suelen caer aguaceros, darse semanas favorables a una enfermedad o faltar días secos para cosechar, para completar el cuadro de riesgos.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señales `excess_rain`, `disease` y `harvest_weather` con la misma forma que las del P0 (con `score` de HU-196 y `counts`), desde `heavy_rain_days_mean`, `blight_days_mean` y `dry_window_freq_pct` (HU-046)
  - [ ] `excess_rain` puede ser crítica; `disease` y `harvest_weather` no
  - [ ] `disease` solo existe para un cultivo con una regla publicada y con fuente (por ejemplo, la gota de la papa); no cubre plagas en general
  - [ ] Una señal que todavía no existe no aparece en la respuesta: no se devuelve vacía ni inventada (R5)
  - [ ] Sin datos nunca cambian la luz (regla 5 del semáforo)
- **Reglas que aplican:** R1, R2, R5, R8
- **Contrato que toca:** `signals` de la respuesta de diagnóstico y de las ventanas de `/calendar`
- **Notas:** Depende de HU-046. Umbrales por confirmar con fuente. Supuestos por confirmar: si estas señales entran a `priorities` y a `weights.yaml` (el contrato solo lista las seis del P0), y si `excess_rain` crítico cuenta como riesgo grave de clima con peso 0 (la regla solo nombra `water`, `frost` y `heat`). Agregada el 11 de octubre de 2026.
