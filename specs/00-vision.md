# Visión: Siembra Segura

## Reto

NASA Space Apps Challenge 2026 · «Field Shift: Adapting Farms with NASA Data» («Cambio de rumbo: adaptando las granjas con datos de la NASA»).

Texto oficial, leído el 11 de octubre de 2026 en <https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/>:

> «Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long-term resilience. Your challenge is to create a decision-support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.»

Una versión local del reto (sede de Moquegua, según una imagen) dice: «Crea una herramienta que combine datos satelitales, suelo y cultivos para ayudar a los agricultores a tomar mejores decisiones».

Hackatón: 14 y 15 de noviembre de 2026. Guías de entrega y de jurado: 13 de noviembre.

**Enunciado completo** (publicado el 28 de octubre, leído el 8 de noviembre de 2026 en <https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/>; decisión 14). Lo que suma al texto corto:

- **Datos de la NASA que sugiere:** SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE y GRACE-FO, y SRTM u otro modelo de elevación; nombra GEDI (biomasa) como ejemplo.
- **Qué analizar:** temperatura, estrés por calor, lluvia, humedad del suelo, evaporación, riesgo de helada, lluvias extremas, estrés de la vegetación y tendencias del agua de largo plazo.
- **Prioridades del agricultor que nombra:** uso del agua, valor como forraje, fijación de nitrógeno, menos erosión, más materia orgánica y mercado.
- **Comparar al menos tres estrategias de rotación, incluida la actual.** Para cada una: por qué se sugiere, qué evidencia la respalda, qué beneficios puede tener, dónde faltan datos y qué riesgos debe revisar el agricultor o un experto local.
- Señalar las épocas en que el campo suele quedar descubierto, cuándo los cultivos son más vulnerables y qué rotaciones cortan plagas, bajan la demanda de agua, mejoran la infiltración o suman ingreso.
- Explicar los términos (evapotranspiración, NDVI, riesgo de helada, balance hídrico) y en qué se diferencia el satélite de la medición en el campo. La IA es opcional («you may»).
- **Que apoye y no reemplace** el criterio del agricultor ni el saber agronómico local.
- **Los recursos del reto se publican el viernes 13 de noviembre** (HU-002).

### Cómo cubre el MVP cada parte del enunciado

