---
id: EP-07
titulo: "Diagnóstico de la ventana explicable"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M1, M2, M4, M6, M7, M10, M11]
depende_de: [HU-011, HU-012, EP-03, EP-04, HU-061, HU-063, HU-142, HU-143, HU-144, HU-220, HU-181, HU-198, HU-199, HU-206, HU-207, HU-216]
reglas: [R1, R2, R3, R4, R5, R6, R8, R9, R10]
estado: en curso
---

# EP-07 · Diagnóstico de la ventana explicable

**Resultado esperado:** Dado un municipio (o un lote), un cultivo, una fecha de siembra y, si quiere, sus prioridades, el sistema dice primero si el cultivo es apto para la zona y, si lo es, responde un semáforo para esa ventana de siembra con sus seis señales calificadas de 0 a 100, razones, acción y limitaciones. Cuando las prioridades del agricultor dan otra luz que las de AgroSense, responde las dos. Cuando la acción es buscar otra ventana, trae las mejores de los próximos doce meses. Además, para un municipio y un cultivo, dice qué cambió entre dos periodos de la historia de la zona. Todo es informativo: decide el agricultor.

**En el MVP el diagnóstico es la revisión de cada ciclo de una estrategia de rotación** (decisión 12, EP-08): el mismo cálculo evalúa cada ciclo, y sigue disponible como consulta suelta. Las ventanas se comparan por mes; la comparación por semana (HU-193) y los cultivos alternativos (HU-197) pasaron a P1 el 11 de octubre de 2026.

Arranca con los datos de ejemplo de HU-011 y HU-012, y pasa a los datos reales de EP-03 y EP-04 en la integración.

La ventana va de `sowing_date` a la cosecha estimada de ese cultivo (`specs/01-reglas.md`, «La ventana de siembra»). No hay semestres en la decisión: el semestre solo se usa para leer la oferta de EVA (HU-072). Todo es historia de la zona, nunca pronóstico.

**Método (decisión 10 de `docs/decisiones.md`):** cada señal se califica de 0 a 100 con una curva por cultivo al estilo EcoCrop de la FAO (HU-196); el nivel sale de la calificación. El semáforo se decide por reglas con los pesos de quien consulta (HU-074). Las ventanas se ordenan primero por el factor que más limita y después por el promedio ponderado por las prioridades (HU-192). El riesgo grave de clima siempre cuenta.

Orden dentro de la épica: aptitud (HU-191) → calificación (HU-196) → señales (HU-071, HU-077, HU-190, HU-183 de EP-18, HU-072, HU-073) → orden de las ventanas (HU-192) → semáforo, dos luces y acción (HU-074) → endpoint (HU-076) → qué cambió (HU-217, HU-218). La señal de agua necesita el balance hídrico (HU-143 y HU-144) y las etapas (HU-142); la duración de la ventana sale de las etapas por calendario (HU-220). Por eso esas HU de EP-14 van antes. En P1: alternativas (HU-197) y etapas por temperatura acumulada (HU-150, HU-186).

## Historias de usuario

### HU-071 · Señal de agua

