---
id: EP-03
titulo: "Dataset de oferta publicado"
prioridad: P0
fase: [Evento]
rol: "Datos"
agentes: [datos]
subsistemas: [D1, D2, D3, D4]
depende_de: [EP-00, HU-011]
reglas: [R5, R7, R8]
estado: pendiente
---

# EP-03 · Dataset de oferta publicado

**Resultado esperado:** La tabla `supply_semester` de la región, validada y con indicadores de oferta.

## Historias de usuario

### HU-031 · Datos de EVA normalizados por DIVIPOLA

- **Historia:** Como motor, quiero los datos de EVA normalizados por DIVIPOLA, cultivo, año y semestre, para evaluar la oferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Script reproducible desde el CSV crudo
  - [ ] Filas rechazadas reportadas con motivo
  - [ ] Datos preliminares marcados

### HU-032 · Variación del área sembrada y participación departamental

- **Historia:** Como motor, quiero la variación del área sembrada y la participación departamental, para detectar sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Definición escrita de cada indicador
  - [ ] Valores comprobados a mano en 2 municipios
  - [ ] Calidad `partial` cuando faltan semestres previos
