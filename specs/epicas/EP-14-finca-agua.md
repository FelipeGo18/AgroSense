---
id: EP-14
titulo: "Agua del plan y etapas del cultivo"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web, Datos y Producto y agro"
agentes: [motor-api, web, datos, producto-agro]
subsistemas: [AG1, D3, M1, M7, M10, W7]
depende_de: [EP-04, EP-06, HU-181]
reglas: [R1, R2, R3, R4, R5, R6, R9, R10]
estado: en curso
---

# EP-14 · Agua del plan y etapas del cultivo

**Resultado esperado:** El motor sabe en qué etapa está cada cultivo de una ventana de siembra (con la duración de su ficha) y cuánta agua necesitará cada ciclo de una estrategia, mes a mes, en año normal y en año seco, con la lluvia de la NASA, la ET0 por Penman-Monteith y el agua que retiene el suelo. El agricultor ve el agua del plan en cada ciclo (HU-215) y los meses en que es probable regar o en que la lluvia no alcanza. El P0 da los meses típicos de déficit con el clima histórico; saber el día exacto exige medir la humedad del lote o tener pronóstico, por eso el aviso semanal queda en P1.

HU-142 (etapas y Kc de los 7 cultivos) se hace en la fase 0; el resto, en el evento.

**El balance hídrico y las etapas van antes del diagnóstico.** HU-143, HU-144 y HU-220, con las etapas de HU-142, son la base de la señal `water` de EP-07 (HU-071) y de la duración de cada ventana. No hay ciclo: EP-07 depende de HU-142 a HU-144 y HU-220. El balance (HU-144) también usa la textura del suelo publicado (HU-181, EP-18), que no depende de EP-07.

**Recorte del MVP (11 de octubre de 2026):** pasaron a P1 la finca temporal (HU-141, HU-145; sin cuenta se consulta por municipio, cultivo y área en las estrategias, HU-214), la etapa por temperatura acumulada y la línea de tiempo (HU-150, HU-186; en el MVP la duración sale de la ficha por calendario, HU-220) y el calendario completo (HU-179, HU-180; las mejores ventanas siguen en el diagnóstico y en las estrategias).

## Historias de usuario

### HU-142 · Etapas de cada cultivo con Kc

- **Historia:** Como motor, quiero las etapas de cada cultivo con su duración y coeficiente de cultivo (Kc), para estimar su consumo de agua y lo que dura cada ventana.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] `crop_stages` de los 7 cultivos del MVP (papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia): cada etapa con `days`, `kc`, `frost_sensitive` y `heat_sensitive`, y `gdd` solo si hay fuente
  - [x] Valores de FAO-56 o de una fuente local, citados (R8); si se adaptan a la región, se dice cómo (`fao_56` por etapa en `catalog/crops.yaml`)
  - [x] La suma de los días de las etapas coincide con `cycle_months` de la ficha, con la tolerancia que se documente (`cycle_months` sale de la suma de las etapas: días entre 30,44, con un decimal; `pipeline/catalog.py`)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R8
- **Contrato que toca:** `crop_stages`
- **Notas:** Se hace en la fase 0, con prioridad alta (`docs/orden-de-desarrollo.md`). Fijada a los 7 cultivos del MVP el 11 de octubre de 2026 (decisión 12).

### HU-220 · Etapas de una ventana por calendario

- **Historia:** Como motor, quiero las etapas de un cultivo y su cosecha estimada desde una fecha de siembra con la duración de su ficha, para evaluar cualquier ventana sin depender de grados-día.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Con `sowing_date` y los `days` de `crop_stages`, da la etapa de cada día de la ventana, los meses que caen en etapas sensibles a la helada y al calor, y `harvest_estimate` con `harvest_basis = calendar`
  - [x] Una sola función (`crop_window`) para todo lo que necesita las etapas de una ventana: las señales (HU-071, HU-077 y HU-190), el orden de ventanas (HU-192), los ciclos de las estrategias (HU-213), «Qué cambió» (HU-217) y la etapa de las temporadas en curso del lote (`stage_method = calendar`). `stage_today` ya la usa; cada una de las demás la llama desde su HU
  - [x] Sin los días de alguna etapa con fuente, no hay ventana: las señales que la necesitan quedan `insufficient_data` (R1)
  - [x] Función pura: misma entrada, misma salida; no lee el reloj ni archivos (R4, R6)
  - [x] Prueba: un cultivo cuyas etapas suman 150 días, sembrado el 3 de agosto, da la cosecha estimada el 31 de diciembre
