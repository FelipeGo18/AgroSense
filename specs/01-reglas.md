# Reglas de diseño (R1–R10)

Aplican a todos los sistemas. **Una historia de usuario que viole una regla no se acepta, aunque funcione.**

| Código | Regla | Qué significa en la práctica |
|---|---|---|
| R1 | Disponibilidad y nivel son campos distintos | Una señal sin datos tiene `status = insufficient_data` y `level = null`. Nunca se interpreta como riesgo. |
| R2 | El semáforo se decide por reglas, no por promedio | Un riesgo desfavorable no se compensa con señales favorables. |
| R3 | Las restricciones agronómicas filtran | Una rotación inválida se excluye y se registra el motivo. No se castiga con puntos. |
| R4 | Resultados deterministas y versionados | Mismos datos, reglas y entrada producen el mismo resultado. Cada respuesta lleva la versión del dataset y de las reglas. |
| R5 | Nada inventado | Los datos de ejemplo se marcan como ejemplo. Las explicaciones solo citan indicadores y reglas que el motor evaluó. |
| R6 | El motor no conoce la web | El módulo de decisión no importa FastAPI ni lee archivos ni la base de datos directamente. Recibe tablas, configuración y, cuando aplica, el historial y el suelo del lote que le pasa la API. |
| R7 | Una sola llave territorial | Todo se une por el código oficial de la unidad territorial de la región (en Colombia, el código DIVIPOLA del municipio, `municipality_id`). Los nombres no se usan como llave. La región todavía no está confirmada: el modelo no supone Colombia fuera de los adaptadores de cada fuente. |
| R8 | Toda regla y dato tiene fuente, y puede tener varias | Cada fila de datos y cada regla agronómica apunta a una entrada de la tabla `sources`. |
| R9 | Los datos de la finca solo se guardan con cuenta y consentimiento | Los endpoints de cálculo (`/diagnostics`, `/rotations`, `/water-plans`, `/changes`, `/calendar`, `/scenarios`) no guardan los datos de la finca ni quién consultó. En el P0 no escriben nada en la base de datos. Desde HU-170 (P1) suman 1 al contador anónimo `usage_daily` (día, tipo de consulta, municipio y cultivo; sin usuario, sesión, IP, hora, fecha de siembra, prioridades ni área). Sin cuenta, los datos de la finca se envían solo para calcular y no se guardan en el servidor ni en sus logs. Con cuenta, se guardan los lotes y su historial con consentimiento registrado, solo los datos mínimos, y el usuario puede borrarlo todo. |
| R10 | El riego y el suelo son estimaciones y se dice siempre | El riego se basa en el clima de la zona, no en mediciones del lote: se muestran rangos y se pide verificar la humedad del suelo en campo. El suelo sale de un mapa global de 250 m (SoilGrids): se muestra con su rango de incertidumbre y se recomienda un análisis de suelo del lote. La humedad del suelo (NASA POWER, SMAP) y el verdor (MODIS NDVI) son de celdas de kilómetros o de 250 m: se dicen como datos de la zona, con su resolución, nunca como una medición del lote. |

> R9 suma `/changes` a los endpoints de cálculo y R10 suma la humedad del suelo y el verdor desde el 11 de octubre de 2026 (decisión 12 de `docs/decisiones.md`). Las demás reglas no cambiaron.

## Cómo se comprueba cada regla

