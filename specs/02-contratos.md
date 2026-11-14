# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado: congelado el 8 de noviembre de 2026** (decisión 15, aprobado por Felipe). Se revisó completo y se llenaron sus huecos: una sola rejilla de 250 m (`grid_cells`), la forma de `rotation_rules`, `thresholds.yaml` y `sources.yaml`, las respuestas de `/water-plans` y `/trends`, las fórmulas de las estrategias, el tope de `excluded`, los valores de `quality` y el error `501`. **Responsables: Haider y Felipe.** Desde aquí, cualquier cambio lo hace o lo aprueba uno de los dos, se registra en `docs/decisiones.md` y se avisa antes, porque rompe el trabajo en paralelo.

> **Cambios del 11 de octubre de 2026 (decisión 12, MVP):** tablas de los productos NASA (`precip_month`, `soil_moisture_month`, `grid_cells`, `ndvi_municipality`, `ndvi_municipality_normal`, `ndvi_grid`, `climate_change_month`), humedad del suelo en `climate_month`, `/rotations` con estrategias de hasta 3 ciclos y `soil_health`, y `GET /api/v1/changes`. Las decisiones son de Felipe; los nombres de las tablas y de los campos nuevos son una propuesta del especificador y **Aprobados por Felipe el 8 de noviembre de 2026, al congelar el contrato (HU-011 y HU-012).**

> **Cambios del 9 de noviembre de 2026 (decisión 16, HU-062):** columna `crops.secondary_families` y precisiones de «Reglas de rotación como datos». Aprobado por Felipe el 11 de noviembre de 2026 (decisión 16).

## Tablas publicadas (Parquet)

El esquema en código está en `pipeline/schema.py` (HU-011): el pipeline no publica una tabla que no lo cumpla, y una prueba revisa que coincida con esta tabla. Un dataset de ejemplo con todas las tablas está en `data/examples/` (`uv run python -m pipeline.examples`): tres municipios reales con cifras inventadas, rotuladas con la fuente `ejemplo` (R5).

