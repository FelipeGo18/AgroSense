"""Dataset de ejemplo con la forma exacta del contrato (HU-011), para que motor, API y web avancen sin esperar los datos.

    uv run python -m pipeline.examples      # escribe data/examples/ (Parquet y manifest.json)

Tres municipios reales (Samacá, Toca y Tunja) con **cifras inventadas**: toda fila inventada cita la fuente `ejemplo`
y el manifiesto dice `"example": true` (R5). Lo real se copia tal cual de `data/published/`: el catálogo de cultivos,
sus etapas y los límites municipales, con sus fuentes de verdad. Las cifras son deterministas (R4): mismo comando,
mismos archivos. Nunca se publican en `data/published/` ni se muestran como datos reales.
"""

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from pipeline import schema
from pipeline.build import PUBLISHED
from pipeline.sources import sipsa

EXAMPLES = Path("data/examples")
SOURCE_ID = "ejemplo"
YEARS = range(2015, 2025)
# (municipality_id, altitud de ejemplo en m, temperatura media anual de ejemplo en °C, pendiente de ejemplo en %)
TOWNS = {"15646": (2660.0, 12.8, 9.0), "15814": (2810.0, 11.9, 14.0), "15001": (2780.0, 12.4, 6.0)}
PERIODS = [
    {"period_id": "p1981_2000", "start_year": 1981, "end_year": 2000, "source_id": SOURCE_ID},
    {"period_id": "p2005_2024", "start_year": 2005, "end_year": 2024, "source_id": SOURCE_ID},
]
SUPPLY_CROPS = ("papa", "arveja", "haba", "maiz", "zanahoria", "cebolla_bulbo")
MARKET_CROPS = ("papa", "arveja", "cebolla_bulbo", "zanahoria")
EXAMPLE_SOURCE = {
    "source_id": SOURCE_ID,
    "name": "Datos de ejemplo (no son reales)",
    "institution": "AgroSense",
    "url": None,
    "downloaded_at": None,
    "period_covered": None,
    "coverage": "Samacá, Toca y Tunja (Boyacá)",
    "license": None,
    "citation": None,
    "notes": "Cifras inventadas con la forma del contrato, para desarrollar y probar el motor, la API y la web (HU-011). "
    "Nunca se muestran como datos reales (R5).",
}


def _wave(month: int, peaks: tuple[int, int] = (4, 10)) -> float:
    """De 0 a 1: el régimen bimodal del altiplano, con lluvias en abril y octubre."""
    return max(math.cos((month - peak) * math.pi / 3) for peak in peaks) * 0.5 + 0.5


def _frost_month(month: int) -> float:
    """De 0 a 1: más heladas en diciembre, enero y febrero, y en julio y agosto, un poco."""
    return max(0.0, math.cos((month - 1) * math.pi / 6)) * 0.8 + (0.2 if month in (7, 8) else 0.0)


# Helada: mínima menor o igual a 2 °C (ZARC de Brasil, `mapa_zarc_2025`; decidido por Felipe el 10 de noviembre de 2026).
FROST_C = 2


def _table(name: str, rows: list[dict[str, Any]]) -> pl.DataFrame:
    spec = schema.TABLES[name]
    table = pl.DataFrame(rows, schema={col: column.dtype for col, column in spec.columns.items()}, orient="row")
    return table.sort(list(spec.key))


def municipalities(published: pl.DataFrame) -> pl.DataFrame:
    rows = published.filter(pl.col("municipality_id").is_in(list(TOWNS))).to_dicts()
    for row in rows:
        altitude, tmean, slope = TOWNS[row["municipality_id"]]
        row.update(altitude_m=altitude, climate_cell_elevation_m=altitude - 180, tmean_annual_c=tmean, slope_pct=slope)
        row["source_ids"] = sorted({*row["source_ids"], SOURCE_ID})
    return _table("municipalities", rows)


