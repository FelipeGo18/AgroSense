# Pipeline de datos de AgroSense

Descarga las fuentes a una caché, las valida y publica el dataset que lee la API (`data/published/`: Parquet y
`manifest.json`). Contrato de las tablas: `specs/02-contratos.md`, «Tablas publicadas».

```bash
uv run python -m pipeline.build --descargar   # baja las fuentes a data/raw/ y publica
uv run python -m pipeline.build               # publica otra vez desde la caché, sin red
```

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
| `market_price_day`, `market_price_season` | SIPSA del DANE, servicio web (`pipeline/sources/sipsa.py`): precios de Corabastos y Tunja desde 2020 y su temporada | HU-221 |
| `sources` | Una fila por fuente | HU-122 |
| `manifest.json` | Versión, región, filas y cobertura por tabla | HU-122 |

Pruebas: `tests/pipeline/` (sin red: usan una caché de ejemplo).
