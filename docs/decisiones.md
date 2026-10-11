# Decisiones de arquitectura tomadas

Las decisiones que guían todo el proyecto, explicadas en lenguaje sencillo. Si una HU choca con alguna, se discute aquí antes de implementarla.

## 1. Monolito modular

**Qué es:** todo el backend es un solo programa en Python, que se ejecuta y se despliega como una sola pieza. Por dentro está ordenado en módulos.

- **El motor** decide: calcula señales, arma el semáforo y ordena rotaciones. Es «puro» porque no sabe nada de internet ni de peticiones HTTP: recibe tablas y devuelve resultados.
- **La API** es la capa delgada de encima: recibe la petición, revisa que esté bien formada, llama al motor y devuelve JSON. No toma decisiones.

**Analogía:** un restaurante. La API es el mesero y el motor es la cocina. Es un solo restaurante (monolito), pero con salón y cocina separados (modular).

**Por qué:** los microservicios agregan piezas que pueden fallar, más configuración y más tiempo, y en 48 horas no compensan. Además, como el motor no depende de la web, se prueba solo, sin levantar un servidor.

**Regla asociada:** R6.

## 2. Contratos primero

**Qué es:** antes de programar, el equipo acuerda por escrito el esquema de datos (tablas, columnas, tipos, unidades) y el contrato de la API (qué se pide y qué se responde). «Congelados» significa que no se cambian a la ligera.

**Por qué:** sin contrato el trabajo va en cadena (la web espera a la API, la API al motor, el motor a los datos). Con contrato, todos arrancan en la hora 0: la web usa respuestas de ejemplo con el formato real, el motor usa Parquet de ejemplo con las mismas columnas, y datos sabe qué tabla producir. Al final se cambian los ejemplos por datos reales y todo encaja.

**Analogía:** construir una casa con planos: electricista y plomero trabajan a la vez porque saben dónde irá cada pared.

**Responsables:** Haider y Felipe. Cualquiera de los dos cambia el contrato o aprueba cada cambio.

**HUs:** HU-011, HU-012, HU-013.

## 3. Datos precalculados

**Qué es:** hay dos momentos separados.

- **Antes de la demo:** el pipeline descarga y limpia los datos, calcula los indicadores y guarda Parquet versionado.
- **Cuando el agricultor consulta:** la API solo lee esos indicadores ya calculados y aplica las reglas (milisegundos).

**Por qué:** descargar 20 años de lluvia diaria tarda minutos; si se hiciera en cada consulta, la app sería lentísima. Si la API de NASA se cae durante la presentación, la demo sigue. Y con la versión del dataset se puede reproducir cualquier resultado.

**Analogía:** cocinar en casa antes de un viaje en lugar de buscar restaurante en carretera.

**HUs:** EP-03, EP-04, HU-123.

## 4. Reglas, no predicción

**Qué es:** la herramienta no intenta adivinar el futuro (cosecha, precio o clima). Mira el historial y aplica reglas claras. Entrega riesgo basado en lo que ya pasó, y siempre puede decir **por qué**. El diagnóstico de una ventana de siembra y el orden de las ventanas (decisión 9) dicen cómo le ha ido a esa época del año en la zona: la misma fecha en otro año da el mismo resultado de clima.

**Por qué:**

- EVA, la fuente de la oferta, solo tiene datos desde 2019 y publica dos semestres por año: unos 12 puntos por municipio. Un modelo de aprendizaje automático con tan poco aprende mal y da números que parecen precisos pero no lo son.
- Las reglas se explican; un modelo de caja negra, no.
- Es más honesto: nadie puede garantizar el precio futuro.

**Reglas asociadas:** R2, R4, R5.

## 5. Sin datos no hay señal

**Qué es:** si una fuente no tiene información para el caso (por ejemplo, SIPSA no cubre la zona), la señal sale como «datos insuficientes». No se inventa un valor, no se usa el promedio de otra zona sin avisar y no se reemplaza por otra señal. Por eso cada señal tiene dos campos separados:

