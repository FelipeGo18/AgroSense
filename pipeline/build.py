"""Reconstruye `data/published/` desde la caché (specs/02-contratos.md, «Tablas publicadas»).

    uv run python -m pipeline.build              # lee la caché de data/raw/ y publica
    uv run python -m pipeline.build --descargar  # antes, baja otra vez las fuentes a la caché
    uv run python -m pipeline.build --traer-cache  # antes, trae la caché compartida (HU-237)
    uv run python -m pipeline.build --verificar  # solo revisa que data/published coincida con su manifiesto (HU-123)

Por ahora publica `municipalities` (DIVIPOLA del DANE, HU-044, con la altura de su celda de NASA POWER),
`municipality_boundaries` (MGN del DANE, HU-044), el catálogo (`crops` y `crop_stages`, HU-061), `rotation_rules` (las
reglas de rotación de `catalog/rotation_rules.yaml`, HU-062), `climate_day` (NASA
POWER, HU-041), `market_price_day` y `market_price_season` (SIPSA del DANE, HU-221), `market_price_latest` (el último
precio de cada producto, HU-221), `market_month` (SIPSA por cultivo, HU-051), `supply_semester` (EVA de la UPRA,
HU-031), `sources` y `manifest.json`. Cada tabla
pasa por las validaciones y por su esquema del contrato (`pipeline/schema.py`, HU-011) antes de escribirse: si una
falla, no se publica nada (R7, R8).
También se valida el mapeo de los productos de SIPSA a los cultivos (`sipsa_crops.yaml`, HU-003) contra los precios que
se publican. Al terminar, lo publicado se revisa contra su manifiesto (HU-123).

Si falta la caché de NASA POWER, la de SIPSA o la de EVA, se publica lo demás sin esas tablas y el log lo dice (`source_missing`):
no hace falta bajar el clima ni los precios para reconstruir los municipios. `climate_day` solo se publica con los
municipios que tienen altitud (NASADEM, HU-206): sin ella la temperatura no se puede corregir y no se publica sin
corregir (R1).

Cada paso deja una línea en la terminal con la fuente, las filas leídas y las descartadas con su motivo (HU-177). Usa la
misma configuración de logs que la API (`common/logging.py`, que no depende del backend): nivel y formato con
`AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT`, sin depender de la base de datos.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl
import shapely
import yaml

from common import signal_sources
from common.logging import configure, get_logger
from pipeline import catalog as crops_catalog
from pipeline import climate_change, climate_normals, climate_risk, raw_cache, rotation_rules, schema
from pipeline.settings import get_settings
from pipeline.sources import dane, dane_mgn, eva, imerg, modis_ndvi, nasa_power, nasadem, sipsa, sipsa_boletin, soilgrids

REGION_FILE = Path(__file__).with_name("region.yaml")
CROPS_FILE = Path(__file__).with_name("sipsa_crops.yaml")
EVA_CROPS_FILE = Path(__file__).with_name("eva_crops.yaml")
PUBLISHED = Path("data/published")

log = get_logger("agrosense.pipeline")

# Como pide el catálogo de cultivos (HU-061): `snake_case`, sin tildes.
CROP_ID = re.compile(r"^[a-z][a-z0-9_]*$")
CROP_FIELDS = {"product_id", "notes", "reason"}


class ValidationError(ValueError):
    """Lo publicado no cumple el contrato. El mensaje dice qué falla."""


def load_region(path: Path = REGION_FILE) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_crops(path: Path = CROPS_FILE) -> dict[str, Any]:
    """Qué producto de SIPSA da el precio de cada cultivo (HU-003): `crop_id` → `product_id`, `notes` y `reason`."""
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("crops")


def load_eva_crops(path: Path = EVA_CROPS_FILE) -> dict[str, Any]:
    """Qué códigos de EVA son cada cultivo (HU-031): `crop_id` → `eva_codes`, `notes` y `reason`."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate(municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """R7: una sola llave territorial, de 5 dígitos y sin repetir. R8: toda fila apunta a una fuente que existe."""
    if municipalities.is_empty():
        raise ValidationError("`municipalities` quedó vacía: revise los departamentos de region.yaml.")
    bad = municipalities.filter(~pl.col("municipality_id").str.contains(r"^\d{5}$"))
    if not bad.is_empty():
        raise ValidationError(f"`municipality_id` que no son DIVIPOLA de 5 dígitos: {bad['municipality_id'].to_list()[:5]}")
    repeated = municipalities.filter(pl.col("municipality_id").is_duplicated())
    if not repeated.is_empty():
        raise ValidationError(f"`municipality_id` repetidos: {sorted(set(repeated['municipality_id'].to_list()))[:5]}")
    unnamed = municipalities.filter(pl.col("name").is_null() | (pl.col("name").str.strip_chars() == ""))
    if not unnamed.is_empty():
        raise ValidationError(f"Municipios sin nombre: {unnamed['municipality_id'].to_list()[:5]}")
    outside = municipalities.filter(~pl.col("lat").is_between(-90, 90) | ~pl.col("lon").is_between(-180, 180))
    if not outside.is_empty():
        raise ValidationError(f"Coordenadas fuera de rango: {outside['municipality_id'].to_list()[:5]}")
    known = set(sources["source_id"].to_list())
    cited = {source_id for ids in municipalities["source_ids"].to_list() for source_id in ids}
    if not cited or cited - known:
        raise ValidationError(f"Filas sin fuente o con una fuente que no está en `sources`: {sorted(cited - known) or 'sin source_ids'}")


def validate_boundaries(boundaries: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """Cada municipio publicado tiene un solo límite, válido, de área mayor que cero, y con una fuente que existe (R7, R8)."""
    ids, wanted = boundaries["municipality_id"].to_list(), set(municipalities["municipality_id"].to_list())
    if len(ids) != len(set(ids)):
        raise ValidationError("`municipality_boundaries` tiene municipios repetidos.")
    missing, extra = sorted(wanted - set(ids)), sorted(set(ids) - wanted)
    if missing or extra:
        raise ValidationError(f"Límites que no cuadran con `municipalities`: faltan {missing[:5]}, sobran {extra[:5]}")
    for municipality_id, wkb in boundaries.select("municipality_id", "geometry").iter_rows():
        geometry = shapely.from_wkb(wkb)
        if geometry.geom_type not in ("Polygon", "MultiPolygon") or not geometry.is_valid or geometry.area <= 0:
            raise ValidationError(f"El límite de {municipality_id} no es un polígono válido.")
    unknown = set(boundaries["source_id"].to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"Límites con una fuente que no está en `sources`: {sorted(unknown)}")


def validate_market(prices: pl.DataFrame, sources: pl.DataFrame) -> None:
    """Las reglas de los precios (`sipsa.validate`), con las fuentes de lo que se publica (R1, R8)."""
    try:
        sipsa.validate(prices, set(sources["source_id"].to_list()))
    except sipsa.PricesError as error:
        raise ValidationError(str(error)) from error


def validate_department_markets(region: dict[str, Any]) -> None:
    """`department_markets` de `region.yaml` (HU-073): cada departamento está en `departments` y cada central en `markets`,
    los dos como texto (un código sin comillas en el YAML es un número y no se encontraría). Un error de tipeo no puede
    dar `insufficient_data` en silencio en la señal de mercado (R1). Sin el campo no hay qué validar."""
    entry = region["region"]
    mapping = entry.get("department_markets")
    if not mapping:
        return
    unknown_departments = sorted(set(mapping) - set(entry.get("departments") or []), key=str)
    if unknown_departments:
        raise ValidationError(f"`department_markets` con departamentos que no están en `departments`: {unknown_departments}.")
    unknown_markets = sorted(set(mapping.values()) - set(entry.get("markets") or {}), key=str)
    if unknown_markets:
        raise ValidationError(f"`department_markets` con centrales que no están en `markets`: {unknown_markets}.")


def validate_crop_market_overrides(region: dict[str, Any]) -> None:
    """`crop_market_overrides` de `region.yaml` (HU-073, decisión 17): por departamento y cultivo, la central que da el
    precio cuando la del departamento no publica ese cultivo, con su porqué. Cada departamento está en `departments`,
    cada central en `markets`, cada cultivo en snake_case y cada `reason` dice algo: una central sin porqué no se usa
    (R1, R5). Sin el campo no hay qué validar."""
    entry = region["region"]
    overrides = entry.get("crop_market_overrides")
    if not overrides:
        return
    departments, markets = set(entry.get("departments") or []), set(entry.get("markets") or {})
    for department, crops in overrides.items():
        if department not in departments:
            raise ValidationError(f"`crop_market_overrides` con un departamento que no está en `departments`: {department!r}.")
        if not isinstance(crops, dict) or not crops:
            raise ValidationError(f"`crop_market_overrides` del departamento {department}: sin cultivos.")
        for crop_id, override in crops.items():
            where = f"`crop_market_overrides` del departamento {department}, {crop_id!r}"
            if not isinstance(crop_id, str) or not CROP_ID.match(crop_id):
                raise ValidationError(f"{where}: el `crop_id` va en snake_case y sin tildes.")
            if not isinstance(override, dict) or set(override) != {"market_id", "reason"}:
                raise ValidationError(f"{where}: lleva `market_id` y `reason`, y nada más.")
            if override["market_id"] not in markets:
                raise ValidationError(f"{where}: la central {override['market_id']!r} no está en `markets`.")
            if not isinstance(override["reason"], str) or not override["reason"].strip():
                raise ValidationError(f"{where}: sin `reason` no se usa otra central (R1).")


def validate_crops(crops: Any, prices: pl.DataFrame, catalog_ids: set[str] | None = None) -> None:
    """El mapeo de `sipsa_crops.yaml` (HU-003): cada cultivo tiene un producto que SIPSA publica en la región, o ninguno y
    el porqué (R1). Un producto no da el precio de dos cultivos: dos productos tampoco se promedian (decisión 11).

    Con `catalog_ids` (los `crop_id` de `catalog/crops.yaml`), cada cultivo del mapeo tiene que estar en el catálogo: los
    identificadores salen de un solo lugar y un `crop_id` mal escrito no se publica."""
    if not isinstance(crops, dict) or not crops:
        raise ValidationError("`sipsa_crops.yaml` no trae cultivos en `crops`.")
    if catalog_ids is not None:
        unknown = sorted(set(crops) - catalog_ids)
        if unknown:
            raise ValidationError(f"Cultivos de `sipsa_crops.yaml` que no están en `catalog/crops.yaml`: {unknown}.")
    published = set(prices["product_id"].unique().to_list())
    owners: dict[str, str] = {}
    for crop_id, entry in crops.items():
        if not isinstance(crop_id, str) or not CROP_ID.match(crop_id):
            raise ValidationError(f"`crop_id` inválido en `sipsa_crops.yaml`: {crop_id!r}. Va en snake_case y sin tildes.")
        if not isinstance(entry, dict) or "product_id" not in entry:
            raise ValidationError(f"{crop_id}: falta `product_id` en `sipsa_crops.yaml` (nulo si SIPSA no tiene el cultivo).")
        unknown = set(entry) - CROP_FIELDS
        if unknown:
            raise ValidationError(f"{crop_id}: campos que no se conocen en `sipsa_crops.yaml`: {sorted(unknown)}.")
        product = entry["product_id"]
        if product is None:
            if not str(entry.get("reason") or "").strip():
                raise ValidationError(f"{crop_id}: sin producto de SIPSA hay que decir por qué en `reason` (R1).")
            continue
        if not isinstance(product, str) or product not in published:
            raise ValidationError(f"{crop_id}: el producto {product!r} no está en los precios de SIPSA que se publican.")
        if product in owners:
            raise ValidationError(f"El producto {product!r} da el precio de dos cultivos: {owners[product]} y {crop_id}.")
        owners[product] = crop_id


def validate_market_month(month: pl.DataFrame, crops: dict[str, Any], sources: pl.DataFrame) -> None:
    """`market_month` (HU-051): llave sin repetir, meses de 1 a 12, índice y precio presentes y positivos, el producto que
    dice el mapeo y una fuente que existe (R1, R8). Vacía es válida: sin años completos no hay índice que publicar."""
    repeated = month.filter(pl.struct("crop_id", "market_id", "month").is_duplicated())
    if not repeated.is_empty():
        raise ValidationError(f"`market_month` repite cultivo, central y mes: {repeated.head(3).to_dicts()}")
    bad = month.filter(
        ~pl.col("month").is_between(1, 12)
        | pl.col("seasonal_index").is_null()
        | (pl.col("seasonal_index") <= 0)
        | pl.col("price_cop_kg").is_null()
        | (pl.col("price_cop_kg") <= 0)
        | ~pl.col("quality").is_in(["ok", "partial"])
        # Los años por encima y por debajo del promedio de su año (HU-073): nunca más que los años del índice.
        | pl.col("years_above").is_null()
        | pl.col("years_below").is_null()
        | (pl.col("years_above") < 0)
        | (pl.col("years_below") < 0)
        | (pl.col("years_above") + pl.col("years_below") > pl.col("years"))
    )
    if not bad.is_empty():
        raise ValidationError(f"`market_month` con mes, índice, precio, años o calidad fuera de lo permitido: {bad.head(3).to_dicts()}")
    expected = {crop_id: entry.get("product_id") for crop_id, entry in crops.items()}
    wrong = [row for row in month.select("crop_id", "product_id").unique().iter_rows() if expected.get(row[0]) != row[1]]
    if wrong:
        raise ValidationError(f"`market_month` con un producto que no es el de `sipsa_crops.yaml`: {sorted(wrong)[:3]}")
    unknown = set(month["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`market_month` con una fuente que no está en `sources`: {sorted(unknown)}")


def validate_climate(climate: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`climate_day` solo trae municipios publicados (R7) y cita fuentes que existen (R8)."""
    extra = set(climate["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`climate_day` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    unknown = set(climate["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`climate_day` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_climate_month(month: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`climate_month` solo trae municipios publicados (R7), meses de 1 a 12, lluvia no negativa y fuentes que existen
    (R8)."""
    extra = set(month["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`climate_month` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = month.filter(~pl.col("month").is_between(1, 12) | (pl.col("precip_mm") < 0) | (pl.col("precip_normal_mm") < 0))
    if not bad.is_empty():
        raise ValidationError(f"`climate_month` con un mes o una lluvia fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(month["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`climate_month` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_precip_month(month: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`precip_month` (HU-207) solo trae municipios publicados (R7), meses de 1 a 12, lluvia no negativa y fuentes que
    existen (R8)."""
    extra = set(month["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`precip_month` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = month.filter(~pl.col("month").is_between(1, 12) | (pl.col("precip_mm") < 0) | (pl.col("precip_normal_mm") < 0))
    if not bad.is_empty():
        raise ValidationError(f"`precip_month` con un mes o una lluvia fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(month["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`precip_month` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_frost(
    risk: pl.DataFrame, frost: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame, threshold_source: str | None
) -> None:
    """`climate_risk_month` y `climate_frost_month` (HU-045) solo traen municipios publicados (R7), meses de 1 a 12,
    porcentajes de 0 a 100, días que caben en el mes y fuentes que existen (R8). El umbral de helada de `region.yaml` cita
    una fuente que también está en `sources` (R8)."""
    if threshold_source is None or threshold_source not in set(sources["source_id"].to_list()):
        raise ValidationError(
            f"El umbral de helada de pipeline/region.yaml (`frost.source_id`: {threshold_source!r}) no está en `sources` (R8)."
        )
    known = set(municipalities["municipality_id"].to_list())
    for name, table in (("climate_risk_month", risk), ("climate_frost_month", frost)):
        extra = set(table["municipality_id"].unique().to_list()) - known
        if extra:
            raise ValidationError(f"`{name}` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
        unknown = set(table["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
        if unknown:
            raise ValidationError(f"`{name}` cita una fuente que no está en `sources`: {sorted(unknown)}")
    bad = risk.filter(~pl.col("month").is_between(1, 12) | ~pl.col("frost_freq_pct").is_between(0, 100) | (pl.col("frost_days_mean") < 0))
    if not bad.is_empty():
        raise ValidationError(f"`climate_risk_month` con un mes o una frecuencia fuera de lo permitido: {bad.head(3).to_dicts()}")
    bad = frost.filter(
        ~pl.col("month").is_between(1, 12)
        | (pl.col("frost_days") < 0)
        | (pl.col("frost_days") > pl.col("valid_days"))
        | (pl.col("valid_days") > 31)
    )
    if not bad.is_empty():
        raise ValidationError(f"`climate_frost_month` con un mes o unos días fuera de lo permitido: {bad.head(3).to_dicts()}")


def validate_change(change: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame, periods: list) -> None:
    """`climate_change_month` (HU-216) solo trae municipios publicados (R7), meses de 1 a 12, frecuencias de 0 a 100,
    lluvia no negativa, una máxima p90 verosímil (de -10 a 50 °C), años que caben en su periodo, periodos de
    `region.yaml` con su misma fuente (decisión 11) y fuentes que existen (R8). Las dos comprobaciones del calor y de los
    años las pidió Haider en la revisión del PR #79."""
    extra = set(change["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`climate_change_month` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = change.filter(
        ~pl.col("month").is_between(1, 12)
        | ~pl.col("frost_freq_pct").is_between(0, 100)
        | (pl.col("precip_normal_mm") < 0)
        | ~pl.col("tmax_p90_c").is_between(-10, 50)
    )
    if not bad.is_empty():
        raise ValidationError(
            f"`climate_change_month` con un mes, una frecuencia, una lluvia o un calor fuera de lo permitido: {bad.head(3).to_dicts()}"
        )
    lengths = pl.DataFrame(
        {"period_id": [p.period_id for p in periods], "period_years": [p.end_year - p.start_year + 1 for p in periods]},
        schema={"period_id": pl.String, "period_years": pl.Int64},
    )
    too_many = change.join(lengths, on="period_id", how="left").filter((pl.col("years") < 1) | (pl.col("years") > pl.col("period_years")))
    if not too_many.is_empty():
        raise ValidationError(f"`climate_change_month` con más años de los que tiene su periodo: {too_many.head(3).to_dicts()}")
    allowed = {(p.period_id, p.source_id) for p in periods}
    wrong = set(change.select("period_id", "source_id").unique().iter_rows()) - allowed
    if wrong:
        raise ValidationError(f"`climate_change_month` trae un periodo que no es de esa fuente en region.yaml: {sorted(wrong)}")
    unknown = set(change["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`climate_change_month` cita una fuente que no está en `sources`: {sorted(unknown)}")


def soil_out_of_range() -> pl.Expr:
    """Las filas con un suelo imposible: pH fuera de 0 a 14, un porcentaje fuera de 0 a 100, carbono o nitrógeno
    negativos o el percentil 5 por encima del 95. Un valor nulo (sin suelo) no cuenta: el filtro lo descarta."""
    return (
        ~pl.col("ph").is_between(0, 14)
        | pl.any_horizontal(~pl.col(c).is_between(0, 100) for c in ("clay_pct", "sand_pct", "silt_pct"))
        | (pl.col("soc_g_kg") < 0)
        | (pl.col("nitrogen_g_kg") < 0)
        | (pl.col("ph_p05") > pl.col("ph_p95"))
        | (pl.col("soc_p05") > pl.col("soc_p95"))
    )


def validate_soil(soil: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`soil_municipality` (HU-181) solo trae municipios publicados (R7), un pH de 0 a 14, porcentajes de 0 a 100,
    carbono y nitrógeno no negativos, el percentil 5 por debajo del 95 y fuentes que existen (R8)."""
    extra = set(soil["municipality_id"].to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`soil_municipality` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = soil.filter(soil_out_of_range())
    if not bad.is_empty():
        raise ValidationError(f"`soil_municipality` con un suelo fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(soil["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`soil_municipality` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_ndvi(ndvi: pl.DataFrame, normal: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`ndvi_municipality` y `ndvi_municipality_normal` (HU-208) solo traen municipios publicados (R7), periodos de 1 a
    23, un NDVI posible (de -0,2 a 1, el rango válido de MOD13Q1), porcentajes de 0 a 100, al menos un año en el promedio
    y fuentes que existen (R8)."""
    known = set(municipalities["municipality_id"].to_list())
    for name, table, value in (("ndvi_municipality", ndvi, "ndvi_median"), ("ndvi_municipality_normal", normal, "ndvi_normal")):
        extra = set(table["municipality_id"].unique().to_list()) - known
        if extra:
            raise ValidationError(f"`{name}` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
        bad = table.filter(~pl.col("period").is_between(1, modis_ndvi.PERIODS) | ~pl.col(value).is_between(-0.2, 1))
        if not bad.is_empty():
            raise ValidationError(f"`{name}` con un periodo o un NDVI fuera de lo permitido: {bad.head(3).to_dicts()}")
        unknown = set(table["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
        if unknown:
            raise ValidationError(f"`{name}` cita una fuente que no está en `sources`: {sorted(unknown)}")
    bad = ndvi.filter(~pl.col("valid_pixels_pct").is_between(0, 100, closed="right"))
    if not bad.is_empty():
        raise ValidationError(f"`ndvi_municipality` con un porcentaje de píxeles válidos fuera de lo permitido: {bad.head(3).to_dicts()}")
    bad = normal.filter(pl.col("years") < 1)
    if not bad.is_empty():
        raise ValidationError(f"`ndvi_municipality_normal` con una normal sin años: {bad.head(3).to_dicts()}")


def validate_supply(supply: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame, catalog_ids: set[str] | None) -> None:
    """`supply_semester` (HU-031) solo trae municipios publicados (R7), cultivos del catálogo, semestres A o B, valores no
    negativos y fuentes que existen (R8)."""
    extra = set(supply["municipality_id"].to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`supply_semester` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    if catalog_ids is not None and (unknown_crops := set(supply["crop_id"].to_list()) - catalog_ids):
        raise ValidationError(f"`supply_semester` trae cultivos que no están en el catálogo: {sorted(unknown_crops)}")
    bad = supply.filter(
        ~pl.col("semester").is_in(["A", "B"])
        | pl.any_horizontal(pl.col(col) < 0 for col in ("planted_ha", "harvested_ha", "production_t", "yield_t_ha"))
    )
    if not bad.is_empty():
        raise ValidationError(f"`supply_semester` con un semestre o un valor fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(supply["source_id"].unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`supply_semester` cita una fuente que no está en `sources`: {sorted(unknown)}")


def validate_grid(grid: pl.DataFrame, municipalities: pl.DataFrame, sources: pl.DataFrame) -> None:
    """`grid_cells` solo trae celdas de municipios publicados (R7), un suelo posible en las celdas que lo tienen (las
    mismas comprobaciones de `soil_municipality`: el suelo del lote, HU-182, lee las celdas) y fuentes que existen (R8)."""
    extra = set(grid["municipality_id"].unique().to_list()) - set(municipalities["municipality_id"].to_list())
    if extra:
        raise ValidationError(f"`grid_cells` trae municipios que no están en `municipalities`: {sorted(extra)[:5]}")
    bad = grid.filter(soil_out_of_range())
    if not bad.is_empty():
        raise ValidationError(f"`grid_cells` con un suelo fuera de lo permitido: {bad.head(3).to_dicts()}")
    unknown = set(grid["source_ids"].explode().drop_nulls().unique().to_list()) - set(sources["source_id"].to_list())
    if unknown:
        raise ValidationError(f"`grid_cells` cita una fuente que no está en `sources`: {sorted(unknown)}")


def lapse_rate_entry(region: dict[str, Any]) -> dict[str, Any]:
    """El gradiente térmico con que se calculó `tmean_annual_c`, para el manifiesto (HU-191, decisión del equipo).

    La API corrige la temperatura a la altitud de un lote con estas mismas tasas, así que la versión del dataset las
    fija y la API nunca aplica otras (R4). Sin gradiente en `region.yaml`, no se publica ninguno: nada se inventa (R1).
    """
    lapse = region.get("temperature_lapse_rate")
    if lapse is None:
        return {}
    return {
        "temperature_lapse_rate": {
            "temp_max_c_per_m": lapse["temp_max_c_per_m"],
            "temp_min_c_per_m": lapse["temp_min_c_per_m"],
            "source_id": lapse["source"]["source_id"],
        }
    }


def climate_normal_entry(region: dict[str, Any]) -> dict[str, Any]:
    """El periodo normal del clima, para el manifiesto (HU-077): la señal de heladas cuenta los años de ese periodo y
    pide al menos `min_years` con dato. Como el gradiente, lo fija la versión del dataset y la API nunca usa otro (R4).
    Sin `climate_normal` en `region.yaml`, no se publica: las señales que lo necesitan son `insufficient_data` (R1)."""
    normal = climate_normals.Normal.from_region(region)
    if normal is None:
        return {}
    return {"climate_normal": {"first_year": normal.first_year, "last_year": normal.last_year, "min_years": normal.min_years}}


def publish(
    region: dict[str, Any],
    municipalities: pl.DataFrame,
    sources: pl.DataFrame,
    folder: Path = PUBLISHED,
    boundaries: pl.DataFrame | None = None,
    crops: tuple[str, pl.DataFrame, pl.DataFrame] | None = None,
    prices: pl.DataFrame | None = None,
    crop_products: dict[str, Any] | None = None,
    climate: pl.DataFrame | None = None,
    grid: pl.DataFrame | None = None,
    climate_month: pl.DataFrame | None = None,
    precip_month: pl.DataFrame | None = None,
    frost: tuple[pl.DataFrame, pl.DataFrame] | None = None,
    change: pl.DataFrame | None = None,
    soil: pl.DataFrame | None = None,
    rules: pl.DataFrame | None = None,
    supply: pl.DataFrame | None = None,
    ndvi: tuple[pl.DataFrame, pl.DataFrame] | None = None,
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto. Las tablas salen ordenadas por su llave: mismos datos, mismos archivos (R4).

    `crops` es el catálogo agronómico (versión, `crops` y `crop_stages`). Con `crop_products` (el mapeo de
    `sipsa_crops.yaml`), lo valida contra los precios y publica además `market_month` (HU-051). `climate`
    (`climate_day`), `climate_month` (HU-042), `precip_month` (HU-207), `frost` (`climate_risk_month` y
    `climate_frost_month`, HU-045), `soil` (`soil_municipality`, HU-181), `grid` (`grid_cells`, HU-206), `supply`
    (`supply_semester`, HU-031) y `ndvi` (`ndvi_municipality` y `ndvi_municipality_normal`, HU-208) solo se escriben
    si traen filas: una tabla vacía no es un dato (R1). Todo se valida antes de escribir nada.
    """
    validate(municipalities, sources)
    validate_department_markets(region)
    validate_crop_market_overrides(region)
    if boundaries is not None:
        validate_boundaries(boundaries, municipalities, sources)
    season = month = latest = None
    if prices is not None:
        validate_market(prices, sources)
        season = sipsa.seasonal(prices)
        # El último precio de cada producto, con el de hace una semana y el cambio: la API solo lo filtra (HU-221).
        latest = sipsa.latest(prices)
    if crop_products is not None:
        if prices is None:
            raise ValidationError("El mapeo de `sipsa_crops.yaml` se valida contra los precios de SIPSA, y no hay precios.")
        validate_crops(crop_products, prices, set(crops[1]["crop_id"].to_list()) if crops is not None else None)
        month = sipsa.monthly(prices, season, crop_products)
        validate_market_month(month, crop_products, sources)
    has_climate = climate is not None and not climate.is_empty()
    if has_climate:
        validate_climate(climate, municipalities, sources)
    has_month = climate_month is not None and not climate_month.is_empty()
    if has_month:
        validate_climate_month(climate_month, municipalities, sources)
    has_precip = precip_month is not None and not precip_month.is_empty()
    if has_precip:
        validate_precip_month(precip_month, municipalities, sources)
    has_frost = frost is not None and not frost[0].is_empty()
    change_periods = climate_change.periods_from_region(region)
    has_change = change is not None and not change.is_empty()
    if has_change:
        validate_change(change, municipalities, sources, change_periods)
    if has_frost:
        validate_frost(frost[0], frost[1], municipalities, sources, climate_risk.frost_source(region))
    has_grid = grid is not None and not grid.is_empty()
    if has_grid:
        validate_grid(grid, municipalities, sources)
    has_soil = soil is not None and not soil.is_empty()
    if has_soil:
        validate_soil(soil, municipalities, sources)
    has_supply = supply is not None and not supply.is_empty()
    if has_supply:
        validate_supply(supply, municipalities, sources, set(crops[1]["crop_id"].to_list()) if crops is not None else None)
    has_ndvi = ndvi is not None and not ndvi[0].is_empty()
    if has_ndvi:
        validate_ndvi(ndvi[0], ndvi[1], municipalities, sources)
    # HU-011: cada tabla tiene exactamente la forma del contrato (columnas, tipos, llave y `quality`) antes de escribir.
    # `sources` junta filas de varias fuentes: va con las columnas del contrato, en su orden. Una fuente sin cita (por
    # ejemplo, las del catálogo) queda con `citation` nula, no inventada (R1).
    source_columns = list(schema.TABLES["sources"].columns)
    sources = sources.with_columns(pl.lit(None, dtype=pl.String).alias(col) for col in source_columns if col not in sources.columns)
    tables = {"municipalities": municipalities, "sources": sources.select(source_columns).sort("source_id")}
    if boundaries is not None:
        tables["municipality_boundaries"] = boundaries
    if crops is not None:
        tables["crops"], tables["crop_stages"] = crops[1], crops[2]
    if rules is not None:
        tables["rotation_rules"] = rules
    if has_climate:
        tables["climate_day"] = climate
    if has_month:
        tables["climate_month"] = climate_month
    if has_precip:
        tables["precip_month"] = precip_month
    if has_frost:
        tables["climate_risk_month"], tables["climate_frost_month"] = frost
    if has_change:
        tables["climate_change_month"] = change
    if has_grid:
        tables["grid_cells"] = grid
    if has_soil:
        tables["soil_municipality"] = soil
    if has_supply:
        tables["supply_semester"] = supply
    if has_ndvi:
        tables["ndvi_municipality"], tables["ndvi_municipality_normal"] = ndvi
    if prices is not None:
        tables |= {"market_price_day": prices, "market_price_latest": latest, "market_price_season": season}
    if month is not None:
        tables["market_month"] = month
    for name, table in tables.items():
        tables[name] = schema.typed(name, table)
        try:
            schema.check(name, tables[name])
        except schema.SchemaError as error:
            raise ValidationError(str(error)) from error
    folder.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.write_parquet(folder / f"{name}.parquet")
        log.info("table_written", table=name, rows=table.height, detail=f"{name}: {table.height} filas escritas en {folder}")
    manifest = {
        "dataset_version": region["dataset_version"],
        # La versión del catálogo agronómico (fichas y, cuando existan, reglas de rotación). Sin catálogo, nula.
        "rules_version": crops[0] if crops is not None else None,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "region": {**region["region"], **lapse_rate_entry(region), **climate_normal_entry(region)},
        # Los periodos de «Qué cambió» (HU-216): solo los de las fuentes que se publicaron.
        "periods": [p.manifest() for p in change_periods if has_change and p.source_id in set(change["source_id"].to_list())],
        "tables": {
            "municipalities": {"rows": municipalities.height, "coverage": region["region"]["name"]},
            "sources": {"rows": sources.height, "coverage": "todas las fuentes de lo publicado"},
        },
    }
    if boundaries is not None:
        manifest["tables"]["municipality_boundaries"] = {"rows": boundaries.height, "coverage": region["region"]["name"]}
    if crops is not None:
        manifest["tables"]["crops"] = {"rows": crops[1].height, "coverage": "cultivos del MVP"}
        manifest["tables"]["crop_stages"] = {"rows": crops[2].height, "coverage": "cultivos del MVP"}
    if rules is not None:
        manifest["tables"]["rotation_rules"] = {"rows": rules.height, "coverage": "reglas de rotación de los cultivos del MVP"}
    if has_climate:
        days = f"del {climate['date'].min()} al {climate['date'].max()}"
        coverage = f"{climate['municipality_id'].n_unique()} municipios con altitud, {days}"
        manifest["tables"]["climate_day"] = {"rows": climate.height, "coverage": coverage}
    if has_month:
        normal = climate_normals.Normal.from_region(region)
        years = f"de {climate_month['year'].min()} a {climate_month['year'].max()}"
        period = f"; normal {normal.first_year}-{normal.last_year}" if normal is not None else ""
        coverage = f"{climate_month['municipality_id'].n_unique()} municipios, meses completos {years}{period}"
        manifest["tables"]["climate_month"] = {"rows": climate_month.height, "coverage": coverage}
    if has_precip:
        years = f"de {precip_month['year'].min()} a {precip_month['year'].max()}"
        periods = sorted(set(precip_month["normal_period"].drop_nulls().to_list()))
        normal_text = f"; normal {', '.join(periods)}" if periods else "; sin normal"
        coverage = f"{precip_month['municipality_id'].n_unique()} municipios, lluvia de GPM IMERG {years}{normal_text}"
        manifest["tables"]["precip_month"] = {"rows": precip_month.height, "coverage": coverage}
    if has_frost:
        risk, by_year = frost
        normal = climate_normals.Normal.from_region(region)
        period = f" de {normal.first_year}-{normal.last_year}" if normal is not None else ""
        threshold = climate_risk.frost_threshold(region)
        towns = risk["municipality_id"].n_unique()
        coverage = f"{towns} municipios con altitud; heladas (mínima ≤ {threshold:g} °C) y máxima p90 por mes{period}"
        manifest["tables"]["climate_risk_month"] = {"rows": risk.height, "coverage": coverage}
        years = f"de {by_year['year'].min()} a {by_year['year'].max()}"
        coverage = f"{by_year['municipality_id'].n_unique()} municipios con altitud; días con mínima ≤ {threshold:g} °C por mes, {years}"
        manifest["tables"]["climate_frost_month"] = {"rows": by_year.height, "coverage": coverage}
    if has_change:
        names = ", ".join(f"{p.period_id} ({p.source_id})" for p in change_periods)
        coverage = f"{change['municipality_id'].n_unique()} municipios; periodos {names}"
        manifest["tables"]["climate_change_month"] = {"rows": change.height, "coverage": coverage}
    if has_grid:
        with_soil = grid.filter(pl.col("ph").is_not_null()).height
        soil_text = f"suelo de SoilGrids en {with_soil} celdas" if with_soil else "sin suelo (falta la caché de SoilGrids)"
        coverage = f"Celdas de 0,0025° de {grid['municipality_id'].n_unique()} municipios; {soil_text}"
        manifest["tables"]["grid_cells"] = {"rows": grid.height, "coverage": coverage}
    if has_soil:
        partial = soil.filter(pl.col("quality") == "partial").height
        coverage = f"{soil.height} municipios, mediana de sus celdas de 0 a 30 cm; {partial} partial"
        manifest["tables"]["soil_municipality"] = {"rows": soil.height, "coverage": coverage}
    if has_supply:
        ordered = supply.sort("year", "semester")
        first, last = ordered.row(0, named=True), ordered.row(-1, named=True)
        preliminary = sorted(set(supply.filter(pl.col("preliminary"))["year"].to_list()))
        coverage = (
            f"{supply['municipality_id'].n_unique()} municipios; {', '.join(sorted(set(supply['crop_id'].to_list())))}; "
            f"siembras de {first['year']}{first['semester']} a {last['year']}{last['semester']}; "
            f"preliminares {', '.join(map(str, preliminary)) or 'ninguno'}"
        )
        manifest["tables"]["supply_semester"] = {"rows": supply.height, "coverage": coverage}
    if has_ndvi:
        by_period, normal_ndvi = ndvi
        partial = by_period.filter(pl.col("quality") == "partial").height
        years = f"de {by_period['year'].min()} a {by_period['year'].max()}"
        coverage = (
            f"{by_period['municipality_id'].n_unique()} municipios, mediana de los píxeles sin nubes cada 16 días, {years}; "
            f"{partial} partial"
        )
        manifest["tables"]["ndvi_municipality"] = {"rows": by_period.height, "coverage": coverage}
        config = modis_ndvi.config_from_region(region)
        period = f" de {config.first_year}-{config.last_year}" if config is not None else ""
        partial = normal_ndvi.filter(pl.col("quality") == "partial").height
        coverage = f"{normal_ndvi['municipality_id'].n_unique()} municipios, verdor promedio{period} por periodo; {partial} partial"
        manifest["tables"]["ndvi_municipality_normal"] = {"rows": normal_ndvi.height, "coverage": coverage}
    if prices is not None:
        manifest["tables"]["market_price_day"] = {
            "rows": prices.height,
            "coverage": f"{' · '.join(sorted(set(prices['market'].to_list())))}; del {prices['date'].min()} al {prices['date'].max()}",
        }
        manifest["tables"]["market_price_latest"] = {
            "rows": latest.height,
            "coverage": "El último precio de cada producto en cada central, con el de hace una semana y el cambio",
        }
        manifest["tables"]["market_price_season"] = {
            "rows": season.height,
            "coverage": f"Productos con al menos {sipsa.MIN_YEARS} años completos de precios",
        }
    if month is not None:
        crops_with_rows = ", ".join(sorted(set(month["crop_id"].to_list()))) or "ningún cultivo"
        manifest["tables"]["market_month"] = {
            "rows": month.height,
            "coverage": f"{crops_with_rows}: índice estacional y precio de cada mes del último año completo, por central",
        }
    # Siempre con LF: en Windows `write_text` escribe CRLF, y el archivo cambiaría según quién publica (R4).
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (folder / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
    return manifest


def verify(folder: Path = PUBLISHED, dataset_version: str | None = None) -> dict[str, Any]:
    """HU-123: lo publicado en `folder` coincide con su manifiesto. Cada tabla que nombra existe y tiene las filas que dice,
    no hay tablas que no nombre y, con `dataset_version`, la versión es esa (la de `region.yaml`). Devuelve el manifiesto.

    Así se sabe que una carpeta copiada o reconstruida es la de la demo, y no una a medias o mezclada con otra (R4).
    """
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise ValidationError(f"No hay `manifest.json` en {folder}: publique con `uv run python -m pipeline.build`.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = manifest.get("tables") or {}
    problems = []
    if dataset_version is not None and manifest.get("dataset_version") != dataset_version:
        problems.append(f"el manifiesto es de la versión {manifest.get('dataset_version')} y `region.yaml` dice {dataset_version}")
    for name, info in listed.items():
        path = folder / f"{name}.parquet"
        if not path.exists():
            problems.append(f"falta `{name}.parquet`")
            continue
        rows = pl.scan_parquet(path).select(pl.len()).collect().item()
        if rows != info.get("rows"):
            problems.append(f"`{name}` tiene {rows} filas y el manifiesto dice {info.get('rows')}")
    extra = sorted(path.name for path in folder.glob("*.parquet") if path.stem not in listed)
    if extra:
        problems.append(f"tablas que el manifiesto no nombra: {extra}")
    if problems:
        raise ValidationError(f"Lo publicado en {folder} no coincide con su manifiesto: {'; '.join(problems)}.")
    return manifest


def terrain_from_cache(
    municipalities: pl.DataFrame, boundaries: pl.DataFrame, cache: Path
) -> tuple[pl.DataFrame, pl.DataFrame | None, list[dict[str, Any]]]:
    """La altitud y la pendiente de NASADEM (HU-206): los municipios con las suyas, `grid_cells` y su fuente.

    Sin la caché de NASADEM devuelve los municipios como estaban, sin rejilla y sin fuente nueva: lo demás se publica, y
    el clima diario no, porque sin altitud no se corrige (R1).
    """
    try:
        cells, meta = nasadem.read_cache(boundaries, cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=nasadem.SOURCE_ID, detail=f"Se publica sin la altitud de NASADEM: {error}")
        return municipalities, None, []
    terrain = nasadem.municipality_terrain(cells, municipalities)
    municipalities = nasadem.with_terrain(municipalities, terrain)
    empty = cells.filter(pl.col("altitude_m").is_null()).height
    log.info(
        "source_read",
        source=nasadem.SOURCE_ID,
        rows_read=cells.height,
        rows_kept=cells.height - empty,
        rows_rejected=empty,
        reasons={"no_valid_pixels": empty},
        detail=f"NASADEM: {cells.height} celdas de 250 m en {terrain.height} municipios; {empty} sin ningún píxel válido "
        "quedan con la altitud nula (R1)",
    )
    return municipalities, nasadem.grid_cells(cells), [nasadem.source(meta)]


def download_soil(tiles: list[tuple[int, int]], cache: Path) -> bool:
    """Baja SoilGrids. Si ISRIC está caído, avisa y deja seguir con las demás fuentes: sin la caché completa el dataset
    sale sin suelo y el pipeline lo dice (R1). Lo que alcanzó a bajar queda en la caché y la próxima vez se retoma."""
    try:
        soilgrids.download(tiles, cache)
    except soilgrids.DownloadError as error:
        log.warning("source_skipped", source=soilgrids.SOURCE_ID, detail=f"SoilGrids no bajó completo: {error}")
        return False
    return True


def soil_from_cache(
    grid: pl.DataFrame | None, boundaries: pl.DataFrame, cache: Path
) -> tuple[pl.DataFrame | None, pl.DataFrame | None, list[dict[str, Any]]]:
    """El suelo de SoilGrids (HU-181): `grid_cells` con el suelo, `soil_municipality` y sus fuentes.

    Sin `grid_cells` (falta NASADEM) o sin la caché de SoilGrids, la rejilla queda como estaba y no hay
    `soil_municipality`: lo demás se publica igual, y la señal de suelo es `insufficient_data` (R1).
    """
    if grid is None:
        return grid, None, []
    try:
        cells, meta = soilgrids.read_cache(nasadem.tiles(boundaries), cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=soilgrids.SOURCE_ID, detail=f"Se publica sin el suelo de SoilGrids: {error}")
        return grid, None, []
    grid = soilgrids.with_soil(grid, cells)
    table = soilgrids.soil_municipality(grid)
    empty = grid.filter(pl.col("ph").is_null()).height
    log.info(
        "source_read",
        source=soilgrids.SOURCE_ID,
        rows_read=grid.height,
        rows_kept=grid.height - empty,
        rows_rejected=empty,
        reasons={"no_soil_pixel": empty},
        detail=f"SoilGrids: suelo en {grid.height - empty} de {grid.height} celdas; {empty} sin dato (agua o zona urbana) quedan "
        f"nulas (R1); soil_municipality con {table.height} municipios",
    )
    return grid, table, soilgrids.sources(meta)


def download_supply(departments: list[str], cache: Path) -> None:
    """Baja EVA. Si datos.gov.co falla, se avisa y se sigue con las demás fuentes: la oferta será `insufficient_data` (R1)."""
    log.info("source_downloading", source=eva.SOURCE_ID, detail=f"Bajando EVA de la UPRA a {cache}")
    try:
        eva.download(departments, cache)
    except (OSError, eva.EvaError) as error:
        log.warning("source_skipped", source=eva.SOURCE_ID, detail=f"EVA no bajó: {error}")


def supply_from_cache(
    departments: list[str], municipalities: pl.DataFrame, catalog_ids: set[str], cache: Path, own: list[dict[str, Any]]
) -> pl.DataFrame | None:
    """`supply_semester` desde la caché de EVA (HU-031), con una línea en la terminal que dice cuántas filas se leyeron y
    cuántas se descartaron, por motivo. Sin caché, se publica lo demás sin la oferta (R1). Suma su fuente a `own`."""
    try:
        raw, meta = eva.read_cache(cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=eva.SOURCE_ID, detail=f"Se publica sin la oferta de EVA: {error}")
        return None
    try:
        codes = eva.crop_codes(load_eva_crops(), catalog_ids)
    except eva.EvaError as error:
        raise ValidationError(str(error)) from error
    counts: Counter[str] = Counter()
    supply = eva.normalize(raw, codes, departments, set(municipalities["municipality_id"].to_list()), counts)
    reasons = {reason: counts[reason] for reason in eva.REASONS if counts[reason]}
    rejected = sum(reasons.values())
    reasons_text = ", ".join(f"{n} {reason}" for reason, n in reasons.items()) or "ninguna"
    log.info(
        "source_read",
        source=eva.SOURCE_ID,
        rows_read=counts["read"],
        rows_kept=counts["read"] - counts["other_crop"] - rejected,
        rows_rejected=rejected,
        reasons=reasons,
        detail=f"EVA: {counts['read']} filas leídas, {counts['other_crop']} de cultivos que no son del MVP, {rejected} "
        f"descartadas ({reasons_text}) y {supply.height} filas de municipio, cultivo y semestre",
    )
    own.append(eva.source(meta, supply))
    return supply


def climate_from_cache(
    region: dict[str, Any], municipalities: pl.DataFrame, cache: Path
) -> tuple[pl.DataFrame, pl.DataFrame | None, pl.DataFrame | None, list[dict[str, Any]]]:
    """El clima de NASA POWER (HU-041, HU-042): los municipios con la altura de su celda, `climate_day`,
    `climate_month` y sus fuentes.

    Sin la caché de POWER devuelve los municipios como estaban, sin clima y sin fuentes nuevas: lo demás se publica igual.
    """
    try:
        series, meta = nasa_power.read_cache(nasa_power.cells(municipalities), cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=nasa_power.SOURCE_ID, detail=f"Se publica sin el clima de NASA POWER: {error}")
        return municipalities, None, None, []
    municipalities = nasa_power.with_cell_elevation(municipalities, meta["elevations"])
    lapse = region.get("temperature_lapse_rate")
    climate = nasa_power.climate_day(series, municipalities, lapse)
    # La lluvia no se corrige por altitud: sale para todos los municipios con coordenadas. La ET0 sí necesita la altitud.
    normal = climate_normals.Normal.from_region(region)
    if normal is None:
        log.warning("climate_normal_missing", table="climate_month", detail="region.yaml no trae climate_normal: no hay climate_month")
        month = None
    else:
        month = nasa_power.climate_month(series, municipalities, date.fromisoformat(meta["requested_end"]), normal, climate)
    sources = [nasa_power.source(series, meta)]
    if lapse is not None:
        sources.append(lapse["source"])
    without = municipalities.filter(pl.col("altitude_m").is_null()).height
    if without:
        log.warning(
            "climate_not_corrected",
            table="climate_day",
            municipalities=without,
            detail=f"{without} municipios sin altitud de NASADEM (HU-206): no tienen filas en climate_day",
        )
    if lapse is None:
        log.warning("climate_not_corrected", table="climate_day", detail="region.yaml no trae temperature_lapse_rate")
    return municipalities, climate, month, sources


def precip_from_cache(region: dict[str, Any], boundaries: pl.DataFrame, cache: Path) -> tuple[pl.DataFrame | None, list[dict[str, Any]]]:
    """La lluvia de GPM IMERG por municipio (HU-207): `precip_month` y su fuente.

    Sin la caché de IMERG (pide cuenta de Earthdata) no devuelve nada: lo demás se publica igual y la lluvia de contraste
    es `insufficient_data` (R1).
    """
    normal = imerg.normal_from_region(region)
    if normal is None:
        log.warning("climate_normal_missing", table="precip_month", detail="region.yaml no trae imerg_normal: no hay precip_month")
        return None, []
    try:
        cells, meta = imerg.read_cache(boundaries, cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=imerg.SOURCE_ID, detail=f"Se publica sin la lluvia de GPM IMERG: {error}")
        return None, []
    month = imerg.precip_month(cells, imerg.weights(boundaries), normal)
    partial = month.filter(pl.col("quality") == "partial").height
    log.info(
        "source_read",
        source=imerg.SOURCE_ID,
        rows_read=cells.height,
        rows_kept=month.height,
        detail=f"GPM IMERG: {len(meta['months'])} meses de {cells.select('row', 'col').unique().height} celdas; precip_month "
        f"con {month.height} filas de {month['municipality_id'].n_unique()} municipios, {partial} partial (R1)",
    )
    return month, [imerg.source(cells, meta)]


def ndvi_from_cache(
    region: dict[str, Any], boundaries: pl.DataFrame, cache: Path
) -> tuple[tuple[pl.DataFrame, pl.DataFrame] | None, list[dict[str, Any]]]:
    """El verdor de MODIS por municipio (HU-208): `ndvi_municipality`, `ndvi_municipality_normal` y su fuente.

    Sin el bloque `ndvi` de `region.yaml` o sin la caché de MODIS (pide cuenta de Earthdata) no devuelve nada: lo demás se
    publica igual y el verdor es `insufficient_data` (R1).
    """
    config = modis_ndvi.config_from_region(region)
    if config is None:
        log.warning("source_config_missing", source=modis_ndvi.SOURCE_ID, detail="region.yaml no trae ndvi: no hay verdor")
        return None, []
    try:
        table, meta = modis_ndvi.read_cache(boundaries, config, cache)
    except FileNotFoundError as error:
        log.warning("source_missing", source=modis_ndvi.SOURCE_ID, detail=f"Se publica sin el verdor de MODIS: {error}")
        return None, []
    normal = modis_ndvi.ndvi_normal(table, config)
    partial = table.filter(pl.col("quality") == "partial").height
    log.info(
        "source_read",
        source=modis_ndvi.SOURCE_ID,
        rows_read=len(meta["composites"]),
        rows_kept=table.height,
        detail=f"MODIS NDVI: {len(meta['composites'])} compuestos; ndvi_municipality con {table.height} filas de "
        f"{table['municipality_id'].n_unique()} municipios, {partial} partial (menos del {config.min_valid_pct:g} % de "
        f"píxeles sin nubes); promedio con {normal.height} filas (R1)",
    )
    return (table, normal), [modis_ndvi.source(table, meta, config)]


def frost_tables(region: dict[str, Any], climate: pl.DataFrame | None) -> tuple[pl.DataFrame, pl.DataFrame] | None:
    """Las heladas y la máxima por mes (HU-045): `climate_risk_month` y `climate_frost_month`, desde `climate_day`.

    Sin `climate_day` (falta la caché de POWER o la altitud), sin el umbral de helada o sin el periodo normal en
    `region.yaml`, no se publican: no se inventan (R1, R8), y el log lo dice.
    """
    threshold, normal = climate_risk.frost_threshold(region), climate_normals.Normal.from_region(region)
    if climate is None or climate.is_empty():
        return None
    if threshold is None or normal is None:
        log.warning("frost_config_missing", table="climate_risk_month", detail="region.yaml no trae frost o climate_normal: no hay heladas")
        return None
    risk = climate_risk.climate_risk_month(climate, threshold, normal)
    by_year = climate_risk.climate_frost_month(climate, threshold)
    partial = risk.filter(pl.col("quality") == "partial").height
    log.info(
        "frost_computed",
        rows=risk.height,
        detail=f"Heladas (mínima ≤ {threshold:g} °C) y máxima p90: {risk.height} filas de climate_risk_month ({partial} partial) y "
        f"{by_year.height} de climate_frost_month",
    )
    return risk, by_year


def build(
    download: bool = False,
    folder: Path = PUBLISHED,
    cache: Path = dane.CACHE,
    market_cache: Path | None = None,
    power_cache: Path | None = None,
    dem_cache: Path | None = None,
    rain_cache: Path | None = None,
    soil_cache: Path | None = None,
    supply_cache: Path | None = None,
    ndvi_cache: Path | None = None,
) -> dict[str, Any]:
    # Las cachés de SIPSA, NASA POWER y NASADEM se buscan al correr, no al importar: así las pruebas las apuntan a una
    # carpeta vacía y nunca leen las de quien las corre.
    market_cache = market_cache or sipsa.CACHE
    power_cache = power_cache or nasa_power.CACHE
    dem_cache = dem_cache or nasadem.CACHE
    soil_cache = soil_cache or soilgrids.CACHE
    rain_cache = rain_cache or imerg.CACHE
    supply_cache = supply_cache or eva.CACHE
    ndvi_cache = ndvi_cache or modis_ndvi.CACHE
    region = load_region()
    version, name = region["dataset_version"], region["region"]["name"]
    departments = region["region"]["departments"]
    log.info("pipeline_started", dataset_version=version, detail=f"Reconstruyendo el dataset {version} de {name}")
    if download:
        log.info("source_downloading", source=dane.SOURCE_ID, detail=f"Bajando DIVIPOLA del DANE a {cache}")
        dane.download(cache)
        log.info("source_downloading", source=dane_mgn.SOURCE_ID, detail=f"Bajando los límites municipales del DANE a {cache}")
        dane_mgn.download(departments, cache)
        log.info("source_downloading", source=sipsa.SOURCE_ID, detail=f"Bajando SIPSA del DANE a {market_cache} (unos 300 MB)")
        sipsa.download(market_cache)
        download_supply(departments, supply_cache)
    rows, meta = dane.read_cache(cache)
    municipalities = dane.municipalities(rows, departments)
    outside = len(rows) - municipalities.height
    log.info(
        "source_read",
        source=dane.SOURCE_ID,
        rows_read=len(rows),
        rows_kept=municipalities.height,
        rows_rejected=outside,
        reasons={"outside_region": outside},
        detail=f"DIVIPOLA: {len(rows)} filas leídas, {municipalities.height} de la región y {outside} descartadas por ser de "
        "otros departamentos",
    )
    features, mgn_meta = dane_mgn.read_cache(departments, cache)
    boundaries = dane_mgn.boundaries(features)
    if download:
        nasadem.download(nasadem.tiles(boundaries), dem_cache)
        download_soil(nasadem.tiles(boundaries), soil_cache)
        nasa_power.download(nasa_power.cells(municipalities), power_cache)
        # IMERG y MODIS piden una cuenta de NASA Earthdata: sin el token se baja lo demás y se avisa.
        token = get_settings().earthdata_token
        ndvi_config = modis_ndvi.config_from_region(region)
        if token is not None and token.get_secret_value().strip():
            imerg.download(boundaries, rain_cache)
            if ndvi_config is not None:
                modis_ndvi.download(boundaries, ndvi_config, ndvi_cache)
        else:
            log.warning("source_skipped", source=imerg.SOURCE_ID, detail="Sin AGROSENSE_EARTHDATA_TOKEN no se baja GPM IMERG (HU-207)")
            log.warning(
                "source_skipped", source=modis_ndvi.SOURCE_ID, detail="Sin AGROSENSE_EARTHDATA_TOKEN no se baja MODIS NDVI (HU-208)"
            )
    # Primero la altitud: el clima se corrige con ella (HU-044).
    municipalities, grid, terrain_sources = terrain_from_cache(municipalities, boundaries, dem_cache)
    grid, soil, soil_sources = soil_from_cache(grid, boundaries, soil_cache)
    municipalities, climate, climate_month, climate_sources = climate_from_cache(region, municipalities, power_cache)
    precip_month, rain_sources = precip_from_cache(region, boundaries, rain_cache)
    ndvi, ndvi_sources = ndvi_from_cache(region, boundaries, ndvi_cache)
    frost = frost_tables(region, climate)
    # «Qué cambió» (HU-216): los indicadores de cada periodo de region.yaml, cada uno de una sola fuente.
    change = climate_change.climate_change_month(region, climate, climate_month, precip_month)
    # La temperatura media anual (HU-044), con el periodo normal de `region.yaml`: la usa el filtro de aptitud.
    normal = climate_normals.Normal.from_region(region)
    if climate is not None and not climate.is_empty():
        if normal is None:
            log.warning("climate_normal_missing", detail="region.yaml no trae climate_normal: tmean_annual_c queda nula")
        else:
            tmean = climate_normals.tmean_annual(climate, normal)
            municipalities = climate_normals.with_tmean(municipalities, tmean)
            missing = municipalities.filter(pl.col("tmean_annual_c").is_null()).height
            log.info(
                "tmean_annual_computed",
                municipalities=municipalities.height - missing,
                detail=f"Temperatura media anual de {normal.first_year}-{normal.last_year}: {municipalities.height - missing} "
                f"municipios; {missing} sin años suficientes quedan nulos (R1)",
            )
    catalog = crops_catalog.load()
    crops_table, stages_table, catalog_sources = crops_catalog.build(catalog)
    # Las reglas citan las fuentes de las fichas y las suyas, y usan las familias de las fichas (HU-062).
    rules_table, rules_sources = rotation_rules.build(
        rotation_rules.load(),
        crop_sources=catalog.get("sources") or [],
        known_families=set(crops_table["family"].drop_nulls().to_list()),
        expected_version=catalog["version"],
    )
    own = [dane.source(meta), dane_mgn.source(mgn_meta)]
    prices = crop_products = None
    counts: Counter[str] = Counter()
    try:
        prices, downloaded_at = sipsa.read_cache(region["region"]["markets"], market_cache, counts)
    except FileNotFoundError as error:
        # Sin la caché de SIPSA (unos 300 MB) se publica lo demás, sin las tablas de precios: no se inventan (R1), y el
        # manifiesto dice qué trae. Así reconstruir los municipios no obliga a bajar los precios.
        log.warning("source_missing", source=sipsa.SOURCE_ID, detail=f"Se publica sin los precios de SIPSA: {error}")
    else:
        rejected = counts["other_market"] + counts["no_average"]
        log.info(
            "source_read",
            source=sipsa.SOURCE_ID,
            rows_read=counts["read"],
            rows_kept=prices.height,
            rows_rejected=rejected,
            reasons={"other_market": counts["other_market"], "no_average": counts["no_average"]},
            detail=f"SIPSA: {counts['read']} filas leídas, {prices.height} de las centrales de la región y {rejected} "
            f"descartadas: {counts['other_market']} de otras centrales y {counts['no_average']} sin precio medio ese día (R1)",
        )
        own.append(sipsa.source(prices, downloaded_at))
        crop_products = load_crops()
    supply = supply_from_cache(departments, municipalities, set(crops_table["crop_id"].to_list()), supply_cache, own)
    sources = pl.concat(
        [
            pl.DataFrame([*own, *terrain_sources, *soil_sources, *climate_sources, *rain_sources, *ndvi_sources]),
            catalog_sources,
            rules_sources,
        ],
        how="diagonal_relaxed",
    )
    check_signal_sources(region["region"]["id"], set(sources["source_id"].to_list()))
    crops = (catalog["version"], crops_table, stages_table)
    return publish(
        region,
        municipalities,
        sources,
        folder,
        boundaries,
        crops,
        prices,
        crop_products,
        climate,
        grid,
        climate_month,
        precip_month,
        frost,
        change,
        soil,
        rules_table,
        supply,
        ndvi=ndvi,
    )


SIGNAL_SOURCES_FILE = signal_sources.SIGNAL_SOURCES_FILE
# Las fuentes que tienen adaptador en el pipeline: si una no se publica, es porque falta su caché, no un error.
ADAPTERS = frozenset(
    module.SOURCE_ID for module in (dane, dane_mgn, sipsa, sipsa_boletin, nasa_power, nasadem, imerg, modis_ndvi, soilgrids, eva)
)


def check_signal_sources(region_id: str, published: set[str]) -> None:
    """`catalog/sources.yaml` contra lo que se va a publicar (HU-122, R8): una fuente que no está en `sources`, ni tiene
    adaptador, ni está en `planned` hace fallar el pipeline. Una con adaptador que esta vez no se publica (falta su caché)
    solo se dice en el log: su señal será `insufficient_data` (R1)."""
    try:
        config = signal_sources.load_signal_sources(SIGNAL_SOURCES_FILE)
        missing = signal_sources.check_sources(config, region_id, published, set(ADAPTERS))
    except signal_sources.SignalSourcesError as error:
        raise ValidationError(str(error)) from error
    for source in missing:
        log.warning("signal_source_missing", source=source, detail=f"catalog/sources.yaml usa {source}, que no se publica esta vez")
    planned = sorted(config.planned)
    log.info(
        "signal_sources_checked",
        version=config.version,
        planned=planned,
        detail=f"catalog/sources.yaml {config.version}: fuentes por llegar {', '.join(planned) or 'ninguna'}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye data/published desde la caché.")
    parser.add_argument("--descargar", action="store_true", help="Baja otra vez las fuentes a data/raw/ antes de publicar.")
    parser.add_argument(
        "--traer-cache", action="store_true", help="Antes de publicar, trae la caché compartida de pipeline/raw_cache.json (HU-237)."
    )
    parser.add_argument("--verificar", action="store_true", help="No publica: solo revisa que data/published coincida con su manifiesto.")
    args = parser.parse_args()
    # El pipeline no usa la base de datos: lee su configuración de `pipeline/settings.py`, no la de la API.
    settings = get_settings()
    configure(settings.log_level, settings.log_format)
    expected = load_region()["dataset_version"]
    try:
        if args.traer_cache and not args.verificar:
            raw_cache.pull()
        if not args.verificar:
            build(download=args.descargar)
        manifest = verify(PUBLISHED, expected)
    except (
        FileNotFoundError,
        ValidationError,
        crops_catalog.CatalogError,
        rotation_rules.RotationRulesError,
        nasa_power.DownloadError,
        nasadem.TileError,
        raw_cache.CacheError,
    ) as error:
        event = "dataset_mismatch" if args.verificar else "dataset_not_published"
        log.error(event, detail=f"{'Lo publicado no pasó la revisión' if args.verificar else 'No se publicó nada'}: {error}")
        sys.exit(1)
    tables = ", ".join(f"{name} ({info['rows']} filas)" for name, info in manifest["tables"].items())
    verb = "revisado: coincide con su manifiesto" if args.verificar else "publicado y revisado contra su manifiesto"
    log.info(
        "dataset_verified" if args.verificar else "dataset_published",
        dataset_version=manifest["dataset_version"],
        tables=len(manifest["tables"]),
        detail=f"Dataset {manifest['dataset_version']} {verb} en {PUBLISHED}: {tables}",
    )


if __name__ == "__main__":
    main()
