# Guion de la demo

HU-131. Es el recorrido que se muestra al jurado y la base del video (HU-132). Sigue el flujo del MVP y abre con lo que es el centro del producto: la rotación, el suelo, los datos de la NASA y «Qué cambió». La oferta va al final, como valor agregado (decisión 12).

**Estado (14 nov):** el guion está escrito y los dos casos están elegidos con los datos publicados (dataset `2026.11.18`). El diagnóstico ya responde con el motor (#102): el caso del cultivo no apto quedó confirmado. Los demás resultados se llenan cuando respondan los endpoints que todavía dan `501` y cuando el dataset traiga el periodo normal del clima (ver «Antes de la demo»). Falta ensayarlo.

## Lo que se dice siempre

Estas frases no se negocian. Si en un momento de la demo no caben, se dicen al cierre.

- **«Ventana de siembra»:** de la fecha de siembra a la cosecha estimada de ese cultivo. Nunca «semestre».
- **Es historia de la zona, no un pronóstico.** El diagnóstico, el orden de las ventanas y «Qué cambió» dicen cómo le ha ido a cada época, no cómo será el próximo año.
- **Las estrategias se comparan por reglas con fuente.** No predicen cuánto va a mejorar el suelo, ni cuánto se va a cosechar.
- **NASA POWER es un reanálisis**, un modelo con observaciones, no una observación directa del satélite.
- **La decisión es del agricultor.**
- **Es una región piloto:** el altiplano de Boyacá y Cundinamarca, con la sede en Duitama. Las fuentes propias de la región son las de Colombia: DIVIPOLA del DANE, EVA, SIPSA, el IDEAM, la UPRA y el IGAC (decisión 11).

## Los productos de la NASA en pantalla

Se nombra cada uno cuando aparece, con para qué sirve:

| Producto | Para qué, en la demo | Dónde se ve |
|---|---|---|
| **NASA POWER** (reanálisis) | Temperatura, heladas, calor y la ET0 con la que se calcula cuánta agua necesita el cultivo | Aptitud y diagnóstico del ciclo, agua del plan, «Qué cambió» |
| **NASADEM** | Altitud, con la que se corrige la temperatura del municipio o del lote, y pendiente, para la erosión | Aptitud del cultivo, salud del suelo |
| **GPM IMERG** | La lluvia de la señal de agua y del agua del plan; la de POWER se muestra al lado para contrastar, sin mezclarlas | Diagnóstico del ciclo, agua del plan |
| **MODIS NDVI**, **SMAP** y la **capa GIBS** del mapa | Verdor de la zona, humedad del suelo y la imagen satelital del mapa del lote | **Solo si están el día de la demo** (HU-208, HU-210 y HU-211). Hoy el NDVI y SMAP no están en el dataset y la capa GIBS no está en la web: lo que no llegue no se nombra |

## Recorrido

Cada paso dice qué se muestra y qué se dice. Las pantallas de los pasos 0 a 4 y 6 ya existen en la web; a las que muestran un cálculo les falta el motor detrás (ver «Antes de la demo»). La de «Qué cambió» (paso 5) todavía es una página pendiente (HU-219).

| # | Pantalla | Qué se muestra | Qué se dice |
|---|---|---|---|
| 0 | Inicio (`/`) | La pregunta del agricultor | «¿Qué siembro después en este lote, para cuidar el suelo y no perder la cosecha por una helada?» |
| 1 | Entrada a las estrategias (`/consultar`), con el lote del usuario de demo o con municipio y área, sin cuenta | El municipio, el área, lo que se sembró antes y la rotación que ya hace | «Con o sin cuenta. Sin cuenta, los datos de la finca solo se usan para calcular y no se guardan en el servidor» (R9) |
| 2 | Estrategias (HU-102) | Hasta 3 ciclos por estrategia, sus cuatro criterios (agua, suelo, ingreso y riesgo), la salud del suelo con sus cinco criterios y fuentes, y la comparación con la rotación actual | «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo». Señalar la rotación actual y cuánto gana o pierde cada estrategia frente a ella |
| 3 | Un ciclo con su diagnóstico (HU-215) | La aptitud, la ventana de siembra, las señales con su calificación de 0 a 100, la luz y la acción | «Primero, si el cultivo se da en la zona. Después, seis señales, y la luz se decide por reglas: un riesgo grave no se compensa con lo demás» (R2). Si hay tiempo, las dos luces: con las prioridades del agricultor y con el criterio de AgroSense |
| 4 | Agua del plan (en el ciclo) | Cuánta agua necesita el ciclo y en qué meses no alcanza la lluvia | «Es una estimación con el clima de la zona, no una medición del lote: verifique la humedad del suelo en campo» (R10). Y que se planea con la lluvia del año seco, porque en los valles del altiplano IMERG y POWER dan casi el doble de lluvia que las estaciones del IDEAM |
| 5 | «Qué cambió en su zona» (HU-219) | Heladas, lluvia y calor por mes en dos periodos, y cómo se movieron las mejores ventanas | «Así fue en la historia de su zona. No es un pronóstico» |
| 6 | La oferta, en un ciclo | La señal de oferta como una señal más, con su fuente y su fecha cuando las tenga | Si tiene curva y datos: «Además, le avisamos si hay mucho de ese cultivo sembrado en su zona». Si sale «datos insuficientes», que es lo que pasa hoy, se dice por qué, con la razón que da la respuesta. Hoy el diagnóstico dice «Esta versión de AgroSense todavía no evalúa la oferta» (HU-072); y aunque estuviera, EVA todavía no está en el dataset (HU-031) y `thresholds.yaml` no tiene curva para la oferta, porque ninguna fuente dice qué es «mucho». AgroSense no lo inventa (R1) |
| 7 | Cierre | El impacto potencial y los límites (`docs/impacto.md`) | El impacto es potencial; la decisión es del agricultor; no sustituye la asistencia técnica |

## Caso A · Duitama: una estrategia que cuida el suelo

La sede del equipo. Es el caso favorable.

**Lo que dicen hoy los datos publicados** (dataset `2026.11.18`):

| Dato | Valor | Fuente |
|---|---|---|
| Temperatura media anual | 14,4 °C, dentro del óptimo de la papa (12 a 15 °C) | NASA POWER corregida por altitud con NASADEM |
| Altitud del municipio | 2.527 m | NASADEM |
| Pendiente (mediana del municipio) | 30,2 %, por encima del 12 % desde el que aumenta la susceptibilidad a la erosión | NASADEM; corte del IGAC |
| Heladas | Ningún mes con helada | NASA POWER, **con el aviso** de que POWER ve menos heladas de las que hay en el altiplano |
| Máxima que se supera uno de cada diez días | De 19,7 a 22,9 °C según el mes, por debajo de los 25 °C del óptimo alto de la papa | NASA POWER |
| Suelo | pH 5,75 (rango de 4,1 a 7,9) y textura franco arcillosa; carbono orgánico de 57 g/kg | SoilGrids, estimación de 250 m (R10) |

**La entrada:** lo de antes del terreno es **papa**, y la rotación actual que escribe (o que sale del historial de la cuenta de demo) es **papa, papa**.

**Qué se muestra:**

- La rotación actual: papa seguida de papa. Sale igual, con sus motivos en `issues` (`familia_seguida`, de Penn State Extension, y `papa_seguida`, del ICA), sin excluirse en silencio (decisión 14).
- La estrategia de referencia: **avena con vicia → arveja → papa**, la rotación que evaluó Agrosavia en Tibaitatá (papa, avena y arveja), empezando después de la papa que ya había. Tiene que empezar así: una estrategia que arranca con papa después de papa queda excluida por `papa_seguida`. Pasa el filtro de familias, porque ese filtro solo compara la familia principal de cada cultivo y la avena con vicia es Gramineae (decisión 16). Se espera que salga bien en nitrógeno, por la arveja y la vicia, y que el criterio de erosión importe por la pendiente. Al presentarla se aclara que en el catálogo la avena está como avena con vicia, un abono verde: es la que más se parece a la de Agrosavia, no la misma.
- Un ciclo de esa estrategia con su diagnóstico.

**Se confirma con el motor:** el orden de las estrategias, sus calificaciones y la luz de cada ciclo.

## Caso B · Güicán de la Sierra: una estrategia excluida por helada

Un municipio alto de Boyacá, donde las heladas de verdad pesan.

**Lo que dicen hoy los datos publicados** (dataset `2026.11.18`, periodo normal 1991–2020):

| Dato | Valor | Fuente |
|---|---|---|
| Temperatura media anual | 12,0 °C, dentro del óptimo de la papa | NASA POWER corregida por altitud con NASADEM |
| Altitud del municipio | 2.898 m | NASADEM |
| Pendiente (mediana del municipio) | 48,8 % | NASADEM |
| Heladas por mes | Enero, en el 43,3 % de los años; diciembre, 20 %; febrero, 16,7 % | NASA POWER (`climate_risk_month`) |
| Papa sembrada a principios de diciembre (ventana de diciembre a mayo) | Heló en alguno de esos meses en unos 2 de cada 3 años (cálculo propio con `climate_frost_month`; el número exacto lo da el motor) | NASA POWER |
| Papa sembrada a principios de abril (ventana de abril a septiembre) | Ningún año con helada en esos meses | NASA POWER |
| Suelo | pH 5,82 y textura franca; carbono orgánico de 66 g/kg | SoilGrids, estimación de 250 m |

**Por qué se excluye:** la papa es sensible a la helada en sus cuatro etapas (`crop_stages`). La curva de heladas de `thresholds.yaml` da 40 con helada en el 40 % de los años y baja hasta 0 en el 100 %, y es crítica por debajo de 40. Con helada en unos 2 de cada 3 años, la señal es desfavorable y crítica. Un ciclo así es de alto riesgo y excluye la estrategia, con su motivo (R2, R3).

**La entrada:** lo de antes del terreno es **arveja**, con la primera siembra a principios de diciembre. Así, la primera siembra de papa no choca con ninguna regla de familias (arveja y papa son de familias distintas): lo que excluye esas estrategias es la helada. Para mostrarlo, se elige una cuyos ciclos siguientes tampoco choquen entre sí, por ejemplo papa → avena con vicia → arveja.

**Qué se muestra:**

- Las estrategias que empiezan con papa en diciembre: excluidas, con el motivo de la helada. Puede que otras también salgan excluidas: la arveja y la avena con vicia son sensibles a la helada en sus últimas etapas, que, sembradas en diciembre, caerían entre enero y marzo.
- El diagnóstico de esa papa en diciembre: luz roja y acción `other_window`, con sus mejores ventanas. Abril aparece sin heladas.
- «Qué cambió» en Güicán: cómo se movieron las heladas de un periodo a otro.

**Se confirma con el motor:** el porcentaje exacto, la calificación, la luz y el orden de las ventanas.

## Si alcanza el tiempo: un cultivo que no es apto

**Papa en Puerto Salgar (Cundinamarca):** 28,4 °C de temperatura media anual, muy por encima de los 16 °C que aguanta la papa. Luz roja, acción `rotate` y ninguna ventana: «Este cultivo no se da en su zona: elija otro» (regla 0).

**Confirmado con el motor (14 nov, `POST /api/v1/diagnostics`):** aptitud `not_suitable`, luz `red` y acción `rotate` con los dos criterios de pesos, y la razón «La temperatura media anual del municipio (28,4 °C, a 176 m) pasa de la que aguanta la papa (hasta 16 °C)».

## Antes de la demo

**Lo que tiene que estar en `desarrollo`:**

| Qué | HU | Por qué |
|---|---|---|
| Señal de agua | HU-071 | Sin agua, la luz con los pesos de AgroSense sale siempre «no evaluable» (regla 1 del semáforo). Felipe lo puso como condición para la demo |
| Señal de suelo | HU-183 | Paso 3 y la salud del suelo de los dos casos. El diagnóstico ya califica el suelo con el pH estimado del municipio y su rango (SoilGrids); la razón dice el rango de SoilGrids, que es ancho, y pide un análisis de suelo del lote. Con los datos publicados, la papa y el maíz salen favorables; la cebolla y el haba, que piden un pH más alto, moderadas en más de la mitad de los municipios |
| Diagnóstico con el motor | HU-076 | Pasos 3 y 6. Ya responde (#102, 14 nov); sigue en curso hasta que esté el agua |
| Estrategias con el motor | HU-084 | Paso 2 y los dos casos |
| Agua del plan | HU-146 | Paso 4 |
| Clima de dos periodos y su pantalla | HU-216, HU-218, HU-219 | Paso 5 |
| `climate_normal` en el manifiesto publicado | Próxima publicación del dataset (PR #96) | Sin él, heladas y calor salen «datos insuficientes» con los datos reales. Hoy el dataset `2026.11.18` no lo trae: el diagnóstico de la papa en Güicán sembrada en diciembre responde hoy «Sin el periodo de referencia del clima de la zona: la señal no se evalúa», y con los pesos de AgroSense la luz es `not_evaluable` |

**Lo que se prepara:**

- [ ] Un usuario de demo con el lote de Duitama y su historial (papa después de papa), **rotulado como ejemplo** en el nombre del lote y en la cuenta (R5).
- [ ] El recorrido sin cuenta como respaldo: municipio, área, cultivo anterior y rotación actual escritos a mano.
- [ ] Revisar cada número de los dos casos contra lo que responde el motor y cambiarlo aquí si no coincide.
- [ ] El modo ligero encendido si la conexión del lugar es mala (HU-158).
- [ ] Ensayo completo al menos una vez, con el tiempo que fije la guía de entrega (HU-132).

## Lo que no se dice

- Que AgroSense predice la cosecha, el precio o el clima.
- Que el suelo va a mejorar en un tanto por ciento.
- Que el agua o el suelo son una medición del lote.
- Que NASA POWER es una observación directa del satélite.
- Un producto de la NASA que no esté publicado ese día.
