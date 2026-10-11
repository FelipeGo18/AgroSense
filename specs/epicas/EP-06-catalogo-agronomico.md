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
estado: pendiente
---

# EP-06 · Catálogo agronómico con fuentes

**Resultado esperado:** Fichas de 6 a 8 cultivos, de los abonos verdes y del descanso, y reglas de rotación como datos, cada una con fuente. Cada ficha dice lo que el cultivo necesita y lo que aguanta (agua, altitud, temperatura, helada y pH), con su rango óptimo y sus límites absolutos: contra eso se califica cada ventana de siembra (HU-196). Además, los pesos por defecto de cada señal, con quién los definió y por qué.

La ficha no dice en qué época se siembra: eso lo responde el motor, ventana por ventana, con la historia de la zona.

Los cultivos dependen de la región piloto, que es un supuesto mientras el reto no confirme la región (decisión 11, HU-002).

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo con lo que necesita y lo que aguanta, para saber si se da en una zona y evaluar sus ventanas de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Todos los campos del contrato llenos; los que el contrato permite nulos (`altitude_min_m`, `altitude_max_m`, `heat_max_c`, los límites de las curvas `temp_*`, `rain_*` y `altitude_opt_*`, pH, `base_temp_c`, `gdd`) quedan nulos solo si no hay fuente, y se anota por qué
  - [ ] `altitude_min_m` y `altitude_max_m` (rango en que se da el cultivo) con fuente: de ahí sale la aptitud en la zona (HU-191)
  - [ ] `heat_max_c` (temperatura máxima que aguanta) con fuente: de ahí sale la señal de calor (HU-190)
  - [ ] La ficha no tiene ningún campo de épocas de siembra
  - [ ] Fuente por campo; ningún valor «típico» sin cita (R8)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Contrato que toca:** tabla `crops`
- **Notas:** Sin el rango de altitud con fuente, la aptitud queda en «datos insuficientes» y no filtra; sin `heat_max_c`, la señal de calor queda en «datos insuficientes» (`docs/riesgos.md`). Los rangos óptimos para las curvas son HU-199. Fuentes por confirmar (`docs/fuentes.md`). Cambiada el 11 de octubre de 2026.

### HU-199 · Límites óptimos y absolutos de cada cultivo

- **Historia:** Como motor, quiero el rango óptimo y los límites absolutos de temperatura, lluvia y altitud de cada cultivo, con fuente, para calificar cada señal de 0 a 100 con una curva por cultivo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Por cultivo: temperatura óptima (mínima y máxima) y absoluta (mínima y máxima), lluvia óptima y absoluta, y altitud óptima y absoluta, en las columnas de `crops` del contrato (`temp_min_c`, `temp_opt_min_c`, `temp_opt_max_c`, `rain_min_mm`, `rain_opt_min_mm`, `rain_opt_max_mm`, `rain_max_mm`, `altitude_opt_min_m` y `altitude_opt_max_m`; los absolutos de altitud y de calor son `altitude_min_m`, `altitude_max_m` y `heat_max_c`, de HU-061)
  - [ ] Cada valor con su fuente en `sources` (R8). La candidata es FAO EcoCrop, **por confirmar**: se verifica el acceso, la licencia, la especie o variedad que describe y la unidad de cada campo antes de usarla
  - [ ] Si hay una fuente local (por ejemplo, fichas técnicas de Agrosavia) que difiere de EcoCrop, se anotan las dos en las notas de la ficha y se dice cuál se usa y por qué
  - [ ] Sin fuente, el campo queda nulo y la señal que lo necesita queda en «datos insuficientes» (R1); nunca un valor «típico»
  - [ ] Validación: el óptimo cae dentro de los límites absolutos; si no, el catálogo no se publica
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R1, R8
- **Contrato que toca:** tabla `crops`
- **Notas:** Decisión 10. Las columnas ya están en el contrato (`specs/02-contratos.md`, tabla `crops`). Los `rain_*` son la lluvia anual que pide el cultivo: sirven de referencia y de contraste y no entran a la curva de una ventana; la señal de agua sale del balance hídrico, con cortes en `thresholds.yaml` (`specs/01-reglas.md`, «Cómo se califica cada señal»). El rango óptimo de altitud se usa para la nota informativa de aptitud (`suitability.score`, HU-191); la aptitud se decide solo con el rango absoluto (`specs/01-reglas.md`, «Aptitud del cultivo en la zona»).

### HU-198 · Pesos por defecto con su porqué

- **Historia:** Como equipo, queremos fijar el peso por defecto de cada señal con quién lo definió y por qué, para que el criterio de AgroSense sea explicable y se pueda revisar.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `weights.yaml` tiene un peso entero de 0 a 5 para cada señal del P0 (`water`, `frost`, `heat`, `soil`, `supply`, `market`), con número de versión
  - [ ] Cada peso lleva, en el mismo archivo o en una nota enlazada, quién lo definió, cuándo y su porqué en una frase
  - [ ] El porqué se presenta como criterio del equipo, no como dato agronómico: no cita una fuente que no lo dice (R5, R8)
  - [ ] Ningún peso por defecto es 0: el criterio de AgroSense mira las seis señales
  - [ ] Los pesos los propone el rol Producto y agro y los aprueba el dueño del producto; el cambio queda en `docs/registro-de-decisiones.md`
  - [ ] El panel «¿Cómo funciona y de dónde sale esto?» (HU-122) muestra los pesos por defecto y su porqué
- **Reglas que aplican:** R4, R5, R8
- **Contrato que toca:** `weights` y `overall_default` de la respuesta de diagnóstico; `priorities` de `/calendar`
- **Notas:** Decisión 10. Los valores no están decididos: no hay evidencia que fije cuánto pesa cada señal (`docs/riesgos.md`). Se revisan si aparece evidencia, por ejemplo con agricultores en la fase 0. El mecanismo de carga y validación del archivo es HU-075.

### HU-062 · Reglas de rotación como datos

- **Historia:** Como motor, quiero las reglas de rotación como datos, para filtrar y puntuar secuencias sin cambiar código.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Como mínimo: no repetir familia, bonificar leguminosas y alternar tipo de raíz
  - [ ] Cada regla con tipo, condición, efecto y fuente

### HU-063 · Suelo, heladas y abonos verdes en el catálogo

- **Historia:** Como motor, quiero el rango de pH de cada cultivo, sus etapas sensibles a la helada y al calor y los abonos verdes y el descanso como opciones de rotación, para evaluar suelo, heladas y calor y recomendar rotaciones que recuperen el suelo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `kind`, `ph_min`, `ph_max`, `ph_opt_min` y `ph_opt_max` en cada ficha, con fuente; nulos si no hay fuente. Son los límites absolutos y óptimos de la curva de la señal de suelo (HU-196)
  - [ ] `frost_sensitive` y `heat_sensitive` por etapa en `crop_stages`, con fuente
  - [ ] Al menos un abono verde de la región (por ejemplo, avena con vicia) y el descanso, con sus reglas de rotación
  - [ ] Reglas de suelo con fuente: exclusión por pH fuera de rango y bonificación de abonos verdes, descanso y leguminosas con carbono orgánico bajo (umbral con fuente)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Notas:** Punto de partida: las rotaciones papa-avena-arveja evaluadas por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`). Ese punto de partida es de la región piloto supuesta en Colombia (decisión 11).
