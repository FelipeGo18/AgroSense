---
id: EP-13
titulo: "Demo y entrega"
prioridad: "P0"
fase: "Hora 42 (el guion desde la hora 0)"
rol: "Producto y agro"
agente: producto-agro
subsistemas: "S4"
depende_de: "Todas las P0"
reglas: "R5, R8"
estado: pendiente
---

# EP-13 · Demo y entrega

**Resultado esperado:** Una entrega completa que muestra el problema, el uso de datos NASA y dos casos reales, sin prometer más de lo que hace el producto.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Hora 42 (el guion desde la hora 0) |
| Rol responsable | Producto y agro |
| Agente sugerido | `producto-agro` (ver `.claude/agents/`) |
| Subsistemas | S4 (ver `specs/03-sistemas.md`) |
| Depende de | Todas las P0 |
| Reglas de diseño que aplican | R5, R8 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-131 · Dos casos reales para la demo

- **Historia:** Como jurado, quiero ver dos casos reales en pocos minutos, para entender el valor rápido.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Guion con un caso favorable y uno con alerta de sobreoferta
  - [ ] Ensayado al menos una vez
- **Notas:** —

### HU-132 · Video y descripción de la entrega

- **Historia:** Como jurado, quiero el video y la descripción según la guía de entrega, para evaluar el proyecto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cumple la guía publicada el 13 de noviembre
  - [ ] Cita todas las fuentes de datos
- **Notas:** —

### HU-133 · Impacto económico, social y ambiental

- **Historia:** Como jurado, quiero entender el impacto económico, social y ambiental y sus límites, para valorar el alcance.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Impacto presentado como potencial
  - [ ] Límites dichos con claridad
- **Notas:** —
