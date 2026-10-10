---
id: EP-10
titulo: "Rotaciones comprensibles en la web"
prioridad: P0
fase: [Evento]
rol: "Web"
agentes: [web]
subsistemas: [W4]
depende_de: [EP-09, EP-08]
reglas: [R3, R5]
estado: pendiente
---

# EP-10 · Rotaciones comprensibles en la web

**Resultado esperado:** El agricultor fija sus prioridades y entiende por qué cada rotación queda en su lugar.

Arranca contra las respuestas simuladas y se integra con EP-08.

## Historias de usuario

### HU-101 · Prioridades del agricultor

- **Historia:** Como agricultor, quiero indicar qué me importa más, para que el ranking refleje mis prioridades.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cuatro controles: agua, suelo, ingreso y riesgo, cada uno de 0 a 5 (contrato de `POST /api/v1/rotations`)
  - [ ] El ranking se actualiza al cambiarlos
- **Notas:** Con cuenta, los cultivos anteriores salen del historial del lote; sin cuenta, el usuario elige a mano el cultivo anterior.

### HU-102 · Ranking con desglose y razones

- **Historia:** Como agricultor, quiero ver el ranking con su desglose y razones, y por qué se descartaron otras opciones, para decidir con confianza.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Desglose por criterio visible
  - [ ] Las opciones excluidas y su regla se ven a pedido
