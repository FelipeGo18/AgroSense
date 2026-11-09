"""Precios mayoristas diarios: SIPSA del DANE (HU-221; specs/02-contratos.md, tabla `market_price_day`).

Fuente: el servicio web del Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA), del
DANE. Es SOAP 1.2 y la operación `promediosSipsaParcial` devuelve, de una vez y sin filtros, el precio mínimo, medio y
máximo por kilo de cada producto en cada central de abastos y cada día desde febrero de 2020 (unos 300 MB de XML).

Lo propio de Colombia (SIPSA, sus centrales y sus nombres de producto) vive solo en este adaptador y en la configuración
del pipeline (R7). Los productos se publican con el nombre del DANE. Qué producto da el precio de cada cultivo lo dice
`pipeline/sipsa_crops.yaml` (HU-003), que `pipeline.build` valida contra estos precios.
"""

import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import IO, Any

import polars as pl

from pipeline.settings import get_settings
from pipeline.sources import dane
from pipeline.sources.fetch import fetch

SOURCE_ID = "dane_sipsa"
SERVICE_URL = "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"
PAGE_URL = (
    "https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa/"
    "servicio-web-para-consulta-de-la-base-de-datos-de-sipsa"
)
# Licencia de uso (HU-221): los términos del portal del DANE y la cita textual que piden a quien use sus datos.
TERMS_URL, CITATION = dane.TERMS_URL, dane.CITATION
ENVELOPE = (
    '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ser="http://servicios.sipsa.co.gov.dane/">'
    "<soap:Body><ser:promediosSipsaParcial/></soap:Body></soap:Envelope>"
)

CACHE = Path("data/raw/sipsa")
ROWS_FILE = "promedios_parcial.xml"
META_FILE = "promedios_parcial.meta.txt"

SCHEMA = {
    "product_id": pl.String,
    "market_id": pl.String,
    "date": pl.Date,
    "product": pl.String,
    "group": pl.String,
    "several_varieties": pl.Boolean,
    "market": pl.String,
    "min_cop_kg": pl.Int64,
    "avg_cop_kg": pl.Int64,
    "max_cop_kg": pl.Int64,
    "source_id": pl.String,
}

# El DANE escribe los grupos en mayúsculas y sin tildes: se muestran como se leen.
GROUPS = {
    "TUBERCULOS, RAICES Y PLATANOS": "Tubérculos, raíces y plátanos",
    "VERDURAS Y HORTALIZAS": "Verduras y hortalizas",
    "FRUTAS": "Frutas",
}


def download(cache: Path = CACHE) -> Path:
    """Baja la respuesta completa del servicio a la caché, por partes (pesa unos 300 MB y tarda de 2 a 5 minutos).

    Corta por tiempo total y por tamaño (`AGROSENSE_MARKET_TIMEOUT_S`, `AGROSENSE_MARKET_MAX_MB`): una respuesta rara del
    DANE no llena el disco ni deja la descarga colgada.
    """
    settings = get_settings()
    request = urllib.request.Request(  # noqa: S310 - dirección fija del DANE
        SERVICE_URL, data=ENVELOPE.encode(), headers={"Content-Type": "application/soap+xml; charset=utf-8"}
    )
    fetch(request, cache / ROWS_FILE, settings.market_timeout_s, int(settings.market_max_mb * 2**20))
    (cache / META_FILE).write_text(datetime.now(UTC).isoformat(timespec="seconds"), encoding="utf-8")
    return cache / ROWS_FILE


class PricesError(ValueError):
    """Unos precios no cumplen las reglas de `market_price_day`. El mensaje dice qué falla."""


def validate(prices: pl.DataFrame, known_sources: set[str]) -> None:
    """La llave (producto, central, día) no se repite; hay precio medio, y el mínimo y el máximo, si están, lo encierran
    (R1); cada fila cita una fuente conocida (R8). Se tolera un peso: el DANE redondea el medio («1563» con mínimo y
    máximo de 1562,5). La usan el pipeline y las actualizaciones de precios (HU-222)."""
    if prices.is_empty():
        raise PricesError("`market_price_day` quedó vacía: revise las centrales de region.yaml.")
    repeated = prices.filter(pl.struct("product_id", "market_id", "date").is_duplicated())
    if not repeated.is_empty():
        raise PricesError(f"Precios repetidos para un mismo producto, central y día: {repeated.head(3).to_dicts()}")
    bad = prices.filter(
        pl.col("avg_cop_kg").is_null()
        | (pl.col("avg_cop_kg") <= 0)
        | (pl.col("min_cop_kg") > pl.col("avg_cop_kg") + 1).fill_null(False)
        | (pl.col("avg_cop_kg") > pl.col("max_cop_kg") + 1).fill_null(False)
    )
    if not bad.is_empty():
        raise PricesError(f"Precios sin promedio o con el medio fuera del mínimo y el máximo: {bad.head(3).to_dicts()}")
    unknown = set(prices["source_id"].unique().to_list()) - known_sources
    if unknown:
        raise PricesError(f"Precios con una fuente que no está en `sources`: {sorted(unknown)}")


