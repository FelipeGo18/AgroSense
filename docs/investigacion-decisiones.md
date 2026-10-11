# Investigación: qué decisiones toma un agricultor y cuáles podemos calcular

10 de octubre de 2026. Sirve de base para decidir qué más entra en AgroSense, además de qué sembrar y cuándo regar.

> **Las secciones 1 a 4 describen el estado previo a la decisión.** Lo que se decidió está en la sección 5 y ya está en las specs (EP-18, HU-044, HU-045, HU-077, HU-179, HU-180, `specs/01-reglas.md`). Donde la tabla dice «P1 alto» o «P0, pero cambia el contrato», manda la sección 5.

## 1. Qué pide el reto, según la página oficial

Página del reto: «Field Shift: Adapting Farms with NASA Data» ([spaceappschallenge.org](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)). Nivel intermedio y avanzado; temas: ciencias de la Tierra, software, artes y multimedia.

Resumen publicado (traducción nuestra): los agricultores enfrentan cambios de temperatura, lluvias que cambian de patrón, escasez de agua, clima extremo y deterioro del suelo, y eso hace difícil **elegir rotaciones que protejan el campo, ahorren agua y den resiliencia a largo plazo**. El reto es una herramienta de apoyo a la decisión que use **observaciones de la Tierra de la NASA junto con información local del suelo, características de los cultivos y las prioridades del agricultor**, para explorar rotaciones que mejoren la salud del suelo y adapten la finca.

Lo que eso significa para nosotros:

- **El centro del reto son las rotaciones y la salud del suelo**, no el semáforo. Hoy nuestro P0 pone el diagnóstico de ventana primero y deja el suelo para el P1 («ajuste por suelo del usuario»). Es el hueco más grande frente al reto.
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
| Antes de sembrar | Qué cultivo y en qué semestre | Sí: diagnóstico (EP-07) |
| Antes de sembrar | Qué sembrar después en el mismo lote | Sí: rotaciones (EP-08), pero sin datos de suelo |
| Antes de sembrar | En qué **mes** sembrar, dentro del semestre | No |
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
| 4 | **Mejor mes para sembrar** | Para el cultivo y el municipio: meses del semestre en los que, históricamente, la lluvia del primer mes de la etapa inicial cubre su necesidad de agua y el riesgo de helada es bajo | NASA POWER (lluvia y temperatura), Kc y etapas (HU-142) | Diagnóstico: de «el semestre» a «el mes dentro del semestre» | P1 alto. Reutiliza el balance hídrico de EP-14 |
| 5 | **Riesgo de gota en papa** | Días por mes con humedad relativa ≥ 90 % y temperatura en el rango favorable para el hongo, según una regla con fuente | NASA POWER `RH2M`, `T2M` | Calendario del lote: «meses de vigilar la gota» | P1. La humedad de NASA POWER es de celda de unos 50 km: se dice como orientación |
| 6 | **Cuándo fertilizar** | Frecuencia histórica de aguaceros (por ejemplo, más de 20 mm en un día, umbral por definir con fuente) por mes y etapa. Mensaje: «evite abonar en semanas de aguaceros frecuentes». **Nunca la dosis**, que exige análisis de suelo | NASA POWER `PRECTOTCORR` | Calendario del lote | P1 |
| 7 | **Días para labores y para cosechar** | Probabilidad por mes de tener 3 días seguidos con menos de 5 mm, para preparar el terreno, cosechar o secar | NASA POWER (lluvia diaria) | Calendario del lote | P1 |
| 8 | **Cuándo vender** | Índice estacional de precio por mes, histórico | SIPSA (DANE) | Señal de mercado que ya existe en el P1 | P1, como ya estaba. Nunca precio futuro |
| 9 | **Si asegurar la cosecha** | Frecuencia histórica en la zona de los riesgos que cubre el seguro (helada, sequía, exceso de lluvia), más el enlace oficial al Incentivo al Seguro Agropecuario. No recomienda un producto | NASA POWER y la información de Finagro | Ficha del lote | P1, pequeño |
| 10 | **Años de El Niño y La Niña** | Cómo fue la lluvia del semestre en los años El Niño y La Niña del pasado, frente a los neutros. Mostrar la fase actual exige citar el boletín oficial y no hacerlo pasar por nuestro pronóstico | NASA POWER e índice ONI de la NOAA | Diagnóstico | P1. **Necesita una decisión** sobre la regla «nunca pronóstico» |
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
2. **Las heladas y el suelo son señales del semáforo, no avisos aparte** (decisión 8 de `docs/decisiones.md`). El semáforo pasa de tres a cinco señales: lluvia, heladas, suelo, oferta y mercado. El suelo nunca es crítico porque es una estimación. Hay una tabla explícita de acciones por luz (`specs/01-reglas.md`).
3. **Calendario del cultivo** (HU-179 y HU-180): mes a mes, mejores meses de siembra y riesgo de helada. La señal de heladas usa ese mismo cálculo. En P1 se suman aguaceros, ventanas secas y gota (HU-046).
4. **Temperaturas corregidas por altitud** (HU-044 pasa a P0), para que la etapa del cultivo, la ET0 y las heladas usen la misma temperatura.
5. **Sigue abierto:** El Niño y La Niña (punto 10) y el seguro (punto 9) quedan en P1 sin decidir. El P0 creció a unas 262 horas con integración: hay que decidir qué más se adelanta en la fase 0 o qué se recorta (`docs/plan-48h.md`).

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
