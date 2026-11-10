---
id: EP-06
titulo: "Catálogo agronómico con fuentes"
prioridad: P0
fase: [Fase 0]
rol: "Producto y agro"
agentes: [producto-agro]
subsistemas: [AG1, AG2, AG3]
depende_de: [HU-001]
reglas: [R3, R8]
estado: en curso
---

# EP-06 · Catálogo agronómico con fuentes

**Resultado esperado:** Las fichas completas, cada campo con su fuente, de los **7 cultivos del MVP** del altiplano: papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia (abono verde, `kind = cover`), más el descanso (`kind = fallow`). Y las reglas de rotación entre ellos como datos, incluidas las de los cuatro criterios de salud del suelo de las estrategias (HU-212). Cada ficha dice lo que el cultivo necesita y lo que aguanta (agua, altitud, temperatura, helada y pH), con su rango óptimo y sus límites absolutos: contra eso se califica cada ventana de siembra (HU-196). Además, los pesos por defecto de cada señal, con quién los definió y por qué.

La ficha no dice en qué época se siembra: eso lo responde el motor, ventana por ventana, con la historia de la zona.

**Es trabajo de la fase 0, sin código, y va primero en el orden de desarrollo** (`docs/orden-de-desarrollo.md`): sin fichas con fuente, la aptitud, el calor, las curvas y las estrategias quedan en «datos insuficientes». Fuentes candidatas: FAO EcoCrop, FAO-56 (Kc y etapas) y Agrosavia (fichas técnicas y las rotaciones papa-avena-arveja de Tibaitatá), todas por confirmar en `docs/fuentes.md`.

Los cultivos dependen de la región piloto, que es un supuesto mientras el reto no confirme la región (decisión 11, HU-002). La lista de 7 se decidió el 11 de octubre de 2026 (decisión 12).

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo con lo que necesita y lo que aguanta, para saber si se da en una zona y evaluar sus ventanas de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Hay una ficha por cada uno de los 7 cultivos del MVP (papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia) y otra para el descanso, con `crop_id` en `snake_case` sin tildes (`crop_id`: `papa`, `arveja`, `haba`, `maiz`, `zanahoria`, `cebolla_bulbo`, `avena_vicia` y `descanso`; un `crop_id` es un cultivo con ficha propia, no una variedad)
  - [ ] Cada ficha trae, con fuente: temperatura media anual en que se da el cultivo (`tmean_min_c`, `tmean_max_c`; antes era la altitud mínima, máxima y óptima, cambiado por la decisión 13); temperatura óptima y `heat_max_c`; rango de pH; familia (`family`); tipo de raíz (`root_type`); si fija nitrógeno (`fixes_nitrogen`); duración (`cycle_months` y los días de cada etapa en `crop_stages`, HU-142) y, si hay fuente, grados-día
  - [x] Todos los campos del contrato llenos; los que el contrato permite nulos (`tmean_min_c`, `tmean_max_c`, `heat_max_c`, los límites de las curvas `temp_*`, `rain_*` y `tmean_opt_*`, pH, `base_temp_c`, `gdd`) quedan nulos solo si no hay fuente, y se anota por qué
  - [x] `tmean_min_c` y `tmean_max_c` (temperatura media anual en que se da el cultivo) con fuente: de ahí sale la aptitud en la zona (HU-191). Cambiado el 16 de octubre de 2026 (decisión 13): antes era el rango de altitud
  - [x] `heat_max_c` (temperatura máxima que aguanta) con fuente: de ahí sale la señal de calor (HU-190) (EcoCrop, con un supuesto por confirmar en HU-190: es el máximo de la temperatura del ciclo)
  - [x] La ficha no tiene ningún campo de épocas de siembra
  - [x] Fuente por campo; ningún valor «típico» sin cita (R8)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Contrato que toca:** tabla `crops`
- **Notas:** Sin el rango de temperatura media con fuente, la aptitud queda en «datos insuficientes» y no filtra; sin `heat_max_c`, la señal de calor queda en «datos insuficientes» (`docs/riesgos.md`). Los rangos óptimos para las curvas son HU-199. Fuentes por confirmar (`docs/fuentes.md`). Cambiada el 11 de octubre de 2026 y, el mismo día, fijada a los 7 cultivos del MVP (decisión 12). Supuesto por confirmar: la avena con vicia es una mezcla de dos especies; su ficha se arma con la fuente que la describa como abono verde, o se dice qué dato sale de cada especie. **16 de octubre de 2026:** `catalog/crops.yaml` (versión 0.1.0), validado y publicado por el pipeline (`pipeline/catalog.py`, pruebas en `tests/pipeline/test_catalogo.py`). Fuentes: FAO EcoCrop (CC BY 4.0), FAO-56 tablas 11 y 12, UPRA (papa Diacol Capiro y cebolla de bulbo) y FAO para la fijación de nitrógeno. Quedan nulos, con su razón: `root_type` y `water_need` (sin fuente de una clasificación; HU-062), `base_temp_c` y `gdd` (P1). Las duraciones de FAO-56 no son de los Andes: se eligió la fila más cercana y se pide una fuente local. **Falta la revisión cruzada.**

