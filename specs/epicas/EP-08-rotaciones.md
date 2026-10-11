---
id: EP-08
titulo: "Rotaciones válidas y ordenadas"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M3, M4, M6]
depende_de: [EP-06, HU-071, HU-072, HU-073, HU-181]
reglas: [R3, R4, R5, R6]
estado: pendiente
---

# EP-08 · Rotaciones válidas y ordenadas

**Resultado esperado:** Un ranking de secuencias de 2 ciclos que cumplen las reglas, ordenado por las prioridades del agricultor y explicado.

## Historias de usuario

### HU-081 · Filtrar rotaciones válidas

- **Historia:** Como agricultor, quiero ver solo rotaciones agronómicamente válidas, para no recibir recomendaciones dañinas.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Las reglas de filtro excluyen secuencias
  - [ ] Cada exclusión registra la regla que la causó
  - [ ] Abonos verdes y descanso entran como opciones de la secuencia (HU-063)

### HU-082 · Ordenar rotaciones por prioridades

- **Historia:** Como agricultor, quiero ordenar las rotaciones según mis prioridades (agua, suelo, ingreso y riesgo), para elegir la que me conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Puntaje de 0 a 100 por criterio y total ponderado
  - [ ] Misma entrada, mismo orden; desempate determinista

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
  - [ ] Cumple el OpenAPI
  - [ ] Prioridades fuera de rango responden 422
