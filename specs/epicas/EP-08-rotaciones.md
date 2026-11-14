---
id: EP-08
titulo: "Estrategias de rotación válidas, ordenadas y explicadas"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M1, M2, M3, M4, M6]
depende_de: [EP-06, HU-071, HU-072, HU-073, HU-074, HU-181, HU-191, HU-192, HU-220]
reglas: [R1, R2, R3, R4, R5, R6, R8, R9]
estado: pendiente
---

# EP-08 · Estrategias de rotación válidas, ordenadas y explicadas

**Resultado esperado:** Para un lote (o un municipio y un área, sin cuenta), el motor responde un ranking de **estrategias de rotación de hasta 3 ciclos**: secuencias que cumplen las reglas, que se dan en la zona y sin ningún ciclo de alto riesgo, ordenadas por las prioridades del agricultor (agua, suelo, ingreso y riesgo), con su salud del suelo (HU-212, EP-18) y explicadas, **comparadas contra la rotación que el agricultor ya hace** (HU-223, decisión 14). Cada ciclo trae su ventana de siembra y su diagnóstico.

**Es el centro del producto (decisión 12).** El flujo del MVP es: lote o municipio y área → estrategias de rotación → un ciclo con su diagnóstico → agua del plan → qué cambió. El diagnóstico de ventana (EP-07) es la revisión de cada ciclo.

La estrategia empieza en `sowing_date`, la fecha en que se sembraría su primer ciclo. Cada ciclo se evalúa en su propia ventana de siembra (`specs/01-reglas.md`, «Estrategias de rotación»). Comparar estrategias según reglas no es predecir cuánto mejora el suelo: no hay modelo de suelo.

## Historias de usuario

### HU-081 · Filtrar estrategias válidas

