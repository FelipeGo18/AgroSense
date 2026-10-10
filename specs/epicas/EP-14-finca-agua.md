---
id: EP-14
titulo: "Finca y plan de agua"
prioridad: "P0"
fase: "Evento"
rol: "Web, Motor y API, Datos y Producto y agro"
agente: motor-api
subsistemas: "AG1, D3, M7, W7"
depende_de: "EP-04, EP-06"
reglas: "R9, R10"
estado: pendiente
---

# EP-14 · Finca y plan de agua

**Resultado esperado:** El agricultor registra su finca con el porcentaje del terreno de cada cultivo y ve cuánta agua necesitará cada uno y en qué meses o semanas es probable que tenga que regar. El P0 da las semanas típicas de déficit con el clima histórico; saber el día exacto exige medir la humedad del lote o tener pronóstico, por eso el aviso semanal queda en P1.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | Evento |
| Rol responsable | Web, Motor y API, Datos y Producto y agro |
| Agente sugerido | `motor-api` (ver `.claude/agents/`) |
| Subsistemas | AG1, D3, M7, W7 (ver `specs/03-sistemas.md`) |
| Depende de | EP-04, EP-06 |
| Reglas de diseño que aplican | R9, R10 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-141 · Registrar la finca

- **Historia:** Como agricultor, quiero registrar mi finca con su área total, el porcentaje de cada cultivo y su fecha de siembra, para recibir un plan a mi medida.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Área en hectáreas; solo cultivos del catálogo
  - [ ] Los porcentajes suman como máximo 100 %; el resto se muestra como descanso
  - [ ] Los datos no se guardan en el servidor
- **Notas:** —

### HU-142 · Etapas de cada cultivo con Kc

- **Historia:** Como motor, quiero las etapas de cada cultivo con su duración y coeficiente de cultivo (Kc), para estimar su consumo de agua.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Valores de FAO-56 o de una fuente local, citados
  - [ ] Revisión cruzada por otro integrante
- **Notas:** Se hace en la fase 0.

### HU-143 · Lluvia y ET0 mensuales por municipio

- **Historia:** Como motor, quiero la lluvia y la evapotranspiración de referencia (ET0) mensuales por municipio, con su normal y un año seco, para calcular el balance de agua.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] ET0 por Hargreaves con temperatura máxima y mínima, método documentado
  - [ ] Año seco definido como un percentil bajo de la serie
  - [ ] Comprobación manual en un municipio
- **Notas:** —

### HU-144 · Déficit de agua por cultivo y etapa

- **Historia:** Como agricultor, quiero saber cuánta agua le falta a cada cultivo según su etapa, para planear el riego.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Déficit = ET0 × Kc menos lluvia efectiva, por cultivo y mes
  - [ ] Volumen en m³ según el área de cada cultivo
  - [ ] Año normal y año seco; misma entrada, mismo resultado
- **Notas:** —

### HU-145 · Calendario de riego de la finca

- **Historia:** Como agricultor, quiero un calendario de riego de mi finca, para saber en qué semanas o meses regar y cuánto.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Meses de déficit resaltados por cultivo, con rangos
  - [ ] Volumen total de la finca
  - [ ] Rótulo: «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote»
- **Notas:** —

### HU-146 · Endpoint del plan de agua

- **Historia:** Como desarrollador web, quiero el endpoint del plan de agua, para mostrar el calendario.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] 422 si los porcentajes pasan de 100 o el cultivo no existe
  - [ ] No persiste los datos de la finca
- **Notas:** —

### HU-147 · Aviso de riego semanal

- **Historia:** Como agricultor, quiero un aviso de riego para esta semana con la lluvia más reciente, para decidir con datos actuales.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usa los últimos datos disponibles de NASA y muestra su fecha
  - [ ] Dice explícitamente que no es un pronóstico
- **Notas:** —

### HU-148 · Rotaciones ponderadas por área

- **Historia:** Como agricultor, quiero que las rotaciones tengan en cuenta cuánto terreno tengo de cada cultivo, para que la recomendación sea realista.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Los criterios de agua e ingreso se ponderan por área
- **Notas:** —

### HU-149 · Guardar la finca en el dispositivo

- **Historia:** Como agricultor, quiero guardar mi finca en este dispositivo, para no escribirla cada vez.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Se guarda solo en el navegador y se puede borrar
  - [ ] La página funciona aunque el navegador no permita guardar
- **Notas:** —