- **Reglas que aplican:** R1, R4, R6, R8
- **Contrato que toca:** `harvest_basis` (`calendar`), `stage_method`, `crop_stages`
- **Notas:** Decisión 12. Reemplaza en el MVP al cálculo por temperatura acumulada (HU-150 y HU-186, que pasaron a P1): cuando existan, la duración sale del clima de la zona y la base cambia a `normal_year`. Agregada el 11 de octubre de 2026. Avance del 17 de octubre de 2026: `backend/engine/stages.py` (`stage_today`) da la etapa de hoy, su avance y la cosecha estimada de las temporadas en curso (`stage_method = calendar`); falta la etapa de cada día de una ventana y los meses sensibles, para las señales. **10 de noviembre de 2026:** hecha. `crop_window` (`backend/engine/stages.py`) da las etapas de la ventana con sus fechas, su Kc y su sensibilidad, la etapa de cada día, los meses que toca (con el año de cada mes, para las ventanas que pasan de diciembre a enero) y los meses en etapa sensible a la helada o al calor, con su estado: `available`, `not_applicable` si ninguna etapa es sensible, o `insufficient_data` si alguna etapa no dice si lo es (R1). Pruebas en `tests/engine/test_ventana.py`. **Hallazgo:** en el catálogo, cebolla de bulbo, haba y maíz no dicen la sensibilidad a la helada, y ningún cultivo dice la del calor: esas señales quedan en `insufficient_data` hasta HU-063. Una etapa sin días (0) también deja al cultivo sin ventana, en vez de saltarla; el catálogo no tiene ninguna.

### HU-143 · Lluvia y ET0 mensuales por municipio

- **Historia:** Como motor, quiero la lluvia y la evapotranspiración de referencia (ET0) mensuales por municipio, con su normal y un año seco, para calcular el balance de agua.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] ET0 por Penman-Monteith (FAO-56) con la temperatura, la radiación, el viento y la humedad relativa de NASA POWER (HU-205); método documentado (`pipeline/et0.py`)
  - [x] Un mes sin alguna de esas variables no tiene ET0: `et0_mm` queda nulo y `quality = partial`. Nunca se cambia de método en silencio (R1)
  - [x] Año seco definido como un percentil bajo de la serie: el percentil 20 de 1991–2020, decidido por Felipe el 10 de noviembre de 2026
  - [x] `et0_mm`, `et0_normal_mm` y `precip_dry_mm` en `climate_month`, sobre la lluvia de HU-042; el año seco de IMERG va en `precip_month` (HU-207)
  - [x] Comprobación manual en un municipio (en 4, contra la evaporación del IDEAM: ver las notas)
- **Reglas que aplican:** R1, R8
- **Contrato que toca:** `climate_month`
- **Notas:** Va antes del diagnóstico: la señal `water` (HU-071) lo necesita. Cambió de Hargreaves a Penman-Monteith el 11 de octubre de 2026 (decisión 12), porque POWER ampliado entrega la radiación, el viento y la humedad. La versión por semana (`et0_normal_mm` de `climate_risk_week`, HU-193, P1) usa este mismo método. **10 de noviembre de 2026:** `pipeline/et0.py` es la ecuación 6 de FAO-56, diaria, con el flujo de calor del suelo en cero; reproduce el ejemplo 18 del libro (3,9 mm/día en Bruselas). Usa la mínima y la máxima corregidas por altitud, la humedad relativa media de POWER para la presión de vapor (ecuación 19: POWER no da la máxima ni la mínima), el viento a 2 m, la radiación y la altitud del municipio para la presión. Un mes tiene ET0 solo si todos sus días la tienen: no la tienen de 1981 a 1983, porque la radiación de POWER empieza en 1984, ni un mes al que le falta un día de radiación. La normal es la de 1991–2020 con 24 años. El año seco es el percentil 20 de la lluvia de cada mes en 1991–2020: la que se supera en 4 de cada 5 años. **Comprobación** contra la evaporación de tanque de las normales 1991–2020 del IDEAM, con el coeficiente de tanque de FAO-56 (de 0,6 a 0,85): UPTC, Tunja, ET0 de 951 mm al año y 1289 de evaporación (0,74); Surbata Bonza, Duitama, 1110 y 1408 (0,79); Villa de Leyva, 1058 y 1485 (0,71); todas dentro del rango (con la altitud de la cabecera, decidida por Felipe; antes, con la mediana, 0,72, 0,74 y 0,70). Tibaitatá, Mosquera, 1077 y 1134 (0,95), por encima: su celda de POWER está a 1790 m y es más seca que la estación. **Revisión de Felipe del PR #24 (10 de noviembre de 2026):** el año seco es el percentil 20 de la lluvia de cada mes, la lluvia confiable con que la FAO planea el riego (decidido por Felipe). El periodo normal, sus años mínimos, el 90 % de los días y el percentil del año seco van en `pipeline/region.yaml` (`climate_normal`), uno solo para la lluvia, la ET0 y la temperatura media anual. La ET0 toma la mínima y la máxima ya corregidas de `climate_day`: la corrección por altitud está en un solo lugar.

