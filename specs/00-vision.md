# Visión: Siembra Segura

## Reto

NASA Space Apps Challenge 2026 · «Cambio de rumbo: adaptando las granjas con datos de la NASA». Los agricultores enfrentan cambios de temperatura, variaciones en la lluvia, escasez de agua, fenómenos extremos y deterioro del suelo. El reto pide usar datos de la NASA para ayudar a tomar mejores decisiones.

Hackatón: 14 y 15 de noviembre de 2026. Enunciados completos: 28 de octubre. Guías de entrega y de jurado: 13 de noviembre.

## Problema

Quien siembra decide qué cultivar y cuándo con información dispersa: un clima que cambia y sin saber cuánto están sembrando los demás en su zona. Si muchos siembran lo mismo en la misma ventana, la oferta puede saturar el mercado; si pocos lo hacen, se pierde una oportunidad que nadie ve. Además, repetir el mismo cultivo en el mismo lote desgasta el suelo y acumula plagas, y el agua es cada vez menos predecible.

## Idea

Una herramienta web, usable desde el celular, que con datos abiertos y reglas explicables responde:

1. **Diagnóstico de ventana:** para un municipio, un cultivo y un semestre, un semáforo (verde, amarillo, rojo o no evaluable) construido con cinco señales: lluvia, heladas, suelo, oferta y mercado. Cada resultado explica sus razones y sus limitaciones.
2. **Rotaciones:** qué sembrar después, como ranking de secuencias agronómicamente válidas, ordenado según las prioridades del agricultor (agua, suelo, ingreso y riesgo), con el suelo de su zona o de su lote, e incluyendo abonos verdes y descanso para recuperar el suelo. Es el centro del reto («Field Shift»).
3. **Finca, calendario y plan de agua:** mes a mes, cuándo conviene sembrar y cuándo hay riesgo de helada; con el porcentaje de la finca que ocupa cada cultivo, cuánta agua hará falta y en qué meses es probable regar.

Sin cuenta se puede consultar. Con cuenta, el agricultor registra uno o varios lotes en una o varias zonas, y al volver encuentra su historial y su progreso; las rotaciones usan lo que de verdad sembró. La escena refleja el clima aproximado de ahora en su municipio, como ambiente.

## Usuarios

Pequeños y medianos productores, y técnicos o asesores agropecuarios que los acompañan. El jurado del reto es también un usuario del producto: debe entenderlo y poder verificarlo en pocos minutos.

## Cómo funciona

| Paso | Qué hace | Dónde se especifica |
|---|---|---|
| 1. Elegir el contexto | Municipio, cultivo y semestre entre opciones válidas | EP-09 |
| 2. Ver el diagnóstico | Semáforo, acción sugerida, señales, razones y limitaciones | EP-07, EP-09 |
| 3. Planear la siguiente siembra | Rotaciones y plan de agua de la finca | EP-08, EP-10, EP-14 |
| 4. Volver a su finca | Con cuenta: sus lotes, su historial y su progreso | EP-16 |

### Las cinco señales

| Señal | Qué mide | Fuente prevista | Indicador clave |
|---|---|---|---|
| Lluvia | Si la lluvia de la ventana ha sido favorable | NASA POWER (por punto, comunidad AG) | `precip_anomaly_pct` |
| Heladas | Qué tan seguido ha helado en las etapas sensibles del cultivo | NASA POWER, corregida por altitud | `frost_freq_pct` |
| Suelo | Si el pH está en el rango del cultivo (estimación); la textura y el carbono orgánico se muestran y alimentan las rotaciones | SoilGrids (ISRIC) | `ph` |
| Oferta | Si en la zona se está sembrando mucho o poco de ese cultivo | EVA / UPRA | `planted_change_pct`, `dept_share_pct` |
| Mercado | Si el precio suele bajar cuando sale la cosecha | SIPSA / DANE (por confirmar, P1) | `seasonal_index` |

Si una señal no tiene datos, sale como «datos insuficientes» con su razón. No se rellena ni se sustituye (R1).

