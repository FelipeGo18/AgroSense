---
id: EP-18
titulo: "Suelo de la zona y del lote en las decisiones"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Datos y Motor y API, con Web y Producto y agro"
agentes: [datos, motor-api, web, producto-agro]
subsistemas: [D1, D3, D4, M1, M3, W2, W4, W7]
depende_de: [HU-011, HU-063]
reglas: [R1, R2, R3, R5, R6, R7, R8, R9, R10]
estado: pendiente
---

# EP-18 · Suelo de la zona y del lote en las decisiones

**Resultado esperado:** El diagnóstico, el balance de agua y las rotaciones usan el suelo estimado de la zona o del lote dibujado (el pH en la señal de suelo, la textura en cuánta agua retiene y el carbono orgánico en las rotaciones), y el agricultor ve su suelo con su rango y el aviso de que es una estimación.

El reto («Field Shift») pide usar información local del suelo y rotaciones que mejoren la salud del suelo. Se decidió el 10 de octubre de 2026 (`docs/investigacion-decisiones.md`). La descarga y publicación (HU-181) se puede adelantar en la fase 0 si HU-004 lo permite.

## Historias de usuario

### HU-181 · Suelo de la región publicado

- **Historia:** Como motor, quiero el suelo de la región en tablas publicadas, para evaluarlo sin consultar servicios externos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Adaptador de SoilGrids (ISRIC, CC BY 4.0) con caché: pH, carbono orgánico, nitrógeno, arcilla, arena y limo de 0 a 30 cm, con el intervalo del 90 % del pH
  - [ ] `soil_grid` (celdas de 250 m de la región) y `soil_municipality` (mediana por municipio, con `cells` y `quality`) según el contrato
  - [ ] Entrada en `sources` con licencia y versión de SoilGrids
  - [ ] Comprobación manual en 2 municipios contra un estudio de suelos del IGAC, si lo hay (IGAC es de la región piloto supuesta en Colombia; con otra región, el estudio oficial que corresponda)
- **Reglas que aplican:** R7, R8
- **Notas:** La textura (`clay_pct`, `sand_pct`, `silt_pct`, `texture_class`) también la usa el balance de agua (HU-144).

### HU-182 · Suelo de un lote

- **Historia:** Como agricultor, quiero ver el suelo estimado de mi lote, para entender qué le conviene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La API calcula el suelo del lote como mediana de las celdas de `soil_grid` que toca el polígono; sin polígono, usa `soil_municipality`, y lo dice en `basis`
  - [ ] `soil` en la respuesta de `GET /lots/{lot_id}`
  - [ ] El suelo del lote no se guarda en la base de datos
  - [ ] `lot_id` opcional en `/diagnostics` y `/rotations`: un lote ajeno responde 404
- **Reglas que aplican:** R6, R9, R10
- **Notas:** Depende de HU-164 (polígono del lote) y HU-181. Si se recorta, queda el suelo del municipio (HU-183).

### HU-183 · Señal de suelo en el diagnóstico

- **Historia:** Como agricultor, quiero saber si el suelo de mi zona o de mi lote le sirve al cultivo, para no sembrar donde no va a darse.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `score` con la curva de HU-196: 100 con el pH en el rango óptimo (`ph_opt_min`–`ph_opt_max`), 0 fuera del tolerado (`ph_min`–`ph_max`) y una recta entre ambos; el nivel sale de la calificación
  - [ ] Se mantiene la lectura con el intervalo `ph_p05`–`ph_p95`: si todo el intervalo queda fuera del tolerado, el nivel es `unfavorable`; si el intervalo cruza un límite, el nivel no pasa de `moderate`
  - [ ] Nunca crítica (R10): solo puede llevar a rojo junto con otra señal desfavorable
  - [ ] Sin suelo, o con un cultivo sin rango de pH con fuente: `insufficient_data` y a las limitaciones
  - [ ] La razón recomienda un análisis de suelo del lote
  - [ ] Con HU-078, `GET /catalogs/municipalities/{municipality_id}/soil` muestra el suelo del municipio sin cuenta
- **Reglas que aplican:** R1, R2, R5, R10
- **Notas:** Depende de HU-181, HU-063 y HU-196; la usa HU-074 (antes decía que dependía de HU-074, lo que hacía un ciclo). Va con el diagnóstico, en la etapa 1. El suelo no cambia con la fecha: la señal es la misma en todas las ventanas de un cultivo, y por eso con suelo desfavorable la acción es `rotate` y no `other_window`. En el orden de ventanas (HU-192) califica igual en todas, pero puede ser el factor limitante. La textura no entra en esta señal: entra en el balance de agua (HU-144, decisión 10). Supuesto por confirmar: qué valor del pH entra a la curva (la mediana) y cómo se combina con el intervalo, como dice el segundo criterio.

### HU-184 · Suelo en las rotaciones

- **Historia:** Como agricultor, quiero que las rotaciones tengan en cuenta mi suelo y me propongan cómo recuperarlo, para que la tierra rinda en los próximos años.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Exclusión por pH fuera de rango con la regla citada (R3)
  - [ ] El criterio «suelo» usa el carbono orgánico y las reglas de HU-063: bonifica abonos verdes, descanso y leguminosas cuando es bajo
  - [ ] Las razones citan la propiedad del suelo y la regla
- **Reglas que aplican:** R3, R5, R8
- **Notas:** Depende de HU-081, HU-082 y HU-181; con HU-182, usa el suelo del lote.

### HU-185 · Ver el suelo en la web

- **Historia:** Como agricultor, quiero ver mi suelo explicado en palabras sencillas, para entender por qué la app me recomienda algo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] pH, carbono orgánico y textura con su rango y una frase sencilla de qué significan; la de la textura dice que cambia cuánta agua guarda el suelo y que por eso entra en la señal de agua
  - [ ] Rótulo: «Estimación de un mapa global de 250 m. Un análisis de suelo de su lote es más preciso» (R10)
  - [ ] En la ficha del lote (Lote · ahora) y en el detalle de la señal de suelo
- **Reglas que aplican:** R5, R10
