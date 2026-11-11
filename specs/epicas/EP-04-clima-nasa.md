---
id: EP-04
titulo: "Datos de la NASA publicados para el núcleo"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Datos"
agentes: [datos]
subsistemas: [D1, D2, D3, D4]
depende_de: [HU-002, HU-011]
reglas: [R1, R5, R7, R8, R10]
estado: pendiente
---

# EP-04 · Datos de la NASA publicados para el núcleo

**Resultado esperado:** Las tablas de la región con lo que da la NASA: el clima de NASA POWER (lluvia, temperatura corregida por altitud, humedad del suelo modelada y la ET0 por Penman-Monteith), la altitud de NASADEM, la lluvia por satélite de GPM IMERG, el verdor de MODIS NDVI por municipio y por lote, la humedad del suelo de SMAP y el clima de dos periodos para «Qué cambió». Con ellas el motor evalúa cualquier ventana de siembra y cualquier estrategia de rotación.

**La NASA es el núcleo (decisión 12).** Cada producto entra por su propio adaptador (`nasa_power`, `nasadem`, `imerg`, `modis_ndvi`, `smap`) y publica tablas versionadas. `sources.yaml` dice qué producto calcula cada señal en cada región. Si un producto falta, la señal o el indicador es `insufficient_data` (R1). Ningún producto cambia el motor (R6). Lo que recomiende el enunciado del 28 de octubre (HU-002) entra por el mismo mecanismo.

**Orden de recorte (decisión 12):** primero SMAP (HU-210), luego la capa GIBS de la web (HU-211, EP-16), luego el NDVI por lote (HU-209; queda el del municipio). POWER, NASADEM e IMERG no se recortan.

Ninguna tabla de clima va por semestre: el semestre solo existe en la oferta de EVA (EP-03).

**Región piloto (decisión 11):** confirmada el 28 de octubre de 2026: Boyacá y Cundinamarca, con sede en Duitama (HU-002). Los productos NASA cubren todo el mundo, pero varias piezas de esta épica son de Colombia: los municipios y sus límites del DANE, el criterio de helada de la UPRA con datos del IDEAM, la comprobación contra estaciones del IDEAM y contra la Gobernación de Boyacá. Esas piezas viven en los adaptadores y en la configuración del pipeline, no en el motor (R7). Si la región cambia, se reemplazan con su fuente.

**Acceso:** IMERG, NASADEM, MODIS y SMAP piden una cuenta de NASA Earthdata (por verificar para cada producto). Las credenciales van en variables de entorno, nunca en el repositorio. Con la caché, el dataset se reconstruye sin volver a descargar (HU-123).

## Historias de usuario

### HU-041 · Series diarias de lluvia y temperatura

- **Historia:** Como motor, quiero series diarias de lluvia y temperatura por municipio, para evaluar el clima de cada ventana de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Descarga con caché y reintentos
  - [ ] Fuente y fecha registradas
  - [ ] Días faltantes o incompletos marcados en `quality` (`climate_day`); nunca se rellenan (R1)
  - [ ] Publica `climate_day` (mínima y máxima diarias corregidas por altitud), de la que salen las heladas, el calor y «Qué cambió» (HU-045, HU-216)
- **Notas:** La etapa por temperatura acumulada que también la usa (HU-150) pasó a P1 el 11 de octubre de 2026.

### HU-042 · Lluvia mensual y su normal

