# Guion de la demo

HU-131. Es el recorrido que se muestra al jurado y la base del video (HU-132). Sigue el flujo del MVP y abre con lo que es el centro del producto: la rotación, el suelo, los datos de la NASA y «Qué cambió». La oferta va al final, como valor agregado (decisión 12).

**Estado (15 nov):** los dos casos están confirmados con el motor y los datos publicados (dataset `2026.11.25`, reglas `0.1.0+umbrales.1.0.0+pesos.1.0.0`), sin cuenta, con el suelo y la pendiente del municipio. Ya responden `/rotations` (HU-084, #160), `/diagnostics`, `/water-plans` y `GET /changes`. Los números de abajo son los que respondió el motor el 15 de noviembre. Faltan el usuario de demo, la oferta como señal (HU-072) y el ensayo (ver «Antes de la demo»).

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
| **MODIS NDVI**, **SMAP** y la **capa GIBS** del mapa | Verdor de la zona, humedad del suelo y la imagen satelital del mapa del lote | **Solo si están el día de la demo** (HU-208, HU-210 y HU-211). El 15 de noviembre no se ven: el NDVI está publicado, pero `GET /trends` lo devuelve `insufficient_data` porque `catalog/sources.yaml` no le asigna una fuente al verdor, y el ciclo dice que no hay datos del verdor; SMAP no está publicado y la capa GIBS no está en la web. Lo que no llegue no se nombra |

## Recorrido

Cada paso dice qué se muestra y qué se dice. Todas las pantallas existen en la web y, desde el 15 de noviembre, todas responden con el motor; la de «Qué cambió» es HU-219.

| # | Pantalla | Qué se muestra | Qué se dice |
|---|---|---|---|
| 0 | Inicio (`/`) | La pregunta del agricultor | «¿Qué siembro después en este lote, para cuidar el suelo y no perder la cosecha por una helada?» |
| 1 | Entrada a las estrategias (`/consultar`), con el lote del usuario de demo o con municipio y área, sin cuenta | El municipio, el área, lo que se sembró antes y la rotación que ya hace | «Con o sin cuenta. Sin cuenta, los datos de la finca solo se usan para calcular y no se guardan en el servidor» (R9) |
| 2 | Estrategias (HU-102) | Hasta 3 ciclos por estrategia, sus cuatro criterios (agua, suelo, ingreso y riesgo), la salud del suelo con sus cinco criterios y fuentes, y la comparación con la rotación actual | «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo». Señalar la rotación actual y cuánto gana o pierde cada estrategia frente a ella |
| 3 | Un ciclo con su diagnóstico (HU-215) | La aptitud, la ventana de siembra, las señales con su calificación de 0 a 100, la luz y la acción | «Primero, si el cultivo se da en la zona. Después, seis señales, y la luz se decide por reglas: un riesgo grave no se compensa con lo demás» (R2). Si hay tiempo, las dos luces: con las prioridades del agricultor y con el criterio de AgroSense |
| 4 | Agua del plan (en el ciclo) | Cuánta agua necesita el ciclo y en qué meses no alcanza la lluvia | «Es una estimación con el clima de la zona, no una medición del lote: verifique la humedad del suelo en campo» (R10). Y que se planea con la lluvia del año seco, porque en los valles del altiplano IMERG y POWER dan casi el doble de lluvia que las estaciones del IDEAM |
| 5 | «Qué cambió en su zona» (HU-219) | Heladas, lluvia y calor por mes en dos periodos, y cómo se movieron las mejores ventanas | «Así fue en la historia de su zona. No es un pronóstico» |
| 6 | La oferta, en un ciclo | La señal de oferta como una señal más, con su fuente y su fecha cuando las tenga | Desde la decisión 17 la oferta y el mercado se muestran **sin calificar**, como contexto: «Además, le mostramos cuánto de ese cultivo se sembró en su zona y cómo le fue al precio en el mes de la cosecha». El 15 de noviembre el diagnóstico todavía dice «Esta versión de AgroSense todavía no evalúa la oferta» (HU-072) y, en Güicán, «Sin datos de mercado para la zona». Si así sigue el día de la demo, se dice por qué: ninguna fuente dice qué es «mucho» ni «un precio bajo», y AgroSense no lo inventa (R1) |
| 7 | Cierre | El impacto potencial y los límites (`docs/impacto.md`) | El impacto es potencial; la decisión es del agricultor; no sustituye la asistencia técnica |

## Caso A · Duitama: una estrategia que cuida el suelo

La sede del equipo. Es el caso favorable.

**La entrada** (sin cuenta, o el lote del usuario de demo): Duitama (15238), siembra el **lunes 5 de abril de 2027**, lo de antes del terreno es **papa** y la rotación que viene haciendo es **papa, papa** (el motor la completa a tres ciclos: papa, papa, papa). Prioridades de la rotación: primero todas en 3 y después **suelo en 5**.

Por qué abril: es el comienzo de las lluvias del primer semestre en el altiplano. Sembrando el 7 de diciembre, en plena temporada seca, 182 estrategias quedan fuera por un ciclo con el agua desfavorable y crítica en un año seco; en abril quedan 24.

**Lo que respondió el motor (15 nov):**

| Qué | Resultado |
|---|---|
| Rotación actual (papa, papa, papa) | Se muestra y no entra al ranking: total **44** (agua 58, suelo 50, riesgo 20). En `issues`, `familia_seguida` (Penn State Extension) y `papa_seguida` (ICA) en cada par de ciclos. Salud del suelo: nitrógeno y corte de plagas desfavorables, carbono orgánico moderado |
| Con todas las prioridades en 3 | Primera, **maíz → descanso → arveja** (88): gana en agua y riesgo, pero la erosión sale desfavorable (deja el suelo descubierto 6,1 meses con una pendiente de 30,2 %) y la cobertura, moderada. Segunda, **arveja → avena con vicia → haba** (86) |
| Con **suelo en 5** | **arveja → avena con vicia → haba pasa a la primera** (88): agua 83, suelo 100, riesgo 74; los tres ciclos en verde; los cinco criterios de salud del suelo favorables (tres ciclos con leguminosa, suelo cubierto el 98,6 % del tiempo, la familia de la papa no vuelve, 0,2 meses descubierto). Frente a la rotación actual: **+44** en total, +50 en suelo, +54 en riesgo, +25 en agua |
| Ciclos de esa estrategia | Arveja del 5 de abril al 24 de julio de 2027; avena con vicia del 26 de julio al 23 de diciembre; haba del 27 de diciembre de 2027 al 19 de junio de 2028 |
| Agua del plan (arveja desde abril, 1 ha) | La lluvia de un año normal y de un año seco cubre lo que necesita de abril a junio; en julio, en un año seco, pueden faltar hasta 10 mm (hasta 99 m³ para 1 ha). Con el aviso de que IMERG sobrestima la lluvia del altiplano |
| Ingreso | No califica en ninguna estrategia: «Ningún cultivo tiene dato de oferta ni de mercado» (decisión 17, HU-241). El total sale de agua, suelo y riesgo |

**Qué se muestra y qué se dice:**

1. La rotación actual, papa sobre papa, con sus motivos (decisión 14): no se excluye en silencio, se muestra para que se vea por qué no conviene.
2. Con las prioridades iguales, la primera gana en agua y riesgo pero deja el suelo descubierto en una ladera: la salud del suelo lo dice.
3. Se sube el suelo a 5: **arveja → avena con vicia → haba** pasa a la primera. «La decisión es del agricultor: AgroSense ordena según lo que a usted le importa».
4. Un ciclo con su diagnóstico (la arveja de abril, en verde) y su agua del plan.

**La rotación de Agrosavia** (papa, avena y arveja, la referencia con fuente de `specs/01-reglas.md`): adaptada al catálogo y empezando después de la papa, **avena con vicia → arveja → papa**, en abril califica 75 (suelo 90, sin `issues`) y **no entra entre las 10**, que en abril empiezan en 82. En diciembre queda fuera: la avena con vicia de diciembre a mayo cubre el 46 % de lo que necesita en un año seco (agua 18, crítica). Si el jurado la pide, se escribe como rotación actual y se ve con sus números.

## Caso B · Güicán de la Sierra: una estrategia excluida por helada

Un municipio alto de Boyacá (2.898 m, 12,0 °C de media anual), donde las heladas de verdad pesan.

**La entrada:** Güicán de la Sierra (15332), siembra el **lunes 7 de diciembre de 2026**, lo de antes del terreno es **arveja** y la rotación que el agricultor piensa hacer, escrita como rotación actual, es **papa → avena con vicia → arveja**. Prioridades de la rotación en 3.

Por qué se escribe como rotación actual: las estrategias sugeridas que empiezan con papa en diciembre sí quedan fuera por la helada (247 descartadas por alto riesgo en total), pero `excluded` trae solo 10 y hoy salen las de `rule` en orden alfabético (`arveja → …`), así que esas no se ven. La rotación actual nunca se excluye en silencio: se muestra con sus motivos.

**Lo que respondió el motor (15 nov):**

| Qué | Resultado |
|---|---|
| Rotación actual (papa → avena con vicia → arveja) | Total 57, riesgo 20. Dos ciclos de alto riesgo en `issues`: **la papa de diciembre** («Sembrando en diciembre, heló en todo el cultivo (de diciembre a mayo) 53 de cada 100 años: en 16 de los 30 años con dato, sembrando de 1991 a 2020») y la arveja de finales de octubre de 2027 (heló de diciembre a febrero en 15 de 30 años) |
| Las sugeridas | Las 10 empiezan con un **descanso** de diciembre a junio. Primera, **descanso → arveja → descanso** (87; frente a la actual, +30 en total y +80 en riesgo). Su salud del suelo es honesta: cobertura y erosión desfavorables, porque deja el suelo descubierto 12 meses (cubierto el 23,2 % del tiempo) en una pendiente de 48,8 % |
| Diagnóstico de la papa del 7 de diciembre | Apta (12,0 °C, dentro de 8 a 16 °C). **Luz roja y acción `other_window`** con los dos criterios de pesos. Helada **31 de 100, crítica**; agua 33, desfavorable (cubre el 57 % en un año seco); calor y suelo favorables (pH 5,82) |
| Mejores ventanas | **1 de abril**, 1 de mayo y 1 de marzo de 2027 |
| «Qué cambió» (papa, Güicán) | Heladas de diciembre: 45 % de los años en 1981–2000 y 15 % en 2005–2024; enero, de 50 % a 30 % (NASA POWER). Las mejores ventanas pasaron de abril, mayo y junio, limitadas por la helada, a marzo, abril y mayo, limitadas por el agua. La lluvia se compara con IMERG en 2001–2012 y 2013–2024, y la respuesta avisa que POWER e IMERG dan cambios de lluvia opuestos en cerca de 7 de cada 10 comparaciones de la región |

**Qué se muestra y qué se dice:**

1. La rotación que piensa hacer, con la papa de diciembre marcada como alto riesgo de helada: «un riesgo grave no se compensa con lo demás» (R2).
2. Las sugeridas: en diciembre conviene esperar. Si alguien pregunta por la erosión del descanso, se dice tal cual: la estrategia que menos arriesga deja el suelo descubierto, y la salud del suelo lo muestra.
3. El diagnóstico de esa papa: rojo, con sus mejores ventanas; abril sale sin heladas.
4. «Qué cambió»: las heladas de diciembre bajaron en la historia, **y aun así** con el periodo normal 1991–2020 heló en la mitad de los años. «Así fue en la historia de su zona. No es un pronóstico». Y POWER cuenta menos heladas de las que hay en el altiplano: la respuesta lo dice.

## Si alcanza el tiempo: un cultivo que no es apto

**Papa en Puerto Salgar (Cundinamarca):** 28,4 °C de temperatura media anual, muy por encima de los 16 °C que aguanta la papa. Luz roja, acción `rotate` y ninguna ventana: «Este cultivo no se da en su zona: elija otro» (regla 0).

**Confirmado con el motor (14 nov, y otra vez el 15 nov con el dataset `2026.11.25`, `POST /api/v1/diagnostics`):** aptitud `not_suitable`, luz `red` y acción `rotate` con los dos criterios de pesos, y la razón «La temperatura media anual del municipio (28,4 °C, a 176 m) pasa de la que aguanta la papa (hasta 16 °C)».

## Antes de la demo

**Lo que ya está en `desarrollo` (15 nov):** la señal de agua (HU-071), la de suelo (HU-183), el diagnóstico con el motor (HU-076), las estrategias (HU-084), el agua del plan (HU-146), «Qué cambió» con su pantalla (HU-216, HU-218 y HU-219), el suelo del lote dibujado (HU-182) y el periodo normal del clima en el dataset publicado (las heladas se evalúan con 1991–2020).

**Lo que todavía falta y cambia la demo:**

| Qué | HU | Qué pasa sin ello |
|---|---|---|
| La oferta y el mercado sin calificar, como contexto | HU-072, HU-239 y HU-241 (decisión 17) | El paso 6 dice «datos insuficientes» y el criterio de ingreso no califica en ninguna estrategia |
| El verdor de la zona en el ciclo | HU-208 (falta la fuente del verdor en `sources.yaml`) | El ciclo dice que no hay datos del verdor y MODIS NDVI no se nombra |
| La web desplegada | HU-023 y HU-236 | La demo se hace en local o con el video |

**Lo que se prepara:**

- [ ] Un usuario de demo con el lote de Duitama y su historial (papa después de papa), **rotulado como ejemplo** en el nombre del lote y en la cuenta (R5). Con un lote dibujado, el suelo y la pendiente salen del polígono (HU-182): **volver a confirmar los números del caso A con ese lote**, porque los de arriba son con el suelo y la pendiente del municipio.
- [ ] El recorrido sin cuenta como respaldo: municipio, área, cultivo anterior y rotación actual escritos a mano (las entradas de arriba).
- [x] Revisar cada número de los dos casos contra lo que responde el motor (15 nov, dataset `2026.11.25`, sin cuenta).
- [ ] El modo ligero encendido si la conexión del lugar es mala (HU-158).
- [ ] Ensayo completo al menos una vez, con el tiempo que fije la guía de entrega (HU-132).

## Lo que no se dice

- Que AgroSense predice la cosecha, el precio o el clima.
- Que el suelo va a mejorar en un tanto por ciento.
- Que el agua o el suelo son una medición del lote.
- Que NASA POWER es una observación directa del satélite.
- Un producto de la NASA que no esté publicado ese día.
