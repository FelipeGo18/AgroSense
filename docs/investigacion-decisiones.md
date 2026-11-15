# Investigación: qué decisiones toma un agricultor y cuáles podemos calcular

10 de octubre de 2026. Sirve de base para decidir qué más entra en AgroSense, además de qué sembrar y cuándo regar.

> **Las secciones 1 a 4 describen el estado previo a la decisión.** Lo que se decidió está en las secciones 5, 5b y 5c y ya está en las specs (EP-18, HU-044, HU-045, HU-077, HU-179, HU-180, `specs/01-reglas.md`). Donde la tabla dice «P1 alto» o «P0, pero cambia el contrato», mandan las secciones 5 y 5b. El 11 de octubre de 2026 la decisión pasó a evaluarse por ventana de siembra (sección 5b y decisión 9 de `docs/decisiones.md`) y, al final del día, el MVP se centró en el reto oficial (sección 5d y decisión 12).

## 1. Qué pide el reto, según la página oficial

Página del reto: «Field Shift: Adapting Farms with NASA Data» ([spaceappschallenge.org](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)). Nivel intermedio y avanzado; temas: ciencias de la Tierra, software, artes y multimedia.

**Texto oficial**, leído el 11 de octubre de 2026 en <https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/>:

> «Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long-term resilience. Your challenge is to create a decision-support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.»

Una versión local del reto (sede de Moquegua, según una imagen) dice: «Crea una herramienta que combine datos satelitales, suelo y cultivos para ayudar a los agricultores a tomar mejores decisiones». La sede del equipo no está confirmada: la región piloto sigue en Colombia como supuesto (HU-002).

Cómo cubre el MVP cada parte del enunciado: tabla en `specs/00-vision.md`.

Resumen publicado (traducción nuestra): los agricultores enfrentan cambios de temperatura, lluvias que cambian de patrón, escasez de agua, clima extremo y deterioro del suelo, y eso hace difícil **elegir rotaciones que protejan el campo, ahorren agua y den resiliencia a largo plazo**. El reto es una herramienta de apoyo a la decisión que use **observaciones de la Tierra de la NASA junto con información local del suelo, características de los cultivos y las prioridades del agricultor**, para explorar rotaciones que mejoren la salud del suelo y adapten la finca.

Lo que eso significa para nosotros:

- **El centro del reto son las rotaciones y la salud del suelo**, no el semáforo. Hoy nuestro P0 pone el diagnóstico de ventana primero y deja el suelo para el P1 («ajuste por suelo del usuario»). Es el hueco más grande frente al reto. **Resuelto el 11 de octubre de 2026 (sección 5d):** las estrategias de rotación pasan al centro.
- **Pide «información local del suelo» de forma explícita.** No tenemos ningún dato de suelo en el P0.
- **Las «prioridades del agricultor»** ya están: las rotaciones se ordenan por agua, suelo, ingreso y riesgo (HU-082).
- La página aún muestra solo el resumen. El enunciado completo, con los datos recomendados, sale el **28 de octubre** (`specs/00-vision.md`). Hay que revisarlo ese día.

## 2. Qué decisiones toma un agricultor en un ciclo

Lo que dicen los estudios:

