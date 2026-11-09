"""Municipios de Colombia: DIVIPOLA del DANE (HU-044; specs/02-contratos.md, tabla `municipalities`).

Fuente: «DIVIPOLA - Códigos municipios», publicada por el DANE en datos.gov.co, licencia CC BY-SA 4.0. Trae el código
DIVIPOLA de 5 dígitos, el departamento, el nombre oficial (en mayúsculas) y unas coordenadas de referencia del municipio.

Lo propio de Colombia (DIVIPOLA, departamentos) vive solo en este adaptador (R7). Los límites municipales (Marco
Geoestadístico Nacional) y la altitud (NASADEM) llegan con sus propias HU; mientras tanto esas columnas van nulas, no
inventadas (R1).
"""

import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

SOURCE_ID = "dane_divipola"
DATASET = "gdxc-w37w"
ROWS_URL = f"https://www.datos.gov.co/resource/{DATASET}.json?$limit=5000"
META_URL = f"https://www.datos.gov.co/api/views/{DATASET}.json"
PAGE_URL = f"https://www.datos.gov.co/d/{DATASET}"
# Los términos y condiciones del portal del DANE, que valen para su información, y la cita textual que piden a quien la
# use (verificados el 8 de noviembre de 2026, HU-221). Va en la columna `citation` de cada fuente del DANE.
TERMS_URL = "https://www.dane.gov.co/index.php/terminos-y-condiciones"
CITATION = "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co"

CACHE = Path("data/raw/dane")
ROWS_FILE = "divipola.json"
META_FILE = "divipola.meta.json"

# Palabras que van en minúscula dentro de un nombre: «Villa de Leyva», «San Juan de Rioseco».
_SMALL = frozenset({"de", "del", "la", "las", "los", "el", "y", "e", "en"})


def download(cache: Path = CACHE) -> Path:
    """Baja la tabla y sus metadatos a la caché. Es lo único que usa la red; lo demás lee de la caché."""
    cache.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ROWS_URL, timeout=60) as response:  # noqa: S310 - dirección fija de datos.gov.co
        rows = json.load(response)
    with urllib.request.urlopen(META_URL, timeout=60) as response:  # noqa: S310
        meta = json.load(response)
    (cache / ROWS_FILE).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    keep = {
        "name": meta.get("name"),
        "attribution": meta.get("attribution"),
        "license": (meta.get("license") or {}).get("name"),
        "rows_updated_at": meta.get("rowsUpdatedAt"),
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (cache / META_FILE).write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache / ROWS_FILE


def read_cache(cache: Path = CACHE) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows_path, meta_path = cache / ROWS_FILE, cache / META_FILE
    if not rows_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de DIVIPOLA en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    return json.loads(rows_path.read_text(encoding="utf-8")), json.loads(meta_path.read_text(encoding="utf-8"))


def display_name(official: str) -> str:
    """El nombre oficial viene en mayúsculas («VILLA DE LEYVA»); se escribe como se lee («Villa de Leyva»).
    Las siglas con punto quedan en mayúscula («Bogotá, D.C.»)."""
    words = []
    for i, word in enumerate(official.strip().lower().split()):
        if "." in word:
            words.append(word.upper())
        elif i > 0 and word in _SMALL:
            words.append(word)
        else:
            # La primera letra, también después de un paréntesis o un guion: «(Gachetá)», «Paz-Río».
            words.append(re.sub(r"(^|[(\-])(\w)", lambda m: m.group(1) + m.group(2).upper(), word))
    return " ".join(words)


def _coordinate(value: Any) -> float | None:
    """Las coordenadas vienen como texto con coma decimal («-73,5491»). Sin dato, nulo (R1)."""
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).replace(",", "."))


def municipalities(rows: list[dict[str, Any]], departments: list[str]) -> pl.DataFrame:
    """La tabla `municipalities` de los departamentos de la región, ordenada por código (R4)."""
    wanted = set(departments)
    records = [
        {
            "municipality_id": row["cod_mpio"],
            "name": display_name(row["nom_mpio"]),
            "department_id": row["cod_dpto"],
            "department": display_name(row["dpto"]),
            "lat": _coordinate(row.get("latitud")),
            "lon": _coordinate(row.get("longitud")),
            # Llegan con NASADEM (HU-206) y NASA POWER (HU-044): todavía no hay dato, así que van nulas.
            "altitude_m": None,
            "climate_cell_elevation_m": None,
            "tmean_annual_c": None,
            "slope_pct": None,
            "source_ids": [SOURCE_ID],
        }
        for row in rows
        if row.get("cod_dpto") in wanted
    ]
    schema = {
        "municipality_id": pl.String,
        "name": pl.String,
        "department_id": pl.String,
        "department": pl.String,
        "lat": pl.Float64,
        "lon": pl.Float64,
        "altitude_m": pl.Float64,
        "climate_cell_elevation_m": pl.Float64,
        "tmean_annual_c": pl.Float64,
        "slope_pct": pl.Float64,
        "source_ids": pl.List(pl.String),
    }
    return pl.DataFrame(records, schema=schema).sort("municipality_id")


def source(meta: dict[str, Any]) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8)."""
    updated = meta.get("rows_updated_at")
    period = f"Actualizada por el DANE el {datetime.fromtimestamp(updated, UTC):%Y-%m-%d}" if updated else None
    return {
        "source_id": SOURCE_ID,
        "name": meta.get("name") or "DIVIPOLA - Códigos municipios",
        "institution": "Departamento Administrativo Nacional de Estadística (DANE)",
        "url": PAGE_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": "Colombia",
        "license": meta.get("license") or "Creative Commons Attribution | Share Alike 4.0 International",
        "citation": CITATION,
        "notes": (
            "Códigos DIVIPOLA de municipio y departamento, nombre y coordenadas de referencia del municipio. "
            "Los nombres se escriben en mayúscula inicial a partir del nombre oficial, que viene en mayúsculas."
        ),
    }