def product_id(name: str) -> str:
    """«Papa negra*» → «papa-negra»; «Fríjol verde*» → «frijol-verde». Estable: es la llave en la URL de la web."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


def _pesos(value: str | None) -> int | None:
    """El DANE manda decimales largos («1555.5555…»): se publican pesos enteros. Sin dato, nulo (R1).

    Un 0 tampoco es un precio: el servicio lo manda cuando no tiene el mínimo o el máximo de ese día.
    """
    if value is None or value.strip() == "":
        return None
    pesos = round(float(value))
    return pesos if pesos > 0 else None


def read_cache(markets: dict[str, str], cache: Path = CACHE, counts: Counter[str] | None = None) -> tuple[pl.DataFrame, str]:
    """Las filas de las centrales de `markets` (código de SIPSA → nombre que se muestra) y la fecha de descarga.

    Recorre el XML por partes: no lo carga entero en memoria. Con `counts`, cuenta lo leído y lo descartado (ver `prices`).
    """
    rows_path, meta_path = cache / ROWS_FILE, cache / META_FILE
    if not rows_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de SIPSA en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    return prices(rows_path, markets, counts), meta_path.read_text(encoding="utf-8").strip()


def prices(xml: Path | IO[bytes], markets: dict[str, str], counts: Counter[str] | None = None) -> pl.DataFrame:
    """La tabla `market_price_day` a partir de la respuesta del servicio, ordenada por su llave (R4).

    Con `counts`, suma ahí las filas leídas (`read`) y las descartadas por motivo, para el log del pipeline (HU-177):
    `other_market` (una central que no está en la región) y `no_average` (sin precio medio ese día, R1).
    """
    counts = Counter() if counts is None else counts
    records = []
    # La respuesta viene de una dirección fija del DANE. El expat de Python 3.12 no carga entidades externas y limita la
    # expansión de entidades, así que un XML hostil no lee archivos ni agota la memoria.
    for _event, element in ET.iterparse(xml):  # noqa: S314
        if element.tag != "return":
            continue
        row = {child.tag: child.text for child in element}
        element.clear()
        counts["read"] += 1
        market_id = row.get("fuenId")
        if market_id not in markets:
            counts["other_market"] += 1
            continue
        average = _pesos(row.get("promedioKg"))
        # Sin precio medio no hay precio de ese día: la fila no se publica (R1).
        if average is None:
            counts["no_average"] += 1
            continue
        name = (row.get("artiNombre") or "").strip()
        # El asterisco del DANE quiere decir que el precio junta varias variedades del producto.
        several = name.endswith("*")
        name = name.rstrip("* ").strip()
        group = (row.get("grupNombre") or "").strip()
        records.append(
            {
                "product_id": product_id(name),
                "market_id": market_id,
                "date": date.fromisoformat((row.get("enmaFecha") or "")[:10]),
                "product": name,
                "group": GROUPS.get(group, group.capitalize()),
                "several_varieties": several,
                "market": markets[market_id],
                "min_cop_kg": _pesos(row.get("minimoKg")),
                "avg_cop_kg": average,
                "max_cop_kg": _pesos(row.get("maximoKg")),
                "source_id": SOURCE_ID,
            }
        )
    return pl.DataFrame(records, schema=SCHEMA).sort("product_id", "market_id", "date")


# Años completos que se necesitan, como mínimo, para decir en qué meses suele subir o bajar un precio.
MIN_YEARS = 3


def seasonal(prices: pl.DataFrame) -> pl.DataFrame:
    """La tabla `market_price_season`: en qué meses suele estar el precio por encima o por debajo de su año.

    Para cada año completo (los doce meses con precio), el promedio del mes se divide por el promedio de ese año: así la
    inflación entre años no cuenta. El índice del mes es el promedio de esos cocientes (1,00 = un mes como cualquiera).
    Con menos de `MIN_YEARS` años completos el producto no tiene índice: no se inventa (R1).
    """
    monthly = (
        prices.with_columns(pl.col("date").dt.year().alias("year"), pl.col("date").dt.month().alias("month"))
        .group_by("product_id", "market_id", "year", "month")
        .agg(pl.col("avg_cop_kg").mean().alias("avg"))
    )
    full = monthly.group_by("product_id", "market_id", "year").agg(pl.len().alias("months")).filter(pl.col("months") == 12)
    ratios = monthly.join(full, on=["product_id", "market_id", "year"]).with_columns(
        (pl.col("avg") / pl.col("avg").mean().over("product_id", "market_id", "year")).alias("ratio")
    )
    years = ratios.group_by("product_id", "market_id").agg(
        pl.col("year").n_unique().alias("years"), pl.col("year").min().alias("first_year"), pl.col("year").max().alias("last_year")
    )
    return (
        ratios.group_by("product_id", "market_id", "month")
        .agg(pl.col("ratio").mean().round(3).alias("seasonal_index"))
        .join(years, on=["product_id", "market_id"])
        .filter(pl.col("years") >= MIN_YEARS)
        .with_columns(pl.col("month").cast(pl.Int8), pl.col("years").cast(pl.Int16), pl.lit(SOURCE_ID).alias("source_id"))
        .select("product_id", "market_id", "month", "seasonal_index", "years", "first_year", "last_year", "source_id")
        .sort("product_id", "market_id", "month")
    )


MONTH_SCHEMA = {
    "crop_id": pl.String,
    "market_id": pl.String,
    "month": pl.Int8,
    "product_id": pl.String,
    "price_cop_kg": pl.Int64,
    "price_year": pl.Int32,
    "volume_t": pl.Float64,
    "seasonal_index": pl.Float64,
    "years": pl.Int16,
    "quality": pl.String,
    "source_id": pl.String,
}


def monthly(prices: pl.DataFrame, season: pl.DataFrame, crops: dict[str, Any]) -> pl.DataFrame:
    """La tabla `market_month` (HU-051): por cultivo, central y mes, el índice estacional y el precio de ese mes.

    - El cultivo sale de `crops` (`sipsa_crops.yaml`, HU-003). Un cultivo sin producto no tiene filas (R1).
    - `seasonal_index` y `years` son los de `market_price_season`: sin 3 años completos no hay filas (R1).
    - `price_cop_kg` es el precio medio de ese mes en `price_year`, el último año completo del producto en esa central.
      Es lo que se pagó, no un precio estimado: los 12 meses salen del mismo año, así que se comparan sin inflación.
    - `volume_t` va nulo: `promediosSipsaParcial` no trae volumen (R1).
    - `quality` es `partial` cuando el último año completo es anterior al año pasado: SIPSA dejó de publicar ese
      producto en esa central o le faltan meses recientes. Si no, `ok`.
    """
    mapping = pl.DataFrame(
        [{"crop_id": crop_id, "product_id": entry["product_id"]} for crop_id, entry in crops.items() if entry.get("product_id")],
        schema={"crop_id": pl.String, "product_id": pl.String},
    )
    if prices.is_empty() or mapping.is_empty() or season.is_empty():
        return pl.DataFrame(schema=MONTH_SCHEMA)
    last_year_expected = prices["date"].max().year - 1
    month_prices = (
        prices.with_columns(pl.col("date").dt.year().alias("price_year"), pl.col("date").dt.month().cast(pl.Int8).alias("month"))
        .group_by("product_id", "market_id", "price_year", "month")
        .agg(pl.col("avg_cop_kg").mean().round(0).cast(pl.Int64).alias("price_cop_kg"))
    )
    return (
        season.join(mapping, on="product_id")
        .with_columns(pl.col("last_year").cast(pl.Int32).alias("price_year"))
        .join(month_prices, on=["product_id", "market_id", "price_year", "month"], how="left")
        .with_columns(
            pl.lit(None, dtype=pl.Float64).alias("volume_t"),
            pl.when(pl.col("price_year") >= last_year_expected).then(pl.lit("ok")).otherwise(pl.lit("partial")).alias("quality"),
            pl.lit(SOURCE_ID).alias("source_id"),
        )
        .select(list(MONTH_SCHEMA))
        .cast(MONTH_SCHEMA)
        .sort("crop_id", "market_id", "month")
    )


# Los grupos en el orden en que le importan al altiplano: primero lo que más se siembra (papa), las frutas al final.
GROUP_ORDER = ("Tubérculos, raíces y plátanos", "Verduras y hortalizas", "Frutas")
# Contra qué día se compara el último precio: el último con precio hasta una semana antes.
WEEK_DAYS = 7

LATEST_SCHEMA = {
    "market_id": pl.String,
    "product_id": pl.String,
    "position": pl.Int16,
    "product": pl.String,
    "group": pl.String,
    "several_varieties": pl.Boolean,
    "market": pl.String,
    "date": pl.Date,
    "min_cop_kg": pl.Int64,
    "avg_cop_kg": pl.Int64,
    "max_cop_kg": pl.Int64,
    "week_ago_date": pl.Date,
    "week_ago_min_cop_kg": pl.Int64,
    "week_ago_avg_cop_kg": pl.Int64,
    "week_ago_max_cop_kg": pl.Int64,
    "change_pct": pl.Float64,
    "market_date": pl.Date,
    "market_source_id": pl.String,
    "source_id": pl.String,
}


def latest(prices: pl.DataFrame) -> pl.DataFrame:
    """La tabla `market_price_latest`: por central y producto, el último precio, el de hace una semana y el cambio.

    La escriben el pipeline y cada actualización de precios (HU-222), para que la API solo filtre y devuelva.

    - El último precio es el del último día con precio del producto en esa central; el nombre, el grupo y el asterisco
      son los de ese día.
    - El de hace una semana es el del último día con precio hasta `WEEK_DAYS` días antes. Sin ese día, el precio de
      hace una semana y `change_pct` van nulos (R1).
    - `change_pct` es el cambio del precio medio, en %, con un decimal.
    - `market_date` es el último día con precios en la central, y `market_source_id` la fuente de ese día.
    - `position` es el orden en que se muestran los productos de una central: por grupo (`GROUP_ORDER`) y por nombre.
    """
    if prices.is_empty():
        return pl.DataFrame(schema=LATEST_SCHEMA)
    ordered = prices.sort("market_id", "product_id", "date")
    keys = ["market_id", "product_id"]
    last = ordered.group_by(keys, maintain_order=True).last()
    week = (
        ordered.join(last.select(*keys, (pl.col("date") - pl.duration(days=WEEK_DAYS)).alias("cutoff")), on=keys)
        .filter(pl.col("date") <= pl.col("cutoff"))
        .group_by(keys, maintain_order=True)
        .last()
        .select(*keys, *(pl.col(col).alias(f"week_ago_{col}") for col in ("date", "min_cop_kg", "avg_cop_kg", "max_cop_kg")))
    )
    market = (
        prices.sort("market_id", "date", "source_id")
        .group_by("market_id", maintain_order=True)
        .agg(pl.col("date").last().alias("market_date"), pl.col("source_id").last().alias("market_source_id"))
    )
    rank = {group: i for i, group in enumerate(GROUP_ORDER)}
    return (
        last.join(week, on=keys, how="left")
        .join(market, on="market_id")
        .with_columns(
            ((pl.col("avg_cop_kg") / pl.col("week_ago_avg_cop_kg") - 1) * 100).round(1).alias("change_pct"),
            pl.col("group").replace_strict(rank, default=len(GROUP_ORDER), return_dtype=pl.Int16).alias("group_rank"),
        )
        .sort("market_id", "group_rank", "group", "product", "product_id")
        .with_columns(pl.int_range(1, pl.len() + 1, dtype=pl.Int16).over("market_id").alias("position"))
        .select(list(LATEST_SCHEMA))
        .cast(LATEST_SCHEMA)
    )


def source(table: pl.DataFrame, downloaded_at: str) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8)."""
    period = f"Del {table['date'].min()} al {table['date'].max()}" if table.height else None
    markets = " · ".join(sorted(set(table["market"].to_list())))
    return {
        "source_id": SOURCE_ID,
        "name": "SIPSA · Precios mayoristas diarios (servicio web)",
        "institution": "Departamento Administrativo Nacional de Estadística (DANE)",
        "url": PAGE_URL,
        "downloaded_at": downloaded_at,
        "period_covered": period,
        "coverage": f"Colombia; publicadas: {markets}" if markets else "Colombia",
        # Revisados el 8 de noviembre de 2026: la página del servicio web no trae condiciones propias, así que valen las
        # del portal del DANE. Permiten usar y transformar los datos con una cita textual (CITATION), que la web muestra.
        "license": (
            f"Términos y condiciones del DANE ({TERMS_URL}): se autoriza el uso, aprovechamiento, transformación y análisis "
            f"de la información citando «{CITATION}». Se rigen por la ley colombiana y el DANE puede cambiarlos sin aviso."
        ),
        "citation": CITATION,
        "notes": (
            "Precio mínimo, medio y máximo por kilo de cada producto en la central de abastos, por día. Es el precio "
            "mayorista (lo que se paga en la central), no el de la tienda. Los nombres con asterisco en SIPSA juntan "
            "varias variedades. Se publican en pesos enteros."
        ),
    }
