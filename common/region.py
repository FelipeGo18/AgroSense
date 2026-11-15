"""La región de AgroSense y su «hoy» (contrato, «Fechas»; decidido por Felipe el 11 de noviembre de 2026).

«Hoy» es el día en la región donde está la finca, con la zona horaria de `pipeline/region.yaml` (`region.timezone`), no
el día del servidor ni el de quien consulta: la fecha de siembra es del campo, y la misma consulta da lo mismo desde
cualquier país (R4). Está en `common/` porque lo usan la API y el pipeline sin importarse.

Las funciones reciben el instante (`now`) como argumento opcional: así las pruebas fijan la hora sin tocar el reloj.
"""

from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

REGION_FILE = Path(__file__).resolve().parent.parent / "pipeline" / "region.yaml"


class RegionError(ValueError):
    """`pipeline/region.yaml` no dice bien la zona horaria de la región. El mensaje dice qué corregir."""


def load_timezone(path: Path = REGION_FILE) -> ZoneInfo:
    try:
        region = yaml.safe_load(path.read_text(encoding="utf-8"))["region"]
    except (FileNotFoundError, KeyError, TypeError, yaml.YAMLError) as error:
        raise RegionError(f"No se pudo leer la región de {path.name}: {error}") from error
    name = region.get("timezone") if isinstance(region, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise RegionError(f"{path.name} debe decir `region.timezone` (por ejemplo America/Bogota).")
    try:
        return ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise RegionError(f"`region.timezone` de {path.name} no es una zona horaria conocida: {name!r}.") from error


@lru_cache
def region_timezone() -> ZoneInfo:
    return load_timezone()


def region_today(now: datetime | None = None) -> date:
    """El día de hoy en la región. `now`, si llega, debe traer su zona horaria."""
    return (now or datetime.now(UTC)).astimezone(region_timezone()).date()