- En Colombia, un estudio del CIAT y CCAFS con 151 agricultores de Córdoba y Santander encontró que piden información agroclimática **local, confiable y a tiempo** para decidir siembra, variedades, insumos y manejo del suelo. También encontró desconfianza en las instituciones que dan la información ([Alliance Bioversity-CIAT](https://alliancebioversityciat.org/publications-data/local-reliable-and-timely-agro-climatic-information-requirement-colombian-farmers), [mapeo de necesidades en maíz y frijol](https://buscador.una.edu.ni/Record/CGSpace71110)).
- Con servicios agroclimáticos, los cambios más comunes son la **fecha de siembra** y la **variedad** ([CGIAR](https://www.cgiar.org/implementing-agroclimate-services-to-help-more-than-500000-farmers)).
- En otro estudio (revista *Atmosphere*, 2021), cerca del 80 % de los encuestados usó la información para decidir la fecha de siembra, el 60 % para la variedad y el 70 % para **cuándo fertilizar** ([DOAJ](https://doaj.org/article/b2aedf0f38b84ea39a770c537edccacd)).
- La humedad del suelo pesa mucho para decidir **cuándo fertilizar y cuándo sembrar**, y casi nunca la tienen ([Wageningen, Ghana](https://research.wur.nl/en/publications/the-role-of-soil-moisture-information-in-developing-robust-climat/)).
- Con servicios climáticos también cambian la **preparación del terreno** y las labores del día a día ([Frontiers in Climate, 2024](https://www.frontiersin.org/journals/climate/articles/10.3389/fclim.2024.1458999/full)).
- Las mesas técnicas agroclimáticas de MinAgricultura e IDEAM recomiendan cosas parecidas: ajustar el calendario, construir reservorios en lluvias y buscar fuentes de agua alternas ante sequía ([boletín agroclimático nacional](https://www.agronet.gov.co/agroclima/Documents/Boletin%20Agroclim%C3%A1tico%20Nacional%20-%20Mayo%202021%20(1).pdf), [mesas técnicas](https://www.valoraanalitik.com/minagricultura-consolida-las-mesas-tecnicas-para-anticipar-riesgos-y-proteger-la-produccion/)).

Para nuestra región piloto (altiplano de Boyacá y Cundinamarca, papa):

- **Heladas:** ocurren sobre todo de diciembre a marzo. En una sola temporada afectaron 48.000 ha de 13.498 productores en 59 municipios ([circular de la Gobernación de Boyacá](https://www.boyaca.gov.co/wp-content/uploads/2020/12/324.CIRCULAR-GOB-BOYACÁ-HELADAS_V3.pdf)). La UPRA usa con datos del IDEAM el criterio de temperatura mínima menor a 2 °C para marcar amenaza ([UPRA](https://upra.gov.co/es-co/Documents/fenomeno_nino/20240125_Heladas-Enero-2024.pdf)). Ante una helada, algunos **adelantan la cosecha**, y eso movió el precio de la papa criolla ([DANE, SIPSA](https://www.dane.gov.co/files/investigaciones/agropecuario/sipsa/heladas/informe-heladas-21-feb-2020.pdf)).
- **Gota (tizón tardío) de la papa:** depende de la humedad relativa y la temperatura. Hay modelos para Cundinamarca que orientan cuándo aplicar fungicida y cuándo sembrar ([Uniandes](https://revistas.uniandes.edu.co/index.php/nys/article/download/4725/4316)).
- **El Niño y La Niña:** en la región Andina, El Niño puede bajar la lluvia entre 10 % y 50 %, y La Niña trae excesos, encharcamientos y hongos ([IDEAM, boletín agroclimático ENANDES](https://ideam.gov.co/sites/default/files/prensa/boletines/2024-09-11/boletin_agroclimatico_comunitario_enandes_agosto_2024.pdf)).
- **Seguro agropecuario:** el Incentivo al Seguro Agropecuario subsidia entre 50 % y 90 % de la prima a pequeños productores. Cubre heladas, sequía, exceso de lluvia e inundación ([Agronegocios](https://www.agronegocios.co/agricultura/coberturas-del-seguro-agropecuario-en-colombia-para-productores-por-heladas-y-altas-temperaturas-2949966)).

Las decisiones se ordenan así a lo largo del ciclo:

| Momento | Decisión | ¿AgroSense la apoya hoy? |
|---|---|---|
| Antes de sembrar | Qué cultivo y en qué época del año | Sí: diagnóstico (EP-07) |
| Antes de sembrar | Qué sembrar después en el mismo lote | Sí: rotaciones (EP-08), pero sin datos de suelo |
| Antes de sembrar | En qué **mes** sembrar | No |
| Antes de sembrar | Si el suelo necesita encalado, materia orgánica o descanso | No |
| Antes de sembrar | Si asegurar la cosecha | No |
| Preparación | Cuándo entrar a preparar el terreno (días secos para labores) | No |
| Durante el ciclo | Cuándo regar y cuánto | Sí: plan de agua (EP-14) |
| Durante el ciclo | Cuándo fertilizar (evitar aguaceros que lavan el abono) | No |
| Durante el ciclo | Cuándo vigilar heladas y gota | No |
| Durante el ciclo | Cómo va el cultivo | En parte: etapa por temperatura acumulada (HU-150); NDVI en P1 (HU-043) |
| Cosecha | Cuándo cosechar y secar (ventanas sin lluvia) | No |
| Venta | Cuándo vender | En parte: señal de mercado (P1, SIPSA) |

## 3. Qué podemos calcular con reglas y datos abiertos

Criterios: el dato es abierto y tiene fuente (R8); el cálculo es una regla explicable, no un pronóstico (decisión 4); y si falta el dato, sale «datos insuficientes» (R1). Todo lo climático es **frecuencia histórica de la zona**, no lo que va a pasar este año.

| # | Decisión | Qué calculamos | Datos | Encaje | Propuesta |
|---|---|---|---|---|---|
| 1 | **Suelo del lote** | pH, carbono orgánico, textura (arena, limo, arcilla) y nitrógeno a 0–30 cm, en el polígono del lote, con su intervalo de incertidumbre. Reglas: cultivos que no toleran ese pH se filtran o se avisan; que la textura ajuste el plan de agua es un supuesto sin HU todavía | SoilGrids de ISRIC, 250 m, CC BY 4.0 ([ISRIC](https://docs.isric.org/globaldata/soilgrids/)). Si se puede, contrastar con los estudios de suelos del IGAC | Rotaciones (filtro y criterio «suelo»), ficha del lote | **P0.** Es lo que el reto pide de forma explícita, y el polígono del lote (HU-164) ya lo permite |
| 2 | **Rotaciones que cuidan el suelo** | Incluir en el catálogo descanso, abonos verdes y leguminosas (arveja, haba, avena con vicia), con sus reglas de rotación y fuente. Ya hay rotaciones evaluadas por Agrosavia en Tibaitatá: papa-avena-arveja ([Redalyc](https://www.redalyc.org/journal/6538/653871546014/653871546014.pdf)) | Catálogo agronómico con fuentes | EP-06 y EP-08 | **P0.** Ajusta el catálogo, no la arquitectura |
| 3 | **Riesgo de heladas por mes** | Porcentaje de años con al menos un día de mínima ≤ 2 °C, por mes, corregido por altitud con la diferencia entre la altura del municipio y la de la celda de NASA (gradiente térmico, con fuente) | NASA POWER `T2M_MIN`; altitud (HU-044); criterio de la UPRA | Señal en el diagnóstico y en el calendario del lote | **P0, pero cambia el contrato y quizá el semáforo** (ver punto 5) |
| 4 | **Mejor mes para sembrar** | Para el cultivo y el municipio: meses en los que, históricamente, la lluvia del primer mes de la etapa inicial cubre su necesidad de agua y el riesgo de helada es bajo | NASA POWER (lluvia y temperatura), Kc y etapas (HU-142) | Diagnóstico: de una época amplia del año al mes de siembra | P1 alto. Reutiliza el balance hídrico de EP-14. Reemplazado el 11 de octubre por el orden de ventanas (sección 5b) |
| 5 | **Riesgo de gota en papa** | Días por mes con humedad relativa ≥ 90 % y temperatura en el rango favorable para el hongo, según una regla con fuente | NASA POWER `RH2M`, `T2M` | Calendario del lote: «meses de vigilar la gota» | P1. La humedad de NASA POWER es de celda de unos 50 km: se dice como orientación |
| 6 | **Cuándo fertilizar** | Frecuencia histórica de aguaceros (por ejemplo, más de 20 mm en un día, umbral por definir con fuente) por mes y etapa. Mensaje: «evite abonar en semanas de aguaceros frecuentes». **Nunca la dosis**, que exige análisis de suelo | NASA POWER `PRECTOTCORR` | Calendario del lote | P1 |
| 7 | **Días para labores y para cosechar** | Probabilidad por mes de tener 3 días seguidos con menos de 5 mm, para preparar el terreno, cosechar o secar | NASA POWER (lluvia diaria) | Calendario del lote | P1 |
| 8 | **Cuándo vender** | Índice estacional de precio por mes, histórico | SIPSA (DANE) | Señal de mercado que ya existe en el P1 | P1, como ya estaba. Nunca precio futuro |
| 9 | **Si asegurar la cosecha** | Frecuencia histórica en la zona de los riesgos que cubre el seguro (helada, sequía, exceso de lluvia), más el enlace oficial al Incentivo al Seguro Agropecuario. No recomienda un producto | NASA POWER y la información de Finagro | Ficha del lote | P1, pequeño |
| 10 | **Años de El Niño y La Niña** | Cómo fue la lluvia de los meses de la ventana en los años El Niño y La Niña del pasado, frente a los neutros. Mostrar la fase actual exige citar el boletín oficial y no hacerlo pasar por nuestro pronóstico | NASA POWER e índice ONI de la NOAA | Diagnóstico | P1. **Necesita una decisión** sobre la regla «nunca pronóstico» |
| 11 | **Cómo va el cultivo** | Verdor del lote (NDVI) a 30 m en el polígono, frente a su propia historia | NASA HLS | Lote · ahora | P1, ya es HU-043 |
| 12 | **Humedad del suelo** | Humedad superficial y de raíces, para ajustar el aviso de riego | NASA SMAP L4 a 9 km ([NSIDC](https://nsidc.org/data/spl4smgp/versions/2)), disponible en AppEEARS. Por verificar: NASA POWER también publica humedad del suelo (`GWETTOP`, `GWETROOT`) con la misma API que ya usamos | Plan y aviso de agua | P1, ya está en HU-043 y HU-147 |

## 4. Lo que no calculamos, y por qué

| Decisión | Por qué no |
|---|---|
| Cuánto va a producir (rendimiento) | Sería un pronóstico; lo prohíbe la decisión 4 |
| Precio futuro | Igual: solo índice histórico |
| Dosis de fertilizante o de cal | Exige análisis de suelo del lote; SoilGrids es una estimación de 250 m. Se recomienda hacer el análisis |
| Plagas en general | Sin datos abiertos por municipio. Solo la gota, con su regla |
| Variedad | No hay catálogo de variedades con fuente en la región. Posible P1 si Agrosavia lo publica |
| Costos y mano de obra | Sin datos abiertos confiables por municipio |

## 5. Qué se decidió (10 de octubre de 2026)

1. **El suelo entra al P0** (EP-18): SoilGrids por municipio y por lote dibujado, en el diagnóstico, en las rotaciones y en la ficha del lote.
2. **Las heladas y el suelo son señales del semáforo, no avisos aparte** (decisión 8 de `docs/decisiones.md`). El semáforo suma esas dos señales a las que ya tenía. El suelo nunca es crítico porque es una estimación. Hay una tabla explícita de acciones por luz (`specs/01-reglas.md`). La lista de señales cambió al día siguiente: ver la sección 5b.
3. **Calendario del cultivo** (HU-179 y HU-180): mes a mes, cuándo sembrar y el riesgo de helada. En P1 se suman aguaceros, ventanas secas y gota (HU-046). Cómo se elige cuándo sembrar y de qué depende la señal de heladas cambió al día siguiente: ver la sección 5b.
4. **Temperaturas corregidas por altitud** (HU-044 pasa a P0), para que la etapa del cultivo, la ET0 y las heladas usen la misma temperatura.
5. **Sigue abierto:** El Niño y La Niña (punto 10) y el seguro (punto 9) quedan en P1 sin decidir. El P0 creció a unas 262 horas con integración: hay que decidir qué más se adelanta en la fase 0 o qué se recorta (`docs/plan-48h.md`).

## 5b. Qué cambió el 11 de octubre de 2026: ventanas de siembra

Aprobado por Felipe. Explicación en la decisión 9 de `docs/decisiones.md`; reglas en `specs/01-reglas.md`.

1. **La decisión se evalúa por ventana de siembra**: una fecha de siembra más lo que dura el cultivo. Las ventanas se comparan por mes y por semana. Responde a lo que dicen los estudios de la sección 2: el cambio más común con información agroclimática es la **fecha de siembra**.
2. **Aptitud del cultivo en la zona**, antes de todo: la temperatura media anual del municipio frente al rango de la ficha (por altitud hasta la decisión 13). Es un filtro (R3).
3. **Seis señales en el P0**: agua, heladas, calor, suelo, oferta y mercado. El agua reemplaza a la señal que solo miraba la lluvia y sale del balance hídrico de EP-14; el calor es nueva. En el P1: exceso de lluvia, enfermedades por clima (la gota, punto 5 de la sección 3) y clima de cosecha (punto 7).
4. **El riego cuenta**: los lotes guardan si tienen riego, y con riego la falta de lluvia no es un riesgo.
5. **Orden de las ventanas**: un orden con las prioridades del agricultor reemplaza al «mejor mes» del punto 4 de la sección 3. Una ventana con una señal crítica es de alto riesgo y no se compensa. El mismo día el orden pasó a ir primero por el factor que más limita y después por el balance (sección 5c).
6. **La señal de heladas** ya no depende del calendario: evalúa las semanas de la ventana en que el cultivo está en una etapa sensible. Es el calendario el que reutiliza las señales.
7. **Sigue siendo historia de la zona, no pronóstico.** El semestre solo queda en la oferta de EVA, que se publica así.
8. **Por confirmar con fuente (R8):** la temperatura máxima que aguanta cada cultivo y su rango de temperatura media anual (decisión 13). Sin fuente, el calor y la aptitud quedan en «datos insuficientes» (`docs/riesgos.md`).

## 5c. Qué cambió después, el mismo 11 de octubre: prioridades y fuentes

Aprobado por Felipe. Explicación en las decisiones 10 y 11 de `docs/decisiones.md`. Corrige lo que en las secciones anteriores dice que el orden de ventanas es solo un balance:

1. **Método de la FAO:** cada señal se califica de 0 a 100 con una curva por cultivo al estilo EcoCrop; las ventanas se ordenan primero por el factor que más limita y después por el promedio ponderado.
2. **Las prioridades del agricultor** ya no son solo de las rotaciones (punto 1 de la sección 1): también hay un peso de 0 a 5 por señal en el diagnóstico y en el calendario. El riesgo grave de clima cuenta siempre.
3. **La oferta y el mercado cambian el semáforo**, y con «rotar» se sugieren cultivos alternativos.
4. **La textura del suelo** entra en el balance de agua.
5. **Varias fuentes, ninguna única verdad**, y la región es un supuesto hasta el 28 de octubre.

## 5d. Qué cambió al final del 11 de octubre: MVP centrado en el reto

Decidido por Felipe. Explicación en la decisión 12 de `docs/decisiones.md`. Manda sobre lo que las secciones anteriores digan distinto:

1. **La NASA es el núcleo.** Además de NASA POWER (ampliado, y dicho como reanálisis): NASADEM, GPM IMERG, MODIS NDVI, SMAP y la capa GIBS del mapa. Los puntos 11 y 12 de la sección 3 (NDVI y humedad del suelo) pasan de P1 a P0, con MODIS a 250 m en lugar de HLS a 30 m, que queda en P1.
2. **Las estrategias de rotación de 3 ciclos son la entrada del producto**, con la salud del suelo en cuatro criterios por reglas con fuente. No es una predicción de cuánto mejora el suelo.
3. **«Qué cambió»** compara dos periodos de la historia de la zona. Responde a «adaptarse a condiciones que cambian» sin pronosticar.
4. **Siete cultivos** con ficha completa y con fuente: papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia.
5. **P0 es el MVP.** El calendario completo, el lote vivo, el clima en vivo, la escena 3D, la finca temporal y los cultivos alternativos pasan a P1. En el MVP las ventanas se comparan por mes y la duración del cultivo sale de su ficha.
6. **La oferta es valor agregado**, no protagonista: una señal más, dentro del criterio de ingreso de las estrategias, y al final de la demo.

## 5e. Los cortes de la señal de mercado: propuesta, no en uso (14 de noviembre de 2026)

**Estado: propuesta, no en uso.** `market` sigue sin curva (`curve: null` en `thresholds.yaml` 1.0.0) y es `insufficient_data`.

- **Estacionalidad de la UPRA, descartada.** Para decidir qué índice estacional de precio es «precio bajo» (HU-073) se investigó la estacionalidad del precio de la papa que publica la UPRA. Se descartó como fuente de los cortes: es propia de la papa y de sus variedades, y no se generaliza a la arveja, la cebolla de bulbo ni la zanahoria, que también tienen precio en SIPSA.
- **Cuantiles documentados.** El índice estacional de `market_price_season.parquet` (dataset 2026.11.12; 756 meses de 63 series producto-central, de todos los productos de SIPSA publicados y no solo de los cultivos del catálogo) tiene: P10 ≈ 0,82, P25 ≈ 0,91, P50 ≈ 1,00, P75 ≈ 1,08 y P90 ≈ 1,16.
- **Curva propuesta**, para el día en que una fuente externa diga qué índice estacional es «precio bajo»: `[[0,85, 0], [0,91, 40], [1,0, 70], [1,15, 100]]`, con calificación crítica solo en 0 y `source_id = dane_sipsa`. Cada punto se anclaría a un cuantil: 1,0 → 70 (el precio promedio, ≈ P50), 0,91 → 40 (≈ P25), 0,85 → 0 (≥ P10) y 1,15 → 100 (≤ P90).
- **Hoy no se usa.** `market` y `supply` no son protagonistas (decisión 12: valor agregado) y no cumplen el criterio de la regla del equipo del 11 de noviembre de 2026, citada por Felipe en la revisión del PR #72: un criterio del equipo se acepta solo si (a) es central para el producto y (b) cada número se apoya en un dato externo citado. Los cuantiles cumplen (b) pero no (a), y por eso Felipe rechazó la curva: decidir que el cuarto más barato es `unfavorable` sigue siendo un criterio propio sin fuente externa, y con la curva el precio podría mandar sobre el semáforo (rojo o `rotate`), justo lo que la decisión 12 quería evitar. Revisión de Felipe del PR #72, 14 de noviembre de 2026.

## 5f. Oferta y mercado: se muestran sin calificar y la historia del precio sirve para comparar (15 de noviembre de 2026)

**Estado: propuesta, pendiente de aprobar por Haider o Felipe (decisión 17 de `docs/decisiones.md`).** Reemplaza el camino de 5e (buscar una curva para `market`): después de buscar otra vez, ninguna fuente externa da el corte, y los datos muestran que el valor del precio está en comparar fechas, no en calificar una sola. Se reflejaría en HU-072, HU-073, HU-239, HU-240 y HU-241.

### Qué se buscó y qué se encontró

Se buscó una fuente externa que diga qué es «precio bajo» en el precio mayorista y qué es «sobreoferta». **Ninguna lo dice.** Lo marcado ✔ se leyó en el documento original; lo demás se cita como lo describe su fuente, sin usarlo.

| Fuente | Qué dice | Por qué no da el corte |
|---|---|---|
| MADR, Programa de Apoyo a la Comercialización de la Papa (2020), según la Bolsa Mercantil, «Preguntas frecuentes» ✔ | El apoyo es «la diferencia entre el [costo promedio de producción por tonelada …] y el [precio de venta por tonelada …]». Costo de la parda pastusa, suprema, superior y capiro: 700.000 $/t | Es un costo **en finca**, y SIPSA es precio **mayorista**. En 2020 el mes más barato de la parda pastusa en Corabastos fue 715 $/kg (microdatos SIPSA) y aun así hubo apoyo: contra el mayorista, el costo casi nunca dispara |
| Finagro, Marcos de Referencia Agroeconómicos ✔ | «El precio mínimo para cubrir los costos de producción»: COP 723/kg en papa Betina (Boyacá) y COP 664/kg en cebolla de bulbo (Sutamarchán y Villa de Leyva) | Mismo problema: en finca y sin tierra. No hay uno de papa parda pastusa en la región |
| PMA (ALPS) ✔ y FAO (GIEWS) ✔ | Alertan precios «unusually high» y «abnormal high levels» | Solo miran hacia arriba |
| FEWS NET, guía de 2019 ✔ | ±10 % para decir si la oferta sube, baja o se queda igual | Es para balances de oferta, no para precios: sería trasladar un corte, como el IFPA rechazado en 5e |
| Texas A&M, E-314 y RM2-5 ✔ | El índice estacional y la «seasonal high-low table»: en qué meses suele caer el precio más alto y el más bajo de cada año | Describe la temporada. No dice qué precio es malo para quien vende |
| DANE, metodología de SIPSA-A (DSO-SIPSA_A-MET-001) ✔; UPRA, Plan de Ordenamiento de la Producción de la papa (2023) ✔; UPRA, intención de siembra | Volumen que llega a las centrales; el precio de la papa «relacionado con los volúmenes», pero sus ciclos «no responden exclusivamente al volumen ofertado» | Ninguno define cuánto es «mucho». La intención de siembra es cualitativa |
| Minagri (Perú), declaración en prensa de 2020 | Sembrar «por encima del 3 % sobre el promedio ya implica un nivel de riesgo» | Una declaración de prensa, de otro país y del total nacional: no cumple R8 |

Calificar la oferta o el mercado sería, entonces, un criterio del equipo, y la regla del 11 de noviembre de 2026 (decisión 16) solo lo permite en lo central del producto.

### Qué dicen los datos (verificado el 15 de noviembre de 2026)

Con los datos publicados (`market_price_day`, servicio web de SIPSA, 2020–2026), los microdatos mensuales de SIPSA del DANE (catálogo 776, 2013–2024), una muestra de SIPSA-A (catálogo 697, septiembre a diciembre de 2025) y `supply_semester` (EVA, 2019–2025). Los cálculos se repiten con los datos de `desarrollo`.

1. **La temporada de la papa es nacional y se repite.** En los microdatos, septiembre es el mes más barato de la papa parda pastusa en 22 de las 23 centrales con 5 años completos o más. En Corabastos estuvo por debajo del promedio de su año en septiembre los 12 años de 2013 a 2024, y en el servicio web los 5 años de 2021 a 2025. El perfil de los 12 meses de Tunja (2013–2020) es casi el de Corabastos en los mismos años (correlación de 0,98).
2. **Correr la siembra cambia mucho el mes de la cosecha.** La papa dura 165 días en su ficha. Con el índice publicado de Corabastos (2021–2025): sembrada a comienzos de abril se cosecha a mediados de septiembre, que estuvo por encima del promedio de su año en 0 de 5 años (índice 0,77); sembrada a comienzos de noviembre se cosecha a mediados de abril, que estuvo por encima en 4 de 5 (índice 1,26). En la arveja de Corabastos, abril, mayo y junio estuvieron por encima los 5 años, y octubre, noviembre y diciembre solo 1 de 5.
3. **Contar años es más honesto que promediar el índice.** En la cebolla de bulbo de Corabastos, julio tiene un índice medio de 1,12, pero estuvo por encima del promedio de su año solo en 2 de 5 años: un año muy caro sube el promedio. «En N de M años» dice cuánto se repite; el promedio solo, no.
4. **La temporada no dice el nivel.** En 2025 el patrón se cumplió y el precio igual se desplomó: la papa negra en Corabastos valió 1.026 $/kg en julio y 809 en octubre de 2025, frente a 3.725 y 1.672 en los mismos meses de 2024 (`market_price_day`). Por eso todo se dice como historia, nunca como pronóstico.
5. **Los microdatos y el servicio web dan la misma temporada.** Papa en Corabastos, 2021–2024: el índice mes a mes de los dos coincide (correlación de 1,00 y diferencia máxima de 0,01). Se pueden empalmar (HU-239).
6. **Boyacá no tiene precio de papa en su central.** El servicio web publica papa negra en Tunja solo del 4 de febrero de 2020 al 27 de julio de 2021, y los microdatos la tienen en Tunja y Sogamoso hasta 2020 y en Duitama hasta 2017. Hoy la papa de un municipio de Boyacá, Duitama incluida, no tiene señal de mercado. En la muestra de SIPSA-A, la papa que salió de Boyacá se repartió entre muchas centrales (Barranquilla 16 %, Tunja 15 %, Bucaramanga 14 %, Corabastos 13 %), y la de Cundinamarca fue sobre todo a Corabastos (71 %).
7. **EVA no alcanza para hablar de sobreoferta.** Cubre de 2019 a 2025, y 2.750 de sus 8.456 filas son preliminares. En el 27 % de las filas, el área sembrada de un municipio, cultivo y semestre es exactamente la del mismo semestre del año anterior (en la haba, el 52 %). Al sembrar, el último dato tiene un año o más. La variación del área (`planted_change_pct`) está vacía en todas las filas: la calcula HU-032.
8. **Un caso coincide, pero no prueba nada.** En 2025 A se registró la mayor área de papa de la serie en Boyacá y Cundinamarca: 65.566 ha, 11 % más que el promedio de 2022–2024 A (dato preliminar). Su cosecha coincidió con el desplome del punto 4. Un caso, con 7 años de EVA, no permite decir que el área anticipa el precio.
9. **Los microdatos tienen haba.** El servicio web no publica haba en ninguna central (`pipeline/sipsa_crops.yaml`), pero los microdatos traen «Haba verde» en Corabastos y Tunja de 2013 a 2024. Si es el mismo producto que la haba del catálogo lo decide Felipe, como el maíz y el chócolo.

### La propuesta, punto por punto

1. **Oferta y mercado se muestran sin calificar.** `status = available` cuando hay dato, con `level`, `score` y `critical` nulos (falso): el dato existe, pero ninguna fuente dice cómo calificarlo (R1 separa disponibilidad y nivel). Nunca cambian la luz ni la acción, no son factor limitante y van a las limitaciones con «sin calificar». Así se cumple lo que pidió Felipe en el PR #72: el precio nunca manda sobre el semáforo. Sin dato siguen siendo `insufficient_data`.
2. **El mercado dice la historia del mes de cosecha.** «En Corabastos, en septiembre (el mes en que saldría su cosecha), el precio de la papa negra estuvo por encima del promedio de su año en 0 de 5 años (2021–2025) y por debajo en 5; en promedio, 23 % por debajo. Así fue en la historia: no es un pronóstico del precio. Fuente: DANE». Para eso, `market_price_season` y `market_month` suman `years_above` y `years_below`, y `market_month` suma `first_year` y `last_year` (HU-073).
3. **La central de referencia, por cultivo cuando hace falta.** `region.crop_market_overrides` del manifiesto dice, por departamento y cultivo, qué central da el precio cuando la del departamento no lo publica: la papa de Boyacá, Corabastos. Se apoya en los puntos 1 y 6: la temporada de Tunja y la de Corabastos son casi iguales, y Corabastos es una de las centrales a las que va la papa de Boyacá. La respuesta lo dice siempre. No es un relleno automático: solo vale lo que está en la configuración, aprobado (HU-073).
4. **El precio ordena las ventanas solo si al agricultor le importa mucho.** Con peso 4 o 5 en `market` («me importa mucho»), entre las ventanas cuyo factor limitante cae en la misma decena va primero la que cosecha en el mes que más años estuvo por encima del promedio de su año; después, el promedio ponderado. Con peso de 0 a 3 (también el de AgroSense, que es 1), el orden no cambia. El precio nunca saca a una ventana de su decena ni sube una de alto riesgo: el clima sigue mandando (HU-240).
5. **El ingreso de las estrategias, sin inventar una escala.** `income` es el promedio, ciclo por ciclo, del porcentaje de años en que el mes de cosecha estuvo por encima del promedio de su año (100 × `years_above` / `years`); el abono verde y el descanso valen 0, como en la decisión 15; un cultivo sin historia de precio no cuenta. Es una frecuencia, como la de las heladas: no hay corte del equipo. La oferta sale del ingreso (HU-241).
6. **La oferta, como contexto.** El área sembrada del municipio según EVA, en el semestre en que cae la siembra, con su variación cuando exista HU-032, si es preliminar y si es el mismo valor que el año anterior. Su historia ya no promete «evitar la sobreoferta» (HU-072).
7. **Doce años de historia.** HU-239 empalma los microdatos de SIPSA (2013–2024) con el servicio web: 5 años pasan a 13 en la papa de Corabastos, y la haba puede tener historia.
8. **Manejo de los datos y licencias.** Los términos de dane.gov.co (los del servicio web) autorizan el uso, la transformación y el análisis con la cita «Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co». Los del portal de microdatos (catálogos 776 y 697) agregan: «Queda en cambio prohibida la copia o reproducción de los datos en cualquier medio electrónico (redes, bases de datos, cd rom, diskettes) que permita la disponibilidad de esta información a multiples usuarios sin el previo visto bueno del DANE por medio escrito». Por eso: los microdatos se bajan del DANE en cada construcción, con su URL y su sha256 fijos, a una caché local fuera de git (`data/raw/`); no van a la *release* pública de la caché (HU-237) ni a una base de datos compartida, la del equipo incluida, mientras no haya ese visto bueno; no los sirve la API; se publica solo lo que sale del análisis (índices y conteos por mes), con la cita. Si el equipo quiere una copia compartida, primero pide el visto bueno escrito del DANE (HU-239).
9. **Lo que no se hace.** No se califica la oferta ni el mercado con un corte propio, no se usa el costo en finca contra el precio mayorista, no se dice «precio bajo» ni «sobreoferta» como veredicto, y el precio nunca cambia la luz ni excluye una estrategia.

### Por qué da valor al agricultor, y cómo puede dar más

- **Elegir la fecha con dos razones a la vez.** Hoy la ventana dice si el clima conviene. Con esto también dice, sin pronosticar, si su cosecha suele caer en el mes barato o en el caro, y cuántos años de cuántos fue así. En la papa, la diferencia entre sembrar en abril y en noviembre es cosechar en el mes que estuvo por debajo de su promedio 5 de 5 años o en uno que estuvo por encima 4 de 5.
- **Que el precio no le gane al clima.** El precio solo ordena entre ventanas igual de seguras, y solo si el agricultor dice que le importa mucho. Nunca vuelve verde una ventana con helada.
- **Estrategias con dimensión económica honesta.** El ingreso compara en qué meses cosecha cada estrategia, sin prometer cuánto va a ganar.
- **Contexto de la zona.** Cuánto se sembró de su cultivo en su municipio, y si el dato es preliminar o repetido.
- **Más valor después (P1):** el volumen que llega a la central por mes (SIPSA-A) explica por qué baja el precio («en septiembre llega más papa»); la historia de la haba; el orden por semanas (HU-193); y el precio en finca, si aparece una fuente pública.

### Para la entrega

- **La historia de la demo:** papa en Duitama. El clima de la NASA dice qué ventanas son seguras; la historia del DANE dice en cuál de ellas la cosecha suele caer en mejor mes; la estrategia compara con lo que el agricultor ya hace. Cada número lleva su fuente y su periodo.
- **Manejo de los datos como argumento:** ninguna cifra inventada, cada fuente con su licencia (`docs/licencias.md`), los datos de uso restringido nunca publicados y todo reconstruible (R4, R8).
- **Si no alcanza el tiempo:** HU-073 y HU-072 primero (mostrar sin calificar); HU-240 y HU-241 se recortan antes: sin ellas, el precio se muestra pero no ordena, y el ingreso no califica. HU-239 es P1.

## 6. Fuentes

- [Reto «Field Shift: Adapting Farms with NASA Data»](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)
- [Local, reliable and timely agro-climatic information: a requirement of Colombian farmers (CIAT)](https://alliancebioversityciat.org/publications-data/local-reliable-and-timely-agro-climatic-information-requirement-colombian-farmers)
- [Mapeo de actores y necesidades de información agroclimática en maíz y frijol, Colombia](https://buscador.una.edu.ni/Record/CGSpace71110)
- [CGIAR: servicios agroclimáticos para más de 500.000 agricultores](https://www.cgiar.org/implementing-agroclimate-services-to-help-more-than-500000-farmers)
- [Atmosphere (2021): uso de información climática para siembra, variedad y fertilización](https://doaj.org/article/b2aedf0f38b84ea39a770c537edccacd)
- [Frontiers in Climate (2024): servicios climáticos y decisiones de pequeños productores](https://www.frontiersin.org/journals/climate/articles/10.3389/fclim.2024.1458999/full)
- [Humedad del suelo en servicios climáticos para pequeños productores (Wageningen)](https://research.wur.nl/en/publications/the-role-of-soil-moisture-information-in-developing-robust-climat/)
- [Boletín agroclimático nacional (Agronet)](https://www.agronet.gov.co/agroclima/Documents/Boletin%20Agroclim%C3%A1tico%20Nacional%20-%20Mayo%202021%20(1).pdf) y [mesas técnicas agroclimáticas](https://www.valoraanalitik.com/minagricultura-consolida-las-mesas-tecnicas-para-anticipar-riesgos-y-proteger-la-produccion/)
- [Boletín agroclimático ENANDES del IDEAM, agosto de 2024](https://ideam.gov.co/sites/default/files/prensa/boletines/2024-09-11/boletin_agroclimatico_comunitario_enandes_agosto_2024.pdf)
- [Circular sobre heladas, Gobernación de Boyacá](https://www.boyaca.gov.co/wp-content/uploads/2020/12/324.CIRCULAR-GOB-BOYACÁ-HELADAS_V3.pdf), [UPRA: amenaza por heladas](https://upra.gov.co/es-co/Documents/fenomeno_nino/20240125_Heladas-Enero-2024.pdf) y [DANE, SIPSA: informe de heladas](https://www.dane.gov.co/files/investigaciones/agropecuario/sipsa/heladas/informe-heladas-21-feb-2020.pdf)
- [Modelo de tizón tardío de la papa en Cundinamarca (Uniandes)](https://revistas.uniandes.edu.co/index.php/nys/article/download/4725/4316)
- [Rotaciones papa-avena-arveja en Tibaitatá (Redalyc)](https://www.redalyc.org/journal/6538/653871546014/653871546014.pdf)
- [SoilGrids (ISRIC)](https://docs.isric.org/globaldata/soilgrids/) y [preguntas frecuentes](https://www.isric.org/explore/soilgrids/faq-soilgrids)
- [Metodología de NASA POWER por comunidad](https://power.larc.nasa.gov/docs/methodology/communities/)
- [SMAP L4 (NSIDC)](https://nsidc.org/data/spl4smgp/versions/2) y [SMAP L4 en AppEEARS](https://www.earthdata.nasa.gov/data/alerts-outages/new-versions-smap-level-4-products-now-available-appeears)
- [Seguro agropecuario: coberturas por heladas y temperatura (Agronegocios)](https://www.agronegocios.co/agricultura/coberturas-del-seguro-agropecuario-en-colombia-para-productores-por-heladas-y-altas-temperaturas-2949966)
- [Días aptos para labores según lluvia y humedad (Redalyc)](https://www.redalyc.org/pdf/4457/445744116017.pdf)
- Oferta y mercado (sección 5f): [Bolsa Mercantil, preguntas frecuentes del apoyo a la papa (2020)](https://www.bolsamercantil.com.co/sites/default/files/2022-06/PREGUNTAS%20FRECUENTES.pdf), [Finagro, papa Betina en Boyacá](https://www.finagro.com.co/sites/default/files/2022-05/papa_betina_boyaca.pdf), [Finagro, cebolla de bulbo en Sutamarchán y Villa de Leyva](https://www.finagro.com.co/sites/default/files/2022-07/MRA-Cebolla-Boyaca-Sutamarchan-VilladeLeyva.pdf), [Texas A&M, RM2-5: estacionalidad en los mercados de cultivos](https://agecoext.tamu.edu/wp-content/uploads/2013/10/rm2-5oh.pdf), [PMA, ALPS](https://docs.wfp.org/api/documents/WFP-0000155936/download/), [FAO GIEWS, alertas de precios](https://www.fao.org/giews/food-prices/price-warnings/en/), [FEWS NET, guía de oferta y mercado (2019)](https://fews.net/sites/default/files/documents/reports/Supply_and_Market_Outlook_guidance_document_20190725.pdf), [DANE, metodología de SIPSA-A](https://www.dane.gov.co/files/investigaciones/agropecuario/fichas/DSO-SIPSA_A-MET-001.pdf), [UPRA, Plan de Ordenamiento de la Producción de la papa (copia de Fedepapa)](https://fedepapa.com/home/wp-content/uploads/2026/02/PLAN-DE-ORDENAMIENTO-PRODUCTIVO-PARA-LA-CADENA-DE-LA-PAPA.pdf), [DANE, términos y condiciones](https://www.dane.gov.co/index.php/terminos-y-condiciones), [DANE, microdatos SIPSA-P 2013–2024 (catálogo 776)](https://microdatos.dane.gov.co/index.php/catalog/776) y [SIPSA-A 2018–2026 (catálogo 697)](https://microdatos.dane.gov.co/index.php/catalog/697)
