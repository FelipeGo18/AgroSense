# Entrega a NASA Space Apps 2026

HU-132. Borrador de los campos de la página del proyecto en Space Apps, según la [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/). **La página y todo lo que se enlace va en inglés**: por eso los textos de los campos están en inglés. Las notas para el equipo van en español.

## Lo que pide la guía (leída el 14 de noviembre de 2026)

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

- [ ] Completar «What works in this version» (abajo) con lo que de verdad responde ese día, y quitar de los textos lo que no esté.
- [ ] Volver a generar `docs/licencias.md` (`uv run python scripts/licencias.py`): hoy lista 39 fuentes y el dataset publicado trae 41.
- [ ] El enlace del proyecto: el dominio o la dirección de Cloud Run con `?lang=en` (HU-023, HU-233 y HU-236).
- [ ] **Todo lo enlazado en inglés.** El repositorio está en español: si se enlaza (en «Link to Final Project» o en las referencias), necesita al menos un README en inglés en la raíz, y las referencias en inglés (por ejemplo, la lista de fuentes y licencias). Decidirlo antes de enviar.
- [ ] El video de 30 segundos (o las 7 diapositivas), subido con enlace público y probado en una ventana privada.
- [ ] Probar en una ventana privada cada enlace de la página.
- [ ] Revisar que ninguna imagen ni video tenga personas menores de 18 años.
- [ ] Las imágenes del video (por ejemplo, la ladera del altiplano) son propias o tienen una licencia que lo permita, y van en las referencias.
- [ ] Que el texto de los campos no diga que algo funciona si no está en `desarrollo` y desplegado.

## Campos de la página

Los textos describen el MVP completo. **Antes de enviar se ajustan a lo que funcione ese día** (ver «Antes de enviar»): la página no puede decir que algo funciona si no está.

### Project Name

AgroSense

### High-Level Project Summary

> AgroSense is a decision-support web tool that helps small and medium-sized farmers in the Colombian highlands of Boyacá and Cundinamarca explore crop rotation strategies that protect their soil and fit their local climate. For a plot, or just a municipality and an area, it compares up to three-cycle rotation strategies against the rotation the farmer already uses, scoring them by water, soil, income and risk according to the farmer's own priorities. Each cycle gets a sowing-window diagnosis built from NASA data (the NASA POWER reanalysis, NASADEM elevation and GPM IMERG satellite rainfall), global soil data (SoilGrids) and crop data with cited sources. It works from a phone, explains every result in plain language with its data source, and never presents the climate history of the area as a forecast: the decision stays with the farmer.

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
> **What works in this version.** *(Se completa justo antes de enviar, con lo que de verdad responde ese día.)*

**Cómo cubre el MVP cada parte del enunciado:** la tabla de `specs/00-vision.md` («Cómo cubre el MVP cada parte del enunciado»), traducida, va en la descripción solo con las filas que estén funcionando al enviar.

### NASA Data

> - **NASA POWER** (daily agroclimatology data, AG community; NASA Langley Research Center): air temperature, frost and heat in each crop stage, mean annual temperature for crop suitability, and the reference evapotranspiration (FAO-56 Penman–Monteith) for the crop water needs. POWER is a reanalysis (a model with observations), and the app says so. https://power.larc.nasa.gov/
> - **NASADEM HGT v001** (1 arc-second, about 30 m; NASA JPL, distributed by LP DAAC): elevation, to correct temperature to the altitude of the municipality or the plot, and slope, for the erosion criterion. https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001
> - **GPM IMERG Final Run V07, monthly** (NASA and JAXA, GPM mission; distributed by GES DISC): satellite rainfall for the water signal and the water plan, shown next to the POWER rainfall for contrast and never mixed. https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07

Nota para el equipo: MODIS NDVI, SMAP y la capa GIBS solo se agregan aquí si están publicados y en la web el día de enviar (HU-208, HU-210 y HU-211).

### Space Agency Partner Data and Other References

> - **JAXA** (Space Agency Partner): GPM is a joint NASA–JAXA mission, and IMERG is the GPM rainfall product we use.
> - **Soil:** SoilGrids 2.0 (ISRIC), pH, organic carbon, nitrogen and texture at 250 m, with its uncertainty range.
> - **Territory:** DIVIPOLA municipality codes and the 2025 national geostatistical framework (DANE, Colombia).
> - **Market:** SIPSA wholesale prices (DANE, Colombia).
> - **Crops and rotation rules:** FAO-56, FAO EcoCrop, UPRA crop zoning, Agrosavia (potato–oat–pea rotation in Tibaitatá), ICA, IGAC, CEVIPAPA and other cited publications.
> - **Every source, with its license or terms of use, and every third-party library**, is listed in `docs/licencias.md` in the public repository: https://github.com/FelipeGo18/AgroSense

## Guion del video de 30 segundos

Sigue los tiempos que propone la guía. Se puede grabar en español con subtítulos en inglés; abajo va el texto en inglés. El recorrido completo para el jurado local está en `docs/guion-demo.md` (HU-131).

| Tiempo | Qué se ve | Texto (inglés) |
|---|---|---|
| 0:00–0:02 | El logo y el equipo | "We are RealE4Life." |
| 0:02–0:05 | Una ladera del altiplano | "Field Shift: farmers need rotations that protect the soil and survive changing weather." |
| 0:05–0:10 | El inicio de AgroSense | "AgroSense helps them explore rotation strategies with NASA data." |
| 0:10–0:20 | Las estrategias comparadas contra la rotación actual, y un ciclo con su diagnóstico | "It compares rotations against what the farmer already does, using NASA POWER, NASADEM and GPM IMERG, with every result explained and sourced." |
| 0:20–0:30 | El lote dibujado en el mapa de Mi finca | "Our goal: healthier soil and fewer lost harvests, with the farmer always making the final decision." |
