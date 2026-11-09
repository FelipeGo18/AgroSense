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
- Los precios de SIPSA, además, los baja la API cada día por su cuenta (HU-222, `backend/README.md`): lo publicado
  aquí es el punto de partida.
- `--descargar` baja también SIPSA: unos 300 MB que tardan un par de minutos. Sin `--descargar` hace falta su caché en
  `data/raw/sipsa/`.

## Qué publica hoy

| Tabla | Fuente | HU |
|---|---|---|
| `municipalities` (sin altitud todavía) | DIVIPOLA del DANE en datos.gov.co, CC BY-SA 4.0 (`pipeline/sources/dane.py`) | HU-044 |
| `municipality_boundaries` | Marco Geoestadístico Nacional 2025 del DANE, servicio del geoportal (`pipeline/sources/dane_mgn.py`), simplificado a unos 10 m | HU-044 |
| `crops` y `crop_stages` | Catálogo agronómico de `catalog/crops.yaml`: FAO EcoCrop, FAO-56, UPRA y FAO, con fuente por valor (`pipeline/catalog.py`) | HU-061, HU-199, HU-063 |
| `market_price_day`, `market_price_season` | SIPSA del DANE, servicio web (`pipeline/sources/sipsa.py`): precios de Corabastos y Tunja desde 2020 y su temporada | HU-221 |
| `market_month` | Lo mismo por cultivo, con el producto de `pipeline/sipsa_crops.yaml`: índice estacional y precio de cada mes del último año completo | HU-051 |
| `sources` | Una fila por fuente | HU-122 |
| `manifest.json` | Versión, región, filas y cobertura por tabla | HU-122 |

Antes de publicar, cada tabla se revisa contra su esquema del contrato (`pipeline/schema.py`, HU-011): columnas, orden,
tipos, nulos, llave sin repetir y `quality`. Si no cumple, no se publica nada.

## Datos de ejemplo (HU-011)

```bash
uv run python -m pipeline.examples   # escribe data/examples/: todas las tablas del contrato
```

Tres municipios reales (Samacá, Toca y Tunja) con **cifras inventadas**: cada fila inventada cita la fuente `ejemplo` y
el manifiesto dice `"example": true` (R5). El catálogo de cultivos y los límites municipales son los reales. Sirven para
programar y probar el motor, la API y la web antes de que lleguen los datos. Nunca se publican en `data/published/`.

Pruebas: `tests/pipeline/` (sin red: usan una caché de ejemplo). `tests/pipeline/test_esquema.py` revisa que el esquema
coincida con el contrato y que lo publicado y los ejemplos lo cumplan.
