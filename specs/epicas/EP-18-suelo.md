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
estado: pendiente
---

# EP-18 · Suelo de la zona y del lote en las decisiones

**Resultado esperado:** El diagnóstico, el balance de agua y las estrategias de rotación usan el suelo estimado de la zona o del lote dibujado (el pH en la señal de suelo, la textura en cuánta agua retiene y el carbono orgánico en la salud del suelo), cada estrategia dice cómo cuida el suelo con cuatro criterios por reglas con fuente (HU-212), y el agricultor ve su suelo con su rango y el aviso de que es una estimación.

El reto («Field Shift») pide usar información local del suelo y rotaciones que mejoren la salud del suelo. Se decidió el 10 de octubre de 2026 (`docs/investigacion-decisiones.md`). La descarga y publicación (HU-181) se puede adelantar en la fase 0 si HU-004 lo permite.

## Historias de usuario

### HU-181 · Suelo de la región publicado

- **Historia:** Como motor, quiero el suelo de la región en tablas publicadas, para evaluarlo sin consultar servicios externos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador de SoilGrids (ISRIC, CC BY 4.0) con caché: pH, carbono orgánico, nitrógeno, arcilla, arena y limo de 0 a 30 cm, con el intervalo del 90 % del pH
  - [ ] `soil_grid` (celdas de 250 m de la región) y `soil_municipality` (mediana por municipio, con `cells` y `quality`) según el contrato
  - [ ] Entrada en `sources` con licencia y versión de SoilGrids
  - [ ] Comprobación manual en 2 municipios contra un estudio de suelos del IGAC, si lo hay (IGAC es de la región piloto supuesta en Colombia; con otra región, el estudio oficial que corresponda)
- **Reglas que aplican:** R7, R8
- **Notas:** La textura (`clay_pct`, `sand_pct`, `silt_pct`, `texture_class`) también la usa el balance de agua (HU-144).

### HU-182 · Suelo de un lote

- **Historia:** Como agricultor, quiero ver el suelo estimado de mi lote, para entender qué le conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La API calcula el suelo del lote como mediana de las celdas de `soil_grid` que toca el polígono; sin polígono, usa `soil_municipality`, y lo dice en `basis`
  - [ ] `soil` en la respuesta de `GET /lots/{lot_id}`
  - [ ] El suelo del lote no se guarda en la base de datos
  - [ ] `lot_id` opcional en `/diagnostics` y `/rotations` (y en `/calendar`, P1): usan el suelo del lote; sin sesión responde 401 y un lote ajeno, 404. `/water-plans` no recibe `lot_id` y usa siempre el suelo del municipio, también con cuenta
  - [ ] Con el mismo método (mediana de las celdas que toca el polígono), la API calcula la altitud del lote (`elevation_grid`, HU-206) y su verdor (`ndvi_grid`, HU-209), sin guardarlos (R9)
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
- **Contrato que toca:** `POST /api/v1/rotations`; `soil_grid`, `soil_municipality`
- **Notas:** Depende de HU-081 y HU-181; con HU-182, usa el suelo del lote. El 11 de octubre de 2026 la bonificación por carbono orgánico pasó al criterio `organic_carbon` de HU-212 (decisión 12).

### HU-212 · Salud del suelo de cada estrategia

- **Historia:** Como agricultor, quiero ver cómo cuida mi suelo cada estrategia (nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión), para elegir una rotación que lo proteja.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cada estrategia trae `soil_health` con cinco criterios: `nitrogen`, `organic_carbon`, `soil_cover`, `pest_break` y `erosion` (HU-224). Cada uno con `status`, `level` (`favorable`, `moderate`, `unfavorable` o nulo), `reasons` y `rule_ids`: las reglas de `rotation_rules` que lo deciden, cada una con fuente (R8)
  - [ ] `nitrogen`: según los ciclos de leguminosa (`fixes_nitrogen`) o de abono verde con leguminosa, con los cortes de su regla
  - [ ] `organic_carbon`: según los ciclos de abono verde, descanso o con residuos, y el carbono orgánico (`soc_g_kg`) del suelo; con carbono bajo (umbral con fuente), una estrategia sin abono verde ni descanso no es `favorable`. Sin carbono orgánico, `insufficient_data` (R1)
  - [ ] `soil_cover`: meses con el suelo cubierto sobre el tiempo que dura la estrategia, con la duración de cada ciclo (HU-220). Cuando existe el NDVI (HU-208, HU-209), la razón muestra el verdor normal de esos meses para contrastar
  - [ ] `pest_break`: si una familia vuelve al terreno antes del número de ciclos que fija su regla, contando los cultivos anteriores (`previous_crop_ids`)
  - [ ] Un criterio sin regla con fuente queda `insufficient_data`, no se inventa un corte (R1, R8)
  - [ ] El criterio `soil` del ranking (HU-082) sale de estos cinco, como dice `specs/01-reglas.md` («Estrategias de rotación»)
  - [ ] Ninguna razón dice cuánto va a mejorar el suelo: compara estrategias según reglas (decisión 4, R5)
  - [ ] Función pura del motor: recibe el suelo y el NDVI ya leídos (R6)
  - [ ] Prueba: dos estrategias iguales salvo una leguminosa dan `nitrogen` mejor a la que la tiene; con carbono bajo, la que tiene abono verde da `organic_carbon` mejor
- **Reglas que aplican:** R1, R3, R5, R6, R8, R10
- **Contrato que toca:** `strategies[].soil_health` de `POST /api/v1/rotations`; `rotation_rules`; `soil_grid`, `soil_municipality`, `ndvi_grid`, `ndvi_municipality_normal`
- **Notas:** Decisión 12. No hay modelo de suelo: es una comparación entre estrategias según reglas con fuente, no una predicción. Depende de HU-062, HU-063, HU-181 y HU-213. Supuesto por confirmar: cómo entra el NDVI al nivel de `soil_cover` (hoy solo en la razón, como contraste). Agregada el 11 de octubre de 2026.

### HU-224 · Erosión en la salud del suelo

- **Historia:** Como agricultor, quiero saber si una estrategia deja mi suelo descubierto en un terreno con pendiente, para no perder suelo con la lluvia.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Criterio `erosion` de `soil_health`, con `status`, `level`, `reasons` y `rule_ids`, como los otros cuatro (HU-212)
  - [ ] Sale de la pendiente (`slope_pct`) del lote o del municipio (HU-206) y de los meses que la estrategia deja el suelo descubierto (los de `soil_cover`), con los cortes de una regla de `rotation_rules` con fuente (HU-062)
  - [ ] La razón dice la pendiente, de dónde sale (lote o municipio, NASADEM a 30 m) y cuántos meses queda descubierto el suelo; la pendiente es del terreno de la zona, no una medición del lote (R10)
  - [ ] Sin pendiente o sin regla con fuente, `insufficient_data`: no se inventa un corte (R1, R8)
  - [ ] Ninguna razón dice cuánto suelo se va a perder: compara estrategias según reglas (decisión 4)
  - [ ] Prueba: en un terreno con pendiente, una estrategia con abono verde en los meses de lluvia da `erosion` mejor que una con descanso desnudo
- **Reglas que aplican:** R1, R5, R6, R8, R10
- **Contrato que toca:** `strategies[].soil_health.erosion` de `POST /api/v1/rotations`; `municipalities.slope_pct`; `elevation_grid`; `rotation_rules`
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