### HU-144 · Déficit de agua por cultivo y etapa

- **Historia:** Como agricultor, quiero saber cuánta agua le falta a cada cultivo según su etapa, para planear el riego y saber si la lluvia de una ventana le alcanza.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Déficit = ET0 × Kc menos lluvia efectiva, por cultivo y mes
  - [ ] La lluvia sale de la fuente que define `sources.yaml` para la región (IMERG o POWER) y la ET0, de `climate_month`; la respuesta dice la fuente de cada una
  - [ ] El balance tiene en cuenta cuánta agua retiene el suelo según su textura (`texture_class` o `clay_pct`, `sand_pct` y `silt_pct`): un suelo arenoso guarda menos agua entre lluvias que uno arcilloso. El método es uno con fuente (R8)
  - [ ] Para la señal `water` de `/diagnostics` y de los ciclos de `/rotations`, el suelo es el del lote cuando llega `lot_id` (HU-182) y, si no, el del municipio (`soil_municipality`). El plan de agua (`/water-plans`) no recibe `lot_id` y usa siempre el del municipio, también con cuenta. La respuesta dice cuál se usó (R10)
  - [ ] Sin la textura del suelo, el balance se calcula sin retención y se agrega a las limitaciones (R1)
  - [ ] Volumen en m³ según el área de cada cultivo
  - [ ] Año normal y año seco; misma entrada, mismo resultado. Para la señal `water` (HU-071) el déficit se calcula con el año seco (`precip_dry_mm`), no con el normal (decidido por Felipe el 11 de noviembre de 2026); el plan de agua (`/water-plans`) sigue mostrando los dos
  - [ ] El mismo cálculo, sin área, da el déficit de una ventana de siembra para la señal `water` (HU-071): no hay dos balances de agua
  - [ ] Sin lluvia de la fuente elegida, sin ET0 o sin Kc de alguna etapa, no devuelve un déficit: quien lo llama responde `insufficient_data` (R1). El Kc de la etapa de desarrollo no falta: se interpola en línea recta entre el de la inicial y el de la media (FAO-56; contrato, `crop_stages`)
  - [ ] Prueba: con la misma lluvia y el mismo cultivo, un suelo arenoso da un déficit mayor o igual que uno arcilloso
- **Reglas que aplican:** R1, R4, R6, R8, R10
- **Contrato que toca:** `climate_month`, `precip_month`, `crop_stages`, `grid_cells`, `soil_municipality`
- **Notas:** Va antes del diagnóstico. La lluvia efectiva y el agua que retiene cada textura necesitan un método con fuente: por confirmar con fuente (R8); la candidata para la retención es FAO-56, por verificar. La textura entró al balance el 11 de octubre de 2026 (decisión 10) y la lluvia de IMERG el mismo día (decisión 12). Lluvia y ET0 son variables distintas: usar IMERG para una y POWER para la otra no es mezclar fuentes de un mismo indicador (decisión 11).

### HU-146 · Endpoint del plan de agua

- **Historia:** Como desarrollador web, quiero el endpoint del plan de agua, para mostrar el agua de cada ciclo de una estrategia.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Responde con la forma del contrato: por cultivo y por finca, el déficit y el volumen por mes en rangos, en año normal y año seco, con `sources`, `soil_basis` y `versions`
  - [ ] 422 si los porcentajes pasan de 100 o el cultivo no existe
  - [ ] Trae, por mes, la humedad del suelo de la zona (POWER y, si existe, SMAP) como contraste, cada una en su unidad y con su fuente; no cambia el déficit (decisión 11)
  - [ ] No persiste los datos de la finca (R9)
- **Reglas que aplican:** R1, R9, R10
- **Contrato que toca:** `POST /api/v1/water-plans`
- **Notas:** En el MVP la web lo llama desde el ciclo de una estrategia (HU-215) con un solo cultivo y `area_pct` 100. La humedad del suelo se sumó el 11 de octubre de 2026 (decisión 12).

### HU-141 · Registrar la finca

