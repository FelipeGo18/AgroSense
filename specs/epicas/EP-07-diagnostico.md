---
id: EP-07
titulo: "Diagnóstico de la ventana explicable"
prioridad: P0
fase: [Evento]
rol: "Motor y API"
agentes: [motor-api]
subsistemas: [M1, M2, M4, M6]
depende_de: [HU-011, HU-012, EP-03, EP-04, HU-063, HU-179, HU-181]
reglas: [R1, R2, R4, R5, R6]
estado: pendiente
---

# EP-07 · Diagnóstico de la ventana explicable

**Resultado esperado:** Dado un municipio, un cultivo y un semestre, el sistema responde un semáforo con señales, razones, acción y limitaciones.

Arranca con los datos de ejemplo de HU-011 y HU-012, y pasa a los datos reales de EP-03 y EP-04 en la integración.

## Historias de usuario

### HU-071 · Señal de lluvia

- **Historia:** Como agricultor, quiero saber si la lluvia de mi ventana ha sido favorable, para decidir si siembro.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Señal con estado, nivel, indicadores y razones
  - [ ] Umbrales leídos de la configuración

### HU-072 · Señal de oferta

- **Historia:** Como agricultor, quiero saber si en mi zona se está sembrando mucho o poco de mi cultivo, para evitar la sobreoferta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Nivel según la variación del área sembrada
  - [ ] Con poca siembra y sin mercado, la razón dice «posible oportunidad, sin confirmar precio»

### HU-073 · Señal de mercado sin datos

- **Historia:** Como agricultor, quiero saber cuándo no hay datos de mercado, para no confiar en una señal que no existe.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Sin datos: `insufficient_data`, nivel nulo y razón explícita
  - [ ] Con EP-05: nivel según el índice estacional

### HU-074 · Semáforo global y acción sugerida

- **Historia:** Como agricultor, quiero un semáforo global con una acción sugerida, para decidir rápido.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Implementa las reglas de agregación y la tabla de acciones de `specs/01-reglas.md`
  - [ ] Prueba: una señal desfavorable crítica nunca da verde
  - [ ] Prueba: sin lluvia o sin oferta, la luz es `not_evaluable`
  - [ ] Prueba: heladas, suelo o mercado sin datos no cambian la luz y aparecen en las limitaciones
- **Notas:** Las señales pasaron de tres a cinco el 10 de octubre de 2026 (heladas y suelo). Ver `docs/registro-de-decisiones.md`.

### HU-077 · Señal de heladas

- **Historia:** Como agricultor, quiero saber qué tan seguido ha helado cuando mi cultivo es sensible, para no perder la siembra por una helada.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usa el mismo cálculo del calendario (HU-179): el mejor mes de siembra del semestre y la frecuencia de heladas en los meses de las etapas sensibles
  - [ ] La razón nombra el mes y la etapa («Sembrando en agosto, hubo heladas en la floración 2 de cada 10 años»)
  - [ ] `not_applicable` si ninguna etapa es sensible; `insufficient_data` si falta `climate_risk_month`
  - [ ] Niveles y grado crítico en `thresholds.yaml`
  - [ ] Caso de referencia: helada crítica con lluvia y oferta favorables da rojo y la acción es esperar otro semestre
- **Reglas que aplican:** R1, R2, R4, R5
- **Notas:** Depende de HU-045 (heladas por mes), HU-063 (etapas sensibles) y HU-179 (cálculo del calendario, que se adelanta a la etapa 1).

### HU-075 · Umbrales y pesos versionados

- **Historia:** Como equipo, quiero umbrales y pesos versionados en configuración, para ajustarlos sin tocar código y explicar qué versión se usó.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Archivos YAML con número de versión
  - [ ] La respuesta incluye la versión del dataset y de las reglas

### HU-076 · Endpoint de diagnóstico con errores claros

- **Historia:** Como desarrollador web, quiero el endpoint de diagnóstico con errores claros, para distinguir una entrada inválida de una sin datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] 422 para entradas fuera del catálogo o un cultivo con `kind` distinto de `crop`
  - [ ] 200 con `insufficient_data` para entradas válidas sin datos
  - [ ] 401 con `lot_id` y sin sesión; 404 con un lote ajeno

### HU-078 · Endpoints de catálogo y tendencias

- **Historia:** Como desarrollador web, quiero los endpoints de municipios, cultivos, límites, suelo del municipio y tendencias, para armar la consulta y las gráficas.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /catalogs/municipalities`, `/catalogs/crops`, `/catalogs/municipalities/{id}/boundary`, `/catalogs/municipalities/{id}/soil` y `/trends` según el contrato
  - [ ] Solo leen el dataset publicado; sin datos, `insufficient_data` (R1)
- **Reglas que aplican:** R1, R4, R7
