---
id: EP-02
titulo: "Base del proyecto desplegada"
prioridad: "P0"
fase: "Hora 0"
rol: "Plataforma (o Motor y API si son 4 personas)"
agente: plataforma
subsistemas: "S1, S2"
depende_de: "Ninguna"
reglas: "—"
estado: pendiente
---

# EP-02 · Base del proyecto desplegada

**Resultado esperado:** Cualquier integrante arranca el proyecto en minutos, y la URL pública existe desde las primeras horas.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Hora 0 |
| Rol responsable | Plataforma (o Motor y API si son 4 personas) |
| Agente sugerido | `plataforma` (ver `.claude/agents/`) |
| Subsistemas | S1, S2 (ver `specs/03-sistemas.md`) |
| Depende de | Ninguna |
| Reglas de diseño que aplican | — (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-021 · Clonar y ejecutar con pocos comandos

- **Historia:** Como integrante, quiero clonar y ejecutar todo con pocos comandos, para no perder tiempo configurando.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] README de arranque probado por otra persona
  - [ ] Estructura del repositorio acordada
- **Notas:** —

### HU-022 · Lint y pruebas automáticas en cada cambio

- **Historia:** Como equipo, quiero lint y pruebas automáticas en cada cambio, para detectar roturas temprano.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] GitHub Actions corre Ruff, pytest y el build web
- **Notas:** —

### HU-023 · Esqueleto desplegado en URL pública

- **Historia:** Como equipo, quiero el esqueleto desplegado, para que el despliegue no sea un riesgo al final.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un contenedor sirve API y web en una URL pública
  - [ ] `/api/v1/version` responde
- **Notas:** —
