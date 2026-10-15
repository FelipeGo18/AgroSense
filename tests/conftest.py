"""Las pruebas de las cuentas corren contra un PostgreSQL real: la base `<POSTGRES_DB>_test`, aparte de la de desarrollo.

Se crea sola y se arma con las migraciones de Alembic, así que cada corrida prueba también las migraciones.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.accounts.limits import LIMITER
from backend.api.main import app
from backend.config.settings import get_settings
from backend.db.models import Base
from backend.db.session import get_db
from backend.db.state import forget_down


def alembic_config(url) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    config.attributes["configure_logger"] = False
    # La base de pruebas se rehace en cada corrida: no necesita copia de seguridad.
    config.attributes["backup_checked"] = True
    return config


@pytest.fixture(scope="session")
def database_url():
    url = get_settings().database_url
    test_url = url.set(database=f"{url.database}_test")
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(text("select 1 from pg_database where datname = :name"), {"name": test_url.database})
        if not exists:
            connection.execute(text(f'create database "{test_url.database}"'))
    admin.dispose()
    return test_url


@pytest.fixture(scope="session")
def engine(database_url) -> Iterator[Engine]:
    engine = create_engine(database_url)
    # Se parte de cero y se sube con las migraciones: lo mismo que hará quien clone el repositorio.
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade; create schema public;"))
    command.upgrade(alembic_config(database_url), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    """La API contra la base de pruebas, vacía en cada prueba."""
    forget_down()
    # Los límites por conexión viven en memoria: cada prueba parte sin nada anotado.
    LIMITER.reset()
    with engine.begin() as connection:
        tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        connection.execute(text(f"truncate {tables} cascade"))
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    # https: la cookie de sesión es `Secure` y el cliente de pruebas solo la devuelve por HTTPS, como un navegador.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------- Dataset publicado ----------

# Municipios de ejemplo para las pruebas (R5): códigos DIVIPOLA reales, el resto de columnas como las publica el DANE.
SAMPLE_MUNICIPALITIES = [
    {"cod_dpto": "15", "dpto": "BOYACÁ", "cod_mpio": "15646", "nom_mpio": "SAMACÁ", "latitud": "5,4925", "longitud": "-73,4856"},
    {"cod_dpto": "15", "dpto": "BOYACÁ", "cod_mpio": "15407", "nom_mpio": "VILLA DE LEYVA", "latitud": "5,6339", "longitud": "-73,5249"},
    {"cod_dpto": "25", "dpto": "CUNDINAMARCA", "cod_mpio": "25899", "nom_mpio": "ZIPAQUIRÁ", "latitud": "5,0221", "longitud": "-74,0048"},
    {"cod_dpto": "05", "dpto": "ANTIOQUIA", "cod_mpio": "05001", "nom_mpio": "MEDELLÍN", "latitud": "6,2466", "longitud": "-75,5817"},
]
SAMPLE_META = {
    "name": "DIVIPOLA - Códigos municipios (ejemplo de pruebas)",
    "license": "CC BY-SA 4.0",
    "downloaded_at": "2026-10-15T00:00:00+00:00",
}
SAMPLE_REGION = {
    "dataset_version": "0.0.0-pruebas",
    "region": {"id": "pruebas", "name": "Región de ejemplo de las pruebas", "country": "CO", "departments": ["15", "25"]},
}


@pytest.fixture(autouse=True)
def no_dataset(tmp_path_factory, monkeypatch):
    """Cada prueba parte sin dataset publicado: nada depende de lo que haya en data/published."""
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(tmp_path_factory.mktemp("sin-dataset")))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    """Un dataset de ejemplo publicado con el mismo código del pipeline."""
    import polars as pl

    from pipeline.build import publish
    from pipeline.sources import dane

    folder = tmp_path / "published"
    publish(SAMPLE_REGION, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), pl.DataFrame([dane.source(SAMPLE_META)]), folder)
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()
    return folder
