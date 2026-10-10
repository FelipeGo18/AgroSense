---
id: EP-05
titulo: "Señal de mercado con datos reales"
prioridad: "P1, condicionada"
fase: "Evento"
rol: "Datos"
agente: datos
subsistemas: "D1–D4"
depende_de: "HU-003"
reglas: "R1, R7, R8"
estado: pendiente
---

# EP-05 · Señal de mercado con datos reales

**Resultado esperado:** La tabla `market_month` con índice estacional de precio. Solo si HU-003 confirma la cobertura; si no, el P0 cubre la ausencia con HU-073.

| Campo | Valor |
|---|---|
| Prioridad | P1, condicionada |
| Fase | Evento |
| Rol responsable | Datos |
| Agente sugerido | `datos` (ver `.claude/agents/`) |
| Subsistemas | D1–D4 (ver `specs/03-sistemas.md`) |
| Depende de | HU-003 |
| Reglas de diseño que aplican | R1, R7, R8 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-051 · Índice estacional de precio

- **Historia:** Como agricultor, quiero saber si el precio suele bajar cuando sale la cosecha de mi ventana, para evitar vender barato.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Precio mensual por producto y central
  - [ ] Índice estacional documentado
  - [ ] Mapeo de producto a cultivo revisado
- **Notas:** —