| Tabla | Llave primaria | Columnas principales | Origen |
|---|---|---|---|
| `municipalities` | `municipality_id` (DIVIPOLA, 5 dígitos) | `name`, `department_id`, `department`, `lat`, `lon`, `altitude_m` (de NASADEM, HU-206), `climate_cell_elevation_m` (altura de la celda de NASA POWER que lo cubre), `tmean_annual_c` (temperatura media anual de NASA POWER corregida por altitud, para la aptitud; agregada el 16 de octubre de 2026, decisión 13), `slope_pct` (mediana de la pendiente de sus celdas de `grid_cells`, en %; decisión 14), `source_ids` | DANE, NASADEM y NASA POWER |
| `crops` | `crop_id` | `name_es`, `kind` (`crop`, `cover` para abono verde o cobertura, `fallow` para descanso), `archetype` (cómo se dibuja: `tuber`, `root`, `bulb`, `leafy`, `cereal`, `climbing_legume`, `bush_legume`, `creeping`, `tall_grass`, `shrub_fruit`, `tree_fruit`, y `cover` y `fallow` para el abono verde y el descanso, como en el diseño; agregados el 16 de octubre de 2026, aprobado por Felipe), `article` (el «el»/«la» de cada cultivo, dato de presentación para el texto de aptitud de HU-191, sin fuente agronómica, mismo tipo de campo que `archetype`; agregado el 12 de noviembre de 2026, aprobado por Felipe el 12 de noviembre de 2026), `family`, `cycle_months`, `water_need`, `root_type`, `fixes_nitrogen`, `tmean_min_c`, `tmean_max_c` (temperatura media anual en que se da; fuera de ella no es apto para la zona; reemplazan a `altitude_min_m` y `altitude_max_m` desde el 16 de octubre de 2026, decisión 13, aprobado por Felipe), `secondary_families` (lista de texto: las otras familias de una ficha que mezcla especies, como la vicia de `avena_vicia`, cada valor con su fuente; vacía si la ficha es de una sola especie; aprobado por Felipe el 11 de noviembre de 2026, decisión 16), `base_temp_c`, `heat_max_c` (temperatura máxima que aguanta), los límites de sus curvas de calificación (`temp_min_c`, `temp_opt_min_c`, `temp_opt_max_c`; `tmean_opt_min_c`, `tmean_opt_max_c`, el rango óptimo de temperatura media anual, que da la nota informativa de aptitud; y `rain_min_mm`, `rain_opt_min_mm`, `rain_opt_max_mm`, `rain_max_mm`, la lluvia anual que pide el cultivo, de referencia y contraste: la curva de `water` usa `thresholds.yaml`), `ph_min`, `ph_max` (rango que tolera), `ph_opt_min`, `ph_opt_max` (rango óptimo) — nulos si no hay fuente —, `frost_killing_c` (temperatura que mata la planta en crecimiento, de EcoCrop; agregada el 16 de octubre de 2026, aprobado por Felipe), `source_ids`. `cycle_months` es la suma de los días de sus etapas dividida por 30,44 | Catálogo (`catalog/crops.yaml`) |
| `rotation_rules` | `rule_id` | `kind` (`filter` o `health`), `criterion` (nulo en un `filter`; en un `health`, el criterio de `soil_health` que decide), `condition_type` (de la lista cerrada de «Reglas de rotación como datos»), `params` (JSON con los números de la regla), `levels` (JSON con los cortes de cada nivel; nulo en un `filter`), `reason_template` (la razón en español, con `{marcadores}` que llena el motor), `source_id` | Catálogo (`catalog/rotation_rules.yaml`, HU-062) |
| `climate_risk_week` (P1, HU-193) | `municipality_id`, `week` (1 a 52; los días 365 y 366 van a la semana 52) | Los indicadores de `climate_risk_month` y las normales de `climate_month`, por semana del año y suavizados con las semanas vecinas: `frost_freq_pct`, `tmax_p90_c`, `precip_normal_mm`, `precip_dry_mm`, `et0_normal_mm` y, en P1, `heavy_rain_days_mean`, `dry_window_freq_pct` y `blight_days_mean`; más `years`, `quality`, `source_id` | NASA (para comparar ventanas por semana) |
| `climate_day` | `municipality_id`, `date` | `temp_min_c`, `temp_max_c`, `quality`, `source_id` | NASA POWER (de aquí salen las heladas, el calor y «Qué cambió»; en P1, la etapa del cultivo, HU-150) |
| `climate_normal_doy` (P1, HU-186) | `municipality_id`, `doy` (1 a 366) | `temp_min_c`, `temp_max_c` normales de ese día del año (promedio 1991–2020, suavizado), `source_id` | NASA (para estimar el crecimiento después de hoy, HU-186) |
| `climate_risk_month` | `municipality_id`, `month` (1 a 12) | `frost_freq_pct` (porcentaje de años con al menos un día de mínima menor o igual a 2 °C en ese mes; antes «menor que 2 °C», cambiado el 10 de noviembre de 2026, aprobado por Felipe el 10 de noviembre de 2026), `frost_days_mean`, `tmax_p90_c` (temperatura máxima que se supera uno de cada diez días de ese mes; para la señal de calor), `heavy_rain_days_mean` (P1), `dry_window_freq_pct` (P1, años con 3 días seguidos de menos de 5 mm), `blight_days_mean` (P1, días favorables a la gota), `years`, `quality`, `source_id` | NASA (HU-045) |
| `climate_frost_month` (HU-045, HU-077; agregada el 10 de noviembre de 2026, aprobado por Felipe el 10 de noviembre de 2026) | `municipality_id`, `year`, `month` (1 a 12) | `frost_days` (días con mínima menor o igual a 2 °C en ese mes de ese año), `valid_days` (días con mínima), `quality` (`ok` con todos los días del mes; `partial` si falta alguno), `source_id`. De `climate_day`, corregida por altitud. Con ella el motor cuenta los años con helada de una ventana | NASA POWER |
| `climate_month` | `municipality_id`, `year`, `month` | `precip_mm`, `precip_normal_mm`, `precip_dry_mm` (año seco), `et0_mm`, `et0_normal_mm` (ET0 por Penman-Monteith, FAO-56), `soil_wetness_top`, `soil_wetness_root` (humedad del suelo modelada, superficial y de raíces, fracción de 0 a 1), `quality`, `source_id` | NASA POWER (reanálisis; HU-042, HU-143, HU-205) |
| `precip_month` | `municipality_id`, `year`, `month`, `source_id` | `precip_mm` (promedio de las celdas que tocan el municipio), `precip_normal_mm`, `precip_dry_mm`, `normal_period` (los años de la normal), `quality` | GPM IMERG, lluvia por satélite de unos 10 km (HU-207). La lluvia de NASA POWER sigue en `climate_month` |
| `soil_moisture_month` | `municipality_id`, `year`, `month`, `source_id` | `sm_surface_m3_m3`, `sm_rootzone_m3_m3` (humedad superficial y de raíces, en m³/m³), `quality` | SMAP nivel 4, 9 km, desde 2015 (HU-210). Solo para contrastar; unidad distinta de la de POWER |
| `ndvi_municipality` | `municipality_id`, `year`, `period` (1 a 23: el compuesto de 16 días del año) | `ndvi_median`, `valid_pixels_pct` (píxeles sin nubes), `quality`, `source_id` | MODIS MOD13Q1, 250 m (HU-208) |
| `ndvi_municipality_normal` | `municipality_id`, `period` (1 a 23) | `ndvi_normal`, `years`, `quality`, `source_id` | MODIS MOD13Q1 (HU-208) |
| `ndvi_grid` (P1, HU-209) | `cell_id` (el de `grid_cells`), `period` (1 a 23) | `ndvi_normal`, `years`, `valid_pct`, `quality`, `source_id`. Solo las celdas de los municipios con lotes, para que no pase de unos cientos de miles de filas | MODIS MOD13Q1; para el verdor de un lote. En el P0 el verdor es el del municipio |
| `climate_change_month` | `municipality_id`, `period_id`, `month` (1 a 12), `source_id` | `frost_freq_pct`, `tmax_p90_c` (nulos en las filas de una fuente de lluvia), `precip_normal_mm`, `years`, `quality` | NASA POWER y GPM IMERG (HU-216); para «Qué cambió» |
| `crop_stages` | `crop_id`, `stage` (`initial`, `development`, `mid`, `late`, las de FAO-56) | `days`, `kc` (nulo en `development`: en FAO-56 sube en línea recta de la inicial a la media), `gdd` (grados-día que cierran la etapa; nulo si no hay fuente), `frost_sensitive` (la helada daña en esta etapa), `heat_sensitive` (el calor por encima de `heat_max_c` daña en esta etapa), `source_id` | Catálogo (FAO-56 o fuente local) |
| `supply_semester` | `municipality_id`, `crop_id`, `year`, `semester`, `source_id` | `planted_ha`, `harvested_ha`, `production_t`, `yield_t_ha`, `planted_change_pct`, `dept_share_pct`, `preliminary`, `quality` | EVA |
| `market_month` (P1, HU-051; columnas detalladas el 7 de noviembre de 2026, aprobado por Felipe el 10 de noviembre de 2026) | `crop_id`, `market_id`, `month` (1 a 12) | `product_id` (el producto de SIPSA que da el precio del cultivo, según `pipeline/sipsa_crops.yaml`), `price_cop_kg` (precio medio de ese mes en `price_year`, en pesos enteros por kilo), `price_year` (el último año completo del producto en esa central), `volume_t` (nulo: `promediosSipsaParcial` no trae volumen), `seasonal_index` y `years` (los de `market_price_season`), `quality` (`partial` si el último año completo es anterior al año pasado), `source_id`. Un cultivo sin producto en SIPSA, o sin 3 años completos en una central, no tiene filas allí (R1) | SIPSA |
| `market_price_day` (P1, HU-221; agregada el 20 de octubre de 2026, aprobado por Felipe el 10 de noviembre de 2026) | `product_id`, `market_id`, `date` | `product` (nombre del DANE sin asterisco), `group`, `several_varieties` (el asterisco de SIPSA: junta variedades), `market`, `min_cop_kg` y `max_cop_kg` (nulos si el DANE no los da), `avg_cop_kg`, `source_id`. Solo las centrales de `region.yaml` | SIPSA (servicio web del DANE) |
| `market_price_latest` (HU-221, HU-222; agregada el 9 de noviembre de 2026 por la revisión de Felipe del PR #12, aprobado por Felipe el 10 de noviembre de 2026) | `market_id`, `product_id` | `position` (orden en que se muestran los productos de la central: por grupo, primero tubérculos, raíces y plátanos, y por nombre), `product`, `group`, `several_varieties`, `market`, `date` (el último día con precio del producto), `min_cop_kg`, `avg_cop_kg`, `max_cop_kg` (los de ese día), `week_ago_date`, `week_ago_min_cop_kg`, `week_ago_avg_cop_kg`, `week_ago_max_cop_kg` (el último día con precio hasta 7 días antes; nulos si no hay), `change_pct` (cambio del precio medio, en %, con un decimal; nulo sin precio de hace una semana), `market_date` (el último día con precios en la central), `market_source_id` (la fuente de ese día), `source_id` (la del último precio del producto). La escriben el pipeline y cada actualización de precios a partir de `market_price_day`, para que `/market/prices` solo filtre y devuelva | SIPSA |
| `market_price_season` (P1, HU-221; aprobado por Felipe el 10 de noviembre de 2026) | `product_id`, `market_id`, `month` | `seasonal_index` (precio del mes sobre el promedio de su mismo año, promediado entre años; 1 = un mes como cualquiera), `years`, `first_year`, `last_year`, `source_id`. Solo productos con 3 o más años completos | SIPSA |
| `municipality_boundaries` | `municipality_id` | `geometry` (polígono WGS84 simplificado a unos 10 m, en WKB; aprobado por Felipe el 16 de octubre de 2026), `source_id` | DANE (Marco Geoestadístico Nacional 2025, servicio del geoportal) |
| `grid_cells` | `cell_id` (ver «La rejilla de 250 m») | `lat`, `lon` (centro de la celda), `municipality_id` (el municipio que contiene el centro), `altitude_m` (promedio de los píxeles de NASADEM de 30 m dentro de la celda), `slope_pct` (mediana de la pendiente de esos píxeles, en %), `ph`, `ph_p05`, `ph_p95`, `soc_g_kg` (carbono orgánico), `soc_p05`, `soc_p95`, `nitrogen_g_kg`, `clay_pct`, `sand_pct`, `silt_pct`, `texture_class` (clase USDA); el suelo es el promedio ponderado de 0 a 30 cm; `quality`, `source_ids`. Unas 600.000 celdas en la región | NASADEM (HU-206) y SoilGrids de ISRIC (HU-181); para la altitud, la pendiente y el suelo de un lote |
| `soil_municipality` | `municipality_id` | Las propiedades de suelo de `grid_cells` (`ph`, `ph_p05`, `ph_p95`, `soc_g_kg`, `soc_p05`, `soc_p95`, `nitrogen_g_kg`, `clay_pct`, `sand_pct`, `silt_pct`, `texture_class`), como mediana de las celdas del municipio (los percentiles 5 y 95 también, como mediana de los de cada celda; la textura, la clase más frecuente), más `cells`, `quality` y `source_id` | SoilGrids (HU-181) |
| `sources` | `source_id` | `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `coverage` (país o región que cubre), `license`, `citation` (la cita textual que pide la fuente a quien use sus datos, como la del DANE; nula si no pide una. La API y la web la muestran tal cual y sirve para las citas de la entrega, R8. Agregada el 9 de noviembre de 2026 por la revisión de Felipe del PR #12, aprobado por Felipe el 10 de noviembre de 2026), `notes` | Todas. Un indicador puede tener varias fuentes; `sources.yaml` dice cuál usa cada señal en cada región y las demás se muestran para contrastar |
| `manifest.json` | — | `dataset_version`, `rules_version`, `created_at`, `region` (con `id`, `name`, `country`, `departments`, `markets` y `temperature_lapse_rate`: las tasas `temp_max_c_per_m` y `temp_min_c_per_m` del gradiente térmico con que se calculó `tmean_annual_c` y su `source_id`; agregado el 13 de noviembre de 2026 en HU-191, aprobado por Felipe el 13 de noviembre de 2026: la API corrige la temperatura a la altitud de un lote con estas tasas y nunca con otras, R4), `periods` (los periodos de «Qué cambió»: `period_id`, `start_year`, `end_year`, `source_id`), filas y cobertura por tabla | Pipeline |

### La rejilla de 250 m (`grid_cells`)

Decisión 15. Los datos que vienen como cuadrícula se publican en **una sola rejilla común**, para que un lote se resuelva con una sola tabla:

- Rejilla regular en grados WGS84 de **0,0025°** (unos 277 m de lado en el altiplano). `cell_id` es `"{fila}_{columna}"`, con `fila = floor((90 − lat) / 0,0025)` y `columna = floor((lon + 180) / 0,0025)`: cualquier punto se ubica en su celda sin consultar la tabla.
- Cada fuente se lleva a esa rejilla en el pipeline. NASADEM (30 m): la altitud es el promedio de sus píxeles dentro de la celda, y la pendiente se calcula a 30 m y se guarda la mediana, para no perder el relieve. SoilGrids (250 m, en otra proyección): el valor del píxel que contiene el centro de la celda. MODIS (250 m, en otra proyección): igual, en `ndvi_grid` (P1).
- Una celda sin dato de una fuente queda con esas columnas nulas y `quality = partial` (R1).
- El suelo, la altitud y la pendiente de un **lote** son la mediana de las celdas cuyo centro cae dentro de su polígono. Un lote más chico que una celda usa la celda que contiene su centro y lo dice (`cells = 1`). La API los calcula al vuelo y no los guarda (R9). Un lote sin polígono usa los de su municipio.

### Valores de `quality`

En todas las tablas: `ok` (el dato está completo para lo que se calcula) o `partial` (faltan días, años, píxeles o una fuente; la tabla dice cuántos en `years`, `cells` o `valid_pct`). Una fila sin ningún dato no se publica: no se rellena (R1).

### Decisiones sobre el clima publicado

- Todas las temperaturas publicadas (`climate_day`, `climate_month`, `climate_risk_month` y `climate_risk_week`) se corrigen por altitud: la celda de NASA POWER tiene unos 50 km y su altura puede diferir cientos de metros de la del municipio. La corrección usa la diferencia entre `altitude_m` y `climate_cell_elevation_m` con un gradiente térmico con fuente (HU-044). Así la etapa del cultivo, la ET0 y las heladas usan la misma temperatura.
- El umbral de helada es una mínima menor o igual a 2 °C a 2 m (el criterio del ZARC de Brasil, `mapa_zarc_2025`; antes «menor que 2 °C», de la UPRA con datos del IDEAM, cuyo boletín ya no está en su enlace; decidido por Felipe el 10 de noviembre de 2026).
- NASA POWER es un **reanálisis** (un modelo con observaciones asimiladas), no una observación directa; su entrada en `sources` lo dice. Es la serie larga (desde 1981).
- La lluvia tiene dos fuentes: NASA POWER (`climate_month`) y GPM IMERG (`precip_month`). `sources.yaml` dice cuál calcula la señal `water` en cada región; la otra se muestra para contrastar. Nunca se promedian ni una rellena a la otra.
- La humedad del suelo tiene dos fuentes con unidades distintas: la de POWER (`soil_wetness_*`, fracción de 0 a 1) y la de SMAP (`sm_*_m3_m3`). No se convierten una en otra.
- La pendiente (`slope_pct`, decisión 14) sale de NASADEM en el pipeline: la de cada celda en `grid_cells` y la del municipio en `municipalities.slope_pct`. La de un lote se calcula como en «La rejilla de 250 m».
- En el MVP la señal de calor lee `climate_risk_month`, y la de heladas, `climate_frost_month`; `climate_risk_week` llega en P1.
- **Heladas de una ventana** (HU-077, aprobado por Felipe el 10 de noviembre de 2026): `frost_freq_pct` de la señal es el porcentaje de años con al menos una helada en **cualquiera** de los meses sensibles de la ventana, no el promedio de los meses, porque así lo cuentan los cortes de `thresholds.yaml` (ZARC). Se cuenta con `climate_frost_month`: un año tiene helada si algún mes sensible tiene `frost_days` ≥ 1; no tiene helada si todos sus meses sensibles son `ok` con `frost_days` = 0; en otro caso (falta dato y no heló) **ese año no cuenta** (R1). Si la ventana pasa de diciembre a enero, enero es del año siguiente. Se cuentan los años del periodo normal de `pipeline/region.yaml`; con menos años de los que pide ese periodo, la señal es `insufficient_data`. La frecuencia por mes de `climate_risk_month` se sigue publicando para mostrar y para «Qué cambió».

### Ingestión, almacenamiento y actualización diaria de precios de SIPSA (HU-221, HU-222)

- **Origen y protocolo (servicio web SOAP 1.2 del DANE):** los precios mayoristas se descargan del servicio público `https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService` enviando un `POST` con cabecera `Content-Type: application/soap+xml; charset=utf-8` y cuerpo `<ser:promediosSipsaParcial/>` (sin cuenta ni clave). El servicio devuelve un XML de unos 300 MB con la serie diaria desde el 1 de febrero de 2020 hasta el día hábil anterior.
- **Filtrado, limpieza y validación (`pipeline/sources/sipsa.py` y `pipeline/build.py`):**
  - El XML se lee en *streaming* (`ET.iterparse`) vaciando cada nodo `<return>` para no saturar la memoria, y se conservan únicamente las centrales declaradas en `pipeline/region.yaml` (`"1"`: `Corabastos (Bogotá)`, `"9"`: `Tunja (Complejo de Servicios del Sur)`).
  - Los precios (`minimoKg`, `promedioKg`, `maximoKg`) se convierten de texto decimal a **pesos enteros por kilo (`COP/kg`)** con redondeo mitad arriba. Un `0` o un campo vacío del DANE se convierte en `null`, nunca en cero (R1), y cualquier fila sin `avg_cop_kg` válido se descarta.
  - Si el nombre del producto (`artiNombre`) termina en `*`, se quita el asterisco en `product` y se marca `several_varieties = true` (indica que SIPSA agrupa varias variedades bajo ese nombre).
  - Antes de publicar se valida que no existan llaves repetidas `(product_id, market_id, date)`, que todas las filas pertenezcan a centrales de la región, que `avg_cop_kg > 0`, que `min_cop_kg <= avg_cop_kg + 1` y `max_cop_kg >= avg_cop_kg - 1` (1 peso de tolerancia por el redondeo del DANE) y que `source_id = "dane_sipsa"` exista en la tabla `sources` (R8).
- **Índice estacional (`market_price_season`):** para cada `(product_id, market_id)` se filtran los años calendario con los 12 meses completos. En cada año completo se divide el promedio de cada mes entre el promedio de su propio año (así la inflación entre años no distorsiona la curva) y luego se promedian esos cocientes por mes (`1` a `12`) para obtener `seasonal_index` (donde `1.0` representa un mes igual al promedio del año). Solo se publica la temporada de los productos con **3 o más años completos** (`MIN_YEARS = 3`); con menos años no se publica temporada (R1).
- **Precio y temporada por cultivo (`market_month`, HU-051):** `pipeline/sipsa_crops.yaml` dice qué producto de SIPSA da el precio de cada cultivo (HU-003), y `pipeline.build` lo valida contra los precios antes de publicar. Para cada cultivo con producto y cada central, los 12 meses llevan el `seasonal_index` de `market_price_season` y el precio que se pagó ese mes en el último año completo (`price_year`). No es un promedio entre años, que mezclaría la inflación, ni un precio estimado. La señal `market` del motor usará `seasonal_index` del mes de cosecha (HU-073). `market_month` sale del dataset publicado: la actualización diaria (HU-222) no la recalcula.
- **Almacenamiento local en dos capas (nunca se consulta al DANE por petición del usuario):**
  1. **Base publicada (`data/published/`):** generada por `python -m pipeline.build` y versionada en el repositorio (`market_price_day`, `market_price_latest`, `market_price_season` y `market_month`). Garantiza que el sistema funcione sin conexión ni esperas apenas se despliega (decisión 3). Sin la caché de SIPSA, el pipeline publica lo demás sin estas tablas y lo dice en el log (`source_missing`).
  2. **Versiones de los crons (`data/market/`, volumen Docker `market_data`, HU-222):** excepción acotada a la decisión 3 para que los precios reflejen el último día publicado por el DANE sin reconstruir el dataset. Las escribe el servicio `market` de Docker Compose (perfil `market`: no arranca con `docker compose up`), con supercronic, en la hora de Bogotá y con los horarios del `.env`:
     - **Diario** (`AGROSENSE_MARKET_DAILY_SCHEDULE`, por defecto de lunes a viernes a las 3:00 p. m.; el DANE publica hacia las 2:00): `python -m backend.market.updates diario` baja el **anexo del boletín diario** del DANE (`pipeline/sources/sipsa_boletin.py`, `https://www.dane.gov.co/files/operaciones/SIPSA/anex-SIPSADiario-DDmmmAAAA.xlsx`, unos 340 KB) de cada día hábil que falte, hasta 10 días atrás, y lo suma a la última versión. Trae solo el precio medio: `min_cop_kg` y `max_cop_kg` van nulos (R1) y `source_id = dane_sipsa_boletin` (R8). Es la misma serie del servicio web (el 6 de noviembre de 2026 los 63 precios de Corabastos y Tunja eran iguales). Un día sin boletín (festivo) responde 404 y no es un error; sin días nuevos no se escribe nada. Si el DANE cambia el formato del anexo, falla en vez de leer mal.
     - **Semanal** (`AGROSENSE_MARKET_WEEKLY_SCHEDULE`, por defecto los domingos a las 3:00 p. m.): `python -m backend.market.updates semanal` baja la serie completa del servicio web (unos 300 MB), con hasta 3 intentos. Reemplaza los días del boletín: solo se conservan los del boletín posteriores al último día del servicio en cada central.
     - Las dos descargas cortan por tiempo total y por tamaño (`AGROSENSE_MARKET_TIMEOUT_S`, por defecto 900 s; `AGROSENSE_MARKET_MAX_MB`, por defecto 600). Cada actualización buena se valida con las mismas reglas del pipeline (`sipsa.validate`), se escribe en una carpeta aparte `sipsa-AAAAMMDDTHHMMSS-boletin` o `-servicio` con `market_price_day.parquet`, `market_price_latest.parquet` (calculada con la misma función que usa el pipeline, `sipsa.latest`) y `sources.json` (las filas de `sources` de la versión, con su `citation`), y se publica al final cambiando `current.json` (`version`, `updated_at`). Se guardan las 2 últimas. Si algo falla, **no se toca la versión vigente** (R1), el log dice `market_refresh_failed` y el comando termina con error. Un candado (`data/market/.lock`) evita dos actualizaciones a la vez; no se borra al arrancar el servicio: si un proceso murió con él puesto, se da por muerto a las 6 horas (`LOCK_STALE_S`).
     - El servicio `market` **no usa la base de datos**: lee su configuración de `pipeline/settings.py` (`AGROSENSE_DATA_DIR`, `AGROSENSE_MARKET_DIR`, los límites de descarga y los logs) y no recibe las variables `POSTGRES_*`. No importa la configuración de la API.
     - La temporada (`market_price_season`) y el precio por cultivo (`market_month`) **no** se recalculan en los crons: solo cambian cuando cierra un año completo y salen del dataset publicado.
- **Lectura en la API (`backend/api/market.py`, `backend/market/store.py`):** la API nunca baja nada ni calcula precios: **las rutas `GET /market/*` solo filtran por central o por producto y devuelven**. El último precio, el de hace una semana, el cambio y el orden ya vienen en `market_price_latest`. Qué versión se sirve lo decide el acceso a los datos, la dependencia `market_tables` (`store.current_tables`): mira `current.json` como mucho cada minuto y, si cambió, lee la versión nueva en memoria, sin reiniciarse; usa la versión de `data/market/` solo si su último día es mayor o igual que el de `data/published/`; si no, sirve `data/published/` con `version = dataset_version` y `updated_at = null`. La temporada es siempre la de `data/published/`. La cita sale de la columna `citation` de la fila de su fuente en `sources` (del dataset o del `sources.json` de la versión): la API no importa el pipeline. No usa PostgreSQL ni registra quién consultó (R9).

### Lo que depende de verificar una fuente

Ninguno cambia la forma de las tablas:

- Si EVA trae el código DIVIPOLA y cómo son sus semestres (HU-001). Se toma A = enero a junio y B = julio a diciembre. El semestre solo existe en `supply_semester`: la decisión se toma sobre ventanas de siembra (ver `specs/01-reglas.md`) y la oferta se lee del semestre en que cae la fecha de siembra. **Si EVA no sirve, la señal `supply` queda en `insufficient_data` (R1) y el diagnóstico sigue: no se calcula sin ella** (regla 1 de la agregación).
- `planted_change_pct` compara contra el promedio de los tres mismos semestres anteriores; con menos de tres, `quality = partial` y, sin ninguno, la fila no trae el cambio (nulo).

## Configuración versionada

Decisión 15. El motor la recibe ya leída (R6). Cada archivo tiene `version`, que va en `versions.rules` de cada respuesta (R4), y la API no arranca si un archivo no cumple su forma.

### `backend/config/weights.yaml` (hecho, HU-075 y HU-198)

`version` y, por señal del P0, `weight` (0 a 5) y `reason`.

### `backend/config/thresholds.yaml` (HU-075)

```yaml
version: "1.0.0"
levels: { favorable: 70, moderate: 40 }   # calificación desde la que una señal es favorable o moderada
signals:
  water:  { variable: coverage_pct,    unit: "%",  curve: [[0, 0], [50, 40], [100, 100]], critical_below: 20, source_id: "…" }
  frost:  { variable: frost_freq_pct,  unit: "%",  curve: [[0, 100], [10, 70], [40, 0]],  critical_below: 25, source_id: "…" }
  heat:   { variable: tmax_p90_c,      unit: "°C", curve: crop,                          critical_below: 25, source_id: "…" }
  soil:   { variable: ph,              unit: "pH", curve: crop,                          critical_below: null }
  supply: { variable: planted_change_pct, unit: "%", curve: [[-20, 100], [10, 100], [40, 0]], critical_below: 10, source_id: "…" }
  market: { variable: seasonal_index,  unit: "",   curve: [[0.8, 0], [1.0, 70], [1.2, 100]], critical_below: 10, source_id: "…" }
```

- `water` califica `coverage_pct` con la lluvia del **año seco** de la fuente de `sources.yaml` (`precip_dry_mm`, el percentil 20), no con la normal (decidido por Felipe el 11 de noviembre de 2026): es la lluvia confiable de la FAO y deja la señal del lado prudente, porque las dos fuentes de la NASA dan casi el doble de lluvia en los valles del altiplano, donde están los cultivos (259 estaciones del IDEAM; IMERG 1,85 veces, POWER 1,80; PR #44), y con la normal el agua saldría verde donde falta. La lluvia normal se muestra en `signals.water.sources` para contrastar.
- `curve`: puntos `[valor, calificación]` en orden de valor; entre dos puntos la calificación va en línea recta, y fuera de ellos vale la del punto más cercano. `crop` quiere decir que la curva sale de la ficha del cultivo: `heat` va de 100 en `temp_opt_max_c` a 0 en `heat_max_c`, y `soil` de 0 en `ph_min` a 100 entre `ph_opt_min` y `ph_opt_max` y a 0 en `ph_max`.
- `critical_below`: una señal es crítica si su calificación baja de ese número (R2). `soil` nunca es crítica (R10).
- **Los números de este ejemplo son ilustrativos.** Los de verdad los fija HU-075, cada curva con su `source_id` (R8). Sin fuente para una curva, la señal es `insufficient_data` (R1).
- **Versión 1.0.0 (decidido por Felipe el 10 de noviembre de 2026, HU-075):** una señal sin fuente para sus cortes lleva `curve: null`, `critical_below: null` y `source_id: null`, y es `insufficient_data` (hoy, `supply` y `market`). `levels` lleva también su `source_id`, y cada señal puede llevar una `note` que dice de dónde y cómo se derivó. La API no arranca si el archivo no cumple esta forma (`backend/config/thresholds.py`).

### `catalog/sources.yaml` (HU-122)

```yaml
version: "1.3.0"
regions:
  co-boyaca-cundinamarca:
    water:  { rain: imerg, rain_contrast: [nasa_power], rain_caveat: "La lluvia sale de GPM IMERG (satélite)…", et0: nasa_power,
              soil_moisture_contrast: [nasa_power, smap] }
    frost:  { used: nasa_power, frost_caveat: "Las heladas salen de NASA POWER (reanálisis)…" }
    heat:   { used: nasa_power }
    soil:   { used: soilgrids }
    supply: { used: eva, contrast: [] }
    market: { used: dane_sipsa }
planned: { soilgrids: HU-181, eva: HU-031, smap: HU-210 }
```

Por región y por señal: qué fuente la calcula (`used`) y cuáles se muestran para contrastar. Un `source_id` que no está en `sources`, ni tiene adaptador en el pipeline, ni está en `planned` hace fallar el pipeline (R8). `planned` lista las fuentes que todavía no tienen adaptador, con la HU que las trae: mientras estén ahí, lo que las usa es `insufficient_data` (R1) y el contraste no se muestra; una fuente de `planned` que ya se publica también hace fallar el pipeline, para que no se quede en la lista. `rain_caveat` es el aviso que lleva siempre la señal de agua mientras la lluvia salga de una fuente con un sesgo conocido. **Versión 1.0.0 (decidido por Felipe el 11 de noviembre de 2026):** la lluvia de `water` sale de NASA POWER de forma **temporal**, con el aviso de que en el altiplano la sobrestima (de 1,7 a 2,7 veces la del IDEAM, PR #24); cuando exista GPM IMERG (HU-207), `rain` pasa a `imerg` y POWER pasa al contraste. **Versión 1.2.0 (aprobado por Felipe el 11 de noviembre de 2026, PR #44, HU-207):** la lluvia de `water` sale de GPM IMERG (`precip_month`), que sigue mejor los meses del año que POWER, y NASA POWER (`climate_month`) pasa al contraste. El aviso no se quita: IMERG también sobrestima la lluvia en los valles del altiplano (cerca de 1,85 veces la del IDEAM en 169 estaciones), así que ahora lo dice de IMERG. `imerg` sale de `planned` porque ya se publica. **Versión 1.3.0 (aprobado por Felipe el 13 de noviembre de 2026, PR #61, HU-045):** `frost` lleva `frost_caveat`, el aviso fijo de la señal de heladas, igual que `rain_caveat` en `water`: con NASA POWER la mínima de los valles del altiplano sale más caliente que la de las estaciones del IDEAM y se cuentan menos heladas de las que hay (solo 24 de los 239 municipios tienen alguna en 1991–2020; en Tibaitatá el IDEAM midió 26 días de helada de 2024 a 2026 y POWER 0). Si existe, debe ser un texto (`common/signal_sources.py`). Lo leen el pipeline, antes de publicar, y la API al arrancar (`common/signal_sources.py`). Si la fuente usada no tiene dato para un municipio, la señal es `insufficient_data`: nunca se cambia a la de contraste (R1).

### Reglas de rotación como datos (`rotation_rules`, HU-062)

Cada regla es una fila con un `condition_type` de esta lista cerrada. El motor solo sabe evaluar estos tipos; una regla con otro tipo hace fallar el pipeline. Una estrategia se evalúa sobre su secuencia de ciclos con los cultivos anteriores delante (`previous_crop_ids`).

| `condition_type` | `kind` | Qué mira | `params` | `levels` |
|---|---|---|---|---|
| `same_family_consecutive` | `filter` | Dos ciclos seguidos (o el último anterior y el primero) de la misma familia. Compara **solo `family`**: `secondary_families` no cuenta (decisión 16) | `{"families": null}` (nulo: todas) | — |
| `family_return_min_cycles` | `filter` o `health` (`pest_break`) | Una familia vuelve antes de `min_cycles` ciclos de otras familias. Cuenta **`family` y `secondary_families`** de cada ciclo (decisión 16). **En `pest_break` cuenta también los cultivos anteriores del terreno** (`current_crop_ids`, y con cuenta el historial de HU-165, `previous_crop_ids`), además de los ciclos de la estrategia, para que una estrategia de 3 ciclos pueda llegar a `favorable` (11 de noviembre de 2026) | `{"family": "Solanaceae", "min_cycles": 3}` | Cortes por ciclos de espera, por ejemplo `{"favorable": 3, "moderate": 2}` (`papa_espera`; con franja intermedia). En `kind = health`, `params.min_cycles` es igual a `levels.favorable` (si no, el pipeline falla) |
| `legume_cycles` | `health` (`nitrogen`) | Cuántos ciclos tienen un cultivo con `fixes_nitrogen` (o un abono verde con leguminosa) | `{}` | Por número de ciclos, `{"favorable": 2, "moderate": 1}` |
| `organic_matter_cycles` | `health` (`organic_carbon`) | Cuántos ciclos devuelven materia orgánica (abono verde o descanso), según el carbono del suelo | `{"soc_low_g_kg": 20}` | Por número de ciclos, con el suelo bajo y con el suelo normal: `{"low": {"favorable": 2, "moderate": 1}, "normal": {"favorable": 1, "moderate": 0}}` (ver abajo) |
| `covered_months_pct` | `health` (`soil_cover`) | Porcentaje de los meses de la estrategia con el suelo cubierto por un ciclo. Un descanso cuenta como suelo descubierto | `{}` | `{"favorable": 80, "moderate": 60}` |
| `bare_months_on_slope` | `health` (`erosion`) | Meses descubiertos cuando la pendiente es de `slope_pct_from` o más (`slope_pct >= slope_pct_from`: el IGAC dice «a partir de»). Un descanso cuenta como suelo descubierto | `{"slope_pct_from": 8}` | Menos es mejor: `{"favorable": 1, "moderate": 3}` |

- `levels` dice desde qué valor un criterio es `favorable` o `moderate` (menos que eso, `unfavorable`). En `bare_months_on_slope` los cortes son máximos. En un terreno con menos pendiente que `slope_pct_from`, `erosion` es `favorable` (aprobado por Felipe el 11 de noviembre de 2026).
  - **Sin franja intermedia** (propuesto por Juan Cárdenas el 9 de noviembre de 2026, aprobado por Felipe el 11 de noviembre de 2026): los cortes admiten `moderate == favorable`, que quiere decir que el criterio no tiene franja intermedia: es `favorable` desde ese valor y `unfavorable` por debajo, nunca `moderate`. En los demás tipos, `moderate <= favorable`; en `bare_months_on_slope` (cortes máximos), `favorable <= moderate`. Cualquier otro orden hace fallar el pipeline.
- `params.family` y `params.families` usan el valor exacto de `family` de `crops` (con la misma mayúscula); una familia que no está en ninguna ficha hace fallar el pipeline (decisión 16).
- **`levels` de `organic_matter_cycles`** (decisión 16): un objeto con las dos llaves obligatorias `low` y `normal`, y cada una con `favorable` y `moderate` (desde cuántos ciclos de abono verde o descanso el criterio es `favorable` o `moderate`; menos que eso, `unfavorable`). `low` aplica cuando `soc_g_kg` del lote o del municipio es menor que `params.soc_low_g_kg`; si no, `normal`. `low.favorable` es al menos 1 (con carbono bajo, una estrategia sin abono verde ni descanso no es `favorable`); si no, el pipeline falla. Sin `soc_g_kg`, el criterio es `insufficient_data` (R1).
- **El descanso en la cobertura** (decisión 16): en `covered_months_pct` y `bare_months_on_slope`, un ciclo de descanso (`kind = fallow`) cuenta como suelo descubierto hasta que una fuente diga otra cosa.
- **Versión de los catálogos** (decisión 16): `catalog/crops.yaml` y `catalog/rotation_rules.yaml` comparten la misma `version`, y esa es `rules_version` de `manifest.json`. El pipeline falla si difieren. La forma del manifiesto no cambia.
- **Marcadores de `reason_template`** (aprobados por Felipe el 11 de noviembre de 2026). El motor llena solo estos; otro marcador hace fallar el pipeline (R5):

  | `condition_type` | Marcadores |
  |---|---|
  | `same_family_consecutive` | `{family}` |
  | `family_return_min_cycles` | `{family}`, `{cycles}` |
  | `legume_cycles` | `{count}` |
  | `organic_matter_cycles` | `{count}`, `{soc_level}` (`bajo` o `normal`), `{soc_range}` (el rango p05–p95 del carbono estimado, en g/kg: el suelo es una estimación de 250 m, R10) |
  | `covered_months_pct` | `{pct}` |
  | `bare_months_on_slope` | `{slope}`, `{months}` |

- Un criterio de `soil_health` sin una regla `health` con fuente es `insufficient_data` (R1, R8).
- Una regla que cite `criterio_equipo_2026` solo es válida si es central para el producto y cada número se apoya en un dato externo citado (R8, decisión 16). La `reason` de cada criterio de `soil_health` que la cite dice «criterio del equipo», y la web lo muestra (aprobado por Felipe el 11 de noviembre de 2026).
- Los números de los ejemplos son ilustrativos: los fija HU-062, cada regla con su `source_id`.

> **Cambios del 9 de noviembre de 2026 (decisión 16, HU-062):** `crops.secondary_families`; qué familias cuenta cada condición; la forma de `levels` de `organic_matter_cycles`; el valor exacto de la familia en `params` (el ejemplo pasa de `"solanaceae"` a `"Solanaceae"`); `min_cycles == levels.favorable`; el descanso como suelo descubierto, y la versión compartida de los dos catálogos. Aprobados por Felipe el 11 de noviembre de 2026. **10 de noviembre de 2026**, propuestos y aprobados por Felipe el 11 de noviembre de 2026: «sin franja intermedia» (`moderate == favorable`), la lista de marcadores de `reason_template` y la erosión «a partir de» `slope_pct_from` (antes decía «pasa de»). **11 de noviembre de 2026**, aprobado por Felipe en la revisión del PR #46: el corte de plagas cuenta también los cultivos anteriores del terreno, y el ejemplo de `family_return_min_cycles` pasa a la forma de `papa_espera` (3 y 2, con franja intermedia).

## Base de datos de cuentas (PostgreSQL)

Decisión 6 de `docs/decisiones.md` y regla R9. PostgreSQL (en la nube para el equipo y la demo; en Docker Compose para las pruebas), aparte del dataset publicado. El motor no la lee: la API consulta los lotes y le pasa al motor solo lo que necesita.

| Tabla | Llave primaria | Columnas principales | Notas |
|---|---|---|---|
| `users` | `user_id` (UUID) | `username` (único), `password_hash`, `display_name`, `role` (`farmer` por defecto; ver «Roles»), `blocked_at` (nulo si no está bloqueado), `consent_version`, `consent_at`, `priorities` (los pesos de 0 a 5 por señal que el agricultor eligió; nulo = los de AgroSense), `created_at`, `updated_at` | Sin correo, celular, documento de identidad ni dirección. La contraseña se guarda solo como hash Argon2 |
| `sessions` | `session_id` (UUID) | `user_id`, `token_hash`, `created_at`, `expires_at` | Una fila por sesión abierta. Se guarda el hash del token, nunca el token. Vence a los 30 días |
| `lots` | `lot_id` (UUID) | `user_id`, `municipality_id`, `name`, `geometry` (polígono GeoJSON en WGS84, dibujado en el mapa; nulo si el usuario aún no lo dibuja), `area_ha`, `irrigated` (si el lote tiene riego; nulo si no lo ha dicho), `deleted_at`, `created_at`, `updated_at` | Un usuario tiene uno o varios lotes; la «zona» es el municipio (R7). Con polígono, `area_ha` se calcula de él y el polígono debe caer dentro de su municipio |
| `seasons` | `season_id` (UUID) | `lot_id`, `crop_id`, `area_ha` (la parte del lote que ocupa), `follows_season_ids` (lista de las temporadas que había antes en ese terreno; vacía si es la primera), `diagnosis_irrigated` (el `irrigated` con que se vio el diagnóstico), `diagnosis_light_default` (la luz con los pesos de AgroSense), `diagnosis_weights` (los pesos con que se vio; `diagnosis_light` es la luz con esos pesos), `sowing_date`, `harvest_date` (nula si sigue en curso), `diagnosis_light`, `diagnosis_action`, `dataset_version`, `rules_version`, `deleted_at`, `created_at` | Una temporada por cultivo y ciclo en una parte del lote. Un lote grande puede tener varios cultivos a la vez, cada uno en su parte. Guarda el diagnóstico que se vio al sembrar, con sus versiones (R4) |

- Borrar un usuario borra en cascada, y para siempre, sus sesiones, lotes, temporadas, tickets y sus eventos de `activity_log` (R9).
- Borrar un lote o una temporada es reversible: se marca `deleted_at` y se puede restaurar durante 30 días; después se borra para siempre. Borrar un lote borra con él sus temporadas, y restaurarlo las restaura. El agricultor y el administrador pueden restaurar.
- Un polígono de lote debe ser válido (sin cruces), tener área mayor que cero y caer dentro de `municipality_boundaries` de su municipio; si no, 422.
- `activity_log`: trazabilidad de lo que hacen agricultores y administradores. Ver «Trazabilidad» más abajo.
- `login_attempts` (agregada el 12 de octubre de 2026; aprobada por Felipe): `attempt_id`, `username_hash` y `attempted_at`. Una fila por intento fallido de entrar, de cambiar la contraseña o de borrar la cuenta, solo para el **tope general** de 20 intentos en 15 minutos por usuario desde cualquier conexión (cambiado el 15 de octubre de 2026; aprobado por Felipe: antes era el único tope, de 5). El tope de 5 por conexión vive en memoria (ver «Cómo viaja la credencial»). Guarda el hash del usuario que se intentó, nunca el texto (podría ser una contraseña escrita en el campo equivocado), ni la IP. Las filas de más de 15 minutos se borran solas. La fila se anota **antes** de verificar la contraseña y se quita si era la buena, para que varias peticiones a la vez no se salten el tope; un intento rechazado con 429 no se anota, así que no alarga el bloqueo. Está en la base de datos para que el tope sobreviva a un reinicio.
- `usage_daily` (P1, HU-170): contador anónimo de uso para las métricas. En el P0 la tabla no existe y los endpoints de cálculo no escriben nada en la base de datos. Columnas: `day` (fecha), `endpoint` (`diagnostics`, `rotations`, `changes`, `calendar`, `water_plans`, `scenarios`), `municipality_id`, `crop_id` y `count`; llave (`day`, `endpoint`, `municipality_id`, `crop_id`). Cada consulta de cálculo suma 1 a su fila. El `crop_id` que se cuenta: en `/diagnostics`, `/changes`, `/calendar` y `/scenarios`, el cultivo consultado; en `/water-plans`, una fila por cultivo; en `/rotations`, el primer cultivo de `previous_crop_ids` (el más reciente). No tiene usuario, sesión, IP, hora, fecha de siembra, prioridades, área ni riego, ni se puede unir con `activity_log`. Se conserva como estadística. No cambia ningún resultado (R4). Si falla, la consulta responde igual.
- El suelo, la altitud y la pendiente de un lote **no se guardan**: la API los calcula al vuelo con `grid_cells` (ver «La rejilla de 250 m»). Un lote sin polígono usa los de su municipio.
- `support_tickets` (P1): `ticket_id`, `user_id`, `lot_id` (opcional), `message`, `status` (`open`, `in_progress`, `closed`), `created_at`, `closed_at`.
- `crop_id` y `municipality_id` deben existir en el catálogo publicado; si no, 422.
- Un lote puede tener varias temporadas en curso a la vez, cada una en una parte del lote. Las partes son de área, no de forma: no se dibujan. La suma de `area_ha` de las temporadas en curso no puede pasar del `area_ha` del lote; si pasa, 422. Vale también al editar el lote: un `PATCH` que lo deja más chico que lo que ocupan sus temporadas en curso responde 422. Sin `area_ha`, la temporada ocupa todo lo que queda libre.
- El agricultor divide su lote como quiera: puede sembrar hoy la mitad y otra parte en un mes, y al cosechar puede repartir ese terreno entre varios cultivos o juntar varias partes en una. Por eso una temporada puede venir de varias (`follows_season_ids`) y tener varias sucesoras.
- Cada temporada de `follows_season_ids` es una temporada cosechada del mismo lote, con `harvest_date` igual o anterior a `sowing_date`. El área de una temporada no puede pasar de la suma de las áreas de las que viene más el área libre del lote. La suma de las temporadas en curso nunca pasa del área del lote, y eso basta para que un terreno no se reparta dos veces. Así se puede dividir un terreno en varios y juntar varios en uno. Si algo no se cumple, 422.
- Esas relaciones son el historial de cada terreno: para las rotaciones y el progreso, los cultivos anteriores de una temporada son los de todas las temporadas de las que viene.
- El **progreso** no se guarda: la API lee las temporadas del lote y le pide al motor que evalúe las reglas de filtro sobre ese historial (temporadas registradas, rotaciones que cumplen las reglas, hitos).

### Trazabilidad: `activity_log` (HU-178)

Registro de lo que hace cada persona con una cuenta: el agricultor sobre sus datos y el administrador sobre los datos de otros. Es distinto de los logs de la terminal (HU-177, más abajo en «Logs de la terminal»): aquellos son para operar el servidor y se pierden; este se guarda en PostgreSQL para poder responder «quién hizo qué, cuándo y sobre qué».

| Columna | Qué guarda |
|---|---|
| `event_id` (UUID) | Llave primaria |
| `occurred_at` | Fecha y hora UTC |
| `request_id` | El mismo identificador de la petición que sale en la terminal y en la cabecera `X-Request-ID`: une las dos trazas |
| `actor_user_id`, `actor_role` | Quién lo hizo. Nulo solo en un inicio de sesión fallido con un usuario que no existe |
| `subject_user_id` | De quién son los datos afectados. Igual a `actor_user_id` cuando el agricultor actúa sobre lo suyo |
| `action` | Qué hizo, del catálogo de abajo |
| `object_type`, `object_id` | Sobre qué: `user`, `session`, `lot`, `season` o `ticket`, y su id |
| `outcome` | Estado del evento: `ok`, `denied` (sin permiso, bloqueado, demasiados intentos) o `failed` (error de validación o interno) |
| `ticket_id`, `reason` | Obligatorios en las acciones de un administrador sobre datos ajenos |
| `details` (JSONB) | Solo los **nombres** de los campos que cambiaron (por ejemplo `["name", "geometry"]`), nunca sus valores |

Catálogo de `action`:

| Quién | Acciones |
|---|---|
| Agricultor | `auth.registered`, `auth.login`, `auth.login_failed`, `auth.logout`, `auth.password_changed`, `profile.updated`, `consent.accepted`, `lot.created`, `lot.updated`, `lot.deleted`, `lot.restored`, `season.created`, `season.updated`, `season.deleted`, `season.restored`, `ticket.opened`, `account.deleted` |
| Administrador (P1) | `admin.user_viewed`, `admin.user_created`, `admin.user_blocked`, `admin.user_unblocked`, `admin.role_changed`, `admin.lot_deleted`, `admin.lot_restored`, `admin.season_deleted`, `admin.season_restored`, `admin.ticket_updated`, `admin.activity_viewed` |
| Desarrollador (solo desarrollo) | `dev.fixtures_loaded` |

Reglas del registro:

- **Nunca se guardan** contraseñas, tokens, cookies, el polígono ni los valores de los campos; tampoco el usuario que se intentó en un inicio de sesión fallido (podría ser una contraseña escrita en el campo equivocado), ni la IP.
- El evento se escribe **en la misma transacción** que el cambio: no hay cambio sin traza ni traza de un cambio que no ocurrió. Los intentos `denied` y `failed` se escriben aparte.
- Un bloqueo por demasiados intentos (429) deja **un** evento `denied` por ventana de 15 minutos, no uno por petición; con un usuario que no existe, ninguno (14 de octubre de 2026, revisión de seguridad; aprobado por Felipe).
- **Solo se agrega.** El usuario de base de datos de la API tiene `INSERT` y `SELECT` sobre `activity_log`, no `UPDATE` ni `DELETE`; solo la tarea de limpieza y el borrado de cuenta usan otro rol.
- Se conserva **180 días** y luego se borra. La limpieza la hace el mantenimiento de las cuentas (`python -m backend.accounts.maintenance`), que también borra las sesiones vencidas: corre al arrancar la API y se puede programar una vez al día. **Ningún endpoint la hace** (cambiado el 9 de noviembre de 2026, aprobado por Felipe: antes corría también en cada inicio de sesión).
- **Los endpoints de cálculo no escriben aquí** (R9): consultar un diagnóstico, una rotación o un plan de agua no deja ningún evento. Desde HU-170 (P1) solo suma 1 al contador anónimo `usage_daily`, que no dice quién consultó.
- **Al borrar la cuenta** se borran los eventos del agricultor. Las acciones de administradores sobre sus datos se conservan, pero con `subject_user_id`, `object_id` y `reason` en nulo, para no perder quién hizo qué sin guardar de quién era.
- Lo dice el consentimiento desde la versión 2 (vigente: 3, HU-163): «registramos lo que hace con su cuenta durante 180 días para su seguridad».

Respuesta de `GET /api/v1/me/activity` (la de `GET /api/v1/admin/activity` es igual, más `actor_user_id`, `subject_user_id` y `request_id`):

```json
{
  "items": [
    {
      "event_id": "5f0c…",
      "occurred_at": "2026-11-14T15:02:11Z",
      "action": "lot.restored",
      "actor_role": "admin",
      "object_type": "lot",
      "object_id": "a81e…",
      "outcome": "ok",
      "ticket_id": "c4d2…",
      "details": {"fields": []}
    }
  ],
  "next_before": "2026-11-14T15:02:11Z"
}
```

`next_before` es nulo cuando no hay más páginas. Varios eventos pueden tener la misma hora (los de una misma petición): si el corte de una página cae entre ellos, la página se alarga hasta incluirlos a todos, así que puede traer algunos más que `limit` (14 de octubre de 2026; aprobado por Felipe: antes se perdían). Al agricultor nunca se le muestra quién es el administrador, solo `actor_role`.

### Logs de la terminal (HU-177)

No son parte de la API ni se consultan desde la web; se documentan aquí porque fijan qué se puede escribir y qué no. Los escribe `structlog` a la salida estándar: con color en desarrollo y una línea JSON por evento en producción. En la consola cada parte tiene su color: el nivel (gris `debug`, verde `info`, amarillo `warning`, rojo `error`), el mensaje (blanco), el código de la respuesta (verde, amarillo o rojo), el endpoint (azul claro) y lo demás atenuado.

```json
{"ts": "2026-11-14T15:02:11.204Z", "level": "info", "event": "request", "request_id": "9b1e…", "method": "POST", "route": "/api/v1/lots/{lot_id}/restore", "status": 200, "duration_ms": 18, "user_id": "3c7a…", "role": "farmer", "dataset": "2026.11.1", "rules": "1.4.0"}
```

| Campo | Siempre | Notas |
|---|---|---|
| `ts`, `level`, `event`, `request_id` | Sí | `level`: `debug` (solo desarrollo), `info`, `warning` (todo lo rechazado, de `400` a `499`, y `503`), `error` (`500`, con la traza del error). Cambiado el 12 de octubre de 2026: antes solo `403` y `429` eran `warning` |
| `detail` | Sí | Qué pasó, en español y en palabras: «Inicio de sesión rechazado: usuario no registrado», «Perfil actualizado: display_name». Puede decir más que la respuesta (por ejemplo, si falló el usuario o la contraseña), porque solo se ve en la terminal del servidor. Nunca repite lo que escribió la persona |
| `endpoint` | En peticiones que llegan a una ruta | La función que atendió, como `auth.login`. Solo en el log: la respuesta no lo lleva |
| `method`, `route`, `status`, `duration_ms` | En peticiones | `route` es la plantilla de la ruta, no la URL con sus parámetros de consulta. Una dirección que no existe en la API se escribe `[sin ruta]`: nunca lo que llegó |
| `user_id`, `role` | Si hay sesión | Nunca el `username` ni el nombre |
| `dataset`, `rules` | En endpoints de cálculo | Versiones usadas (R4) |

Cuando las cuentas están apagadas, cada intento de usarlas deja un evento `accounts_unavailable` de nivel `warning` con `reason` (`database_down` o `migration_pending`), `current_migration`, `expected_migration` y `detail` («Cuentas no disponibles (503) porque la migración 2.1 no se completó; la base de datos está en la 1.9»). Al arrancar, la API registra `migration_applied`, `migration_up_to_date`, `migration_skipped` (la base no responde) o `migration_failed` (nivel `error`, con las dos versiones y la traza).

`GET /api/v1/health` responde siempre `200` mientras la API esté arriba, con `accounts`: `available`, `reason` (`ok`, `database_down` o `migration_pending`), `current_migration` y `expected_migration`.

Nunca se escriben: contraseñas, tokens, cookies, la cabecera `Authorization`, polígonos ni los cuerpos de los endpoints de cálculo (R9). Un procesador de redacción borra esas llaves de cualquier evento. Otro escribe los caracteres de control de cualquier texto como `\x1b`, para que lo que llega de afuera no parta una línea ni cambie lo que muestra la terminal. Las trazas de errores de base de datos no llevan los valores de la consulta.

## Endpoints

Los endpoints de cálculo ya existen con esta forma y sus ejemplos en el OpenAPI (HU-012): validan la entrada y responden `501` `not_implemented` hasta que llega su HU del motor.

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/catalogs/municipalities` | Municipios habilitados de la región: una lista de `municipality_id`, `name`, `department`, `lat`, `lon`, por departamento y nombre. Sin dataset publicado, `503` `dataset_unavailable` | P0 |
| `GET /api/v1/market/prices?market_id=` (HU-221, aprobado por Felipe el 10 de noviembre de 2026) | `market` (la central consultada; por defecto, la primera de la región) y `products`: el último precio de cada producto (`product_id`, `product`, `group`, `several_varieties`, `latest` con `date`, `min_cop_kg`, `avg_cop_kg` y `max_cop_kg`), con `week_ago` (el último precio hasta 7 días antes) y `change_pct`, ambos nulos si no hay con qué comparar (los tres salen de `market_price_latest`: la ruta solo filtra); `markets`, `date`, `source_id` (la fuente del último día: `dane_sipsa` o `dane_sipsa_boletin`), `citation` (la de la fila de su fuente en `sources`: la cita textual que piden los términos del DANE, que la web muestra tal cual; nula si la fuente no pide una), y `version` y `updated_at` de los precios usados (la versión del dataset publicado con `updated_at` nulo, o la última que dejaron los crons, HU-222). Sin precios publicados, `503` `market_unavailable`; una central que no está, `404` `unknown_market` | P1 |
| `GET /api/v1/market/prices/{product_id}?market_id=` (HU-221, aprobado por Felipe el 10 de noviembre de 2026) | El producto (`product_id`, `product`, `group`, `several_varieties`), la central (`market`), su último precio (`latest`) y los precios del último año en la central (`days`) y su temporada (`season`, nula sin años completos suficientes; siempre del dataset publicado), con `version`, `updated_at`, `source_id` (la del último día) y `citation`. Un producto sin precios en esa central, `404` `unknown_product` | P1 |
| `GET /api/v1/catalogs/crops` | Cultivos habilitados: `crop_id`, `name_es`, `kind`, `archetype` (cómo se dibuja, HU-187), `family`, `cycle_months`. El diagnóstico solo acepta `kind = crop`; las rotaciones aceptan los tres | P0 |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/soil` | Suelo estimado del municipio (`soil_municipality`): cada propiedad con su valor y, el pH y el carbono orgánico, con su rango del 5 al 95 %; más `slope_pct`, `cells`, `quality` y `source_id`. Sin suelo publicado, `503` `dataset_unavailable` | P0 |
| `GET /api/v1/trends?municipality_id=&crop_id=&sowing_date=` | Series para las gráficas: agua, área sembrada y verdor (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/diagnostics` | Diagnóstico de una ventana de siembra | P0 |
| `POST /api/v1/rotations` | Estrategias de rotación de hasta 3 ciclos, ordenadas según las prioridades, con la salud del suelo y el diagnóstico de cada ciclo | P0 |
| `POST /api/v1/water-plans` | Plan de agua de una finca o de un ciclo de una estrategia | P0 |
| `GET /api/v1/changes?municipality_id=&crop_id=&irrigated=` | «Qué cambió»: el clima de dos periodos y cómo se movieron las mejores ventanas del cultivo (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/calendar` | **Pasó a P1 el 11 de octubre de 2026 (HU-179).** Calendario de un cultivo en un municipio. Sin `sowing_date`: las ventanas de siembra de los próximos doce meses, ordenadas primero por el factor que más limita y después por las prioridades, con sus señales; con `month`, las semanas de ese mes. Con `sowing_date`: mes a mes, la etapa del cultivo ya sembrado y cuándo vigilar heladas y calor; también aguaceros (cuándo abonar), ventanas secas (labores y cosecha) y gota (ver «Cuerpos y respuestas») | P1 |
| `GET /api/v1/version` | Versiones del dataset y de las reglas, región y fuentes (HU-122) | P0 |
| `POST /api/v1/scenarios` | Escenario hipotético y diferencias con el caso base | P1 |

Condiciones actuales (decisión 7):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/conditions?municipality_id=` | Condición aproximada actual del municipio para la escena, de Open-Meteo: `status`, `precipitation_mm`, `cloud_cover_pct`, `wind_speed_kmh`, `wind_direction_deg`, `temp_c`, `observed_at`, `source_id`. Caché de 15 minutos. Solo el «ahora», sin pronóstico | P1 (HU-175, desde el 11 de octubre de 2026) |

`status` usa los valores de `specs/01-reglas.md`: `available` o `insufficient_data`. Sin datos del proveedor responde `200` con `status = insufficient_data` y valores nulos. Nunca entra al motor. La noche y el día los calcula la web con `lat` y `lon` del catálogo.

Endpoints de cuenta (requieren sesión, salvo `register` y `login`):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `POST /api/v1/auth/register` | Crear cuenta: `username`, `password`, `display_name`, `consent_version` y `consent_accepted`. Sin `consent_accepted = true`, responde 422 | P0 |
| `POST /api/v1/auth/login` | Iniciar sesión con `username` y `password`; deja la cookie de sesión | P0 |
| `POST /api/v1/auth/logout` | Cerrar la sesión actual | P0 |
| `GET /api/v1/me` | Perfil y consentimiento del usuario | P0 |
| `PATCH /api/v1/me` | Editar el perfil: `display_name`, `username` y `priorities` (sus pesos por señal; nulo vuelve a los de AgroSense). Responde el perfil actualizado | P1 (HU-160) |
| `POST /api/v1/me/password` | Cambiar la contraseña con `current_password` y `new_password`. Cierra las demás sesiones del usuario; la actual sigue abierta | P1 (HU-160) |
| `DELETE /api/v1/me` | Borrar la cuenta con sus sesiones, lotes, temporadas, tickets y sus eventos de `activity_log` (las acciones de administradores sobre sus datos quedan anonimizadas). Pide la contraseña en el cuerpo: `{"password": "..."}` (15 de octubre de 2026; aprobado por Felipe). Sin ella, `422`; si no coincide, `403` `wrong_password`, la sesión sigue y cuenta para los topes de intentos | P0 |
| `GET /api/v1/lots` · `POST /api/v1/lots` | Listar y crear lotes. Cada lote de la lista trae `current_crop_ids`: los cultivos en curso, de mayor a menor área, para la fila de Mi finca (agregado el 15 de octubre de 2026; aprobado por Felipe). Con HU-204 (P1), la lista incluye los lotes borrados hace menos de 30 días, con `deleted_at` y `restorable_until` | P0 |
| `GET`, `PATCH`, `DELETE /api/v1/lots/{lot_id}` | Ver, editar y borrar un lote. `GET` trae las temporadas en curso, cada una con su parte del área y su etapa estimada (ver «Cuerpos de cuenta»). `DELETE` es reversible durante 30 días | P0 |
| `POST /api/v1/lots/{lot_id}/restore` | Restaurar un lote borrado hace menos de 30 días. Restaura también las temporadas que se borraron con él. Pasados los 30 días, o si no está borrado, 404 | P1 (HU-204) |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/boundary` | Límite del municipio en GeoJSON (`Feature` con `municipality_id`, `name` y `source_id`; aprobado por Felipe el 16 de octubre de 2026), para centrar el mapa y validar el dibujo en la web. Un municipio fuera de la región, 404 | P0 |
| `GET /api/v1/me/activity?before=&limit=` | Mi actividad: los eventos de `activity_log` del usuario y las acciones de soporte sobre sus datos, del más reciente al más antiguo, paginados (`limit` hasta 50). Ver «Trazabilidad» | P1 (HU-178) |
| `POST /api/v1/me/tickets` · `GET /api/v1/me/tickets` | Reportar un problema (opcionalmente sobre un lote) y ver sus tickets | P1 |
| `GET /api/v1/lots/{lot_id}/seasons` · `POST /api/v1/lots/{lot_id}/seasons` | Historial del lote y nueva temporada. Con HU-204 (P1), el historial incluye las temporadas borradas hace menos de 30 días, con `deleted_at` y `restorable_until`, para poder restaurarlas | P0 |
| `PATCH`, `DELETE /api/v1/seasons/{season_id}` | Registrar la cosecha, corregir o borrar una temporada. `DELETE` es reversible durante 30 días | P0 |
| `POST /api/v1/seasons/{season_id}/restore` | Restaurar una temporada borrada hace menos de 30 días. Vuelve a validar el área y las temporadas de las que viene: si ya no cabe, 422. Pasados los 30 días, o si no está borrada, 404. Lo borrado no cuenta en el área libre ni en el progreso | P1 (HU-204) |
| `GET /api/v1/lots/{lot_id}/progress` | Progreso derivado del historial | P1 (HU-167) |
| `GET /api/v1/seasons/{season_id}/growth` | Línea de tiempo de un cultivo en curso, de la siembra a la cosecha estimada, para simular el paso del tiempo (ver «Cuerpos de cuenta») | P1 (HU-186) |

**Cómo viaja la credencial:** el usuario y la contraseña solo se envían una vez, en `/auth/register` y `/auth/login`, siempre por HTTPS. La API responde con un token de sesión aleatorio de 256 bits; en la base de datos se guarda solo su hash. De ahí en adelante cada petición lleva únicamente ese token, nunca la contraseña. El token viaja en una cookie `httpOnly` (el JavaScript de la página no lo puede leer), `Secure` (solo por HTTPS) y `SameSite=Lax`; además, la API rechaza las peticiones que cambian datos si su cabecera `Origin` no es la de la web (protección contra CSRF). Como la API y la web comparten origen, no hace falta CORS. Contraseña de al menos 8 caracteres. Los intentos fallidos de entrar, de cambiar la contraseña y de borrar la cuenta cuentan para los topes de abajo. Recuperar la contraseña queda en P1, porque no se guarda correo ni celular. Un usuario solo ve y modifica sus propios lotes: pedir uno ajeno responde 404.

**Límites por conexión y topes de intentos** (15 de octubre de 2026, revisión de seguridad; aprobado por Felipe). Todo lo que verifica una contraseña (entrar, cambiar la contraseña y borrar la cuenta) anota el intento **antes** de verificarla:

| Límite | Cuánto | Dónde vive | Respuesta |
|---|---|---|---|
| Contraseñas que no coinciden para un usuario **desde una misma conexión** | 5 en 15 minutos | Memoria de la API | `429` `too_many_attempts`, solo para esa conexión |
| Intentos fallidos de un usuario **desde cualquier conexión** (ataque repartido) | 20 en 15 minutos | `login_attempts` (sobrevive a un reinicio) | `429` `too_many_attempts` |
| Inicios de sesión desde una misma conexión, salgan bien o mal | 30 en 15 minutos | Memoria de la API | `429` `too_many_requests` |
| Registros desde una misma conexión, salgan bien o mal (también los `409`) | 10 por hora | Memoria de la API | `429` `too_many_requests` |
| Cálculos de contraseña (Argon2, unos 64 MiB cada uno) a la vez | 4; los demás esperan hasta 10 segundos | Memoria de la API | `503` `server_busy` |

- Todo `429` y el `503` llevan `Retry-After` con los segundos que faltan.
- Así, equivocarse a propósito con la contraseña de otra persona solo bloquea la conexión de quien lo hace, no la cuenta; y el `409` del registro no sirve para probar en masa qué usuarios existen.
- **La IP no se guarda** (R9): ni en la base de datos ni en el log. En memoria solo queda su hash con una sal aleatoria que cambia cada vez que arranca la API, y se olvida al pasar la ventana. Un reinicio borra los límites de memoria; el tope general sigue.
- Detrás de un proxy, Uvicorn toma la IP de `X-Forwarded-For` solo si el proxy está en `FORWARDED_ALLOW_IPS`; si no, todas las personas parecerían una sola conexión.

**Cabeceras de seguridad** (14 de octubre de 2026, revisión de seguridad; aprobado por Felipe): toda respuesta lleva `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` y, por HTTPS, `Strict-Transport-Security`. `/api/v1/auth/*` y `/api/v1/me*` van además con `Cache-Control: no-store`. La documentación (`/api/docs` y `/api/openapi.json`) solo existe con `AGROSENSE_API_DOCS=true`, en desarrollo.

### Roles (documentado; se implementa en HU-170)

Cada usuario tiene un `role`. Hoy solo existe `farmer`; los otros dos quedan definidos para no rehacer el esquema después.

| Rol | Valor | Quién es | Qué puede hacer | Dónde existe |
|---|---|---|---|---|
| Agricultor | `farmer` | El usuario final | Consultar, sus lotes, sus temporadas y su cuenta. **Nunca ve datos inventados**: solo el dataset publicado y lo que él registró (R5) | Producción y desarrollo. Es el rol por defecto al registrarse |
| Administrador web | `admin` | Quien opera la web y da soporte | Lo del agricultor, más: ver a los agricultores con sus lotes, temporadas y tickets; borrar y restaurar lotes y temporadas para resolver un ticket; crear, bloquear y desbloquear usuarios; ver métricas de uso agregadas y la bitácora. Toda acción queda en `activity_log` | Producción y desarrollo. Solo lo asigna otro administrador o la configuración inicial |
| Desarrollador | `developer` | El equipo, con la app en modo desarrollo | Lo del administrador, más: simulaciones con datos inventados (HU-014), crear datos de prueba y saltarse los topes y límites (intentos, ritmo, velocidad del recorrido) | **Solo en desarrollo** (`AGROSENSE_SIMULATION=true`). La API se niega a arrancar en producción si existe un usuario `developer` o si la simulación está activa |

Endpoints previstos (P1, sin implementar; requieren sesión y el rol indicado, si no `403`):

| Endpoint | Rol | Uso |
|---|---|---|
| `GET /api/v1/admin/users` | `admin` | Lista de usuarios: `user_id`, `username`, `display_name`, `role`, `created_at`, `blocked_at`, número de lotes y de tickets abiertos |
| `GET /api/v1/admin/users/{user_id}` | `admin` | Ficha de un agricultor: perfil, lotes (también los borrados hace menos de 30 días), temporadas y tickets. Se registra en `activity_log` como `admin.user_viewed` |
| `DELETE` y `POST …/restore` en `/api/v1/admin/lots/{lot_id}` y `/api/v1/admin/seasons/{season_id}` | `admin` | Borrar o restaurar un lote o una temporada de un agricultor. Exige `reason` y, si viene de un ticket, `ticket_id` |
| `GET /api/v1/admin/tickets` · `PATCH /api/v1/admin/tickets/{ticket_id}` | `admin` | Bandeja de tickets y cambio de estado |
| `POST /api/v1/admin/users` | `admin` | Crear un usuario con `username`, `display_name` y una contraseña temporal |
| `PATCH /api/v1/admin/users/{user_id}` | `admin` | Bloquear o desbloquear (`blocked`), y cambiar el rol entre `farmer` y `admin` |
| `GET /api/v1/admin/activity?user_id=&action=&outcome=&from=&to=&before=&limit=` | `admin` | Bitácora: eventos de `activity_log` con filtros, paginados. Consultarla también queda registrado (`admin.activity_viewed`) |
| `GET /api/v1/admin/metrics` | `admin` | Métricas agregadas: consultas por día, cuentas creadas, municipios y cultivos más consultados (de `usage_daily`), lotes por municipio y siembras por cultivo (de las cuentas). Sin datos personales. Un municipio o cultivo con menos de 5 consultas, o con lotes de menos de 5 cuentas, va en «Otros» |
| `POST /api/v1/dev/fixtures` | `developer` | Cargar datos de prueba en la base de desarrollo |

- Un usuario bloqueado no puede iniciar sesión (`403` con `account_blocked`) y sus sesiones abiertas se cierran.
- En desarrollo, toda respuesta construida con datos simulados lleva `"simulated": true` en la raíz; la web muestra la franja «Modo simulación · datos de ejemplo» (HU-014, R5). En producción ese campo no existe.
- El administrador ve datos personales de los agricultores, así que el texto de consentimiento lo dice («el equipo de soporte puede ver sus lotes para resolver un problema») desde la versión 2 (vigente: 3, HU-163). El agricultor ve en «Mi actividad» (`GET /me/activity`) qué acciones de soporte se hicieron sobre sus datos.
- Por decidir: qué más hace el administrador, y si su panel va en esta web o en una aparte.

### Cómo se conectan cálculo y cuentas

- `/diagnostics`, `/rotations`, `/water-plans`, `/changes`, `/calendar` y `/scenarios` **no guardan los datos de la finca ni quién consultó (R9)**, con o sin cuenta. Desde HU-170 (P1) solo suman 1 al contador anónimo `usage_daily`.
- Con sesión, `/diagnostics` y `/rotations` (y `/calendar`, P1) aceptan `lot_id` solo para leer el lote: usan su suelo, su altitud (para la aptitud) y su verdor (las medianas de las celdas cuyo centro cae dentro de su polígono) y su `irrigated`; el resultado es el mismo que si se enviaran esos datos. `/water-plans` y `/changes` no reciben `lot_id` y usan siempre los datos del municipio, también con cuenta.
- Para las estrategias de un lote, la web envía en `previous_crop_ids` los cultivos de las temporadas de las que viene el terreno que se va a sembrar (`follows_season_ids`). Sin cuenta, el usuario elige a mano el cultivo anterior, o ninguno.
- Para el agua de un ciclo de una estrategia, la web llama a `/water-plans` con el cultivo del ciclo, su `sowing_date`, el área de la entrada como `total_area_ha` y `area_pct` 100 (HU-215).
- Para el plan de agua de una zona (P1, HU-145), la web arma `crops` con las temporadas en curso de los lotes de ese municipio: `total_area_ha` es la suma de las áreas de los lotes y `area_pct` la parte de cada temporada (`seasons.area_ha` / `total_area_ha`).

### Identificador de petición

Toda respuesta lleva la cabecera `X-Request-ID` (UUID). Si la petición trae una válida, se respeta; si no, la API la crea. Ese identificador aparece en cada línea de log de la terminal y en `activity_log.request_id`, y la web lo muestra en los errores («Código para soporte: …») para que un ticket se pueda rastrear.

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, diagnóstico de un cultivo con `kind` distinto de `crop`, prioridades fuera de rango o todas en 0, `sowing_date` con formato inválido, anterior a hoy o a más de doce meses (salvo en «Mi cultivo»), `month` fuera de 1 a 12, `cycles` distinto de 2 o 3, más de 3 cultivos en `previous_crop_ids`, `current_crop_ids` con menos de 2 o más de 3 cultivos, `/changes` con un cultivo que no es `kind = crop`, porcentajes de finca que pasan de 100, registro sin consentimiento, temporadas en curso que pasan del área del lote, lote editado más chico que sus temporadas en curso, `follows_season_ids` inválido, nombre vacío, contraseña nueva de menos de 8 caracteres o igual a la actual) | `422` |
| Endpoint de cuenta sin sesión válida, usuario y contraseña incorrectos, o `lot_id` en `/diagnostics`, `/rotations` o `/calendar` sin sesión | `401` |
| Contraseña actual incorrecta al cambiarla, o contraseña incorrecta al borrar la cuenta | `403` `wrong_password` (la sesión sigue abierta) |
| Rol sin permiso para el endpoint, o cuenta bloqueada al iniciar sesión | `403` |
| Nombre de usuario ya registrado, al crear la cuenta o al editar el perfil | `409` |
| `lot_id` de un lote de otro municipio que el `municipality_id` de la consulta, en `/diagnostics` y `/rotations` (agregado el 13 de noviembre de 2026 en HU-191, aprobado por Felipe el 13 de noviembre de 2026: mezclaría la temperatura de un municipio con la altitud de otro). Mensaje: «Ese lote es de otro municipio.» | `422` `invalid_input` |
| Un lote que quedaría más chico que lo sembrado en curso | `422` `area_below_seasons` |
| Una temporada que no cabe en lo libre del lote | `422` `area_exceeds_free` |
| Demasiados intentos con la contraseña de un usuario (`too_many_attempts`) o demasiadas peticiones de entrar o crear cuenta desde una misma conexión (`too_many_requests`) | `429` con `Retry-After` |
| Todos los cálculos de contraseña ocupados (agregado el 15 de octubre de 2026; aprobado por Felipe) | `503` `server_busy` con `Retry-After` |
| Lote o temporada que no existe o es de otro usuario | `404` |
| Entrada válida sin datos | `200` con `insufficient_data` en la señal |
| Cultivo que no es apto para la zona | `200` con `suitability.level = not_suitable`, luz `red` y acción `rotate`; sin ventanas |
| Las cuentas no se pueden atender (agregado el 12 de octubre de 2026; aprobado por Felipe): la base de datos no responde, o su esquema no está en la última migración que trae el código | `503` en los endpoints de cuenta, con `code = accounts_database_down` o `accounts_migration_pending`. El mensaje para la persona es el mismo en los dos casos («Las cuentas no están disponibles en este momento. Puede seguir consultando sin cuenta.»); el motivo exacto va al log de la terminal. Los endpoints que no usan la base de datos siguen respondiendo |
| El dataset publicado no está o no se puede leer (agregado el 15 de octubre de 2026; aprobado por Felipe) | `503` `dataset_unavailable` en los endpoints que lo leen (catálogos y crear o editar un lote); el motivo va al log. `GET /version` responde igual, con los campos del dataset nulos |
| Endpoint del contrato que todavía no está construido (decisión 15) | `501` `not_implemented`, con el mismo formato de error. El OpenAPI ya trae su forma y sus ejemplos |
| El dataset publicado no trae precios (HU-221, aprobado por Felipe el 10 de noviembre de 2026) | `503` `market_unavailable` en `/market/*` |
| Central que no está en la región, o producto sin precios en esa central (HU-221, aprobado por Felipe el 10 de noviembre de 2026) | `404` `unknown_market` o `404` `unknown_product` en `/market/*` |
| Fallo interno | `500` con `{"error": {"code": "...", "message": "...", "request_id": "..."}}` |

## Cuerpos y respuestas

Los ejemplos son ilustrativos, no son datos reales. Toda respuesta de cálculo trae `versions` con `dataset` y `rules` (R4).

### Cuerpo de `POST /api/v1/diagnostics`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "sowing_date": "2026-08-03", "irrigated": false,
  "priorities": { "water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3 }, "lot_id": null }
```

Evalúa **una ventana de siembra**: de `sowing_date` a la cosecha estimada de ese cultivo (ver `specs/01-reglas.md`). Es riesgo histórico de esa época del año, no un pronóstico: la misma fecha en otro año da el mismo resultado de clima.

- `sowing_date` anterior a hoy o a más de doce meses responde 422 (ver «Fechas» en `/calendar`). «Hoy» es el de la hora de la región: en la piloto, `America/Bogota` (UTC−5).
- `irrigated`: si hay riego. Con riego, la falta de lluvia no es un riesgo en la señal `water`. Nulo se trata como sin riego y se agrega a las limitaciones.
- `priorities`: el peso de 0 a 5 de cada señal para quien consulta (ver «Las prioridades del agricultor» en `specs/01-reglas.md`). Opcional: sin él se usan los pesos por defecto de `weights.yaml`. Fuera de rango, o todas en 0, responde 422.
- `lot_id` es opcional y exige sesión: con él, la señal de suelo usa el suelo del lote y `irrigated` se toma del lote. Un lote ajeno responde 404.

**No guarda los datos de la finca ni quién consultó (R9).** La respuesta está en «Respuesta de diagnóstico», más abajo.

### Respuesta de `GET /api/v1/trends`

Tres series separadas, cada una con su unidad, para no mezclar unidades en un eje (W3):

- `water`: por año, la lluvia que cayó en los meses de la ventana (`precip_mm`) y lo que el cultivo habría necesitado (`need_mm`), en mm, con el `source_id` de la lluvia (la fuente que calcula la señal).
- `supply`: por año, `planted_ha` (ha) y `preliminary` del semestre en que cae la fecha de siembra.
- `ndvi`: por `period` (1 a 23), `ndvi_normal` del municipio, con `source_id` y `quality` (HU-208). Sirve para ver cuándo suele estar verde el campo junto a la ventana.

Sin datos para una serie, la serie viene vacía con `status = insufficient_data`. No guarda nada (R9).

```json
{
  "request": { "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "sowing_date": "2027-08-02" },
  "water": { "status": "available", "source_id": "imerg", "unit": "mm",
             "points": [ { "year": 2015, "precip_mm": 410, "need_mm": 465 } ] },
  "supply": { "status": "insufficient_data", "source_id": "eva", "unit": "ha", "semester": "B", "points": [] },
  "ndvi": { "status": "available", "source_id": "modis_ndvi", "quality": "ok",
            "points": [ { "period": 1, "ndvi_normal": 0.52 } ] },
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

### Respuesta de `GET /api/v1/version`

`dataset_version`, `rules_version`, `created_at`, `region`, `default_weights` (los pesos por defecto de `weights.yaml`, para mostrarlos antes de consultar), `weights_version` (la versión de `weights.yaml`), `weights_reasons` (el porqué de cada peso, como criterio del equipo) y `sources` (lista con `source_id`, `name`, `institution`, `url`, `coverage` y `license`). Es lo que muestra el panel «¿Cómo funciona y de dónde sale esto?».

> **13 de octubre de 2026 (aprobado por Felipe):** el endpoint ya existe con lo único que hay, los pesos por defecto. Mientras no haya dataset ni reglas publicados, `dataset_version`, `rules_version`, `created_at` y `region` vienen nulos y `sources` vacío: no se inventan (R5). `weights_version` y `weights_reasons` son campos nuevos. No usa la base de datos ni guarda nada.

### Respuestas de `GET /api/v1/market/prices` y `GET /api/v1/market/prices/{product_id}` (HU-221, HU-222)

Consultan los precios mayoristas diarios y la estacionalidad histórica de SIPSA servidos desde memoria a partir de los Parquet locales (`data/market/` o `data/published/`; ver «Ingestión, almacenamiento y actualización diaria de precios de SIPSA» más arriba). **Es historia de precios mayoristas, nunca pronóstico (decisión 4).** No usan PostgreSQL ni guardan quién consultó (R9). Los ejemplos son respuestas reales con el dataset `2026.11.4`, recortadas a un producto.

**1. `GET /api/v1/market/prices?market_id=1`** (`market_id` opcional; sin él se usa la primera central de la región):

```json
{
  "version": "2026.11.4",
  "updated_at": null,
  "market": { "market_id": "1", "name": "Corabastos (Bogotá)" },
  "markets": [
    { "market_id": "1", "name": "Corabastos (Bogotá)" },
    { "market_id": "9", "name": "Tunja (Complejo de Servicios del Sur)" }
  ],
  "date": "2026-10-19",
  "products": [
    {
      "product_id": "papa-negra",
      "product": "Papa negra",
      "group": "Tubérculos, raíces y plátanos",
      "several_varieties": true,
      "latest": { "date": "2026-10-19", "min_cop_kg": 2800, "avg_cop_kg": 2925, "max_cop_kg": 3000 },
      "week_ago": { "date": "2026-10-12", "min_cop_kg": 3000, "avg_cop_kg": 3150, "max_cop_kg": 3200 },
      "change_pct": -7.1
    }
  ],
  "source_id": "dane_sipsa",
  "citation": "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co"
}
```

- `date`: el último día con precios en esa central.
- `version` y `updated_at`: con una versión de los crons (HU-222), `sipsa-AAAAMMDDTHHMMSS-boletin` o `-servicio` y cuándo se escribió; con el dataset publicado, `dataset_version` y `null`.
- `products`: un elemento por producto de la central, por grupo (primero tubérculos, raíces y plátanos; las frutas al final) y por nombre, con su último precio (`latest`). En un día del boletín, `min_cop_kg` y `max_cop_kg` van `null` (R1).
- `week_ago`: el último precio del producto con fecha menor o igual a `latest.date - 7 días` en esa central. Si no hay, `week_ago` y `change_pct` van `null` (R1).
- `source_id`: la fuente del último día (`dane_sipsa` o `dane_sipsa_boletin`); `citation`: la columna `citation` de esa fuente en `sources`, que la web muestra tal cual; nula si la fuente no pide una (R1).

**2. `GET /api/v1/market/prices/{product_id}?market_id=1`**:

```json
{
  "version": "2026.11.4",
  "updated_at": null,
  "product_id": "papa-negra",
  "product": "Papa negra",
  "group": "Tubérculos, raíces y plátanos",
  "several_varieties": true,
  "market": { "market_id": "1", "name": "Corabastos (Bogotá)" },
  "latest": { "date": "2026-10-19", "min_cop_kg": 2800, "avg_cop_kg": 2925, "max_cop_kg": 3000 },
  "days": [
    { "date": "2026-10-17", "min_cop_kg": 2800, "avg_cop_kg": 2925, "max_cop_kg": 3000 },
    { "date": "2026-10-19", "min_cop_kg": 2800, "avg_cop_kg": 2925, "max_cop_kg": 3000 }
  ],
  "season": {
    "years": 5,
    "first_year": 2021,
    "last_year": 2025,
    "months": [
      { "month": 1, "seasonal_index": 1.063 },
      { "month": 2, "seasonal_index": 1.066 }
    ]
  },
  "source_id": "dane_sipsa",
  "citation": "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co"
}
```

- `days`: los precios del último año (desde `latest.date - 365 días`), del más viejo al más nuevo.
- `season`: la estacionalidad del producto en esa central (`market_price_season`, del dataset publicado), o `null` si no tiene al menos 3 años calendario completos (R1). Los meses más caros y más baratos los calcula la web.

### Cuerpo y respuesta de `POST /api/v1/rotations`

```json
{
  "municipality_id": "MUNICIPIO_ID",
  "sowing_date": "2027-01-04",
  "previous_crop_ids": ["papa"],
  "current_crop_ids": ["papa", "arveja"],
  "cycles": 3,
  "priorities": { "water": 3, "soil": 5, "income": 2, "risk": 4 },
  "signal_priorities": null,
  "irrigated": false,
  "lot_id": null
}
```

Responde **estrategias de rotación** de hasta 3 ciclos (ver «Estrategias de rotación» en `specs/01-reglas.md`). No guarda los datos de la finca ni quién consultó (R9).

- `cycles`: 2 o 3; sin él, 3. Otro valor responde 422.
- `sowing_date`: la fecha en que se sembraría el primer ciclo. Anterior a hoy o a más de doce meses responde 422. Los ciclos siguientes pueden caer después de esos doce meses.
- `previous_crop_ids`: de 0 a 3 cultivos del catálogo (de cualquier `kind`), el más reciente primero. Vacía es la primera siembra del terreno.
- `current_crop_ids` (decisión 14, aprobado por Felipe el 8 de noviembre de 2026): opcional; la rotación que el agricultor viene haciendo, de 2 a 3 cultivos del catálogo en el orden en que los siembra. Se evalúa como la estrategia de referencia (`current_strategy`); si tiene menos cultivos que `cycles`, se repite desde el primero. Sin ella no hay referencia y `limitations` lo dice. Con menos de 2 o más de 3 cultivos, o alguno fuera del catálogo, responde 422.
- `priorities`: las cuatro prioridades de la rotación (`water`, `soil`, `income`, `risk`), un entero de 0 a 5 cada una.
- `signal_priorities`: opcional; los pesos de 0 a 5 por señal para el diagnóstico de cada ciclo, igual que `priorities` de `/diagnostics`. Sin él, los de `weights.yaml`.
- `irrigated`: igual que en el diagnóstico. `lot_id` es opcional y exige sesión: con él, el suelo, la altitud, el verdor e `irrigated` salen del lote.
- Prioridades fuera de rango, o todas en 0, responden 422.

```json
{
  "strategies": [
    {
      "rank": 1,
      "kind": "suggested",
      "crop_ids": ["avena_vicia", "arveja", "papa"],
      "total_score": 76,
      "scores": { "water": 74, "soil": 88, "income": 60, "risk": 71 },
      "vs_current": { "water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15 },
      "cycles": [
        { "cycle": 1, "crop_id": "avena_vicia", "sowing_date": "2027-01-04", "harvest_estimate": "2027-04-19",
          "harvest_basis": "calendar", "light": "green", "light_default": "green", "limiting_signal": "water", "high_risk": false },
        { "cycle": 2, "crop_id": "arveja", "sowing_date": "2027-04-26", "harvest_estimate": "2027-08-23",
          "harvest_basis": "calendar", "light": "yellow", "light_default": "yellow", "limiting_signal": "frost", "high_risk": false },
        { "cycle": 3, "crop_id": "papa", "sowing_date": "2027-08-30", "harvest_estimate": "2028-01-24",
          "harvest_basis": "calendar", "light": "green", "light_default": "green", "limiting_signal": "frost", "high_risk": false }
      ],
      "soil_health": {
        "nitrogen": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"], "source_ids": ["FUENTE_ID"],
          "reasons": ["Dos de los tres ciclos tienen leguminosas (vicia y arveja), que fijan nitrógeno"] },
        "organic_carbon": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"], "source_ids": ["FUENTE_ID", "soilgrids"],
          "reasons": ["El carbono orgánico estimado del suelo es bajo y la estrategia empieza con un abono verde"] },
        "soil_cover": { "status": "available", "level": "moderate", "rule_ids": ["REGLA_ID"], "source_ids": ["FUENTE_ID"],
          "reasons": ["El suelo queda cubierto 11 de los 13 meses de la estrategia"] },
        "pest_break": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"], "source_ids": ["FUENTE_ID"],
          "reasons": ["La papa vuelve al terreno después de dos ciclos de otras familias"] },
        "erosion": { "status": "available", "level": "moderate", "rule_ids": ["REGLA_ID"], "source_ids": ["FUENTE_ID", "nasadem"],
          "reasons": ["El lote tiene una pendiente de 14 % y el suelo queda descubierto 2 meses"] }
      },
      "reasons": ["Empieza con un abono verde y su suelo tiene poco carbono orgánico", "Ningún ciclo tiene un riesgo alto de clima"],
      "limitations": ["Suelo estimado para el municipio, no para su lote"]
    }
  ],
  "current_strategy": {
    "rank": null,
    "kind": "current",
    "crop_ids": ["papa", "arveja", "papa"],
    "total_score": 61,
    "scores": { "water": 68, "soil": 50, "income": 69, "risk": 59 },
    "cycles": [],
    "soil_health": {},
    "issues": [
      { "cycle": 3, "kind": "rule", "rule_id": "REGLA_ID",
        "reason": "La papa vuelve al terreno después de un solo ciclo de otra familia", "source_ids": ["FUENTE_ID"] }
    ],
    "reasons": ["Es la rotación que usted viene haciendo: las demás se comparan contra ella"],
    "limitations": []
  },
  "excluded": [
    { "crop_ids": ["papa", "arveja", "haba"], "cycle": 1, "kind": "rule", "rule_id": "REGLA_ID",
      "reason": "Repite la familia de la papa, que había antes en el terreno", "source_ids": ["FUENTE_ID"] },
    { "crop_ids": ["arveja", "papa", "maiz"], "cycle": 2, "kind": "high_risk", "signal": "frost",
      "reason": "Alto riesgo en el ciclo 2: heladas frecuentes en el llenado de la papa", "source_ids": ["nasa_power"] }
  ],
  "weights": { "water": 3, "soil": 5, "income": 2, "risk": 4 },
  "soil_basis": "municipality",
  "limitations": ["Compara estrategias según reglas con fuente. No predice cuánto va a mejorar el suelo"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `strategies`: hasta 10, en orden (`rank`). `scores` trae el puntaje de 0 a 100 de cada criterio (nulo si no califica) y `total_score` el total ponderado por `weights`. Cómo se calcula cada criterio está en `specs/01-reglas.md` («Estrategias de rotación»).
- Cada ciclo trae además `diagnosis`: el diagnóstico de esa ventana, con la misma forma de «Respuesta de diagnóstico» (sin `request`, `best_windows` ni `alternatives`). El ejemplo lo omite por brevedad. `light` es la luz con los pesos de quien consulta y `light_default` con los de AgroSense. En un ciclo de descanso, `light`, `light_default`, `limiting_signal` y `diagnosis` vienen nulos.
- `kind`: `suggested` en las estrategias del ranking y `current` en la de referencia. `vs_current`: en cada sugerida, la diferencia de cada criterio y del total frente a la actual (positivo es mejor); nulo sin rotación actual o si el criterio no califica en alguna de las dos.
- `current_strategy` (decisión 14, aprobado por Felipe el 8 de noviembre de 2026): la rotación actual evaluada con la misma forma de una estrategia (el ejemplo omite sus ciclos y su salud del suelo por brevedad), con `rank` nulo. **Nunca se excluye:** si viola una regla, tiene un cultivo no apto, un pH fuera de rango o un ciclo de alto riesgo, `issues` lo dice con la misma forma de `excluded` (sin `crop_ids`). Nula sin `current_crop_ids`. Una estrategia sugerida igual a la actual no se repite en `strategies`.
- `soil_health`: los cinco criterios de salud del suelo (`erosion` desde la decisión 14), cada uno con `status`, `level` (nulo con `insufficient_data`), `reasons`, `rule_ids` (reglas de `rotation_rules`, con fuente) y `source_ids` (las fuentes de esas reglas y de los datos que usan, para que la web las cite; vacía sin regla con fuente). **No es una predicción de cuánto mejora el suelo.**
- `excluded`: las estrategias descartadas, con el ciclo y el motivo. **Trae hasta 10** (decisión 15): primero las que quedaron fuera por un solo motivo, y entre ellas, en el orden en que se habrían ordenado. `excluded_counts` cuenta todas las descartadas por `kind` (por ejemplo `{"rule": 212, "high_risk": 48, "not_suitable": 30, "soil_ph": 0}`), para que la web diga cuántas son sin traerlas todas. `kind` es `rule` (viola una regla de filtro; trae `rule_id`), `not_suitable` (un cultivo no se da en la zona), `soil_ph` (el pH queda fuera de todo el intervalo) o `high_risk` (un ciclo con `water`, `frost` o `heat` desfavorable y crítica; trae `signal`).
- Cada descartada y cada `issues` trae `source_ids`: la fuente de su regla, de la ficha del cultivo, del suelo o del clima de la señal (R8).
- La oferta y el mercado no excluyen estrategias: entran solo por `income`.
- `soil_basis` y `slope_basis`: `lot` o `municipality`, de dónde salen el suelo y la pendiente.
- Sin estrategias válidas, `strategies` viene vacía y `excluded` dice por qué.

Con cuenta, la web arma `previous_crop_ids` con los cultivos de las temporadas de las que viene el terreno que se va a sembrar (`follows_season_ids`). Con el suelo (del lote o del municipio): un cultivo cuyo rango de pH tolerado queda fuera de **todo** el intervalo `ph_p05`–`ph_p95` excluye la estrategia por regla (R3); el carbono orgánico entra al criterio `organic_carbon` de `soil_health`, con reglas de `rotation_rules` con fuente. Cada estrategia trae de 2 a 4 razones.

Cambió el 11 de octubre de 2026 (decisión 12): antes respondía secuencias de 2 ciclos sin `soil_health`, y `previous_crop_ids` pedía al menos un cultivo.

> **8 de noviembre de 2026 (decisión 14, aprobado por Felipe):** `current_crop_ids` en el cuerpo; `kind`, `vs_current`, `current_strategy` con `issues` y el criterio `erosion` de `soil_health` en la respuesta.

> **11 de noviembre de 2026 (HU-102, aprobado por Haider; decisión 15 de `docs/decisiones.md`):** `source_ids` en cada criterio de `soil_health`, en cada `issues` y en cada `excluded`. Es un campo nuevo; los demás no cambian.

### Cuerpo de `POST /api/v1/water-plans`

```json
{
  "municipality_id": "MUNICIPIO_ID",
  "total_area_ha": 5.0,
  "crops": [
    { "crop_id": "papa", "area_pct": 60, "sowing_date": "2026-03-15" },
    { "crop_id": "arveja", "area_pct": 30, "sowing_date": "2026-04-01" }
  ]
}
```

La suma de `area_pct` no puede pasar de 100. Lo que falta es terreno en descanso o sin sembrar. Con cuenta, entran las temporadas en curso de cada lote, cada una con su `area_ha`. La respuesta trae, por cultivo y por finca, el déficit mensual y el volumen en m³ para año normal y año seco, con rangos y el rótulo de estimación (R10). **Este endpoint no guarda los datos de la finca ni quién consultó (R9)**, aunque el usuario tenga cuenta. No recibe `lot_id`: usa siempre el suelo del municipio (`soil_municipality`), también con cuenta.

La lluvia es la de la fuente que define `sources.yaml` y la ET0 es la de `climate_month`; la respuesta dice la fuente de cada una. Trae además `soil_moisture`: por mes, la humedad del suelo normal de la zona según cada fuente (`source_id`, `indicator`, `value`, `unit`), la de POWER y, si existe, la de SMAP. Es contraste: no cambia el déficit.

```json
{
  "request": { "municipality_id": "MUNICIPIO_ID", "total_area_ha": 1.26,
               "crops": [ { "crop_id": "papa", "area_pct": 100, "sowing_date": "2027-08-02" } ] },
  "crops": [
    { "crop_id": "papa", "area_ha": 1.26, "sowing_date": "2027-08-02", "harvest_estimate": "2027-12-27", "harvest_basis": "calendar",
      "months": [
        { "year": 2027, "month": 9, "stage": "development", "need_mm": 95, "rain_mm": { "normal": 70, "dry": 41 },
          "deficit_mm": { "normal": [20, 30], "dry": [48, 62] }, "volume_m3": { "normal": [252, 378], "dry": [605, 781] } }
      ],
      "total_volume_m3": { "normal": [900, 1300], "dry": [2100, 2700] } }
  ],
  "farm": { "months": [ { "year": 2027, "month": 9, "volume_m3": { "normal": [252, 378], "dry": [605, 781] } } ],
            "total_volume_m3": { "normal": [900, 1300], "dry": [2100, 2700] } },
  "soil_moisture": [ { "month": 9, "source_id": "nasa_power", "indicator": "soil_wetness_root", "value": 0.61, "unit": "fracción" } ],
  "sources": { "rain": "imerg", "et0": "nasa_power", "soil": "soilgrids" },
  "soil_basis": "municipality",
  "limitations": ["Es una estimación con el clima de la zona: verifique la humedad del suelo en su lote"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `deficit_mm` y `volume_m3` son rangos `[mínimo, máximo]` (R10): el rango sale de la retención de agua del suelo con sus percentiles 5 y 95. Un mes sin déficit trae `[0, 0]`.
- `dry` es el año seco de la lluvia (`precip_dry_mm`). Sin lluvia de la fuente usada para un mes, ese mes trae `status = insufficient_data` y valores nulos (R1).

### Respuesta de `GET /api/v1/changes`

`GET /api/v1/changes?municipality_id=MUNICIPIO_ID&crop_id=papa&irrigated=false`. Compara dos periodos de la misma fuente (ver «Qué cambió en la zona» en `specs/01-reglas.md`). **Es historia comparada, nunca pronóstico.** No guarda nada (R9). `irrigated` es opcional; sin él se compara sin riego y se dice en las limitaciones.

```json
{
  "request": { "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "irrigated": false },
  "periods": {
    "before": { "period_id": "p1981_2000", "start_year": 1981, "end_year": 2000, "source_id": "nasa_power" },
    "after": { "period_id": "p2005_2024", "start_year": 2005, "end_year": 2024, "source_id": "nasa_power" }
  },
  "suitability": { "level": "suitable", "score": 92, "basis": "municipality", "tmean_annual_c": 12.8, "altitude_m": 2660,
                   "reasons": ["La temperatura media anual del municipio (12,8 °C) está dentro del rango de la papa (8 a 16 °C)"] },
  "months": [
    { "month": 1,
      "frost_freq_pct": { "status": "available", "before": 30, "after": 18, "change": -12 },
      "precip_normal_mm": { "status": "available", "before": 28, "after": 35, "change": 7 },
      "tmax_p90_c": { "status": "insufficient_data", "before": null, "after": 21.4, "change": null } }
  ],
  "best_windows": {
    "before": [ { "month": 3, "limiting_signal": "frost", "limiting_score": 64, "high_risk": false } ],
    "after": [ { "month": 4, "limiting_signal": "water", "limiting_score": 68, "high_risk": false } ]
  },
  "weights_basis": "default",
  "reasons": ["Entre 1981 y 2000 heló en enero en 30 de cada 100 años; entre 2005 y 2024, en 18"],
  "limitations": ["NASA POWER es un reanálisis, no una observación directa", "La oferta, el mercado y el suelo son los mismos en los dos periodos"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `months` trae los doce meses; el ejemplo muestra uno. `change` es después menos antes. Si un periodo no tiene datos suficientes, el valor de ese periodo y `change` son nulos y `status` es `insufficient_data`.
- `best_windows`: de 0 a 3 meses de siembra por periodo, con el orden de las ventanas y los pesos por defecto; nunca uno de alto riesgo.
- Si `sources.yaml` da la lluvia a GPM IMERG, la respuesta trae también `precip_periods` (los dos periodos de IMERG, desde 2001) y `precip_normal_mm` sale de esos periodos; las heladas y el calor siguen saliendo de los de NASA POWER. Nunca se compara un periodo de una fuente con uno de otra.
- Si el cultivo no es apto para la zona, `best_windows` viene vacío y `suitability` dice por qué; `months` viene igual.

### Cuerpo y respuesta de `POST /api/v1/calendar`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "sowing_date": null, "month": null,
  "priorities": null, "irrigated": false, "lot_id": null }
```

Tiene dos lecturas, según venga o no `sowing_date`. No guarda los datos de la finca ni quién consultó (R9) y trae `versions` y `reference_date` (el día desde el que se cuentan los doce meses), para que el mismo resultado se pueda reproducir (R4).

Fechas: la ventana de un mes empieza el día 1 y la de una semana, su lunes. `month` se refiere a la próxima vez que llega ese mes desde `reference_date`. En `/diagnostics` y en «Planear una siembra» de `/calendar`, una fecha de siembra anterior a hoy o a más de doce meses responde 422; el mes en curso se acepta aunque su día 1 ya haya pasado. En «Mi cultivo» (`/calendar` con `sowing_date`), la fecha puede ser pasada. **«Hoy» y «el mes en curso» se cuentan en la hora de la región**, nunca en UTC ni en la hora del servidor: en la región piloto (Colombia), `America/Bogota`, UTC−5 todo el año (sin horario de verano). La zona sale de `region.timezone` en `pipeline/region.yaml`. Es la de la región y no la de quien consulta, aunque consulte desde otro país: el mes de siembra es el del campo (decidido por Felipe el 11 de noviembre de 2026). La web cuenta los doce meses con la misma hora, así que el mes que ofrece es siempre uno que la API acepta. Vale para `/diagnostics`, `/rotations` y `/calendar` (decidido el 10 de noviembre de 2026).

**Planear una siembra (sin `sowing_date`).** Responde `suitability` y `windows`:

- Sin `month`: doce ventanas, una por cada mes de siembra de los próximos doce meses (`granularity = month`). Con `month` (1 a 12): las semanas de ese mes (`granularity = week`).
- Cada ventana trae `sowing_start`, `harvest_estimate`, `signals` (las mismas del diagnóstico, cada una con `status`, `level`, `critical`, `reasons`, `score` de 0 a 100 —nulo si no califica— y `counts`), `limiting_signal` (la señal que más limita), `limiting_score`, `weighted_score` (promedio ponderado por los pesos), `high_risk` y `rank`. La respuesta trae también `weights` y `weights_basis`.
- `priorities`: un entero de 0 a 5 por señal (`water`, `frost`, `heat`, `soil`, `supply`, `market`), igual que en el diagnóstico. Sin él, se usan los pesos por defecto de `weights.yaml`. Fuera de rango, o todas en 0, responde 422.
- `best_windows`: de 0 a 3 ventanas, las primeras del orden que no son de alto riesgo. Puede venir vacío: no siempre hay un buen mes.
- Si el cultivo no es apto para la zona, `windows` viene vacío y `suitability` dice por qué.

**Mi cultivo (con `sowing_date`).** Sirve para seguir un cultivo ya sembrado. Responde `months`: cada mes entre la siembra y la cosecha estimada, con `month`, `year`, `stage` (la etapa que ocupa la mayor parte del mes), `basis` (`observed` hasta el último dato de temperatura y `normal_year` después, con el mismo cálculo de la línea de tiempo) y estos bloques, con `status`, `level` y `reasons` como las señales (R1):

- `frost`: `frost_freq_pct` del mes, `sensitive` (alguna etapa de ese mes es sensible a la helada) y `watch` (es sensible y el nivel no es `favorable`).
- `heat`: `tmax_p90_c` del mes frente a `heat_max_c` del cultivo, con `sensitive` y `watch` igual que la helada.
- P1: `fertilizing` (días de aguacero), `field_work` (ventanas secas para labores y cosecha), `blight` (días favorables a la gota, solo para cultivos con esa regla) y `selling` (índice estacional de precio del mes; nunca precio futuro).

Más `harvest_estimate` y `harvest_basis`. El cruce entre el riesgo y la etapa lo hace el motor, no la web (R5). La vista del lote combina esta lectura con el plan de agua: el calendario no repite el riego.

`irrigated` se comporta igual que en el diagnóstico; con `lot_id`, el suelo y `irrigated` salen del lote. El diagnóstico de una ventana y el orden de las ventanas salen del mismo cálculo: una ventana del calendario y el diagnóstico de esa fecha dan las mismas señales.

### Cuerpos de cuenta

- `PATCH /api/v1/me`: `priorities` (opcional: un entero de 0 a 5 por señal; nulo vuelve a los de AgroSense; fuera de rango o todas en 0, 422), `display_name` (1 a 40 caracteres) y `username` (3 a 30 caracteres: letras minúsculas sin tilde, números, punto y guion bajo), ambos opcionales. Cambiar el usuario no cierra la sesión. El consentimiento no se edita aquí: para retirarlo se borra la cuenta.
- `POST /api/v1/me/password`: `current_password` y `new_password` (al menos 8 caracteres y distinta de la actual). Responde `204`.
- `POST /api/v1/lots` y `PATCH /api/v1/lots/{lot_id}`: `name`, `municipality_id`, `irrigated` (opcional: si el lote tiene riego) y `geometry` (polígono GeoJSON). Sin `geometry`, `area_ha` (mayor que cero) es obligatoria; con `geometry`, `area_ha` la calcula la API y se ignora la enviada.
- Con `geometry` (desde el 15 de octubre de 2026, entrega 2; aprobado por Felipe): un polígono GeoJSON en WGS84 de un solo anillo, sin huecos, de 3 a 500 puntos, sin cruces y de área mayor que cero; si no, `422` `invalid_geometry`. Debe caer dentro del límite publicado de su municipio, con un margen de unos 10 m por la simplificación del límite; si no, `422` `geometry_outside_municipality`, con el nombre del municipio. El área la calcula la API sobre el elipsoide WGS84 y la enviada se ignora. Sin `geometry` ni `area_ha`, `422`. En un `PATCH`, el dibujo no se quita (`geometry` nulo responde `422`), se corrige; cambiar de municipio un lote dibujado vuelve a validar su contorno en el nuevo. La API guarda el contorno en sentido antihorario y con 7 decimales (R4).
- Respuesta de `GET /api/v1/lots/{lot_id}`: el lote, `soil` (las propiedades de suelo de `grid_cells` como mediana del polígono, con `basis`: `lot` o `municipality`, y `cells`; nulo mientras no esté publicado el suelo, HU-181), `terrain` (`altitude_m`, `slope_pct`, `basis` y `cells`, de `grid_cells`; nulo mientras no esté publicada la rejilla, HU-206) y `current_seasons` (lista, vacía si no hay temporadas en curso; de mayor a menor área) con `season_id`, `crop_id`, `area_ha`, `follows_season_ids`, `sowing_date`, `days_since_sowing`, `stage`, `stage_progress_pct`, `stage_method` (`thermal_time` si se usó la temperatura acumulada del municipio, `calendar` si se usó la duración por días porque faltan datos de temperatura o grados-día con fuente), `thermal_data_until` (fecha del último dato de temperatura usado; nula con `calendar`), `harvest_estimate` con su `harvest_basis` y `harvest_due` (ya pasó la cosecha estimada y no se ha registrado: la etapa se queda en la última, al 100 %) y `versions`. En el MVP la etapa sale del calendario (HU-220): `stage_method = calendar` y `harvest_basis = calendar`. Un cultivo sin etapas (el descanso) trae `stage`, `stage_progress_pct` y `harvest_estimate` nulos. `harvest_estimate`, `harvest_basis` y `harvest_due`: aprobado por Felipe el 8 de noviembre de 2026. Es una estimación con el clima del municipio, no una observación del lote (HU-150).
- Respuesta de `GET /api/v1/seasons/{season_id}/growth`: `points` (uno por semana, de la siembra a la cosecha estimada) con `date`, `stage`, `stage_progress_pct`, `gdd_accumulated` y `basis`: `observed` mientras hay temperatura real (`climate_day`, hasta `thermal_data_until`) y `normal_year` después (`climate_normal_doy`). Más `today`, `harvest_estimate` (fecha, siempre con `harvest_basis`) y `versions`. Lo `normal_year` es una estimación con un año normal, **no un pronóstico**: la web lo rotula así. Sin temperatura con fuente o sin grados-día del cultivo, se usa la duración por calendario y se dice (R1). No guarda nada.
- `POST /api/v1/lots/{lot_id}/seasons`: `crop_id`, `sowing_date`, `area_ha` (opcional: sin ella ocupa lo que queda libre del lote), `follows_season_ids` (opcional: qué había antes en ese terreno) y el diagnóstico que vio el usuario al sembrar (`diagnosis_light`, `diagnosis_light_default`, `diagnosis_action`, `diagnosis_weights`, `diagnosis_irrigated`, `dataset_version`, `rules_version`), que la web toma de la respuesta de `/diagnostics`. Si no consultó el diagnóstico, esos campos van nulos.
- `PATCH /api/v1/seasons/{season_id}`: `harvest_date` o correcciones de `crop_id`, `sowing_date`, `area_ha` y `follows_season_ids`, con las mismas validaciones. Las dos rutas responden la temporada con su etapa de hoy (los mismos campos de `current_seasons`); `GET /api/v1/lots/{lot_id}/seasons` también, con la etapa nula en las cosechadas. Los dos GET (`/lots/{lot_id}` y `/lots/{lot_id}/seasons`) solo leen y calculan la etapa con la misma función: sin dataset publicado responden igual, con la etapa nula (R1), en vez de `503` (9 de noviembre de 2026, aprobado por Felipe).
- Validaciones de las temporadas (422): el cultivo está en el catálogo; `sowing_date` no es posterior a hoy; `harvest_date` va entre `sowing_date` y hoy; una cosecha no se deshace ni se mueve a después de la siembra de una temporada que viene de ella; `follows_season_ids` sin repetidas. El área de una temporada en curso no pasa de lo libre del lote (el área menos las demás temporadas en curso; el terreno de una cosechada ya está libre): `area_exceeds_free`, «No cabe: en el lote quedan X ha libres.». aprobado por Felipe el 8 de noviembre de 2026.
- Respuesta de `GET /api/v1/lots/{lot_id}/progress`: `seasons_count`, `valid_rotations_count`, `rotations` (una por cada relación entre una temporada y una de sus sucesoras, con `from_season_id`, `to_season_id`, `valid` y `violated_rule_ids`, la lista de reglas de `rotation_rules` que viola; vacía si cumple) y `milestones` (cada uno con `milestone_id`, `achieved_at` y `basis`: la regla de `rotation_rules` o el hecho registrado que lo produce), más `versions`.

### Respuesta de diagnóstico

```json
{
  "request": {
    "municipality_id": "MUNICIPIO_ID",
    "crop_id": "papa",
    "sowing_date": "2026-08-03",
    "irrigated": false,
    "lot_id": null
  },
  "suitability": {
    "level": "suitable",
    "score": 92,
    "basis": "municipality",
    "tmean_annual_c": 12.8,
    "altitude_m": 2660,
    "reasons": ["La temperatura media anual del municipio (12,8 °C, corregida a 2.660 m) está dentro del rango de la papa (8 a 16 °C)"]
  },
  "window": {
    "sowing_start": "2026-08-03",
    "harvest_estimate": "2026-12-28",
    "harvest_basis": "calendar",
    "supply_semester": { "year": 2025, "semester": "B", "preliminary": true }
  },
  "overall": {
    "light": "green",
    "action": "sow",
    "high_risk": false,
    "weights_basis": "farmer",
    "limiting_signal": "frost",
    "reasons": ["Con sus prioridades, la oferta no cuenta para la luz y ninguna otra señal es desfavorable"]
  },
  "overall_default": {
    "light": "yellow",
    "action": "rotate",
    "high_risk": false,
    "weights_basis": "default",
    "limiting_signal": "supply",
    "reasons": ["Con el criterio de AgroSense, la oferta desfavorable pone la luz en amarillo"]
  },
  "weights": { "water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3 },
  "signals": {
    "water": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 86,
      "counts": true,
      "indicators": ["water_deficit_mm"],
      "reasons": ["En 7 de los últimos 10 años, la lluvia de agosto a diciembre cubrió lo que necesita la papa"]
    },
    "frost": {
      "status": "available",
      "level": "moderate",
      "critical": false,
      "score": 58,
      "counts": true,
      "indicators": ["frost_freq_pct"],
      "reasons": ["Sembrando en agosto, heló en el llenado (diciembre) 12 de cada 100 años"]
    },
    "heat": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 94,
      "counts": true,
      "indicators": ["tmax_p90_c"],
      "reasons": ["De agosto a diciembre, la máxima rara vez pasa de 22 °C; la papa aguanta hasta 28 °C"]
    },
    "soil": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 80,
      "counts": true,
      "indicators": ["ph"],
      "reasons": ["pH estimado de 5,2 a 5,8, dentro del rango de la papa. Estimación de 250 m: confírmelo con un análisis de suelo"]
    },
    "supply": {
      "status": "available",
      "level": "unfavorable",
      "critical": false,
      "score": 30,
      "counts": false,
      "indicators": ["planted_change_pct"],
      "sources": [
        { "source_id": "eva", "indicator": "planted_change_pct", "value": 35, "unit": "%", "period": "2025-B", "preliminary": true, "used": true }
      ],
      "reasons": ["En 2025 B (último dato, preliminar) se sembró 35 % más papa que en los tres semestres B anteriores"]
    },
    "market": {
      "status": "insufficient_data",
      "level": null,
      "critical": false,
      "score": null,
      "counts": true,
      "indicators": [],
      "reasons": ["Sin datos de mercado para la zona"]
    }
  },
  "alternatives": [
    { "crop_id": "haba", "reasons": ["Sale bien en clima en esta ventana", "En 2025 B se sembró menos haba que en los tres semestres B anteriores"] }
  ],
  "limitations": ["Datos EVA del último año son preliminares", "Suelo estimado para el municipio, no para su lote"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `overall` usa los pesos de quien consulta y `overall_default` los de AgroSense; la web muestra las dos luces cuando difieren. `counts` dice si la señal cuenta para la luz con los pesos de quien consulta, `score` es su calificación de 0 a 100 y cada luz trae su `limiting_signal`, la señal que más limita con esos pesos.
- `sources` aparece en una señal cuando hay más de una fuente: todas se muestran para contrastar y `used` dice cuál calculó la señal. En `water` trae la lluvia de GPM IMERG y la de NASA POWER (una con `used = true`) y, con `used = false`, la humedad del suelo de la zona: `soil_wetness_root` de POWER y, si existe, `sm_rootzone_m3_m3` de SMAP, cada una en su unidad. El ejemplo no lo muestra.
- `suitability` trae `basis` (`lot` o `municipality`), `tmean_annual_c` y `altitude_m`: la temperatura media anual que se usó y la altitud a la que se corrigió. Con `lot_id`, es la del lote (`grid_cells`) y la razón lo dice.
- En P1 (HU-200), `supply.sources` suma las siembras registradas en AgroSense (`source_id = agrosense`, `used = false`, solo con 5 cuentas o más). En el MVP no viene.
- `alternatives` es P1 (HU-197): en el MVP no viene. Cuando exista, viene cuando la acción, con alguno de los dos juegos de pesos, es `rotate`: hasta tres cultivos aptos para la zona que en esta ventana salen bien en clima y tienen mejor oferta. Nunca uno no apto ni uno que sale mal en clima. Se ordenan igual que las ventanas (factor limitante y después prioridades). Un candidato con aptitud `insufficient_data` puede aparecer, con esa limitación. También vienen cuando el cultivo consultado no es apto.
- `best_windows` viene cuando la acción de `overall` o de `overall_default` es `other_window`: hasta tres ventanas de los próximos doce meses, sin las de alto riesgo, cada una con `sowing_start`, `harvest_estimate`, `limiting_signal`, `limiting_score`, `weighted_score` y `high_risk`. Puede venir vacío. En el ejemplo no viene, porque sus acciones son `sow` y `rotate`.
- `harvest_estimate` es siempre una fecha y su base va al lado, en `harvest_basis`: `calendar` cuando sale de la duración de la ficha (el MVP, HU-220) y `normal_year` cuando sale del clima de un año normal (P1, HU-150 y HU-186). Así en `window`, en los ciclos de `/rotations` y, en P1, en «Mi cultivo» de `/calendar` y en `/growth`.
- `suitability.score` es una nota informativa de 0 a 100 de la aptitud (la curva de temperatura media anual de la ficha: 100 dentro del rango óptimo, 0 fuera del absoluto); la web la muestra con su nota y en la escala de cinco semillas. No es una señal: no entra al semáforo ni al orden. La aptitud se decide solo por la temperatura media anual: solo fuera del rango absoluto es `not_suitable`. Si el cultivo no es apto para la zona, `suitability.level` es `not_suitable`, `window` y `signals` vienen nulos, la luz es `red` y la acción `rotate`.
- Las señales del P1 (`excess_rain`, `disease`, `harvest_weather`) aparecen solo cuando existen.

## Valores permitidos y semáforo

Ver `specs/01-reglas.md` (valores permitidos y agregación del semáforo).
