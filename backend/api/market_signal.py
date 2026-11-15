"""Los datos de la señal de mercado (HU-073): qué central le toca a un municipio y a un cultivo, y la historia del precio
del mes de cosecha en esa central. Son lecturas del dataset publicado, sin errores HTTP, sin base de datos y sin guardar
nada (R9). El motor recibe la historia ya leída (`backend.engine.market_signal`, R6).

**La central** (decisión 17, aprobada por Felipe el 15 de noviembre de 2026): la del departamento del municipio
(`region.department_markets` del manifiesto, `market_basis = department`); si esa central no tiene filas del cultivo en
`market_month`, la de `region.crop_market_overrides` para ese departamento y cultivo (`crop_override`), y la razón dice
por qué. Nunca otra central por defecto: sin ninguna de las dos, la señal es `insufficient_data` (R1).
"""

from collections.abc import Mapping
from typing import Any

import polars as pl

from backend.dataset import Dataset, Municipality
from backend.engine.market_signal import CROP_OVERRIDE, DEPARTMENT, MarketSignalResult, PriceHistory, market_signal
from backend.engine.stages import CropWindow


def market_for(dataset: Dataset, municipality: Municipality) -> str | None:
    """El `market_id` de SIPSA que da el precio en el departamento del municipio (`department_markets` de la región).

    Un departamento que no está en el mapa, o una región sin mapa, no tiene central: None. Nunca se usa otra central
    por defecto (R1).
    """
    # El pipeline ya validó que llaves y centrales son texto y existen (`pipeline.build.validate_department_markets`).
    return (dataset.region.get("department_markets") or {}).get(municipality.department_id)


def _crop_rows(dataset: Dataset, crop_id: str, market_id: str | None) -> pl.DataFrame | None:
    table = dataset.market_month
    if table is None or market_id is None:
        return None
    rows = table.filter((pl.col("crop_id") == crop_id) & (pl.col("market_id") == market_id))
    return None if rows.is_empty() else rows


def crop_market(dataset: Dataset, municipality: Municipality, crop_id: str) -> tuple[str, str, str | None] | None:
    """La central de referencia del cultivo en el municipio: `(market_id, market_basis, reason)`.

    Primero la del departamento, si `market_month` tiene filas del cultivo allí (`department`, sin razón). Si no, la de
    `crop_market_overrides` para ese departamento y cultivo (`crop_override`, con su `reason`), si allí sí tiene filas.
    None sin ninguna (R1).
    """
    department = market_for(dataset, municipality)
    if _crop_rows(dataset, crop_id, department) is not None:
        return department, DEPARTMENT, None
    overrides: Mapping[str, Any] = (dataset.region.get("crop_market_overrides") or {}).get(municipality.department_id) or {}
    override = overrides.get(crop_id)
    if override and _crop_rows(dataset, crop_id, override.get("market_id")) is not None:
        return override["market_id"], CROP_OVERRIDE, override.get("reason")
    return None


def _market_name(dataset: Dataset, market_id: str) -> str:
    """El nombre de la central como lo publica la región («Corabastos (Bogotá)»); su código si no lo dice."""
    return (dataset.region.get("markets") or {}).get(market_id) or dict(dataset.markets).get(market_id) or market_id


def _product_name(dataset: Dataset, product_id: str, market_id: str, crop: Mapping[str, Any]) -> str:
    """El producto de SIPSA como lo dice la razón, con el artículo del cultivo: «la papa negra». El nombre sale de los
    precios publicados (`market_price_latest`); sin ellos, del `product_id` («papa-negra» → «papa negra»)."""
    name = None
    latest = dataset.market_latest
    if latest is not None and "product" in latest.columns:
        rows = latest.filter((pl.col("product_id") == product_id) & (pl.col("market_id") == market_id)).select("product")
        if rows.is_empty():
            rows = latest.filter(pl.col("product_id") == product_id).select("product")
        if not rows.is_empty():
            name = rows.item(0, 0)
    name = (name or product_id.replace("-", " ")).lower()
    article = crop.get("article")
    return f"{article} {name}" if article else name


def _int(row: Mapping[str, Any], column: str) -> int | None:
    value = row.get(column)
    return None if value is None else int(value)


def price_history(dataset: Dataset, municipality: Municipality, crop_id: str, crop: Mapping[str, Any], month: int) -> PriceHistory | None:
    """La historia del precio del cultivo en su central de referencia (`crop_market`) en el mes de cosecha (1 a 12), de
    `market_month`. None sin central, sin fila o sin índice (R1).

    Con un `market_month` publicado antes de HU-073 (sin `years_above`, `years_below`, `first_year` ni `last_year`),
    esos campos llegan nulos y el motor no inventa el conteo."""
    found = crop_market(dataset, municipality, crop_id)
    if found is None:
        return None
    market_id, basis, reason = found
    rows = _crop_rows(dataset, crop_id, market_id)
    row_frame = None if rows is None else rows.filter(pl.col("month") == month)
    if row_frame is None or row_frame.is_empty():
        return None
    row = row_frame.row(0, named=True)
    if row.get("seasonal_index") is None or row.get("years") is None:
        return None
    return PriceHistory(
        market_id=market_id,
        market=_market_name(dataset, market_id),
        market_basis=basis,
        product_id=row["product_id"],
        month=month,
        seasonal_index=float(row["seasonal_index"]),
        years=int(row["years"]),
        years_above=_int(row, "years_above"),
        years_below=_int(row, "years_below"),
        first_year=_int(row, "first_year"),
        last_year=_int(row, "last_year"),
        source_id=row["source_id"],
        product_name=_product_name(dataset, row["product_id"], market_id, crop),
        override_reason=reason,
    )


def market_in(
    dataset: Dataset, municipality: Municipality, crop_id: str, crop: Mapping[str, Any], window: CropWindow | None
) -> MarketSignalResult:
    """La señal de mercado de la ventana: la historia del mes de la cosecha estimada. Sin ventana no hay mes (R1)."""
    history = None if window is None else price_history(dataset, municipality, crop_id, crop, window.harvest_estimate.month)
    return market_signal(history)


def seasonal_index(dataset: Dataset, crop_id: str, market_id: str | None, month: int) -> tuple[float | None, int | None]:
    """El `seasonal_index` y sus `years` de `market_month` para el cultivo, la central y el mes de cosecha (1 a 12).

    Sin `market_month`, sin central o sin fila (un cultivo sin producto en SIPSA, o sin 3 años completos en esa
    central, no tiene filas): `(None, None)` (R1).
    """
    rows = _crop_rows(dataset, crop_id, market_id)
    if rows is None:
        return None, None
    rows = rows.filter(pl.col("month") == month).select("seasonal_index", "years")
    if rows.is_empty():
        return None, None
    index, years = rows.row(0)
    if index is None:
        return None, None
    return float(index), int(years) if years is not None else None