- **Historia:** Como motor, quiero la lluvia de cada mes de cada año y su normal por municipio, para saber cuánta agua suele caer en los meses de una ventana de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_month` con `precip_mm` por `municipality_id`, `year` y `month`, y `precip_normal_mm`, con `quality` y `source_id`
  - [ ] Periodo base de la normal documentado
  - [ ] Comprobación manual en 2 municipios
  - [ ] Calidad `partial` bajo un mínimo de días válidos; un mes sin días válidos no se publica con un valor rellenado (R1)
- **Reglas que aplican:** R1, R7, R8
- **Contrato que toca:** `climate_month`
- **Notas:** Antes publicaba el total y la anomalía de un periodo fijo de seis meses, en una tabla que ya no existe: cambió el 11 de octubre de 2026. El año seco (`precip_dry_mm`) y la ET0 de la misma tabla los agrega HU-143. Es la lluvia de NASA POWER, la serie larga desde 1981; la lluvia por satélite es HU-207 y va en otra tabla (`precip_month`). La señal de agua (HU-071) y la serie `water` de `/trends` leen la fuente que dice `sources.yaml`.

### HU-205 · NASA POWER ampliado: humedad, radiación y viento

- **Historia:** Como motor, quiero la humedad del suelo modelada, la radiación, el viento y la humedad relativa de NASA POWER por municipio, para calcular la ET0 por Penman-Monteith y mostrar la humedad del suelo junto a la señal de agua.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El adaptador `nasa_power` descarga, además de la lluvia y la temperatura, la humedad del suelo superficial y de la zona de raíces (`GWETTOP`, `GWETROOT`), la radiación solar, el viento a 2 m y la humedad relativa (`RH2M`), con caché y reintentos. Los nombres exactos de la radiación y del viento se verifican en la documentación de POWER antes de usarlos
  - [ ] Desde qué año hay datos de cada variable queda verificado y documentado (la serie de lluvia y temperatura empieza en 1981; la de radiación puede empezar después)
  - [ ] `climate_month` gana `soil_wetness_top` y `soil_wetness_root` (fracción de 0 a 1, promedio del mes), con `quality`
  - [ ] La entrada de NASA POWER en `sources` dice que es un **reanálisis** (un modelo con observaciones asimiladas), no una observación directa, y que su celda mide unos 50 km
  - [ ] Días faltantes marcados en `quality`; nunca se rellenan (R1)
  - [ ] Comprobación manual en 2 municipios
- **Reglas que aplican:** R1, R7, R8, R10
- **Contrato que toca:** `climate_month` (`soil_wetness_top`, `soil_wetness_root`), `sources`
- **Notas:** Decisión 12. La ET0 por Penman-Monteith con estas variables es HU-143. En el MVP la humedad no cambia la calificación de `water`: se muestra para contrastar (HU-071), junto a la de SMAP (HU-210). Es la serie larga para «Qué cambió» (HU-216). Agregada el 11 de octubre de 2026.

### HU-206 · Altitud de municipios y lotes con NASADEM

- **Historia:** Como motor, quiero la altitud de cada municipio y de cada lote desde NASADEM, para decidir si un cultivo se da en la zona y corregir la temperatura.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `nasadem` con caché: descarga los mosaicos de NASADEM (30 m) que cubren la región
  - [ ] `municipalities.altitude_m` sale de NASADEM con un método documentado (supuesto por confirmar: la mediana de las celdas dentro del polígono municipal o la altitud de la cabecera)
  - [ ] Publica la altitud (promedio de los píxeles de 30 m) en `grid_cells`, la rejilla común de 250 m (decisión 15), para que la API calcule la altitud de un lote como la mediana de las celdas de su polígono, igual que el suelo (HU-182)
  - [ ] Entrada de NASADEM en `sources` con producto, versión, resolución, acceso y licencia
  - [ ] Comprobación manual en 2 municipios contra la altitud oficial de la cabecera
  - [ ] **Pendiente (decisión 14):** la pendiente se calcula a 30 m y `grid_cells.slope_pct` guarda la mediana de cada celda; `municipalities.slope_pct`, la del municipio. La de un lote la calcula la API al vuelo, como la altitud. La usa el criterio `erosion` (HU-224)
  - [ ] Sin celdas válidas, `altitude_m` queda nulo y la aptitud es `insufficient_data` (R1)
- **Reglas que aplican:** R1, R7, R8, R9
- **Contrato que toca:** `municipalities.altitude_m`, `municipalities.slope_pct`, `grid_cells`
- **Notas:** Decisión 12. Reemplaza al «modelo de elevación por elegir» de HU-044. La altitud del lote no se guarda: la API la calcula al vuelo (R9). Con un lote dibujado, la aptitud usa la temperatura media corregida a la altitud del lote (`specs/01-reglas.md`, «Aptitud del cultivo en la zona», decisión 13). Supuesto por confirmar: en el MVP la corrección de la temperatura sigue usando la altitud del municipio, porque los indicadores de clima se precalculan por municipio; corregir por la altitud del lote necesita una decisión. No se recorta. Agregada el 11 de octubre de 2026.

### HU-207 · Lluvia por satélite con GPM IMERG

- **Historia:** Como motor, quiero la lluvia observada por satélite en cada municipio, para calcular la señal de agua con una observación y contrastarla con la serie larga de NASA POWER.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `imerg` con caché: lluvia de la corrida final (Final Run) de GPM IMERG, celdas de unos 10 km (0,1°), desde junio de 2000. El producto exacto (diario o mensual) y su versión se verifican antes de usarlo
  - [ ] Descarga solo el recuadro de la región (subconjunto espacial); el tamaño de la descarga queda medido y documentado
  - [ ] `precip_month` por `municipality_id`, `year`, `month` y `source_id`, con `precip_mm` (promedio de las celdas que tocan el polígono del municipio, ponderado por área), `precip_normal_mm`, `precip_dry_mm`, `normal_period` y `quality`
  - [ ] La normal de IMERG dice su periodo (desde 2001); nunca se completa con años de POWER (R1, decisión 11)
  - [ ] `sources.yaml` dice para la región qué fuente de lluvia calcula `water`: IMERG si cubre la región; si no, POWER. La otra se muestra para contrastar
  - [ ] Comprobación manual en 2 municipios: lluvia mensual de IMERG frente a POWER y, si la hay, frente a una estación de la región. Las diferencias se anotan; no se corrigen
  - [ ] Un mes con pocos datos válidos queda `partial`; sin datos, la fila no se publica (R1)
- **Reglas que aplican:** R1, R7, R8
- **Contrato que toca:** `precip_month`, `sources`
- **Notas:** Decisión 12. No se recorta. Antes estaba descartado del P0 por el trabajo con mallas (`specs/04-stack.md`); ese costo se aceptó el 11 de octubre de 2026. El método de calibración de la versión que se use se cita de su documentación. Riesgo: el tamaño de la descarga (`docs/riesgos.md`). Agregada el 11 de octubre de 2026.

### HU-208 · Verdor del campo por municipio con MODIS NDVI

- **Historia:** Como motor, quiero el NDVI de cada municipio cada 16 días y su normal, para mostrar en qué épocas suele estar verde el campo de la zona y estimar la cobertura del suelo de las estrategias.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `modis_ndvi` con caché: MOD13Q1 (satélite Terra, 250 m, compuesto de 16 días, desde febrero de 2000), recortado a la región. La versión se verifica antes de usarlo
  - [ ] Usa la capa de calidad del producto para descartar los píxeles con nubes; el porcentaje de píxeles válidos queda en `valid_pixels_pct`
  - [ ] `ndvi_municipality` por `municipality_id`, `year` y `period` (1 a 23, el compuesto de 16 días del año), con `ndvi_median`, `valid_pixels_pct`, `quality` y `source_id`
  - [ ] `ndvi_municipality_normal` por `municipality_id` y `period`, con `ndvi_normal`, `years`, `quality` y `source_id`
  - [ ] Si se usa una máscara de áreas de cultivo, lleva su fuente (por elegir). Sin máscara, el valor es de todo el municipio y la respuesta lo dice
  - [ ] Con menos píxeles válidos que el mínimo de la configuración del pipeline, el periodo queda `partial` o no se publica; nunca se interpola en silencio (R1)
  - [ ] `/trends` suma la serie `ndvi` con la normal del municipio (HU-078)
  - [ ] Comprobación manual en 2 municipios: los picos de verdor caen en épocas coherentes con las temporadas de siembra de la región
- **Reglas que aplican:** R1, R5, R7, R8, R10
- **Contrato que toca:** `ndvi_municipality`, `ndvi_municipality_normal`, serie `ndvi` de `GET /api/v1/trends`
- **Notas:** Decisión 12. El NDVI es contraste, no señal: no cambia la luz ni el orden de las ventanas. La cobertura del suelo de las estrategias (`soil_cover`, HU-212) lo usa cuando existe. Las nubes del altiplano dejan huecos (`docs/riesgos.md`). Agregada el 11 de octubre de 2026.

### HU-209 · Verdor por lote con MODIS NDVI

- **Historia:** Como motor, quiero el verdor normal de las celdas de 250 m que toca un lote, para estimar en qué meses ha tenido el suelo cubierto.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `ndvi_grid` por `cell_id` (el de `grid_cells`) y `period`, con `ndvi_normal`, `years`, `valid_pct`, `quality` y `source_id`, desde los mismos datos de HU-208, solo para las celdas de los municipios con lotes
  - [ ] La API calcula el verdor del lote como la mediana de las celdas que toca su polígono, igual que el suelo (HU-182); sin polígono usa el del municipio y lo dice en `basis`
  - [ ] Se dice siempre que una celda mide 250 m por 250 m (6,25 ha), más que muchos lotes, y que puede mezclar el lote con sus vecinos (R10)
  - [ ] El verdor del lote no se guarda en la base de datos (R9)
  - [ ] Prueba: un lote más chico que una celda usa la celda que lo contiene y lo dice
- **Reglas que aplican:** R6, R9, R10
- **Contrato que toca:** `ndvi_grid`
- **Notas:** Decisión 12. **Pasó a P1 el 8 de noviembre de 2026 (decisión 15):** a 250 m y con 23 periodos, toda la región serían unos 14 millones de filas; en el P0 el verdor es el del municipio (HU-208). El verdor por lote a 30 m es HU-043 (P1). Agregada el 11 de octubre de 2026.

### HU-210 · Humedad del suelo por satélite con SMAP

- **Historia:** Como agricultor, quiero ver la humedad del suelo que estima el satélite en mi zona junto a la que modela NASA POWER, para contrastar el agua de mi ventana y de mi plan.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `smap` con caché: humedad superficial y de la zona de raíces de SMAP nivel 4 (celdas de 9 km, desde marzo de 2015). Producto, versión y profundidades se verifican antes de usarlo
  - [ ] `soil_moisture_month` por `municipality_id`, `year`, `month` y `source_id`, con `sm_surface_m3_m3`, `sm_rootzone_m3_m3` y `quality`
  - [ ] Sus unidades (m³/m³) son distintas de las de POWER (fracción de 0 a 1): nunca se convierten una en otra ni se promedian; se muestran lado a lado (decisión 11)
  - [ ] Aparece en `signals.water.sources` y en el plan de agua como contraste (`used = false`); no cambia la calificación (R1, R2)
  - [ ] Sin datos para un municipio o un mes, no aparece; nunca se rellena (R1)
  - [ ] Comprobación manual en un municipio
- **Reglas que aplican:** R1, R8, R10
- **Contrato que toca:** `soil_moisture_month`, `signals.water.sources`
- **Notas:** Decisión 12. **Desde el 8 de noviembre de 2026 (decisión 14) ya no es lo primero que se recorta:** el enunciado completo lo nombra primero entre los datos sugeridos, así que va al final de lo recortable de la NASA. La serie es corta (desde 2015): no sirve para normales largas ni para «Qué cambió». Agregada el 11 de octubre de 2026.

### HU-216 · Clima de dos periodos para «Qué cambió»

- **Historia:** Como motor, quiero los indicadores de clima de dos periodos de la misma fuente, para comparar cómo cambió la zona.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Los periodos viven en la configuración versionada del pipeline, cada uno con `period_id`, año inicial y año final. Por defecto, con POWER, `p1981_2000` (1981–2000) y `p2005_2024` (2005–2024); con IMERG, dos periodos desde 2001 (por defecto 2001–2012 y 2013–2024), y la respuesta lo dice. `manifest.json` los lista (R4)
  - [ ] `climate_change_month` por `municipality_id`, `period_id`, `month` y `source_id`, con `frost_freq_pct` y `tmax_p90_c` (de POWER), `precip_normal_mm` (de cada fuente de lluvia), `years` y `quality`
  - [ ] Mismo umbral de helada y misma corrección por altitud que HU-045
  - [ ] Los dos periodos de una comparación son de la misma fuente; nunca se mezclan fuentes entre periodos (decisión 11)
  - [ ] Un mes de un periodo con menos años válidos que el mínimo de la configuración no se publica; la comparación de ese mes queda `insufficient_data` (R1)
  - [ ] Comprobación manual en 2 municipios
- **Reglas que aplican:** R1, R4, R7, R8
- **Contrato que toca:** `climate_change_month`, `manifest.json`
- **Notas:** Decisión 12. Es historia comparada, nunca pronóstico. La lluvia por año de cada periodo ya está en `climate_month` y `precip_month`: el motor filtra los años del periodo para recalcular el agua de las ventanas (HU-217). Agregada el 11 de octubre de 2026.

### HU-044 · Municipios, límites, altitud y corrección de la temperatura

- **Historia:** Como motor, quiero la altitud de cada municipio y la de su celda de NASA POWER, para corregir la temperatura y filtrar cultivos por piso térmico.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] `altitude_m` desde NASADEM (HU-206), con fuente
  - [ ] `climate_cell_elevation_m` desde la respuesta de NASA POWER
  - [ ] Todas las temperaturas publicadas se corrigen con un gradiente térmico con fuente; el gradiente vive en la configuración del pipeline
  - [ ] Comprobación manual en 2 municipios contra una estación del IDEAM, si la hay
- **Reglas que aplican:** R7, R8
- **Notas:** También publica `municipalities` (con `source_ids`) y `municipality_boundaries` desde el Marco Geoestadístico Nacional del DANE, que usan HU-164, HU-181 y HU-078. Pasa a P0 el 10 de octubre de 2026 porque las heladas dependen de la temperatura mínima, y la celda de unos 50 km puede estar cientos de metros más arriba o más abajo que el municipio. Desde el 11 de octubre de 2026 la altitud sale de NASADEM (HU-206, decisión 12). **15 de octubre de 2026:** adelantada la parte de municipios (decisión de Felipe, para los lotes): `pipeline/sources/dane.py` publica `municipalities` desde DIVIPOLA del DANE (datos.gov.co, CC BY-SA 4.0) para Boyacá y Cundinamarca (`pipeline/region.yaml`, supuesto hasta el 28 de octubre), con `sources` y `manifest.json`; 239 municipios. `altitude_m` y `climate_cell_elevation_m` van nulas hasta NASADEM y NASA POWER. El 15 de octubre de 2026 se publicaron los límites (`municipality_boundaries`) desde el servicio MGN 2025 del geoportal del DANE (`pipeline/sources/dane_mgn.py`), simplificados a unos 10 m; los 239 puntos de DIVIPOLA caen dentro de su límite. Faltan la altitud y la corrección de la temperatura. Pruebas en `tests/pipeline/test_municipios.py`.

### HU-045 · Heladas y temperatura máxima por mes

- **Historia:** Como motor, quiero saber en qué meses suele helar y qué tan alta suele ser la temperatura máxima en cada municipio, para evaluar las heladas y el calor de cada ventana de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_risk_month` con `frost_freq_pct`, `frost_days_mean`, `tmax_p90_c`, `years` y `quality`, desde la mínima y la máxima diarias corregidas por altitud
  - [ ] Umbral de helada: mínima **menor o igual a 2 °C** a 2 m, con fuente, en la configuración del pipeline (decidido por Felipe el 10 de noviembre de 2026: es el criterio del ZARC de Brasil, `mapa_zarc_2025`, el mismo de `docs/investigacion-decisiones.md`; el boletín de la UPRA de enero de 2024 ya no está en su enlace)
  - [ ] `tmax_p90_c` es la temperatura máxima que se supera uno de cada diez días de ese mes; el método queda documentado
  - [ ] `climate_frost_month`: los días con helada de cada mes de cada año (`frost_days`, `valid_days`, `quality`), para que la señal de heladas cuente los años con helada de una ventana (HU-077). Agregado el 10 de noviembre de 2026, aprobado por Felipe el 10 de noviembre de 2026
  - [ ] Comprobación: los meses con más heladas en el altiplano caen entre diciembre y marzo, como dicen la Gobernación de Boyacá y el IDEAM
  - [ ] Con pocos años o pocos días válidos, `quality = partial`; sin datos, la fila no se publica (R1)
