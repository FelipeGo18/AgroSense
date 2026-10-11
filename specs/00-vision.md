# Visión: Siembra Segura

## Reto

NASA Space Apps Challenge 2026 · «Cambio de rumbo: adaptando las granjas con datos de la NASA». Los agricultores enfrentan cambios de temperatura, variaciones en la lluvia, escasez de agua, fenómenos extremos y deterioro del suelo. El reto pide usar datos de la NASA para ayudar a tomar mejores decisiones.

Hackatón: 14 y 15 de noviembre de 2026. Enunciados completos: 28 de octubre. Guías de entrega y de jurado: 13 de noviembre.

## Problema

Quien siembra decide qué cultivar y cuándo con información dispersa: un clima que cambia y sin saber cuánto están sembrando los demás en su zona. Si muchos siembran lo mismo en la misma ventana, la oferta puede saturar el mercado; si pocos lo hacen, se pierde una oportunidad que nadie ve. Además, repetir el mismo cultivo en el mismo lote desgasta el suelo y acumula plagas, y el agua es cada vez menos predecible.

## Idea

Una herramienta web, usable desde el celular, que con datos abiertos y reglas explicables responde:

1. **Diagnóstico de ventana:** para un municipio, un cultivo y una fecha de siembra, primero dice si el cultivo se da en esa zona. Si se da, evalúa la **ventana de siembra** (de la siembra a la cosecha estimada de ese cultivo) con un semáforo (verde, amarillo, rojo o no evaluable) construido con seis señales: agua, heladas, calor, suelo, oferta y mercado. Cada señal se califica de 0 a 100 contra lo que ese cultivo necesita o aguanta, al estilo del método de aptitud de cultivos de la FAO. El agricultor puede decir qué le importa más (un peso de 0 a 5 por señal); si su criterio da otra luz que el de AgroSense, se muestran las dos. Cada resultado explica sus razones y sus limitaciones; si la fecha no conviene, muestra las mejores ventanas de los próximos doce meses, y si conviene cambiar de cultivo, sugiere cultivos que en esa ventana salen bien en clima y tienen mejor oferta.
2. **Rotaciones:** qué sembrar después, como ranking de secuencias agronómicamente válidas y aptas para la zona, ordenado según las prioridades del agricultor (agua, suelo, ingreso y riesgo), con el suelo de su zona o de su lote, e incluyendo abonos verdes y descanso para recuperar el suelo. Es el centro del reto («Field Shift»).
3. **Finca, calendario y plan de agua:** las ventanas de siembra de los próximos doce meses, por mes y por semana, ordenadas según lo que más le importa al agricultor; mes a mes, cuándo vigilar heladas y calor en lo ya sembrado; y, con el porcentaje de la finca que ocupa cada cultivo, cuánta agua hará falta y en qué meses es probable regar.

Casi nunca hay un mes perfecto, y cada cultivo dura distinto: una lechuga dura dos meses y una papa cinco. Por eso la decisión se evalúa por ventana de siembra, no por periodos fijos del año. Las ventanas se ordenan primero por lo que más limita a cada una y después por lo que prefiere el agricultor, y se muestra qué gana y qué sacrifica cada una. Es historia de la zona, no un pronóstico: decide el agricultor. El riesgo grave de clima (agua, helada o calor críticos) cuenta siempre, aunque el agricultor diga que no le importa.

Ningún dato tiene una única fuente de verdad: cuando un indicador viene de varias fuentes (por ejemplo, la estadística oficial y las siembras registradas en AgroSense), se muestran juntas para contrastarlas y nunca se mezclan.

Sin cuenta se puede consultar. Con cuenta, el agricultor registra uno o varios lotes en una o varias zonas, los divide y junta por partes como trabaja, y al volver encuentra su historial y su progreso; las rotaciones usan lo que de verdad sembró. La escena refleja el clima aproximado de ahora en su municipio, como ambiente.

**La región todavía no está confirmada.** El reto no ha dicho qué datos ni qué región (sale el 28 de octubre, HU-002). Colombia es un supuesto: el P0 se prepara con una región piloto colombiana y lo propio de Colombia vive en los adaptadores de cada fuente (decisión 11).

## Usuarios

Pequeños y medianos productores, y técnicos o asesores agropecuarios que los acompañan. El jurado del reto es también un usuario del producto: debe entenderlo y poder verificarlo en pocos minutos.

## Cómo funciona

