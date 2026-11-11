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

**Resultado esperado:** Las fichas completas, cada campo con su fuente, de los **7 cultivos del MVP** del altiplano: papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia (abono verde, `kind = cover`), más el descanso (`kind = fallow`). Y las reglas de rotación entre ellos como datos, incluidas las de los cinco criterios de salud del suelo de las estrategias (HU-212 y, para la erosión, HU-224; decisión 14). Cada ficha dice lo que el cultivo necesita y lo que aguanta (agua, altitud, temperatura, helada y pH), con su rango óptimo y sus límites absolutos: contra eso se califica cada ventana de siembra (HU-196). Además, los pesos por defecto de cada señal, con quién los definió y por qué.

La ficha no dice en qué época se siembra: eso lo responde el motor, ventana por ventana, con la historia de la zona.

**Es trabajo de la fase 0, sin código, y va primero en el orden de desarrollo** (`docs/orden-de-desarrollo.md`): sin fichas con fuente, la aptitud, el calor, las curvas y las estrategias quedan en «datos insuficientes». Fuentes candidatas: FAO EcoCrop, FAO-56 (Kc y etapas) y Agrosavia (fichas técnicas y las rotaciones papa-avena-arveja de Tibaitatá), todas por confirmar en `docs/fuentes.md`.

