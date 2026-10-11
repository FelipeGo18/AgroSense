---
id: EP-14
titulo: "Finca y plan de agua"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web, Datos y Producto y agro"
agentes: [motor-api, web, datos, producto-agro]
subsistemas: [AG1, D3, M1, M7, W7]
depende_de: [EP-04, EP-06]
reglas: [R1, R2, R4, R6, R9, R10]
estado: pendiente
---

# EP-14 · Finca y plan de agua

**Resultado esperado:** El agricultor ve, mes a mes, cuándo conviene sembrar cada cultivo y cuándo hay riesgo de helada (calendario). Además, registra su finca (sin cuenta, como finca temporal en su dispositivo con el porcentaje del terreno de cada cultivo; con cuenta, como lotes de EP-16) y ve cuánta agua necesitará cada uno y en qué meses o semanas es probable que tenga que regar. El P0 da las semanas típicas de déficit con el clima histórico; saber el día exacto exige medir la humedad del lote o tener pronóstico, por eso el aviso semanal queda en P1.

HU-142 (etapas y Kc) se hace en la fase 0; el resto, en el evento.

## Historias de usuario

### HU-141 · Registrar la finca

- **Historia:** Como agricultor, quiero registrar mi finca con su área total, el porcentaje de cada cultivo y su fecha de siembra, para recibir un plan a mi medida.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Área en hectáreas; solo cultivos del catálogo
  - [ ] Los porcentajes suman como máximo 100 %; el resto se muestra como descanso
  - [ ] Sin cuenta, los datos no salen del dispositivo; con cuenta, se guardan como lotes (EP-16)

### HU-142 · Etapas de cada cultivo con Kc

- **Historia:** Como motor, quiero las etapas de cada cultivo con su duración y coeficiente de cultivo (Kc), para estimar su consumo de agua.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Valores de FAO-56 o de una fuente local, citados
  - [ ] Revisión cruzada por otro integrante
- **Notas:** Se hace en la fase 0.

### HU-150 · Etapa del cultivo por temperatura acumulada

- **Historia:** Como agricultor, quiero que la etapa de mi cultivo siga la temperatura real de mi zona, para ver el lote más cerca de como está de verdad.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El catálogo guarda, por cultivo, la temperatura base y la temperatura acumulada (grados-día) que cierra cada etapa, con su fuente (R8)
  - [ ] El motor calcula la etapa del lote con la temperatura diaria del municipio (NASA POWER) acumulada desde la fecha de siembra
  - [ ] La respuesta dice con qué método se calculó (`thermal_time` o `calendar`) y hasta qué fecha llegan los datos de temperatura
  - [ ] Si faltan datos de temperatura o el cultivo no tiene grados-día con fuente, se usa la duración por calendario de HU-142 y se dice en pantalla: nunca se sustituye en silencio (R1)
  - [ ] La web muestra «etapa estimada con la temperatura de la zona» junto a la etapa, y la fecha del último dato
  - [ ] Caso de referencia del motor: misma fecha de siembra, un semestre frío y uno cálido dan etapas distintas
- **Reglas que aplican:** R1, R4, R5, R6, R8
- **Notas:** Es una estimación con el clima del municipio, no una observación del lote: NASA POWER da un punto por municipio y publica con 2 a 7 días de retraso. No predice rendimiento ni fecha de cosecha. Contrato aprobado por Felipe el 10 de octubre de 2026: tabla `climate_day`, `base_temp_c` en `crops`, `gdd` en `crop_stages` y la etapa en la respuesta de `GET /api/v1/lots/{lot_id}`. Falta el catálogo de grados-día con fuente por cultivo. Decidido el 10 de octubre de 2026 (ver `docs/registro-de-decisiones.md`).

### HU-143 · Lluvia y ET0 mensuales por municipio

- **Historia:** Como motor, quiero la lluvia y la evapotranspiración de referencia (ET0) mensuales por municipio, con su normal y un año seco, para calcular el balance de agua.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] ET0 por Hargreaves con temperatura máxima y mínima, método documentado
  - [ ] Año seco definido como un percentil bajo de la serie
  - [ ] Comprobación manual en un municipio

