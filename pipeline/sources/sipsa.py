"""Precios mayoristas diarios: SIPSA del DANE (HU-221; specs/02-contratos.md, tabla `market_price_day`).

Fuente: el servicio web del Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA), del
DANE. Es SOAP 1.2 y la operación `promediosSipsaParcial` devuelve, de una vez y sin filtros, el precio mínimo, medio y
máximo por kilo de cada producto en cada central de abastos y cada día desde febrero de 2020 (unos 300 MB de XML).

Lo propio de Colombia (SIPSA, sus centrales y sus nombres de producto) vive solo en este adaptador (R7). Los productos
no se mapean todavía a `crop_id`: el catálogo de cultivos no existe (HU-061). Se publican con el nombre del DANE.
"""

import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from typing import IO, Any

import polars as pl

SOURCE_ID = "dane_sipsa"
SERVICE_URL = "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"
PAGE_URL = (
    "https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa/"
    "servicio-web-para-consulta-de-la-base-de-datos-de-sipsa"
)
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
    "municipality_id": pl.String,
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
    """Baja la respuesta completa del servicio a la caché, por partes (pesa unos 300 MB y tarda un par de minutos)."""
    cache.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(  # noqa: S310 - dirección fija del DANE
        SERVICE_URL, data=ENVELOPE.encode(), headers={"Content-Type": "application/soap+xml; charset=utf-8"}
    )
    partial = cache / f"{ROWS_FILE}.part"
    with urllib.request.urlopen(request, timeout=600) as response, partial.open("wb") as out:  # noqa: S310
        while chunk := response.read(1 << 20):
            out.write(chunk)
    partial.replace(cache / ROWS_FILE)
    (cache / META_FILE).write_text(datetime.now(UTC).isoformat(timespec="seconds"), encoding="utf-8")
    return cache / ROWS_FILE


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


def read_cache(markets: dict[str, str], cache: Path = CACHE) -> tuple[pl.DataFrame, str]:
    """Las filas de las centrales de `markets` (código de SIPSA → nombre que se muestra) y la fecha de descarga.

    Recorre el XML por partes: no lo carga entero en memoria.
    """
    rows_path, meta_path = cache / ROWS_FILE, cache / META_FILE
    if not rows_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de SIPSA en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    return prices(rows_path, markets), meta_path.read_text(encoding="utf-8").strip()


def prices(xml: Path | IO[bytes], markets: dict[str, str]) -> pl.DataFrame:
    """La tabla `market_price_day` a partir de la respuesta del servicio, ordenada por su llave (R4)."""
    records = []
    # La respuesta viene de una dirección fija del DANE. El expat de Python 3.12 no carga entidades externas y limita la
    # expansión de entidades, así que un XML hostil no lee archivos ni agota la memoria.
    for _event, element in ET.iterparse(xml):  # noqa: S314
        if element.tag != "return":
            continue
        row = {child.tag: child.text for child in element}
        element.clear()
        market_id = row.get("fuenId")
        average = _pesos(row.get("promedioKg"))
        # Sin precio medio no hay precio de ese día: la fila no se publica (R1).
        if market_id not in markets or average is None:
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
                "municipality_id": row.get("muniId"),
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
        # Sin verificar: el DANE publica sus «Términos y condiciones» aparte y nadie del equipo los ha revisado.
        "license": "Por verificar en los términos y condiciones del DANE",
        "notes": (
            "Precio mínimo, medio y máximo por kilo de cada producto en la central de abastos, por día. Es el precio "
            "mayorista (lo que se paga en la central), no el de la tienda. Los nombres con asterisco en SIPSA juntan "
            "varias variedades. Se publican en pesos enteros."
        ),
    }
