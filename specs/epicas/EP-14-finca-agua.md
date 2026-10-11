---
id: EP-14
titulo: "Finca y plan de agua"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web, Datos y Producto y agro"
agentes: [motor-api, web, datos, producto-agro]
subsistemas: [AG1, D3, M1, M7, M10, W7]
depende_de: [EP-04, EP-06, HU-181, HU-192, HU-196]
reglas: [R1, R2, R3, R4, R5, R6, R9, R10]
estado: pendiente
---

# EP-14 · Finca y plan de agua

**Resultado esperado:** El agricultor compara las ventanas de siembra de los próximos doce meses, por mes y por semana, ordenadas según lo que más le importa, y sigue mes a mes el cultivo que ya sembró, con las heladas y el calor que debe vigilar (calendario). Además, registra su finca (sin cuenta, como finca temporal en su dispositivo con el porcentaje del terreno de cada cultivo; con cuenta, como lotes de EP-16) y ve cuánta agua necesitará cada cultivo y en qué meses es probable que tenga que regar. El P0 da los meses típicos de déficit con el clima histórico; saber el día exacto exige medir la humedad del lote o tener pronóstico, por eso el aviso semanal queda en P1.

HU-142 (etapas y Kc) se hace en la fase 0; el resto, en el evento.

**El balance hídrico va antes del diagnóstico.** HU-143 y HU-144, con las etapas de HU-142, ya no sirven solo al plan de agua: son la base de la señal `water` de EP-07 (HU-071). El cálculo de etapas (HU-150 y HU-186) también va antes, porque de él sale lo que dura cada ventana. En cambio, el calendario (HU-179) va después de EP-07: reutiliza sus señales y el orden de ventanas (HU-192). No hay ciclo: EP-07 depende de HU-142 a HU-144, HU-150 y HU-186; solo HU-179 y HU-180 dependen de EP-07. Desde el 11 de octubre de 2026 el balance (HU-144) también usa la textura del suelo publicado (HU-181, EP-18), que no depende de EP-07.

## Historias de usuario

### HU-141 · Registrar la finca

- **Historia:** Como agricultor, quiero registrar mi finca con su área total, el porcentaje de cada cultivo y su fecha de siembra, para recibir un plan a mi medida.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Área en hectáreas; solo cultivos del catálogo
  - [ ] Los porcentajes suman como máximo 100 %; el resto se muestra como descanso
  - [ ] Sin cuenta, los datos se envían solo para calcular y no se guardan; con cuenta, se guardan como un lote con sus temporadas (EP-16, HU-168)

### HU-142 · Etapas de cada cultivo con Kc

- **Historia:** Como motor, quiero las etapas de cada cultivo con su duración y coeficiente de cultivo (Kc), para estimar su consumo de agua.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Valores de FAO-56 o de una fuente local, citados
  - [ ] Revisión cruzada por otro integrante
- **Notas:** Se hace en la fase 0.

### HU-150 · Etapa del cultivo por temperatura acumulada

- **Historia:** Como agricultor, quiero que la etapa de mi cultivo siga la temperatura real de mi zona, para ver el lote más cerca de como está de verdad.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El catálogo guarda, por cultivo, la temperatura base y la temperatura acumulada (grados-día) que cierra cada etapa, con su fuente (R8)
  - [ ] El motor calcula la etapa de cada temporada en curso con la temperatura diaria del municipio (NASA POWER) acumulada desde la fecha de siembra
  - [ ] La respuesta dice con qué método se calculó (`thermal_time` o `calendar`) y hasta qué fecha llegan los datos de temperatura
  - [ ] Si faltan datos de temperatura o el cultivo no tiene grados-día con fuente, se usa la duración por calendario de HU-142 y se dice en pantalla: nunca se sustituye en silencio (R1)
  - [ ] La web muestra «etapa estimada con la temperatura de la zona» junto a la etapa, y la fecha del último dato
  - [ ] Caso de referencia del motor: misma fecha de siembra, un periodo frío y uno cálido dan etapas distintas
