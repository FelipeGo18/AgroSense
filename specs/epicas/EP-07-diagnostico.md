---
id: EP-07
titulo: "Diagnóstico de la ventana explicable"
prioridad: "P0"
fase: "Evento"
rol: "Motor y API"
agente: motor-api
subsistemas: "M1, M2, M4, M6"
depende_de: "HU-011, HU-012 (datos de ejemplo), luego EP-03 y EP-04"
reglas: "R1, R2, R4, R5, R6"
estado: pendiente
---

# EP-07 · Diagnóstico de la ventana explicable

**Resultado esperado:** Dado un municipio, un cultivo y un semestre, el sistema responde un semáforo con señales, razones, acción y limitaciones.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Evento |
| Rol responsable | Motor y API |
| Agente sugerido | `motor-api` (ver `.claude/agents/`) |
| Subsistemas | M1, M2, M4, M6 (ver `specs/03-sistemas.md`) |
| Depende de | HU-011, HU-012 (datos de ejemplo), luego EP-03 y EP-04 |
| Reglas de diseño que aplican | R1, R2, R4, R5, R6 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-071 · Señal de clima

- **Historia:** Como agricultor, quiero saber si el clima de mi ventana ha sido favorable, para decidir si siembro.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal con estado, nivel, indicadores y razones
  - [ ] Umbrales leídos de la configuración
- **Notas:** —

### HU-072 · Señal de oferta

- **Historia:** Como agricultor, quiero saber si en mi zona se está sembrando mucho o poco de mi cultivo, para evitar la sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Nivel según la variación del área sembrada
  - [ ] Con poca siembra y sin mercado, la razón dice «posible oportunidad, sin confirmar precio»
- **Notas:** —

### HU-073 · Señal de mercado sin datos

- **Historia:** Como agricultor, quiero saber cuándo no hay datos de mercado, para no confiar en una señal que no existe.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Sin datos: `insufficient_data`, nivel nulo y razón explícita
  - [ ] Con EP-05: nivel según el índice estacional
- **Notas:** —

### HU-074 · Semáforo global y acción sugerida

- **Historia:** Como agricultor, quiero un semáforo global con una acción sugerida, para decidir rápido.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Implementa las reglas de agregación del contrato
  - [ ] Prueba: una señal desfavorable crítica nunca da verde
  - [ ] Prueba: sin clima, la luz es `not_evaluable`
- **Notas:** —

### HU-075 · Umbrales y pesos versionados

- **Historia:** Como equipo, quiero umbrales y pesos versionados en configuración, para ajustarlos sin tocar código y explicar qué versión se usó.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Archivos YAML con número de versión
  - [ ] La respuesta incluye la versión del dataset y de las reglas
- **Notas:** —

### HU-076 · Endpoint de diagnóstico con errores claros

- **Historia:** Como desarrollador web, quiero el endpoint de diagnóstico con errores claros, para distinguir una entrada inválida de una sin datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] 422 para entradas fuera del catálogo
  - [ ] 200 con `insufficient_data` para entradas válidas sin datos
- **Notas:** —
