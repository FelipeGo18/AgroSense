# Pipeline de datos de AgroSense

Descarga las fuentes a una caché, las valida y publica el dataset que lee la API (`data/published/`: Parquet y
`manifest.json`). Contrato de las tablas: `specs/02-contratos.md`, «Tablas publicadas».

```bash
uv run python -m pipeline.build --descargar   # baja las fuentes a data/raw/ y publica
uv run python -m pipeline.build               # publica otra vez desde la caché, sin red
```

- `data/raw/` es caché y no va a git. `data/published/` sí va a git y entra en la imagen de Docker: es el dataset de la demo.
- `pipeline/region.yaml` dice la región y la versión del dataset. **La región es un supuesto** (Boyacá y Cundinamarca)
  hasta el enunciado del 28 de octubre de 2026. `dataset_version` sube a mano cada vez que cambia lo publicado (R4).
- Antes de escribir se valida todo: `municipality_id` de 5 dígitos y sin repetir (R7), nombre, coordenadas en rango y
  que cada fila cite una fuente que está en `sources` (R8). Si algo falla, no se publica nada.
- Lo que todavía no tiene fuente va nulo, nunca inventado (R1).

## Qué publica hoy

| Tabla | Fuente | HU |
|---|---|---|
| `municipalities` (sin altitud todavía) | DIVIPOLA del DANE en datos.gov.co, CC BY-SA 4.0 (`pipeline/sources/dane.py`) | HU-044 |
| `municipality_boundaries` | Marco Geoestadístico Nacional 2025 del DANE, servicio del geoportal (`pipeline/sources/dane_mgn.py`), simplificado a unos 10 m | HU-044 |
| `crops` y `crop_stages` | Catálogo agronómico de `catalog/crops.yaml`: FAO EcoCrop, FAO-56, UPRA y FAO, con fuente por valor (`pipeline/catalog.py`) | HU-061, HU-199, HU-063 |
| `rotation_rules` | Reglas de rotación de `catalog/rotation_rules.yaml`, cada una con su fuente (`pipeline/rotation_rules.py`) | HU-062 |
| `sources` | Una fila por fuente | HU-122 |
| `manifest.json` | Versión, región, filas y cobertura por tabla | HU-122 |

Antes de publicar, cada tabla se revisa contra su esquema del contrato (`pipeline/schema.py`, HU-011): columnas, orden,
tipos, nulos, llave sin repetir y `quality`. Si no cumple, no se publica nada.

## Reglas de rotación (HU-062)

`catalog/rotation_rules.yaml` trae `version` (la misma de `catalog/crops.yaml`: las dos son `rules_version` del
manifiesto; si difieren, el build falla), una sección `sources:` con el formato de la de `crops.yaml` y la lista `rules:`.
Cada regla tiene las columnas de `rotation_rules` del contrato; `params` y `levels` se escriben como mapas YAML y se
publican como JSON con las llaves ordenadas (R4). `criterion` y `levels` se pueden omitir en un `filter` (valen nulo).
Una regla puede citar una fuente de `crops.yaml` sin repetirla; si la repite, debe ser idéntica.

La lista cerrada de tipos de condición vive en un solo lugar, `CONDITION_TYPES` de `pipeline/schema.py`: por tipo, los
`kind` que admite, su criterio de `soil_health`, las llaves y valores de `params` y `levels`, el sentido de los cortes y
los `{marcadores}` que admite `reason_template`. Agregar un tipo es agregar una entrada (y es un cambio de contrato).

El build falla, nombrando `rule_id.campo`, si un `kind`, `condition_type` o `criterion` no corresponde; si `params` o
`levels` no tienen las llaves de su tipo; si `levels` falta en un `health` o sobra en un `filter`; si los cortes no son
coherentes (`moderate` no puede pasar de `favorable`; al revés en `bare_months_on_slope`); si en un
`family_return_min_cycles` de salud `params.min_cycles` no es `levels.favorable`; si `reason_template` usa un marcador
que su tipo no admite; si `source_id` está vacío o no está en `sources` (R8); si una fuente de los dos catálogos tiene
datos distintos; si un `rule_id` se repite; o si una familia de `params` no es, con la misma mayúscula, la `family` de
alguna ficha. Sin `catalog/rotation_rules.yaml` no se publica nada.

`levels` de `organic_matter_cycles` tiene la forma de la decisión 16 (`docs/decisiones.md`): los grupos `low` y
`normal`, los dos obligatorios, cada uno con `favorable` y `moderate` enteros ≥ 0 y `moderate` no mayor que
`favorable`; `low.favorable` es al menos 1. En `CONDITION_TYPES` se declara con valores de tipo `object` (un grupo de
cortes), sin código propio para ese tipo.

**Sin franja intermedia.** Una regla puede no tener nivel `moderate` (decisión del 9 de noviembre de 2026): se escribe
`moderate` igual a `favorable`. Con cortes mínimos (`higher_is_better`) se exige `moderate <= favorable`; con cortes
máximos (`lower_is_better`, `bare_months_on_slope`), `favorable <= moderate`. Si son iguales, el nivel es `favorable`
desde ese valor y `unfavorable` del otro lado; nunca `moderate`. Vale también dentro de cada grupo de
`organic_matter_cycles`.

`CONDITION_TYPES` y lo que se lee del YAML son de solo lectura: la lista cerrada es un `MappingProxyType` que se
autocomprueba al importar `pipeline/schema.py` (`check_condition_types`; un error ahí es de programación y da
`ValueError`), y cada regla guarda una copia profunda de `params` y `levels` con mapas de solo lectura y listas como
tuplas. Al publicar, `params.families` sale ordenada alfabéticamente, sin importar el orden del YAML (R4).

> **Acoplamiento con `catalog/crops.yaml`.** Los dos catálogos comparten `version` (es `rules_version` del
> manifiesto): si una sube, la otra también, o el build falla. Las familias de `params` (`family` y `families`) deben
> existir, con la misma mayúscula, en el campo `family` de alguna ficha: cambiar o quitar una familia de las fichas
> puede romper las reglas.

## Datos de ejemplo (HU-011)

```bash
uv run python -m pipeline.examples   # escribe data/examples/: todas las tablas del contrato
```

Tres municipios reales (Samacá, Toca y Tunja) con **cifras inventadas**: cada fila inventada cita la fuente `ejemplo` y
el manifiesto dice `"example": true` (R5). El catálogo de cultivos y los límites municipales son los reales. Sirven para
programar y probar el motor, la API y la web antes de que lleguen los datos. Nunca se publican en `data/published/`.

Pruebas: `tests/pipeline/` (sin red: usan una caché de ejemplo). `tests/pipeline/test_esquema.py` revisa que el esquema
coincida con el contrato y que lo publicado y los ejemplos lo cumplan.
