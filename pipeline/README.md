# Pipeline de datos de AgroSense

Descarga las fuentes a una caché, las valida y publica el dataset que lee la API (`data/published/`: Parquet y
`manifest.json`). Contrato de las tablas: `specs/02-contratos.md`, «Tablas publicadas».

```bash
uv run python -m pipeline.build --descargar   # baja las fuentes a data/raw/ y publica
uv run python -m pipeline.build               # publica otra vez desde la caché, sin red
uv run python -m pipeline.build --verificar   # solo revisa que data/published coincida con su manifiesto
```

- Al terminar de publicar, el comando revisa lo publicado contra su manifiesto (HU-123): cada tabla que nombra existe y
  tiene sus filas, no hay tablas que no nombre y la versión es la de `region.yaml`. Si algo no coincide, termina con
  error. Desde la misma caché, reconstruir da los mismos archivos byte a byte (R4); solo cambia `created_at`.
- Cada paso deja una línea en la terminal (HU-177): por fuente, las filas leídas, las que quedan y las descartadas con su
  motivo; por tabla, las filas escritas; al final, si se publicó o por qué no. Nivel y formato con `AGROSENSE_LOG_LEVEL`
  y `AGROSENSE_LOG_FORMAT` (`console` o `json`), igual que la API.

- `data/raw/` es caché y no va a git. `data/published/` sí va a git y entra en la imagen de Docker: es el dataset de la demo.
- `pipeline/region.yaml` dice la región y la versión del dataset: **Boyacá y Cundinamarca, Colombia** (confirmada el 28 de octubre de 2026 con la sede de Duitama, HU-002). `dataset_version` sube a mano cada vez que cambia lo publicado (R4).
- Antes de escribir se valida todo: `municipality_id` de 5 dígitos y sin repetir (R7), nombre, coordenadas en rango y
  que cada fila cite una fuente que está en `sources` (R8). Si algo falla, no se publica nada.
- Lo que todavía no tiene fuente va nulo, nunca inventado (R1).
- `pipeline/sipsa_crops.yaml` dice qué producto de SIPSA da el precio de cada cultivo del MVP (HU-003). Un cultivo sin
  producto lleva su porqué. Antes de publicar se valida contra los precios: si un producto no está, si dos cultivos
  usan el mismo o si falta el porqué, no se publica nada.
- Los días de precios que faltan después del dataset los suman los crons del servicio `market` (HU-222,
  `backend/README.md`): lo publicado aquí es el punto de partida.
- `--descargar` baja también SIPSA (unos 300 MB que tardan un par de minutos, a `data/raw/sipsa/`) y NASA POWER.
- Sin `--descargar` el pipeline no usa la red. Si falta la caché de una fuente que no es imprescindible (hoy, NASA
  POWER y SIPSA), publica lo demás sin ella y el log lo dice (`source_missing`).

## Qué publica hoy

