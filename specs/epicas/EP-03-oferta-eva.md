---
id: EP-03
titulo: "Dataset de oferta publicado"
prioridad: P0
fase: [Evento]
rol: "Datos"
agentes: [datos]
subsistemas: [D1, D2, D3, D4]
depende_de: [EP-00, HU-011]
reglas: [R1, R5, R7, R8]
estado: pendiente
---

# EP-03 · Dataset de oferta publicado

**Resultado esperado:** La tabla `supply_semester` de la región, validada y con indicadores de oferta, con su fuente y lo que cubre. En el P1, otras fuentes del mismo indicador para contrastar, mostradas juntas y nunca mezcladas.

**Este es el único sitio donde vive el semestre.** La decisión se evalúa sobre ventanas de siembra (`specs/01-reglas.md`); EVA publica por semestre y por eso la oferta se guarda así. El motor lee el semestre en que cae la fecha de siembra (HU-072) y la respuesta lo dice en `window.supply_semester`. Ninguna otra tabla ni endpoint usa el semestre.

**Varias fuentes, ninguna única verdad (decisión 11).** Un indicador puede venir de varias fuentes: la estadística oficial del país, FAOSTAT, reportes descargados de portales públicos y las siembras registradas en AgroSense. `sources.yaml` dice cuál calcula la señal en cada región; las demás se muestran al lado para contrastar.

**Región piloto:** EVA, el código DIVIPOLA y los semestres A y B son de Colombia. La región está confirmada desde el 28 de octubre de 2026: Boyacá y Cundinamarca (HU-002). Lo propio de Colombia vive en el adaptador de EVA; el modelo no lo supone fuera de él (R7).

## Historias de usuario

### HU-031 · Datos de EVA normalizados por DIVIPOLA

- **Historia:** Como motor, quiero los datos de EVA normalizados por DIVIPOLA, cultivo, año y semestre, para evaluar la oferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Script reproducible desde el CSV crudo
  - [x] Filas rechazadas reportadas con motivo
  - [x] Datos preliminares marcados
  - [x] `semester` toma solo `A` (enero a junio) o `B` (julio a diciembre); la correspondencia con los periodos de EVA queda documentada (supuesto por confirmar en HU-001)
  - [x] Entrada de EVA en `sources` con `coverage` (el país y los municipios que cubre); `sources.yaml` la nombra como la fuente que calcula `supply` en la región piloto