- **Reglas que aplican:** R1, R4, R5, R6, R8
- **Notas:** Es una estimación con el clima del municipio, no una observación del lote: NASA POWER da un punto por municipio y publica con 2 a 7 días de retraso. No predice rendimiento. La cosecha estimada (`harvest_estimate`, HU-186) sale de un año normal, lleva siempre su `basis` y no es un pronóstico. Contrato aprobado por Felipe el 10 de octubre de 2026: tabla `climate_day`, `base_temp_c` en `crops`, `gdd` en `crop_stages` y la etapa en `current_seasons` de `GET /api/v1/lots/{lot_id}`. Falta el catálogo de grados-día con fuente por cultivo. Decidido el 10 de octubre de 2026 (ver `docs/registro-de-decisiones.md`).

### HU-143 · Lluvia y ET0 mensuales por municipio

- **Historia:** Como motor, quiero la lluvia y la evapotranspiración de referencia (ET0) mensuales por municipio, con su normal y un año seco, para calcular el balance de agua.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] ET0 por Hargreaves con temperatura máxima y mínima, método documentado
  - [ ] Año seco definido como un percentil bajo de la serie
  - [ ] `et0_mm`, `et0_normal_mm` y `precip_dry_mm` en `climate_month`, sobre la lluvia de HU-042
  - [ ] Comprobación manual en un municipio
- **Contrato que toca:** `climate_month`
- **Notas:** Va antes del diagnóstico: la señal `water` (HU-071) lo necesita. La versión por semana (`et0_normal_mm` de `climate_risk_week`) es HU-193 y usa este mismo método.

### HU-144 · Déficit de agua por cultivo y etapa

- **Historia:** Como agricultor, quiero saber cuánta agua le falta a cada cultivo según su etapa, para planear el riego y saber si la lluvia de una ventana le alcanza.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Déficit = ET0 × Kc menos lluvia efectiva, por cultivo y mes
  - [ ] El balance tiene en cuenta cuánta agua retiene el suelo según su textura (`texture_class` o `clay_pct`, `sand_pct` y `silt_pct`): un suelo arenoso guarda menos agua entre lluvias que uno arcilloso. El método es uno con fuente (R8)
  - [ ] El suelo es el del lote si la API lo pasa (HU-182) y, si no, el del municipio (`soil_municipality`); la respuesta dice cuál se usó (R10)
  - [ ] Volumen en m³ según el área de cada cultivo
  - [ ] Año normal y año seco; misma entrada, mismo resultado
  - [ ] El mismo cálculo, sin área, da el déficit de una ventana de siembra para la señal `water` (HU-071): no hay dos balances de agua
  - [ ] Sin `climate_month` o sin Kc de alguna etapa, no devuelve un déficit: quien lo llama responde `insufficient_data` (R1)
  - [ ] Prueba: con la misma lluvia y el mismo cultivo, un suelo arenoso da un déficit mayor o igual que uno arcilloso
- **Reglas que aplican:** R1, R4, R6, R8, R10
- **Contrato que toca:** `climate_month`, `crop_stages`, `soil_grid`, `soil_municipality`
- **Notas:** Va antes del diagnóstico. La lluvia efectiva y el agua que retiene cada textura necesitan un método con fuente: por confirmar con fuente (R8); la candidata para la retención es FAO-56, por verificar. La textura entró al balance el 11 de octubre de 2026 (decisión 10). Supuesto por confirmar: si falta la textura, el balance se calcula sin retención del suelo y la limitación lo dice, o la señal de agua queda en `insufficient_data` (la segunda opción deja la luz en `not_evaluable`). `POST /water-plans` no recibe `lot_id`: el plan de agua sin cuenta usa el suelo del municipio.

### HU-145 · Calendario de riego de la finca

- **Historia:** Como agricultor, quiero un calendario de riego de mi finca, para saber en qué semanas o meses regar y cuánto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Meses de déficit resaltados por cultivo, con rangos
  - [ ] Volumen total de la finca
  - [ ] Rótulo: «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote»

### HU-146 · Endpoint del plan de agua

- **Historia:** Como desarrollador web, quiero el endpoint del plan de agua, para mostrar el calendario.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] 422 si los porcentajes pasan de 100 o el cultivo no existe
  - [ ] No persiste los datos de la finca

### HU-179 · Calendario del cultivo

