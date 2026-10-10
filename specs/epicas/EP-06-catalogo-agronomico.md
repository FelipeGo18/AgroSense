---
id: EP-06
titulo: "Catálogo agronómico con fuentes"
prioridad: P0
fase: [Fase 0]
rol: "Producto y agro"
agentes: [producto-agro]
subsistemas: [AG1, AG2, AG3]
depende_de: [HU-001]
reglas: [R3, R8]
estado: pendiente
---

# EP-06 · Catálogo agronómico con fuentes

**Resultado esperado:** Fichas de 6 a 8 cultivos y reglas de rotación como datos, cada una con fuente.

## Historias de usuario

### HU-061 · Ficha por cultivo

- **Historia:** Como motor, quiero una ficha por cultivo, para saber qué se puede sembrar y cuándo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Todos los campos del contrato llenos
  - [ ] Fuente por campo
  - [ ] Revisión cruzada por otro integrante

### HU-062 · Reglas de rotación como datos

- **Historia:** Como motor, quiero las reglas de rotación como datos, para filtrar y puntuar secuencias sin cambiar código.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Como mínimo: no repetir familia, bonificar leguminosas y alternar tipo de raíz
  - [ ] Cada regla con tipo, condición, efecto y fuente