- **Estado:** ¿hay datos? (`available`, `insufficient_data` o `not_applicable` cuando la señal no aplica, por ejemplo heladas o calor en un cultivo que no los sufre)
- **Nivel:** ¿qué tan bueno o malo es? (`favorable`, `moderate`, `unfavorable`). Sin datos, el nivel queda vacío.

**Por qué:** «no sabemos» y «está mal» son cosas distintas. Mostrar la falta de datos como rojo haría creer que hay riesgo; rellenarla haría parecer sólida una recomendación que no lo es.

Lo mismo vale para la aptitud del cultivo y para el orden de las ventanas (decisión 9): una ficha sin rango de altitud con fuente deja la aptitud en «datos insuficientes» y no descarta el cultivo, y una señal sin datos no puntúa en el balance de una ventana.

**Ejemplo de error que esta regla evita:** decir que, si SIPSA falla, el mercado se apoya solo en EVA. EVA no tiene precios; sería mezclar oferta con mercado.

**Regla asociada:** R1.

## 6. Calcular no es guardar

**Qué es:** el usuario puede crear una cuenta y registrar uno o varios lotes, en una o varias zonas, con su historial de temporadas. Para eso hay una base de datos de cuentas. Pero el cálculo sigue igual: el diagnóstico, el calendario, las rotaciones y el plan de agua no guardan nada; la web les envía los datos del lote y recibe la respuesta. Solo los endpoints de cuenta (`/me`, `/me/password`, `/lots`, `/seasons`) escriben en la base de datos. Los de cálculo no guardan los datos de la finca: solo suman 1 a un contador anónimo de uso (día, tipo de consulta, municipio y cultivo) para las métricas, sin nada que diga quién consultó; con `lot_id` pueden leer el polígono de un lote propio para calcular su suelo.

- **Sin cuenta:** se puede consultar; los datos de la finca se envían solo para calcular y no se guardan en el servidor ni en sus logs. La consulta solo se cuenta, sin datos de quien consulta.
- **Métricas:** el servidor sí persiste lo necesario para saber cómo se usa la app: un contador por día, tipo de consulta, municipio y cultivo (`usage_daily`). Decidido el 11 de octubre de 2026.
- **Con cuenta:** se guardan los lotes y su historial, con consentimiento registrado. El usuario puede borrar todo.
- **Sin servicios externos:** PostgreSQL propio en Docker y autenticación propia con usuario y contraseña. No se pide correo ni celular. Si la base de datos falla, el modo sin cuenta sigue funcionando.

**Analogía:** la calculadora de una ferretería y el cuaderno de fiado. La calculadora la usa cualquiera y no anota nada; el cuaderno solo existe si el cliente abrió su cuenta, y la puede cerrar cuando quiera.

**Por qué:** el valor de «qué sembrar después» crece con el historial real del lote, y el progreso de un agricultor que vuelve necesita memoria. Separar cálculo y cuentas mantiene puro el motor (R6) y deja el cálculo igual de reproducible (R4).

**Lo que exige:** base de datos, autenticación, política de tratamiento de datos (Ley 1581 de 2012 de Colombia), borrado de la cuenta y más horas en el evento.

**Regla asociada:** R9.

## 7. El clima en vivo es ambiente, no decisión

**Qué es:** la escena refleja lo que pasa ahora en el municipio: si llueve, si es de noche, si hay viento o nubes. Pero el diagnóstico, las rotaciones y el plan de agua siguen usando solo el historial publicado.

- **Noche y día:** se calculan en el navegador con la hora y la posición del municipio. No dependen de internet.
- **Lluvia, viento y nubes:** vienen de Open-Meteo, consultado por la API con caché de 15 minutos. NASA POWER no sirve para esto porque publica con 2 a 7 días de retraso.
- **Aproximado, no exacto:** el valor sale de modelos meteorológicos para el punto del municipio, no de una estación en el lote. La escena lo rotula como «condición aproximada en <municipio>», con fuente y hora.
- **Sin datos en vivo:** la escena queda en un clima neutro y lo dice. Nunca se inventa lluvia ni sol.
- **Sin pronóstico:** solo se muestra el «ahora». El pronóstico del proveedor no se usa, ni siquiera como ambiente, para no presentar nada como pronóstico (ver «Lo que nunca se hace» en `CLAUDE.md`).