| Parte del enunciado | Cómo la cubre el MVP | Dónde |
|---|---|---|
| NASA Earth observations | La NASA es el núcleo de los datos: NASA POWER (lluvia, temperatura, humedad del suelo modelada y ET0; es un reanálisis y se dice), NASADEM (altitud y pendiente; sale de SRTM), GPM IMERG (lluvia por satélite), MODIS NDVI (verdor), SMAP (humedad del suelo por satélite) y la capa GIBS en el mapa del lote. En P1: GRACE-FO (tendencia del agua), ECOSTRESS (calor y evapotranspiración) y Landsat (HLS, verdor a 30 m). Cada producto por su adaptador | EP-04, HU-211, HU-225, HU-226, HU-043, `docs/fuentes.md` |
| Local soil information | pH, carbono orgánico y textura de SoilGrids, del municipio o del lote dibujado, con su rango y el aviso de que es una estimación (R10) | EP-18 |
| Crop characteristics | Fichas con fuente de 7 cultivos del altiplano: altitud, temperatura, etapas sensibles a la helada, Kc por etapa, duración, pH, familia, tipo de raíz y reglas de rotación entre ellos | EP-06, HU-142 |
| Farmer priorities | Dos juegos de pesos de 0 a 5: los de la rotación (agua, suelo, ingreso y riesgo) y los de las señales de cada ventana. Si su criterio da otra luz que el de AgroSense, se muestran las dos | HU-101, HU-202, HU-074 |
| Explore rotation strategies | Es la entrada del producto: estrategias de rotación de hasta 3 ciclos, comparadas lado a lado **contra la rotación que el agricultor ya hace** (al menos tres, incluida la actual), con las descartadas y su motivo | EP-08, EP-10, HU-223 |
| Strengthen soil health | Cada estrategia trae su salud del suelo con cinco criterios por reglas con fuente: nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión (con la pendiente de NASADEM). Es una comparación entre estrategias, no una predicción de cuánto mejora el suelo | HU-212, HU-224 |
| Adapt to changing conditions | «Qué cambió en su zona»: dos periodos de la misma fuente (1981–2000 y 2005–2024 con POWER), por mes, y cómo se movieron las mejores ventanas del cultivo. Es historia comparada, nunca pronóstico | HU-216 a HU-219 |
| Presión: temperatura | Señales de heladas y de calor de cada ciclo; temperatura corregida por altitud | HU-077, HU-190 |
| Presión: lluvia | Señal de agua con la lluvia de IMERG o de POWER y el balance hídrico por etapa | HU-071, HU-144 |
| Presión: escasez de agua | El agua del plan de cada ciclo: déficit mensual y volumen, en año normal y año seco, con o sin riego | HU-144, HU-146, HU-215 |
| Presión: extremos | El riesgo grave de clima (agua, helada o calor críticos) cuenta siempre y descarta la estrategia que lo tiene | HU-074, HU-081 |
| Presión: deterioro del suelo | La salud del suelo de cada estrategia, con abonos verdes y descanso como ciclos | HU-212, HU-063 |
| Por qué, evidencia, beneficios, vacíos y riesgos de cada estrategia | Razones de plantillas que citan la regla o el indicador evaluado (R5), limitaciones y «datos insuficientes» (R1), la fuente de cada regla (R8) y el rótulo «La decisión es suya» | HU-083, HU-102 |
| Prioridades: forraje | El valor como forraje en la ficha del cultivo (P1) | HU-227 |
| IA («SI», opcional) | Reglas con fuente y explicables, no aprendizaje automático (decisión 4): la entrega explica por qué | HU-132 |

**La sede y la región todavía no están confirmadas.** Si la sede del equipo es Moquegua (Perú), hay que decidir si la región piloto pasa a la región de la sede. Hasta entonces, la región piloto es el altiplano colombiano, como supuesto (decisión 11, HU-002). Lo propio de Colombia vive en los adaptadores de cada fuente.

## Problema

Quien siembra decide qué cultivar y cuándo con información dispersa y con un clima que cambia. Repetir el mismo cultivo en el mismo lote desgasta el suelo y acumula plagas; el agua es cada vez menos predecible; y las fechas que servían antes ya no siempre sirven. Elegir una rotación que cuide el suelo, ahorre agua y aguante el clima es difícil sin datos. Además, nadie sabe cuánto están sembrando los demás en su zona.

## Idea

Una herramienta web, usable desde el celular, que con datos de la NASA, el suelo de la zona y reglas explicables ayuda a **explorar estrategias de rotación**. El flujo principal del MVP es:

**lote (o municipio y área, sin cuenta) → estrategias de rotación de 3 ciclos → un ciclo con su diagnóstico de ventana → agua del plan → qué cambió.**

1. **Estrategias de rotación:** secuencias de hasta 3 ciclos (cultivos, abonos verdes y descanso) que cumplen las reglas agronómicas, se dan en la zona y no tienen ningún ciclo de alto riesgo de clima. Se ordenan según las prioridades del agricultor (agua, suelo, ingreso y riesgo) y cada una dice cómo cuida el suelo con cinco criterios: nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión. Todas se comparan contra la rotación que el agricultor ya hace (decisión 14). Es una comparación según reglas con fuente, no una predicción de cuánto mejora el suelo.
2. **Diagnóstico de cada ciclo:** primero dice si el cultivo se da en esa zona (por la temperatura media anual, decisión 13). Si se da, evalúa su **ventana de siembra** (de la siembra a la cosecha estimada) con un semáforo (verde, amarillo, rojo o no evaluable) construido con seis señales: agua, heladas, calor, suelo, oferta y mercado. Cada señal se califica de 0 a 100 contra lo que ese cultivo necesita o aguanta. El agricultor puede decir qué le importa más; si su criterio da otra luz que el de AgroSense, se muestran las dos. Si la fecha no conviene, muestra las mejores ventanas de los próximos doce meses. El diagnóstico sigue disponible como consulta suelta.
3. **Agua del plan:** cuánta agua necesitará cada ciclo, mes a mes, y en qué meses es probable regar o la lluvia no alcanza. Es una estimación (R10).
4. **Qué cambió en su zona:** cómo cambiaron las heladas, la lluvia y el calor de cada mes entre dos periodos de la historia de la zona, y cómo se movieron las mejores fechas de siembra del cultivo. Es historia comparada, no un pronóstico.