- **Historia:** Como agricultor, quiero saber si la lluvia que suele caer en mi ventana cubre lo que mi cultivo necesita, según cuánta agua retiene mi suelo y si tengo riego, para decidir si siembro.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal `water` con `status`, `level`, `critical`, `score`, `counts`, `indicators` (`water_deficit_mm`) y `reasons`, según el contrato
  - [ ] Usa el balance hídrico de M7 (HU-144) por etapa del cultivo (HU-142) sobre los meses de la ventana: no hay un segundo cálculo de agua
  - [ ] La lluvia sale de la fuente que define `sources.yaml` para la región: GPM IMERG (`precip_month`, HU-207) cuando la región la tiene y NASA POWER (`climate_month`) si no. La ET0 sale siempre de `climate_month` (HU-143). La razón dice qué fuente de lluvia se usó
  - [ ] La lluvia que se compara con lo que pide el cultivo es la del **año seco** de la fuente (`precip_dry_mm`, el percentil 20 de su periodo normal: la que se supera en 4 de cada 5 años), no la normal. La razón lo dice («en un año seco, de los que llueve menos que en 4 de cada 5») y `signals.water.sources` muestra también la normal. Decidido por Felipe el 11 de noviembre de 2026: las dos fuentes de la NASA dan casi el doble de lluvia en los valles del altiplano, donde están los cultivos (259 estaciones del IDEAM; IMERG 1,85 veces, POWER 1,80; PR #44), y con la normal el agua saldría verde donde falta
  - [ ] Si `sources.yaml` trae `rain_caveat` para la región, la señal lo lleva en sus limitaciones en cada respuesta, y la web lo muestra junto al agua. Hoy, en la región piloto, la lluvia es la de GPM IMERG, que la sobrestima en los valles del altiplano (HU-207; decidido por Felipe el 11 de noviembre de 2026, PR #44)
  - [ ] `signals.water.sources` trae juntas la lluvia de IMERG y la de POWER, cada una con su valor y su periodo, y `used` marca la que calculó la señal; nunca se promedian ni una rellena a la otra (decisión 11). Si la fuente que calcula la señal no tiene dato para el municipio, la señal es `insufficient_data` aunque la otra tenga (R1)
  - [ ] `signals.water.sources` trae también, para contrastar y con `used = false`, la humedad del suelo de la zona: la modelada por POWER (`soil_wetness_root`, HU-205) y, si existe, la de SMAP (`sm_rootzone_m3_m3`, HU-210), cada una en su unidad. No cambian la calificación
  - [ ] El balance tiene en cuenta cuánta agua retiene el suelo según su textura (HU-144): del lote si viene `lot_id` con polígono, si no del municipio. Prueba: la misma ventana con un suelo arenoso da un déficit mayor o igual que con uno arcilloso
  - [ ] Sin riego (`irrigated = false`): `score` sale de la curva de HU-196 y el nivel, de la calificación; grado crítico en `thresholds.yaml`
  - [ ] Con riego (`irrigated = true`): el nivel es `favorable`; nunca es `unfavorable` ni crítica por falta de lluvia; la razón dice cuánto riego haría falta, como rango y con el rótulo de estimación (R10)
  - [ ] `irrigated` nulo se trata como sin riego y se agrega a las limitaciones
  - [ ] Sin la textura del suelo, el balance se calcula sin retención y se agrega a las limitaciones; la señal no queda en `insufficient_data` por eso
  - [ ] La razón dice siempre el periodo que se evaluó (por ejemplo, «en 7 de los últimos 10 años»): es historia, no pronóstico (R5, decisión 4)
  - [ ] Sin `climate_month` para el municipio o sin etapas con Kc para el cultivo: `insufficient_data`, nivel y `score` nulos (R1). El Kc de la etapa de desarrollo va nulo en la ficha a propósito: se interpola en línea recta entre el de la inicial y el de la media (FAO-56, como dice el contrato en `crop_stages`), y no cuenta como un Kc que falta
  - [ ] Caso de referencia: la misma ventana con déficit alto da `unfavorable` sin riego y no da `unfavorable` con riego
- **Reglas que aplican:** R1, R2, R4, R5, R6, R10
- **Contrato que toca:** `signals.water` (con `sources`) de la respuesta de diagnóstico; `climate_month`, `precip_month`, `soil_moisture_month`, `crop_stages`, `grid_cells`, `soil_municipality`
- **Notas:** Reemplaza a la señal anterior, que solo miraba la lluvia frente a lo normal; cambió el 11 de octubre de 2026. El mismo día sumó la textura del suelo (decisión 10) y, después, la lluvia de IMERG y la humedad del suelo como contraste (decisión 12). Que la humedad del suelo entre a la calificación necesita una regla con fuente: queda por decidir. Depende de HU-142, HU-143, HU-144 y HU-196. Con riego, `water` es `favorable` aunque el déficit sea alto, y la razón dice cuánto riego haría falta (`specs/01-reglas.md`, «Agregación del semáforo»). Sin la textura del suelo, el agua se calcula sin retención y se agrega a las limitaciones (`specs/01-reglas.md`, «Cómo se califica cada señal»).

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
- **Notas:** Desde el 11 de octubre de 2026 la oferta es valor agregado, no protagonista (decisión 12): sigue siendo una de las seis señales, con su peso y estas reglas; en las estrategias entra solo por el criterio de ingreso y nunca excluye una estrategia (HU-081, HU-082). Es el único punto de la decisión donde se usa el semestre, porque EVA lo publica así. EVA y el semestre A/B son supuestos de la región piloto en Colombia (decisión 11). En el P0 solo hay una fuente (EVA) y `sources` no viene; las fuentes de contraste llegan en P1 (HU-200 y HU-201). La sugerencia de cultivos con mejor oferta es HU-197.

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
  - [ ] Los límites que dependen del cultivo salen de su ficha con fuente (HU-061, HU-063, HU-199); los que no dependen del cultivo (por ejemplo, el porcentaje de la necesidad de agua que cubre la lluvia o la variación del área sembrada) viven en `thresholds.yaml`
  - [ ] Sin el límite de la ficha con fuente, o sin el dato de la zona: `insufficient_data`, nivel y `score` nulos (R1, R8). Nunca se usa un límite «típico»
  - [ ] Pruebas: un valor dentro del óptimo da 100; un valor en el límite absoluto o fuera da 0; el punto medio entre el óptimo y el límite da 50; mismo valor, misma calificación (R4)
  - [ ] Es una función pura del motor: recibe el valor y los límites, no lee archivos (R6)
- **Reglas que aplican:** R1, R4, R6, R8, R10
- **Contrato que toca:** `score` y `level` de cada señal en `/diagnostics` y en las ventanas de `/calendar`; `crops`; `thresholds.yaml`
- **Notas:** Decisión 10. Reemplaza el supuesto de HU-192 sobre cómo se convierte cada señal en puntaje. Qué mide cada curva (`specs/01-reglas.md`, «Cómo se califica cada señal»): `water` califica el porcentaje de la necesidad que cubre la lluvia en la ventana, con cortes en `thresholds.yaml` (los `rain_*` de la ficha son la lluvia anual que pide el cultivo: sirven de referencia y de contraste, no entran a la curva de una ventana); `heat` compara `tmax_p90_c` con el óptimo y el máximo de temperatura de la ficha (`temp_*`, `heat_max_c`); `frost` califica el porcentaje de años con helada en los meses sensibles de la ventana (semanas en P1; cortes en `thresholds.yaml`); `soil` usa `ph_opt_min`–`ph_opt_max` y `ph_min`–`ph_max`; `supply` y `market` usan cortes de `thresholds.yaml`, iguales para todos los cultivos. Las columnas de `crops` para estos límites ya están en el contrato (`specs/02-contratos.md`, tabla `crops`); las llena HU-199.

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
  - [ ] Con `other_window`, en `overall` o en `overall_default`, la respuesta trae `best_windows` (HU-192): de 0 a 3 ventanas de los próximos doce meses, ninguna de alto riesgo. Si ninguna de las dos acciones es `other_window`, `best_windows` no viene
  - [ ] Con `rotate` en `overall` o en `overall_default`, la respuesta trae el campo `alternatives` solo cuando exista HU-197 (P1); en el MVP no viene y la web lleva a las estrategias de rotación (HU-214)
  - [ ] `limiting_signal` es la señal con la calificación más baja entre las que cuentan (HU-192)
  - [ ] `high_risk` es verdadero cuando alguna señal que cuenta es `unfavorable` y crítica
  - [ ] Prueba: una señal desfavorable crítica nunca da verde
  - [ ] Prueba: con la oferta desfavorable y peso 0 en `supply`, `overall` puede dar verde mientras `overall_default` da amarillo
  - [ ] Prueba: una helada crítica con peso 0 en `frost` sigue dando rojo
  - [ ] Prueba: si `water` cuenta y no está disponible, la luz es `not_evaluable` y la acción `review_data`; con peso 0 en el agua, la luz no queda en `not_evaluable`
  - [ ] Prueba: sin datos de `supply`, la luz y el orden de las ventanas salen igual que con peso 0 en la oferta, y la limitación lo dice
  - [ ] Prueba: con peso 0 en `water` y sin que sea crítica, la regla 3 no exige `water` `favorable`: la luz es `green` si ninguna señal que cuenta es `unfavorable`
  - [ ] Prueba: `frost`, `heat`, `soil` o `market` sin datos no cambian la luz y aparecen en las limitaciones; `not_applicable` tampoco la cambia
- **Reglas que aplican:** R1, R2, R3, R4, R5
- **Contrato que toca:** `overall`, `overall_default`, `weights`, `limiting_signal`, `counts`, `best_windows`, `alternatives` y `limitations` de la respuesta de diagnóstico
- **Notas:** El 11 de octubre de 2026 las señales pasaron a seis por ventana de siembra y la acción `other_window` reemplazó a la anterior (decisión 9). El mismo día entraron las prioridades del agricultor y las dos luces (decisión 10): la HU pasó de M a L. Las señales del P1 (HU-195) entran a las mismas reglas cuando existan. Los casos con peso 0 siguen `specs/01-reglas.md` («Agregación del semáforo»): las reglas 1 y 3 solo miran `water` y `supply` cuando cuentan, y la tabla de acciones mira solo las señales que cuentan con los pesos de esa luz.

### HU-197 · Cultivos alternativos con mejor oferta

- **Historia:** Como agricultor, quiero que, cuando conviene cambiar de cultivo, la app me sugiera cultivos que en esa misma ventana salen bien en clima y tienen mejor oferta, para tener por dónde empezar.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Se calcula cuando la acción es `rotate` en `overall` o en `overall_default` (cualquiera de las dos luces), también cuando el cultivo consultado no es apto
  - [ ] Candidatos: cultivos del catálogo con `kind = crop`, distintos del consultado y que no sean `not_suitable` para la zona (HU-191). Uno con aptitud `insufficient_data` puede aparecer, con esa limitación; uno no apto, nunca
  - [ ] Cada candidato se evalúa en su propia ventana desde la misma `sowing_date`, con el mismo cálculo de señales del diagnóstico
  - [ ] Entra solo si sale bien en clima: `water`, `frost` y `heat` sin ningún `unfavorable` ni crítico, y `water` disponible
  - [ ] Entra solo si su oferta es mejor: `supply` disponible y con calificación mayor que la del cultivo consultado (con el cultivo consultado no apto, ver la nota)
  - [ ] Hasta tres, ordenados igual que las ventanas: primero el factor que más limita y después las prioridades (HU-192), en orden determinista (R4); cada uno con `crop_id` y razones que citan las señales evaluadas (R5)
  - [ ] Sin candidatos que cumplan, `alternatives` viene como lista vacía
  - [ ] Caso de referencia: un cultivo apto con helada crítica en esa ventana nunca aparece como alternativa, aunque su oferta sea la mejor
- **Reglas que aplican:** R1, R2, R3, R4, R5, R6
- **Contrato que toca:** `alternatives` de la respuesta de diagnóstico
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP, cuando conviene rotar, la web lleva a las estrategias de rotación (EP-08, EP-10), que ya proponen otros cultivos con las reglas y el historial. Decisión 10. Es una sugerencia informativa: no revisa las reglas de rotación con el historial del lote (eso es EP-08). Depende de HU-074 (la acción), HU-191, HU-196 y de las señales de clima y oferta. El orden, los candidatos con aptitud `insufficient_data` y cuándo se muestran están en `specs/01-reglas.md` («Agregación del semáforo»). Único punto abierto: con el cultivo consultado no apto no hay oferta suya con qué comparar: por definir qué significa "mejor oferta" en ese caso.

### HU-077 · Señal de heladas

- **Historia:** Como agricultor, quiero saber qué tan seguido ha helado en las semanas en que mi cultivo es sensible, para no perder la siembra por una helada.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Evalúa los meses de la ventana en que el cultivo está en una etapa con `frost_sensitive`: el porcentaje de años con al menos una helada en cualquiera de esos meses, contado con `climate_frost_month` (HU-045; método en el contrato, «Heladas de una ventana»); las etapas de cada mes salen de las etapas por calendario (HU-220). Cuando existan `climate_risk_week` (HU-193, P1) y las etapas por temperatura acumulada (HU-150, P1), evalúa por semana
  - [ ] `score` con la curva de HU-196; el nivel sale de la calificación
  - [ ] La razón nombra la fecha de siembra, la etapa y el mes («Sembrando en agosto, heló en el llenado (diciembre) 12 de cada 100 años»)
  - [ ] `not_applicable` si ninguna etapa es sensible; `insufficient_data` si falta `climate_risk_month` o la ficha no dice la sensibilidad con fuente
  - [ ] Grado crítico en `thresholds.yaml`. Una helada crítica cuenta siempre, aunque el agricultor le ponga peso 0
  - [ ] Caso de referencia: helada crítica con agua y oferta favorables da rojo y la acción es `other_window`
  - [ ] Cuando exista «Mi cultivo» en el calendario (HU-179, P1), su bloque `frost` sale de este mismo cálculo
- **Reglas que aplican:** R1, R2, R4, R5
- **Contrato que toca:** `signals.frost`; `climate_risk_month` (y `climate_risk_week` en P1), `crop_stages`
- **Notas:** Depende de HU-045 (riesgo por mes), HU-063 (etapas sensibles), HU-220 (etapas de la ventana) y HU-196. Ya no depende del «mejor mes» ni de HU-179: es HU-179 la que reutiliza esta señal. Cambiada el 11 de octubre de 2026 y, el mismo día, pasada a meses en el MVP (decisión 12). **10 de noviembre de 2026 (HU-075):** los cortes de `thresholds.yaml` vienen del ZARC de Brasil, que cuenta el % de **años** con pérdida. Lo comparable es el % de años con al menos una helada en **cualquiera** de los meses sensibles de la ventana, no el promedio de los meses. Como `climate_risk_month` trae la frecuencia de cada mes por separado y con ella no se puede contar esa unión, se agregó `climate_frost_month` con los días con helada de cada mes de cada año (aprobado por Felipe el 10 de noviembre de 2026); el método está en el contrato («Heladas de una ventana»).

### HU-190 · Señal de calor

- **Historia:** Como agricultor, quiero saber si en mi ventana suele hacer más calor del que mi cultivo aguanta, para no sembrar cuando el calor lo daña.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal `heat` con `status`, `level`, `critical`, `score`, `counts`, `indicators` (`tmax_p90_c`) y `reasons`, según el contrato
  - [ ] Compara `tmax_p90_c` de los meses de la ventana (`climate_risk_month`; por semana con `climate_risk_week` cuando exista, P1) con los límites de temperatura de la ficha (`heat_max_c` y el óptimo, `temp_opt_min_c`–`temp_opt_max_c`, de HU-199) mediante la curva de HU-196
  - [ ] La razón dice el periodo, la temperatura de la zona y la que aguanta el cultivo («De agosto a diciembre, la máxima rara vez pasa de 22 °C; la papa aguanta hasta 28 °C»)
  - [ ] Grado crítico en `thresholds.yaml`. Un calor crítico cuenta siempre, aunque el agricultor le ponga peso 0
  - [ ] Sin `heat_max_c` con fuente o sin `tmax_p90_c`: `insufficient_data`, nivel y `score` nulos y a las limitaciones; no cambia la luz (R1, R8)
  - [ ] `not_applicable` cuando la ficha dice que ninguna etapa es sensible al calor
  - [ ] Caso de referencia: calor crítico con agua y oferta favorables da rojo y la acción es `other_window`
  - [ ] Cuando exista «Mi cultivo» en el calendario (HU-179, P1), su bloque `heat` sale de este mismo cálculo
- **Reglas que aplican:** R1, R2, R4, R5, R8
- **Contrato que toca:** `signals.heat`; `climate_risk_month.tmax_p90_c` (y `climate_risk_week.tmax_p90_c` en P1), `crops.heat_max_c`, `crop_stages.heat_sensitive`
- **Notas:** Depende de HU-045, HU-061, HU-220 y HU-196; de HU-193 solo en P1. Las etapas sensibles al calor salen de `crop_stages.heat_sensitive`. Agregada el 11 de octubre de 2026.

### HU-191 · Aptitud del cultivo en la zona

- **Historia:** Como agricultor, quiero saber de entrada si mi cultivo se da en mi municipio, para no planear una siembra que no va a prosperar.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Antes de evaluar señales, el motor compara la temperatura media anual con `tmean_min_c`–`tmean_max_c` de la ficha: la del municipio (`tmean_annual_c`) o, si viene `lot_id` con polígono, corregida a la altitud del lote (mediana de `grid_cells` en su polígono, que calcula la API, HU-206) con el gradiente de HU-044. La razón dice cuál se usó, con la temperatura y la altitud
  - [x] Fuera del rango: `suitability.level = not_suitable`, luz `red`, acción `rotate`, `window` y `signals` nulos, y la razón cita el dato de la ficha (el límite que se cruzó); la fuente va en `source_ids` del cultivo. No se evalúa ninguna ventana
  - [ ] Dentro del rango, incluidos los dos límites: `suitable`, y la razón dice la temperatura media de la zona y el rango del cultivo
  - [ ] Si la ficha no tiene el rango con fuente, o el municipio no tiene `tmean_annual_c`: `insufficient_data`; no bloquea y se agrega a las limitaciones (R1, R8)
  - [x] Es un filtro: no es una señal ni entra al orden; trae un `score` informativo (R3)
  - [x] `suitability.score`: nota informativa de 0 a 100 con la curva de temperatura media (la función de HU-196): 100 dentro del rango óptimo (`tmean_opt_min_c`–`tmean_opt_max_c`) y 0 fuera del absoluto. No entra al semáforo ni al orden de las ventanas
  - [x] La aptitud se decide solo por la temperatura media anual: solo fuera del rango absoluto es `not_suitable`; una nota baja dentro del rango sigue siendo `suitable`
  - [ ] Las estrategias de rotación (HU-081, HU-213), «Qué cambió» (HU-217) y, en P1, el calendario (HU-179) y las alternativas (HU-197) usan esta misma función
  - [x] Caso de referencia: un cultivo de clima frío en un municipio a nivel del mar da `not_suitable` sin ventanas
- **Reglas que aplican:** R1, R3, R4, R5, R6, R8
- **Contrato que toca:** `suitability` (con `score`) en las respuestas de `/diagnostics`, `/rotations` y `/changes`; `crops.tmean_min_c`, `crops.tmean_max_c`, `crops.tmean_opt_min_c`, `crops.tmean_opt_max_c`, `municipalities.tmean_annual_c`, `municipalities.altitude_m`, `grid_cells`
- **Notas:** Depende de HU-044 y HU-206 (temperatura media corregida por altitud con NASADEM, del municipio y del lote), HU-061 (rango de temperatura media con fuente) y HU-199 (rango óptimo, para la nota). Cambiada el 16 de octubre de 2026 (decisión 13): antes se decidía por la altitud. El motor recibe la altitud ya calculada: no lee `grid_cells` (R6). Agregada el 11 de octubre de 2026; la altitud del lote se sumó el mismo día (decisión 12). **En curso desde el 12 de noviembre de 2026:** motor (`backend/engine/suitability.py`) y el caso `not_suitable` de `/diagnostics` implementados. **13 de noviembre de 2026, primer criterio hecho (tamaño de S a M):** la API calcula la altitud del lote (mediana de las celdas de `grid_cells` cuyo centro cae dentro de su polígono; un lote más chico que una celda usa la celda de su centro) y corrige la temperatura del municipio con el gradiente del manifiesto (`region.temperature_lapse_rate`, ahora publicado: dataset 2026.11.12). `zone_temperature` (`backend/api/lot_terrain.py`) es la única que decide qué temperatura entra a la aptitud; la razón dice la temperatura y la altitud usadas, también con municipio. Un lote sin contorno usa el municipio y lo dice en las limitaciones; un lote con contorno sin altitud usable (celdas sin dato, dataset sin `grid_cells` o sin gradiente) da `insufficient_data`, no la temperatura del municipio (R1). Un lote de otro municipio que el de la consulta responde `422` `invalid_input`. Falta la razón y las limitaciones del caso `suitable`/`insufficient_data` (esperan las señales, todavía en 501) y el cableado en `/rotations` y `/changes`.

### HU-192 · Orden de las ventanas por factor limitante y prioridades

- **Historia:** Como agricultor, quiero comparar las ventanas de siembra de los próximos doce meses según lo que más me importa, sin que un factor muy malo quede escondido detrás de un buen promedio, para elegir cuándo sembrar sabiendo qué gano y qué sacrifico.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Genera doce ventanas, una por mes de siembra (`granularity = month`); las semanas de un mes (`granularity = week`) llegan con HU-193 (P1). Cada una con `sowing_start`, `harvest_estimate` y las mismas señales del diagnóstico, cada una con su `score` (HU-196)
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
- **Contrato que toca:** `best_windows` y `limiting_signal` de `/diagnostics`; `best_windows` de `/changes`; `windows` y `best_windows` de `/calendar` (P1)
- **Notas:** En el MVP este orden sirve a `best_windows` del diagnóstico y a «Qué cambió» (HU-217); la vista que muestra las doce ventanas (HU-179, HU-180) pasó a P1 el 11 de octubre de 2026. Método de la FAO para aptitud de cultivos (decisión 10). El orden sirve para comparar ventanas; no decide el semáforo (R2). Es historia de la zona, no un pronóstico. Depende de las señales (HU-071, HU-077, HU-190, HU-183, HU-072, HU-073), de HU-191 y de HU-196. Las ventanas de `/calendar` ya traen el factor limitante (`limiting_signal`, `limiting_score`) y `weighted_score`, y la respuesta dice los pesos (`weights`, `weights_basis`) (`specs/02-contratos.md`). Ventanas «parecidas» son las que tienen el factor limitante en la misma decena; dentro de la decena ordena `weighted_score` (`specs/01-reglas.md`, «Orden de las ventanas»). Supuesto por confirmar: qué vale `weighted_score` si ninguna señal califica. Agregada el 11 de octubre de 2026 y cambiada el mismo día al método de factor limitante.

### HU-075 · Umbrales y pesos versionados

- **Historia:** Como equipo, quiero umbrales y pesos versionados en configuración, para ajustarlos sin tocar código y explicar qué versión se usó.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Archivos YAML con número de versión
  - [x] `thresholds.yaml` con la forma del contrato («Configuración versionada»): los cortes de nivel (70 y 40) y, por señal, `variable`, `unit`, `curve` (puntos o `crop`), `critical_below` y `source_id`; la señal de suelo no tiene umbral crítico (R10). Versión 1.0.0, decidido por Felipe el 10 de noviembre de 2026
  - [x] `weights.yaml` fija el peso por defecto de 0 a 5 de cada señal del P0; su contenido y su porqué salen de HU-198
  - [ ] El motor recibe la configuración ya leída: no abre los archivos (R6)
  - [x] Si falta una señal en `weights.yaml` o un peso está fuera de 0 a 5, la API no arranca y dice por qué. Lo mismo con `thresholds.yaml`: una curva sin orden, una calificación fuera de 0 a 100, una curva sin fuente, un suelo crítico o una señal sin curva con umbral (`backend/config/thresholds.py`, pruebas en `tests/test_umbrales.py`)
  - [ ] La respuesta incluye la versión del dataset y de las reglas, y los pesos usados (`weights`)
- **Reglas que aplican:** R4, R6, R10
- **Notas:** **13 de octubre de 2026:** hecha la parte de los pesos (`backend/config/weights.py`, con pruebas en `tests/test_version.py`). Falta `thresholds.yaml` y todo lo que depende del motor. **10 de noviembre de 2026:** hecho `thresholds.yaml` 1.0.0 (decidido por Felipe el 10 de noviembre de 2026). Agua: clases del WRSI de FEWS NET (100 sin déficit, menos de 50 pérdida, Smith 1992); heladas: niveles de riesgo del ZARC de Brasil (20, 30 y 40 % de los años, mínima ≤ 2 °C); calor: crítica solo al llegar a `heat_max_c` de EcoCrop; suelo: de la ficha y nunca crítica; oferta y mercado: **sin fuente**, `insufficient_data`; 70 y 40: convención, con el ejemplo de la FAO de 1985. Las fuentes del agua y las heladas son derivadas y se dice en `sources`. Falta lo que depende del motor: que reciba los umbrales ya leídos y que cada respuesta diga sus versiones.

### HU-076 · Endpoint de diagnóstico con errores claros

- **Historia:** Como desarrollador web, quiero el endpoint de diagnóstico con errores claros, para distinguir una entrada inválida de una sin datos y de un cultivo que no es apto.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /api/v1/diagnostics` recibe `municipality_id`, `crop_id`, `sowing_date`, `irrigated`, `priorities` y `lot_id`, según el contrato
  - [ ] 422 para entradas fuera del catálogo, un cultivo con `kind` distinto de `crop`, un `sowing_date` con formato inválido, anterior a hoy o a más de doce meses, o `priorities` con un peso fuera de 0 a 5 o todos en 0
  - [x] «Hoy» y «el mes en curso» se cuentan en la hora de la región (en la piloto, `America/Bogota`, UTC−5), no en UTC ni en la del servidor. Prueba: el 30 de noviembre a las 8:00 p. m. de Bogotá (1 de diciembre en UTC), un `sowing_date` del 1 de noviembre se acepta; el 1 de diciembre a las 12:30 a. m. de Bogotá, se rechaza (`specs/02-contratos.md`, «Fechas»). Hecho el 11 de noviembre de 2026: la zona sale de `region.timezone` en `pipeline/region.yaml` y la API la usa en una sola función (`common/region.py`, `region_today`); pruebas en `tests/test_hoy_en_la_region.py`. Es la hora de la región, no la de quien consulta: el mes de siembra es el del campo, y la misma consulta da lo mismo desde cualquier país (decidido por Felipe el 11 de noviembre de 2026)
  - [ ] Sin `priorities`, usa los pesos por defecto y `overall` coincide con `overall_default`
  - [ ] 200 con `insufficient_data` para entradas válidas sin datos
  - [ ] 200 con `suitability.level = not_suitable`, luz `red` y acción `rotate` para un cultivo que no es apto; no es un error
  - [ ] Con `lot_id`, el suelo, la altitud y `irrigated` se toman del lote; 401 con `lot_id` y sin sesión; 404 con un lote ajeno
  - [ ] No guarda los datos de la finca ni quién consultó, tampoco las prioridades (R9)
- **Reglas que aplican:** R1, R3, R4, R9
- **Contrato que toca:** `POST /api/v1/diagnostics` y la tabla de errores

### HU-078 · Endpoints de catálogo y tendencias

- **Historia:** Como desarrollador web, quiero los endpoints de municipios, cultivos, límites, suelo del municipio y tendencias, para armar la consulta y las gráficas.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] `GET /catalogs/municipalities`, `/catalogs/crops`, `/catalogs/municipalities/{id}/boundary`, `/catalogs/municipalities/{id}/soil` y `/trends` según el contrato
  - [ ] `/trends` recibe `sowing_date` y devuelve tres series: `water` (por año, `precip_mm` de los meses de la ventana, de la fuente de lluvia que calcula la señal, y `need_mm` del cultivo), `supply` (por año, `planted_ha` y `preliminary` del semestre de EVA en que cae la fecha) y `ndvi` (por periodo de 16 días, `ndvi_normal` del municipio, HU-208)
  - [ ] Solo leen el dataset publicado; sin datos, la serie viene vacía con `insufficient_data` (R1)
- **Reglas que aplican:** R1, R4, R7
- **Notas:** La serie `ndvi` se sumó el 11 de octubre de 2026 (decisión 12): sirve para contrastar la ventana con la época en que el campo suele estar verde. **15 de octubre de 2026:** hecho `GET /catalogs/municipalities` (`backend/api/catalogs.py`): lee el dataset publicado y, sin él, responde 503 `dataset_unavailable` con el motivo en el log. El 15 de octubre de 2026, también `GET /catalogs/municipalities/{id}/boundary`. Faltan los cultivos, el suelo y `/trends`. **10 de noviembre de 2026:** `/catalogs/crops` y `/catalogs/municipalities/{id}/soil` ya existen (`backend/api/catalogs.py`); falta `/trends`, que responde 501.

### HU-217 · Comparar dos periodos de la historia de la zona

- **Historia:** Como motor, quiero comparar el clima de un municipio y las mejores ventanas de un cultivo entre dos periodos de la misma fuente, para que el agricultor vea qué cambió en su zona y adapte su finca.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Función pura: recibe `climate_change_month` de los dos periodos, los años de cada periodo de `climate_month` y `precip_month`, la ficha del cultivo, el suelo y la oferta del municipio y la configuración; no lee archivos (R6)
  - [ ] Por mes (1 a 12): `frost_freq_pct`, `precip_normal_mm` y `tmax_p90_c` de cada periodo y su diferencia (después menos antes), cada uno con `status` (R1)
  - [ ] Las mejores ventanas por mes de siembra en cada periodo, con el orden de HU-192 y los pesos por defecto de `weights.yaml`. Solo cambia el clima: la oferta, el mercado y el suelo son los mismos en los dos periodos, y la respuesta lo dice en `limitations`
  - [ ] El agua de cada ventana usa el balance de HU-144 sobre los años de su periodo, con la fuente de lluvia del periodo
  - [ ] Primero la aptitud (HU-191): si el cultivo no es apto, no hay ventanas y la razón lo dice
  - [ ] Un mes sin datos suficientes en alguno de los dos periodos tiene la diferencia en `insufficient_data`; nunca se compara con un solo periodo ni se rellena (R1)
  - [ ] Cada razón dice el periodo de cada valor («Entre 1981 y 2000 heló en enero en 30 de cada 100 años; entre 2005 y 2024, en 18») y ninguna dice qué pasará (decisión 4, R5)
  - [ ] Los periodos llegan de la configuración versionada, no del código; misma entrada, misma salida (R4)
  - [ ] Caso de referencia: con datos de ejemplo en que las heladas de enero bajan, la diferencia de enero es negativa y la razón lo cuenta como historia
- **Reglas que aplican:** R1, R2, R4, R5, R6, R8
- **Contrato que toca:** respuesta de `GET /api/v1/changes`; `climate_change_month`, `climate_month`, `precip_month`
- **Notas:** Decisión 12. Depende de HU-216, HU-144, HU-191, HU-192 y HU-196. Con IMERG solo hay datos desde 2000, y la respuesta lo dice. Supuesto por confirmar: sin `irrigated`, la comparación del agua se hace sin riego y lo dice en las limitaciones. Agregada el 11 de octubre de 2026.

### HU-218 · Endpoint de «Qué cambió»

- **Historia:** Como desarrollador web, quiero el endpoint de «Qué cambió», para mostrar la pantalla «Qué cambió en su zona».
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /api/v1/changes?municipality_id=&crop_id=&irrigated=` según el contrato; `irrigated` es opcional
  - [ ] 422 si el municipio o el cultivo no están en el catálogo, o si el cultivo no tiene `kind = crop`
  - [ ] 200 con `insufficient_data` en cada valor que no tiene datos; 200 con `suitability.level = not_suitable` y sin ventanas si el cultivo no es apto
  - [ ] Trae `periods` (cada uno con `period_id`, `start_year`, `end_year` y `source_id`), `weights_basis = default` y `versions` (R4)
  - [ ] No guarda los datos de la consulta ni quién consultó (R9)
- **Reglas que aplican:** R1, R4, R9
- **Contrato que toca:** `GET /api/v1/changes`, tabla de errores
- **Notas:** Decisión 12. Agregada el 11 de octubre de 2026.

### HU-195 · Señales de exceso de lluvia, enfermedad y cosecha

- **Historia:** Como agricultor, quiero saber si en mi ventana suelen caer aguaceros, darse semanas favorables a una enfermedad o faltar días secos para cosechar, para completar el cuadro de riesgos.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señales `excess_rain`, `disease` y `harvest_weather` con la misma forma que las del P0 (con `score` de HU-196 y `counts`), desde `heavy_rain_days_mean`, `blight_days_mean` y `dry_window_freq_pct` (HU-046)
  - [ ] `excess_rain` puede ser crítica y, crítica, cuenta siempre como riesgo grave de clima, también con peso 0; `disease` y `harvest_weather` no
  - [ ] Cuando existan, las tres tienen peso de 0 a 5, como las del P0
  - [ ] `disease` solo existe para un cultivo con una regla publicada y con fuente (por ejemplo, la gota de la papa); no cubre plagas en general
  - [ ] Una señal que todavía no existe no aparece en la respuesta: no se devuelve vacía ni inventada (R5)
  - [ ] Sin datos nunca cambian la luz (regla 5 del semáforo)
- **Reglas que aplican:** R1, R2, R5, R8
- **Contrato que toca:** `signals` de la respuesta de diagnóstico y de las ventanas de `/calendar`
- **Notas:** Depende de HU-046. Umbrales por confirmar con fuente. Las señales del P1 también tienen peso y `excess_rain` crítico cuenta como riesgo grave de clima (`specs/01-reglas.md`, «Agregación del semáforo»); `priorities` y `weights.yaml` suman sus pesos cuando existan. Agregada el 11 de octubre de 2026.