Los cultivos dependen de la región piloto, que es un supuesto mientras el reto no confirme la región (decisión 11, HU-002). La lista de 7 se decidió el 11 de octubre de 2026 (decisión 12).

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo con lo que necesita y lo que aguanta, para saber si se da en una zona y evaluar sus ventanas de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Hay una ficha por cada uno de los 7 cultivos del MVP (papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia) y otra para el descanso, con `crop_id` en `snake_case` sin tildes (`crop_id`: `papa`, `arveja`, `haba`, `maiz`, `zanahoria`, `cebolla_bulbo`, `avena_vicia` y `descanso`; un `crop_id` es un cultivo con ficha propia, no una variedad)
  - [ ] Cada ficha trae, con fuente: altitud mínima, máxima y óptima; temperatura óptima y `heat_max_c`; rango de pH; familia (`family`); tipo de raíz (`root_type`); si fija nitrógeno (`fixes_nitrogen`); duración (`cycle_months` y los días de cada etapa en `crop_stages`, HU-142) y, si hay fuente, grados-día
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
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `catalog/rotation_rules.yaml` tiene `version`, una sección `sources:` con el mismo formato que la de `catalog/crops.yaml` y una lista `rules:`. Cada regla trae las columnas de `rotation_rules` del contrato: `rule_id`, `kind` (`filter` o `health`), `criterion` (nulo en un `filter`), `condition_type` de la lista cerrada («Reglas de rotación como datos»), `params`, `levels` (nulo en un `filter`), `reason_template` y `source_id`
  - [ ] Como mínimo: una regla `filter` `same_family_consecutive` (no repetir familia en ciclos seguidos) y, por cada criterio de `soil_health`, una regla `health` con el `condition_type` que le da el contrato y los cortes de cada nivel: `nitrogen` (`legume_cycles`), `organic_carbon` (`organic_matter_cycles`), `soil_cover` (`covered_months_pct`), `pest_break` (`family_return_min_cycles`) y `erosion` (`bare_months_on_slope`, que cruza la pendiente con los meses de suelo descubierto; decisión 14). Son las que usan HU-081, HU-212 y HU-224
  - [ ] **Sin fuente no hay regla** (R1, R8): si para un criterio no se encuentra una fuente que dé sus cortes, la regla no se escribe, ni con números «típicos» ni con la fuente `ejemplo`. Ese criterio queda `insufficient_data` en el motor (`specs/02-contratos.md`: «Un criterio de `soil_health` sin una regla `health` con fuente es `insufficient_data`»), la nota de esta HU dice qué se buscó y se avisa al equipo, porque deja el criterio sin nivel en la demo
  - [x] `params.family` y `params.families` usan el valor exacto de `family` de las fichas de `catalog/crops.yaml` (`Solanaceae`, `Leguminosae`, `Gramineae`, `Umbelliferae`, `Alliaceae`), con la misma mayúscula
  - [x] En una regla `family_return_min_cycles` de `kind = health`, `params.min_cycles` es igual a `levels.favorable`
  - [x] En `organic_matter_cycles`, con el carbono bajo, el corte `favorable` pide al menos un ciclo de abono verde o descanso (HU-212: con carbono bajo, una estrategia sin abono verde ni descanso no es `favorable`). La forma de `levels` de esta regla es la de `specs/02-contratos.md` (`low` y `normal`, decisión 16)
  - [x] `uv run python -m pipeline.build` lee `catalog/rotation_rules.yaml`, une su sección `sources:` a la tabla `sources`, publica `data/published/rotation_rules.parquet` con el esquema de `pipeline/schema.py` y lo anota en `manifest.json` (`tables.rotation_rules`, con sus filas)
  - [x] El build falla, con un mensaje que nombra la regla, si: `kind` no es `filter` ni `health`; `condition_type` no está en la lista cerrada o no admite ese `kind`; `criterion` no es nulo en un `filter`, o en un `health` no es el criterio que el contrato le da a su `condition_type`; `params` o `levels` no son un objeto con las llaves de su tipo (se publican como JSON válido); `levels` falta en un `health` o sobra en un `filter`; los cortes no son coherentes (`moderate` mayor que `favorable`, salvo en `bare_months_on_slope`, donde son máximos y va al revés; `moderate == favorable` vale y quiere decir «sin franja intermedia», aprobado por Felipe el 10 nov 2026); `source_id` vacío o que no está en `sources`; un mismo `source_id` definido en los dos catálogos con datos distintos; un `rule_id` repetido; o una familia de `params` que no está en ninguna ficha. Hay una prueba por cada caso en `tests/pipeline/`
  - [x] **Matriz de pares** (prueba en `tests/pipeline/`): con `catalog/rotation_rules.yaml` y las familias de `catalog/crops.yaml`, arma la matriz de 8 × 8 (los 7 cultivos y el descanso como ciclo anterior y como ciclo siguiente, con la diagonal, porque entre `previous_crop_ids` y el primer ciclo sí se puede repetir un cultivo) y, para cada par, lista las reglas `filter` que se evalúan y si lo excluyen. El resultado coincide con la tabla «Matriz esperada» de abajo. Si cambian las familias o los filtros, la tabla se actualiza en esta HU en el mismo cambio. HU-081 usa la misma tabla para probar el motor
  - [x] La rotación de referencia con fuente (papa → avena → arveja, Agrosavia en Tibaitatá, mapeada a `papa` → `avena_vicia` → `arveja`; nota 2) no viola ninguna regla `filter`: prueba
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R1, R3, R5, R8
- **Contrato que toca:** `rotation_rules`, `sources`, `manifest.json` (`rules_version`) y `crops` (`secondary_families`). Los cambios 1 a 4 de la propuesta de contrato (`crops.secondary_families`, qué familias cuenta cada condición, la forma de `levels` de `organic_matter_cycles`, el valor exacto de la familia, `min_cycles` igual a `levels.favorable`, el descanso como suelo descubierto y la versión compartida de los catálogos) están **aprobados el 9 de noviembre de 2026 (decisión 16)** por Felipe. Ya están en `specs/02-contratos.md`
- **Matriz esperada** (familias de `catalog/crops.yaml` 0.1.0 y solo el filtro `same_family_consecutive` por `family`; X = excluye, · = pasa; filas = ciclo anterior, columnas = ciclo siguiente):

  | anterior \ siguiente | `papa` | `arveja` | `haba` | `maiz` | `zanahoria` | `cebolla_bulbo` | `avena_vicia` | `descanso` |
  |---|---|---|---|---|---|---|---|---|
  | `papa` (Solanaceae) | X | · | · | · | · | · | · | · |
  | `arveja` (Leguminosae) | · | X | X | · | · | · | · | · |
  | `haba` (Leguminosae) | · | X | X | · | · | · | · | · |
  | `maiz` (Gramineae) | · | · | · | X | · | · | X | · |
  | `zanahoria` (Umbelliferae) | · | · | · | · | X | · | · | · |
  | `cebolla_bulbo` (Alliaceae) | · | · | · | · | · | X | · | · |
  | `avena_vicia` (Gramineae) | · | · | · | X | · | · | X | · |
  | `descanso` (sin familia) | · | · | · | · | · | · | · | · (*) |

  (*) Ninguna regla `filter` excluye descanso tras descanso; dentro de una estrategia no es candidata (`specs/01-reglas.md`, «Cómo se arman», paso 0). Entre `previous_crop_ids` y el primer ciclo, ver la contradicción 3 de las notas.

