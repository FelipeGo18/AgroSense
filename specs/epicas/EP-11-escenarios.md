---
id: EP-11
titulo: "Escenarios hipotéticos"
prioridad: "P1"
fase: "Evento"
rol: "Motor y API y Web"
agente: motor-api
subsistemas: "M5, W5"
depende_de: "EP-07, EP-08, EP-10"
reglas: "R4, R5"
estado: pendiente
---

# EP-11 · Escenarios hipotéticos

**Resultado esperado:** El usuario prueba «¿y si llueve menos?» o «¿y si se siembra más?» y ve qué cambia. Solo entra si todo el P0 pasa sus pruebas en la hora 34.

| Campo | Valor |
|---|---|
| Prioridad | P1 |
| Fase | Evento |
| Rol responsable | Motor y API y Web |
| Agente sugerido | `motor-api` (ver `.claude/agents/`) |
| Subsistemas | M5, W5 (ver `specs/03-sistemas.md`) |
| Depende de | EP-07, EP-08, EP-10 |
| Reglas de diseño que aplican | R4, R5 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-111 · Reevaluar con cambios en memoria

- **Historia:** Como motor, quiero aplicar cambios en memoria y reevaluar, para comparar con el caso base.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cambios de lluvia y área en rangos validados
  - [ ] El dataset publicado no se modifica
- **Notas:** —

### HU-112 · Endpoint de escenarios

- **Historia:** Como desarrollador web, quiero el endpoint de escenarios, para mostrar la comparación.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Devuelve el resultado base, el del escenario y las diferencias
- **Notas:** —

### HU-113 · Comparación de escenarios

- **Historia:** Como agricultor, quiero ver qué cambia bajo un escenario, para prepararme.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Comparación lado a lado
  - [ ] Rótulo visible: «escenario hipotético, no es un pronóstico»
- **Notas:** —