- **Historia:** Como agricultor, quiero ver solo estrategias agronómicamente válidas, que se den en mi zona y sin ciclos de alto riesgo, para no recibir recomendaciones dañinas.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - **Candidatas (decisión 15, paso 0)**
  - [ ] El motor arma todas las secuencias de `cycles` ciclos (2 o 3) con los cultivos del catálogo, de cualquier `kind` (`crop`, `cover`, `fallow`; HU-063), sin el mismo `crop_id` en dos ciclos seguidos y sin dos descansos seguidos
  - [ ] El orden de las candidatas es determinista: el de los `crop_id` del catálogo ordenados alfabéticamente, ciclo por ciclo (R4). Dos ejecuciones iguales dan la misma lista
  - [ ] Prueba: con los 8 cultivos actuales de `catalog/crops.yaml` salen 392 candidatas con `cycles = 3` (8 × 7 × 7) y 56 con `cycles = 2` (8 × 7)
  - **Fase 1, sin fechas: `rule`, `not_suitable` y `soil_ph`**
  - [ ] Las reglas `filter` de `rotation_rules` se revisan entre cada par de ciclos seguidos y entre el cultivo anterior más reciente y el primer ciclo; una que se viola da el motivo `rule` con `rule_id` (R3)
  - [ ] `same_family_consecutive` compara solo `family` entre ciclos seguidos y entre el más reciente de `previous_crop_ids` (el primero de la lista) y el primer ciclo. Con `families` nulo vale para todas las familias
  - [ ] `family_return_min_cycles` con `kind = filter` cuenta `family` y `secondary_families` de la ficha (decisión 16). El catálogo hoy solo la usa como `health` (`pest_break`, HU-212); el filtro igual la soporta
  - [ ] Un ciclo con un cultivo que no es apto para la zona (HU-191, temperatura media anual, decisión 13) da el motivo `not_suitable`: cita el ciclo (el primero donde aparece el cultivo), el `crop_id`, el rango de temperatura media de la ficha y la misma razón de `/diagnostics`; `source_ids` trae la fuente del rango de la ficha, `nasa_power` y `cenicafe_lapse_rate`
  - [ ] Un cultivo cuyo rango de pH tolerado queda fuera de **todo** el intervalo `ph_p05`–`ph_p95` del suelo (lote o municipio) da el motivo `soil_ph` (HU-184), con el `cycle` (el primero donde aparece el cultivo), el `crop_id`, el intervalo de pH del suelo y el rango del cultivo; `source_ids` trae la fuente del rango de pH de la ficha y la del suelo (HU-181)
  - [ ] A un ciclo de descanso (`kind = fallow`) no se le aplican ni la aptitud ni el pH: no tiene rango, y eso no es una limitación
  - [ ] Un cultivo sin rango de temperatura media o de pH con fuente, o sin suelo publicado (HU-181), no se excluye: se agrega a `limitations` (R1, R8)
  - [ ] Abonos verdes (`kind = cover`) y descanso (`kind = fallow`) entran como ciclos (HU-063)
  - **Fase 2: `high_risk`**
  - [ ] Solo las candidatas que sobreviven la fase 1 se diagnostican (HU-213). El filtro **recibe** el diagnóstico de cada ciclo como entrada y no lo calcula: no lee archivos ni base de datos (R6)
  - [ ] Un ciclo con `water`, `frost` o `heat` desfavorable y crítica da el motivo `high_risk` con `signal`; cita el ciclo, la señal crítica y su razón (R2)
  - [ ] La oferta y el mercado nunca excluyen una estrategia: un ciclo con `supply` o `market` desfavorable, aunque sea crítico, baja el criterio `income` y se dice en las razones (hoy `supply` y `market` son siempre `insufficient_data`: sin curva, decisión de Felipe del 11 nov 2026)
  - **Salida**
  - [ ] Cada exclusión registra `crop_ids`, el ciclo, el `kind` del motivo, la regla o la señal, la razón y `source_ids` (R8), con la forma de `excluded` del contrato
  - [ ] Una estrategia con varios motivos se excluye una sola vez: el motor junta todos sus motivos, `excluded` muestra el primero en el orden `rule` → `not_suitable` → `soil_ph` → `high_risk` y `excluded_counts` la cuenta una sola vez, por ese primer motivo (supuesto por confirmar, contrato)
  - [ ] Mientras HU-082 no exista, `excluded` se ordena por número de motivos (menos primero) y después por `crop_ids` en orden alfabético (R4); con HU-082, en el orden que habría tenido en el ranking (supuesto por confirmar)
  - [ ] Modo «actual» (decisión 14, HU-223): el mismo filtro, sobre la rotación actual, devuelve todos sus motivos como `issues` y nunca la excluye
  - [ ] Prueba: una estrategia que repite familia en dos ciclos seguidos no aparece en el ranking y su exclusión cita la regla
  - [ ] Prueba: una estrategia con un ciclo de helada crítica no aparece, por buenos que sean sus demás criterios
  - [ ] Prueba: papa en un municipio cálido de la región (por ejemplo, Puerto Salgar, 28,4 °C frente a un máximo de 16 °C) da `not_suitable`; el descanso nunca
  - [ ] Prueba: `backend/engine/` no importa `fastapi` ni `sqlalchemy` ni abre archivos (R6)
  - [ ] HU-081 se da por hecha con sus pruebas unitarias; los casos de referencia de `tests/engine/casos/test_estrategias.py` (PR #70) siguen en `xfail` hasta HU-084
- **Reglas que aplican:** R1, R2, R3, R4, R6, R8
- **Contrato que toca:** `excluded` y `excluded_counts` de la respuesta de `POST /api/v1/rotations`; `rotation_rules`
- **Notas:** HU-081 es el motor (`backend/engine/`); el endpoint es HU-084. Entrega en 3 PR de código: B (candidatas y reglas), C (aptitud y pH) y D (alto riesgo y `excluded`). Con cuenta, los cultivos anteriores son los de todas las temporadas de las que viene el terreno (`follows_season_ids`, HU-165): si el terreno junta dos partes con cultivos distintos, cada regla de filtro se revisa contra cada cultivo anterior (supuesto por confirmar). `previous_crop_ids` va del más reciente al más antiguo. Las 392 y 56 candidatas salen de 8 cultivos del catálogo; «sin dos descansos seguidos» ya lo cubre la regla del mismo `crop_id`, porque hay un solo descanso. El `cycle` de una exclusión por `not_suitable` o `soil_ph` es el primero donde aparece el cultivo (contrato, aprobado por Felipe el 14 de noviembre de 2026, PR #73). La decisión 16 y `crops.secondary_families` llegan con el PR #62 (HU-062). Pregunta para Felipe (contrato): ¿aprueba que `excluded` muestre el primer motivo en el orden `rule` → `not_suitable` → `soil_ph` → `high_risk`, que `excluded_counts` cuente cada estrategia una vez por ese motivo y que «primero las de un solo motivo» se ordene por el número de motivos? Cambiada el 11 de octubre de 2026 a estrategias de hasta 3 ciclos (decisión 12). Precisada el 14 de noviembre de 2026.

### HU-213 · Ciclos de una estrategia con su diagnóstico

- **Historia:** Como motor, quiero armar los ciclos de cada estrategia con su ventana de siembra y su diagnóstico, para que cada ciclo se revise con el mismo cálculo del diagnóstico.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `cycles` es 2 o 3 (por defecto 3). El primer ciclo se siembra en `sowing_date`; cada ciclo siguiente, en la fecha que fija la regla de encadenamiento de `specs/01-reglas.md` después de la cosecha estimada del anterior
  - [ ] Cada ciclo trae `crop_id`, `sowing_date`, `harvest_estimate`, `harvest_basis`, la luz con los pesos de quien consulta (`light`) y con los de AgroSense (`light_default`), `limiting_signal`, `high_risk` y `diagnosis`: el diagnóstico de esa ventana con la forma de la respuesta de `/diagnostics` (sin `request`, `best_windows` ni `alternatives`)
  - [ ] El diagnóstico de un ciclo sale de la misma función del motor que `/diagnostics`: prueba de que el primer ciclo y `/diagnostics` con la misma entrada dan las mismas señales y calificaciones
  - [ ] Las señales usan `signal_priorities` (un peso de 0 a 5 por señal, como `priorities` de `/diagnostics`); sin ellas, los pesos de `weights.yaml`. Con `lot_id`, el suelo, la altitud y `irrigated` salen del lote
  - [ ] La duración de cada ciclo sale de las etapas por calendario (HU-220). El descanso dura lo que dice su ficha y no tiene diagnóstico: `light`, `limiting_signal` y `diagnosis` vienen nulos
  - [ ] La fecha de referencia entra al motor como parámetro: el motor no lee el reloj (R4, R6)
  - [ ] Un ciclo que cae más de doce meses después de hoy se evalúa igual, con la historia de la zona; la oferta usa el último dato de su semestre y la razón lo dice
- **Reglas que aplican:** R1, R2, R4, R5, R6
- **Contrato que toca:** `strategies[].cycles` de la respuesta de `POST /api/v1/rotations`
- **Notas:** Decisión 12. Depende de HU-074, HU-191, HU-192 y HU-220. Encadenamiento decidido el 8 de noviembre de 2026 (decisión 15): el ciclo siguiente se siembra el lunes siguiente a la cosecha estimada del anterior. Agregada el 11 de octubre de 2026.

### HU-082 · Ordenar estrategias por prioridades

- **Historia:** Como agricultor, quiero ordenar las estrategias según mis prioridades (agua, suelo, ingreso y riesgo), para elegir la que me conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Puntaje de 0 a 100 por criterio (`water`, `soil`, `income`, `risk`) y total ponderado por `priorities` (un entero de 0 a 5 por criterio)
  - [ ] Cada criterio sale de los ciclos con una regla documentada en `specs/01-reglas.md` («Estrategias de rotación»): `water` de las señales `water` de sus ciclos, `soil` de `soil_health` (HU-212), `income` de las señales `supply` y `market` de sus ciclos, y `risk` del factor que más limita entre sus ciclos
  - [ ] Un criterio sin datos tiene puntaje nulo, no entra al total y va a las limitaciones (R1); nunca se rellena
  - [ ] Devuelve hasta 10 estrategias; misma entrada, mismo orden; desempate determinista (R4)
  - [ ] Prueba: subir el peso de `soil` sube en el ranking a una estrategia con abono verde frente a una sin él, con todo lo demás igual
- **Reglas que aplican:** R1, R4, R5
- **Contrato que toca:** `strategies[].scores`, `total_score` y `rank` de `POST /api/v1/rotations`
- **Notas:** La oferta (`supply`) entra a las estrategias solo por el criterio `income` (decisión 12: es valor agregado, no protagonista); en cada ciclo sigue siendo una de las seis señales, con su peso. Decidido el 8 de noviembre de 2026 (decisión 15, `specs/01-reglas.md`): la fórmula de cada criterio, el tope de 10 estrategias y el desempate (primero `risk` más alto y después el orden de los `crop_id`). Cambiada el 11 de octubre de 2026 a estrategias de hasta 3 ciclos (decisión 12); la fecha de cada ciclo la resuelve HU-213.

### HU-083 · Explicar el orden de las estrategias

- **Historia:** Como agricultor, quiero entender por qué una estrategia quedó arriba, para confiar en ella.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] De 2 a 4 razones por estrategia, de plantillas fijas
  - [ ] Cada razón cita una regla o un indicador que el motor evaluó (R5)
  - [ ] Al menos una razón cita un criterio de salud del suelo (HU-212) cuando está disponible
  - [ ] Con rotación actual (HU-223), al menos una razón dice en qué gana o pierde la estrategia frente a ella, con el criterio y la regla que lo explican
  - [ ] Ninguna razón dice cuánto va a mejorar el suelo ni cuánto se va a cosechar: es una comparación entre estrategias según reglas (decisión 4)
- **Reglas que aplican:** R5, R8

### HU-084 · Endpoint de estrategias de rotación

- **Historia:** Como desarrollador web, quiero el endpoint de estrategias de rotación, para mostrar el ranking y cada ciclo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cumple el OpenAPI: recibe `municipality_id`, `sowing_date`, `previous_crop_ids`, `current_crop_ids` (HU-223), `cycles`, `priorities`, `signal_priorities`, `irrigated` y `lot_id`, según el contrato
  - [ ] 422 con `cycles` distinto de 2 o 3; `priorities` o `signal_priorities` con un peso fuera de 0 a 5 o todos en 0; `sowing_date` con formato inválido, anterior a hoy o a más de doce meses; `previous_crop_ids` con más de 3 cultivos o alguno fuera del catálogo; o `current_crop_ids` con menos de 2 o más de 3 cultivos o alguno fuera del catálogo
  - [ ] La respuesta trae hasta 10 estrategias excluidas con su motivo, incluidas las que tienen un cultivo no apto o un ciclo de alto riesgo, y `excluded_counts` con el total por motivo
  - [ ] Sin estrategias válidas: 200 con `strategies` vacía y las exclusiones
  - [ ] 401 con `lot_id` y sin sesión; 404 con un lote ajeno
  - [ ] No guarda los datos de la finca ni quién consultó (R9)
- **Reglas que aplican:** R1, R3, R4, R9
- **Contrato que toca:** `POST /api/v1/rotations`, tabla de errores
- **Notas:** `previous_crop_ids` admite de 0 a 3 cultivos: vacía es la primera siembra del terreno (cambio del 11 de octubre de 2026, decisión 12).

### HU-223 · La rotación actual como referencia

- **Historia:** Como agricultor, quiero ver la rotación que ya hago evaluada igual que las sugeridas, para saber qué gano o pierdo si la cambio.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `current_crop_ids` (opcional, de 2 a 3 cultivos del catálogo en el orden en que se siembran) se evalúa como `current_strategy`, con los mismos ciclos desde `sowing_date`, el mismo diagnóstico por ciclo (HU-213), los mismos criterios (HU-082) y la misma salud del suelo (HU-212)
  - [ ] Si tiene menos cultivos que `cycles`, se repite desde el primero hasta completarlos
  - [ ] **Nunca se excluye:** si viola una regla de filtro, tiene un cultivo no apto, un pH fuera de rango o un ciclo de alto riesgo, viene igual, con esos motivos en `issues` y la misma forma de `excluded` (R3 sigue valiendo para las sugeridas)
  - [ ] `rank` nulo y `kind = current`. Cada estrategia sugerida trae `kind = suggested` y `vs_current`: la diferencia de cada criterio y del total frente a la actual; nula si el criterio no califica en alguna de las dos (R1)
  - [ ] Una estrategia sugerida igual a la actual no se repite en `strategies`
  - [ ] Sin `current_crop_ids`, `current_strategy` es nula, `vs_current` también y `limitations` dice que no hay referencia
  - [ ] Prueba: la rotación papa–papa–papa viene en `current_strategy` con el motivo de la regla de familia en `issues`, aunque ninguna sugerida la repite
  - [ ] Prueba: con la actual y dos sugeridas válidas, la respuesta permite comparar al menos tres estrategias, como pide el reto
- **Reglas que aplican:** R1, R2, R3, R4, R5, R6
- **Contrato que toca:** `current_crop_ids`, `current_strategy`, `kind` y `vs_current` de `POST /api/v1/rotations`
- **Notas:** Decisión 14: el enunciado completo pide comparar «al menos tres estrategias de rotación, incluida la actual». Con cuenta, la web arma `current_crop_ids` con el historial del terreno (HU-165): los cultivos de las temporadas de las que viene, del más antiguo al más reciente (HU-214). Depende de HU-081, HU-082, HU-212 y HU-213. Agregada el 8 de noviembre de 2026.
