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

**Resultado esperado:** Las tablas de clima de la región (`climate_semester`, `climate_month`, `climate_day` y `climate_risk_month`), con temperaturas corregidas por altitud, anomalías respecto a lo normal y frecuencia de heladas por mes.

## Historias de usuario

### HU-041 · Series diarias de lluvia y temperatura

- **Historia:** Como motor, quiero series diarias de lluvia y temperatura por municipio, para evaluar el clima de cada semestre.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Descarga con caché y reintentos
  - [ ] Fuente y fecha registradas
  - [ ] Días faltantes contados en `valid_days`
  - [ ] Publica `climate_day` (mínima y máxima diarias corregidas por altitud) para la etapa del cultivo (HU-150)

### HU-042 · Total, normal y anomalía por semestre

- **Historia:** Como motor, quiero el total, la normal y la anomalía por semestre, para saber si una ventana suele ser seca o lluviosa.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Periodo base de la normal documentado
  - [ ] Comprobación manual en 2 municipios
  - [ ] Calidad `partial` bajo un mínimo de días válidos

### HU-043 · Humedad del suelo y NDVI

- **Historia:** Como motor, quiero humedad del suelo y NDVI por municipio, para enriquecer las señales de lluvia y el aviso de riego.
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

### HU-045 · Frecuencia de heladas por mes

- **Historia:** Como motor, quiero saber en qué meses suele helar en cada municipio, para avisar el riesgo en el diagnóstico y en el calendario.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `climate_risk_month` con `frost_freq_pct`, `frost_days_mean`, `years` y `quality`, desde la mínima diaria corregida por altitud
  - [ ] Umbral de helada: mínima menor que 2 °C a 2 m, con fuente (UPRA e IDEAM)
  - [ ] Comprobación: los meses con más heladas en el altiplano caen entre diciembre y marzo, como dicen la Gobernación de Boyacá y el IDEAM
- **Reglas que aplican:** R1, R8

### HU-046 · Aguaceros, ventanas secas y gota por mes

- **Historia:** Como agricultor, quiero saber en qué meses suelen caer aguaceros, cuándo hay días secos seguidos y cuándo el clima favorece la gota, para decidir cuándo abonar, cuándo hacer labores y cosechar, y cuándo vigilar mi papa.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `heavy_rain_days_mean`, `dry_window_freq_pct` y `blight_days_mean` en `climate_risk_month`, con umbrales con fuente
  - [ ] La gota usa humedad relativa (`RH2M`) y temperatura de NASA POWER con una regla publicada
- **Notas:** Ver `docs/investigacion-decisiones.md`. La humedad de NASA POWER es de celda de unos 50 km: se presenta como orientación.
