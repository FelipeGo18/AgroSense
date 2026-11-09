"""Configuración del pipeline que cambia entre equipos o entornos: sale del `.env` (o de variables de entorno) y solo se
lee aquí. Lo que es igual para todos y tiene fuente (la región, las centrales) va en `pipeline/region.yaml`.

El pipeline no usa la base de datos: por eso no lee la configuración de la API (`backend/config/settings.py`).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Descargas de precios de SIPSA (HU-221, HU-222): tiempo máximo de cada descarga, contado de punta a punta (no por
    # lectura), y tamaño máximo. La respuesta completa del servicio pesa unos 300 MB y tarda de 2 a 5 minutos; el anexo del
    # boletín diario, unos 340 KB.
    market_timeout_s: float = Field(900, gt=0, validation_alias="AGROSENSE_MARKET_TIMEOUT_S")
    market_max_mb: float = Field(600, gt=0, validation_alias="AGROSENSE_MARKET_MAX_MB")


@lru_cache
def get_settings() -> PipelineSettings:
    return PipelineSettings()
