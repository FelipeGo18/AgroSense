---
id: EP-18
titulo: "Suelo de la zona y del lote en las decisiones"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Datos y Motor y API, con Web y Producto y agro"
agentes: [datos, motor-api, web, producto-agro]
subsistemas: [D1, D3, D4, M1, M3, W2, W4, W7]
depende_de: [HU-011, HU-062, HU-063]
reglas: [R1, R2, R3, R5, R6, R7, R8, R9, R10]
estado: en curso
---

# EP-18 · Suelo de la zona y del lote en las decisiones

**Resultado esperado:** El diagnóstico, el balance de agua y las estrategias de rotación usan el suelo estimado de la zona o del lote dibujado (el pH en la señal de suelo, la textura en cuánta agua retiene y el carbono orgánico en la salud del suelo), cada estrategia dice cómo cuida el suelo con cinco criterios por reglas con fuente (HU-212), y el agricultor ve su suelo con su rango y el aviso de que es una estimación.

El reto («Field Shift») pide usar información local del suelo y rotaciones que mejoren la salud del suelo. Se decidió el 10 de octubre de 2026 (`docs/investigacion-decisiones.md`). La descarga y publicación (HU-181) se puede adelantar en la fase 0 si HU-004 lo permite.

## Historias de usuario

### HU-181 · Suelo de la región publicado

- **Historia:** Como motor, quiero el suelo de la región en tablas publicadas, para evaluarlo sin consultar servicios externos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Adaptador de SoilGrids (ISRIC, CC BY 4.0) con caché: pH, carbono orgánico, nitrógeno, arcilla, arena y limo de 0 a 30 cm, con el intervalo del 90 % del pH y del carbono orgánico
  - [x] El suelo en `grid_cells` (la rejilla común de 250 m, decisión 15) y `soil_municipality` (mediana por municipio, con `cells` y `quality`) según el contrato
  - [x] Entrada en `sources` con licencia y versión de SoilGrids
  - [x] Comprobación manual en 2 municipios contra un estudio de suelos del IGAC, si lo hay (IGAC es de la región piloto supuesta en Colombia; con otra región, el estudio oficial que corresponda)
- **Reglas que aplican:** R7, R8
- **Notas:** La textura (`clay_pct`, `sand_pct`, `silt_pct`, `texture_class`) también la usa el balance de agua (HU-144). **14 de noviembre de 2026 (hecho):** `pipeline/sources/soilgrids.py` baja SoilGrids 2.0 por WCS (`maps.isric.org`, sin cuenta) en mosaicos de 1° y ya en la rejilla común de 0,0025°: el servidor lleva su proyección a la rejilla con vecino más cercano, así que cada celda tiene el valor del píxel que contiene su centro, como pide el contrato. Son 30 mapas por mosaico (6 propiedades por 3 capas, más los percentiles 5 y 95 del pH y del carbono orgánico) y 13 mosaicos: 390 mapas, 57 MB en `data/raw/soilgrids/`. El servidor de ISRIC estuvo lento e inestable: la descarga va de a 2 mapas, con 5 intentos, y retoma lo que ya bajó. De 0 a 30 cm: el promedio de las capas 0-5, 5-15 y 15-30 cm ponderado por su grosor; los percentiles se promedian igual, capa por capa (una aproximación, porque los percentiles no se suman). Un píxel en 0 es «sin dato» y queda nulo (R1). La textura sale del triángulo del USDA, con los nombres en español del IGAC (fuente `usda_textura`). Dataset `2026.11.12`: suelo en 587 313 de las 593 648 celdas de `grid_cells` (6335 sin dato, agua o zona urbana) y `soil_municipality` con los 239 municipios (232 `ok` y 7 `partial`, con menos del 90 % de sus celdas con suelo). **Comprobación** frente al estudio geoquímico de suelos de la cuenca del río Bogotá del INGEOMINAS (Prieto, González, Vargas y Matamoros, Boletín Geológico n.º 41), porque no se encontró en línea un estudio del IGAC con cifras por municipio. En la Sabana (cuenca alta: Mosquera, Funza, Madrid, Cota, Tenjo y otros), el INGEOMINAS da suelos ácidos de pH 4 a 6,5, y SoilGrids da de 5,6 a 5,8: **coincide**. En la cuenca baja (Girardot, Tocaima, Ricaurte, Nilo y otros), el INGEOMINAS da pH de 6,6 a 9 y textura sobre todo franco arcillosa; SoilGrids acierta la textura (franco arcilloso) pero da pH de 5,2 a 5,4: **los suelos básicos de la cuenca baja salen ácidos**. Además, SoilGrids es muy parejo en la región: 230 de los 239 municipios salen «franco arcilloso». Es un modelo de 250 m y suaviza: se dice siempre (R10) y queda en `docs/riesgos.md`. **En Boyacá**, frente a las 301 muestras del distrito de riego del Alto Chicamocha (Walteros Torres, Cely Reyes y Moreno Pérez, 2018, Revista Facultad Nacional de Agronomía Medellín 71(3), doi 10.15446/rfnam.v71n3.72375), que cubre Duitama, Paipa, Tibasosa, Santa Rosa de Viterbo, Nobsa y Sogamoso: el estudio da un pH medio de 5,52, casi todo moderadamente ácido (de 5 a 6), y SoilGrids da de 5,65 a 5,95 en esos municipios: **coincide**. **Revisión del PR #76 (Haider, 14 de noviembre de 2026):** `grid_cells` se valida con las mismas comprobaciones de `soil_municipality` en las celdas con suelo (el suelo del lote, HU-182, las lee); la celda con clase de textura cita `usda_textura` (R8); y si ISRIC está caído, `--descargar` avisa (`source_skipped`) y sigue con las demás fuentes. El `ok` con el 90 % de las celdas quedó aprobado por Haider.

