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
    # Ni versiones de precios bajadas (HU-222): cada prueba parte de una carpeta vacía y la API la vuelve a mirar.
    monkeypatch.setenv("AGROSENSE_MARKET_DIR", str(tmp_path_factory.mktemp("sin-precios")))
    get_settings.cache_clear()
    from backend.market import store

    monkeypatch.setattr(store, "served", store.Served())
    yield
    get_settings.cache_clear()


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    """Un dataset de ejemplo publicado con el mismo código del pipeline."""
    import polars as pl

    from pipeline import catalog as crops_catalog
    from pipeline.build import publish
    from pipeline.sources import dane, dane_mgn

    folder = tmp_path / "published"
    sources = pl.DataFrame([dane.source(SAMPLE_META), dane_mgn.source(SAMPLE_META)])
    municipalities = dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"])
    # El catálogo es el real (catalog/crops.yaml): son datos con fuente, no de ejemplo.
    catalog = crops_catalog.load()
    crops, stages, catalog_sources = crops_catalog.build(catalog)
    sources = pl.concat([sources, catalog_sources], how="diagonal_relaxed")
    publish(SAMPLE_REGION, municipalities, sources, folder, sample_boundaries(municipalities), (catalog["version"], crops, stages))
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()
    return folder


def sample_boundaries(municipalities):
    """Límites de ejemplo (R5): un cuadrado de 0,1° (unos 11 km) alrededor del punto de cada municipio."""
    import polars as pl
    import shapely
    from shapely.geometry import box

    rows = [
        {
            "municipality_id": m["municipality_id"],
            "geometry": shapely.to_wkb(box(m["lon"] - 0.05, m["lat"] - 0.05, m["lon"] + 0.05, m["lat"] + 0.05)),
            "source_id": "dane_mgn_2025",
        }
        for m in municipalities.iter_rows(named=True)
    ]
    return pl.DataFrame(rows, schema={"municipality_id": pl.String, "geometry": pl.Binary, "source_id": pl.String})


# Precios de SIPSA de ejemplo (HU-221): las columnas y los códigos como los manda el servicio del DANE; los precios son
# de ejemplo. Corabastos (1) y Tunja (9) se publican; la central de Medellín (2) no está en la región.
SAMPLE_MARKETS = {"1": "Corabastos (Bogotá)", "9": "Tunja (Complejo de Servicios del Sur)"}


def sipsa_row(market_id: str, product: str, day: str, low, avg, high, group: str = "TUBERCULOS, RAICES Y PLATANOS") -> str:
    names = {"1": "Bogotá, D.C., Corabastos", "9": "Tunja, Complejo de Servicios del Sur", "2": "Medellín, Central Mayorista de Antioquia"}
    towns = {"1": "11001", "9": "15001", "2": "05001"}
    return (
        f"<return><artiNombre>{product}</artiNombre><deptNombre>X</deptNombre><enmaFecha>{day}T00:00:00-05:00</enmaFecha>"
        f"<fuenId>{market_id}</fuenId><fuenNombre>{names[market_id]}</fuenNombre><futiId>1</futiId><grupNombre>{group}</grupNombre>"
        f"<maximoKg>{high}</maximoKg><minimoKg>{low}</minimoKg><muniId>{towns[market_id]}</muniId><promedioKg>{avg}</promedioKg></return>"
    )


SAMPLE_SIPSA_ROWS = [
    sipsa_row("1", "Papa negra*", "2026-10-05", 2400, 2500, 2600),
    sipsa_row("1", "Papa negra*", "2026-10-12", 2600, 2750, 2900),
    sipsa_row("1", "Papa negra*", "2026-10-19", 2800, 2925, 3000),
    # Sin mínimo ese día: el servicio manda 0.
    sipsa_row("1", "Papa criolla", "2026-10-19", 0, "4972.4", "5111.11111111111111"),
    sipsa_row("1", "Zanahoria", "2026-10-17", 1500, 1604, 1666.6666666666667, group="VERDURAS Y HORTALIZAS"),
    # Sin precio medio: no hay precio de ese día.
    sipsa_row("1", "Zanahoria", "2026-10-19", 1500, "", 1700, group="VERDURAS Y HORTALIZAS"),
    sipsa_row("1", "Aguacate*", "2026-10-19", 10000, 10313, 11000, group="FRUTAS"),
    sipsa_row("9", "Papa negra*", "2026-10-19", 2500, 2600, 2700),
    sipsa_row("2", "Papa negra*", "2026-10-19", 2700, 2800, 2900),
]


def sipsa_xml(rows: list[str]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?><S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope"><S:Body>'
        '<ns2:promediosSipsaParcialResponse xmlns:ns2="http://servicios.sipsa.co.gov.dane/">'
        + "".join(rows)
        + "</ns2:promediosSipsaParcialResponse></S:Body></S:Envelope>"
    )


@pytest.fixture
def market_dataset(tmp_path, monkeypatch):
    """El dataset de ejemplo con los precios de ejemplo de SIPSA."""
    import io

    import polars as pl

    from pipeline.build import publish
    from pipeline.sources import dane, sipsa

    prices = sipsa.prices(io.BytesIO(sipsa_xml(SAMPLE_SIPSA_ROWS).encode()), SAMPLE_MARKETS)
    folder = tmp_path / "published"
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    publish(SAMPLE_REGION, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, folder, prices=prices)
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()
    return folder
