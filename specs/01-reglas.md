# Reglas de diseño (R1–R10)

Aplican a todos los sistemas. **Una historia de usuario que viole una regla no se acepta, aunque funcione.**

| Código | Regla | Qué significa en la práctica |
|---|---|---|
| R1 | Disponibilidad y nivel son campos distintos | Una señal sin datos tiene `status = insufficient_data` y `level = null`. Nunca se interpreta como riesgo. |
| R2 | El semáforo se decide por reglas, no por promedio | Un riesgo desfavorable no se compensa con señales favorables. |
| R3 | Las restricciones agronómicas filtran | Una rotación inválida se excluye y se registra el motivo. No se castiga con puntos. |
| R4 | Resultados deterministas y versionados | Mismos datos, reglas y entrada producen el mismo resultado. Cada respuesta lleva la versión del dataset y de las reglas. |
| R5 | Nada inventado | Los datos de ejemplo se marcan como ejemplo. Las explicaciones solo citan indicadores y reglas que el motor evaluó. |
| R6 | El motor no conoce la web | El módulo de decisión no importa FastAPI ni lee archivos ni la base de datos directamente. Recibe tablas, configuración y, cuando aplica, el historial y el suelo del lote que le pasa la API. |
| R7 | Una sola llave territorial | Todo se une por código DIVIPOLA del municipio. Los nombres no se usan como llave. |
| R8 | Toda regla y dato tiene fuente | Cada fila de datos y cada regla agronómica apunta a una entrada de la tabla `sources`. |
| R9 | Los datos de la finca solo se guardan con cuenta y consentimiento | Los endpoints de cálculo (`/diagnostics`, `/rotations`, `/water-plans`, `/calendar`, `/scenarios`) nunca guardan nada. Sin cuenta, los datos no salen del dispositivo. Con cuenta, se guardan los lotes y su historial con consentimiento registrado, solo los datos mínimos, y el usuario puede borrarlo todo. |
| R10 | El riego y el suelo son estimaciones y se dice siempre | El riego se basa en el clima de la zona, no en mediciones del lote: se muestran rangos y se pide verificar la humedad del suelo en campo. El suelo sale de un mapa global de 250 m (SoilGrids): se muestra con su rango de incertidumbre y se recomienda un análisis de suelo del lote. |

## Cómo se comprueba cada regla

| Regla | Comprobación sugerida |
|---|---|
| R1 | Prueba: una señal sin datos devuelve `insufficient_data` y `level` nulo; la web no la pinta como riesgo. |
| R2 | Prueba: una señal `unfavorable` crítica nunca da verde, aunque las otras sean `favorable`. Prueba: una helada crítica da rojo con lluvia y oferta favorables. |
| R3 | Prueba: una secuencia que viola un `filter` no aparece en el ranking y su exclusión cita la regla. |
| R4 | Prueba: dos ejecuciones iguales dan salida idéntica; toda respuesta trae `versions.dataset` y `versions.rules`. |
| R5 | Revisión: ningún dato ficticio sin rótulo; cada razón de M4 mapea a un indicador o regla evaluados. |
| R6 | Prueba o lint: `backend/engine/` no importa `fastapi` ni `sqlalchemy` ni abre archivos. |
| R7 | Prueba: las uniones usan `municipality_id`; unicidad de llaves en los Parquet. |
| R8 | Validación: ninguna fila ni regla con `source_id` vacío o inexistente en `sources`. |
| R9 | Prueba: los endpoints de cálculo no escriben en la base de datos. Prueba: sin sesión, ningún endpoint de cuenta acepta escritura. Prueba: borrar la cuenta elimina usuario, sesiones, lotes, temporadas, tickets y sus eventos de `activity_log`. Revisión: el registro guarda el consentimiento y su versión. |
| R10 | Revisión: el rótulo de estimación aparece junto a todo resultado de riego y de suelo; se muestran rangos. Prueba: la señal de suelo nunca es crítica. |

## Señales del diagnóstico

Cinco señales independientes. Ninguna se promedia con otra (R2).

| Señal | Qué evalúa | Puede ser crítica |
|---|---|---|
| `rain` (lluvia) | Si la lluvia del semestre suele estar dentro de lo favorable para el cultivo | Sí |
| `frost` (heladas) | Qué tan frecuentes han sido las heladas en los meses en que el cultivo es sensible, para el mejor mes de siembra del semestre (el mismo cálculo del calendario del lote) | Sí |
| `soil` (suelo) | Si el pH del suelo de la zona, o del lote si se envía, está en el rango del cultivo. La textura y el carbono orgánico se muestran y alimentan las rotaciones, pero no esta señal | **No:** es una estimación de 250 m (R10) |
| `supply` (oferta) | Si en la zona se está sembrando mucho o poco del cultivo | Sí |
| `market` (mercado) | Si el precio suele bajar cuando sale la cosecha | Sí |

`frost` es `not_applicable` cuando ninguna etapa del cultivo es sensible a la helada según su ficha. El grado crítico de cada señal lo fija `thresholds.yaml`; la respuesta lo dice en el campo `critical`.

## Agregación del semáforo

Los umbrales viven en configuración versionada (`backend/config/`). Las reglas se aplican en orden:

1. Si `rain` u `supply` no están disponibles, la luz es `not_evaluable` y la acción es `review_data`.
2. Si alguna señal disponible es `unfavorable` y crítica, o dos señales disponibles son `unfavorable`, la luz es `red`.
3. Si `rain` es `favorable` y ninguna señal disponible es `unfavorable`, la luz es `green`.
4. En cualquier otro caso, la luz es `yellow`.
5. `frost`, `soil` y `market` sin datos **nunca cambian la luz**, pero se agregan a las limitaciones. `not_applicable` tampoco la cambia.

Acción según la luz:

| Luz | Acción |
|---|---|
| `green` | `sow` |
| `yellow` | `rotate` si `soil` es `unfavorable` (esperar no cambia el suelo); si no, `wait_other_semester` |
| `red` | `wait_other_semester` si todas las señales desfavorables son de clima (`rain`, `frost`); `rotate` si alguna es `soil`, `supply` o `market` |
| `not_evaluable` | `review_data` |

## Valores permitidos

| Campo | Valores |
|---|---|
| `status` | `available`, `insufficient_data`, `not_applicable` |
| `level` | `favorable`, `moderate`, `unfavorable` o nulo |
| `light` | `green`, `yellow`, `red`, `not_evaluable` |
| `action` | `sow`, `wait_other_semester`, `rotate`, `review_data` |