### HU-182 · Suelo de un lote

- **Historia:** Como agricultor, quiero ver el suelo estimado de mi lote, para entender qué le conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La API calcula el suelo del lote como la mediana de las celdas de `grid_cells` de su polígono (ver «La rejilla de 250 m» en el contrato); sin polígono, usa `soil_municipality`, y lo dice en `basis`
  - [ ] `soil` en la respuesta de `GET /lots/{lot_id}`
  - [ ] El suelo del lote no se guarda en la base de datos
  - [ ] `lot_id` opcional en `/diagnostics` y `/rotations` (y en `/calendar`, P1): usan el suelo del lote; sin sesión responde 401 y un lote ajeno, 404. `/water-plans` no recibe `lot_id` y usa siempre el suelo del municipio, también con cuenta
  - [ ] Con el mismo método, la API calcula la altitud y la pendiente del lote (`terrain`, de `grid_cells`, HU-206), sin guardarlas (R9). El verdor del lote es P1 (HU-209)
- **Reglas que aplican:** R6, R9, R10
- **Notas:** Depende de HU-164 (polígono del lote) y HU-181. Si se recorta, queda el suelo del municipio (HU-183).

### HU-183 · Señal de suelo en el diagnóstico

- **Historia:** Como agricultor, quiero saber si el suelo de mi zona o de mi lote le sirve al cultivo, para no sembrar donde no va a darse.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `score` con la curva de HU-196: 100 con el pH en el rango óptimo (`ph_opt_min`–`ph_opt_max`), 0 fuera del tolerado (`ph_min`–`ph_max`) y una recta entre ambos; el nivel sale de la calificación
  - [ ] Se mantiene la lectura con el intervalo `ph_p05`–`ph_p95`: si todo el intervalo queda fuera del tolerado, el nivel es `unfavorable`; si el intervalo cruza un límite, el nivel no pasa de `moderate`
  - [ ] Nunca crítica (R10): solo puede llevar a rojo junto con otra señal desfavorable
  - [ ] Sin suelo, o con un cultivo sin rango de pH con fuente: `insufficient_data` y a las limitaciones
  - [ ] La razón recomienda un análisis de suelo del lote
  - [ ] Con HU-078, `GET /catalogs/municipalities/{municipality_id}/soil` muestra el suelo del municipio sin cuenta
