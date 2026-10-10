---
id: EP-10
titulo: "Rotaciones comprensibles en la web"
prioridad: "P0"
fase: "Evento"
rol: "Web"
agente: web
subsistemas: "W4"
depende_de: "EP-09; integración con EP-08"
reglas: "R3, R5"
estado: pendiente
---

# EP-10 · Rotaciones comprensibles en la web

**Resultado esperado:** El agricultor fija sus prioridades y entiende por qué cada rotación queda en su lugar.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Evento |
| Rol responsable | Web |
| Agente sugerido | `web` (ver `.claude/agents/`) |
| Subsistemas | W4 (ver `specs/03-sistemas.md`) |
| Depende de | EP-09; integración con EP-08 |
| Reglas de diseño que aplican | R3, R5 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-101 · Prioridades del agricultor

- **Historia:** Como agricultor, quiero indicar qué me importa más, para que el ranking refleje mis prioridades.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cuatro controles: agua, suelo, ingreso y riesgo
  - [ ] El ranking se actualiza al cambiarlos
- **Notas:** —

### HU-102 · Ranking con desglose y razones

- **Historia:** Como agricultor, quiero ver el ranking con su desglose y razones, y por qué se descartaron otras opciones, para decidir con confianza.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Desglose por criterio visible
  - [ ] Las opciones excluidas y su regla se ven a pedido
- **Notas:** —
