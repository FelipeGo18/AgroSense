# Entrega a NASA Space Apps 2026

HU-132. Borrador de los campos de la página del proyecto en Space Apps, según la [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/). **La página y todo lo que se enlace va en inglés**: por eso los textos de los campos están en inglés. Las notas para el equipo van en español.

## Lo que pide la guía (leída el 14 de noviembre de 2026)

El 15 de noviembre no se pudo volver a leer desde el computador de Haider (la conexión segura con spaceappschallenge.org falla por el certificado de la red). Antes de enviar, alguien la abre en el navegador y confirma el plazo y los límites de la demo.

- **Plazo:** el envío abre el sábado 14 de noviembre a las 9:00 a. m. y **cierra el domingo 15 de noviembre a las 11:59 p. m.**, en la hora del evento local. Lo que se guarde o envíe después no entra.
- **Idioma:** todo en inglés. Un video puede ir hablado en español, pero **con subtítulos en inglés**. Las diapositivas, en inglés.
- **Demo:** un video de **30 segundos o menos** o un máximo de **7 diapositivas**, contando el título y la introducción. Pasarse del límite saca el proyecto del juzgamiento global. Se sube a un sitio externo (YouTube, Google Drive o GitHub) con un enlace público, sin contraseña ni registro.
- **Criterios del jurado:** impacto, creatividad, validez, relevancia y presentación.
- **Datos de la NASA:** hay que usar al menos un dato o recurso de la NASA para optar a un premio global, y decir cuáles.
- **Referencias:** listar todos los datos, recursos y herramientas, incluidos el código, los textos y las imágenes de terceros.
- **Uso de IA («Super Intelligence»):** el campo lo responde Haider directamente en el formulario (decidido el 14 de noviembre de 2026). No va en este archivo.
- **Sin personas menores de 18 años** en imágenes, video o audio.
- **Para enviar:** todos los integrantes confirmados en el mismo evento local, todos los campos llenos, aceptar los términos, confirmar que el trabajo es original y pulsar «Submit for Judging».
- **Enlace del proyecto:** se recomienda pedir la clasificación de FortiGuard para el sitio, para que el jurado lo pueda abrir (HU-236).

## Antes de enviar

