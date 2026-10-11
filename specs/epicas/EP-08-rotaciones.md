---
id: EP-08
titulo: "Rotaciones válidas y ordenadas"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M3, M4, M6]
depende_de: [EP-06, HU-071, HU-072, HU-073, HU-181, HU-191]
reglas: [R3, R4, R5, R6]
estado: pendiente
---

# EP-08 · Rotaciones válidas y ordenadas

**Resultado esperado:** Un ranking de secuencias de 2 ciclos que cumplen las reglas y son aptas para la zona, ordenado por las prioridades del agricultor y explicado.

La secuencia empieza en `sowing_date`, la fecha en que se sembraría su primer cultivo. Cada opción se evalúa en su propia ventana de siembra (`specs/01-reglas.md`): la petición lleva una fecha, no un periodo.

## Historias de usuario

### HU-081 · Filtrar rotaciones válidas

- **Historia:** Como agricultor, quiero ver solo rotaciones agronómicamente válidas y que se den en mi zona, para no recibir recomendaciones dañinas.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Las reglas de filtro excluyen secuencias
  - [ ] Un cultivo que no es apto para la zona (HU-191) se excluye; el motivo cita el rango de altitud de su ficha y su fuente
  - [ ] Un cultivo sin rango de altitud con fuente no se excluye por aptitud: se agrega a las limitaciones (R1)
  - [ ] Cada exclusión registra la regla o el dato que la causó
  - [ ] Abonos verdes y descanso entran como opciones de la secuencia (HU-063)
- **Reglas que aplican:** R1, R3, R8
- **Notas:** Supuesto por confirmar: la aptitud por altitud no aplica al descanso (`kind = fallow`), que no tiene rango. Con cuenta, los cultivos anteriores son los de todas las temporadas de las que viene el terreno (`follows_season_ids`, HU-165): si el terreno junta dos partes con cultivos distintos, cada regla de filtro se revisa contra cada uno (supuesto por confirmar). Las alternativas del diagnóstico (HU-197) no reemplazan este filtro: son una sugerencia para una ventana, sin el historial.

### HU-082 · Ordenar rotaciones por prioridades

- **Historia:** Como agricultor, quiero ordenar las rotaciones según mis prioridades (agua, suelo, ingreso y riesgo), para elegir la que me conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Puntaje de 0 a 100 por criterio y total ponderado
  - [ ] Cada opción se evalúa en su propia ventana: el primer cultivo desde `sowing_date` hasta su cosecha estimada
  - [ ] Misma entrada, mismo orden; desempate determinista
- **Notas:** Supuesto por confirmar: desde qué fecha se evalúa el segundo ciclo de la secuencia (la cosecha estimada del primero es lo coherente con la regla, pero el contrato no lo dice).

### HU-083 · Explicar el orden del ranking

- **Historia:** Como agricultor, quiero entender por qué una rotación quedó arriba, para confiar en ella.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] De 2 a 4 razones por opción, de plantillas fijas
  - [ ] Cada razón cita una regla o indicador real

### HU-084 · Endpoint de rotaciones

- **Historia:** Como desarrollador web, quiero el endpoint de rotaciones, para mostrar el ranking.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cumple el OpenAPI: recibe `municipality_id`, `sowing_date`, `previous_crop_ids`, `priorities` y `lot_id`
  - [ ] Prioridades fuera de rango o todas en 0 responden 422; `sowing_date` con formato inválido responde 422
  - [ ] La respuesta trae las opciones excluidas con su motivo, incluidas las que no son aptas para la zona
  - [ ] No guarda los datos de la finca ni quién consultó (R9)
- **Contrato que toca:** `POST /api/v1/rotations`
