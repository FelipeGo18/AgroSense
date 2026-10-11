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

**Resultado esperado:** Fichas de 6 a 8 cultivos, de los abonos verdes y del descanso, y reglas de rotación como datos, cada una con fuente.

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo, para saber qué se puede sembrar y cuándo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Todos los campos del contrato llenos; los que el contrato permite nulos (pH, `base_temp_c`, `gdd`) quedan nulos solo si no hay fuente, y se anota por qué
  - [ ] Fuente por campo
  - [ ] Revisión cruzada por otro integrante

### HU-062 · Reglas de rotación como datos

- **Historia:** Como motor, quiero las reglas de rotación como datos, para filtrar y puntuar secuencias sin cambiar código.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Como mínimo: no repetir familia, bonificar leguminosas y alternar tipo de raíz
  - [ ] Cada regla con tipo, condición, efecto y fuente

### HU-063 · Suelo, heladas y abonos verdes en el catálogo

- **Historia:** Como motor, quiero el rango de pH de cada cultivo, sus etapas sensibles a la helada y los abonos verdes y el descanso como opciones de rotación, para evaluar suelo y heladas y recomendar rotaciones que recuperen el suelo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `kind`, `ph_min`, `ph_max`, `ph_opt_min` y `ph_opt_max` en cada ficha, con fuente; nulos si no hay fuente
  - [ ] `frost_sensitive` por etapa en `crop_stages`, con fuente
  - [ ] Al menos un abono verde de la región (por ejemplo, avena con vicia) y el descanso, con sus reglas de rotación
  - [ ] Reglas de suelo con fuente: exclusión por pH fuera de rango y bonificación de abonos verdes, descanso y leguminosas con carbono orgánico bajo (umbral con fuente)
  - [ ] Revisión cruzada por otro integrante
- **Reglas que aplican:** R3, R8
- **Notas:** Punto de partida: las rotaciones papa-avena-arveja evaluadas por Agrosavia en Tibaitatá (`docs/investigacion-decisiones.md`).
