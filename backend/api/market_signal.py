"""Los datos de la señal de mercado (HU-073, decisión 17): qué central le toca a un municipio y a un cultivo, y la historia
del precio del cultivo en el mes de cosecha. Son lecturas del dataset publicado, sin errores HTTP, sin base de datos y
sin guardar nada (R9). El motor recibe la historia ya armada (`backend.engine.market_signal`, R6).
"""

from dataclasses import dataclass

import polars as pl

from backend.dataset import Dataset, Municipality
from backend.engine.market_signal import CROP_OVERRIDE, DEPARTMENT, MarketSignalResult, PriceHistory, market_signal


@dataclass(frozen=True)
class MarketChoice:
    """La central de un cultivo en un municipio: su código, de dónde sale (`department` o `crop_override`) y, con
    `crop_override`, el porqué que dice `region.crop_market_overrides`."""

    market_id: str
    basis: str
    reason: str | None = None


@dataclass(frozen=True)
class MarketHistory:
    """Lo que la API le pasa al motor: la historia (o None), el nombre del producto en SIPSA y el porqué de la central."""

    history: PriceHistory | None
    product_name: str | None = None
    override_reason: str | None = None


def market_for(dataset: Dataset, municipality: Municipality) -> str | None:
    """El `market_id` de SIPSA que da el precio en el departamento del municipio (`department_markets` de la región).

    Un departamento que no está en el mapa, o una región sin mapa, no tiene central: None. Nunca se usa otra central
    por defecto (R1).
    """
    # El pipeline ya validó que llaves y centrales son texto y existen (`pipeline.build.validate_department_markets`).
    return (dataset.region.get("department_markets") or {}).get(municipality.department_id)


def market_choice(dataset: Dataset, municipality: Municipality, crop_id: str) -> MarketChoice | None:
    """La central que da el precio del cultivo en el municipio.

    Primero la del departamento (`department_markets`). Si esa central no tiene ninguna fila del cultivo en
    `market_month` (Tunja no publica papa negra desde 2021), la de `crop_market_overrides` para ese departamento y ese
    cultivo, con su porqué. Sin ninguna de las dos: None, y la señal es `insufficient_data` (R1). Nunca otra central
    por defecto.
    """
    department_market = market_for(dataset, municipality)
    if department_market is not None and _has_crop(dataset, crop_id, department_market):
        return MarketChoice(department_market, DEPARTMENT)
    overrides = (dataset.region.get("crop_market_overrides") or {}).get(municipality.department_id) or {}
    override = overrides.get(crop_id)
    if override is not None:
        return MarketChoice(override["market_id"], CROP_OVERRIDE, override["reason"])
    return MarketChoice(department_market, DEPARTMENT) if department_market is not None else None


def market_history(dataset: Dataset, choice: MarketChoice | None, crop_id: str, month: int) -> MarketHistory:
    """La historia del precio del cultivo en la central elegida y el mes de cosecha (1 a 12), de `market_month`.

    Sin `market_month`, sin central o sin fila (un cultivo sin producto en SIPSA, o sin 3 años completos en esa
    central): sin historia (R1).
    """
    table = dataset.market_month
    if table is None or choice is None:
        return MarketHistory(None)
    rows = table.filter((pl.col("crop_id") == crop_id) & (pl.col("market_id") == choice.market_id) & (pl.col("month") == month))
    if rows.is_empty():
        return MarketHistory(None)
    row = rows.row(0, named=True)
    if row["seasonal_index"] is None or row["years"] is None:
        return MarketHistory(None)
    history = PriceHistory(
        market_id=choice.market_id,
        market=dict(dataset.markets).get(choice.market_id, choice.market_id),
        market_basis=choice.basis,
        product_id=row["product_id"],
        month=month,
        seasonal_index=float(row["seasonal_index"]),
        years=int(row["years"]),
        years_above=int(row["years_above"]),
        years_below=int(row["years_below"]),
        first_year=row["first_year"],
        last_year=row["last_year"],
        source_id=row["source_id"],
    )
    return MarketHistory(history, _product_name(dataset, row["product_id"], choice.market_id), choice.reason)


def _has_crop(dataset: Dataset, crop_id: str, market_id: str) -> bool:
    table = dataset.market_month
    return table is not None and not table.filter((pl.col("crop_id") == crop_id) & (pl.col("market_id") == market_id)).is_empty()


def _product_name(dataset: Dataset, product_id: str, market_id: str) -> str | None:
    """El nombre del producto como lo publica SIPSA («Papa negra»), del último precio de la central o, si esa central
    ya no lo publica, de otra. None si no está: la razón va sin él."""
    table = dataset.market_latest
    if table is None:
        return None
    rows = table.filter(pl.col("product_id") == product_id).sort(pl.col("market_id") != market_id, "market_id")
    return None if rows.is_empty() else rows["product"][0]


def market_in(dataset: Dataset, municipality: Municipality, crop_id: str, crop_name: str, month: int | None) -> MarketSignalResult:
    """La señal `market` de una ventana cuya cosecha estimada cae en `month` (None sin ventana: sin mes no hay historia).
    La usan `/diagnostics`, los ciclos de `/rotations` y `/changes`, para que las tres digan lo mismo."""
    if month is None:
        return market_signal(None, crop_name)
    found = market_history(dataset, market_choice(dataset, municipality, crop_id), crop_id, month)
    return market_signal(found.history, crop_name, found.product_name, found.override_reason)
