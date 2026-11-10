"""Precio del día del boletín diario de SIPSA (HU-222; specs/02-contratos.md, tabla `market_price_day`).

Fuente: el anexo en Excel del boletín diario de precios mayoristas del DANE (unos 340 KB), en el portal del DANE y no en
el servicio web. Trae el precio medio por kilo del día de cada producto en 16 centrales, entre ellas Corabastos y Tunja,
con los mismos nombres de producto que el servicio. No trae el mínimo ni el máximo: van nulos (R1).

Es la misma serie que `promediosSipsaParcial` (`pipeline/sources/sipsa.py`): el 6 de noviembre de 2026 los 63 precios
de Corabastos y Tunja del anexo eran iguales a los del servicio, y no faltaba ninguno. Aun así es otro canal, y por eso
cada fila dice de dónde salió (`source_id = dane_sipsa_boletin`): nunca se mezcla en silencio (R8). La descarga semanal
del servicio reemplaza estos días por los del servicio, que sí traen el mínimo y el máximo.

El boletín sale de lunes a viernes, salvo festivos: un día sin boletín responde 404 y no es un error.

Lo propio de Colombia (el boletín, sus columnas y los nombres de los meses) vive solo en este adaptador (R7).
"""

import re
import unicodedata
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
from openpyxl import load_workbook

from pipeline.settings import get_settings
from pipeline.sources import sipsa
from pipeline.sources.fetch import fetch

SOURCE_ID = "dane_sipsa_boletin"
FILES_URL = "https://www.dane.gov.co/files/operaciones/SIPSA"
PAGE_URL = (
    "https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa/"
    "componente-precios-mayoristas"
)
# Así abrevia el DANE los meses en el nombre del archivo: «anex-SIPSADiario-06nov2026.xlsx» (verificado para los 12
# meses el 9 de noviembre de 2026; septiembre es «sep», no «sept»).
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MONTH_NAMES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
# La columna de cada central en el anexo, por su código de SIPSA (`fuenId`, el `market_id` de `region.yaml`).
COLUMNS = {"1": "Bogotá, Corabastos", "9": "Tunja"}
HEADER = "Precio $/Kg"
# Los grupos del anexo, escritos como los de `promediosSipsaParcial` en la web.
GROUPS = {
    "Verduras y hortalizas": "Verduras y hortalizas",
    "Frutas frescas": "Frutas",
    "Tubérculos, raíces y plátanos": "Tubérculos, raíces y plátanos",
}


class BulletinError(ValueError):
    """El anexo no tiene la forma esperada (el DANE cambió el formato) o no es del día pedido."""


def url(day: date) -> str:
    return f"{FILES_URL}/anex-SIPSADiario-{day.day:02d}{MONTHS[day.month - 1]}{day.year}.xlsx"


def download(day: date, folder: Path) -> Path | None:
    """Baja el anexo del día a `folder`. Sin boletín ese día (sábado, domingo o festivo), el DANE responde 404: nada."""
    settings = get_settings()
    request = urllib.request.Request(url(day), headers={"User-Agent": "AgroSense"})  # noqa: S310 - dirección fija del DANE
    try:
        return fetch(request, folder / f"boletin-{day:%Y%m%d}.xlsx", settings.market_timeout_s, int(settings.market_max_mb * 2**20))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _text(value: Any) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _day_of(rows: list[tuple]) -> date | None:
    """El día del boletín, como lo escribe arriba: «Viernes 6 de noviembre de 2026»."""
    for row in rows:
        for cell in row:
            found = re.search(r"(\d{1,2}) de ([a-z]+) de (\d{4})", _plain(_text(cell)))
            if found and found.group(2) in MONTH_NAMES:
                return date(int(found.group(3)), MONTH_NAMES.index(found.group(2)) + 1, int(found.group(1)))
    return None


def _pesos(value: Any) -> int | None:
    """Un número es el precio; «n.d.» (no disponible) o una celda vacía no son precio (R1)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    pesos = round(float(value))
    return pesos if pesos > 0 else None


def prices(path: Path, day: date, markets: dict[str, str]) -> pl.DataFrame:
    """Los precios medios del día de las centrales de `markets` (código de SIPSA → nombre que se muestra).

    Revisa que el anexo tenga su fila de centrales y que sea de `day`: si el DANE cambia el formato, falla con
    `BulletinError` en vez de leer mal (R1). Cada boletín trae solo las centrales que reportaron ese día (Tunja, unos tres
    días por semana): una central sin columna no tiene precios ese día, no es un error. Sale con las columnas de
    `market_price_day`, ordenada por su llave (R4).
    """
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(book.worksheets[0].iter_rows(values_only=True))
    finally:
        # En modo de solo lectura el archivo queda abierto hasta cerrarlo, y así no se podría borrar la descarga.
        book.close()
    header_at = next((i for i, row in enumerate(rows) if row and _text(row[0]) == HEADER), None)
    if header_at is None:
        raise BulletinError(f"El anexo del {day} no trae la fila «{HEADER}»: el DANE cambió el formato.")
    found = _day_of(rows[:header_at])
    if found != day:
        raise BulletinError(f"El anexo pedido para el {day} dice ser del {found}.")
    columns = {_text(name): i for i, name in enumerate(rows[header_at]) if name is not None}
    present = {market_id: columns[COLUMNS[market_id]] for market_id in markets if COLUMNS.get(market_id) in columns}
    records, group = [], None
    for row in rows[header_at + 2 :]:
        name = _text(row[0]) if row else ""
        if not name or name.startswith(("*", "Var%", "n.d.")):
            continue
        values = row[1:]
        if all(value is None for value in values):
            group = GROUPS.get(name, name)
            continue
        several = "*" in name
        clean = " ".join(name.replace("*", " ").split())
        for market_id, column in present.items():
            market = markets[market_id]
            average = _pesos(row[column])
            if average is None:
                continue
            records.append(
                {
                    "product_id": sipsa.product_id(clean),
                    "market_id": market_id,
                    "date": day,
                    "product": clean,
                    "group": group,
                    "several_varieties": several,
                    "market": market,
                    "min_cop_kg": None,
                    "avg_cop_kg": average,
                    "max_cop_kg": None,
                    "source_id": SOURCE_ID,
                }
            )
    return pl.DataFrame(records, schema=sipsa.SCHEMA).sort("product_id", "market_id", "date")


def source(table: pl.DataFrame, downloaded_at: str) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8)."""
    period = f"Del {table['date'].min()} al {table['date'].max()}" if table.height else None
    return {
        "source_id": SOURCE_ID,
        "name": "SIPSA · Boletín diario de precios mayoristas (anexo)",
        "institution": "Departamento Administrativo Nacional de Estadística (DANE)",
        "url": PAGE_URL,
        "downloaded_at": downloaded_at,
        "period_covered": period,
        "coverage": "Colombia; se publican las centrales de la región",
        "license": (
            f"Términos y condiciones del DANE ({sipsa.TERMS_URL}): se autoriza el uso, aprovechamiento, transformación y "
            f"análisis de la información citando «{sipsa.CITATION}»."
        ),
        "citation": sipsa.CITATION,
        "notes": (
            "Precio medio por kilo del día en la central, de lunes a viernes. Es la misma serie del servicio web de SIPSA "
            "(dane_sipsa), sin el mínimo ni el máximo: van nulos. Se usa solo para los días que el servicio todavía no se "
            "ha bajado; la descarga semanal del servicio los reemplaza."
        ),
    }
