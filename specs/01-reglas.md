# Reglas de diseño (R1–R10)

Aplican a todos los sistemas. **Una historia de usuario que viole una regla no se acepta, aunque funcione.**

| Código | Regla | Qué significa en la práctica |
|---|---|---|
| R1 | Disponibilidad y nivel son campos distintos | Una señal sin datos tiene `status = insufficient_data` y `level = null`. Nunca se interpreta como riesgo. |
| R2 | El semáforo se decide por reglas, no por promedio | Un riesgo desfavorable no se compensa con señales favorables. |
| R3 | Las restricciones agronómicas filtran | Una rotación inválida se excluye y se registra el motivo. No se castiga con puntos. |
| R4 | Resultados deterministas y versionados | Mismos datos, reglas y entrada producen el mismo resultado. Cada respuesta lleva la versión del dataset y de las reglas. |
| R5 | Nada inventado | Los datos de ejemplo se marcan como ejemplo. Las explicaciones solo citan indicadores y reglas que el motor evaluó. |
| R6 | El motor no conoce la web | El módulo de decisión no importa FastAPI ni lee archivos directamente. Recibe tablas y configuración. |
| R7 | Una sola llave territorial | Todo se une por código DIVIPOLA del municipio. Los nombres no se usan como llave. |
| R8 | Toda regla y dato tiene fuente | Cada fila de datos y cada regla agronómica apunta a una entrada de la tabla `sources`. |
| R9 | Los datos de la finca no se guardan en el servidor | El servidor calcula y responde. Si se guardan, es solo en el dispositivo del usuario (P1). |
| R10 | El riego es una estimación y se dice siempre | Se basa en el clima de la zona, no en mediciones del lote. Se muestran rangos y se pide verificar la humedad del suelo en campo. |

## Cómo se comprueba cada regla

| Regla | Comprobación sugerida |
|---|---|
| R1 | Prueba: una señal sin datos devuelve `insufficient_data` y `level` nulo; la web no la pinta como riesgo. |
| R2 | Prueba: una señal `unfavorable` crítica nunca da verde, aunque las otras sean `favorable`. |
| R3 | Prueba: una secuencia que viola un `filter` no aparece en el ranking y su exclusión cita la regla. |
| R4 | Prueba: dos ejecuciones iguales dan salida idéntica; toda respuesta trae `versions.dataset` y `versions.rules`. |
| R5 | Revisión: ningún dato ficticio sin rótulo; cada razón de M4 mapea a un indicador o regla evaluados. |
| R6 | Prueba o lint: `backend/engine/` no importa `fastapi` ni abre archivos. |
| R7 | Prueba: las uniones usan `municipality_id`; unicidad de llaves en los Parquet. |
| R8 | Validación: ninguna fila ni regla con `source_id` vacío o inexistente en `sources`. |
| R9 | Revisión: `/water-plans` no persiste; ningún almacenamiento de finca en el servidor. |
| R10 | Revisión: el rótulo de estimación aparece junto a todo resultado de riego; se muestran rangos. |

## Agregación inicial del semáforo

Los umbrales viven en configuración versionada (`backend/config/`).

1. Si clima u oferta no están disponibles, la luz es `not_evaluable` y la acción es `review_data`.
2. Si alguna señal disponible es `unfavorable` en grado crítico, o dos son `unfavorable`, la luz es `red`.
3. Si el clima es `favorable` y ninguna señal disponible es `unfavorable`, la luz es `green`.
4. En cualquier otro caso, la luz es `yellow`.
5. Un mercado sin datos **nunca cambia la luz**, pero se agrega a las limitaciones.

## Valores permitidos

| Campo | Valores |
|---|---|
| `status` | `available`, `insufficient_data`, `not_applicable` |
| `level` | `favorable`, `moderate`, `unfavorable` o nulo |
| `light` | `green`, `yellow`, `red`, `not_evaluable` |
| `action` | `sow`, `wait_other_semester`, `rotate`, `review_data` |
