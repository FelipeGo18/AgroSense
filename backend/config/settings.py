"""Configuración del backend. Todo sale de variables de entorno (`.env` en desarrollo); ningún secreto va en el código."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL de las cuentas. Las mismas variables que usa Docker Compose para crear la base de datos.
    postgres_db: str
    postgres_user: str
    postgres_password: str
    # 127.0.0.1 y no «localhost»: Docker publica el puerto solo en IPv4 y con «localhost» algunos sistemas prueban antes IPv6 y esperan.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    # Orígenes de la web que pueden cambiar datos (protección contra CSRF), separados por coma.
    web_origins: str = "http://localhost:5173"
    # La cookie de sesión solo viaja por HTTPS. Los navegadores tratan `localhost` como seguro, así que sirve en desarrollo.
    session_cookie_secure: bool = True

    # Logs de la terminal (HU-177): DEBUG solo en desarrollo; `console` con color o `json` (una línea por evento).
    log_level: str = Field("INFO", validation_alias="AGROSENSE_LOG_LEVEL")
    log_format: str = Field("console", validation_alias="AGROSENSE_LOG_FORMAT")

    @computed_field
    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def allowed_origins(self) -> frozenset[str]:
        return frozenset(origin.strip().rstrip("/") for origin in self.web_origins.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