| Regla | Comprobación sugerida |
|---|---|
| R1 | Prueba: una señal sin datos devuelve `insufficient_data` y `level` nulo; la web no la pinta como riesgo. |
| R2 | Prueba: una señal `unfavorable` crítica nunca da verde, aunque las otras sean `favorable`. Prueba: una helada crítica da rojo con agua y oferta favorables. Prueba: una ventana con una señal crítica queda marcada como de alto riesgo y nunca entra entre las mejores, por alto que sea su balance. |
| R3 | Prueba: una estrategia que viola un `filter` entre dos ciclos seguidos no aparece en el ranking y su exclusión cita la regla. Prueba: un cultivo que no es apto para la zona no se evalúa por ventanas y la respuesta cita el dato de su ficha que lo excluye. |
| R4 | Prueba: dos ejecuciones iguales dan salida idéntica; toda respuesta trae `versions.dataset` y `versions.rules`. |
| R5 | Revisión: ningún dato ficticio sin rótulo; cada razón de M4 mapea a un indicador o regla evaluados. |
| R6 | Prueba o lint: `backend/engine/` no importa `fastapi` ni `sqlalchemy` ni abre archivos. |
| R7 | Prueba: las uniones usan `municipality_id`; unicidad de llaves en los Parquet. Revisión: ninguna regla del motor depende de una fuente o un código propios de un país. |
| R8 | Validación: ninguna fila ni regla con `source_id` vacío o inexistente en `sources`. |
| R9 | Prueba: los endpoints de cálculo no escriben en la base de datos, salvo el contador `usage_daily` cuando existe (HU-170), que no tiene ninguna columna que identifique a una persona ni datos de la finca. Prueba: sin sesión, ningún endpoint de cuenta acepta escritura. Prueba: borrar la cuenta elimina usuario, sesiones, lotes, temporadas, tickets y sus eventos de `activity_log`. Revisión: el registro guarda el consentimiento y su versión. |
| R10 | Revisión: el rótulo de estimación aparece junto a todo resultado de riego y de suelo; se muestran rangos. Prueba: la señal de suelo nunca es crítica. Revisión: la humedad del suelo y el verdor llevan su fuente y su resolución, y el rótulo de que son de la zona. |

## La ventana de siembra

Todo se evalúa sobre una **ventana de siembra**: una fecha de siembra más lo que dura ese cultivo en campo, de la siembra a la cosecha estimada. No hay semestres en la decisión: una lechuga dura dos meses y una papa cinco, y cada una se evalúa en su propio tramo.

- En el MVP la duración sale de los días de cada etapa del cultivo (`crop_stages.days`), por calendario (HU-220), y la respuesta lo dice (`harvest_basis = calendar`). Con grados-día con fuente y la temperatura normal de la zona (HU-150 y HU-186, P1), sale del clima (`harvest_basis = normal_year`).
- Las ventanas se comparan por **mes** de siembra. Dentro de un mes, por **semana**, cuando exista el riesgo por semana (HU-193, P1).
- El semestre solo sobrevive por dentro, donde la fuente lo trae así: la oferta de EVA se lee del semestre en que cae la siembra, y la respuesta lo dice.

## Aptitud del cultivo en la zona

Antes de evaluar ventanas, el motor comprueba que el cultivo se puede dar en ese municipio. Es un filtro, no una señal (R3).

- Un cultivo **no es apto** si la temperatura media anual queda fuera de `tmean_min_c`–`tmean_max_c` de su ficha. Ejemplo: papa en un municipio de la costa. (Cambiado el 16 de octubre de 2026, decisión 13: antes se decidía por la altitud, pero ninguna fuente da bien la altitud de estos cultivos en Colombia y el criterio oficial de la UPRA es la temperatura media anual.)
- La temperatura media anual es la de NASA POWER corregida por altitud con NASADEM (HU-044): la del municipio o, si se consulta con un lote dibujado, corregida a la altitud del lote. La respuesta dice cuál se usó, con la temperatura y la altitud.
- Si no es apto, la luz es `red`, la acción es `rotate` («este cultivo no se da en su zona: elija otro»), la razón cita el dato de la ficha (el límite que se cruzó; la fuente va en `source_ids` del cultivo, no por valor), y **no se evalúan ventanas**.
- Si la ficha no tiene ese rango con fuente, la aptitud es `insufficient_data`: no bloquea y se agrega a las limitaciones (R1, R8).
- La aptitud se decide **solo por la temperatura media anual**. Solo una temperatura fuera del rango absoluto da `not_suitable`.
- `suitability.score` es una nota informativa de 0 a 100 con la curva de temperatura media: 100 dentro del rango óptimo (`tmean_opt_min_c`–`tmean_opt_max_c`) y 0 fuera del absoluto. No es una señal: no entra al semáforo ni al orden de las ventanas.
- Con la zonificación de la UPRA, el rango óptimo es la aptitud alta (A1) y el absoluto va de la baja a la alta (A3 a A1); fuera de él es no apta (N1).

## Señales de una ventana

Seis señales independientes en el P0 y tres más en el P1. Ninguna se promedia con otra para decidir el semáforo (R2). Cada señal se mide **contra lo que ese cultivo necesita o aguanta**, según su ficha: un cultivo que pide poca agua rara vez sale mal en agua.