**Por qué:** hace que la app se sienta viva y conectada al campo real, sin mezclar el «ahora» con una decisión que se basa en historial (decisión 4). Si el servicio en vivo se cae, nada del resultado cambia.

**Regla asociada:** R5 (se muestra la fuente y la hora de la condición) y R8.

## 8. Suelo y heladas dentro del diagnóstico

**Qué es:** el semáforo no tiene una sola señal de «clima»: tiene señales independientes, y las heladas y el suelo son dos de ellas. No son avisos aparte: son parte de la pregunta «¿conviene sembrar este cultivo aquí, en esta fecha?». Desde la decisión 9 las señales del P0 son seis: agua, heladas, calor, suelo, oferta y mercado.

- **Heladas:** frecuencia histórica de heladas en las semanas en que el cultivo está en una etapa sensible, con la temperatura de NASA POWER corregida por la altitud del municipio. Pueden ser críticas: una helada frecuente en la floración da rojo aunque el agua alcance.
- **Suelo:** pH de SoilGrids, del municipio o del lote dibujado. Nunca es crítico, porque es una estimación de 250 m; solo cuenta para rojo junto con otra señal desfavorable. La textura y el carbono orgánico se muestran y alimentan las rotaciones.
- **El mismo cálculo en todas partes:** el diagnóstico de una fecha y la ventana de esa fecha en el calendario dan las mismas señales, y el suelo del lote es el mismo en el diagnóstico, en las rotaciones y en la ficha del lote.

**Por qué:** el reto («Field Shift») pide usar información local del suelo y rotaciones que mejoren la salud del suelo, y las heladas son el riesgo climático más dañino del altiplano. Ponerlas como avisos aparte del semáforo dejaría dos respuestas que se pueden contradecir.

**Reglas asociadas:** R1, R2, R3 y R10.

## 9. Ventanas de siembra, no semestres

**Qué es:** la decisión se evalúa sobre una **ventana de siembra**: una fecha de siembra más lo que dura ese cultivo en campo, de la siembra a la cosecha estimada. Las ventanas se comparan por mes y, dentro de un mes, por semana.

- **Primero, la aptitud.** Antes de mirar fechas, el motor comprueba que el cultivo se da en ese municipio: la altitud debe caer en el rango de su ficha. Si no (papa en la costa), la respuesta lo dice con su razón y no evalúa ventanas. Es un filtro, no una señal.
- **Seis señales por ventana.** Agua, heladas, calor, suelo, oferta y mercado. Cada una se mide contra lo que ese cultivo necesita o aguanta: un cultivo que pide poca agua rara vez sale mal en agua. En el P1 se suman exceso de lluvia, enfermedades por clima y clima de cosecha.
- **El riego cuenta.** El agricultor dice si tiene riego. Con riego, la falta de lluvia no es un riesgo: la señal de agua informa cuánto riego haría falta.
- **Un orden para comparar.** Las ventanas se ordenan primero por el factor que más limita y después por un balance de 0 a 100, ponderado por las prioridades del agricultor (de 0 a 5 por señal); el método está en la decisión 10. Una ventana con una señal crítica desfavorable es de **alto riesgo**: el balance no la rescata, va después de las demás y nunca entra entre las mejores.
- **«Otra ventana» en lugar de «espere».** Si lo que sale mal es el clima de esa fecha, la acción es buscar otra ventana, y la respuesta trae las mejores de los próximos doce meses. Si es el suelo, la oferta o el mercado, o el cultivo no es apto, la acción es rotar.
- **El semestre solo vive en la oferta.** EVA publica por semestre. La señal de oferta lee el semestre en que cae la fecha de siembra, y la respuesta dice cuál usó.

**Analogía:** elegir cuándo viajar. No se pregunta «¿primer o segundo semestre?», sino «si salgo este día y el viaje dura tanto, ¿cómo suele estar el camino?». Y nadie elige por uno: se le muestran las opciones con lo que cada una gana y sacrifica.

**Por qué:**

