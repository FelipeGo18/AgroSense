"""Límites municipales: Marco Geoestadístico Nacional (MGN) 2025 del DANE (HU-044; tabla `municipality_boundaries`).

Fuente: servicio `Divipola/Serv_DIVIPOLA_MGN_2025` del geoportal del DANE, capa «Municipio». Se pide por departamento
en GeoJSON y en WGS84 (EPSG:4326). La geometría se simplifica a unos 10 m: alcanza para dibujar el límite en el mapa y
validar que un lote cae dentro de su municipio, y deja la tabla liviana.

Lo propio de Colombia (DIVIPOLA, departamentos, el geoportal del DANE) vive solo en este adaptador (R7).
"""

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import shapely
from shapely.geometry import shape

SOURCE_ID = "dane_mgn_2025"
SERVICE = "https://geoportal.dane.gov.co/mparcgis/rest/services/Divipola/Serv_DIVIPOLA_MGN_2025/FeatureServer/317"
CACHE = Path("data/raw/dane")
# Unos 10 m en el ecuador. La validación del lote deja el mismo margen (backend/api/lots.py).
SIMPLIFY_DEGREES = 0.0001
# El geoportal rechaza el agente por defecto de Python: se dice quién pide y para qué.
USER_AGENT = "AgroSense-pipeline/1.0 (+https://github.com/FelipeGo18/AgroSense)"


def _file(department: str) -> str:
    return f"mgn_municipios_{department}.geojson"


def download(departments: list[str], cache: Path = CACHE) -> None:
    """Baja los municipios de cada departamento a la caché. Es lo único que usa la red."""
    cache.mkdir(parents=True, exist_ok=True)
    for department in departments:
        query = urllib.parse.urlencode(
            {"where": f"DPTO_CCDGO='{department}'", "outFields": "MPIO_CDPMP,MPIO_CNMBRE,MPIO_NANO", "outSR": 4326, "f": "geojson"}
        )
        request = urllib.request.Request(f"{SERVICE}/query?{query}", headers={"User-Agent": USER_AGENT})  # noqa: S310 - https fijo
        with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310 - dirección fija del DANE
            data = json.load(response)
        if "features" not in data:
            raise RuntimeError(f"El DANE no devolvió municipios para el departamento {department}: {str(data)[:200]}")
        (cache / _file(department)).write_text(json.dumps(data), encoding="utf-8")
    meta = {"downloaded_at": datetime.now(UTC).isoformat(timespec="seconds")}
    (cache / "mgn.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def read_cache(departments: list[str], cache: Path = CACHE) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for department in departments:
        path = cache / _file(department)
        if not path.exists():
            raise FileNotFoundError(
                f"No está la caché de límites del departamento {department}. Bájela con: uv run python -m pipeline.build --descargar"
            )
        features += json.loads(path.read_text(encoding="utf-8"))["features"]
    meta_path = cache / "mgn.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return features, meta


def boundaries(features: list[dict[str, Any]]) -> pl.DataFrame:
    """La tabla `municipality_boundaries`: el polígono de cada municipio en WKB (WGS84), simplificado y válido."""
    records = []
    for feature in features:
        geometry = shapely.make_valid(shape(feature["geometry"]))
        simple = shapely.make_valid(geometry.simplify(SIMPLIFY_DEGREES, preserve_topology=True))
        properties = {key.upper(): value for key, value in feature["properties"].items()}
        records.append({"municipality_id": properties["MPIO_CDPMP"], "geometry": shapely.to_wkb(simple), "source_id": SOURCE_ID})
    schema = {"municipality_id": pl.String, "geometry": pl.Binary, "source_id": pl.String}
    return pl.DataFrame(records, schema=schema).sort("municipality_id")


def source(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": SOURCE_ID,
        "name": "Marco Geoestadístico Nacional 2025 · Municipios",
        "institution": "Departamento Administrativo Nacional de Estadística (DANE)",
        "url": SERVICE,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": "Versión 2025 del Marco Geoestadístico Nacional",
        "coverage": "Colombia",
        "license": "Datos abiertos del DANE, con cita de la fuente (por confirmar en HU-122)",
        "notes": (
            "Límite de cada municipio, simplificado a unos 10 m para dibujarlo en el mapa y validar que un lote cae dentro de su municipio."
        ),
    }