| Tabla | Fuente | HU |
|---|---|---|
| `municipalities` (con la altitud y la pendiente de NASADEM y la altura de su celda de NASA POWER) | DIVIPOLA del DANE en datos.gov.co, CC BY-SA 4.0 (`pipeline/sources/dane.py`), NASADEM y NASA POWER | HU-044, HU-206, HU-041 |
| `climate_day` | NASA POWER, API diaria por punto (`pipeline/sources/nasa_power.py`), corregida por la altitud de NASADEM. Es un reanálisis | HU-041 |
| `climate_month` | NASA POWER: la lluvia de cada mes completo de la celda del municipio, su normal 1991–2020 y su año seco, la ET0 por Penman-Monteith de FAO-56 con su normal (HU-143) y la humedad del suelo de un modelo, de 0 a 1 (HU-205). Es un reanálisis y en el altiplano da más lluvia que el IDEAM | HU-042 |
| `precip_month` | GPM IMERG mensual, corrida final V07 (`pipeline/sources/imerg.py`): la lluvia de cada mes por municipio, promedio de sus celdas de 0,1° ponderado por área, con su normal 2001–2024 y su año seco. Pide cuenta de NASA Earthdata (`AGROSENSE_EARTHDATA_TOKEN`); sin la caché se publica lo demás y el log dice `source_missing` | HU-207 |
| `grid_cells` | NASADEM (`pipeline/sources/nasadem.py`) y SoilGrids (`pipeline/sources/soilgrids.py`): altitud, pendiente y suelo de 0 a 30 cm de cada celda de 250 m | HU-206 |
| `soil_municipality` | SoilGrids 2.0 (`pipeline/sources/soilgrids.py`): la mediana de las celdas de cada municipio (pH, carbono orgánico, nitrógeno, arcilla, arena y limo de 0 a 30 cm, con los percentiles 5 y 95 del pH y del carbono) y la textura más frecuente. Sin la caché de SoilGrids se publica lo demás y el log dice `source_missing` | HU-181 |
| `municipality_boundaries` | Marco Geoestadístico Nacional 2025 del DANE, servicio del geoportal (`pipeline/sources/dane_mgn.py`), simplificado a unos 10 m | HU-044 |
| `crops` y `crop_stages` | Catálogo agronómico de `catalog/crops.yaml`: FAO EcoCrop, FAO-56, UPRA y FAO, con fuente por valor (`pipeline/catalog.py`) | HU-061, HU-199, HU-063 |
| `market_price_day`, `market_price_latest`, `market_price_season` | SIPSA del DANE, servicio web (`pipeline/sources/sipsa.py`): precios de Corabastos y Tunja desde 2020, el último de cada producto con el de hace una semana y su cambio (lo que lee `/market/prices`, que no calcula nada), y su temporada. Sin la caché de SIPSA se publica lo demás y el log dice `source_missing`. Los días que faltan después del dataset los suman los crons de precios (HU-222, `backend/README.md`), también con el boletín diario (`pipeline/sources/sipsa_boletin.py`) | HU-221, HU-222 |
| `market_month` | Lo mismo por cultivo, con el producto de `pipeline/sipsa_crops.yaml`: índice estacional y precio de cada mes del último año completo | HU-051 |
| `sources` | Una fila por fuente, con la cita textual que pide (`citation`, nula si no pide una) | HU-122, HU-221 |
| `manifest.json` | Versión, región, filas y cobertura por tabla | HU-122 |

Antes de publicar, cada tabla se revisa contra su esquema del contrato (`pipeline/schema.py`, HU-011): columnas, orden,
tipos, nulos, llave sin repetir y `quality`. Si no cumple, no se publica nada.

## Altitud y pendiente de NASADEM (HU-206)

- Se bajan los mosaicos de 1° que tocan la región (13, unos 224 MB en `data/raw/nasadem/`, menos de 2 minutos) de la
  copia en GeoTIFF de NASADEM HGT v001 que publica Microsoft Planetary Computer, sin cuenta. Cada mosaico se revisa al
  bajarlo (tamaño y georreferencia) y se reintenta 3 veces, con `AGROSENSE_NASADEM_TIMEOUT_S` y
  `AGROSENSE_NASADEM_MAX_MB`. El manifiesto de la caché (`nasadem.meta.json`) solo se escribe si bajaron todos.
- La rejilla del contrato es de 0,0025°, y un píxel de NASADEM mide 1 segundo: cada celda son exactamente 9 × 9 píxeles.
  La altitud es su promedio y la pendiente, la mediana de la de sus píxeles, calculada a 30 m con diferencias centrales.
- Cada celda va con el municipio que contiene su centro (`grid_cells`, 593 648 celdas). Sin el suelo (HU-181) son todas
  `partial`.
- La altitud de un municipio es la de la celda de su cabecera (el punto de DIVIPOLA), y su pendiente, la mediana de
  sus celdas (decidido por Felipe el 10 de noviembre de 2026, HU-206).
- `municipalities.tmean_annual_c` es la temperatura media de 1991–2020, corregida por altitud: el periodo normal está
  en `region.yaml` (`climate_normal`) y la calcula `pipeline/climate_normals.py` (HU-044). Sin la caché de NASADEM se publica lo demás, sin la rejilla ni el clima diario, y el log lo dice.

## Lluvia por satélite de GPM IMERG (HU-207)

- Pide una cuenta de NASA Earthdata: genere el token en https://urs.earthdata.nasa.gov («Generate Token»), apruebe la
  app «NASA GESDISC DATA ARCHIVE» y ponga el token en `AGROSENSE_EARTHDATA_TOKEN` en su `.env`. Sin el token,
  `--descargar` baja lo demás y lo dice en el log (`source_skipped`).
- El catálogo de la NASA (CMR, sin cuenta) da los meses de la colección `GPM_3IMERGM` V07. De cada uno se baja por
  OPeNDAP solo el recuadro de la región en CSV (34 × 30 celdas, unos 8 KB), de a 4 a la vez y con 3 intentos, con
  `AGROSENSE_IMERG_TIMEOUT_S` y `AGROSENSE_IMERG_MAX_MB`. Los 333 meses son 2,7 MB en `data/raw/imerg/` y bajan en
  unos 2 minutos y medio. Un mes que ya está en la caché no se vuelve a bajar. El manifiesto de la caché
  (`imerg.meta.json`) solo se escribe si bajaron todos.
