---
id: EP-12
titulo: "Calidad y trazabilidad"
prioridad: P0
fase: [Hora 0, Evento]
rol: "Calidad, con Datos"
agentes: [calidad, datos]
subsistemas: [S3, D4]
depende_de: [HU-011]
reglas: [R1, R2, R3, R4, R7, R8, R9]
estado: en curso
---

# EP-12 · Calidad y trazabilidad

**Resultado esperado:** El equipo puede demostrar que cada resultado es correcto, reproducible y trazable a sus fuentes.

Empieza en la hora 0 con los casos de referencia y se cierra al final del evento.

## Historias de usuario

### HU-121 · Casos de referencia del motor

- **Historia:** Como equipo, quiero casos de referencia con resultado esperado escrito antes de programar, para saber si el motor acierta.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Dos clases de casos, cada una rotulada en su nombre y en su módulo. **Casos de ejemplo:** tablas mínimas armadas en la prueba, rotuladas como ejemplo (R5); prueban cada regla con exactitud. **Casos reales:** municipio, cultivo y fecha reales sobre `data/published`. Cada caso real fija la `dataset_version` con la que se calculó su resultado esperado (R4) y dice de qué tabla y columnas sale el valor esperado y cómo se calcula (R5, R8). Si la versión publicada no es esa, la prueba falla con un mensaje que dice que hay que recalcular el caso; nunca pasa en silencio ni se salta. Un caso real nunca inventa ni rellena un valor: sin dato, el esperado es `insufficient_data` (R1)
  - [ ] Casos reales mínimos de aptitud: papa en Puerto Salgar (`25572`, `tmean_annual_c` 28,4 °C, sobre el `tmean_max_c` de 16 °C de su ficha) es `not_suitable`, y papa en Duitama (`15238`, 14,4 °C, dentro del óptimo de 12 a 15 °C) es `suitable` con `suitability.score` 100. Los valores se vuelven a comprobar contra la versión fijada (la 2026.11.10 hoy; la 2026.11.11 cuando entre el PR #62)
  - [ ] Casos que esperan otra HU: un caso cuyo motor aún no existe se escribe ya, con su resultado esperado, y se marca `pytest.mark.xfail(strict=True, reason="espera HU-xxx")` con la HU de la que depende. Con `strict`, cuando esa HU se implemente y el caso pase, la prueba **falla** hasta que se quite la marca, así que un caso pendiente no se puede olvidar en silencio. Nunca se usa `skip` ni un `xfail` sin `strict` en estos casos. Un conteo de los casos pendientes con su HU sale en el resumen de la prueba (`-rx`), y quitar la marca va en el PR de la HU que los activa
  - [ ] De 8 a 12 combinaciones de municipio, cultivo y fecha de siembra, incluidos verde, rojo y «no evaluable», un rojo por helada crítica, un suelo desfavorable que no basta para rojo y una exclusión de rotación por pH
  - [ ] Cultivo no apto para la zona: `suitability.level = not_suitable`, luz `red`, acción `rotate`, `window` y `signals` nulos, y ninguna estrategia que lo use
  - [ ] Estrategias, exclusión por regla: una que repite familia en ciclos seguidos no está en `strategies`, está en `excluded` (o la cuenta en `excluded_counts`) con `kind = rule`, `cycle` y `rule_id` de la regla de `same_family_consecutive` (`familia_seguida`), y su razón dice la familia repetida
  - [ ] Estrategias, exclusión por clima: una con un ciclo de helada crítica (`frost` `unfavorable` y crítica) no está en `strategies` y está en `excluded` con `kind = high_risk`, `signal = frost` y el `cycle` en que ocurre; ninguna otra señal buena la rescata (R2)
  - [ ] Estrategias, `source_ids`: cada elemento de `excluded` y cada `issues` trae `source_ids` no vacío y cada uno existe en `sources` (R8)
  - [ ] Estrategias, oferta y mercado: con `supply` o `market` críticos en un ciclo, la estrategia no se excluye (`excluded_counts` no suma por ellos) y el efecto se ve solo en que baja su `scores.income` (R3)
  - [ ] Estrategias, coherencia: el primer ciclo de una estrategia y `/diagnostics` con la misma entrada (municipio, cultivo, fecha, `irrigated`, `signal_priorities` y suelo) dan las mismas señales, calificaciones y luces
  - [ ] Estrategias, prioridades: con `soil` en 5 y las demás prioridades iguales, una estrategia con abono verde queda con `rank` menor (mejor) que una igual sin él
  - [ ] Estrategias, rotación actual: con `current_crop_ids` que viola una regla, `current_strategy` sale con `rank` nulo y `issues` con la regla y su `source_ids`, y no aparece en `excluded`; sin `current_crop_ids`, `current_strategy` es nula y `limitations` lo dice (R1)
  - [ ] Salud del suelo, carbono: sin carbono orgánico del suelo, `organic_carbon` es `insufficient_data`, con `level` nulo, y la web no lo pinta como malo (R1)
  - [ ] Salud del suelo, nitrógeno: una estrategia con leguminosa da `nitrogen` mejor (`favorable` o `moderate` frente a `unfavorable`, según los cortes de `legume_cycles`) que una igual sin ella
  - [ ] Salud del suelo, rotación de referencia (Agrosavia, Tibaitatá): papa → avena con vicia → arveja no sale `unfavorable` en `pest_break`; con `papa_espera` en 3 y 2 sale `moderate` (PR #62)
  - [ ] Salud del suelo, forma: cada uno de los cinco criterios trae `status`, `level` (nulo con `insufficient_data`), `rule_ids` y `source_ids`; un criterio sin regla `health` con fuente es `insufficient_data` y nunca se inventa un corte (R1, R8)
  - [ ] Varias fuentes de lluvia: si la fuente que calcula `water` no tiene dato para el municipio, la señal es `insufficient_data` aunque la otra tenga, y `sources` trae las dos sin mezclar
  - [ ] «Qué cambió»: un mes sin datos en uno de los dos periodos da la diferencia `insufficient_data`; misma entrada, misma salida
  - [ ] Ficha sin rango de temperatura media con fuente: aptitud `insufficient_data`, no bloquea y aparece en las limitaciones
  - [ ] Ventana de alto riesgo que no entra en las mejores: una ventana con una señal crítica desfavorable y el balance más alto queda después de las demás y fuera de `best_windows`
  - [ ] Con y sin riego: la misma ventana con déficit de agua es `unfavorable` en `water` con `irrigated = false` y no lo es con `irrigated = true`; con `irrigated` nulo, se evalúa como sin riego y lo dice en las limitaciones
  - [ ] Acción `other_window` con `best_windows`, y un caso en que `best_windows` viene vacío
  - [ ] Coherencia: una de las mejores ventanas (`best_windows`) y el diagnóstico de esa misma fecha dan las mismas señales y calificaciones
  - [ ] Curva: un valor dentro del óptimo califica 100, uno en el límite absoluto califica 0 y el punto medio, 50 (HU-196)
  - [ ] Peso 0 en oferta cambia la luz: con la oferta `unfavorable` no crítica y las demás señales `favorable`, `overall_default` da `yellow` con `rotate` y, con `supply` en 0, `overall` da `green` con `sow`; la respuesta trae las dos
  - [ ] Riesgo grave de clima con peso 0 sigue contando: una helada crítica con `frost` en 0 da `red` en `overall`, y la señal trae `counts = true`
  - [ ] Peso 4 o 5: un `moderate` en esa señal cuenta como `unfavorable` y cambia la luz frente a la de AgroSense
  - [ ] Factor limitante: una ventana con una señal en 15 y el promedio ponderado más alto nunca queda por encima de una ventana con todas sus señales en 60 o más, ni entra primera en `best_windows`
  - [ ] P1 (con HU-197): con `rotate`, ningún cultivo `not_suitable` ni con una señal de clima `unfavorable` aparece en `alternatives`
  - [ ] Automatizados en pytest y corriendo en Docker, en local y en CI
  - [ ] Los casos del motor viven en `tests/engine/casos/` (`test_estrategias.py`, `test_salud_del_suelo.py`, `test_diagnostico.py`, `test_aptitud.py`, `test_que_cambio.py`), con lo común (cargar `data/published`, comprobar la `dataset_version`, armar tablas de ejemplo) en `tests/engine/casos/conftest.py`. Los de las cuentas siguen en `tests/accounts/`, contra el PostgreSQL de Compose
- **Grupos, dependencias y entrega** (HU-121 se entrega en tres PR de 700 líneas o menos, regla del equipo desde el 12 de noviembre de 2026):

  | Grupo de criterios | HU de la que depende el motor | Responsable | PR de HU-121 |
  |---|---|---|---|
  | Estrategias y salud del suelo | HU-081, HU-212 y HU-213 | Juan Cárdenas | PR 1 |
  | Diagnóstico, aptitud, curvas, pesos, factor limitante y fuentes de lluvia | HU-191, HU-071 a HU-074, HU-192 y HU-196 | David Carreño | PR 2 |
  | «Qué cambió» | HU-216 y HU-218 | Luisa (HU-216) y Juan David (HU-218) | PR 3 |
  | Cuentas | HU-165 | Haider | PR 3 |
- **Casos de las cuentas** (contra el PostgreSQL de Compose; lo que dicen del progreso se comprueba cuando exista HU-167, P1):
  - [ ] Dividir: una temporada cosechada de 1 ha con dos sucesoras de 0,5 ha cada una se acepta, y el progreso da dos relaciones
  - [ ] Juntar: dos temporadas cosechadas de 0,5 ha con una sucesora de 1 ha se acepta, y el progreso da dos relaciones hacia la misma
  - [ ] Área que no cabe: en un lote de 1 ha, las sucesoras de una temporada cosechada de 1 ha que suman 1,2 ha responden 422, porque las temporadas en curso pasarían del área del lote
  - [ ] Terreno anterior más terreno libre: después de una temporada cosechada de 1 ha, una sucesora de 1,5 ha se acepta si hay 0,5 ha libres en el lote
  - [ ] `follows_season_ids` con una temporada de otro lote, sin cosechar o cosechada después de la nueva siembra responde 422
  - [ ] P1 (con HU-204): una temporada borrada aparece en el historial con `restorable_until` y vuelve al restaurarla
- **Reglas que aplican:** R1, R2, R3, R4, R9
- **Notas:** Los casos nuevos se agregaron el 11 de octubre de 2026 con el cambio a ventanas de siembra y, el mismo día, con las prioridades, el factor limitante, las alternativas y la división de lotes (decisión 10), y después con las estrategias, la salud del suelo, las fuentes de lluvia y «Qué cambió» (decisión 12). Pasa de M a L.
  **Dos clases de casos (14 de noviembre de 2026):** los de ejemplo, con tablas mínimas rotuladas como ejemplo (R5), prueban cada regla con exactitud; los reales usan municipios, cultivos y fechas de `data/published` con la `dataset_version` fijada, y prueban que el motor acierta con los datos de la demo. Si cambia el dataset publicado, los casos reales fallan hasta que se recalculan a mano y se anota la nueva versión; no se regeneran solos. Los casos de un motor que no existe se escriben ya con `xfail(strict=True)` (ver el criterio). `tests/engine/casos/` es una carpeta nueva con su `__init__.py`; no choca con `tests/engine/test_suitability.py`, `test_curve.py`, `test_ventana.py` ni `test_etapas.py`, que son pruebas unitarias de cada módulo y siguen donde están.
  **Sin caso en el PR 1 (14 de noviembre de 2026):** exclusión por helada crítica, oferta y mercado que no excluyen, coherencia del primer ciclo con `/diagnostics` y prioridad `soil` en 5. Necesitan que el dataset de ejemplo publique las heladas por mes (`climate_risk_month`, `climate_frost_month`: HU-045, PR #61) y la oferta (`supply_semester`), que `publish()` todavía no escribe; inventar esos Parquet a mano sería suponer cómo los lee el motor. Se escriben en el PR 2.
  **Supuestos por confirmar (PR 1):** (a) los ids de `rotation_rules` (`familia_seguida`, `papa_espera`) y sus cortes salen del PR #62, que aún no está en esta rama: se confirman al entrar; (b) los municipios, cultivos y fechas de los casos reales de estrategias, y sus resultados esperados, se eligen con el dataset 2026.11.11 y no se inventan aquí; (c) el resultado exacto de `nitrogen` con y sin leguminosa depende de los cortes de `legume_cycles` de HU-062; (d) el contrato no dice si `excluded` trae `cycle` en las exclusiones `not_suitable` y `soil_ph` ni qué trae en `soil_ph` (su ejemplo solo muestra `rule` y `high_risk`): se deja sin comprobar hasta que Haider o Felipe lo precisen; (e) los responsables de «Qué cambió» no se conocen con lo que hay en el repositorio y se confirman en Plane.

### HU-122 · Procedencia de cada dato

- **Historia:** Como jurado, quiero saber de dónde sale cada dato, para confiar en el resultado.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Manifiesto con versión, fuentes y cobertura
  - [x] Cada entrada de `sources` dice qué cubre (`coverage`: país o región) (hecho para DIVIPOLA)
  - [x] `sources.yaml` dice, por región, qué fuente calcula cada señal (también qué producto NASA da la lluvia de `water`); la validación falla si una señal de la región no tiene fuente asignada o la fuente no existe en `sources` (R8)
  - [ ] Cada producto NASA del MVP (POWER, NASADEM, IMERG, MODIS NDVI, SMAP y GIBS) tiene su entrada en `sources` con misión, resolución, periodo, acceso y licencia, y el panel lo muestra
  - [ ] `GET /api/v1/version` responde `dataset_version`, `rules_version`, `created_at`, `region`, `default_weights` (los pesos por defecto de `weights.yaml`, para mostrarlos antes de consultar) y `sources` (lista con `source_id`, `name`, `institution`, `url`, `coverage` y `license`), según el contrato. **Parcial (13 de octubre de 2026):** el endpoint ya existe y publica `default_weights`, `weights_version` y `weights_reasons`; lo demás viene nulo o vacío hasta que haya dataset, reglas y fuentes publicados
  - [ ] La web muestra fuentes, versión y los pesos por defecto con su porqué (HU-198)
- **Reglas que aplican:** R4, R7, R8
- **Contrato que toca:** `GET /api/v1/version`, `manifest.json`, `sources`
- **Notas:** Decisión 11: un indicador puede tener varias fuentes; se muestran juntas y nunca se mezclan. **15 de octubre de 2026:** `manifest.json` y `sources` ya se publican (con DIVIPOLA como primera fuente) y `GET /version` responde con el dataset, la región y las fuentes; `rules_version` va nula mientras no exista el catálogo. Falta `sources.yaml`, las fuentes de la NASA y la web. **11 de noviembre de 2026:** hecho `catalog/sources.yaml` 1.0.0 (`common/signal_sources.py`): lo revisan el pipeline antes de publicar y la API al arrancar; las fuentes sin adaptador van en `planned` con su HU. La lluvia de `water` es la de NASA POWER, temporal y con aviso, hasta IMERG (decidido por Felipe el 11 de noviembre de 2026). Faltan las fuentes de la NASA que aún no tienen adaptador y la web.

### HU-123 · Reconstruir el dataset con un comando

- **Historia:** Como equipo, quiero reconstruir el dataset con un comando, para repetir la demo con los mismos datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Un comando regenera `data/published` desde la caché: `uv run python -m pipeline.build` (con `--descargar`, antes baja las fuentes)
  - [x] El resultado coincide con el manifiesto: al terminar de publicar, `pipeline.build` revisa que cada tabla que nombra el manifiesto exista y tenga sus filas, que no haya tablas que no nombre y que la versión sea la de `region.yaml`. `uv run python -m pipeline.build --verificar` hace solo esa revisión, sin publicar, y termina con error si no coincide
- **Notas:** Hecha el 8 de noviembre de 2026 (`verify` en `pipeline/build.py`; pruebas en `tests/pipeline/test_reconstruir.py`). Reconstruir dos veces desde la misma caché da los mismos archivos byte a byte (R4); solo cambia la fecha de `created_at` del manifiesto.
