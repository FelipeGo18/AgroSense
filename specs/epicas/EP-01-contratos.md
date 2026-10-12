---
id: EP-01
titulo: "Contratos congelados y datos de ejemplo"
prioridad: P0
fase: [Fase 0, Hora 0]
rol: "Motor y API, con Web"
agentes: [motor-api, web]
subsistemas: [D4, M6, W6, S5]
depende_de: [EP-00]
reglas: [R4, R5, R7]
estado: pendiente
---

# EP-01 · Contratos congelados y datos de ejemplo

**Resultado esperado:** Datos, motor y web pueden avanzar en paralelo contra un contrato estable.

## Historias de usuario

### HU-011 · Esquema de las tablas publicadas

- **Historia:** Como desarrollador, quiero el esquema de las tablas publicadas, para que pipeline y motor trabajen en paralelo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Llaves, tipos y unidades documentados
  - [ ] Un Parquet de ejemplo por tabla, rotulado como ejemplo
  - [ ] Unicidad de llaves comprobada
- **Notas:** Se hace en la fase 0.

### HU-012 · OpenAPI con ejemplos de cada estado

- **Historia:** Como desarrollador web, quiero el OpenAPI con ejemplos de cada estado, para construir la interfaz sin esperar al motor.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] OpenAPI generado de los modelos Pydantic
  - [ ] Tipos TypeScript generados
  - [ ] Ejemplos de `available`, `insufficient_data`, `not_applicable` y error 422
  - [ ] Incluye los endpoints de cuenta del P0 (con ejemplos de 401 y 404), `/rotations` con una estrategia excluida y `/changes` con un periodo en `insufficient_data`

### HU-013 · Respuestas simuladas (MSW)

- **Historia:** Como desarrollador web, quiero respuestas simuladas, para desarrollar contra casos realistas.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] MSW responde todos los endpoints P0, incluidos `/rotations` con estrategias de 3 ciclos y `/changes`
  - [ ] Se puede forzar cada estado con un parámetro de la URL en desarrollo (por ejemplo, `?estado=insufficient_data`)
  - [ ] Cada respuesta simulada lleva el rótulo de ejemplo en pantalla (R5)
- **Reglas que aplican:** R5
- **Notas:** El panel de simulación para forzar estados, usuarios, clima y tiempo es HU-014, que pasó a P1 el 11 de octubre de 2026; en el MVP basta el parámetro de la URL.

### HU-014 · Modo simulación para desarrolladores

- **Historia:** Como desarrollador, quiero activar un modo simulación con una variable de entorno, para ver cada resultado, usuario, clima y momento sin depender del backend real.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `VITE_SIMULATION=true` activa MSW para todos los endpoints (cálculo, cuentas y condiciones) y el panel de simulación de `specs/05-frontend.md`
  - [ ] `AGROSENSE_SIMULATION=true` arranca el backend con usuario simulado y base de datos de ejemplo
  - [ ] Franja visible «Modo simulación · datos de ejemplo» mientras está activo
  - [ ] El build de producción no incluye MSW ni el panel; el CI falla si la variable está activa en producción; el backend no arranca en producción con simulación
- **Reglas que aplican:** R5
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP, las respuestas simuladas de HU-013 bastan para desarrollar la web.