| Señal | Qué evalúa en la ventana | Puede ser crítica | Prioridad |
|---|---|---|---|
| `water` (agua) | Si la lluvia que suele caer cubre lo que el cultivo necesita en cada etapa (balance hídrico), teniendo en cuenta cuánta agua retiene el suelo según su textura (un suelo arenoso se seca antes que uno arcilloso). Con riego (`irrigated`), la falta de lluvia no es un riesgo: la señal informa cuánto riego haría falta y nunca es `unfavorable` por eso | Sí, solo sin riego | P0 |
| `frost` (heladas) | Qué tan frecuentes han sido las heladas en los meses en que el cultivo está en una etapa sensible (por semanas con HU-193, P1) | Sí | P0 |
| `heat` (calor) | Si en las etapas del cultivo suelen darse temperaturas máximas por encima de lo que aguanta (`heat_max_c` de su ficha) | Sí | P0 |
| `soil` (suelo) | Si el pH del suelo de la zona, o del lote si se envía, está en el rango del cultivo. La textura entra en la señal de agua; el carbono orgánico alimenta la salud del suelo de las estrategias | **No:** es una estimación de 250 m (R10) | P0 |
| `supply` (oferta) | Si en la zona se está sembrando mucho o poco del cultivo, según el último dato del semestre en que cae la siembra | Sí | P0 |
| `market` (mercado) | Si el precio suele estar bajo en el mes en que saldría la cosecha | Sí | P0 la señal; los datos de SIPSA son P1 |
| `excess_rain` (exceso de lluvia) | Aguaceros frecuentes que encharcan, lavan el abono o impiden las labores | Sí | P1 |
| `disease` (enfermedades por clima) | Semanas húmedas y templadas que favorecen una enfermedad con regla publicada, como la gota de la papa. No cubre plagas en general: no hay datos abiertos | No | P1 |
| `harvest_weather` (cosecha) | Si en las semanas de cosecha suele haber días secos seguidos | No | P1 |

