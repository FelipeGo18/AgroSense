"""Configuración del pipeline y de las actualizaciones de precios que cambia entre equipos o entornos: sale del `.env` (o
de variables de entorno) y solo se lee aquí. Lo que es igual para todos y tiene fuente (la región, las centrales) va en
`pipeline/region.yaml`.

Ni el pipeline ni las actualizaciones de precios usan la base de datos: por eso no leen la configuración de la API
(`backend/config/settings.py`), que la exige.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Logs de la terminal (HU-177), con la misma configuración que la API (`common/logging.py`).
    log_level: str = Field("INFO", validation_alias="AGROSENSE_LOG_LEVEL")
    log_format: str = Field("console", validation_alias="AGROSENSE_LOG_FORMAT")

    # El dataset publicado, del que parten las actualizaciones de precios si no hay una versión más nueva.
    data_dir: Path = Field(Path("data/published"), validation_alias="AGROSENSE_DATA_DIR")
    # Dónde dejan las actualizaciones de precios sus versiones (HU-222). La API las lee de la misma carpeta.
    market_dir: Path = Field(Path("data/market"), validation_alias="AGROSENSE_MARKET_DIR")

    # NASA POWER (HU-041): tiempo máximo de cada descarga, contado de punta a punta (no por lectura), y tamaño máximo de
    # cada respuesta. Hoy una celda con 45 años de mínima, máxima y lluvia pesa unos 0,8 MB y baja en unos 3 s.
    power_timeout_s: float = Field(120, gt=0, validation_alias="AGROSENSE_POWER_TIMEOUT_S")
    power_max_mb: float = Field(10, gt=0, validation_alias="AGROSENSE_POWER_MAX_MB")

    # Descargas de precios de SIPSA (HU-221, HU-222): tiempo máximo de cada descarga, contado de punta a punta (no por
    # lectura), y tamaño máximo. La respuesta completa del servicio pesa unos 300 MB y tarda de 2 a 5 minutos; el anexo del
    # boletín diario, unos 340 KB.
    market_timeout_s: float = Field(900, gt=0, validation_alias="AGROSENSE_MARKET_TIMEOUT_S")
    market_max_mb: float = Field(600, gt=0, validation_alias="AGROSENSE_MARKET_MAX_MB")


@lru_cache
def get_settings() -> PipelineSettings:
    return PipelineSettings()