La oferta (cuánto se está sembrando en la zona) es un **valor agregado, no el protagonista**: es una de las seis señales, con su peso, y en las estrategias entra solo por el criterio de ingreso.

Casi nunca hay un mes perfecto, y cada cultivo dura distinto. Por eso la decisión se evalúa por ventana de siembra, no por periodos fijos del año. Las ventanas se ordenan primero por lo que más limita a cada una y después por lo que prefiere el agricultor. Es historia de la zona, no un pronóstico: decide el agricultor. El riesgo grave de clima (agua, helada o calor críticos) cuenta siempre, aunque el agricultor diga que no le importa.

Ningún dato tiene una única fuente de verdad: cuando un indicador viene de varias fuentes (por ejemplo, la lluvia de GPM IMERG y la de NASA POWER), se muestran juntas para contrastarlas y nunca se mezclan.

Sin cuenta se puede consultar por municipio, área y cultivo anterior. Con cuenta, el agricultor dibuja sus lotes en el mapa, sobre la imagen satelital de la NASA, registra sus temporadas, y las estrategias usan lo que de verdad sembró y el suelo de su lote.

## Usuarios

Pequeños y medianos productores, y técnicos o asesores agropecuarios que los acompañan. El jurado del reto es también un usuario del producto: debe entenderlo y poder verificarlo en pocos minutos.

## Cómo funciona

| Paso | Qué hace | Dónde se especifica |
|---|---|---|
| 1. Elegir el contexto | Con cuenta, abre su lote. Sin cuenta: municipio, área, qué había antes, cuándo sembrar y si tiene riego | EP-10 (HU-214), EP-16 |
| 2. Ver las estrategias de rotación | Hasta 3 ciclos por estrategia, ordenadas por sus prioridades, con su salud del suelo, sus razones y las descartadas con su motivo | EP-08, EP-10 (HU-102), EP-18 (HU-212) |
| 3. Revisar un ciclo | El diagnóstico de su ventana: aptitud, semáforo con sus prioridades y con las de AgroSense, señales calificadas, lo que más limita, razones, fuentes y limitaciones | EP-07, EP-09, EP-10 (HU-215) |
| 4. Ver el agua del plan | Déficit mensual y volumen del ciclo, en año normal y año seco, con la humedad del suelo de la zona para contrastar | EP-14 (HU-144, HU-146) |
| 5. Ver qué cambió | Dos periodos de la historia de la zona y cómo se movieron las mejores ventanas | EP-04 (HU-216), EP-07 (HU-217, HU-218), EP-09 (HU-219) |
| 6. Volver a su finca | Con cuenta: sus lotes en el mapa, su suelo y sus temporadas | EP-16 |

### Las seis señales de una ventana