- **Cada cultivo dura distinto.** Una lechuga dura dos meses y una papa cinco. Un semestre no describe a ninguna de las dos: cada una se evalúa en su propio tramo.
- **No hay mes perfecto.** Casi siempre una fecha gana en una cosa y pierde en otra. Un solo «sí o no» por semestre esconde esa elección; el orden de ventanas la muestra.
- **Decide el agricultor.** Él sabe qué le pesa más: el agua, la helada o el precio. Las prioridades ordenan las ventanas, pero el motor nunca esconde un riesgo crítico detrás de un buen balance.

**Lo que no cambia:** sigue siendo historia de la zona, no pronóstico (decisión 4); una señal sin datos no puntúa ni se rellena (decisión 5); el semáforo se decide por reglas, nunca por el balance (R2).

**Lo que exige:** fichas con rango de altitud y temperatura máxima con fuente (R8), datos de clima por semana, y que el balance hídrico esté listo antes que el diagnóstico.

**Reglas asociadas:** R1, R2, R3, R4, R5 y R8. Detalle en `specs/01-reglas.md`. Aprobada por Felipe el 11 de octubre de 2026.

## 10. El agricultor pondera; el riesgo grave no se negocia

**Qué es:** cada señal de una ventana se califica de 0 a 100 y el agricultor puede decir cuánto le importa cada una. El método sigue el de la FAO para evaluar la aptitud de tierras para cultivos:

- **Calificación por curva.** Cada señal recibe de 0 a 100 con una curva por cultivo, al estilo del modelo EcoCrop de la FAO: 100 dentro del rango óptimo del cultivo, 0 fuera de sus límites absolutos y una recta entre ambos. Los límites salen de la ficha del cultivo, con fuente. El nivel sale de la calificación (70 a 100 favorable, 40 a 69 moderado, 0 a 39 desfavorable).
- **Primero lo que más limita.** Las ventanas se ordenan por su peor factor (la «ley del mínimo»): una ventana vale lo que vale la señal más baja entre las que cuentan. Solo entre ventanas con un factor limitante parecido decide el promedio ponderado por las prioridades.
- **Prioridades del agricultor.** Cada señal tiene un peso de 0 a 5. AgroSense propone pesos por defecto (`weights.yaml`, con quién los definió y por qué) y el agricultor los cambia al consultar. Peso 0: la señal se muestra, pero no cambia la luz. Peso 4 o 5: un resultado moderado cuenta como desfavorable.
- **El riesgo grave no se negocia.** Agua, heladas o calor críticos cuentan siempre, aunque el agricultor les ponga peso 0. Una ventana de alto riesgo nunca sube por un buen promedio.
- **Dos luces cuando no coinciden.** Si los pesos del agricultor dan otra luz que los de AgroSense, se muestran las dos: «Con el criterio de AgroSense: amarillo · Con sus prioridades: verde».
- **La oferta y el mercado sí cambian el semáforo.** Son señales como las demás. Si la acción es rotar, la respuesta sugiere cultivos aptos que en esa ventana salen bien en clima y tienen mejor oferta.
- **El suelo pesa dos veces, sin repetirse.** El pH es la señal de suelo; la textura entra en el balance de agua, porque cambia cuánta agua retiene el suelo.
- **Todo es informativo.** La decisión final es del agricultor.

**Analogía:** una cadena se rompe por su eslabón más débil. Primero se mira el eslabón más débil de cada ventana; después, entre cadenas parecidas, se escoge la que más se ajusta a lo que el agricultor necesita. Y si un eslabón está roto (un riesgo grave), no importa cuánto le guste lo demás.

**Por qué:**

- **Un promedio esconde lo peor.** Una ventana con una helada muy probable y todo lo demás perfecto sacaría un buen promedio. La ley del mínimo evita que un buen promedio tape un factor que puede hacer perder la cosecha. Es como trabaja la FAO al evaluar la aptitud de tierras: lo que más limita define la clase.
- **Cada agricultor pesa distinto.** Quien vende a un comprador fijo no se preocupa por la oferta de la zona; quien tiene un reservorio se preocupa menos por la lluvia. Un solo juego de pesos no sirve para todos.
- **Pero no puede taparse el riesgo grave.** Un peso 0 a la helada no hace que deje de helar. Por eso el riesgo grave de clima cuenta siempre.
- **Mostrar las dos luces es honesto.** El agricultor ve qué cambia por sus prioridades y qué diría AgroSense; nadie decide por él.