### HU-199 · Límites óptimos y absolutos de cada cultivo

- **Historia:** Como motor, quiero el rango óptimo y los límites absolutos de temperatura, lluvia y altitud de cada cultivo, con fuente, para calificar cada señal de 0 a 100 con una curva por cultivo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Cubre los 7 cultivos del MVP; el descanso no tiene curvas
  - [x] Por cultivo: temperatura óptima (mínima y máxima) y absoluta (mínima y máxima), lluvia óptima y absoluta, y temperatura media anual óptima y absoluta para la aptitud, en las columnas de `crops` del contrato (`temp_min_c`, `temp_opt_min_c`, `temp_opt_max_c`, `rain_min_mm`, `rain_opt_min_mm`, `rain_opt_max_mm`, `rain_max_mm`, `tmean_opt_min_c` y `tmean_opt_max_c`; los absolutos de aptitud y de calor son `tmean_min_c`, `tmean_max_c` y `heat_max_c`, de HU-061)
  - [x] Cada valor con su fuente en `sources` (R8). La candidata es FAO EcoCrop, **por confirmar**: se verifica el acceso, la licencia, la especie o variedad que describe y la unidad de cada campo antes de usarla Verificado el 16 de octubre: EcoCrop se consulta en ecocrop.apps.fao.org, con licencia CC BY 4.0; describe la especie, y las unidades son °C, mm al año y pH.
  - [x] Si hay una fuente local (por ejemplo, fichas técnicas de Agrosavia) que difiere de EcoCrop, se anotan las dos en las notas de la ficha y se dice cuál se usa y por qué (la UPRA para la aptitud de la papa y la cebolla de bulbo; EcoCrop da para la cebolla una altitud máxima de 2000 m que no sirve para Colombia)
  - [x] Sin fuente, el campo queda nulo y la señal que lo necesita queda en «datos insuficientes» (R1); nunca un valor «típico»
  - [x] Validación: el óptimo cae dentro de los límites absolutos; si no, el catálogo no se publica
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R1, R8
- **Contrato que toca:** tabla `crops`
- **Notas:** Decisión 10. Las columnas ya están en el contrato (`specs/02-contratos.md`, tabla `crops`). Los `rain_*` son la lluvia anual que pide el cultivo: sirven de referencia y de contraste y no entran a la curva de una ventana; la señal de agua sale del balance hídrico, con cortes en `thresholds.yaml` (`specs/01-reglas.md`, «Cómo se califica cada señal»). El rango óptimo de temperatura media se usa para la nota informativa de aptitud (`suitability.score`, HU-191); la aptitud se decide solo con el rango absoluto (`specs/01-reglas.md`, «Aptitud del cultivo en la zona»). **16 de octubre de 2026:** hechos los rangos de los 7 cultivos en `catalog/crops.yaml`. La avena con vicia es la intersección de las dos especies, y cada nota dice de cuál sale cada límite. **Falta la revisión cruzada.**

### HU-198 · Pesos por defecto con su porqué

- **Historia:** Como equipo, queremos fijar el peso por defecto de cada señal con quién lo definió y por qué, para que el criterio de AgroSense sea explicable y se pueda revisar.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `weights.yaml` tiene un peso entero de 0 a 5 para cada señal del P0 (`water`, `frost`, `heat`, `soil`, `supply`, `market`), con número de versión (`backend/config/weights.yaml`, versión 0.1.0)
  - [x] Cada peso lleva, en el mismo archivo o en una nota enlazada, quién lo definió, cuándo y su porqué en una frase
  - [x] El porqué se presenta como criterio del equipo, no como dato agronómico: no cita una fuente que no lo dice (R5, R8)
  - [x] Ningún peso por defecto es 0: el criterio de AgroSense mira las seis señales (la API no arranca si alguno lo es)
  - [ ] Los pesos los propone el rol Producto y agro y los aprueba el dueño del producto; el cambio queda en `docs/registro-de-decisiones.md`
  - [ ] El panel «¿Cómo funciona y de dónde sale esto?» (HU-122) muestra los pesos por defecto y su porqué
