"""Conexión a la base de datos. El motor de decisión nunca importa este módulo (R6)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    # Si la base de datos no responde, se sabe en 3 segundos: la API no se queda colgada esperándola.
    return create_engine(get_settings().database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Una sesión de base de datos por petición. Confirma si todo salió bien y deshace si hubo un error."""
    with _session_factory()() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