- `frost` y `heat` se deciden según la sensibilidad de cada etapa de la ventana: si alguna etapa es sensible, se evalúan los meses en que lo es y los que solo tocan etapas sin el dato con fuente van a las limitaciones; `not_applicable` solo si **todas** las etapas dicen que no son sensibles; si ninguna es sensible y alguna no lo dice, `insufficient_data` (R1; decidido por Felipe el 14 de noviembre de 2026, PR #69). Ejemplo: la helada de la zanahoria (no, sin dato, no, no) es `insufficient_data`, no `not_applicable`: en el desarrollo no se sabe.
- Una señal del P1 que todavía no existe no aparece en la respuesta: no se inventa (R5).
- El grado crítico de cada señal lo fija `thresholds.yaml`; la respuesta lo dice en el campo `critical`.
- Toda razón dice el periodo que se evaluó («en 7 de los últimos 10 años»): es historia, no pronóstico.
- **La lluvia de `water`** sale de la fuente que define `sources.yaml` para la región: GPM IMERG (lluvia por satélite, desde 2000) cuando la región la tiene; si no, NASA POWER (reanálisis, desde 1981). Las dos se muestran juntas para contrastar y nunca se mezclan. «Respaldo» es una elección por región en `sources.yaml`, no un relleno por consulta: si la fuente elegida no tiene dato para un municipio, la señal es `insufficient_data` (R1). En la región piloto la lluvia es la de GPM IMERG, con NASA POWER para contrastar, y la señal lleva siempre el aviso de `rain_caveat`: en los valles del altiplano IMERG la sobrestima, cerca de 1,85 veces la del IDEAM (decidido por Felipe el 11 de noviembre de 2026, PR #44). La ET0 sale de NASA POWER por Penman-Monteith (FAO-56).
- **La humedad del suelo** de la zona (la que modela NASA POWER y la de SMAP) se muestra junto a `water` para contrastar, cada una en su unidad. En el MVP no cambia la calificación.
- **El verdor** (MODIS NDVI) no es una señal: muestra en qué épocas suele estar verde el campo de la zona, para contrastar las ventanas con lo que de verdad se siembra. No cambia la luz ni el orden.
- **La oferta es valor agregado, no protagonista** (decisión 12): sigue siendo una de las seis señales, con su peso y sus reglas; en las estrategias de rotación entra solo por el criterio de ingreso.

## Cómo se califica cada señal

Cada señal recibe una **calificación de 0 a 100** con una curva por cultivo, al estilo del modelo EcoCrop de la FAO: 100 dentro del rango óptimo del cultivo, 0 fuera de sus límites absolutos y una transición recta entre ambos. Los límites de cada cultivo vienen de su ficha, con fuente (R8). La calificación da el nivel:

| Calificación | Nivel |
|---|---|
| 70 a 100 | `favorable` |
| 40 a 69 | `moderate` |
| 0 a 39 | `unfavorable` |

Qué mide cada curva:

| Señal | Variable | Límites |
|---|---|---|
| `water` | Porcentaje de lo que el cultivo necesita que cubre la lluvia **del año seco** en la ventana (`precip_dry_mm`: la que se supera en 4 de cada 5 años, la lluvia confiable con que la FAO planea el riego), con la retención del suelo. No la normal: decidido por Felipe el 11 de noviembre de 2026, porque las dos fuentes de la NASA dan casi el doble de lluvia en los valles del altiplano, donde están los cultivos (259 estaciones del IDEAM; IMERG 1,85 veces, POWER 1,80; PR #44), y con la normal el agua saldría verde donde falta | `thresholds.yaml` |
| `frost` | Porcentaje de años con al menos una helada (mínima ≤ 2 °C) en cualquiera de los meses sensibles de la ventana (semanas en P1) | `thresholds.yaml` |
| `heat` | Temperatura máxima que se supera uno de cada diez días, en las etapas sensibles | Ficha (`temp_opt_max_c`, `heat_max_c`: 100 en el óptimo alto, 0 en el máximo; sin límite inferior) |
| `soil` | pH estimado | Ficha (`ph_*`) |
| `supply` | Variación del área sembrada | `thresholds.yaml` |
| `market` | Índice estacional de precio en el mes de cosecha | `thresholds.yaml` |

Los `rain_*` de la ficha son la lluvia anual que pide el cultivo: sirven de referencia y de contraste, no entran a la curva de una ventana.

Sin la textura del suelo, el agua se calcula sin retención y se agrega a las limitaciones.

Una señal es **crítica** cuando su calificación baja del umbral crítico de `thresholds.yaml`. Los cortes de la tabla también viven ahí y se pueden ajustar con evidencia.

## Las prioridades del agricultor

Cada señal tiene un **peso de 0 a 5**. AgroSense propone un peso por defecto para cada una; el agricultor lo puede cambiar al consultar («lo que más me importa es el agua», «la oferta no me importa»). El peso cambia el semáforo y el orden de las ventanas, sin dejar de proteger contra los riesgos graves:

| Peso | Qué significa | Efecto en el semáforo |
|---|---|---|
| 0 | «No me importa» | La señal se muestra, pero no cambia la luz. Excepción: un riesgo grave de clima (`water`, `frost` o `heat` críticos) siempre cuenta |
| 1 a 3 | Importancia normal | La señal cuenta como en las reglas de agregación |
| 4 a 5 | «Me importa mucho» | Un `moderate` en esa señal cuenta como `unfavorable` para la luz |

- Los pesos por defecto viven en `weights.yaml`, versionados, y la respuesta dice cuáles se usaron (R4).
- Cuando los pesos del agricultor dan otra luz que los de AgroSense, **se muestran las dos**: «Con el criterio de AgroSense: amarillo · Con sus prioridades: verde». La decisión es del agricultor.

## Agregación del semáforo

Los umbrales viven en configuración versionada (`backend/config/`). Las reglas se aplican en orden sobre **una** ventana, con los pesos de quien consulta (y otra vez con los pesos por defecto):

0. Si el cultivo no es apto para la zona, la luz es `red` y la acción es `rotate`. No se evalúa nada más.
1. Si `water` cuenta y no está disponible, la luz es `not_evaluable` y la acción es `review_data`. Si `supply` no está disponible, se calcula sin ella, como si su peso fuera 0: no cuenta para la luz ni para el orden de las ventanas, se muestra «sin datos» y se agrega a las limitaciones.
2. Si alguna señal que cuenta es `unfavorable` y crítica, o dos señales que cuentan son `unfavorable`, la luz es `red`.
3. Si ninguna señal que cuenta es `unfavorable` y `water` es `favorable` (o no cuenta), la luz es `green`.
4. En cualquier otro caso, la luz es `yellow`.
5. `frost`, `heat`, `soil`, `supply`, `market` y las señales del P1 sin datos **nunca cambian la luz**, pero se agregan a las limitaciones. `not_applicable` tampoco la cambia.

«Señal que cuenta» es la que tiene peso mayor que 0, más los riesgos graves de clima, que cuentan siempre. Con riego, `water` no es `unfavorable` por falta de lluvia: es `favorable` y la razón dice cuánto riego haría falta.

Acción según la luz:

| Luz | Acción |
|---|---|
| `green` | `sow` |
| `yellow` | `rotate` si `soil`, `supply` o `market` son `unfavorable` (cambiar de fecha no los arregla); si no, `other_window` |
| `red` | `other_window` si todas las señales desfavorables son de clima (`water`, `frost`, `heat`, `excess_rain`); `rotate` si alguna es `soil`, `supply` o `market`, o si el cultivo no es apto |
| `not_evaluable` | `review_data` |

- Con `other_window`, la respuesta trae las mejores ventanas de los próximos doce meses, para que el agricultor vea cuándo sí.
- Con `rotate`, en el MVP la web lleva a las estrategias de rotación. En P1 (HU-197), la respuesta trae además `alternatives`: hasta tres cultivos aptos para la zona que en esa ventana salen bien en clima y tienen mejor oferta, con su razón. Nunca se sugiere un cultivo que no es apto o que sale mal en clima.
- La tabla de acciones mira solo las señales que cuentan con los pesos de esa luz.
- Las alternativas se ordenan igual que las ventanas (factor limitante y después prioridades). Un candidato con aptitud `insufficient_data` puede aparecer, con esa limitación; uno no apto, nunca. Se muestran si cualquiera de las dos luces da `rotate`, también cuando el cultivo consultado no es apto.
- Las prioridades se recuerdan: en el MVP, en el navegador; con cuenta, en el perfil cuando exista HU-160 (P1).
- Las señales del P1, cuando existan, también tienen peso. `excess_rain` crítico cuenta como riesgo grave de clima.
- Todo es informativo: la decisión final es del agricultor.

## Orden de las ventanas

Casi nunca hay un mes perfecto. El orden sigue el método de la FAO para aptitud de cultivos: **primero el factor que más limita, después lo que el agricultor prefiere**.

1. **Factor que más limita:** la ventana vale lo que vale su señal más baja entre las que cuentan (ley del mínimo). Una ventana con un factor muy malo nunca queda arriba, por buenos que sean los demás.
2. **Prioridades:** entre ventanas cuyo factor limitante cae en la misma decena (por ejemplo, de 60 a 69), ordena el promedio de las calificaciones ponderado por los pesos.
3. Una señal sin datos o que no aplica no califica: sale del orden y se agrega a las limitaciones (R1).
4. Una ventana con alguna señal crítica que cuenta se marca `high_risk`: va siempre después de las demás y nunca entra en `best_windows` (R2).
5. Empate: gana la ventana más temprana (R4).
6. La respuesta muestra todas las ventanas con su calificación por señal y cuál es su factor limitante, para que se vea qué gana y qué sacrifica cada una.

## Estrategias de rotación

Es el centro del producto (decisión 12). Una **estrategia** es una secuencia de 2 o 3 ciclos (`cycles`; por defecto 3) sobre un mismo terreno. Un ciclo es un cultivo, un abono verde o un descanso, con su ventana de siembra. El flujo es: lote (o municipio y área, sin cuenta) → estrategias → un ciclo con su diagnóstico → agua del plan → qué cambió.

**Cómo se arman:**

0. **Candidatas:** todas las secuencias de `cycles` ciclos con los cultivos del catálogo (cultivos, abonos verdes y descanso), sin el mismo `crop_id` en dos ciclos seguidos y sin dos descansos seguidos (decisión 15).
1. El primer ciclo se siembra en `sowing_date`. Cada ciclo siguiente se siembra el lunes siguiente a la cosecha estimada del anterior (decisión 15). Un descanso dura lo que dice su ficha.
2. Las reglas de filtro de `rotation_rules` se revisan entre cada par de ciclos seguidos y entre los cultivos anteriores del terreno y el primer ciclo. Una regla violada **excluye** la estrategia, con su motivo (R3).
3. Un ciclo con un cultivo que no es apto para la zona excluye la estrategia. Un ciclo cuya ventana es de alto riesgo por clima (`water`, `frost` o `heat` desfavorable y crítica) también: ningún otro criterio lo compensa (R2).
4. Un cultivo cuyo pH tolerado queda fuera de todo el intervalo estimado del suelo excluye la estrategia.
5. La oferta y el mercado nunca excluyen: bajan el criterio de ingreso.
6. Cada ciclo se revisa con el **mismo cálculo del diagnóstico de ventana**: sus seis señales, sus dos luces y su factor limitante. El descanso no tiene diagnóstico.

**La rotación actual (decisión 14).** La rotación que el agricultor viene haciendo (`current_crop_ids`) entra como **estrategia de referencia** (`kind = current`). El reto pide comparar al menos tres estrategias, incluida la actual.

- Se arma y se evalúa igual que las demás: mismos ciclos desde `sowing_date`, mismo diagnóstico por ciclo, mismos criterios y misma salud del suelo. Si tiene menos ciclos que `cycles`, se repite desde su primer cultivo hasta completarlos.
- **Nunca se excluye en silencio.** Si viola una regla de filtro, tiene un cultivo no apto, un pH fuera de rango o un ciclo de alto riesgo, se muestra igual, con esos motivos en `issues`: es lo que el agricultor ya hace y tiene que ver por qué no conviene (R3 sigue valiendo para las sugeridas).
- No entra al ranking (`rank` nulo), y cada estrategia sugerida dice cuánto gana o pierde frente a ella en cada criterio (`vs_current`).
- Con cuenta sale del historial del terreno (HU-165): los cultivos de las temporadas de las que viene, del más antiguo al más reciente. Sin cuenta, el agricultor la escribe. Si no hay rotación actual, no hay referencia y se agrega a las limitaciones (R1).
- Una estrategia sugerida igual a la actual no se repite.

**Cómo se ordenan.** Cuatro criterios, cada uno de 0 a 100, ponderados por las prioridades de la rotación (un peso de 0 a 5 por criterio). Son prioridades distintas de las de las señales:

| Criterio | De dónde sale |
|---|---|
| `water` (agua) | El promedio de la calificación de la señal `water` de sus ciclos con diagnóstico |
| `soil` (suelo) | Los cinco criterios de salud del suelo: `favorable` vale 100, `moderate` 50 y `unfavorable` 0; el criterio es su promedio entre los disponibles |
| `income` (ingreso) | El promedio, ciclo por ciclo, de la calificación de `supply` y de `market` que tengan dato; un abono verde o un descanso no deja cosecha y vale 0. Es el único lugar donde la oferta entra a las estrategias |
| `risk` (riesgo) | El factor que más limita entre todos sus ciclos: el menor `limiting_score` (ley del mínimo) |

Decisión 15 (antes era un supuesto de HU-082):

- `total_score` es el promedio de los criterios que califican, ponderado por las prioridades de la rotación. Con todas las prioridades de los criterios que califican en 0, la estrategia no tiene total y va al final.
- Un criterio sin datos no califica, no entra al total y se agrega a las limitaciones (R1). En `water` y `risk`, un ciclo sin dato no cuenta y se dice; si ninguno tiene, el criterio no califica. En `income`, un ciclo de cultivo sin oferta ni mercado no cuenta; si ningún ciclo de cultivo tiene, no califica.
- Hasta 10 estrategias. Empate de `total_score`: gana la de `risk` más alto y, si sigue el empate, la de `crop_ids` primero en orden alfabético (R4).
- El ranking ordena estrategias ya filtradas: nunca rescata una excluida.

**Salud del suelo (`soil_health`).** Cada estrategia trae cinco criterios. Cada uno tiene un nivel (`favorable`, `moderate`, `unfavorable`, o nulo con `insufficient_data`), su razón y la regla de `rotation_rules` que lo decide, con fuente (R8):

| Criterio | Qué mira | Con qué datos |
|---|---|---|
| `nitrogen` (nitrógeno) | Si la estrategia incluye leguminosas, que fijan nitrógeno | `fixes_nitrogen` de la ficha |
| `organic_carbon` (carbono orgánico) | Si incluye abono verde, descanso o cultivos que dejan residuos, según qué tan bajo está el carbono orgánico del suelo | Carbono orgánico de SoilGrids, del lote o del municipio |
| `soil_cover` (suelo cubierto) | Cuántos meses queda el suelo cubierto mientras dura la estrategia | La duración de cada ciclo y, cuando existe, el NDVI para contrastar |
| `pest_break` (corte de plagas) | Si una familia vuelve al mismo terreno demasiado pronto, contando los cultivos anteriores | `family` de la ficha y el historial del terreno |
| `erosion` (erosión, decisión 14) | Si la estrategia deja el suelo descubierto en un terreno con pendiente | La pendiente del lote o del municipio (NASADEM, HU-206) y los meses descubiertos de `soil_cover` |

- **No es una predicción.** No hay modelo de suelo: `soil_health` compara estrategias entre sí según reglas con fuente. Nunca dice cuánto va a mejorar el suelo, cuánto nitrógeno queda ni cuánto se va a cosechar (decisión 4). La web lo dice junto al resultado: «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo».
- Un criterio sin regla con fuente, o sin su dato (por ejemplo, sin carbono orgánico), es `insufficient_data`: no se inventa un corte ni se pinta como malo (R1, R8).
- El suelo es una estimación de 250 m y el NDVI es de la zona: se dice siempre (R10).
- Rotación de referencia con fuente: papa, avena y arveja, evaluada por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`).

## Qué cambió en la zona

Para un municipio y un cultivo, AgroSense compara **dos periodos de la misma fuente** (decisión 12): por mes, la frecuencia de heladas, la lluvia normal y la temperatura máxima (p90), y cómo se movieron las mejores ventanas de siembra del cultivo.

- **Es historia comparada, nunca pronóstico** (decisión 4). Dice cómo fue un periodo frente a otro; no dice cómo será el clima. La web lleva el rótulo «Así fue en la historia de su zona. No es un pronóstico».
- Los periodos viven en configuración versionada y la respuesta los dice (R4). Por defecto, con NASA POWER: 1981–2000 y 2005–2024. Con GPM IMERG solo hay datos desde 2000: sus periodos son más cortos (por defecto 2001–2012 y 2013–2024), y se dice.
- Los dos periodos de una comparación son de la misma fuente. Nunca se compara un periodo de una fuente con un periodo de otra.
- Sin datos suficientes en un periodo, el valor y su diferencia son `insufficient_data` (R1). Nunca se compara con un solo periodo.
- Las mejores ventanas de cada periodo salen del mismo orden de ventanas, con los pesos por defecto. Solo cambia el clima: la oferta, el mercado y el suelo son los mismos en los dos periodos, y la respuesta lo dice.
- NASA POWER es un reanálisis (un modelo con observaciones), no una observación directa: se dice junto al resultado (R8).

## Varias fuentes, ninguna única verdad

**La NASA es el núcleo (decisión 12).** Cada producto (NASA POWER, NASADEM, GPM IMERG, MODIS NDVI, SMAP) entra por su propio adaptador y publica tablas versionadas; `sources.yaml` dice qué producto calcula cada señal en cada región. Si un producto falta, la señal o el indicador es `insufficient_data` (R1). Ningún producto cambia el motor (R6).

Un indicador puede venir de varias fuentes (por ejemplo, la lluvia: GPM IMERG y NASA POWER; o la oferta: la estadística oficial del país, FAOSTAT, reportes descargados de portales públicos y las siembras registradas en AgroSense). Las fuentes **se muestran juntas para contrastarlas, nunca se mezclan en silencio** (R1, R8). Cada una dice de dónde viene, de qué fecha es y qué cubre. Una señal se calcula con la fuente que define `sources.yaml` para esa región, y la respuesta dice cuál fue.

Las siembras registradas en AgroSense solo se muestran como totales por municipio y cultivo, y nunca cuando hay menos de 5 cuentas (R9). Se toman de un corte diario versionado, para que el mismo cálculo dé el mismo resultado (R4); el consentimiento versión 3 lo dice.

## Valores permitidos

| Campo | Valores |
|---|---|
| `status` | `available`, `insufficient_data`, `not_applicable` |
| `level` | `favorable`, `moderate`, `unfavorable` o nulo |
| `light` | `green`, `yellow`, `red`, `not_evaluable` |
| `action` | `sow`, `other_window`, `rotate`, `review_data` |
| `suitability` | `suitable`, `not_suitable`, `insufficient_data` |
| `granularity` | `month`, `week` |
| `weights_basis` | `default`, `farmer` |
| `harvest_basis` | `calendar` (duración de la ficha), `normal_year` (clima de un año normal, P1) |
| `cycles` | `2`, `3` |
| Criterios de `soil_health` | `nitrogen`, `organic_carbon`, `soil_cover`, `pest_break`, `erosion`; cada uno con `status` y `level` |
| `kind` de una estrategia | `current` (la rotación actual del agricultor, la referencia), `suggested` |
| Criterios del ranking de estrategias | `water`, `soil`, `income`, `risk` |
