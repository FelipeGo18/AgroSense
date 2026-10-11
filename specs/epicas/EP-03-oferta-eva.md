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

**Supuesto de la región piloto:** EVA, el código DIVIPOLA y los semestres A y B son de Colombia. El reto aún no confirma la región (HU-002). Lo propio de Colombia vive en el adaptador de EVA; el modelo no lo supone fuera de él (R7).

## Historias de usuario

### HU-031 · Datos de EVA normalizados por DIVIPOLA

- **Historia:** Como motor, quiero los datos de EVA normalizados por DIVIPOLA, cultivo, año y semestre, para evaluar la oferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Script reproducible desde el CSV crudo
  - [ ] Filas rechazadas reportadas con motivo
  - [ ] Datos preliminares marcados
  - [ ] `semester` toma solo `A` (enero a junio) o `B` (julio a diciembre); la correspondencia con los periodos de EVA queda documentada (supuesto por confirmar en HU-001)
  - [ ] Entrada de EVA en `sources` con `coverage` (el país y los municipios que cubre); `sources.yaml` la nombra como la fuente que calcula `supply` en la región piloto
- **Reglas que aplican:** R7, R8
- **Contrato que toca:** `supply_semester`, `sources`

### HU-032 · Variación del área sembrada y participación departamental

- **Historia:** Como motor, quiero la variación del área sembrada y la participación departamental, para detectar sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Definición escrita de cada indicador
  - [ ] Valores comprobados a mano en 2 municipios
  - [ ] Calidad `partial` cuando faltan semestres previos

### HU-200 · Siembras registradas en AgroSense como dato de oferta

- **Historia:** Como agricultor, quiero ver cuánto de mi cultivo están sembrando ahora otros usuarios de AgroSense en mi municipio, junto a la estadística oficial, para contrastar un dato reciente con uno oficial que llega con retraso.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La API cuenta, por `municipality_id` y `crop_id`, las temporadas en curso (sin `harvest_date` ni `deleted_at`) de cuentas `farmer`, y suma su `area_ha`. Quedan fuera las cuentas `admin` y `developer` y los datos simulados (R5)
  - [ ] Solo se muestra si hay **al menos 5 cuentas distintas** con ese cultivo en ese municipio; con 4 o menos, la fuente no aparece (R9)
  - [ ] Solo totales: nunca un lote, un usuario, un polígono ni un área individual
  - [ ] Aparece en `signals.supply.sources` con `source_id` `agrosense`, su valor y `used = false`, salvo que `sources.yaml` diga otra cosa para la región; nunca se mezcla con la fuente oficial (R1, R8)
  - [ ] La API le pasa el total al motor; el motor no lee la base de datos (R6)
  - [ ] La razón dice la fecha del corte y que son siembras registradas por usuarios, no una estadística oficial
  - [ ] Los endpoints de cálculo siguen sin escribir nada (R9)
  - [ ] Prueba: con 4 cuentas no aparece; con 5, aparece el total y ningún dato individual
- **Reglas que aplican:** R1, R4, R5, R6, R8, R9
- **Contrato que toca:** `signals.supply.sources`; `seasons`, `lots`, `users`; entrada `agrosense` en `sources`
- **Notas:** Decisión 11. **Por qué P1:** (1) en la demo no habrá 5 cuentas reales por municipio y cultivo, así que la fuente no aparecería nunca; (2) es un dato vivo de PostgreSQL y no del dataset versionado, así que dos consultas iguales pueden dar valores distintos (R4) y hace falta decidir cómo se versiona el corte; (3) usar las siembras de un agricultor para mostrar totales a otros es un uso nuevo de sus datos y el consentimiento debe decirlo (HU-163). Por decidir: si eso entra en la versión 3 del consentimiento o en una versión 4; cómo se fija el corte para que el resultado sea reproducible. La hace el rol Motor y API (está en esta épica porque es un dato de oferta).

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
- **Notas:** Decisión 11. **Bloqueada por el contrato:** la llave de `supply_semester` no incluye la fuente y FAOSTAT no es municipal ni semestral; hace falta una tabla o una columna para los valores de contraste. Lo deciden Haider o Felipe. Las fuentes se eligen cuando se confirme la región (HU-002).
