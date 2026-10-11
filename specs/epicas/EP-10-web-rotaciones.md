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

**Resultado esperado:** El agricultor fija sus prioridades y entiende por qué cada rotación queda en su lugar y por qué otras se descartaron, incluidas las que no se dan en su zona.

Arranca contra las respuestas simuladas y se integra con EP-08.

Desde el diagnóstico se llega aquí de dos formas: con «Qué sembrar después» y desde los cultivos alternativos de la acción `rotate` (HU-203), cuando el agricultor quiere ver la secuencia completa. Las alternativas del diagnóstico son una sugerencia para esa ventana; las rotaciones revisan además las reglas con el historial del terreno. Todo es informativo: decide el agricultor.

## Historias de usuario

### HU-101 · Prioridades del agricultor

- **Historia:** Como agricultor, quiero indicar qué me importa más, para que el ranking refleje mis prioridades.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cuatro controles: agua, suelo, ingreso y riesgo, cada uno de 0 a 5 (contrato de `POST /api/v1/rotations`)
  - [ ] El ranking se actualiza al cambiarlos
  - [ ] La web envía `sowing_date`: la fecha en que se sembraría el primer cultivo, la misma que eligió en la consulta (HU-091); no se pide ningún otro periodo
  - [ ] Con todas las prioridades en 0, la web no envía la petición y pide subir al menos una
- **Contrato que toca:** `POST /api/v1/rotations`
- **Notas:** Con cuenta, los cultivos anteriores salen del historial del terreno que se va a sembrar: los de todas las temporadas de las que viene (`follows_season_ids`, HU-165); sin cuenta, el usuario elige a mano el cultivo anterior. Estas cuatro prioridades son las de las rotaciones; las de las señales (una por señal, para el semáforo y el orden de ventanas) están en HU-202 y HU-180. Usan el mismo control visual.

### HU-102 · Ranking con desglose y razones

- **Historia:** Como agricultor, quiero ver el ranking con su desglose y razones, y por qué se descartaron otras opciones, para decidir con confianza.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Desglose por criterio visible
  - [ ] Las opciones excluidas y su regla se ven a pedido
  - [ ] Una opción excluida porque no es apta para la zona dice «No se da en su zona» con el dato de la ficha y su fuente
  - [ ] Sin opciones válidas, estado vacío con las exclusiones a la vista
  - [ ] Si se llegó desde un cultivo alternativo del diagnóstico (HU-203), ese cultivo se resalta en el ranking o, si quedó excluido, se ve su exclusión con la regla