def climate_day() -> pl.DataFrame:
    rows = []
    for i, (town, (_, tmean, _)) in enumerate(TOWNS.items()):
        day = date(YEARS[0], 1, 1)
        while day.year <= YEARS[-1]:
            k = day.toordinal()
            frost = _frost_month(day.month)
            # El término del año hace que unos años hiele y otros no, como en la historia real de la zona.
            tmin = round(tmean - 7 - 4 * frost + 1.2 * math.sin(k * 0.7) + 1.5 * math.sin(day.year * 1.7 + i), 1)
            tmax = round(tmean + 7 - 1.5 * _wave(day.month) + 1.2 * math.cos(k * 0.5), 1)
            row = {"municipality_id": town, "date": day, "temp_min_c": tmin, "temp_max_c": tmax}
            rows.append({**row, "quality": "ok", "source_id": SOURCE_ID})
            day += timedelta(days=1)
    return _table("climate_day", rows)


def climate_risk_month(days: pl.DataFrame) -> pl.DataFrame:
    """Calculado de `climate_day` de ejemplo, como lo haría el pipeline: helada = mínima menor o igual a 2 °C."""
    monthly = (
        days.with_columns(pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().cast(pl.Int8).alias("month"))
        .group_by("municipality_id", "year", "month")
        .agg((pl.col("temp_min_c") <= FROST_C).sum().alias("frost_days"), pl.col("temp_max_c").quantile(0.9).alias("tmax_p90"))
    )
    table = (
        monthly.group_by("municipality_id", "month")
        .agg(
            ((pl.col("frost_days") > 0).mean() * 100).round(1).alias("frost_freq_pct"),
            pl.col("frost_days").mean().round(1).alias("frost_days_mean"),
            pl.col("tmax_p90").mean().round(1).alias("tmax_p90_c"),
            pl.col("year").n_unique().cast(pl.Int16).alias("years"),
        )
        .with_columns(
            pl.lit(None, pl.Float64).alias("heavy_rain_days_mean"),
            pl.lit(None, pl.Float64).alias("dry_window_freq_pct"),
            pl.lit(None, pl.Float64).alias("blight_days_mean"),
            pl.lit("ok").alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
    )
    return table.select(list(schema.TABLES["climate_risk_month"].columns)).sort("municipality_id", "month")


def climate_frost_month(days: pl.DataFrame) -> pl.DataFrame:
    """Calculado de `climate_day` de ejemplo: los días con helada de cada mes de cada año (HU-045, HU-077)."""
    table = (
        days.with_columns(pl.col("date").dt.year().cast(pl.Int16).alias("year"), pl.col("date").dt.month().cast(pl.Int8).alias("month"))
        .group_by("municipality_id", "year", "month")
        .agg(
            (pl.col("temp_min_c") <= FROST_C).sum().cast(pl.Int16).alias("frost_days"),
            pl.col("temp_min_c").count().cast(pl.Int16).alias("valid_days"),
            pl.col("date").first().dt.month_end().dt.day().alias("days"),
        )
        .with_columns(
            pl.when(pl.col("valid_days") == pl.col("days")).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
    )
    return table.select(list(schema.TABLES["climate_frost_month"].columns)).sort("municipality_id", "year", "month")


def _precip(town_index: int, year: int, month: int) -> float:
    return round(30 + 110 * _wave(month) + 15 * math.sin(year * 1.3 + month + town_index), 1)


def climate_month() -> pl.DataFrame:
    rows = []
    for i, town in enumerate(TOWNS):
        normal = {m: round(sum(_precip(i, y, m) for y in YEARS) / len(YEARS), 1) for m in range(1, 13)}
        for year in YEARS:
            for month in range(1, 13):
                wet = _wave(month)
                rows.append(
                    {
                        "municipality_id": town, "year": year, "month": month,
                        "precip_mm": _precip(i, year, month), "precip_normal_mm": normal[month],
                        "precip_dry_mm": round(normal[month] * 0.6, 1),
                        "et0_mm": round(100 - 15 * wet + 3 * math.cos(year), 1), "et0_normal_mm": round(100 - 15 * wet, 1),
                        "soil_wetness_top": round(0.45 + 0.3 * wet, 2), "soil_wetness_root": round(0.55 + 0.25 * wet, 2),
                        "quality": "ok", "source_id": SOURCE_ID,
                    }
                )  # fmt: skip
    return _table("climate_month", rows)


def precip_month() -> pl.DataFrame:
    rows = []
    for i, town in enumerate(TOWNS):
        normal = {m: round(sum(_precip(i, y, m) * 1.08 for y in YEARS) / len(YEARS), 1) for m in range(1, 13)}
        for year in YEARS:
            for month in range(1, 13):
                rows.append(
                    {
                        "municipality_id": town, "year": year, "month": month, "source_id": SOURCE_ID,
                        "precip_mm": round(_precip(i, year, month) * 1.08, 1), "precip_normal_mm": normal[month],
                        "precip_dry_mm": round(normal[month] * 0.6, 1), "normal_period": "2015-2024", "quality": "ok",
                    }
                )  # fmt: skip
    return _table("precip_month", rows)


def soil_moisture_month() -> pl.DataFrame:
    rows = [
        {
            "municipality_id": town, "year": year, "month": month, "source_id": SOURCE_ID,
            "sm_surface_m3_m3": round(0.22 + 0.12 * _wave(month), 3), "sm_rootzone_m3_m3": round(0.26 + 0.1 * _wave(month), 3),
            "quality": "ok",
        }
        for town in TOWNS for year in YEARS for month in range(1, 13)
    ]  # fmt: skip
    return _table("soil_moisture_month", rows)


def _ndvi(period: int) -> float:
    month = (period - 1) * 16 // 30 + 1
    return round(0.45 + 0.2 * _wave(month + 1), 3)


def ndvi_municipality() -> pl.DataFrame:
    rows = [
        {"municipality_id": town, "year": year, "period": period, "ndvi_median": round(_ndvi(period) + 0.02 * math.sin(year), 3),
         "valid_pixels_pct": 85.0, "quality": "ok", "source_id": SOURCE_ID}
        for town in TOWNS for year in YEARS for period in range(1, 24)
    ]  # fmt: skip
    return _table("ndvi_municipality", rows)


def ndvi_municipality_normal() -> pl.DataFrame:
    rows = [
        {"municipality_id": town, "period": period, "ndvi_normal": _ndvi(period), "years": len(YEARS),
         "quality": "ok", "source_id": SOURCE_ID}
        for town in TOWNS for period in range(1, 24)
    ]  # fmt: skip
    return _table("ndvi_municipality_normal", rows)


def grid_cells(towns: pl.DataFrame) -> pl.DataFrame:
    """Nueve celdas de la rejilla común alrededor del centro de cada municipio."""
    rows = []
    for town in towns.iter_rows(named=True):
        altitude, _, slope = TOWNS[town["municipality_id"]]
        center = schema.cell_id(town["lat"], town["lon"])
        row0, col0 = (int(part) for part in center.split("_"))
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                cell = f"{row0 + dr}_{col0 + dc}"
                lat, lon = schema.cell_center(cell)
                k = dr * 3 + dc
                rows.append(
                    {
                        "cell_id": cell, "lat": round(lat, 6), "lon": round(lon, 6), "municipality_id": town["municipality_id"],
                        "altitude_m": altitude + 12 * k, "slope_pct": round(slope + 1.5 * k, 1),
                        "ph": round(5.5 + 0.05 * k, 2), "ph_p05": round(5.1 + 0.05 * k, 2), "ph_p95": round(5.9 + 0.05 * k, 2),
                        "soc_g_kg": round(31 + k, 1), "soc_p05": round(22 + k, 1), "soc_p95": round(42 + k, 1),
                        "nitrogen_g_kg": round(2.4 + 0.05 * k, 2), "clay_pct": 28.0, "sand_pct": 40.0, "silt_pct": 32.0,
                        "texture_class": "franco arcilloso", "quality": "ok", "source_ids": [SOURCE_ID],
                    }
                )  # fmt: skip
    return _table("grid_cells", rows)


def soil_municipality(cells: pl.DataFrame) -> pl.DataFrame:
    """Como lo haría el pipeline: la mediana de las celdas de cada municipio."""
    numeric = [col for col, column in schema.SOIL.items() if column.dtype == pl.Float64]
    table = (
        cells.group_by("municipality_id")
        .agg(
            *[pl.col(col).median().round(2) for col in numeric],
            pl.col("texture_class").mode().first(),
            pl.len().cast(pl.Int32).alias("cells"),
        )
        .with_columns(pl.lit("ok").alias("quality"), pl.lit(SOURCE_ID).alias("source_id"))
    )
    return table.select(list(schema.TABLES["soil_municipality"].columns)).sort("municipality_id")


def ndvi_grid(cells: pl.DataFrame) -> pl.DataFrame:
    rows = [
        {"cell_id": cell, "period": period, "ndvi_normal": _ndvi(period), "years": len(YEARS), "valid_pct": 85.0,
         "quality": "ok", "source_id": SOURCE_ID}
        for cell in cells["cell_id"].to_list() for period in range(1, 24)
    ]  # fmt: skip
    return _table("ndvi_grid", rows)


def climate_change_month() -> pl.DataFrame:
    rows = []
    for i, town in enumerate(TOWNS):
        for period in PERIODS:
            later = period["start_year"] > 2000
            for month in range(1, 13):
                frost = _frost_month(month)
                rows.append(
                    {
                        "municipality_id": town, "period_id": period["period_id"], "month": month, "source_id": SOURCE_ID,
                        "frost_freq_pct": round(100 * frost * (0.55 if later else 0.75), 1),
                        "tmax_p90_c": round(19.5 + i * 0.3 + (0.6 if later else 0.0) - 1.5 * _wave(month), 1),
                        "precip_normal_mm": round(30 + 110 * _wave(month) * (1.05 if later else 1.0), 1),
                        "years": 20, "quality": "ok",
                    }
                )  # fmt: skip
    return _table("climate_change_month", rows)


def supply_semester() -> pl.DataFrame:
    rows = []
    for i, town in enumerate(TOWNS):
        for j, crop in enumerate(SUPPLY_CROPS):
            for year in range(2019, 2025):
                for semester in ("A", "B"):
                    planted = round(120 + 40 * j + 25 * math.sin(year + i + (0.5 if semester == "B" else 0)), 1)
                    rows.append(
                        {
                            "municipality_id": town, "crop_id": crop, "year": year, "semester": semester, "source_id": SOURCE_ID,
                            "planted_ha": planted, "harvested_ha": round(planted * 0.93, 1), "production_t": round(planted * 0.93 * 14, 1),
                            "yield_t_ha": 14.0, "planted_change_pct": round(10 * math.sin(year * 2 + j), 1) if year > 2020 else None,
                            "dept_share_pct": round(2 + i + 0.5 * j, 1), "preliminary": year == 2024,
                            "quality": "ok" if year > 2020 else "partial",
                        }
                    )  # fmt: skip
    return _table("supply_semester", rows)


# El producto de SIPSA de cada cultivo de ejemplo, como en `pipeline/sipsa_crops.yaml`.
MARKET_PRODUCTS = {
    "papa": "papa-negra",
    "arveja": "arveja-verde-en-vaina",
    "cebolla_bulbo": "cebolla-cabezona-blanca",
    "zanahoria": "zanahoria",
}


def market_month() -> pl.DataFrame:
    rows = [
        {"crop_id": crop, "market_id": "1", "month": month, "product_id": MARKET_PRODUCTS[crop],
         "price_cop_kg": 1500 + 300 * j + int(400 * math.sin(month + j)), "price_year": 2024, "volume_t": None,
         "seasonal_index": round(1 + 0.15 * math.sin(month + j), 3), "years": 4, "quality": "ok", "source_id": SOURCE_ID}
        for j, crop in enumerate(MARKET_CROPS) for month in range(1, 13)
    ]  # fmt: skip
    return _table("market_month", rows)


def market_price_day() -> pl.DataFrame:
    """Cuatro semanas de precios de ejemplo en Corabastos (R5): los nombres son los de SIPSA, las cifras inventadas."""
    start = date(2024, 12, 2)
    rows = [
        {"product_id": product, "market_id": "1", "date": start + timedelta(days=d), "product": product.replace("-", " ").capitalize(),
         "group": "Verduras y hortalizas", "several_varieties": False, "market": "Corabastos (Bogotá)",
         "min_cop_kg": price - 150, "avg_cop_kg": price, "max_cop_kg": price + 150, "source_id": SOURCE_ID}
        for j, product in enumerate(MARKET_PRODUCTS.values()) for d in range(28) if (start + timedelta(days=d)).weekday() < 6
        for price in [1500 + 300 * j + int(200 * math.sin(d / 4 + j))]
    ]  # fmt: skip
    return _table("market_price_day", rows)


def market_price_season() -> pl.DataFrame:
    rows = [
        {"product_id": product, "market_id": "1", "month": month, "seasonal_index": round(1 + 0.15 * math.sin(month + j), 3),
         "years": 4, "first_year": 2021, "last_year": 2024, "source_id": SOURCE_ID}
        for j, product in enumerate(MARKET_PRODUCTS.values()) for month in range(1, 13)
    ]  # fmt: skip
    return _table("market_price_season", rows)


def rotation_rules() -> pl.DataFrame:
    """Una regla de ejemplo por cada tipo de condición del contrato. Los números son inventados: los fija HU-062."""

    def rule(rule_id, kind, criterion, condition_type, params, levels, reason):
        return {
            "rule_id": rule_id, "kind": kind, "criterion": criterion, "condition_type": condition_type,
            "params": json.dumps(params), "levels": json.dumps(levels) if levels is not None else None,
            "reason_template": reason, "source_id": SOURCE_ID,
        }  # fmt: skip

    rows = [
        rule("ejemplo_familia_seguida", "filter", None, "same_family_consecutive", {"families": None}, None,
             "Repite la familia {family} en dos ciclos seguidos"),
        rule("ejemplo_papa_espera", "health", "pest_break", "family_return_min_cycles", {"family": "solanaceae", "min_cycles": 2},
             {"favorable": 2, "moderate": 1}, "La papa vuelve después de {cycles} ciclos de otras familias"),
        rule("ejemplo_leguminosas", "health", "nitrogen", "legume_cycles", {}, {"favorable": 2, "moderate": 1},
             "{count} de los ciclos tienen leguminosas, que fijan nitrógeno"),
        rule("ejemplo_materia_organica", "health", "organic_carbon", "organic_matter_cycles", {"soc_low_g_kg": 20},
             {"favorable": 1, "moderate": 0}, "{count} ciclos devuelven materia orgánica; el carbono del suelo es {soc_level}"),
        rule("ejemplo_suelo_cubierto", "health", "soil_cover", "covered_months_pct", {}, {"favorable": 80, "moderate": 60},
             "El suelo queda cubierto {pct} % de los meses de la estrategia"),
        rule("ejemplo_erosion", "health", "erosion", "bare_months_on_slope", {"slope_pct_from": 8}, {"favorable": 1, "moderate": 3},
             "Con pendiente de {slope} %, el suelo queda descubierto {months} meses"),
    ]  # fmt: skip
    return _table("rotation_rules", rows)


def climate_risk_week(risk_month: pl.DataFrame, month: pl.DataFrame) -> pl.DataFrame:
    """P1: los valores del mes, repartidos en sus semanas (el pipeline real suaviza con las semanas vecinas)."""
    normals = month.group_by("municipality_id", "month").agg(
        pl.col("precip_normal_mm").first(), pl.col("precip_dry_mm").first(), pl.col("et0_normal_mm").first()
    )
    joined = risk_month.join(normals, on=["municipality_id", "month"])
    rows = []
    for row in joined.iter_rows(named=True):
        for week in range(1, 53):
            if min(12, (week - 1) * 12 // 52 + 1) != row["month"]:
                continue
            rows.append(
                {
                    "municipality_id": row["municipality_id"], "week": week, "frost_freq_pct": row["frost_freq_pct"],
                    "tmax_p90_c": row["tmax_p90_c"], "precip_normal_mm": round(row["precip_normal_mm"] * 7 / 30, 1),
                    "precip_dry_mm": round(row["precip_dry_mm"] * 7 / 30, 1), "et0_normal_mm": round(row["et0_normal_mm"] * 7 / 30, 1),
                    "heavy_rain_days_mean": None, "dry_window_freq_pct": None, "blight_days_mean": None,
                    "years": row["years"], "quality": "ok", "source_id": SOURCE_ID,
                }
            )  # fmt: skip
    return _table("climate_risk_week", rows)


def climate_normal_doy(days: pl.DataFrame) -> pl.DataFrame:
    table = (
        days.with_columns(pl.col("date").dt.ordinal_day().cast(pl.Int16).alias("doy"))
        .group_by("municipality_id", "doy")
        .agg(pl.col("temp_min_c").mean().round(1), pl.col("temp_max_c").mean().round(1))
        .with_columns(pl.lit(SOURCE_ID).alias("source_id"))
    )
    return table.select(list(schema.TABLES["climate_normal_doy"].columns)).sort("municipality_id", "doy")


def build(published: Path = PUBLISHED) -> dict[str, pl.DataFrame]:
    """Todas las tablas del contrato con datos de ejemplo, cada una ya revisada contra su esquema."""
    copied = ("municipalities", "municipality_boundaries", "crops", "crop_stages", "sources")
    real = {name: pl.read_parquet(published / f"{name}.parquet") for name in copied}
    towns = municipalities(real["municipalities"])
    days = climate_day()
    month = climate_month()
    risk = climate_risk_month(days)
    cells = grid_cells(towns)
    tables = {
        "municipalities": towns,
        "municipality_boundaries": real["municipality_boundaries"].filter(pl.col("municipality_id").is_in(list(TOWNS))),
        "crops": real["crops"],
        "crop_stages": real["crop_stages"],
        "rotation_rules": rotation_rules(),
        "climate_day": days,
        "climate_month": month,
        "climate_risk_month": risk,
        "climate_frost_month": climate_frost_month(days),
        "precip_month": precip_month(),
        "soil_moisture_month": soil_moisture_month(),
        "ndvi_municipality": ndvi_municipality(),
        "ndvi_municipality_normal": ndvi_municipality_normal(),
        "climate_change_month": climate_change_month(),
        "supply_semester": supply_semester(),
        "grid_cells": cells,
        "soil_municipality": soil_municipality(cells),
        "market_month": market_month(),
        "market_price_day": (day_prices := market_price_day()),
        # Calculada con la misma función del pipeline y de las actualizaciones de precios.
        "market_price_latest": sipsa.latest(day_prices),
        "market_price_season": market_price_season(),
        "climate_risk_week": climate_risk_week(risk, month),
        "climate_normal_doy": climate_normal_doy(days),
        "ndvi_grid": ndvi_grid(cells),
    }
    cited = set().union(*(schema.cited_sources(name, table) for name, table in tables.items()))
    real_sources = real["sources"].filter(pl.col("source_id").is_in(list(cited)))
    tables["sources"] = pl.concat([real_sources, pl.DataFrame([EXAMPLE_SOURCE], schema=real["sources"].schema)]).sort("source_id")
    for name, table in tables.items():
        schema.check(name, table)
    return tables


def write(tables: dict[str, pl.DataFrame], folder: Path = EXAMPLES, published: Path = PUBLISHED) -> dict[str, Any]:
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.parquet"):
        old.unlink()
    for name, table in tables.items():
        table.write_parquet(folder / f"{name}.parquet")
    real_manifest = json.loads((published / "manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "example": True,
        "dataset_version": "ejemplo",
        "rules_version": real_manifest.get("rules_version"),
        # Fija para que los ejemplos sean reproducibles (R4): es la fecha en que se definió el contrato congelado.
        "created_at": "2026-11-08T00:00:00+00:00",
        "region": {**real_manifest["region"], "name": "Ejemplo: Samacá, Toca y Tunja (Boyacá)"},
        "periods": PERIODS,
        "tables": {
            name: {"rows": table.height, "coverage": "catálogo real" if name in ("crops", "crop_stages") else "ejemplo"}
            for name, table in tables.items()
        },
        "notes": "Datos de ejemplo con la forma del contrato (HU-011). Las cifras con la fuente `ejemplo` son inventadas; "
        "el catálogo de cultivos y los límites municipales son los reales.",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    try:
        manifest = write(build())
    except (FileNotFoundError, schema.SchemaError) as error:
        sys.exit(f"No se escribieron los ejemplos: {error}")
    rows = sum(info["rows"] for info in manifest["tables"].values())
    print(f"Ejemplos escritos en {EXAMPLES}: {len(manifest['tables'])} tablas, {rows} filas.")


if __name__ == "__main__":
    main()