- [ ] Revisar «What works in this version» y la tabla de cobertura (abajo), escritas con lo que respondía el 15 de noviembre a las 15:00 UTC, y ajustarlas a lo que responda al enviar. Quitar de los textos lo que no esté.
- [ ] **Las estrategias de rotación:** el 15 de noviembre, `/rotations` todavía responde 501. Esperan HU-223 (#153) y HU-084; HU-082 (el orden) entró con el #146. Si no responden al enviar: usar el resumen B (abajo), cambiar el tramo 0:10–0:20 del video por el diagnóstico de una siembra (texto al final del guion) y no poner MODIS NDVI en «NASA Data» (solo se ve en el ciclo de una estrategia).
- [ ] **La web en inglés** (HU-233, #127) todavía no está en `desarrollo`. Sin ella, el enlace del proyecto abre la web en español.
- [x] `docs/licencias.md` al día: lista las 46 fuentes del dataset `2026.11.24`, las mismas de `sources` (comprobado el 15 de noviembre).
- [ ] El enlace del proyecto: el dominio o la dirección de Cloud Run con `?lang=en` (HU-023, HU-233 y HU-236).
- [ ] **Todo lo enlazado en inglés.** El repositorio está en español: si se enlaza (en «Link to Final Project» o en las referencias), necesita al menos un README en inglés en la raíz, y las referencias en inglés (por ejemplo, la lista de fuentes y licencias). Decidirlo antes de enviar.
- [ ] El video de 30 segundos (o las 7 diapositivas), subido con enlace público y probado en una ventana privada.
- [ ] Probar en una ventana privada cada enlace de la página.
- [ ] Revisar que ninguna imagen ni video tenga personas menores de 18 años.
- [ ] Las imágenes del video (por ejemplo, la ladera del altiplano) son propias o tienen una licencia que lo permita, y van en las referencias.
- [ ] Que el texto de los campos no diga que algo funciona si no está en `desarrollo` y desplegado.

## Campos de la página

El resumen, «What it does» y «How it works» describen el MVP completo; «What works in this version» y la tabla de cobertura dicen lo que respondía el 15 de noviembre. **Antes de enviar se ajustan a lo que funcione ese día** (ver «Antes de enviar»): la página no puede decir que algo funciona si no está.

### Project Name

AgroSense

### High-Level Project Summary

> AgroSense is a decision-support web tool that helps small and medium-sized farmers in the Colombian highlands of Boyacá and Cundinamarca explore crop rotation strategies that protect their soil and fit their local climate. For a plot, or just a municipality and an area, it compares up to three-cycle rotation strategies against the rotation the farmer already uses, scoring them by water, soil, income and risk according to the farmer's own priorities. Each cycle gets a sowing-window diagnosis built from NASA data (the NASA POWER reanalysis, NASADEM elevation and GPM IMERG satellite rainfall), global soil data (SoilGrids) and crop data with cited sources. It works from a phone, explains every result in plain language with its data source, and never presents the climate history of the area as a forecast: the decision stays with the farmer.

**Resumen B**, si `/rotations` no responde al enviar (ver «Antes de enviar»). Dice solo lo que funciona el 15 de noviembre:

> AgroSense is a decision-support web tool for small and medium-sized farmers in the Colombian highlands of Boyacá and Cundinamarca. For a crop and a planting date in any of the 239 municipalities of the region, it first checks whether the crop grows there, by the mean annual temperature corrected to the altitude with NASADEM. It then scores the sowing window with signals built from NASA data: water from GPM IMERG satellite rainfall and a FAO-56 water balance with the local soil texture (SoilGrids), and frost and heat from the NASA POWER reanalysis, plus soil pH. A rule-based traffic light, never an average, keeps a severe climate risk from being hidden, and the tool shows the best sowing windows of the next twelve months. Every result says where its data comes from and is never presented as a forecast. The rotation-strategy engine (agronomic filters, five rule-based soil-health criteria, the diagnosis of each cycle and the ranking by the farmer's priorities) is built and tested, but it is not yet connected in this version.

### Link to Project Demo

Pendiente: el video de 30 segundos (guion abajo) o las 7 diapositivas.

### Link to Final Project

Pendiente: la web desplegada con `?lang=en` (HU-023, HU-233, HU-236). El código es público (<https://github.com/FelipeGo18/AgroSense>), pero está en español: ver «Antes de enviar».

### Detailed Project Description

> **What it does.** Planting potato on the same plot season after season builds up pathogens and pests in the soil: FAO and Colombia's ICA advise rotating it with other crops. At the same time, frost, heat and rainfall make planting dates harder to choose. AgroSense helps a farmer answer one question: *what should I plant next on this plot, so I protect the soil and don't lose the harvest to a frost?*
>
> **How it works.** The main flow is: a plot (or a municipality and an area, without an account) → rotation strategies of up to 3 cycles → one cycle with its sowing-window diagnosis → the water each cycle needs → how the climate of the area changed between two historical periods.
>
> 1. **Rotation strategies.** Sequences of crops, green manure and fallow that pass agronomic filter rules (for example, no potato right after potato) and avoid any cycle with a severe climate risk. They are ranked by four criteria (water, soil, income and risk) weighted by the farmer's priorities, and each one is compared against the rotation the farmer already uses. Each strategy also gets a soil-health comparison with five rule-based criteria: nitrogen, organic carbon, soil cover, pest break and erosion.
> 2. **Sowing-window diagnosis.** First, whether the crop grows in that municipality at all, by mean annual temperature. Then six signals (water, frost, heat, soil, supply and market), each scored 0–100 against what that crop needs or tolerates. A traffic light is decided by rules, never by averaging, so a severe risk is never hidden by good signals. If the farmer's priorities give a different light than AgroSense's defaults, both are shown. If the date is not a good one, it shows the best sowing windows of the next twelve months.
> 3. **Water plan.** An estimate of the water each cycle needs month by month, and the months where rain usually falls short.
> 4. **What changed in your area.** Frost, rainfall and heat month by month in two historical periods of the same source, and how the best sowing windows moved. It is compared history, never a forecast.
>
> **Why rules and not machine learning.** The challenge asks, for each strategy, why it is suggested, what evidence supports it, what its benefits could be, where data is missing and what risks the farmer or a local expert should check. AgroSense answers that with explicit rules, each one tied to a cited source (FAO, ICA, Penn State Extension, IGAC, UPRA and others), and with explanations that only cite the indicators and rules that were actually evaluated. When a source is missing, the signal says "insufficient data" instead of filling the gap. The few cut-offs that no source gives are labeled "team criterion" and are pending validation by an agronomist.
>
> **Benefits (potential, not guaranteed).** Rotations with legumes, green manure and fallow can reduce soil wear and pest build-up; the farmer sees climate risk before planting; and NASA data that is hard to use becomes something a farmer can read on a phone. Its limits: it does not predict yields, prices or weather; soil and water results are estimates for the area, not measurements of the plot; NASA POWER is a reanalysis, not a direct satellite observation; and it is a pilot for one region.
>
> **What we hope to achieve.** A tool a farmer or an extension technician can use in a few minutes to compare options, and that a local agronomist can audit, because every result says where it came from.
>
> **Tools.** Python 3.12 (FastAPI, Pydantic, Polars, Shapely, SQLAlchemy and Alembic, pytest), PostgreSQL, React with TypeScript (Vite, Tailwind, TanStack Query and MapLibre), Docker and GitHub Actions. Data is precomputed by a pipeline and published as versioned Parquet files; the decision engine is a pure Python module, and every response carries the dataset and rules version, so the same input always gives the same result.
>
> **What works in this version.** With real data for the 239 municipalities of Boyacá and Cundinamarca (dataset 2026.11.24):
>
> - **Sowing-window diagnosis:** crop suitability by altitude-corrected mean annual temperature; water, frost, heat and soil pH scored 0–100 for the crop; the traffic light with the farmer's priorities and with AgroSense's defaults; and the best sowing windows of the next twelve months, with the rainfall of the window and its sources. Supply and market still show "insufficient data": their data is published (EVA planted area and SIPSA prices), but no published source says what "oversupply" or "a low price" is, so we do not invent a threshold, and the change in planted area is not computed yet.
> - **Accounts:** sign-up with data-processing consent, plots drawn on a map with the soil of their area, planting and harvest records, and account deletion that removes everything.
> - **Wholesale prices** from the Corabastos (Bogotá) and Tunja markets (SIPSA), and a "How it works" page that explains how a result is decided and shows the default weight of each signal with its reason.
> - **Built and tested, not yet connected:** the rotation-strategy engine (agronomic filters, five rule-based soil-health criteria, the diagnosis of each cycle, the ranking by the farmer's priorities and its reasons), so the strategies screen does not show real results yet; and the water-plan API, which already answers but is shown only inside a strategy cycle.
>
> **How the MVP covers the challenge.**
>
> | Challenge | How this version covers it |
> |---|---|
> | NASA Earth observations | NASA POWER (temperature, frost, heat and reference evapotranspiration; a reanalysis, and the app says so), NASADEM (altitude, to correct temperature) and GPM IMERG (satellite rainfall), each through its own adapter |
> | Local soil information | SoilGrids pH and texture of the municipality, with its uncertainty range and the warning that it is an estimate, not a soil test of the plot |
> | Crop characteristics | Cited crop sheets for 7 highland crops and fallow: temperature ranges, frost- and heat-sensitive stages, crop coefficient (Kc) and length of each stage, pH and family |
> | Farmer priorities | A weight from 0 to 5 for each signal; if the farmer's priorities give a different light than AgroSense's defaults, both are shown. A severe climate risk always counts |
> | Changing temperature and rainfall | Frost and heat signals in the crop's sensitive stages, and a water signal with dry-year rainfall and a water balance by stage |
> | Extremes | A critical water, frost or heat risk always turns the light red, and that window never appears among the best ones |
> | Why, evidence, gaps and risks | Every reason cites the indicator or rule that was evaluated; missing data says "insufficient data" instead of being filled in; each rule and dataset has its source |
> | AI (optional) | Explicit, cited rules instead of machine learning (see "Why rules and not machine learning") |

**Para el equipo, las filas de la tabla que todavía no funcionan** (el 15 de noviembre). Se agregan, en inglés, solo si responden al enviar:

| Parte del enunciado | Qué falta | De qué depende |
|---|---|---|
| Explore rotation strategies (al menos tres, incluida la actual) | `/rotations` responde 501 | HU-223 (#153) y HU-084 |
| Strengthen soil health | Los cinco criterios están en el motor, pero solo salen con `/rotations` | HU-084 |
| Adapt to changing conditions («Qué cambió») | Solo responde con un cultivo que no se da en la zona; con uno apto, 501 | HU-217 y HU-218 (#142) |
| Escasez de agua (el agua de cada ciclo) | La API `/water-plans` responde, pero la web la muestra solo en el ciclo de una estrategia | HU-084 |
| Suelo del lote dibujado | Hoy es siempre el del municipio | HU-182 (#143) |
| MODIS NDVI, SMAP y la capa GIBS | El NDVI está publicado, pero solo se ve en el ciclo de una estrategia; SMAP no está publicado; GIBS, en revisión | HU-084, HU-210 y HU-211 (#144) |

### NASA Data

> - **NASA POWER** (daily agroclimatology data, AG community; NASA Langley Research Center): air temperature, frost and heat in each crop stage, mean annual temperature for crop suitability, and the reference evapotranspiration (FAO-56 Penman–Monteith) for the crop water needs. POWER is a reanalysis (a model with observations), and the app says so. https://power.larc.nasa.gov/
> - **NASADEM HGT v001** (1 arc-second, about 30 m; NASA JPL, distributed by LP DAAC): elevation, to correct temperature to the altitude of the municipality or the plot, and slope, which the rotation-strategy engine uses for the erosion criterion. https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001
> - **GPM IMERG Final Run V07, monthly** (NASA and JAXA, GPM mission; distributed by GES DISC): satellite rainfall for the water signal and the water plan, shown next to the POWER rainfall for contrast and never mixed. https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07

Nota para el equipo: MODIS NDVI, SMAP y la capa GIBS solo se agregan aquí si están publicados y en la web el día de enviar (HU-208, HU-210 y HU-211). El 15 de noviembre, el NDVI está publicado (`ndvi_municipality`, desde 2023) pero solo se ve en el ciclo de una estrategia; SMAP no está publicado y GIBS está en revisión (#144). Si las estrategias responden, esta es la línea del NDVI, y se quita la de «NASA data published by our pipeline but not shown in this version» de las referencias:

> - **MODIS Terra NDVI, MOD13Q1 V061** (250 m, every 16 days; NASA, distributed by LP DAAC): how green the municipality usually is in each part of the year, from 2023 on, shown next to each cycle to contrast the sowing windows with what is really planted. It is the greenness of the whole municipality, not of the plot, and it does not change any result. https://doi.org/10.5067/MODIS/MOD13Q1.061

### Space Agency Partner Data and Other References

> - **JAXA** (Space Agency Partner): GPM is a joint NASA–JAXA mission, and IMERG is the GPM rainfall product we use.
> - **NASA data published by our pipeline but not shown in this version:** MODIS Terra NDVI, MOD13Q1 V061 (NASA, distributed by LP DAAC), the greenness of each municipality since 2023. https://doi.org/10.5067/MODIS/MOD13Q1.061
> - **Soil:** SoilGrids 2.0 (ISRIC), pH, organic carbon, nitrogen and texture at 250 m, with its uncertainty range.
> - **Territory:** DIVIPOLA municipality codes and the 2025 national geostatistical framework (DANE, Colombia).
> - **Market:** SIPSA wholesale prices (DANE, Colombia).
> - **Supply:** Evaluaciones Agropecuarias Municipales, EVA 2019–2025 (UPRA, Colombia): planted area by municipality, crop and semester.
> - **Crop sheets and agronomic rules:**
>   - FAO: FAO-56 *Crop evapotranspiration* (Allen, Pereira, Raes and Smith, 1998), tables 11, 12 and 22; FAO-66 *Crop yield response to water* (Steduto et al., 2012); *Irrigation Water Management*, training manual 3 (Brouwer and Heibloem, 1986), effective rainfall; EcoCrop; *Frost protection: fundamentals, practice and economics* (Snyder and de Melo-Abreu, 2005); Land & Water crop information (potato); *International Year of the Potato 2008*; *The International Year of Pulses, final report* (2019); Soils Bulletin 55 (1985); GLOSOLAN SOP-02 (soil organic carbon, Walkley-Black).
>   - Colombia: UPRA crop zoning for Diacol Capiro potato and bulb onion; Agrosavia, potato rotation systems in Tibaitatá (Vargas Díaz, Wilches Ortiz and Espitia Malagón); CEVIPAPA, first national workshop on potato soils and nutrition (2005); ICA, potato purple top; IGAC, land capability classification (2021); Cenicafé, regionalization of air temperature in Colombia (Chaves Córdoba and Jaramillo Robledo, 1999).
>   - Soil water and texture: USDA NRCS, *National Engineering Handbook* part 652, chapter 2; USDA soil texture triangle.
>   - Frost, heat and water stress: FEWS NET Water Requirement Satisfaction Index (USGS); Brazil's agricultural climate-risk zoning, ZARC (MAPA, 2025); SENAMHI and FAO, frost atlas of Peru (2010); Fairlie and Ortega (1995); Barrales Domínguez et al. (2002); Alharbi et al. (2021); Purdue University, drought and heat stress on corn pollination (Nielsen); Saskatchewan Pulse Growers, environmental stresses in pulses (2023).
>   - Crop guides: Penn State Extension, plant rotation based on plant families (Sánchez and Demchak); Michigan State University Extension E1307 (onions) and E1437 (carrots); NDSU Extension A1166 (field pea); UC ANR 7226 (carrot production in California); CIREN-CORFO, climate and soil requirements (Chile, 1989); Universidad Nacional de Luján, horticulture sheets.
>   - AgroSense team: the few soil-health cut-offs that no source gives, labeled "team criterion" and pending validation by an agronomist; and the visual crop catalog of the app.
> - **Every source above, with its link and its license or terms of use, and every third-party library**, is listed in `docs/licencias.md` in the public repository (in Spanish): https://github.com/FelipeGo18/AgroSense

## Guion del video de 30 segundos

Sigue los tiempos que propone la guía. Se puede grabar en español con subtítulos en inglés; abajo va el texto en inglés. El recorrido completo para el jurado local está en `docs/guion-demo.md` (HU-131).

| Tiempo | Qué se ve | Texto (inglés) |
|---|---|---|
| 0:00–0:02 | El logo y el equipo | "We are RealE4Life." |
| 0:02–0:05 | Una ladera del altiplano | "Field Shift: farmers need rotations that protect the soil and survive changing weather." |
| 0:05–0:10 | El inicio de AgroSense | "AgroSense helps them explore rotation strategies with NASA data." |
| 0:10–0:20 | Las estrategias comparadas contra la rotación actual, y un ciclo con su diagnóstico | "It compares rotations against what the farmer already does, using NASA POWER, NASADEM and GPM IMERG, with every result explained and sourced." |
| 0:20–0:30 | El lote dibujado en el mapa de Mi finca | "Our goal: healthier soil and fewer lost harvests, with the farmer always making the final decision." |

Si `/rotations` no responde al enviar, el tramo 0:10–0:20 muestra el diagnóstico de una siembra (la luz, las señales y las mejores ventanas), con este texto: "For a crop and a planting date, it scores the sowing window with NASA POWER, NASADEM and GPM IMERG, with every result explained and sourced."
