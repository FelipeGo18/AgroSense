# Fuentes de datos y de referencia

Todo dato y toda regla del proyecto debe apuntar a una entrada de la tabla `sources` (R8). Esta lista es el punto de partida; el estado de verificación se actualiza conforme se confirma.

Un indicador puede tener varias fuentes: se muestran juntas para contrastarlas y nunca se mezclan. `sources.yaml` dice qué fuente calcula cada señal en cada región (decisión 11). Las fuentes de Colombia (EVA, SIPSA, IDEAM, UPRA, DANE, IGAC) son de la región piloto, que es un supuesto hasta que el reto confirme la región (HU-002).

## Datos

| Fuente | Qué aporta | Estado |
|---|---|---|
| NASA POWER (comunidad AG) | Series diarias por punto: precipitación, temperatura máxima y mínima y, para P1, humedad relativa. Consultas regionales de hasta 4,5° × 4,5°. Su respuesta trae la altura de la celda. | Documentación del cliente revisada; confirmar contra el enunciado del 28 de octubre (HU-002) |
| EVA / UPRA | Área sembrada, cosechada y producción por municipio, cultivo y semestre (desde 2019); es el único dato que va por semestre. Cobertura aproximada del 70 % de los municipios. Informe final 2024-2025 publicado hacia mayo de 2026; el último año es preliminar. | Verificar DIVIPOLA y definición de semestre (HU-001) |
| SIPSA / DANE | Precios y abastecimiento de alimentos. | **Sin verificar** cobertura de productos y mercados (HU-003) |
| IDEAM | Posible fuente complementaria de clima. | Sin verificar |
| UPRA zonificación de aptitud | Aptitud por cultivo. El mapa de papa es de 2020 y cubre solo Diacol Capiro industrial. | Uso limitado; citar con sus límites. No es la fuente de la aptitud por altitud del motor (HU-191) |
| Rango de altitud por cultivo (`altitude_min_m`, `altitude_max_m`) | Rango en que se da cada cultivo, para la aptitud en la zona (HU-191). | **Por elegir y confirmar con fuente** en HU-061. Candidatas sin verificar: FAO EcoCrop y fichas técnicas de Agrosavia. Sin fuente, el campo queda nulo y la aptitud en «datos insuficientes» |
| Temperatura máxima que aguanta cada cultivo (`heat_max_c`) | Umbral de la señal de calor (HU-190). | **Por elegir y confirmar con fuente** en HU-061. Candidatas sin verificar: FAO EcoCrop y fichas técnicas de Agrosavia. Sin fuente, el campo queda nulo y la señal en «datos insuficientes» |
| FAO EcoCrop | Rangos óptimos y límites absolutos por especie (temperatura, lluvia y otros), para las curvas de calificación de 0 a 100 (HU-196, HU-199). | **Candidata, por confirmar** en HU-199: acceso, licencia, qué especie o variedad describe cada ficha y la unidad de cada campo (por confirmar si la lluvia es anual). Datos globales: se contrastan con una fuente local cuando exista |
| FAOSTAT | Área sembrada y producción por país y año, como fuente de contraste de la oferta (HU-201, P1). | **Candidata, por confirmar**: licencia, cobertura y si sirve a una escala menor que el país. No es un dato municipal ni se presenta como tal |
| Reportes de portales públicos | Reportes descargados de portales oficiales o gremiales sobre siembras o precios, como fuentes de contraste (HU-201, P1). | **Por elegir** cuando se confirme la región. Cada uno con fecha de descarga, cobertura y licencia |
| Siembras registradas en AgroSense (`agrosense`) | Totales por municipio y cultivo de las temporadas en curso de los usuarios con cuenta, como fuente de contraste de la oferta (HU-200, P1). | Propia. Solo con al menos 5 cuentas y solo totales. Falta decidir cómo se versiona el corte (R4) y que el consentimiento lo diga (HU-163) |
| Agua que retiene el suelo según su textura | Método para llevar la textura de SoilGrids al balance de agua (HU-144). | **Por elegir y confirmar con fuente**. Candidata sin verificar: FAO-56 |
| Pesos por defecto (`weights.yaml`) | Cuánto pesa cada señal en el criterio de AgroSense (HU-198). | No es un dato con fuente: es un criterio del equipo, con quién lo definió y su porqué. No se cita una fuente que no lo diga |
| SoilGrids (ISRIC) | pH, carbono orgánico, nitrógeno y textura a 250 m, con intervalo de predicción del 90 %. Licencia CC BY 4.0. (P0, EP-18) | Documentación revisada; verificar acceso (WCS) y versión en HU-181 |
| Modelo de elevación | Altitud de cada municipio para corregir la temperatura (HU-044). | Por elegir |
| UPRA e IDEAM (heladas) | Criterio de amenaza por helada: mínima menor que 2 °C. | Encontrado en un informe de la UPRA de enero de 2024; citar en HU-045 |
| Natural Earth (vía `world-atlas` 2.0.2) | Contornos de continentes y países para la Tierra del inicio. Dominio público. | Elegida |
| NASA Earth Observatory · Blue Marble: Next Generation (diciembre de 2004) | Color de las facetas de tierra del globo. Hay que acreditar «NASA Earth Observatory». | Elegida; solo para la imagen del inicio, no entra en ningún cálculo |
| Font Awesome Free 6.5.2 (íconos de marca) | Logos originales de GitHub, Instagram, LinkedIn y YouTube del pie de página, con los colores de cada marca. Íconos con licencia CC BY 4.0: se acredita en el código (`design/pantallas/marcas.py`). | Elegida |
| DANE (límites municipales) | Códigos DIVIPOLA, nombres y centroides. | Por descargar |
| Open-Meteo (condiciones actuales) | Lluvia, nubes, viento y temperatura actuales por punto, de modelos con resolución de 15 minutos. Solo para el ambiente de la escena (decisión 7). | Elegida; licencia, atribución y límites de uso se verifican en HU-175 |
| NASA GIBS (imágenes satelitales casi en tiempo real) | Posible imagen del día para el nivel «satélite» de la escena (P1). | Sin verificar |

## Referencia

- Términos y condiciones de Space Apps 2025: no prohíben explícitamente preparar antes del evento y exigen citar todas las fuentes. **Hay que confirmar los de 2026 (HU-004).**
- Nota de prensa sobre Space Apps 2026: equipos de hasta 6 personas.
- FAO-56 (Allen et al.): evapotranspiración de referencia y coeficientes de cultivo (Kc).
- Método de la FAO para la evaluación de aptitud de tierras (factor limitante): base del orden de ventanas (decisión 10). Cita exacta por confirmar.
- EVA 2024, UPRA e informe final EVA 2024-2025.

## Por citar al crear `catalog/sources.yaml`

Para cada entrada: `source_id`, `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `coverage`, `license`, `notes` (ver `specs/02-contratos.md`). Además, por región, qué fuente calcula cada señal.
