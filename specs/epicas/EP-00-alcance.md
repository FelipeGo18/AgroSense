---
id: EP-00
titulo: "Alcance piloto decidido con datos reales"
prioridad: P0
fase: [Fase 0]
rol: "Producto y agro, con Datos"
agentes: [producto-agro, datos]
subsistemas: [D1, AG1]
depende_de: [Enunciado del 28 de octubre]
reglas: [R7, R8]
estado: pendiente
---

# EP-00 · Alcance piloto decidido con datos reales

**Resultado esperado:** Región, cultivos, periodos y fuentes elegidos con base en la cobertura real comprobada.

**Sede y región confirmadas (28 de octubre de 2026).** La sede oficial del equipo es **Duitama (Boyacá, Colombia)** y la región piloto queda confirmada en el altiplano de **Boyacá y Cundinamarca, Colombia** (`co-boyaca-cundinamarca`). Lo propio de Colombia (EVA, DIVIPOLA, SIPSA, IDEAM, UPRA, IGAC, Ley 1581) sigue viviendo en los adaptadores de cada fuente y en `sources.yaml`, no en el modelo (R7).

## Historias de usuario

### HU-001 · Comparar la cobertura de EVA y elegir región

- **Historia:** Como equipo, quiero comparar la cobertura de EVA para papa y cultivos de rotación por municipio, para elegir una región con datos completos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tabla de cobertura por municipio y semestre desde 2019
  - [ ] Región elegida con justificación escrita
  - [ ] Lista de municipios habilitados

### HU-002 · Confirmar los datasets NASA del enunciado

- **Historia:** Como equipo, quiero confirmar los datasets NASA que propone el enunciado, para no construir sobre datos que no aplican.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Variables, resolución, periodo y forma de acceso documentados
  - [ ] Descarga de prueba para un municipio
  - [ ] Dice si el enunciado fija una región o unos datos. Si no es compatible con la región piloto, se registra en `docs/registro-de-decisiones.md` y se lista qué adaptadores y entradas de `sources.yaml` hay que cambiar
  - [x] Cada producto NASA que recomiende el enunciado y no esté en el MVP (POWER, NASADEM, IMERG, MODIS NDVI, SMAP, GIBS) queda listado con su HU nueva, que entra por su propio adaptador (decisión 12). **8 de noviembre de 2026 (decisión 14):** el enunciado sugiere SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE y GRACE-FO, y SRTM u otro modelo de elevación (y nombra GEDI como ejemplo). Faltaban GRACE-FO (HU-225) y ECOSTRESS (HU-226); Landsat sigue en HU-043 (HLS); GEDI no entra
  - [ ] Revisar la pestaña de recursos del reto el viernes 13 de noviembre, cuando se publica, y agregar lo que traiga
  - [x] La sede del equipo queda confirmada (**Duitama, Boyacá, Colombia**, confirmada el 28 de octubre de 2026; aprobado por Felipe, 8 de noviembre de 2026) y la región piloto se mantiene en el altiplano de Boyacá y Cundinamarca, registrada en `docs/registro-de-decisiones.md`
- **Notas:** El 28 de octubre de 2026 se confirmó la sede **Duitama (Boyacá)** y la región piloto en Boyacá y Cundinamarca, manteniendo intacto el enfoque de no pronóstico (R1–R10). El enunciado completo se leyó el 8 de noviembre de 2026 (decisión 14). Faltan los recursos del 13 de noviembre y la descarga de prueba. Criterios de los productos NASA y de la sede agregados el 11 de octubre de 2026.

### HU-003 · Verificar SIPSA y decidir si entra al P0

- **Historia:** Como equipo, quiero verificar SIPSA (productos, mercados, frecuencia y última fecha), para decidir si la señal de mercado entra al P0.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Decisión «entra» o «no entra» documentada: **entra**, aprobado por Felipe el 10 de noviembre de 2026 (propuesta de Datos abajo)
  - [x] Si entra, mapeo de producto SIPSA a `crop_id`: `pipeline/sipsa_crops.yaml`, validado por `pipeline.build` contra los precios publicados (`tests/pipeline/test_cultivos_sipsa.py`)
