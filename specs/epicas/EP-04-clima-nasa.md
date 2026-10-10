---
id: EP-04
titulo: "Dataset climático publicado"
prioridad: "P0"
fase: "Evento"
rol: "Datos"
agente: datos
subsistemas: "D1–D4"
depende_de: "HU-002, HU-011"
reglas: "R5, R7, R8"
estado: pendiente
---

# EP-04 · Dataset climático publicado

**Resultado esperado:** La tabla `climate_semester` de la región, con anomalías respecto a lo normal.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Evento |
| Rol responsable | Datos |
| Agente sugerido | `datos` (ver `.claude/agents/`) |
| Subsistemas | D1–D4 (ver `specs/03-sistemas.md`) |
| Depende de | HU-002, HU-011 |
| Reglas de diseño que aplican | R5, R7, R8 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-041 · Series diarias de lluvia y temperatura

- **Historia:** Como motor, quiero series diarias de lluvia y temperatura por municipio, para evaluar el clima de cada semestre.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Descarga con caché y reintentos
  - [ ] Fuente y fecha registradas
  - [ ] Días faltantes contados en `valid_days`
- **Notas:** —

### HU-042 · Total, normal y anomalía por semestre

- **Historia:** Como motor, quiero el total, la normal y la anomalía por semestre, para saber si una ventana suele ser seca o lluviosa.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Periodo base de la normal documentado
  - [ ] Comprobación manual en 2 municipios
  - [ ] Calidad `partial` bajo un mínimo de días válidos
- **Notas:** —

### HU-043 · Humedad del suelo y NDVI

- **Historia:** Como motor, quiero humedad del suelo y NDVI por municipio, para enriquecer la señal climática.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Extracción por polígono municipal
  - [ ] Mismas reglas de calidad
- **Notas:** —

### HU-044 · Altitud de cada municipio

- **Historia:** Como motor, quiero la altitud de cada municipio, para filtrar cultivos por piso térmico.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Altitud desde un modelo de elevación o fuente oficial
  - [ ] Pasa a P0 si la región mezcla pisos térmicos
- **Notas:** —
