"""Precios mayoristas de las centrales de abastos: `/api/v1/market/*` (HU-221; specs/02-contratos.md, «Endpoints»).

Las rutas solo traen datos: filtran por central o por producto y devuelven. Lo calculado (el último precio, el de hace
una semana, el cambio y el orden) ya viene en `market_price_latest`, que escriben el pipeline y las actualizaciones de
precios (HU-222). Qué versión de los precios se sirve lo decide el acceso a los datos (`market_tables`, con
`backend/market/store.py`), no la ruta.

Es lo que pasó en la central: nunca un pronóstico de precio (decisión 4). No baja nada, no usa la base de datos ni guarda
nada (R9).
"""

from datetime import date, datetime, timedelta
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.config.settings import get_settings
from backend.dataset import Dataset
from backend.market import store
from backend.market.store import MarketTables

router = APIRouter(prefix="/api/v1/market", tags=["precios"])

MARKET_UNAVAILABLE = "Los precios de las centrales de abastos no están disponibles en este momento."
UNKNOWN_MARKET = "No tenemos precios de esa central de abastos."
UNKNOWN_PRODUCT = "No tenemos precios de ese producto en esa central de abastos."
# Cuántos días de precios trae la historia de un producto.
SERIES_DAYS = 365


class Market(BaseModel):
    market_id: str
    name: str


class Price(BaseModel):
    """Pesos por kilo de un día. El mínimo y el máximo pueden faltar: el DANE no siempre los da (R1)."""

    date: date
    min_cop_kg: int | None
    avg_cop_kg: int
    max_cop_kg: int | None


class ProductPrice(BaseModel):
    product_id: str
    product: str
    group: str
    # El DANE junta varias variedades en un solo precio (en SIPSA lleva asterisco).
    several_varieties: bool
    latest: Price
    # El precio del último día con dato hasta una semana antes, y su cambio. Nulos si no hay con qué comparar.
    week_ago: Price | None
    change_pct: float | None


class MarketPrices(BaseModel):
    # Qué versión de los precios se usó (R4): la del dataset publicado o la de una actualización (HU-222).
    version: str
    updated_at: datetime | None
    market: Market
    markets: list[Market]
    # El último día con precios en esta central.
    date: date
    products: list[ProductPrice]
    # La fuente del último día (`dane_sipsa` o, entre descargas del servicio, `dane_sipsa_boletin`) y la cita textual que
    # pide, de su fila en `sources` (R8): la web la muestra tal cual. Nula si la fuente no pide una.
    source_id: str
    citation: str | None


class SeasonMonth(BaseModel):
    month: int
    # 1,00 es un mes como cualquiera de su año; 0,80, un 20 % más barato que el promedio del año.
    seasonal_index: float


class Season(BaseModel):
    years: int
    first_year: int
    last_year: int
    months: list[SeasonMonth]


class ProductHistory(BaseModel):
    version: str
    updated_at: datetime | None
    product_id: str
    product: str
    group: str
    several_varieties: bool
    market: Market
    latest: Price
    # Los precios del último año, del más viejo al más nuevo.
    days: list[Price]
    # Nulo con menos años completos de los necesarios: no se inventa una temporada (R1).
    season: Season | None
    source_id: str
    citation: str | None


def market_tables(dataset: Dataset = Depends(require_dataset)) -> MarketTables:
    """El acceso a los precios (dependencia de las rutas): la última versión o el dataset publicado. Sin precios, 503."""
    tables = store.current_tables(dataset, get_settings().market_dir)
    if tables is None:
        raise ApiError(503, "market_unavailable", MARKET_UNAVAILABLE, log=f"El dataset {dataset.version} no trae precios de SIPSA")
    return tables


def _market(tables: MarketTables, market_id: str | None) -> Market:
    """La central pedida, o la primera de la región (Corabastos) si no se pide ninguna."""
    for code, name in tables.markets:
        if market_id is None or code == market_id:
            return Market(market_id=code, name=name)
    raise ApiError(404, "unknown_market", UNKNOWN_MARKET)


def _price(row: dict[str, Any], prefix: str = "") -> Price:
    return Price(
        date=row[f"{prefix}date"],
        min_cop_kg=row[f"{prefix}min_cop_kg"],
        avg_cop_kg=row[f"{prefix}avg_cop_kg"],
        max_cop_kg=row[f"{prefix}max_cop_kg"],
    )


def _product(row: dict[str, Any]) -> ProductPrice:
    return ProductPrice(
        product_id=row["product_id"],
        product=row["product"],
        group=row["group"],
        several_varieties=row["several_varieties"],
        latest=_price(row),
        week_ago=_price(row, "week_ago_") if row["week_ago_date"] is not None else None,
        change_pct=row["change_pct"],
    )


@router.get("/prices")
def market_prices(request: Request, market_id: str | None = Query(None), tables: MarketTables = Depends(market_tables)) -> MarketPrices:
    """El último precio de cada producto en la central, con su cambio frente a hace una semana."""
    market = _market(tables, market_id)
    # `market_price_latest` ya viene en el orden en que se muestran (`position`): filtrar lo conserva.
    rows = tables.latest.filter(pl.col("market_id") == market.market_id).to_dicts()
    if not rows:
        raise ApiError(404, "unknown_market", UNKNOWN_MARKET)
    explain(request, f"Precios consultados: {len(rows)} productos en {market.name}, versión {tables.version}")
    return MarketPrices(
        version=tables.version,
        updated_at=tables.updated_at,
        market=market,
        markets=[Market(market_id=code, name=name) for code, name in tables.markets],
        date=rows[0]["market_date"],
        products=[_product(row) for row in rows],
        source_id=rows[0]["market_source_id"],
        citation=tables.citation(rows[0]["market_source_id"]),
    )


@router.get("/prices/{product_id}")
def product_history(
    request: Request, product_id: str, market_id: str | None = Query(None), tables: MarketTables = Depends(market_tables)
) -> ProductHistory:
    """Los precios del último año de un producto en la central y en qué meses suele estar más caro o más barato."""
    market = _market(tables, market_id)
    found = tables.latest.filter((pl.col("market_id") == market.market_id) & (pl.col("product_id") == product_id)).to_dicts()
    if not found:
        raise ApiError(404, "unknown_product", UNKNOWN_PRODUCT)
    row = found[0]
    days = tables.prices.filter(
        (pl.col("market_id") == market.market_id)
        & (pl.col("product_id") == product_id)
        & (pl.col("date") > row["date"] - timedelta(days=SERIES_DAYS))
    )
    months = (
        tables.season.filter((pl.col("market_id") == market.market_id) & (pl.col("product_id") == product_id)).to_dicts()
        if tables.season is not None
        else []
    )
    season = (
        Season(
            years=months[0]["years"],
            first_year=months[0]["first_year"],
            last_year=months[0]["last_year"],
            months=[SeasonMonth(month=m["month"], seasonal_index=m["seasonal_index"]) for m in months],
        )
        if months
        else None
    )
    explain(request, f"Precios de {product_id} consultados en {market.name}: {days.height} días, versión {tables.version}")
    return ProductHistory(
        version=tables.version,
        updated_at=tables.updated_at,
        product_id=product_id,
        product=row["product"],
        group=row["group"],
        several_varieties=row["several_varieties"],
        market=market,
        latest=_price(row),
        days=[_price(day) for day in days.iter_rows(named=True)],
        season=season,
        source_id=row["source_id"],
        citation=tables.citation(row["source_id"]),
    )