## Impacto esperado (potencial, no garantizado)

El impacto se presenta como **potencial**: la herramienta apoya decisiones, no garantiza resultados.

- **Económico:** ayuda a evitar sembrar en una ventana saturada y a identificar ventanas con menos competencia, lo que podría reducir el riesgo de vender por debajo del costo. No promete mayores ingresos.
- **Social:** pone al alcance de pequeños productores información que hoy está dispersa, desde el celular. Saber cuánto y qué se está sembrando en la zona es información colectiva útil para coordinar y no sembrar todos lo mismo.
- **Ambiental:** la rotación válida reduce el desgaste del suelo y la acumulación de plagas, y el plan de agua apoya un uso más racional del recurso.

## Qué NO es

- No predice rendimiento ni precio futuro. No hay modelo de aprendizaje automático; es riesgo histórico explicable.
- No sustituye la asesoría técnica agropecuaria.
- El plan de riego es una **estimación** con el clima de la zona, no una medición del lote, y el suelo es una estimación de un mapa global de 250 m, no un análisis del lote (R10).
- El clima en vivo de la escena es una condición aproximada de ahora, no un pronóstico, y no entra en ninguna decisión.
- Con pocos datos (EVA desde 2019, dos semestres por año) las tendencias son poco robustas: se habla de señales e historial, y se marca la calidad `partial` cuando corresponde.

## Alcance: viable (P0) frente a ideal (P1)

El escenario viable (P0) es el que se compromete. El ideal (P1) solo entra si el viable está completo y los casos de prueba pasan en la hora 34 del evento.

| Dimensión | Viable (P0) | Ideal (P1) |
|---|---|---|
| Región | Una región piloto con buena cobertura en EVA, por ejemplo el altiplano de Cundinamarca o Boyacá | Una segunda región con otro piso térmico |
| Cultivos | Papa y 5 a 7 cultivos de rotación de la misma región | Más cultivos y variedades |
| Clima (NASA) | Precipitación y temperatura diarias por centroide municipal (NASA POWER, por punto), corregidas por altitud; frecuencia de heladas por mes | Humedad del suelo (SMAP) y vegetación (NDVI) por polígono; aguaceros, ventanas secas y gota en el calendario |
| Suelo | pH, carbono orgánico y textura de SoilGrids por municipio y por lote dibujado | Contraste con los estudios de suelos del IGAC |
| Oferta | EVA por municipio, cultivo y semestre | Igual, con más años y cultivos |
| Mercado | Señal «datos insuficientes» con razón explícita, o SIPSA si se confirma a tiempo | SIPSA con índice estacional de precio por producto |
| Selección de zona | Buscador de municipios | Mapa de la región coloreado por semáforo |
| Rotaciones | Secuencias de 2 ciclos con 4 criterios de puntuación, filtro y criterio de suelo, abonos verdes y descanso | 3 ciclos |
| Finca y agua | Sin cuenta, una finca temporal con el porcentaje del área por cultivo; con cuenta, sus lotes. Plan de agua mensual estimado: déficit y volumen por cultivo, en año normal y año seco | Aviso de riego semanal con la lluvia más reciente y rotaciones ponderadas por el área de cada cultivo |
| Escenarios | No entran | Lluvia y área sembrada con comparación contra el caso base |
| Calendario | Por cultivo y municipio: mejores meses de siembra y riesgo de helada mes a mes | Cuándo abonar, días para labores y cosecha, y gota |
| Cuentas | Registro con usuario y contraseña, varios lotes dibujados en el mapa y zonas, historial de temporadas, progreso, trazabilidad y borrado de la cuenta | Recuperar la contraseña; roles de administrador |
| Ambiente en vivo | Día y noche, lluvia, nubes y viento aproximados en la escena | Imagen satelital del día (NASA GIBS) |
| Despliegue | La app (API y web) y PostgreSQL con Docker Compose, y un video de respaldo | Igual |

## Decisiones de arquitectura

Resumen en `CLAUDE.md`; explicación en lenguaje sencillo en `docs/decisiones.md`.
