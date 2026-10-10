---
id: EP-01
titulo: "Contratos congelados y datos de ejemplo"
prioridad: "P0"
fase: "Fase 0 y hora 0"
rol: "Motor y API (con Web)"
agente: motor-api
subsistemas: "D4, M6, W6"
depende_de: "EP-00"
reglas: "R4, R5, R7"
estado: pendiente
---

# EP-01 · Contratos congelados y datos de ejemplo

**Resultado esperado:** Datos, motor y web pueden avanzar en paralelo contra un contrato estable.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Fase 0 y hora 0 |
| Rol responsable | Motor y API (con Web) |
| Agente sugerido | `motor-api` (ver `.claude/agents/`) |
| Subsistemas | D4, M6, W6 (ver `specs/03-sistemas.md`) |
| Depende de | EP-00 |
| Reglas de diseño que aplican | R4, R5, R7 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-011 · Esquema de las tablas publicadas

- **Historia:** Como desarrollador, quiero el esquema de las tablas publicadas, para que pipeline y motor trabajen en paralelo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Llaves, tipos y unidades documentados
  - [ ] Un Parquet de ejemplo por tabla, rotulado como ejemplo
  - [ ] Unicidad de llaves comprobada
- **Notas:** Se hace en la fase 0.

### HU-012 · OpenAPI con ejemplos de cada estado

- **Historia:** Como desarrollador web, quiero el OpenAPI con ejemplos de cada estado, para construir la interfaz sin esperar al motor.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] OpenAPI generado de los modelos Pydantic
  - [ ] Tipos TypeScript generados
  - [ ] Ejemplos de `available`, `insufficient_data` y error 422
- **Notas:** —

### HU-013 · Respuestas simuladas (MSW)

- **Historia:** Como desarrollador web, quiero respuestas simuladas, para desarrollar contra casos realistas.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] MSW responde todos los endpoints P0
  - [ ] Se puede forzar cada estado desde la interfaz de desarrollo
- **Notas:** —