**Lo que no cambia:** el semáforo se decide por reglas, no por promedio (R2); una señal sin datos no se califica ni se rellena (R1); todo es historia de la zona, no pronóstico (decisión 4).

**Lo que exige:** fichas con rangos óptimos y límites absolutos con fuente (candidata FAO EcoCrop, por confirmar, R8); pesos por defecto con su porqué; un método con fuente para el agua que retiene cada textura; y que la respuesta diga qué pesos usó (R4).

**Reglas asociadas:** R1, R2, R4, R5, R8 y R10. Detalle en `specs/01-reglas.md` («Cómo se califica cada señal», «Las prioridades del agricultor», «Agregación del semáforo» y «Orden de las ventanas»). Aprobada por Felipe el 11 de octubre de 2026.

## 11. Varias fuentes, ninguna única verdad

**Qué es:** un mismo indicador puede venir de varias fuentes. Por ejemplo, la oferta: la estadística oficial del país, FAOSTAT, reportes descargados de portales públicos y las siembras que registran los usuarios de AgroSense.

- **Juntas, nunca mezcladas.** Las fuentes se muestran lado a lado para contrastarlas. Cada una dice de dónde viene, de qué fecha es y qué cubre (`coverage`). No se promedian ni una rellena a otra.
- **Una calcula la señal.** `sources.yaml` dice, para cada región, qué fuente calcula cada señal; la respuesta dice cuál fue. Las demás son de contraste.
- **Las siembras de AgroSense, con cuidado.** Solo se muestran como totales por municipio y cultivo, y nunca cuando hay menos de 5 cuentas, para que nadie pueda deducir lo de un vecino (R9).
- **La región está por confirmar.** El reto todavía no dice qué datos ni qué región. Colombia es un supuesto: el P0 se prepara con una región piloto colombiana (EVA, DIVIPOLA, SIPSA, IDEAM, UPRA, IGAC) hasta que el enunciado del 28 de octubre la confirme o la cambie (HU-002). El modelo no supone Colombia fuera de los adaptadores de cada fuente (R7).

**Analogía:** preguntar la hora a varias personas. Si dos relojes no coinciden, no se saca el promedio: se dice qué marca cada uno y cuál se está usando.

**Por qué:**

- **Ninguna fuente es perfecta.** La estadística oficial llega con meses de retraso y el último año es preliminar; las siembras de AgroSense son recientes pero de pocos usuarios. Juntas dan una idea más honesta que cualquiera sola.
- **Mezclarlas esconde de dónde sale el número.** Un promedio de fuentes distintas no tiene fuente (R8).
- **La región puede cambiar.** Si el reto pide otra región o otros datos, basta con cambiar los adaptadores y `sources.yaml`; el motor sigue igual.

**Lo que no cambia:** sin datos no hay señal (decisión 5): si la fuente que calcula la señal no tiene dato, la señal es «datos insuficientes» aunque otra fuente sí tenga.

**Lo que exige:** `sources` con `coverage`; `sources.yaml` por región; un lugar en el contrato para los valores de contraste (por decidir); y, para usar las siembras de AgroSense, que el consentimiento lo diga.

**Reglas asociadas:** R1, R5, R7, R8 y R9. Aprobada por Felipe el 11 de octubre de 2026.

## Cómo se conectan

Los datos se calculan antes (3), con un formato acordado desde el inicio (2) y sin una única fuente de verdad (11). Un motor separado de la web (1) aplica reglas explicables (4) y dice honestamente cuando le falta información (5). Lo que el usuario registra vive aparte, en su cuenta, y solo llega al cálculo a través de la API (6). El clima de ahora decora la escena, pero nunca entra al cálculo (7). El suelo y las heladas son señales del mismo semáforo (8), que se evalúa sobre una ventana de siembra: primero la aptitud del cultivo, luego sus señales y, para comparar fechas, un orden que deja decidir al agricultor (9). Cada señal se califica con una curva por cultivo, el agricultor pondera, y el riesgo grave cuenta siempre (10).
