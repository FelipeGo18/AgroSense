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
| R9 | Los datos de la finca solo se guardan con cuenta y consentimiento | Los endpoints de cálculo (`/diagnostics`, `/rotations`, `/water-plans`, `/calendar`, `/scenarios`) no guardan los datos de la finca ni quién consultó. En el P0 no escriben nada en la base de datos. Desde HU-170 (P1) suman 1 al contador anónimo `usage_daily` (día, tipo de consulta, municipio y cultivo; sin usuario, sesión, IP, hora, fecha de siembra, prioridades ni área). Sin cuenta, los datos de la finca se envían solo para calcular y no se guardan en el servidor ni en sus logs. Con cuenta, se guardan los lotes y su historial con consentimiento registrado, solo los datos mínimos, y el usuario puede borrarlo todo. |
| R10 | El riego y el suelo son estimaciones y se dice siempre | El riego se basa en el clima de la zona, no en mediciones del lote: se muestran rangos y se pide verificar la humedad del suelo en campo. El suelo sale de un mapa global de 250 m (SoilGrids): se muestra con su rango de incertidumbre y se recomienda un análisis de suelo del lote. |

## Cómo se comprueba cada regla

| Regla | Comprobación sugerida |
|---|---|
| R1 | Prueba: una señal sin datos devuelve `insufficient_data` y `level` nulo; la web no la pinta como riesgo. |
| R2 | Prueba: una señal `unfavorable` crítica nunca da verde, aunque las otras sean `favorable`. Prueba: una helada crítica da rojo con agua y oferta favorables. Prueba: una ventana con una señal crítica queda marcada como de alto riesgo y nunca entra entre las mejores, por alto que sea su balance. |
| R3 | Prueba: una secuencia que viola un `filter` no aparece en el ranking y su exclusión cita la regla. Prueba: un cultivo que no es apto para la zona no se evalúa por ventanas y la respuesta cita el dato de su ficha que lo excluye. |
| R4 | Prueba: dos ejecuciones iguales dan salida idéntica; toda respuesta trae `versions.dataset` y `versions.rules`. |
| R5 | Revisión: ningún dato ficticio sin rótulo; cada razón de M4 mapea a un indicador o regla evaluados. |
| R6 | Prueba o lint: `backend/engine/` no importa `fastapi` ni `sqlalchemy` ni abre archivos. |
| R7 | Prueba: las uniones usan `municipality_id`; unicidad de llaves en los Parquet. Revisión: ninguna regla del motor depende de una fuente o un código propios de un país. |
| R8 | Validación: ninguna fila ni regla con `source_id` vacío o inexistente en `sources`. |
| R9 | Prueba: los endpoints de cálculo no escriben en la base de datos, salvo el contador `usage_daily` cuando existe (HU-170), que no tiene ninguna columna que identifique a una persona ni datos de la finca. Prueba: sin sesión, ningún endpoint de cuenta acepta escritura. Prueba: borrar la cuenta elimina usuario, sesiones, lotes, temporadas, tickets y sus eventos de `activity_log`. Revisión: el registro guarda el consentimiento y su versión. |
| R10 | Revisión: el rótulo de estimación aparece junto a todo resultado de riego y de suelo; se muestran rangos. Prueba: la señal de suelo nunca es crítica. |

## La ventana de siembra

Todo se evalúa sobre una **ventana de siembra**: una fecha de siembra más lo que dura ese cultivo en campo, de la siembra a la cosecha estimada. No hay semestres en la decisión: una lechuga dura dos meses y una papa cinco, y cada una se evalúa en su propio tramo.

- La duración sale de las etapas del cultivo (`crop_stages`) y, cuando hay grados-día con fuente, de la temperatura normal de la zona (el mismo cálculo de HU-150 y HU-186).
- Las ventanas se comparan por **mes** de siembra y, dentro de un mes, por **semana**.
- El semestre solo sobrevive por dentro, donde la fuente lo trae así: la oferta de EVA se lee del semestre en que cae la siembra, y la respuesta lo dice.

## Aptitud del cultivo en la zona

Antes de evaluar ventanas, el motor comprueba que el cultivo se puede dar en ese municipio. Es un filtro, no una señal (R3).

- Un cultivo **no es apto** si la altitud del municipio queda fuera de `altitude_min_m`–`altitude_max_m` de su ficha. Ejemplo: papa en un municipio de la costa.
- Si no es apto, la luz es `red`, la acción es `rotate` («este cultivo no se da en su zona: elija otro»), la razón cita el dato de la ficha y su fuente, y **no se evalúan ventanas**.
- Si la ficha no tiene ese rango con fuente, la aptitud es `insufficient_data`: no bloquea y se agrega a las limitaciones (R1, R8).
- La aptitud se decide **solo por la altitud**. Solo la altitud fuera del rango absoluto da `not_suitable`.
- `suitability.score` es una nota informativa de 0 a 100 con la curva de altitud: 100 dentro del rango óptimo (`altitude_opt_min_m`–`altitude_opt_max_m`) y 0 fuera del absoluto. No es una señal: no entra al semáforo ni al orden de las ventanas.

## Señales de una ventana

Seis señales independientes en el P0 y tres más en el P1. Ninguna se promedia con otra para decidir el semáforo (R2). Cada señal se mide **contra lo que ese cultivo necesita o aguanta**, según su ficha: un cultivo que pide poca agua rara vez sale mal en agua.

