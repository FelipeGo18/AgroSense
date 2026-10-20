"""Precios mayoristas de las centrales de abastos: `/api/v1/market/*` (HU-221; specs/02-contratos.md, «Endpoints»).

Lee las tablas `market_price_day` y `market_price_season` del dataset publicado (SIPSA del DANE). Es lo que pasó en la
central: nunca un pronóstico de precio (decisión 4). No usa la base de datos ni guarda nada (R9).
"""

from datetime import date, timedelta

import polars as pl
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.catalogs import require_dataset
from backend.api.errors import ApiError, explain
from backend.dataset import Dataset

router = APIRouter(prefix="/api/v1/market", tags=["precios"])

MARKET_UNAVAILABLE = "Los precios de las centrales de abastos no están disponibles en este momento."
UNKNOWN_MARKET = "No tenemos precios de esa central de abastos."
UNKNOWN_PRODUCT = "No tenemos precios de ese producto en esa central de abastos."
# Cuántos días atrás se compara el precio de hoy («frente a hace una semana») y cuántos días trae la serie.
WEEK = timedelta(days=7)
SERIES_DAYS = 365
# Los grupos en el orden en que le importan al altiplano: primero lo que más se siembra (papa), las frutas al final.
GROUP_ORDER = ("Tubérculos, raíces y plátanos", "Verduras y hortalizas", "Frutas")


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
    # El precio medio del último día con dato hasta una semana antes, y su cambio. Nulos si no hay con qué comparar.
    week_ago: Price | None
    change_pct: float | None


class MarketPrices(BaseModel):
    market: Market
    markets: list[Market]
    # El último día con precios en esta central.
    date: date
    products: list[ProductPrice]
    source_id: str


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


def _prices(dataset: Dataset) -> pl.DataFrame:
    if dataset.market_prices is None or dataset.market_prices.is_empty():
        raise ApiError(503, "market_unavailable", MARKET_UNAVAILABLE, log=f"El dataset {dataset.version} no trae market_price_day")
    return dataset.market_prices


def _markets(prices: pl.DataFrame) -> list[Market]:
    rows = prices.select("market_id", "market").unique().sort("market_id").iter_rows()
    return [Market(market_id=market_id, name=name) for market_id, name in rows]


def _market(markets: list[Market], market_id: str | None) -> Market:
    """La central pedida, o la primera (Corabastos) si no se pide ninguna."""
    if market_id is None:
        return markets[0]
    for market in markets:
        if market.market_id == market_id:
            return market
    raise ApiError(404, "unknown_market", UNKNOWN_MARKET)


def _price(row: dict) -> Price:
    return Price(date=row["date"], min_cop_kg=row["min_cop_kg"], avg_cop_kg=row["avg_cop_kg"], max_cop_kg=row["max_cop_kg"])


def _latest(rows: pl.DataFrame) -> tuple[Price, Price | None, float | None]:
    """El último precio, el del último día con dato hasta una semana antes y el cambio entre los dos, en %."""
    latest = rows.row(rows.height - 1, named=True)
    before = rows.filter(pl.col("date") <= latest["date"] - WEEK)
    if before.is_empty():
        return _price(latest), None, None
    week_ago = before.row(before.height - 1, named=True)
    change = round((latest["avg_cop_kg"] / week_ago["avg_cop_kg"] - 1) * 100, 1)
    return _price(latest), _price(week_ago), change


@router.get("/prices")
def market_prices(request: Request, market_id: str | None = Query(None), dataset: Dataset = Depends(require_dataset)) -> MarketPrices:
    """El último precio de cada producto en la central, con su cambio frente a hace una semana."""
    prices = _prices(dataset)
    markets = _markets(prices)
    market = _market(markets, market_id)
    rows = prices.filter(pl.col("market_id") == market.market_id)
    products = [
        ProductPrice(
            product_id=product["product_id"][0],
            product=product["product"][-1],
            group=product["group"][-1],
            several_varieties=product["several_varieties"][-1],
            **dict(zip(("latest", "week_ago", "change_pct"), _latest(product), strict=True)),
        )
        for product in rows.partition_by("product_id", maintain_order=True)
    ]
    products.sort(key=lambda p: (GROUP_ORDER.index(p.group) if p.group in GROUP_ORDER else len(GROUP_ORDER), p.group, p.product))
    explain(request, f"Precios consultados: {len(products)} productos en {market.name}, dataset {dataset.version}")
    return MarketPrices(
        market=market,
        markets=markets,
        date=max(p.latest.date for p in products),
        products=products,
        source_id=rows["source_id"][0],
    )


@router.get("/prices/{product_id}")
def product_history(
    request: Request, product_id: str, market_id: str | None = Query(None), dataset: Dataset = Depends(require_dataset)
) -> ProductHistory:
    """Los precios del último año de un producto en la central y en qué meses suele estar más caro o más barato."""
    prices = _prices(dataset)
    market = _market(_markets(prices), market_id)
    rows = prices.filter((pl.col("market_id") == market.market_id) & (pl.col("product_id") == product_id))
    if rows.is_empty():
        raise ApiError(404, "unknown_product", UNKNOWN_PRODUCT)
    latest = rows.row(rows.height - 1, named=True)
    days = rows.filter(pl.col("date") > latest["date"] - timedelta(days=SERIES_DAYS))
    season = None
    if dataset.market_season is not None:
        months = dataset.market_season.filter((pl.col("market_id") == market.market_id) & (pl.col("product_id") == product_id))
        if months.height:
            first = months.row(0, named=True)
            season = Season(
                years=first["years"],
                first_year=first["first_year"],
                last_year=first["last_year"],
                months=[SeasonMonth(month=m, seasonal_index=i) for m, i in months.select("month", "seasonal_index").iter_rows()],
            )
    explain(request, f"Precios de {product_id} consultados en {market.name}: {days.height} días, dataset {dataset.version}")
    return ProductHistory(
        product_id=product_id,
        product=latest["product"],
        group=latest["group"],
        several_varieties=latest["several_varieties"],
        market=market,
        latest=_price(latest),
        days=[_price(row) for row in days.iter_rows(named=True)],
        season=season,
        source_id=latest["source_id"],
    )