- **Historia:** Como agricultor, quiero registrar mi finca con su área total, el porcentaje de cada cultivo y su fecha de siembra, para recibir un plan a mi medida.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Área en hectáreas; solo cultivos del catálogo
  - [ ] Los porcentajes suman como máximo 100 %; el resto se muestra como descanso
  - [ ] Sin cuenta, los datos se envían solo para calcular y no se guardan; con cuenta, se guardan como un lote con sus temporadas (EP-16, HU-168)
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Sin cuenta, el MVP consulta por municipio, cultivo anterior y área en la entrada de las estrategias (HU-214).

### HU-145 · Calendario de riego de la finca

- **Historia:** Como agricultor, quiero un calendario de riego de mi finca, para saber en qué semanas o meses regar y cuánto.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Meses de déficit resaltados por cultivo, con rangos
  - [ ] Volumen total de la finca
  - [ ] Rótulo: «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote»
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP el agua se ve por ciclo de una estrategia (HU-215).

### HU-150 · Etapa del cultivo por temperatura acumulada

- **Historia:** Como agricultor, quiero que la etapa de mi cultivo siga la temperatura real de mi zona, para ver el lote más cerca de como está de verdad.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El catálogo guarda, por cultivo, la temperatura base y la temperatura acumulada (grados-día) que cierra cada etapa, con su fuente (R8)
  - [ ] El motor calcula la etapa de cada temporada en curso con la temperatura diaria del municipio (NASA POWER) acumulada desde la fecha de siembra
  - [ ] La respuesta dice con qué método se calculó (`thermal_time` o `calendar`) y hasta qué fecha llegan los datos de temperatura
  - [ ] Si faltan datos de temperatura o el cultivo no tiene grados-día con fuente, se usa la duración por calendario de HU-220 y se dice en pantalla: nunca se sustituye en silencio (R1)
  - [ ] La web muestra «etapa estimada con la temperatura de la zona» junto a la etapa, y la fecha del último dato
  - [ ] Caso de referencia del motor: misma fecha de siembra, un periodo frío y uno cálido dan etapas distintas
- **Reglas que aplican:** R1, R4, R5, R6, R8
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP (la duración sale de la ficha por calendario, HU-220). Es una estimación con el clima del municipio, no una observación del lote: NASA POWER da un punto por municipio y publica con 2 a 7 días de retraso. No predice rendimiento. La cosecha estimada (`harvest_estimate`, HU-186) sale de un año normal, lleva siempre su base (`harvest_basis`) y no es un pronóstico. Contrato aprobado por Felipe el 10 de octubre de 2026: tabla `climate_day`, `base_temp_c` en `crops`, `gdd` en `crop_stages` y la etapa en `current_seasons` de `GET /api/v1/lots/{lot_id}`. Falta el catálogo de grados-día con fuente por cultivo. Decidido el 10 de octubre de 2026 (ver `docs/registro-de-decisiones.md`).

### HU-179 · Calendario del cultivo