| Señal | Qué evalúa en la ventana | Puede ser crítica | Prioridad |
|---|---|---|---|
| `water` (agua) | Si la lluvia que suele caer cubre lo que el cultivo necesita en cada etapa (balance hídrico), teniendo en cuenta cuánta agua retiene el suelo según su textura (un suelo arenoso se seca antes que uno arcilloso). Con riego (`irrigated`), la falta de lluvia no es un riesgo: la señal informa cuánto riego haría falta y nunca es `unfavorable` por eso | Sí, solo sin riego | P0 |
| `frost` (heladas) | Qué tan frecuentes han sido las heladas en las semanas en que el cultivo está en una etapa sensible | Sí | P0 |
| `heat` (calor) | Si en las etapas del cultivo suelen darse temperaturas máximas por encima de lo que aguanta (`heat_max_c` de su ficha) | Sí | P0 |
| `soil` (suelo) | Si el pH del suelo de la zona, o del lote si se envía, está en el rango del cultivo. La textura entra en la señal de agua; el carbono orgánico alimenta las rotaciones | **No:** es una estimación de 250 m (R10) | P0 |
| `supply` (oferta) | Si en la zona se está sembrando mucho o poco del cultivo, según el último dato del semestre en que cae la siembra | Sí | P0 |
| `market` (mercado) | Si el precio suele estar bajo en el mes en que saldría la cosecha | Sí | P0 la señal; los datos de SIPSA son P1 |
| `excess_rain` (exceso de lluvia) | Aguaceros frecuentes que encharcan, lavan el abono o impiden las labores | Sí | P1 |
| `disease` (enfermedades por clima) | Semanas húmedas y templadas que favorecen una enfermedad con regla publicada, como la gota de la papa. No cubre plagas en general: no hay datos abiertos | No | P1 |
| `harvest_weather` (cosecha) | Si en las semanas de cosecha suele haber días secos seguidos | No | P1 |

- `frost` y `heat` son `not_applicable` cuando la ficha dice que ninguna etapa del cultivo es sensible. Sin el dato de la ficha con fuente, son `insufficient_data`.
- Una señal del P1 que todavía no existe no aparece en la respuesta: no se inventa (R5).
- El grado crítico de cada señal lo fija `thresholds.yaml`; la respuesta lo dice en el campo `critical`.
- Toda razón dice el periodo que se evaluó («en 7 de los últimos 10 años»): es historia, no pronóstico.

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
| `water` | Porcentaje de lo que el cultivo necesita que cubre la lluvia en la ventana, con la retención del suelo | `thresholds.yaml` |
| `frost` | Porcentaje de años con helada en las semanas sensibles | `thresholds.yaml` |
| `heat` | Temperatura máxima que se supera uno de cada diez días, en las etapas sensibles | Ficha (`temp_*`, `heat_max_c`) |
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
1. Si `water` u `supply` cuentan y no están disponibles, la luz es `not_evaluable` y la acción es `review_data`.
2. Si alguna señal que cuenta es `unfavorable` y crítica, o dos señales que cuentan son `unfavorable`, la luz es `red`.
3. Si ninguna señal que cuenta es `unfavorable` y `water` es `favorable` (o no cuenta), la luz es `green`.
4. En cualquier otro caso, la luz es `yellow`.
5. `frost`, `heat`, `soil`, `market` y las señales del P1 sin datos **nunca cambian la luz**, pero se agregan a las limitaciones. `not_applicable` tampoco la cambia.

«Señal que cuenta» es la que tiene peso mayor que 0, más los riesgos graves de clima, que cuentan siempre. Con riego, `water` no es `unfavorable` por falta de lluvia: es `favorable` y la razón dice cuánto riego haría falta.

Acción según la luz:

| Luz | Acción |
|---|---|
| `green` | `sow` |
| `yellow` | `rotate` si `soil`, `supply` o `market` son `unfavorable` (cambiar de fecha no los arregla); si no, `other_window` |
| `red` | `other_window` si todas las señales desfavorables son de clima (`water`, `frost`, `heat`, `excess_rain`); `rotate` si alguna es `soil`, `supply` o `market`, o si el cultivo no es apto |
| `not_evaluable` | `review_data` |

- Con `other_window`, la respuesta trae las mejores ventanas de los próximos doce meses, para que el agricultor vea cuándo sí.
- Con `rotate`, la respuesta trae `alternatives`: hasta tres cultivos aptos para la zona que en esa ventana salen bien en clima y tienen mejor oferta, con su razón. Nunca se sugiere un cultivo que no es apto o que sale mal en clima.
- La tabla de acciones mira solo las señales que cuentan con los pesos de esa luz.
- Las alternativas se ordenan igual que las ventanas (factor limitante y después prioridades). Un candidato con aptitud `insufficient_data` puede aparecer, con esa limitación; uno no apto, nunca. Se muestran si cualquiera de las dos luces da `rotate`, también cuando el cultivo consultado no es apto.
- Las prioridades se recuerdan: con cuenta, en el perfil; sin cuenta, en el navegador.
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

## Varias fuentes, ninguna única verdad

Un indicador puede venir de varias fuentes (por ejemplo, la oferta: la estadística oficial del país, FAOSTAT, reportes descargados de portales públicos y las siembras registradas en AgroSense). Las fuentes **se muestran juntas para contrastarlas, nunca se mezclan en silencio** (R1, R8). Cada una dice de dónde viene, de qué fecha es y qué cubre. Una señal se calcula con la fuente que define `sources.yaml` para esa región, y la respuesta dice cuál fue.

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