- **Reglas que aplican:** R1, R2, R5, R10
- **Notas:** Depende de HU-181, HU-063 y HU-196; la usa HU-074 (antes decía que dependía de HU-074, lo que hacía un ciclo). Va con el diagnóstico, en la etapa 1. El suelo no cambia con la fecha: la señal es la misma en todas las ventanas de un cultivo, y por eso con suelo desfavorable la acción es `rotate` y no `other_window`. En el orden de ventanas (HU-192) califica igual en todas, pero puede ser el factor limitante. La textura no entra en esta señal: entra en el balance de agua (HU-144, decisión 10). Supuesto por confirmar: qué valor del pH entra a la curva (la mediana) y cómo se combina con el intervalo, como dice el segundo criterio.

### HU-184 · Suelo en las estrategias de rotación

- **Historia:** Como agricultor, quiero que las estrategias tengan en cuenta mi suelo, para no recibir una que mi suelo no aguanta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un cultivo cuyo rango de pH tolerado queda fuera de **todo** el intervalo `ph_p05`–`ph_p95` excluye la estrategia, con la regla y el ciclo citados (R3)
  - [ ] El carbono orgánico (`soc_g_kg`) del lote o del municipio llega al criterio `organic_carbon` de la salud del suelo (HU-212)
  - [ ] La respuesta dice qué suelo se usó (`lot` o `municipality`) y lleva el rótulo de estimación (R10)
  - [ ] Las razones citan la propiedad del suelo y la regla
- **Reglas que aplican:** R3, R5, R8, R10
- **Contrato que toca:** `POST /api/v1/rotations`; `grid_cells`, `soil_municipality`
- **Notas:** Depende de HU-081 y HU-181; con HU-182, usa el suelo del lote. El 11 de octubre de 2026 la bonificación por carbono orgánico pasó al criterio `organic_carbon` de HU-212 (decisión 12).

### HU-212 · Salud del suelo de cada estrategia