- **Verificación (7 de noviembre de 2026, con la descarga de SIPSA del 20 de octubre):** el servicio web del DANE (`promediosSipsaParcial`, sin cuenta) trae el precio mínimo, medio y máximo por kilo de cada producto, central y día desde el 1 de febrero de 2020, hasta el día anterior a la descarga. Corabastos publica 36 productos unos seis días por semana; Tunja, 33, unos tres. Para los 7 cultivos del MVP:

  | `crop_id` | Producto de SIPSA | Corabastos | Tunja |
  |---|---|---|---|
  | `papa` | Papa negra* | Precios e índice estacional (2021–2025) | Sin precios desde el 27 de julio de 2021: sin índice |
  | `arveja` | Arveja verde en vaina | Precios e índice (2021–2025) | Precios e índice (2021–2025) |
  | `cebolla_bulbo` | Cebolla cabezona blanca | Precios e índice (2021–2025) | Precios e índice (2021–2025) |
  | `zanahoria` | Zanahoria | Precios e índice (2021–2025) | Precios e índice (2021–2025) |
  | `haba` | — | SIPSA no publica haba en ninguna central | — |
  | `maiz` | — | SIPSA no publica maíz en grano en ninguna central; «Chócolo mazorca» es maíz tierno y no lo representa: queda sin producto (decidido por Felipe el 10 de noviembre de 2026) | — |
  | `avena_vicia` | — | Abono verde: no se vende ni tiene diagnóstico | — |

  «Papa criolla» y «Cebolla junca» son otros cultivos y no entran. El porqué de cada fila está en `pipeline/sipsa_crops.yaml`.
- **Propuesta de Datos (aprobado por Felipe el 10 de noviembre de 2026):** **entra.** Los datos de SIPSA alimentan la señal `market` del P0 en 4 de los 6 cultivos con diagnóstico (papa, arveja, cebolla de bulbo y zanahoria). En haba y maíz la señal es `insufficient_data` (R1): no cambia la luz y queda en las limitaciones (regla 5 de «Agregación del semáforo»). Por qué: el adaptador, sus validaciones y la actualización diaria ya existen (HU-221, HU-222); cubre las dos centrales de referencia de la región con más de seis años de precios; el índice estacional ya se calcula. `market_month` por cultivo ya se publica (HU-051, 7 de noviembre); lo que falta es la parte de datos de la señal (HU-073). Si se aprueba, HU-051 pasa a P0. Si no, la señal `market` queda en `insufficient_data` en el MVP y `/precios` sigue como P1. La licencia lo permite: los términos del DANE autorizan el uso y la transformación de los datos con su cita (verificado el 8 de noviembre en HU-221).

### HU-004 · Confirmar qué se puede preparar antes del evento

- **Historia:** Como equipo, quiero confirmar en los términos de 2026 y con el evento local qué se puede preparar antes, para no arriesgar la entrega.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Regla citada con enlace: «2026 NASA Space Apps Participant Terms and Conditions», actualizados el 7 de agosto de 2026 (https://www.spaceappschallenge.org/legal/), leídos por Felipe el 10 de noviembre de 2026. No limitan cuándo se crea el trabajo: el contenido original es el «created for the NASA Space Apps Challenge», no el creado durante el fin de semana. Lo que sí exigen: que el contenido original sea libre o tenga una licencia OSI (sin licencia, NASA lo publica con Apache 2.0); que el material de terceros (datos o código que no son de la NASA ni de otra agencia espacial) sea libre o tenga licencia OSI y que su licencia vaya en la documentación de la entrega; citar **todas** las fuentes, también las abiertas, o se pierde el premio; tener los derechos de todo lo que se entrega, y no incluir datos personales ni publicidad de productos comerciales
  - [x] Respuesta escrita de la sede local sobre si se puede llevar código preparado (pipeline, motor, web) o solo diseños, guías y datos. **Sí se puede llevar código preparado:** confirmado por Felipe el 8 de noviembre de 2026
  - [x] Plan ajustado si cambia lo permitido (`docs/plan-48h.md`, los dos casos): aplica el escenario «Se puede llevar código y datos preparados»; el orden de recorte no se aplica desde el inicio
- **Notas:** **Urgente: se hace esta semana (antes del 17 de octubre de 2026).** Define todo el plan: si se puede llevar código, los datos NASA y las fichas llegan hechos al evento; si no, el P0 del evento supera de lejos las horas del equipo (`docs/plan-48h.md`). Marcada urgente el 11 de octubre de 2026.