| Paso | Qué hace | Dónde se especifica |
|---|---|---|
| 1. Elegir el contexto | Municipio, cultivo, cuándo sembrar (mes o semana), si hay riego y, si quiere, sus prioridades, entre opciones válidas | EP-09 |
| 2. Saber si el cultivo se da en la zona | Aptitud por altitud. Si no es apto, la respuesta lo dice con su razón y ofrece elegir otro cultivo; no se evalúan ventanas | EP-07 (HU-191), EP-09 |
| 3. Ver el diagnóstico de la ventana | Semáforo con sus prioridades y, si difiere, el de AgroSense; acción sugerida, señales calificadas, lo que más limita, razones, fuentes y limitaciones; con «otra ventana», las mejores de los próximos doce meses; con «rotar», cultivos alternativos | EP-07, EP-09 |
| 4. Comparar ventanas | Las ventanas por mes y por semana, ordenadas primero por el factor que más limita y después por las prioridades del agricultor; las de alto riesgo, aparte | EP-07 (HU-192), EP-14 |
| 5. Planear la siguiente siembra | Rotaciones y plan de agua de la finca | EP-08, EP-10, EP-14 |
| 6. Volver a su finca | Con cuenta: sus lotes, su historial y su progreso | EP-16 |

### Las seis señales de una ventana

| Señal | Qué mide | Fuente prevista | Indicador clave |
|---|---|---|---|
| Agua (`water`) | Si la lluvia que suele caer cubre lo que el cultivo necesita en cada etapa, según cuánta agua retiene el suelo por su textura. Con riego, la falta de lluvia no es un riesgo | NASA POWER (por punto, comunidad AG), Kc y etapas de FAO-56, textura de SoilGrids | `water_deficit_mm` |
| Heladas (`frost`) | Qué tan seguido ha helado en las semanas en que el cultivo está en una etapa sensible | NASA POWER, corregida por altitud | `frost_freq_pct` |
| Calor (`heat`) | Si suelen darse temperaturas máximas por encima de lo que el cultivo aguanta | NASA POWER, corregida por altitud; ficha del cultivo | `tmax_p90_c` frente a `heat_max_c` |
| Suelo (`soil`) | Si el pH está en el rango del cultivo (estimación); la textura entra en la señal de agua y el carbono orgánico alimenta las rotaciones | SoilGrids (ISRIC) | `ph` |
| Oferta (`supply`) | Si en la zona se está sembrando mucho o poco de ese cultivo, según el semestre de EVA en que cae la siembra. Cambia el semáforo como las demás | EVA / UPRA en la región piloto; en P1, fuentes de contraste (FAOSTAT, reportes de portales y siembras registradas en AgroSense) | `planted_change_pct`, `dept_share_pct` |
| Mercado (`market`) | Si el precio suele estar bajo en el mes en que saldría la cosecha | SIPSA / DANE (por confirmar, P1) | `seasonal_index` |

En el P1 se suman tres señales: exceso de lluvia (`excess_rain`), enfermedades por clima con regla publicada (`disease`) y clima de cosecha (`harvest_weather`).

Cada señal se califica de 0 a 100 con una curva por cultivo (100 en su óptimo, 0 fuera de sus límites) y el nivel sale de esa calificación. El semáforo se decide por reglas, nunca por un promedio (R2). Si una señal no tiene datos, sale como «datos insuficientes» con su razón. No se rellena ni se sustituye (R1). Antes de las señales va la **aptitud**: un cultivo cuya ficha dice que no se da a la altitud del municipio se descarta con su motivo (R3). Detalle en `specs/01-reglas.md`.

## Impacto esperado (potencial, no garantizado)

El impacto se presenta como **potencial**: la herramienta apoya decisiones, no garantiza resultados.

- **Económico:** ayuda a evitar sembrar en una ventana saturada y a identificar ventanas con menos competencia, lo que podría reducir el riesgo de vender por debajo del costo. No promete mayores ingresos.
- **Social:** pone al alcance de pequeños productores información que hoy está dispersa, desde el celular. Saber cuánto y qué se está sembrando en la zona es información colectiva útil para coordinar y no sembrar todos lo mismo.
- **Ambiental:** la rotación válida reduce el desgaste del suelo y la acumulación de plagas, y el plan de agua apoya un uso más racional del recurso.

## Qué NO es

