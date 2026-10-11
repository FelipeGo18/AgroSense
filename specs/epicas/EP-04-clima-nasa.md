---
id: EP-04
titulo: "Dataset climático publicado"
prioridad: P0
fase: [Evento]
rol: "Datos"
agentes: [datos]
subsistemas: [D1, D2, D3, D4]
depende_de: [HU-002, HU-011]
reglas: [R5, R7, R8]
estado: pendiente
---

# EP-04 · Dataset climático publicado

**Resultado esperado:** Las tablas de clima de la región (`climate_day`, `climate_month`, `climate_risk_month` y `climate_risk_week`), con temperaturas corregidas por altitud, lluvia mensual con su normal y su año seco, y frecuencia de heladas y temperatura máxima por mes y por semana. Con ellas el motor evalúa cualquier ventana de siembra.

Ninguna tabla de clima va por semestre: el semestre solo existe en la oferta de EVA (EP-03).

**Supuesto de la región piloto (decisión 11):** el reto aún no confirma la región ni los datos (HU-002, enunciado del 28 de octubre). NASA POWER cubre todo el mundo, pero varias piezas de esta épica son de Colombia: los municipios y sus límites del DANE, el criterio de helada de la UPRA con datos del IDEAM, la comprobación contra estaciones del IDEAM y contra la Gobernación de Boyacá. Esas piezas viven en los adaptadores y en la configuración del pipeline, no en el motor (R7). Si la región cambia, se reemplazan con su fuente.

## Historias de usuario

### HU-041 · Series diarias de lluvia y temperatura

- **Historia:** Como motor, quiero series diarias de lluvia y temperatura por municipio, para evaluar el clima de cada ventana de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Descarga con caché y reintentos
  - [ ] Fuente y fecha registradas
  - [ ] Días faltantes o incompletos marcados en `quality` (`climate_day`); nunca se rellenan (R1)
  - [ ] Publica `climate_day` (mínima y máxima diarias corregidas por altitud) para la etapa del cultivo (HU-150)

### HU-042 · Lluvia mensual y su normal

- **Historia:** Como motor, quiero la lluvia de cada mes de cada año y su normal por municipio, para saber cuánta agua suele caer en los meses de una ventana de siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_month` con `precip_mm` por `municipality_id`, `year` y `month`, y `precip_normal_mm`, con `quality` y `source_id`
  - [ ] Periodo base de la normal documentado
  - [ ] Comprobación manual en 2 municipios
  - [ ] Calidad `partial` bajo un mínimo de días válidos; un mes sin días válidos no se publica con un valor rellenado (R1)
- **Reglas que aplican:** R1, R7, R8
- **Contrato que toca:** `climate_month`
- **Notas:** Antes publicaba el total y la anomalía de un periodo fijo de seis meses, en una tabla que ya no existe: cambió el 11 de octubre de 2026. El año seco (`precip_dry_mm`) y la ET0 de la misma tabla los agrega HU-143. La señal de agua (HU-071) y la serie `water` de `/trends` leen esta tabla.

### HU-043 · Humedad del suelo y NDVI

- **Historia:** Como motor, quiero humedad del suelo y NDVI por municipio, para enriquecer la señal de agua y el aviso de riego.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Extracción por polígono municipal
  - [ ] Mismas reglas de calidad
- **Notas:** Con los lotes dibujados en el mapa (HU-164) se puede ir más fino: el NDVI de HLS (Harmonized Landsat Sentinel-2, de la NASA, 30 m) por polígono de lote mostraría el verdor real del cultivo. Un lote de 1,5 ha cubre unos 16 píxeles; las nubes del altiplano dejan huecos. Por evaluar en P1.

### HU-044 · Municipios, límites, altitud y corrección de la temperatura

- **Historia:** Como motor, quiero la altitud de cada municipio y la de su celda de NASA POWER, para corregir la temperatura y filtrar cultivos por piso térmico.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `altitude_m` desde un modelo de elevación o fuente oficial, con fuente
  - [ ] `climate_cell_elevation_m` desde la respuesta de NASA POWER
  - [ ] Todas las temperaturas publicadas se corrigen con un gradiente térmico con fuente; el gradiente vive en la configuración del pipeline
  - [ ] Comprobación manual en 2 municipios contra una estación del IDEAM, si la hay
- **Reglas que aplican:** R7, R8
- **Notas:** También publica `municipalities` (con `source_ids`) y `municipality_boundaries` desde el Marco Geoestadístico Nacional del DANE, que usan HU-164, HU-181 y HU-078. Pasa a P0 el 10 de octubre de 2026 porque las heladas dependen de la temperatura mínima, y la celda de unos 50 km puede estar cientos de metros más arriba o más abajo que el municipio.

### HU-045 · Heladas y temperatura máxima por mes

- **Historia:** Como motor, quiero saber en qué meses suele helar y qué tan alta suele ser la temperatura máxima en cada municipio, para avisar el riesgo de helada y de calor en el calendario del cultivo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_risk_month` con `frost_freq_pct`, `frost_days_mean`, `tmax_p90_c`, `years` y `quality`, desde la mínima y la máxima diarias corregidas por altitud
  - [ ] Umbral de helada: mínima menor que 2 °C a 2 m, con fuente (UPRA e IDEAM; supuesto de la región piloto), en la configuración del pipeline
  - [ ] `tmax_p90_c` es la temperatura máxima que se supera uno de cada diez días de ese mes; el método queda documentado
  - [ ] Comprobación: los meses con más heladas en el altiplano caen entre diciembre y marzo, como dicen la Gobernación de Boyacá y el IDEAM
  - [ ] Con pocos años o pocos días válidos, `quality = partial`; sin datos, la fila no se publica (R1)
