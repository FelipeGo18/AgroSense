---
id: EP-06
titulo: "Catálogo agronómico con fuentes"
prioridad: "P0"
fase: "Fase 0"
rol: "Producto y agro"
agente: producto-agro
subsistemas: "AG1–AG3"
depende_de: "HU-001"
reglas: "R3, R8"
estado: pendiente
---

# EP-06 · Catálogo agronómico con fuentes

**Resultado esperado:** Fichas de 6 a 8 cultivos y reglas de rotación como datos, cada una con fuente.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Fase 0 |
| Rol responsable | Producto y agro |
| Agente sugerido | `producto-agro` (ver `.claude/agents/`) |
| Subsistemas | AG1–AG3 (ver `specs/03-sistemas.md`) |
| Depende de | HU-001 |
| Reglas de diseño que aplican | R3, R8 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo, para saber qué se puede sembrar y cuándo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Todos los campos del contrato llenos
  - [ ] Fuente por campo
  - [ ] Revisión cruzada por otro integrante
- **Notas:** —

### HU-062 · Reglas de rotación como datos

- **Historia:** Como motor, quiero las reglas de rotación como datos, para filtrar y puntuar secuencias sin cambiar código.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Como mínimo: no repetir familia, bonificar leguminosas y alternar tipo de raíz
  - [ ] Cada regla con tipo, condición, efecto y fuente
- **Notas:** —