- **Reglas que aplican:** R1, R8
- **Contrato que toca:** `climate_risk_month`
- **Notas:** Antes se llamaba «Frecuencia de heladas por mes»; sumó `tmax_p90_c` el 11 de octubre de 2026 para la señal de calor (HU-190). En el MVP las señales de heladas y calor leen esta tabla por mes; la versión por semana (HU-193) pasó a P1.

### HU-193 · Riesgo climático por semana

- **Historia:** Como motor, quiero el riesgo de helada, la temperatura máxima, la lluvia y la ET0 normales por semana del año en cada municipio, para comparar ventanas de siembra dentro de un mismo mes.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_risk_week` por `municipality_id` y `week` (1 a 52; los días 365 y 366 van a la semana 52) con `frost_freq_pct`, `tmax_p90_c`, `precip_normal_mm`, `precip_dry_mm`, `et0_normal_mm`, `years`, `quality` y `source_id`, según el contrato
  - [ ] Cada valor se suaviza con las semanas vecinas; el método y el ancho del suavizado quedan documentados y viven en la configuración del pipeline
  - [ ] Mismas temperaturas corregidas por altitud y mismo umbral de helada que HU-045
  - [ ] Unicidad de la llave: 52 filas por municipio (R7)
  - [ ] Comprobación manual en 2 municipios: las semanas de un mes son coherentes con el valor de ese mes en `climate_risk_month`
  - [ ] Con pocos años válidos, `quality = partial`; nunca se rellena una semana sin datos (R1)
- **Reglas que aplican:** R1, R7, R8
- **Contrato que toca:** `climate_risk_week`
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP (en el MVP las ventanas se comparan por mes). El dato semanal es más ruidoso que el mensual: por eso se suaviza y se presenta como orientación (`docs/riesgos.md`). Supuesto por confirmar: qué es exactamente «un año con helada» en una semana suavizada. Depende de HU-041 y HU-044; la ET0 usa el método de HU-143. Cuando exista, la usan HU-077, HU-190 y HU-192. Las columnas del P1 las agrega HU-046. Agregada el 11 de octubre de 2026.

### HU-043 · Verdor por lote con HLS (30 m)

- **Historia:** Como agricultor, quiero ver el verdor de mi lote con más detalle que el de MODIS, para seguir mi cultivo y la cobertura de mi suelo.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] NDVI de HLS (Harmonized Landsat Sentinel-2, de la NASA, 30 m) por polígono de lote, con su fecha
  - [ ] Mismas reglas de calidad que HU-208: píxeles con nubes fuera, porcentaje válido visible, nunca se interpola en silencio (R1)
- **Reglas que aplican:** R1, R8, R10
- **Notas:** El 11 de octubre de 2026 cambió de «Humedad del suelo y NDVI»: la humedad del suelo y el NDVI de MODIS pasaron al P0 (HU-205, HU-208, HU-209 y HU-210, decisión 12). Queda HLS, más fino que MODIS: un lote de 1,5 ha cubre unos 16 píxeles de 30 m. Las nubes del altiplano dejan huecos.

### HU-046 · Aguaceros, ventanas secas y gota por mes

- **Historia:** Como agricultor, quiero saber en qué meses suelen caer aguaceros, cuándo hay días secos seguidos y cuándo el clima favorece la gota, para decidir cuándo abonar, cuándo hacer labores y cosechar, y cuándo vigilar mi papa.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `heavy_rain_days_mean`, `dry_window_freq_pct` y `blight_days_mean` en `climate_risk_month` y en `climate_risk_week`, con umbrales con fuente
  - [ ] La gota usa humedad relativa (`RH2M`) y temperatura de NASA POWER con una regla publicada
- **Notas:** Ver `docs/investigacion-decisiones.md`. La humedad de NASA POWER es de celda de unos 50 km: se presenta como orientación. Con estos datos el motor arma las señales `excess_rain`, `disease` y `harvest_weather` (HU-195).

### HU-188 · Riesgos que cubre un seguro, por municipio

- **Historia:** Como agricultor, quiero saber qué tan seguido han ocurrido en mi zona los riesgos que cubre un seguro agropecuario, para decidir si aseguro la cosecha.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Frecuencia histórica por municipio y mes de helada, sequía y exceso de lluvia, con umbrales con fuente
  - [ ] La web la muestra en «Próxima siembra» con el enlace oficial al Incentivo al Seguro Agropecuario
  - [ ] No recomienda un seguro, una aseguradora ni un producto; es frecuencia histórica, no pronóstico
- **Reglas que aplican:** R5, R8
- **Notas:** Ver `docs/investigacion-decisiones.md`, decisión 9. Agregada el 11 de octubre de 2026.

### HU-189 · Lluvia en años de El Niño y La Niña

- **Historia:** Como agricultor, quiero ver cómo fue la lluvia de los meses de mi ventana de siembra en los años de El Niño y de La Niña del pasado, para saber qué tanto cambia mi zona en esos años.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Lluvia de cada mes por municipio en años El Niño, La Niña y neutros, frente al promedio de los neutros, con el índice y su fuente; la web suma los meses de la ventana
  - [ ] La web la muestra en «Próxima siembra» con el enlace al boletín oficial
  - [ ] No dice en qué fase estamos ni la presenta como pronóstico propio: la fase actual solo se cita del boletín oficial
- **Reglas que aplican:** R5, R8
- **Notas:** Ver `docs/investigacion-decisiones.md`, decisión 10. Cómo mostrar la fase actual sigue por decidir. Agregada el 11 de octubre de 2026.

### HU-225 · Tendencia del agua almacenada con GRACE-FO

- **Historia:** Como agricultor, quiero ver si el agua almacenada de mi región viene bajando o subiendo, para entender si el agua que tengo hoy es la que tendré.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `grace` con caché: anomalía mensual del agua almacenada (TWS) de GRACE y GRACE-FO, producto y versión verificados (candidato: las soluciones mascon del JPL), desde 2002, con el hueco de 2017–2018 entre las dos misiones dicho, no rellenado (R1)
  - [ ] Publica una tabla por municipio con la celda que lo contiene, el mes y la anomalía, y la tendencia de largo plazo con su periodo
  - [ ] Se muestra en «Qué cambió» (HU-219) como **tendencia de la región**, con su resolución (celdas de cientos de kilómetros) y el rótulo de que no es del lote (R10)
  - [ ] Es historia comparada, nunca pronóstico (decisión 4); no cambia ninguna señal ni ningún resultado
  - [ ] Entrada en `sources` con producto, versión, resolución, acceso y licencia (R8)
- **Reglas que aplican:** R1, R4, R8, R10
- **Contrato que toca:** tabla nueva, por definir en esta HU; `GET /api/v1/changes`
- **Notas:** Decisión 14: el enunciado completo sugiere GRACE y GRACE-FO para las tendencias del agua de largo plazo. Agregada el 8 de noviembre de 2026.

### HU-226 · Temperatura de la superficie y evapotranspiración con ECOSTRESS

- **Historia:** Como agricultor, quiero ver el estrés por calor y el agua que pierde el campo de mi zona según ECOSTRESS, para contrastarlos con la señal de calor y el agua del plan.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador `ecostress` con caché: temperatura de la superficie y evapotranspiración (70 m), producto y versión verificados, con las fechas de cada pasada (son irregulares)
  - [ ] Publica agregados por municipio y mes con cuántas pasadas tiene cada mes; un mes sin pasadas no aparece (R1)
  - [ ] Se muestra junto a la señal de calor y al agua del plan como contraste, con su fuente y su resolución, nunca mezclada con POWER (decisión 11) y sin cambiar la calificación
  - [ ] Entrada en `sources` (R8)
- **Reglas que aplican:** R1, R8, R10
- **Contrato que toca:** tabla nueva, por definir en esta HU
- **Notas:** Decisión 14: el enunciado completo sugiere ECOSTRESS para el estrés por calor y la evaporación. La serie empieza en 2018 y las pasadas no son regulares: sirve de contraste, no para normales. Agregada el 8 de noviembre de 2026.