- **Notas:** Punto de partida con fuente: las rotaciones papa-avena-arveja evaluadas por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`). Cambiada el 11 de octubre de 2026 (decisión 12). **Precisada el 9 de noviembre de 2026** (especificador), con estas decisiones y supuestos:
  1. **Familia en `params`.** Valor exacto de `family` de la ficha, con la misma mayúscula; una familia que no está en ninguna ficha hace fallar el pipeline. El contrato ya usa `"Solanaceae"` (decisión 16); falta corregir el ejemplo `ejemplo_papa_espera` de `pipeline/examples.py` (código, fuera de esta spec).
  2. **La avena con vicia tiene dos familias.** Decidido (decisión 16): la ficha guarda `family: Gramineae` y `secondary_families: [Leguminosae]`; `same_family_consecutive` compara solo `family`, y `family_return_min_cycles` (`pest_break`) cuenta `family` y `secondary_families`. Si la vicia contara en el filtro, avena con vicia → arveja quedaría excluida y la única rotación con fuente no pasaría. La fuente de que la vicia (*Vicia sativa*) es Leguminosae es FAO EcoCrop (<https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id=238003>, ya en el catálogo como `fao_ecocrop`). **En Tibaitatá se sembró avena sola**, no avena con vicia (Agrosavia, `agrosavia_tibaitata_2022`, p. 3-4: *Avena sativa* forrajera Cayuse, sin vicia). La rotación de referencia (T2: papa → avena → arveja) se mapea a `papa` → `avena_vicia` → `arveja` por ser `avena_vicia` lo más cercano del catálogo, y se dice en la prueba y en la explicación de la referencia: el ensayo no respalda el aporte de la vicia, solo la secuencia. Para el filtro da igual (las dos son `Gramineae` en `family`); para `pest_break` y `nitrogen`, `avena_vicia` cuenta la vicia, que el ensayo no sembró.
  3. **El descanso** (`kind = fallow`, sin `family`):
     - `same_family_consecutive`: decidido por el contrato («dos ciclos seguidos»): un par con descanso nunca viola el filtro y el descanso es un ciclo que separa; papa → descanso → papa pasa el filtro (y la evalúa `pest_break`).
     - `family_return_min_cycles`: supuesto por confirmar con fuente; opción recomendada: el descanso cuenta como un ciclo sin esa familia.
     - `covered_months_pct` y `bare_months_on_slope`: decidido por el contrato (decisión 16): el descanso cuenta como suelo **descubierto** hasta que una fuente diga otra cosa. La «cobertura natural» de su ficha es una nota del dibujo (`agrosense_diseno`, que la ficha misma dice que «no es un dato agronómico»), y HU-224 ya supone «descanso desnudo».
     - `organic_matter_cycles`: decidido por el contrato: el descanso cuenta, igual que el abono verde (`kind = cover`). Los «cultivos que dejan residuos» que nombran `specs/01-reglas.md` y HU-212 no cuentan: no hay campo en la ficha ni en la condición del contrato.
     - **Contradicción, dependencia de HU-063 y HU-213:** `specs/01-reglas.md` («Cómo se arman», paso 1) y HU-213 dicen «un descanso dura lo que dice su ficha», pero la ficha de `descanso` dice que «su duración la elige quien arma la estrategia» y no trae días, y `POST /api/v1/rotations` no tiene un campo para esa duración. Sin duración, `soil_cover` y `erosion` no se pueden calcular en una estrategia con descanso (quedarían `insufficient_data`, R1) y el ciclo siguiente no tiene fecha. No se resuelve aquí.
     - Hueco menor para HU-081: el paso 0 prohíbe dos descansos seguidos dentro de la estrategia, pero no dice nada de un descanso en `previous_crop_ids` seguido de un primer ciclo de descanso.
  4. **Forma de `levels` de `organic_matter_cycles`.** Decidida (decisión 16): `{"low": {"favorable": n, "moderate": m}, "normal": {"favorable": n, "moderate": m}}`, las dos llaves obligatorias; `low` aplica cuando `soc_g_kg` es menor que `params.soc_low_g_kg`; `low.favorable` es al menos 1. Supuesto por confirmar: se compara `soc_g_kg` (el valor central) y la razón dice el rango `soc_p05`–`soc_p95` (R10). La forma está decidida, pero la regla no está escrita: falta la fuente de los números (nota 9).
  5. **`family_return_min_cycles`.** Opción recomendada para el MVP: solo `kind = health` (`pest_break`); como `filter`, solo si una fuente la da como restricción obligatoria (R3 excluye por regla con fuente). Una regla por familia con fuente; como mínimo `Solanaceae` (papa). **Espera de la papa** (9 de noviembre de 2026, decidido por Juan Cárdenas, opción b; lo confirma Felipe en la revisión cruzada de esta HU porque usa la regla «sin franja intermedia» del contrato, todavía pendiente): `papa_espera` lleva `params {family: Solanaceae, min_cycles: 4}` y `levels {favorable: 4, moderate: 4}`. Motivo: la FAO 2008 (p. 19) dice «rotations of three or more years»; con dos ciclos por año en el altiplano son unos 4 ciclos de otras familias. Con `moderate == favorable` no hay franja intermedia (`favorable` desde 4 ciclos, `unfavorable` por debajo, nunca `moderate`), así que ya no queda un caso intermedio sin fuente (R8). Supuesto declarado: dos ciclos por año (se pide una fuente andina que lo diga en ciclos). Se agrega además el filtro `papa_seguida` (`same_family_consecutive`, `families: [Solanaceae]`) con fuente del ICA. El criterio de coherencia de los cortes del build («`moderate` por debajo de `favorable`») admite la igualdad cuando se confirme la regla del contrato. **Consecuencia para HU-212:** en una estrategia de 3 ciclos, si la papa vuelve dentro de la estrategia (a lo sumo 1 ciclo de otras familias en medio), `pest_break` es `unfavorable`; cómo se cuenta la espera con `previous_crop_ids` lo decide HU-212. Supuestos por confirmar en HU-212: una familia sin regla no se evalúa y va a las limitaciones; el nivel de `pest_break` es el peor de las reglas que aplican; la historia es la de `previous_crop_ids` (hasta 3) más la estrategia, y sin cultivos anteriores la razón lo dice.
  6. **Pares.** El criterio «Cubren todos los pares» se reemplazó por la prueba de la matriz y la de la rotación de referencia.
  7. **Fuentes y versión.** Las fuentes de las reglas van en la sección `sources:` de `catalog/rotation_rules.yaml`, con el formato de `catalog/crops.yaml`; una regla puede citar una fuente ya definida en `crops.yaml` sin repetirla. Decidido (decisión 16): los dos catálogos llevan la misma `version`, que es `rules_version` del manifiesto, y el build falla si difieren. La forma del manifiesto no cambia.
  8. **Sin regla con fuente, `insufficient_data`:** queda como criterio de aceptación; nadie rellena un corte.
  9. **Cuatro criterios de `soil_health` sin regla con fuente** (9 de noviembre de 2026, producto-agro; cabecera de `catalog/rotation_rules.yaml`, versión 0.1.0). El catálogo trae tres reglas: `familia_seguida` (`filter`, `same_family_consecutive`, Penn State Extension), `papa_seguida` (`filter`, ICA) y `papa_espera` (`health`, `pest_break`, FAO 2008, p. 19; 4 ciclos, nota 5). La segunda búsqueda (9 nov 2026) encontró con fuente el umbral de materia orgánica baja del altiplano (< 5 %, Castro, CEVIPAPA 2005, tabla 3; con el factor de Van Bemmelen 1,724 son 29 g/kg de carbono orgánico, aprobado por Felipe el 10 nov 2026) y la pendiente desde la que aplica la erosión (12 %, IGAC 2021, p. 15; «a partir de», es decir `>=`, aprobado por Felipe el 10 nov 2026), pero no los cortes. **El 10 nov 2026 el equipo decidió fijar los cortes que faltan como criterio propio registrado** (fuente propia en `sources`, con su razonamiento); la propuesta de números la prepara producto-agro y la aprueba el equipo antes de escribir las reglas. Para los otros cuatro criterios se buscó fuente y no se encontró un corte, así que **no se escribió la regla**:
     - `nitrogen` (`legume_cycles`): ninguna fuente revisada da cuántos ciclos de leguminosa hacen falta.
     - `organic_carbon` (`organic_matter_cycles`): falta una fuente para `soc_low_g_kg` (desde cuánto carbono orgánico el suelo es bajo) y para los cortes de ciclos. (La forma de `levels`, que también faltaba, ya está decidida: nota 4.)
     - `soil_cover` (`covered_months_pct`): la FAO da un 30 % de cobertura de la superficie al sembrar, que es otra variable (cobertura de la superficie, no meses cubiertos): no sirve para este corte.
     - `erosion` (`bare_months_on_slope`): no se encontró fuente para la pendiente desde la que aplica (`slope_pct_from`) ni para los meses descubiertos. Candidatas que nombra HU-224: el factor C de la ecuación universal de pérdida de suelo y las guías de conservación de suelos de la FAO.

     **En la demo, esos cuatro criterios salen `insufficient_data`** con nivel nulo (R1): no se pintan como malos ni se rellenan, y van a las limitaciones. Mientras tanto, el criterio `soil` del ranking de estrategias sale solo de `pest_break` («su promedio entre los disponibles», `specs/01-reglas.md`), y si `pest_break` tampoco tiene nivel, el criterio `soil` no califica (R1). **Hay una segunda búsqueda de fuentes en curso** (producto-agro). Aviso al equipo: si la segunda búsqueda no encuentra nada, la salud del suelo de la demo tiene un solo criterio con nivel, y solo cuando la papa está en la estrategia o en los cultivos anteriores (la única regla de `pest_break` es la de `Solanaceae`; nota 5).
  - `root_type`: las fichas lo dejan «Pendiente de HU-062 (alternar tipo de raíz)», pero la lista cerrada no tiene una condición de tipo de raíz. Queda fuera del MVP: `root_type` sigue nulo y no hay regla (agregarla sería un cambio de contrato).
  - Tamaño: pasó de M a L por la validación del build y las dos pruebas. Si se pasa de L, se divide en «las reglas con fuente» (datos) y «la validación y publicación en el build».

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