- No predice rendimiento ni precio futuro. No hay modelo de aprendizaje automático; es riesgo histórico explicable.
- El orden de las ventanas de siembra no es un pronóstico ni una orden: dice cómo le ha ido a cada época en la historia de la zona. La misma fecha en otro año da el mismo resultado de clima.
- No sustituye la asesoría técnica agropecuaria.
- El plan de riego es una **estimación** con el clima de la zona, no una medición del lote, y el suelo es una estimación de un mapa global de 250 m, no un análisis del lote (R10).
- El clima en vivo de la escena es una condición aproximada de ahora, no un pronóstico, y no entra en ninguna decisión.
- Con pocos datos (EVA desde 2019, dos semestres por año) las tendencias son poco robustas: se habla de señales e historial, y se marca la calidad `partial` cuando corresponde.

## Alcance: viable (P0) frente a ideal (P1)

El escenario viable (P0) es el que se compromete. El ideal (P1) solo entra si el viable está completo y los casos de prueba pasan en la hora 34 del evento.

| Dimensión | Viable (P0) | Ideal (P1) |
|---|---|---|
| Región | Una región piloto con buena cobertura en EVA, por ejemplo el altiplano de Cundinamarca o Boyacá. **Supuesto** hasta que el enunciado del 28 de octubre confirme región y datos (HU-002) | Una segunda región con otro piso térmico |
| Cultivos | Papa y 5 a 7 cultivos de rotación de la misma región | Más cultivos y variedades |
| Decisión | Aptitud del cultivo en la zona por altitud; diagnóstico de una ventana de siembra con seis señales calificadas de 0 a 100 (agua, heladas, calor, suelo, oferta y mercado); con y sin riego; prioridades del agricultor con las dos luces cuando difieren; mejores ventanas de los próximos doce meses; cultivos alternativos cuando conviene rotar | Tres señales más: exceso de lluvia, enfermedades por clima con regla publicada y clima de cosecha |
| Clima (NASA) | Precipitación y temperatura diarias por centroide municipal (NASA POWER, por punto), corregidas por altitud; lluvia y ET0 mensuales; frecuencia de heladas y temperatura máxima por mes y por semana | Humedad del suelo (SMAP) y vegetación (NDVI) por polígono; aguaceros, ventanas secas y gota en el calendario |
| Suelo | pH, carbono orgánico y textura de SoilGrids por municipio y por lote dibujado | Contraste con los estudios de suelos del IGAC |
| Oferta | EVA por municipio, cultivo y semestre (el único dato que va por semestre; se lee el semestre en que cae la siembra) | Fuentes de contraste mostradas junto a EVA: FAOSTAT, reportes de portales y siembras registradas en AgroSense (solo totales, con al menos 5 cuentas) |
| Mercado | Señal «datos insuficientes» con razón explícita, o SIPSA si se confirma a tiempo | SIPSA con índice estacional de precio por producto |
| Selección de zona | Buscador de municipios | Mapa de la región coloreado por semáforo |
| Rotaciones | Secuencias de 2 ciclos con 4 criterios de puntuación, filtro y criterio de suelo, abonos verdes y descanso | 3 ciclos |
| Finca y agua | Sin cuenta, una finca temporal con el porcentaje del área por cultivo; con cuenta, sus lotes. Plan de agua mensual estimado: déficit y volumen por cultivo, en año normal y año seco | Aviso de riego semanal con la lluvia más reciente y rotaciones ponderadas por el área de cada cultivo |
| Escenarios | No entran | Lluvia y área sembrada con comparación contra el caso base |
| Calendario | Por cultivo y municipio: las ventanas de siembra por mes y por semana, ordenadas por el factor que más limita y después por las prioridades del agricultor, con las de alto riesgo aparte; para lo ya sembrado, etapa, heladas y calor a vigilar mes a mes | Cuándo abonar, días para labores y cosecha, gota y cuándo vender |
| Cuentas | Registro con usuario y contraseña, varios lotes dibujados en el mapa y zonas, partes que se dividen y se juntan, historial de temporadas con lo borrado para restaurar, progreso, trazabilidad y borrado de la cuenta | Recuperar la contraseña; roles de administrador |
| Ambiente en vivo | Día y noche, lluvia, nubes y viento aproximados en la escena | Imagen satelital del día (NASA GIBS) |
| Despliegue | La app (API y web) y PostgreSQL con Docker Compose, y un video de respaldo | Igual |

## Decisiones de arquitectura

Resumen en `CLAUDE.md`; explicación en lenguaje sencillo en `docs/decisiones.md`.