- La lluvia viene en mm/h promedio del mes y se pasa a mm del mes. La de un municipio es el promedio de las celdas
  que tocan su polígono, ponderado por el área de cada una dentro. Un mes es `ok` si hay dato en todo el municipio,
  `partial` si cubre al menos el 90 %, y con menos no se publica (R1).
- La normal es 2001–2024 (`imerg_normal` en `region.yaml`), con al menos 20 años completos: nunca se completa con
  años de NASA POWER (R1).

## Clima diario de NASA POWER (HU-041)

- Se bajan desde 1981 la mínima, la máxima y la lluvia diarias (`T2M_MIN`, `T2M_MAX`, `PRECTOTCORR`) y, desde HU-205,
  la humedad del suelo (`GWETTOP`, `GWETROOT`), la radiación (`ALLSKY_SFC_SW_DWN`, desde 1984), el viento a 2 m
  (`WS2M`) y la humedad relativa (`RH2M`), **una vez por celda** de 0,5° × 0,625° y no por municipio: todos los
  puntos de una celda reciben la misma serie. Los 239 municipios caen en 20 celdas: unos 48 MB en
  `data/raw/nasa_power/` y menos de un minuto. Una caché de antes de HU-205 se baja otra vez.
- Cada celda se baja de a una, con 3 intentos y la misma descarga con límites que SIPSA (`pipeline/sources/fetch.py`).
  Se corta por tiempo total y por tamaño, con `AGROSENSE_POWER_TIMEOUT_S`
  y `AGROSENSE_POWER_MAX_MB` del `.env` (`.env.example` trae los valores de producción; los lee `pipeline/settings.py`).
  El manifiesto de la caché (`nasa_power.meta.json`) solo se escribe si bajaron todas.
- La temperatura se corrige por altitud: la de la celda más el gradiente de `pipeline/region.yaml` por la diferencia
  entre la altura de la celda (que da POWER) y la altitud del municipio (NASADEM, HU-206). El gradiente es el de la
  región Andina de Chaves y Jaramillo (Cenicafé, 1999), con su fila en `sources`.
- Un `-999` de POWER es un día sin dato: queda nulo y el día es `partial`. Un día sin ninguna de las dos temperaturas no
  se publica, y así tampoco los últimos días, que POWER todavía no tiene (R1).
- **Sin la altitud de NASADEM, `climate_day` no se publica**: no se publica una temperatura sin corregir. Con ella son
  unos 4 millones de filas y unos 21 MB de Parquet.
- **`climate_month` (HU-042):** la lluvia de cada mes completo, sin corregir por altitud, y su normal de 1991 a 2020
  (con 24 de los 30 años completos). Un mes es `partial` si le faltan días o no tiene normal; sin el 90 % de sus días
  no tiene total. Comparada con el IDEAM, en el altiplano POWER da de 1,7 a 2,7 veces la lluvia (`docs/riesgos.md`).
- **La ET0 (HU-143):** Penman-Monteith de FAO-56, día por día (`pipeline/et0.py`), con la mínima y la máxima de
  `climate_day` (ya corregidas por altitud) y la humedad relativa, el viento y la radiación de POWER. Un mes tiene ET0
  solo si todos sus días la tienen (no la tienen 1981–1983, sin radiación). El año seco (`precip_dry_mm`) es el
  percentil 20 de la lluvia del mes en 1991–2020.
- El periodo normal, sus 24 años mínimos, el 90 % de los días y el percentil del año seco están en `region.yaml`
  (`climate_normal`): los mismos para la lluvia, la ET0 y la temperatura media anual.

## Datos de ejemplo (HU-011)

```bash
uv run python -m pipeline.examples   # escribe data/examples/: todas las tablas del contrato
```

Tres municipios reales (Samacá, Toca y Tunja) con **cifras inventadas**: cada fila inventada cita la fuente `ejemplo` y
el manifiesto dice `"example": true` (R5). El catálogo de cultivos y los límites municipales son los reales. Sirven para
programar y probar el motor, la API y la web antes de que lleguen los datos. Nunca se publican en `data/published/`.

Pruebas: `tests/pipeline/` (sin red: usan una caché de ejemplo). `tests/pipeline/test_esquema.py` revisa que el esquema
coincida con el contrato y que lo publicado y los ejemplos lo cumplan.