| Señal | Qué mide | Fuente prevista | Indicador clave |
|---|---|---|---|
| Agua (`water`) | Si la lluvia que suele caer cubre lo que el cultivo necesita en cada etapa, según cuánta agua retiene el suelo por su textura. Con riego, la falta de lluvia no es un riesgo | Lluvia de GPM IMERG o de NASA POWER (la que diga `sources.yaml`); ET0 de POWER por Penman-Monteith; Kc y etapas de FAO-56; textura de SoilGrids. La humedad del suelo de POWER y de SMAP, para contrastar | `water_deficit_mm` |
| Heladas (`frost`) | Qué tan seguido ha helado en los meses en que el cultivo está en una etapa sensible | NASA POWER, corregida por altitud con NASADEM | `frost_freq_pct` |
| Calor (`heat`) | Si suelen darse temperaturas máximas por encima de lo que el cultivo aguanta | NASA POWER, corregida por altitud; ficha del cultivo | `tmax_p90_c` frente a `heat_max_c` |
| Suelo (`soil`) | Si el pH está en el rango del cultivo (estimación); la textura entra en la señal de agua y el carbono orgánico alimenta la salud del suelo de las estrategias | SoilGrids (ISRIC) | `ph` |
| Oferta (`supply`) | Si en la zona se está sembrando mucho o poco de ese cultivo, según el semestre de EVA en que cae la siembra. Es valor agregado: una señal más, con su peso | EVA / UPRA en la región piloto; en P1, fuentes de contraste | `planted_change_pct`, `dept_share_pct` |
| Mercado (`market`) | Si el precio suele estar bajo en el mes en que saldría la cosecha | SIPSA / DANE (por confirmar, P1) | `seasonal_index` |

En el P1 se suman tres señales: exceso de lluvia (`excess_rain`), enfermedades por clima con regla publicada (`disease`) y clima de cosecha (`harvest_weather`).

Cada señal se califica de 0 a 100 con una curva por cultivo (100 en su óptimo, 0 fuera de sus límites) y el nivel sale de esa calificación. El semáforo se decide por reglas, nunca por un promedio (R2). Si una señal no tiene datos, sale como «datos insuficientes» con su razón. No se rellena ni se sustituye (R1). Antes de las señales va la **aptitud**: un cultivo cuya ficha dice que no se da a la altitud del lote o del municipio se descarta con su motivo (R3). Detalle en `specs/01-reglas.md`.

## Impacto esperado (potencial, no garantizado)

El impacto se presenta como **potencial**: la herramienta apoya decisiones, no garantiza resultados.

- **Ambiental:** una rotación válida, con leguminosas, abonos verdes y descanso, reduce el desgaste del suelo y la acumulación de plagas, y el agua del plan apoya un uso más racional del recurso.
- **Social:** pone al alcance de pequeños productores datos de la NASA y del suelo que hoy están dispersos, desde el celular y en palabras sencillas.
- **Económico:** ayuda a elegir fechas y cultivos con menos riesgo de clima y, como valor agregado, avisa si en la zona se está sembrando mucho de un cultivo. No promete mayores ingresos.

## Qué NO es

- No predice rendimiento ni precio futuro. No hay modelo de aprendizaje automático; es riesgo histórico explicable.
- La salud del suelo de una estrategia no es una predicción de cuánto mejora el suelo: no hay modelo de suelo. Compara estrategias según reglas con fuente.
- «Qué cambió» no es un pronóstico de cambio climático: compara dos periodos del pasado de la zona.
- El orden de las ventanas de siembra no es un pronóstico ni una orden: dice cómo le ha ido a cada época en la historia de la zona. La misma fecha en otro año da el mismo resultado de clima.
- No sustituye la asesoría técnica agropecuaria.
- El agua del plan es una **estimación** con el clima de la zona, no una medición del lote; el suelo es una estimación de un mapa global de 250 m, no un análisis del lote; y la humedad del suelo y el verdor son datos de la zona, no del lote (R10).
- NASA POWER es un reanálisis (un modelo con observaciones), no una observación directa: se dice.
- Con pocos datos (EVA desde 2019, dos semestres por año) las tendencias de oferta son poco robustas: se habla de señales e historial, y se marca la calidad `partial` cuando corresponde.

## Alcance: MVP (P0) frente a ideal (P1)

**P0 es el MVP** (decisión 12, 11 de octubre de 2026): lo que sirve al flujo principal. Todo lo demás pasó a P1 y solo entra si el MVP está completo y los casos de prueba pasan en la hora 34 del evento.

