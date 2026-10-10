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

**Responsable:** Haider. Cambia el contrato o aprueba cada cambio.

**HUs:** HU-011, HU-012, HU-013.

## 3. Datos precalculados

**Qué es:** hay dos momentos separados.

- **Antes de la demo:** el pipeline descarga y limpia los datos, calcula los indicadores y guarda Parquet versionado.
- **Cuando el agricultor consulta:** la API solo lee esos indicadores ya calculados y aplica las reglas (milisegundos).

**Por qué:** descargar 20 años de lluvia diaria tarda minutos; si se hiciera en cada consulta, la app sería lentísima. Si la API de NASA se cae durante la presentación, la demo sigue. Y con la versión del dataset se puede reproducir cualquier resultado.

**Analogía:** cocinar en casa antes de un viaje en lugar de buscar restaurante en carretera.

**HUs:** EP-03, EP-04, HU-123.

## 4. Reglas, no predicción

**Qué es:** la herramienta no intenta adivinar el futuro (cosecha o precio). Mira el historial y aplica reglas claras. Entrega riesgo basado en lo que ya pasó, y siempre puede decir **por qué**.

**Por qué:**

- EVA solo tiene datos desde 2019 con dos semestres por año: unos 12 puntos por municipio. Un modelo de aprendizaje automático con tan poco aprende mal y da números que parecen precisos pero no lo son.
- Las reglas se explican; un modelo de caja negra, no.
- Es más honesto: nadie puede garantizar el precio futuro.

**Reglas asociadas:** R2, R4, R5.

## 5. Sin datos no hay señal

**Qué es:** si una fuente no tiene información para el caso (por ejemplo, SIPSA no cubre la zona), la señal sale como «datos insuficientes». No se inventa un valor, no se usa el promedio de otra zona sin avisar y no se reemplaza por otra señal. Por eso cada señal tiene dos campos separados:

- **Estado:** ¿hay datos? (`available` o `insufficient_data`)
- **Nivel:** ¿qué tan bueno o malo es? (`favorable`, `moderate`, `unfavorable`). Sin datos, el nivel queda vacío.

**Por qué:** «no sabemos» y «está mal» son cosas distintas. Mostrar la falta de datos como rojo haría creer que hay riesgo; rellenarla haría parecer sólida una recomendación que no lo es.

**Ejemplo de error que esta regla evita:** decir que, si SIPSA falla, el mercado se apoya solo en EVA. EVA no tiene precios; sería mezclar oferta con mercado.

**Regla asociada:** R1.

## 6. Calcular no es guardar

**Qué es:** el usuario puede crear una cuenta y registrar uno o varios lotes, en una o varias zonas, con su historial de temporadas. Para eso hay una base de datos de cuentas. Pero el cálculo sigue igual: el diagnóstico, las rotaciones y el plan de agua no guardan nada; la web les envía los datos del lote y recibe la respuesta. Solo los endpoints de cuenta (`/me`, `/lots`, `/seasons`) leen y escriben en la base de datos.

- **Sin cuenta:** se puede consultar, pero nada sale del dispositivo.
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

## Cómo se conectan

Los datos se calculan antes (3), con un formato acordado desde el inicio (2). Un motor separado de la web (1) aplica reglas explicables (4) y dice honestamente cuando le falta información (5). Lo que el usuario registra vive aparte, en su cuenta, y solo llega al cálculo a través de la API (6). El clima de ahora decora la escena, pero nunca entra al cálculo (7).