- **Reglas que aplican:** R1, R8
- **Contrato que toca:** `climate_risk_month`
- **Notas:** Antes se llamaba «Frecuencia de heladas por mes»; sumó `tmax_p90_c` el 11 de octubre de 2026 para la señal de calor (HU-190). La versión por semana es HU-193.

### HU-193 · Riesgo climático por semana

- **Historia:** Como motor, quiero el riesgo de helada, la temperatura máxima, la lluvia y la ET0 normales por semana del año en cada municipio, para comparar ventanas de siembra dentro de un mismo mes.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_risk_week` por `municipality_id` y `week` (1 a 52; los días 365 y 366 van a la semana 52) con `frost_freq_pct`, `tmax_p90_c`, `precip_normal_mm`, `precip_dry_mm`, `et0_normal_mm`, `years`, `quality` y `source_id`, según el contrato
  - [ ] Cada valor se suaviza con las semanas vecinas; el método y el ancho del suavizado quedan documentados y viven en la configuración del pipeline
  - [ ] Mismas temperaturas corregidas por altitud y mismo umbral de helada que HU-045
  - [ ] Unicidad de la llave: 52 filas por municipio (R7)
  - [ ] Comprobación manual en 2 municipios: las semanas de un mes son coherentes con el valor de ese mes en `climate_risk_month`
  - [ ] Con pocos años válidos, `quality = partial`; nunca se rellena una semana sin datos (R1)
- **Reglas que aplican:** R1, R7, R8
- **Contrato que toca:** `climate_risk_week`
- **Notas:** El dato semanal es más ruidoso que el mensual: por eso se suaviza y se presenta como orientación (`docs/riesgos.md`). Los días 365 y 366 van a la semana 52 (`specs/02-contratos.md`, `climate_risk_week`). Supuesto por confirmar: qué es exactamente «un año con helada» en una semana suavizada. Depende de HU-041 y HU-044; la ET0 usa el método de HU-143. Lo usan HU-077, HU-190 y HU-192. Las columnas del P1 las agrega HU-046. Agregada el 11 de octubre de 2026.

### HU-046 · Aguaceros, ventanas secas y gota por mes

- **Historia:** Como agricultor, quiero saber en qué meses suelen caer aguaceros, cuándo hay días secos seguidos y cuándo el clima favorece la gota, para decidir cuándo abonar, cuándo hacer labores y cosechar, y cuándo vigilar mi papa.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `heavy_rain_days_mean`, `dry_window_freq_pct` y `blight_days_mean` en `climate_risk_month` y en `climate_risk_week`, con umbrales con fuente
  - [ ] La gota usa humedad relativa (`RH2M`) y temperatura de NASA POWER con una regla publicada
- **Notas:** Ver `docs/investigacion-decisiones.md`. La humedad de NASA POWER es de celda de unos 50 km: se presenta como orientación. Con estos datos el motor arma las señales `excess_rain`, `disease` y `harvest_weather` (HU-195).

### HU-188 · Riesgos que cubre un seguro, por municipio

- **Historia:** Como agricultor, quiero saber qué tan seguido han ocurrido en mi zona los riesgos que cubre un seguro agropecuario, para decidir si aseguro la cosecha.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Frecuencia histórica por municipio y mes de helada, sequía y exceso de lluvia, con umbrales con fuente
  - [ ] La web la muestra en «Próxima siembra» con el enlace oficial al Incentivo al Seguro Agropecuario
  - [ ] No recomienda un seguro, una aseguradora ni un producto; es frecuencia histórica, no pronóstico
- **Reglas que aplican:** R5, R8
- **Notas:** Ver `docs/investigacion-decisiones.md`, decisión 9. Agregada el 11 de octubre de 2026.

### HU-189 · Lluvia en años de El Niño y La Niña

- **Historia:** Como agricultor, quiero ver cómo fue la lluvia de los meses de mi ventana de siembra en los años de El Niño y de La Niña del pasado, para saber qué tanto cambia mi zona en esos años.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Lluvia de cada mes por municipio en años El Niño, La Niña y neutros, frente al promedio de los neutros, con el índice y su fuente; la web suma los meses de la ventana
  - [ ] La web la muestra en «Próxima siembra» con el enlace al boletín oficial
  - [ ] No dice en qué fase estamos ni la presenta como pronóstico propio: la fase actual solo se cita del boletín oficial
- **Reglas que aplican:** R5, R8
- **Notas:** Ver `docs/investigacion-decisiones.md`, decisión 10. Cómo mostrar la fase actual sigue por decidir. Agregada el 11 de octubre de 2026.