### HU-144 · Déficit de agua por cultivo y etapa

- **Historia:** Como agricultor, quiero saber cuánta agua le falta a cada cultivo según su etapa, para planear el riego.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Déficit = ET0 × Kc menos lluvia efectiva, por cultivo y mes
  - [ ] Volumen en m³ según el área de cada cultivo
  - [ ] Año normal y año seco; misma entrada, mismo resultado

### HU-145 · Calendario de riego de la finca

- **Historia:** Como agricultor, quiero un calendario de riego de mi finca, para saber en qué semanas o meses regar y cuánto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Meses de déficit resaltados por cultivo, con rangos
  - [ ] Volumen total de la finca
  - [ ] Rótulo: «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote»

### HU-146 · Endpoint del plan de agua

- **Historia:** Como desarrollador web, quiero el endpoint del plan de agua, para mostrar el calendario.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] 422 si los porcentajes pasan de 100 o el cultivo no existe
  - [ ] No persiste los datos de la finca

### HU-179 · Calendario del cultivo

- **Historia:** Como agricultor, quiero ver mes a mes cuándo conviene sembrar mi cultivo y cuándo hay riesgo de helada en mi zona, para elegir el mes de siembra y no solo el semestre.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /api/v1/calendar` según el contrato, con `sowing` y `frost` por mes y `best_sowing_months`
  - [ ] `sowing` combina el balance de agua de la etapa inicial (M7) y el riesgo de helada en las etapas sensibles; nunca promedia (R2)
  - [ ] Misma entrada, misma salida; trae `versions` (R4); no guarda nada (R9)
  - [ ] La señal `frost` del diagnóstico (HU-077) sale de este mismo cálculo
- **Reglas que aplican:** R1, R2, R4, R6, R9
- **Notas:** Los bloques `fertilizing`, `field_work` y `blight` llegan en P1 con HU-046.

### HU-180 · Vista del calendario

- **Historia:** Como agricultor, quiero ver el calendario de mi cultivo de un vistazo, junto con los meses de riego de mi lote, para planear el año.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Doce meses con los mejores meses de siembra y el riesgo de helada, con forma y texto, no solo color
  - [ ] Con temporada en curso, suma los meses de riego del plan de agua (HU-145) sin repetir el cálculo
  - [ ] Disponible sin cuenta desde la consulta y con cuenta en cada lote
  - [ ] Cada control tiene una función; nada decorativo
- **Reglas que aplican:** R1, R5, R10

### HU-186 · Línea de tiempo del cultivo

- **Historia:** Como agricultor, quiero mover el tiempo y ver cómo crece mi cultivo, desde la siembra hasta la cosecha, para entender en qué va y qué viene.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_normal_doy` publicada por el pipeline, con fuente
  - [ ] `GET /api/v1/seasons/{season_id}/growth` según el contrato: `observed` hasta `thermal_data_until`, `normal_year` después
  - [ ] Misma entrada, misma salida; trae `versions` (R4)
  - [ ] Sin temperatura o sin grados-día con fuente: duración por calendario y se dice (R1)
- **Reglas que aplican:** R1, R4, R5, R6
- **Notas:** Reutiliza el cálculo de HU-150. Lo que viene después de hoy es una estimación con un año normal, nunca un pronóstico (decisión 4). Decidido el 11 de octubre de 2026.

### HU-147 · Aviso de riego semanal

- **Historia:** Como agricultor, quiero un aviso de riego para esta semana con la lluvia más reciente, para decidir con datos actuales.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usa los últimos datos disponibles de NASA y muestra su fecha
  - [ ] Dice explícitamente que no es un pronóstico

### HU-148 · Rotaciones ponderadas por área

- **Historia:** Como agricultor, quiero que las rotaciones tengan en cuenta cuánto terreno tengo de cada cultivo, para que la recomendación sea realista.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Los criterios de agua e ingreso se ponderan por área

### HU-149 · Guardar la finca en el dispositivo

- **Historia:** Como agricultor sin cuenta, quiero guardar mi finca en este dispositivo, para no escribirla cada vez.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Se guarda solo en el navegador y se puede borrar
  - [ ] La página funciona aunque el navegador no permita guardar