- **Reglas que aplican:** R4, R5, R8
- **Contrato que toca:** `weights` y `overall_default` de la respuesta de diagnóstico; `priorities` de `/calendar`
- **Notas:** Decisión 10. Los valores no están decididos: no hay evidencia que fije cuánto pesa cada señal (`docs/riesgos.md`). Se revisan si aparece evidencia, por ejemplo con agricultores en la fase 0. El mecanismo de carga y validación del archivo es HU-075. **13 de octubre de 2026:** el archivo existe con valores **provisionales** (los de muestra de los diseños: agua 3, heladas 3, calor 3, suelo 2, oferta 3 y mercado 2), aceptados por Felipe para avanzar con «Sus prioridades». Falta la propuesta del rol Producto y agro, la aprobación formal y mostrarlos en «¿Cómo funciona?» (HU-122). `GET /api/v1/version` ya los publica.

### HU-062 · Reglas de rotación como datos

- **Historia:** Como motor, quiero las reglas de rotación como datos, para filtrar y puntuar estrategias de hasta 3 ciclos y evaluar su salud del suelo sin cambiar código.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `catalog/rotation_rules.yaml` con la forma del contrato («Reglas de rotación como datos»): cada regla con `kind` (`filter` o `health`), `condition_type` de la lista cerrada, `params`, `levels`, `reason_template` y `source_id`. Como mínimo: no repetir familia en ciclos seguidos (filtro) y las reglas `health` de los cinco criterios
  - [ ] Cubren todos los pares posibles entre los 7 cultivos del MVP y el descanso: para cada par de ciclos seguidos se puede decir qué reglas aplican
  - [ ] Reglas de los cinco criterios de salud del suelo (`criterion`: `nitrogen`, `organic_carbon`, `soil_cover`, `pest_break`, `erosion`), con los cortes que dan cada nivel, para HU-212 y HU-224. La de `erosion` cruza la pendiente con los meses de suelo descubierto (decisión 14)
  - [ ] Cada regla con tipo, condición, efecto, criterio y fuente (R8)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Contrato que toca:** `rotation_rules`
- **Notas:** Punto de partida con fuente: las rotaciones papa-avena-arveja evaluadas por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`). Cambiada el 11 de octubre de 2026 (decisión 12). Supuesto por confirmar: cuántos ciclos debe esperar la papa para volver al mismo terreno (`pest_break`) y con qué fuente.

### HU-063 · Suelo, heladas y abonos verdes en el catálogo

- **Historia:** Como motor, quiero el rango de pH de cada cultivo, sus etapas sensibles a la helada y al calor y los abonos verdes y el descanso como opciones de rotación, para evaluar suelo, heladas y calor y recomendar rotaciones que recuperen el suelo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `kind`, `ph_min`, `ph_max`, `ph_opt_min` y `ph_opt_max` en cada ficha, con fuente; nulos si no hay fuente. Son los límites absolutos y óptimos de la curva de la señal de suelo (HU-196)
  - [ ] `frost_sensitive` y `heat_sensitive` por etapa en `crop_stages`, con fuente
  - [ ] La avena con vicia (abono verde, `kind = cover`) y el descanso (`kind = fallow`), con sus reglas de rotación y su duración con fuente
  - [ ] Etapas sensibles a la helada de los 7 cultivos, con fuente
  - [ ] Reglas de suelo con fuente: exclusión por pH fuera de rango y bonificación de abonos verdes, descanso y leguminosas con carbono orgánico bajo (umbral con fuente)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Notas:** Punto de partida: las rotaciones papa-avena-arveja evaluadas por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`). Ese punto de partida es de la región piloto supuesta en Colombia (decisión 11). **16 de octubre de 2026:** pH con fuente (EcoCrop) en los 7. La sensibilidad a la helada por etapa sale de la temperatura que mata la planta en EcoCrop (papa, arveja, zanahoria y avena con vicia), con un supuesto por confirmar: sensible en todas las etapas. Haba, maíz y cebolla quedan sin dato (EcoCrop no lo trae) y la sensibilidad al calor queda nula en todos: falta fuente por etapa. La duración de la avena con vicia sale de FAO-56 (avena); la del descanso la elige quien arma la estrategia. Las reglas de suelo son de HU-062.

### HU-227 · Valor como forraje en el catálogo

- **Historia:** Como agricultor con ganado, quiero saber qué ciclos de una estrategia me dan forraje, para elegir una rotación que también alimente a mis animales.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La ficha de cada cultivo dice si sirve de forraje (`forage`), con fuente (R8); sin fuente, nulo
  - [ ] Las razones de una estrategia lo dicen cuando un ciclo da forraje (por ejemplo, la avena con vicia)
  - [ ] No entra a ningún criterio del ranking hasta que se decida cómo (supuesto por confirmar: un peso propio o dentro de `income`)
- **Reglas que aplican:** R5, R8
- **Contrato que toca:** `crops`
- **Notas:** Decisión 14: el enunciado completo nombra el valor como forraje entre las prioridades del agricultor. Agregada el 8 de noviembre de 2026.