| Dimensión | MVP (P0) | Ideal (P1) |
|---|---|---|
| Región | Una región piloto con buena cobertura en EVA, por ejemplo el altiplano de Cundinamarca o Boyacá. **Supuesto** hasta confirmar la sede y el enunciado del 28 de octubre (HU-002) | Una segunda región con otro piso térmico |
| Cultivos | 7 cultivos del altiplano con ficha completa y con fuente: papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia (abono verde); más el descanso | Más cultivos y variedades |
| Estrategias de rotación | Hasta 3 ciclos (2 o 3), con filtros entre ciclos, 4 criterios de puntuación (agua, suelo, ingreso y riesgo) y la salud del suelo con 4 criterios por reglas con fuente | Rotaciones ponderadas por el área de cada cultivo |
| Diagnóstico de un ciclo | Aptitud por altitud; seis señales calificadas de 0 a 100; con y sin riego; prioridades del agricultor con las dos luces cuando difieren; mejores ventanas de los próximos doce meses, por mes | Cultivos alternativos cuando conviene rotar; ventanas por semana; tres señales más: exceso de lluvia, enfermedades por clima y clima de cosecha |
| Datos de la NASA | NASA POWER ampliado (lluvia, temperatura, humedad del suelo modelada, y radiación, viento y humedad para la ET0 por Penman-Monteith), NASADEM (altitud), GPM IMERG (lluvia por satélite), MODIS NDVI por municipio y por lote, SMAP (humedad del suelo) y la capa GIBS en el mapa. Orden de recorte: SMAP, GIBS, NDVI por lote | NDVI por lote a 30 m (HLS); riesgo climático por semana; aguaceros, ventanas secas y gota; lo que recomiende el enunciado y no alcance a entrar |
| Suelo | pH, carbono orgánico y textura de SoilGrids por municipio y por lote dibujado | Contraste con los estudios de suelos del IGAC |
| Qué cambió | Dos periodos de la misma fuente, por mes: heladas, lluvia y temperatura máxima, y las mejores ventanas de cada periodo | Lluvia en años de El Niño y La Niña |
| Agua | El agua del plan de cada ciclo: déficit mensual y volumen, en año normal y año seco | Finca temporal con varios cultivos; calendario de riego de la finca; aviso de riego semanal |
| Oferta | EVA por municipio, cultivo y semestre, como una señal más y dentro del criterio de ingreso | Fuentes de contraste mostradas junto a EVA: FAOSTAT, reportes de portales y siembras registradas en AgroSense (solo totales, con al menos 5 cuentas) |
| Mercado | Señal «datos insuficientes» con razón explícita, o SIPSA si se confirma a tiempo | SIPSA con índice estacional de precio por producto |
| Selección de zona | Buscador de municipios | Mapa de la región coloreado por semáforo |
| Calendario | No entra: las mejores ventanas están en el diagnóstico y en las estrategias | Calendario completo por mes y por semana, línea de tiempo y seguimiento de lo ya sembrado; etapa por temperatura acumulada |
| Cuentas | Mínimas: registro, entrar, salir, consentimiento y borrar la cuenta; lotes con polígono y su suelo; temporadas; Mi finca con una zona | Editar perfil y contraseña; restaurar lo borrado; progreso; trazabilidad y Mi actividad; varias zonas; roles de administrador; recuperar la contraseña |
| Web | 2D (modo ligero por defecto), con el kit visual y la mascota estática; pantalla de inicio sin 3D | Escena 3D, descenso de cámara, sistema de motion, animaciones de la mascota, lote vivo, audio |
| Ambiente en vivo | No entra | Día y noche, lluvia, nubes y viento aproximados en la escena |
| Escenarios | No entran | Lluvia y área sembrada con comparación contra el caso base |
| Despliegue | La app (API y web) y PostgreSQL con Docker Compose, y un video de respaldo | Igual |

## Decisiones de arquitectura

Resumen en `CLAUDE.md`; explicación en lenguaje sencillo en `docs/decisiones.md`.
