---
id: EP-12
titulo: "Calidad y trazabilidad"
prioridad: P0
fase: [Hora 0, Evento]
rol: "Calidad, con Datos"
agentes: [calidad, datos]
subsistemas: [S3, D4]
depende_de: [HU-011]
reglas: [R1, R2, R3, R4, R7, R8, R9]
estado: pendiente
---

# EP-12 · Calidad y trazabilidad

**Resultado esperado:** El equipo puede demostrar que cada resultado es correcto, reproducible y trazable a sus fuentes.

Empieza en la hora 0 con los casos de referencia y se cierra al final del evento.

## Historias de usuario

### HU-121 · Casos de referencia del motor

- **Historia:** Como equipo, quiero casos de referencia con resultado esperado escrito antes de programar, para saber si el motor acierta.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] De 8 a 12 combinaciones de municipio, cultivo y fecha de siembra, incluidos verde, rojo y «no evaluable», un rojo por helada crítica, un suelo desfavorable que no basta para rojo y una exclusión de rotación por pH
  - [ ] Cultivo no apto para la zona: `suitability.level = not_suitable`, luz `red`, acción `rotate`, `window` y `signals` nulos, y ninguna ventana en el calendario
  - [ ] Ficha sin rango de altitud con fuente: aptitud `insufficient_data`, no bloquea y aparece en las limitaciones
  - [ ] Ventana de alto riesgo que no entra en las mejores: una ventana con una señal crítica desfavorable y el balance más alto queda después de las demás y fuera de `best_windows`
  - [ ] Con y sin riego: la misma ventana con déficit de agua es `unfavorable` en `water` con `irrigated = false` y no lo es con `irrigated = true`; con `irrigated` nulo, se evalúa como sin riego y lo dice en las limitaciones
  - [ ] Acción `other_window` con `best_windows`, y un caso en que `best_windows` viene vacío
  - [ ] Coherencia: una ventana del calendario y el diagnóstico de esa misma fecha dan las mismas señales y calificaciones
  - [ ] Curva: un valor dentro del óptimo califica 100, uno en el límite absoluto califica 0 y el punto medio, 50 (HU-196)
  - [ ] Peso 0 en oferta cambia la luz: con la oferta `unfavorable` no crítica y las demás señales `favorable`, `overall_default` da `yellow` con `rotate` y, con `supply` en 0, `overall` da `green` con `sow`; la respuesta trae las dos
  - [ ] Riesgo grave de clima con peso 0 sigue contando: una helada crítica con `frost` en 0 da `red` en `overall`, y la señal trae `counts = true`
  - [ ] Peso 4 o 5: un `moderate` en esa señal cuenta como `unfavorable` y cambia la luz frente a la de AgroSense
  - [ ] Factor limitante: una ventana con una señal en 15 y el promedio ponderado más alto nunca queda por encima de una ventana con todas sus señales en 60 o más, ni entra primera en `best_windows`
  - [ ] Alternativas: con `rotate`, ningún cultivo `not_suitable` ni con una señal de clima `unfavorable` aparece en `alternatives`
  - [ ] Automatizados en pytest y corriendo en Docker, en local y en CI
- **Casos de las cuentas** (contra el PostgreSQL de Compose):
  - [ ] Dividir: una temporada cosechada de 1 ha con dos sucesoras de 0,5 ha cada una se acepta, y el progreso da dos relaciones
  - [ ] Juntar: dos temporadas cosechadas de 0,5 ha con una sucesora de 1 ha se acepta, y el progreso da dos relaciones hacia la misma
  - [ ] Área que no cabe: en un lote de 1 ha, las sucesoras de una temporada cosechada de 1 ha que suman 1,2 ha responden 422, porque las temporadas en curso pasarían del área del lote
  - [ ] Terreno anterior más terreno libre: después de una temporada cosechada de 1 ha, una sucesora de 1,5 ha se acepta si hay 0,5 ha libres en el lote
  - [ ] `follows_season_ids` con una temporada de otro lote, sin cosechar o cosechada después de la nueva siembra responde 422
  - [ ] Restaurar: una temporada borrada aparece en el historial con `restorable_until` y vuelve al restaurarla (HU-204)
- **Reglas que aplican:** R1, R2, R3, R4, R9
- **Notas:** Los casos nuevos se agregaron el 11 de octubre de 2026 con el cambio a ventanas de siembra y, el mismo día, con las prioridades, el factor limitante, las alternativas y la división de lotes (decisión 10). Pasa de M a L. Se escriben con datos de ejemplo rotulados (R5).

### HU-122 · Procedencia de cada dato

- **Historia:** Como jurado, quiero saber de dónde sale cada dato, para confiar en el resultado.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Manifiesto con versión, fuentes y cobertura
  - [ ] Cada entrada de `sources` dice qué cubre (`coverage`: país o región)
  - [ ] `sources.yaml` dice, por región, qué fuente calcula cada señal; la validación falla si una señal de la región no tiene fuente asignada o la fuente no existe en `sources` (R8)
  - [ ] `GET /api/v1/version` responde `dataset_version`, `rules_version`, `created_at`, `region`, `default_weights` (los pesos por defecto de `weights.yaml`, para mostrarlos antes de consultar) y `sources` (lista con `source_id`, `name`, `institution`, `url`, `coverage` y `license`), según el contrato
  - [ ] La web muestra fuentes, versión y los pesos por defecto con su porqué (HU-198)
- **Reglas que aplican:** R4, R7, R8
- **Contrato que toca:** `GET /api/v1/version`, `manifest.json`, `sources`
- **Notas:** Decisión 11: un indicador puede tener varias fuentes; se muestran juntas y nunca se mezclan.

### HU-123 · Reconstruir el dataset con un comando

- **Historia:** Como equipo, quiero reconstruir el dataset con un comando, para repetir la demo con los mismos datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un comando regenera `data/published` desde la caché
  - [ ] El resultado coincide con el manifiesto
