# Fuentes de datos y de referencia

Todo dato y toda regla del proyecto debe apuntar a una entrada de la tabla `sources` (R8). Esta lista es el punto de partida; el estado de verificación se actualiza conforme se confirma.

## Datos

| Fuente | Qué aporta | Estado |
|---|---|---|
| NASA POWER (comunidad AG) | Series diarias por punto: precipitación, temperatura máxima y mínima y, para P1, humedad relativa. Consultas regionales de hasta 4,5° × 4,5°. Su respuesta trae la altura de la celda. | Documentación del cliente revisada; confirmar contra el enunciado del 28 de octubre (HU-002) |
| EVA / UPRA | Área sembrada, cosechada y producción por municipio, cultivo y semestre (desde 2019). Cobertura aproximada del 70 % de los municipios. Informe final 2024-2025 publicado hacia mayo de 2026; el último año es preliminar. | Verificar DIVIPOLA y definición de semestre (HU-001) |
| SIPSA / DANE | Precios y abastecimiento de alimentos. | **Sin verificar** cobertura de productos y mercados (HU-003) |
| IDEAM | Posible fuente complementaria de clima. | Sin verificar |
| UPRA zonificación de aptitud | Aptitud por cultivo. El mapa de papa es de 2020 y cubre solo Diacol Capiro industrial. | Uso limitado; citar con sus límites |
| SoilGrids (ISRIC) | pH, carbono orgánico, nitrógeno y textura a 250 m, con intervalo de predicción del 90 %. Licencia CC BY 4.0. (P0, EP-18) | Documentación revisada; verificar acceso (WCS) y versión en HU-181 |
| Modelo de elevación | Altitud de cada municipio para corregir la temperatura (HU-044). | Por elegir |
| UPRA e IDEAM (heladas) | Criterio de amenaza por helada: mínima menor que 2 °C. | Encontrado en un informe de la UPRA de enero de 2024; citar en HU-045 |
| DANE (límites municipales) | Códigos DIVIPOLA, nombres y centroides. | Por descargar |
| Open-Meteo (condiciones actuales) | Lluvia, nubes, viento y temperatura actuales por punto, de modelos con resolución de 15 minutos. Solo para el ambiente de la escena (decisión 7). | Elegida; licencia, atribución y límites de uso se verifican en HU-175 |
| NASA GIBS (imágenes satelitales casi en tiempo real) | Posible imagen del día para el nivel «satélite» de la escena (P1). | Sin verificar |

## Referencia

- Términos y condiciones de Space Apps 2025: no prohíben explícitamente preparar antes del evento y exigen citar todas las fuentes. **Hay que confirmar los de 2026 (HU-004).**
- Nota de prensa sobre Space Apps 2026: equipos de hasta 6 personas.
- FAO-56 (Allen et al.): evapotranspiración de referencia y coeficientes de cultivo (Kc).
- EVA 2024, UPRA e informe final EVA 2024-2025.

## Por citar al crear `catalog/sources.yaml`

Para cada entrada: `source_id`, `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `license`, `notes` (ver `specs/02-contratos.md`).