- **Historia:** Como desarrollador web, quiero el endpoint del calendario en sus dos lecturas, para mostrar las ventanas de siembra ordenadas y el seguimiento de un cultivo ya sembrado.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /api/v1/calendar` según el contrato: recibe `municipality_id`, `crop_id`, `sowing_date`, `month`, `priorities`, `irrigated` y `lot_id`
  - [ ] **Planear una siembra** (sin `sowing_date`): responde `suitability`, `windows` y `best_windows` con el orden de HU-192: primero el factor que más limita y después el promedio ponderado por las prioridades. Sin `month`, doce ventanas (`granularity = month`); con `month`, las semanas de ese mes (`granularity = week`)
  - [ ] Cada ventana trae la calificación de 0 a 100 de cada señal (HU-196) y cuál es su factor limitante
  - [ ] `priorities` usa los mismos pesos y el mismo significado que en el diagnóstico (0 a 5 por señal); sin `priorities`, los de `weights.yaml`
  - [ ] Si el cultivo no es apto para la zona, `windows` viene vacío y `suitability` dice por qué (HU-191)
  - [ ] **Mi cultivo** (con `sowing_date`): responde `months`, uno por cada mes de la siembra a la cosecha estimada, con `month`, `year`, `stage`, `basis` y los bloques `frost` y `heat`, cada uno con `status`, `level`, `reasons`, `sensitive` y `watch`; más `harvest_estimate` con su `basis`. Usa el cálculo de etapas de HU-150 y HU-186
  - [ ] El cruce entre el riesgo y la etapa lo hace el motor: `watch` es verdadero solo si la etapa es sensible y el nivel no es `favorable` (R5)
  - [ ] `irrigated` se comporta igual que en el diagnóstico; con `lot_id`, sale del lote
  - [ ] `month` fuera de 1 a 12, o `priorities` fuera de 0 a 5 o todas en 0, responden 422
  - [ ] Misma entrada, misma salida; trae `versions` (R4); no guarda nada (R9)
  - [ ] Prueba: una ventana del calendario y el diagnóstico de esa fecha dan las mismas señales
- **Reglas que aplican:** R1, R2, R3, R4, R5, R6, R9
- **Contrato que toca:** `POST /api/v1/calendar`
- **Notas:** Depende de HU-192 (orden de ventanas), HU-196 (calificación), HU-077 (heladas), HU-190 (calor) y HU-191 (aptitud). Ya no calcula un «mejor mes» propio ni alimenta la señal de heladas: reutiliza las señales de EP-07. «Mi cultivo» no usa prioridades: sigue lo que ya está sembrado. Los bloques `fertilizing`, `field_work`, `blight` y `selling` llegan en P1 con HU-046 y EP-05. Supuesto por confirmar: qué responde «Mi cultivo» si el cultivo no es apto para la zona (el contrato solo lo dice para «Planear una siembra»). Reescrita el 11 de octubre de 2026 y ajustada el mismo día al método de factor limitante (decisión 10).

### HU-180 · Vista del calendario

- **Historia:** Como agricultor, quiero comparar cuándo sembrar según lo que más me importa, y ver mes a mes qué viene para el cultivo que ya sembré, para organizar el año.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Dos lecturas. **Mi cultivo** (por defecto si el cultivo elegido está sembrado en el lote) y **Planear una siembra** (parte libre, otro cultivo o sin cuenta)
  - [ ] **Planear una siembra:** las doce ventanas de los próximos doce meses en el orden del motor (`rank`), cada una con su fecha de siembra, su cosecha estimada, su factor limitante («Lo que más limita: heladas»), su balance de 0 a 100 y la calificación de cada señal, para ver qué gana y qué sacrifica cada una
  - [ ] Un texto corto explica el orden: «Primero, lo que más limita cada fecha; entre fechas parecidas, lo que usted prioriza»
  - [ ] Seis controles de prioridad, uno por señal (agua, heladas, calor, suelo, oferta y mercado), de 0 a 5; al cambiarlos se vuelve a pedir el orden. Con todos en 0, la web no envía la petición y pide subir al menos uno
  - [ ] Usa los mismos pesos que el agricultor puso en la consulta (HU-202); si no puso ninguno, los de AgroSense. Cambiarlos aquí los cambia también para el diagnóstico de esa visita
  - [ ] Las ventanas con `high_risk` van al final, con el rótulo «Alto riesgo» en forma y texto y la señal crítica que lo causa; nunca aparecen entre las mejores
  - [ ] Las mejores ventanas (`best_windows`) se destacan; si viene vacío, la pantalla dice «No hay una ventana sin riesgo alto en los próximos doce meses»
  - [ ] Tocar un mes abre el detalle por semanas de ese mes (`month`), con el mismo orden y desglose
  - [ ] Una señal sin datos o que no aplica se ve como tal y se dice que no entra al balance; no se pinta como riesgo (R1)
  - [ ] Rótulo visible: «Orden según la historia de la zona. No es un pronóstico: usted decide»
  - [ ] Si el cultivo no es apto para la zona, la vista lo dice con su razón y ofrece elegir otro cultivo, sin ventanas
  - [ ] **Mi cultivo:** los meses de la siembra a la cosecha estimada, con la etapa del cultivo, las heladas y el calor con «Vigile» en las etapas sensibles (`frost.watch`, `heat.watch`) y el riego probable del plan de agua (HU-145), sin repetir el cálculo
  - [ ] Cada nivel va con forma y texto, no solo color; lo estimado con un año normal y el riego llevan su rótulo (R10)
  - [ ] Tocar un mes o una ventana muestra las razones que evaluó el motor (R5)
  - [ ] Después de la cosecha estimada, enlace a «Próxima siembra»
  - [ ] P1: en «Mi cultivo» se agregan las filas «Abonar» (aguaceros, nunca la dosis), «Labores y cosecha» (ventanas secas) y «Gota» (solo papa) con HU-046, y «Vender» (índice estacional de precio, nunca precio futuro) con la señal de mercado. Una fila solo aparece cuando su dato existe
  - [ ] Disponible sin cuenta desde la consulta (solo «Planear una siembra») y con cuenta en cada lote
  - [ ] Cada control tiene una función; nada decorativo
- **Reglas que aplican:** R1, R2, R3, R5, R10
- **Contrato que toca:** `POST /api/v1/calendar`
- **Notas:** Las decisiones de cada momento del ciclo están en `docs/investigacion-decisiones.md`. Ampliada el 11 de octubre de 2026 con el orden de ventanas, las prioridades, el alto riesgo, el detalle por semanas y el calor, y el mismo día con el factor limitante y los pesos compartidos con la consulta (decisión 10). Con ese alcance queda por encima de M: revisar el tamaño con el equipo o dividirla en «Planear una siembra» y «Mi cultivo». Los controles de prioridad son el mismo componente de HU-202.

### HU-186 · Línea de tiempo del cultivo

- **Historia:** Como agricultor, quiero mover el tiempo y ver cómo crece mi cultivo, desde la siembra hasta la cosecha, para entender en qué va y qué viene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_normal_doy` publicada por el pipeline, con fuente
  - [ ] `GET /api/v1/seasons/{season_id}/growth` según el contrato: `observed` hasta `thermal_data_until`, `normal_year` después
  - [ ] Misma entrada, misma salida; trae `versions` (R4)
  - [ ] Sin temperatura o sin grados-día con fuente: duración por calendario y se dice (R1)
  - [ ] El mismo cálculo, para una fecha de siembra sin temporada registrada, da las etapas y la cosecha estimada de una ventana de siembra con un año normal: lo usan el diagnóstico (EP-07), el orden de ventanas (HU-192) y el calendario (HU-179)
- **Reglas que aplican:** R1, R4, R5, R6
- **Notas:** Reutiliza el cálculo de HU-150. Va antes del diagnóstico, porque la duración de cada ventana sale de aquí. Lo que viene después de hoy es una estimación con un año normal, nunca un pronóstico (decisión 4). Decidido el 11 de octubre de 2026.

### HU-147 · Aviso de riego semanal

- **Historia:** Como agricultor, quiero un aviso de riego para esta semana con la lluvia más reciente, para decidir con datos actuales.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usa los últimos datos disponibles de NASA y muestra su fecha
  - [ ] Dice explícitamente que no es un pronóstico

### HU-148 · Rotaciones ponderadas por área

- **Historia:** Como agricultor, quiero que las rotaciones tengan en cuenta cuánto terreno tengo de cada cultivo, para que la recomendación sea realista.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Los criterios de agua e ingreso se ponderan por área

### HU-149 · Guardar la finca en el dispositivo

- **Historia:** Como agricultor sin cuenta, quiero guardar mi finca en este dispositivo, para no escribirla cada vez.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Se guarda solo en el navegador y se puede borrar
  - [ ] La página funciona aunque el navegador no permita guardar