- **Historia:** Como desarrollador web, quiero el endpoint del calendario en sus dos lecturas, para mostrar las ventanas de siembra ordenadas y el seguimiento de un cultivo ya sembrado.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /api/v1/calendar` según el contrato: recibe `municipality_id`, `crop_id`, `sowing_date`, `month`, `priorities`, `irrigated` y `lot_id`
  - [ ] **Planear una siembra** (sin `sowing_date`): responde `suitability`, `windows` y `best_windows` con el orden de HU-192: primero el factor que más limita y después el promedio ponderado por las prioridades. Sin `month`, doce ventanas (`granularity = month`); con `month`, las semanas de ese mes (`granularity = week`)
  - [ ] Cada ventana trae la calificación de 0 a 100 de cada señal (HU-196) y cuál es su factor limitante
  - [ ] `priorities` usa los mismos pesos y el mismo significado que en el diagnóstico (0 a 5 por señal); sin `priorities`, los de `weights.yaml`
  - [ ] Si el cultivo no es apto para la zona, `windows` viene vacío y `suitability` dice por qué (HU-191)
  - [ ] **Mi cultivo** (con `sowing_date`): responde `months`, uno por cada mes de la siembra a la cosecha estimada, con `month`, `year`, `stage`, `basis` y los bloques `frost` y `heat`, cada uno con `status`, `level`, `reasons`, `sensitive` y `watch`; más `harvest_estimate` y `harvest_basis`. Usa el cálculo de etapas de HU-150 y HU-186
  - [ ] El cruce entre el riesgo y la etapa lo hace el motor: `watch` es verdadero solo si la etapa es sensible y el nivel no es `favorable` (R5)
  - [ ] `irrigated` se comporta igual que en el diagnóstico; con `lot_id`, sale del lote
  - [ ] `month` fuera de 1 a 12, o `priorities` fuera de 0 a 5 o todas en 0, responden 422
  - [ ] Misma entrada, misma salida; trae `versions` (R4); no guarda los datos de la finca ni quién consultó (R9)
  - [ ] Prueba: una ventana del calendario y el diagnóstico de esa fecha dan las mismas señales
- **Reglas que aplican:** R1, R2, R3, R4, R5, R6, R9
- **Contrato que toca:** `POST /api/v1/calendar`
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Las mejores ventanas siguen en el diagnóstico (HU-192, HU-194) y en las estrategias. Depende de HU-192 (orden de ventanas), HU-196 (calificación), HU-077 (heladas), HU-190 (calor) y HU-191 (aptitud). Ya no calcula un «mejor mes» propio ni alimenta la señal de heladas: reutiliza las señales de EP-07. «Mi cultivo» no usa prioridades: sigue lo que ya está sembrado. Los bloques `fertilizing`, `field_work`, `blight` y `selling` llegan en P1 con HU-046 y EP-05. Supuesto por confirmar: qué responde «Mi cultivo» si el cultivo no es apto para la zona (el contrato solo lo dice para «Planear una siembra»). Reescrita el 11 de octubre de 2026 y ajustada el mismo día al método de factor limitante (decisión 10).

### HU-180 · Vista del calendario

- **Historia:** Como agricultor, quiero comparar cuándo sembrar según lo que más me importa, y ver mes a mes qué viene para el cultivo que ya sembré, para organizar el año.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
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
  - [ ] Rótulo visible: «Según la historia de la zona. No es un pronóstico»
  - [ ] Si el cultivo no es apto para la zona, la vista lo dice con su razón y ofrece elegir otro cultivo, sin ventanas
  - [ ] **Mi cultivo:** los meses de la siembra a la cosecha estimada, con la etapa del cultivo, las heladas y el calor con «Vigile» en las etapas sensibles (`frost.watch`, `heat.watch`) y el déficit de agua del plan de agua (HU-145), sin repetir el cálculo; se dice «riego probable» si el lote tiene riego y «la lluvia no alcanza: el cultivo pasaría sed» si no lo tiene o no está definido
  - [ ] Cada nivel va con forma y texto, no solo color; lo estimado con un año normal y el riego llevan su rótulo (R10)
  - [ ] Tocar un mes o una ventana muestra las razones que evaluó el motor (R5)
  - [ ] Después de la cosecha estimada, enlace a «Próxima siembra»
  - [ ] P1: en «Mi cultivo» se agregan las filas «Abonar» (aguaceros, nunca la dosis), «Labores y cosecha» (ventanas secas) y «Gota» (solo papa) con HU-046, y «Vender» (índice estacional de precio, nunca precio futuro) con la señal de mercado. Una fila solo aparece cuando su dato existe
  - [ ] Disponible sin cuenta desde la consulta (solo «Planear una siembra») y con cuenta en cada lote
  - [ ] Cada control tiene una función; nada decorativo
- **Reglas que aplican:** R1, R2, R3, R5, R10
- **Contrato que toca:** `POST /api/v1/calendar`
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Las decisiones de cada momento del ciclo están en `docs/investigacion-decisiones.md`. Ampliada el 11 de octubre de 2026 con el orden de ventanas, las prioridades, el alto riesgo, el detalle por semanas y el calor, y el mismo día con el factor limitante y los pesos compartidos con la consulta (decisión 10). Con ese alcance queda por encima de M: revisar el tamaño con el equipo o dividirla en «Planear una siembra» y «Mi cultivo». Los controles de prioridad son el mismo componente de HU-202.

### HU-186 · Línea de tiempo del cultivo

- **Historia:** Como agricultor, quiero mover el tiempo y ver cómo crece mi cultivo, desde la siembra hasta la cosecha, para entender en qué va y qué viene.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_normal_doy` publicada por el pipeline, con fuente
  - [ ] `GET /api/v1/seasons/{season_id}/growth` según el contrato: `observed` hasta `thermal_data_until`, `normal_year` después
  - [ ] Misma entrada, misma salida; trae `versions` (R4)
  - [ ] Sin temperatura o sin grados-día con fuente: duración por calendario y se dice (R1)
  - [ ] El mismo cálculo, para una fecha de siembra sin temporada registrada, da las etapas y la cosecha estimada de una ventana de siembra con un año normal; cuando exista, reemplaza a HU-220 en el diagnóstico, el orden de ventanas y las estrategias
- **Reglas que aplican:** R1, R4, R5, R6
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP (en el MVP la duración de la ventana sale de HU-220). Reutiliza el cálculo de HU-150. Lo que viene después de hoy es una estimación con un año normal, nunca un pronóstico (decisión 4). Decidido el 11 de octubre de 2026.

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