- **Historia:** Como agricultor, quiero ver cómo cuida mi suelo cada estrategia (nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión), para elegir una rotación que lo proteja.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] **Interfaz.** Función pura `backend/engine/rotations/soil_health.py` (R6: sin FastAPI, sin SQLAlchemy, sin Polars, sin abrir archivos). Recibe valores ya leídos:
    - `cycles`: la secuencia de ciclos, en orden, cada uno con `crop_id`, `days` (la duración en días del ciclo, o nula si no la hay) y `gap_days` (los días entre su cosecha estimada y la siembra del ciclo siguiente, de 0 a 6; nulo en el último);
    - `crops`: la ficha de cada `crop_id` usado, con `kind`, `family`, `secondary_families` y `fixes_nitrogen`;
    - `previous_crop_ids`: los cultivos anteriores del terreno, del más reciente al más antiguo (ver «Cultivos anteriores»);
    - `rules`: las reglas `kind = health` de `rotation_rules`, con `rule_id`, `criterion`, `condition_type`, `params`, `levels`, `reason_template` y `source_id`;
    - `soil`: `soc_g_kg`, `soc_p05`, `soc_p95` y `source_id`, o nulo;
    - `slope`: `slope_pct` y `source_id`, o nulo.
  - [x] **Salida.** Los cinco criterios `nitrogen`, `organic_carbon`, `soil_cover`, `pest_break` y `erosion` (HU-224), cada uno con la forma del contrato: `status`, `level` (`favorable`, `moderate`, `unfavorable` o nulo), `reasons`, `rule_ids` y `source_ids` (la fuente de la regla y la de los datos que usó: `soilgrids` en `organic_carbon`, la de la pendiente en `erosion`). Mismos datos, mismas reglas y misma entrada dan la misma salida (R4)
  - [x] **Nivel por cortes.** Todos salvo `erosion` comparan un valor con `levels`: `favorable` si el valor llega al corte `favorable`; si no, `moderate` si llega al corte `moderate`; si no, `unfavorable`. Con `moderate == favorable` no hay franja intermedia (contrato). `erosion` usa cortes máximos (HU-224)
  - [x] **Sin regla o sin dato.** Un criterio sin regla `health` con fuente en `rules` queda `status = insufficient_data`, `level` nulo, `rule_ids` y `source_ids` vacíos, y una razón que dice qué falta: no se inventa un corte (R1, R8). Un criterio con regla pero sin su dato queda igual, con `rule_ids` y `source_ids` de la regla. La función no arma las limitaciones: las arma HU-082 a partir de los criterios `insufficient_data`
  - [x] **`nitrogen`.** Cuenta los ciclos con `fixes_nitrogen = true`, con los cortes de `legume_cycles`. Incluye `avena_vicia`, por la vicia, según el catálogo. Si el conteo no llega a `favorable` y algún ciclo tiene `fixes_nitrogen` nulo, `insufficient_data` (R1)
  - [x] **`organic_carbon`.** Cuenta los ciclos con `kind = cover` (abono verde) o `kind = fallow` (descanso). **Los residuos de cultivo no cuentan** (HU-062, nota 3: no hay campo en la ficha ni en la condición). Compara `soc_g_kg` (el valor central) con `params.soc_low_g_kg`: menor es `low`, si no `normal`, y usa los cortes de ese grupo. Con carbono bajo, una estrategia sin abono verde ni descanso no es `favorable`. La razón da el rango `soc_p05` a `soc_p95` en `{soc_range}` y dice que es una estimación de 250 m (R10). Sin `soc_g_kg`, `insufficient_data` (R1)
  - [x] **`soil_cover`.** Un ciclo con `kind` de cultivo o de abono verde cubre el suelo durante sus `days`. Un descanso cuenta como suelo descubierto (decisión 16). `pct` es los días cubiertos entre los días totales de la estrategia (suma de `days` y de `gap_days`), por 100, y se compara sin redondear con `covered_months_pct`. Los meses para la razón son días / 30,4. Si algún ciclo no tiene `days`, `insufficient_data` (R1; hoy el descanso, que no tiene etapas hasta HU-063). El NDVI (HU-208, HU-209) no existe todavía: la razón no lo muestra y eso no es una limitación. Cuando exista, solo se suma a la razón, como contraste
  - [x] **`pest_break`.** Cuenta los ciclos de otras familias entre dos apariciones de la `family` de la regla; cada ciclo aporta su `family` y sus `secondary_families` (contrato). El descanso cuenta como un ciclo sin esa familia (supuesto de HU-062, nota 3). El nivel es el de la peor vuelta de la familia en la secuencia `previous_crop_ids` (invertida) más los ciclos de la estrategia. Sin vuelta de la familia, `favorable`. La razón de una vuelta llena `{family}` y `{cycles}`
  - [x] **Cultivos anteriores.** `previous_crop_ids` solo lo usa `pest_break`: de ellos, la función mira hasta `params.min_cycles + 1` cultivos hacia atrás (así una vuelta justo en el corte favorable se cuenta con sus ciclos; más lejos, la familia «no vuelve» y es `favorable` igual). Lo arma quien llama (HU-081, HU-213): en una estrategia sugerida, los `previous_crop_ids` del cuerpo (con cuenta, los de las temporadas de `follows_season_ids`), invertidos; en la de referencia (`kind = current`), sus propios cultivos repetidos hacia atrás. Aprobado por Felipe el 14 de noviembre de 2026 (PR #109): en una estrategia sugerida, solo los `previous_crop_ids`; en la rotación actual, sus propios cultivos repetidos hacia atrás. Prueba: papa → avena → arveja (`papa_espera`, `favorable: 3` y `moderate: 2`) sin anteriores no sale `unfavorable`; con `previous_crop_ids = [papa]` seguida de 3 ciclos de otros cultivos, sale `favorable`; la rotación de referencia papa, avena, arveja repetida hacia atrás da una vuelta de 2 ciclos y sale `moderate`
  - [x] **Hueco entre ciclos.** Los `gap_days` cuentan como suelo descubierto en `soil_cover` y en `erosion` (el comentario de `erosion_pendiente` lo supone: «el paso entre cosecha y siembra»). Supuesto por confirmar
  - [x] **«Criterio del equipo».** La razón de todo criterio cuya regla tenga `source_id = criterio_equipo_2026` termina con «criterio del equipo, pendiente de validar por un agrónomo» (R8, decisión 16, 11 nov 2026). Hoy son las cinco reglas `health`. Prueba: una estrategia con `nitrogen` evaluado por `leguminosa_en_rotacion` trae la frase en su razón
  - [x] **Puntaje `soil` para HU-082.** La función entrega también el puntaje del criterio `soil` del ranking: `favorable` vale 100, `moderate` 50 y `unfavorable` 0, y el puntaje es el promedio entre los criterios con `level` (los `insufficient_data` no entran). Sin ninguno, nulo. HU-082 lo usa sin recalcularlo (`specs/01-reglas.md`, «Estrategias de rotación»)
  - [x] Ninguna razón dice cuánto va a mejorar el suelo, cuánto nitrógeno o carbono queda ni cuánto se va a cosechar: compara estrategias según reglas (decisión 4, R5). Las razones solo llenan los marcadores de su `reason_template`
  - [x] Prueba: dos estrategias iguales salvo una leguminosa dan `nitrogen` mejor a la que la tiene; con carbono bajo, la que tiene abono verde da `organic_carbon` mejor
  - [x] Prueba (R1): sin suelo, `organic_carbon` es `insufficient_data` con `level` nulo; sin duración en algún ciclo, `soil_cover` también
  - [x] Prueba (R6): `backend/engine/` no importa `fastapi`, `sqlalchemy` ni `polars`
- **Reglas que aplican:** R1, R3, R4, R5, R6, R8, R10
- **Contrato que toca:** `strategies[].soil_health` de `POST /api/v1/rotations`; `rotation_rules`; `grid_cells`, `soil_municipality`, `ndvi_grid`, `ndvi_municipality_normal`
- **Notas:** Decisión 12. No hay modelo de suelo: es una comparación entre estrategias según reglas con fuente, no una predicción. Depende de HU-062, HU-063, HU-181 y HU-213. Supuesto por confirmar: cómo entra el NDVI al nivel de `soil_cover` (hoy solo en la razón, como contraste). Agregada el 11 de octubre de 2026. **Precisada el 14 de noviembre de 2026 (antes del código):** la interfaz, los datos de cada criterio y los pasos de días a meses quedaron en los criterios. Corrige «o con residuos» en `organic_carbon` (HU-062, nota 3) y cambia `previous_crop_ids` por la versión única de «Cultivos anteriores». Los datos ya existen en el dataset 2026.11.18: `soil_municipality` (`soc_g_kg`, `soc_p05`, `soc_p95`, `source_id = soilgrids`), `municipalities.slope_pct` y la duración de los 7 cultivos en `crop_stages`. Falta la del descanso (HU-063, Luisa, en curso): hasta entonces, un ciclo de descanso deja `soil_cover` y `erosion` (con pendiente de `slope_pct_from` o más) en `insufficient_data`, que es lo correcto (R1). **PR previstos:** A, esta spec; B, `nitrogen`, `pest_break` y la forma de los cinco criterios; C, `organic_carbon` y `soil_cover`; D, `erosion` (HU-224) y el puntaje `soil`. **Supuestos aprobados por Felipe el 14 de noviembre de 2026 (PR #109):** (1) en una estrategia sugerida, los cultivos anteriores de `pest_break` son solo los `previous_crop_ids` (lo que hubo en el terreno; `current_crop_ids` describe la estrategia de referencia); en la rotación actual, sus propios cultivos repetidos hacia atrás; (2) el hueco de 0 a 6 días entre ciclos cuenta como suelo descubierto; (3) un mes son 30,4 días y el nivel se decide sin redondear, la razón muestra un decimal; (4) en `pest_break`, si la familia no vuelve, el nivel es `favorable`; (5) en `nitrogen`, un `fixes_nitrogen` nulo sin conteo suficiente da `insufficient_data` (R1). A tener en cuenta (HU-062, nota 5, 9 nov 2026): `papa_espera` cita `criterio_equipo_2026` y, desde el 11 nov 2026 (Felipe, revisión del PR #46), pide `min_cycles: 3` con `levels {favorable: 3, moderate: 2}`: 3 o más ciclos de otros cultivos son `favorable`, 2 son `moderate` y 0 o 1 son `unfavorable`; el corte de plagas cuenta también los cultivos anteriores del terreno (`current_crop_ids`; con cuenta, el historial de HU-165), para que una estrategia de 3 ciclos pueda llegar a `favorable`.

### HU-224 · Erosión en la salud del suelo

- **Historia:** Como agricultor, quiero saber si una estrategia deja mi suelo descubierto en un terreno con pendiente, para no perder suelo con la lluvia.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Criterio `erosion` de `soil_health`, con `status`, `level`, `reasons`, `rule_ids` y `source_ids`, como los otros cuatro (HU-212)
  - [x] Sale de la pendiente (`slope_pct`) del lote o del municipio (HU-206) y de los meses descubiertos, los mismos de `soil_cover` (descanso y hueco entre ciclos, en días / 30,4), con los cortes de `erosion_pendiente` (`bare_months_on_slope`, HU-062)
  - [x] Con `slope_pct >= slope_pct_from` (12 hoy), el nivel sale de los meses descubiertos con cortes máximos: `favorable` hasta el corte `favorable`, `moderate` hasta el `moderate`, `unfavorable` por encima. Con pendiente menor, `favorable` (contrato), sin necesitar la duración de los ciclos
  - [x] La razón dice la pendiente, de dónde sale (lote o municipio, NASADEM a 30 m) y, si la pendiente cuenta, cuántos meses queda descubierto el suelo; la pendiente es del terreno de la zona, no una medición del lote (R10). Termina con «criterio del equipo» (HU-212)
  - [x] Sin pendiente o sin regla con fuente, `insufficient_data`: no se inventa un corte (R1, R8). Con pendiente de `slope_pct_from` o más y algún ciclo sin duración, también
  - [x] El criterio entra al puntaje `soil` de HU-212 como los otros cuatro
  - [x] Ninguna razón dice cuánto suelo se va a perder: compara estrategias según reglas (decisión 4)
  - [x] Prueba: en un terreno con pendiente, una estrategia con abono verde en los meses de lluvia da `erosion` mejor que una con descanso desnudo
  - [x] Prueba (límite): `slope_pct` igual a `slope_pct_from` cuenta; un punto menos da `favorable`
- **Reglas que aplican:** R1, R5, R6, R8, R10
- **Contrato que toca:** `strategies[].soil_health.erosion` de `POST /api/v1/rotations`; `municipalities.slope_pct`; `grid_cells`; `rotation_rules`
- **Notas:** Decisión 14: el enunciado completo nombra la erosión entre las prioridades del agricultor. Depende de HU-206 (pendiente), HU-062 (la regla con fuente; candidatas: el factor de cobertura C de la ecuación universal de pérdida de suelo y las guías de conservación de suelos de la FAO) y HU-212. Agregada el 8 de noviembre de 2026.

### HU-185 · Ver el suelo en la web

- **Historia:** Como agricultor, quiero ver mi suelo explicado en palabras sencillas, para entender por qué la app me recomienda algo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] pH, carbono orgánico y textura con su rango y una frase sencilla de qué significan; la de la textura dice que cambia cuánta agua guarda el suelo y que por eso entra en la señal de agua
  - [ ] Rótulo: «Estimación de un mapa global de 250 m. Un análisis de suelo de su lote es más preciso» (R10)
  - [ ] En el detalle del lote (HU-169), en el detalle de la señal de suelo y en la salud del suelo de las estrategias (HU-102)
- **Reglas que aplican:** R5, R10
- **Notas:** El lote vivo («Lote · ahora», HU-187) pasó a P1 el 11 de octubre de 2026; en el MVP el suelo se ve en el detalle 2D del lote.