- **Reglas que aplican:** R7, R8
- **Contrato que toca:** `supply_semester`, `sources`
- **Hecho (14 de noviembre de 2026):**
  - **La fuente:** «Evaluaciones Agropecuarias Municipales – EVA. 2019 - 2025. Base Agrícola» de la UPRA en datos.gov.co (`uejq-wxrr`, CC BY-SA 4.0, actualizada el 28 de agosto de 2026). Trae el DIVIPOLA de 5 dígitos, el código del cultivo de la clasificación EVA y el periodo. `pipeline/sources/eva.py` baja las filas de Boyacá y Cundinamarca (33 263, todos los cultivos) a `data/raw/eva/eva.csv` y las normaliza desde ahí, sin red.
  - **Los semestres:** el metadato de `periodo` dice «Periodo de siembra (Año y semestre para transitorios) y solo año para los cultivos permanentes»: `2024A` y `2024B` son las siembras del primero y del segundo semestre. Se toma A = enero a junio y B = julio a diciembre, el supuesto del contrato, que confirma HU-001. Una fila de un cultivo del MVP sin semestre se descarta (`no_semester`).
  - **Las filas descartadas** se cuentan por motivo en la línea `source_read` de la terminal: fuera de la región, municipio que no está en `municipalities`, sin semestre, valor que no es número, valor negativo, sin ningún dato y repetida. Las de cultivos que no son del MVP se cuentan aparte (`other_crop`). Ninguna fila se pierde sin motivo. Con la descarga del 14 de noviembre no se descarta ninguna: 9120 filas de los cultivos del MVP dan 8456 de `supply_semester` en 238 municipios.
  - **Preliminares:** la nota de EVA dice que «las cifras de los dos últimos años son susceptibles de modificación»: `preliminary` es verdadero en los dos últimos años de la descarga (hoy 2024 y 2025).
  - **Los cultivos:** `pipeline/eva_crops.yaml` dice qué códigos de EVA son cada cultivo del catálogo, como `sipsa_crops.yaml` con los precios. El maíz suma sus cuatro códigos en grano seco (amarillo y blanco, tecnificado y tradicional); la papa es «todas las variedades», sin la criolla; el abono verde y el descanso no tienen oferta y dicen por qué. Si una de las filas sumadas no trae un valor, el total de ese valor queda nulo (R1); con área cosechada 0, el rendimiento del total es 0, como publica EVA con un solo código. Aprobado por Haider el 15 de noviembre de 2026 (PR #117): los cuatro maíces en grano sumados y sin papa criolla.
  - **Lo que cambió en 2022:** desde 2022, según la nota de EVA, el área cosechada, la producción y el rendimiento son las cosechas efectivas de cada semestre (antes, las de sus siembras): el área cosechada de un semestre puede pasar a la sembrada. No se descarta y la entrada de `sources` lo dice. El área sembrada, la que usa la oferta, significa lo mismo todos los años.
  - **`quality`:** `partial` cuando EVA no trae alguno de los cuatro valores (con la descarga del 15 de noviembre, ninguna: las 29 de antes eran el 0 ÷ 0 del maíz sumado sin cosecha, revisión del PR #117); desde HU-032 también con menos de tres semestres anteriores. `planted_change_pct` y `dept_share_pct` los calcula HU-032.
  - **Sin la caché de EVA** se publica lo demás y el log dice `source_missing`; si datos.gov.co falla en `--descargar`, `source_skipped`. `catalog/sources.yaml` 1.5.0 saca `eva` de `planned`.

### HU-032 · Variación del área sembrada y participación departamental

- **Historia:** Como motor, quiero la variación del área sembrada y la participación departamental, para detectar sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Definición escrita de cada indicador (abajo, en `pipeline/sources/eva.py`, `indicators()`, y en `specs/02-contratos.md`)
  - [x] Valores comprobados a mano en 2 municipios (Villapinzón y Duitama, abajo)
  - [x] Calidad `partial` cuando faltan semestres previos (menos de tres semestres anteriores con dato)
- **Definiciones (HU-032; propuestas de Datos, aprobadas por Felipe el 15 de noviembre de 2026 en el PR #159):**
  - **`planted_change_pct`:** cuánto cambió el área sembrada del municipio, cultivo y semestre frente al promedio del **mismo semestre de los tres años anteriores** (para 2025B, 2022B, 2023B y 2024B; una ventana fija, no «los últimos tres con dato»), en %: (sembrada − promedio) / promedio × 100, con un decimal. Solo cuentan los semestres con dato: un año sin fila es sin dato (R1), no 0 ha, y una fila sin área sembrada (por ejemplo, un maíz con un código sin área) tampoco cuenta. Sin ningún semestre anterior con dato, o con un promedio de 0 ha (no se puede dividir), es nulo. Con menos de tres semestres anteriores, la fila es `partial` (contrato).
  - **`dept_share_pct`:** qué parte del área sembrada del departamento en ese cultivo y semestre es del municipio, en %, con dos decimales. El departamento son los dos primeros dígitos del DIVIPOLA (Boyacá 15, Cundinamarca 25; la región tiene los dos departamentos completos). El total suma los municipios con fila: es la parte **entre los que reportan**, porque un municipio sin fila es sin dato. Si uno de ellos no trae el área sembrada, o el total es 0, es nulo (R1). En un departamento, cultivo y semestre con todas las participaciones, suman 100 (el build lo revisa).
  - **Cómo leerlos:** EVA repite el área del mismo semestre del año anterior en muchas filas (el 27 %; `docs/investigacion-decisiones.md`, 5f): ahí la variación contra ese año es 0 aunque nadie la haya medido. Una variación grande sobre un promedio pequeño (de 1 a 33 ha es +3200 %) es real, pero dice poco. La oferta se muestra sin calificar (decisión 17): ninguno de los dos indicadores tiene un corte de «mucho» o «poco».
- **Con la descarga del 15 de noviembre de 2026 (dataset 2026.11.25):** de 8456 filas, 4240 tienen sus tres semestres anteriores, 2786 tienen uno o dos (`partial`) y 1430 ninguno (2019 y las combinaciones que aparecen después; variación nula y `partial`). 168 tienen promedio anterior de 0 ha (variación nula). La participación no queda nula en ninguna fila. 4216 filas son `partial`.
- **Comprobación a mano** (papa, código 1080701, desde `data/raw/eva/eva.csv`; la prueba `test_comprobacion_a_mano_en_dos_municipios_del_dataset_publicado` la repite contra lo publicado):
  - **Villapinzón (25873), 2025A:** 12 000 ha. 2022A, 2023A y 2024A: 8000, 9000 y 10 000 ha (promedio 9000). Variación: (12 000 − 9000) / 9000 = **+33,3 %**. Cundinamarca sembró 39 128,65 ha de papa en 2025A: 12 000 / 39 128,65 = **30,67 %**.
  - **Duitama (15238), 2024B:** 10 ha. 2021B, 2022B y 2023B: 12, 25 y 15 ha (promedio 17,33). Variación: (10 − 17,33) / 17,33 = **−42,3 %**. Boyacá sembró 23 480,4 ha de papa en 2024B: 10 / 23 480,4 = **0,04 %**.
- **Notas:** **Cómo se leen los vacíos de EVA** (Haider, 15 de noviembre de 2026, PR #117; registro de decisiones): un municipio sin fila para un cultivo en un semestre es **sin dato** (R1), no 0 ha, porque no se sabe si no se sembró o no se reportó; una fila con `planted_ha = 0` sí es 0, porque EVA lo dice (283 filas); la variación del área sembrada se calcula solo con los semestres que tienen dato y, si no alcanzan, es `insufficient_data`. Desde 2022 el área cosechada puede pasar a la sembrada (1449 filas): la oferta nunca usa el área cosechada.

### HU-200 · Siembras registradas en AgroSense como dato de oferta

- **Historia:** Como agricultor, quiero ver cuánto de mi cultivo están sembrando ahora otros usuarios de AgroSense en mi municipio, junto a la estadística oficial, para contrastar un dato reciente con uno oficial que llega con retraso.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La API cuenta, por `municipality_id` y `crop_id`, las temporadas en curso (sin `harvest_date` ni `deleted_at`) de cuentas `farmer`, y suma su `area_ha`. Quedan fuera las cuentas `admin` y `developer` y los datos simulados (R5)
  - [ ] Solo se muestra si hay **al menos 5 cuentas distintas** con ese cultivo en ese municipio; con 4 o menos, la fuente no aparece (R9)
  - [ ] Solo totales: nunca un lote, un usuario, un polígono ni un área individual
  - [ ] Aparece en `signals.supply.sources` con `source_id` `agrosense`, su valor y `used = false`, salvo que `sources.yaml` diga otra cosa para la región; nunca se mezcla con la fuente oficial (R1, R8)
  - [ ] La API le pasa el total al motor; el motor no lee la base de datos (R6)
  - [ ] Los totales se toman de un corte diario versionado, para que el mismo cálculo dé el mismo resultado (R4)
  - [ ] La razón dice la fecha del corte y que son siembras registradas por usuarios, no una estadística oficial
  - [ ] Los endpoints de cálculo siguen sin guardar los datos de la finca ni quién consultó (R9): leer los totales no escribe nada
  - [ ] Prueba: con 4 cuentas no aparece; con 5, aparece el total y ningún dato individual
- **Reglas que aplican:** R1, R4, R5, R6, R8, R9
- **Contrato que toca:** `signals.supply.sources`; `seasons`, `lots`, `users`; entrada `agrosense` en `sources`
- **Notas:** Decisión 11. **Por qué P1:** (1) en la demo no habrá 5 cuentas reales por municipio y cultivo, así que la fuente no aparecería nunca; (2) es un dato vivo de PostgreSQL y no del dataset versionado: por eso se toma de un corte diario versionado, para que el mismo cálculo dé el mismo resultado (R4); (3) usar las siembras de un agricultor para mostrar totales a otros es un uso nuevo de sus datos: el consentimiento versión 3 lo dice (HU-163). Las dos cosas están decididas en `specs/01-reglas.md` («Varias fuentes, ninguna única verdad»). La hace el rol Motor y API (está en esta épica porque es un dato de oferta).

### HU-201 · Fuentes de contraste para la oferta

- **Historia:** Como agricultor, quiero ver al lado de la estadística oficial lo que dicen otras fuentes públicas sobre la oferta de mi cultivo, para no depender de una sola.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un adaptador por fuente (D1), con caché, fecha de descarga y `coverage`: FAOSTAT (candidata, por confirmar) y los reportes descargados de portales públicos que el equipo elija
  - [ ] Cada fuente queda en `sources` con lo que cubre: país, departamento o municipio, y periodo. Una fuente nacional nunca se presenta como dato del municipio
  - [ ] Se muestran juntas en `signals.supply.sources`, cada una con su valor y su fecha; `used` dice cuál calculó la señal según `sources.yaml`
  - [ ] Nunca se promedian ni se rellena una con otra: si la fuente que calcula la señal no tiene dato, la señal es `insufficient_data` aunque otra sí lo tenga (R1)
  - [ ] Revisión: cada fuente nueva tiene licencia que permite su uso
- **Reglas que aplican:** R1, R5, R7, R8
- **Contrato que toca:** `sources`, `signals.supply.sources`
- **Notas:** Decisión 11. La llave de `supply_semester` ya incluye la fuente (`source_id`, `specs/02-contratos.md`). Queda abierto solo dónde van los valores que no son municipales, como los de FAOSTAT: lo deciden Haider o Felipe. Las fuentes se eligen cuando se confirme la región (HU-002).
