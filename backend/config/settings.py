"""Configuración del backend. Todo sale de variables de entorno (`.env` en desarrollo); ningún secreto va en el código."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url

# Nombres con que se llega a un PostgreSQL de esta máquina o de Docker Compose. Cualquier otro es una base remota.
LOCAL_HOSTS = frozenset({"db", "localhost", "127.0.0.1", "::1"})


def is_local(url: URL) -> bool:
    """Si la base está en esta máquina o en Docker Compose, y no en la nube."""
    return (url.host or "localhost") in LOCAL_HOSTS


class Settings(BaseSettings):
    # Una variable vacía cuenta como no puesta: Docker Compose pasa `AGROSENSE_DATABASE_URL=` cuando el .env no la trae.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # PostgreSQL local de Docker Compose. Las mismas variables que usa Compose para crear la base de datos. Las pruebas
    # usan siempre esta, aunque la API apunte a la nube (tests/conftest.py).
    postgres_db: str = "agrosense"
    postgres_user: str = "agrosense"
    postgres_password: str = ""
    # 127.0.0.1 y no «localhost»: Docker publica el puerto solo en IPv4 y con «localhost» algunos sistemas prueban antes IPv6 y esperan.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    # La base de datos en la nube: la cadena de conexión, `postgresql://usuario:clave@host:5432/base`. Con ella, la API y
    # las migraciones usan esa base en vez de la local. Sin `sslmode` en la cadena se exige SSL.
    cloud_database_url: str | None = Field(None, validation_alias="AGROSENSE_DATABASE_URL")

    # Si la API aplica las migraciones al arrancar. Sin la variable: sí con la base local y no con la de la nube, que es
    # compartida y se migra a mano (backend/README.md, «Base de datos en la nube»).
    auto_migrate: bool | None = Field(None, validation_alias="AGROSENSE_AUTO_MIGRATE")

    # Orígenes de la web que pueden cambiar datos (protección contra CSRF), separados por coma.
    web_origins: str = "http://localhost:5173"
    # La cookie de sesión solo viaja por HTTPS. Los navegadores tratan `localhost` como seguro, así que sirve en desarrollo.
    session_cookie_secure: bool = True

    # La documentación de la API (`/api/docs` y `/api/openapi.json`) solo en desarrollo: en producción no se publica el
    # mapa de la API. Docker Compose la enciende; `npm run api:types` la necesita.
    api_docs: bool = Field(False, validation_alias="AGROSENSE_API_DOCS")

    # Dónde está el dataset publicado por el pipeline (Parquet y manifest.json). Solo se lee.
    data_dir: Path = Field(Path("data/published"), validation_alias="AGROSENSE_DATA_DIR")

    # Precios de SIPSA al día (HU-222): las versiones que dejan las actualizaciones del servicio `market` (los crons de
    # `backend/market/updates.py`). La API solo las lee: nunca baja nada.
    market_dir: Path = Field(Path("data/market"), validation_alias="AGROSENSE_MARKET_DIR")

    # Logs de la terminal (HU-177): DEBUG solo en desarrollo; `console` con color o `json` (una línea por evento).
    log_level: str = Field("INFO", validation_alias="AGROSENSE_LOG_LEVEL")
    log_format: str = Field("console", validation_alias="AGROSENSE_LOG_FORMAT")

    @property
    def local_database_url(self) -> URL:
        """El PostgreSQL de Docker Compose, armado con las variables `POSTGRES_*`."""
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @computed_field
    @property
    def database_url(self) -> URL:
        """La base que usan la API y las migraciones: la de la nube si está puesta; si no, la local."""
        if not self.cloud_database_url:
            return self.local_database_url
        url = make_url(self.cloud_database_url).set(drivername="postgresql+psycopg")
        if "sslmode" not in url.query:
            url = url.update_query_dict({"sslmode": "require"})
        return url

    @property
    def migrate_on_startup(self) -> bool:
        return self.auto_migrate if self.auto_migrate is not None else is_local(self.database_url)

    @property
    def allowed_origins(self) -> frozenset[str]:
        return frozenset(origin.strip().rstrip("/") for origin in self.web_origins.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
