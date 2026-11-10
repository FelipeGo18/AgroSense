"""La base de datos en la nube: la API y las migraciones la usan con SSL, no la migran solas al arrancar, y las
pruebas nunca la tocan (backend/README.md, «Base de datos en la nube»)."""

import pytest
from alembic import command
from pydantic import ValidationError
from structlog.testing import capture_logs

from backend.config.settings import Settings, get_settings, is_local
from backend.db import migrate
from tests.conftest import alembic_config

# Una cadena de conexión de la nube. Usuario, clave y host de ejemplo (R5).
HOST = "base.nube-de-ejemplo.com"
CLOUD = f"postgresql://usuario.ejemplo:clave-de-ejemplo@{HOST}:5432/postgres"


def cloud_settings(monkeypatch, **env: str) -> Settings:
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", CLOUD)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_con_la_cadena_de_la_nube_se_conecta_con_psycopg_y_exige_ssl(monkeypatch):
    url = cloud_settings(monkeypatch).database_url
    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database, url.username) == (HOST, 5432, "postgres", "usuario.ejemplo")
    assert url.query["sslmode"] == "require"
    assert not is_local(url)


def test_un_sslmode_escrito_en_la_cadena_se_respeta(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", f"{CLOUD}?sslmode=verify-full")
    assert Settings(_env_file=None).database_url.query["sslmode"] == "verify-full"


def test_sin_la_cadena_de_la_nube_se_usa_la_base_local_y_se_migra_al_arrancar(monkeypatch):
    monkeypatch.delenv("AGROSENSE_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None, postgres_host="db")
    assert settings.database_url == settings.local_database_url
    assert is_local(settings.database_url)
    assert settings.migrate_on_startup is True


def test_la_base_de_la_nube_no_se_migra_sola_al_arrancar_salvo_que_se_pida(monkeypatch):
    assert cloud_settings(monkeypatch).migrate_on_startup is False
    assert cloud_settings(monkeypatch, AGROSENSE_AUTO_MIGRATE="true").migrate_on_startup is True


def test_una_variable_vacia_cuenta_como_no_puesta(monkeypatch):
    # Docker Compose pasa `AGROSENSE_DATABASE_URL=` cuando el .env no la trae.
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", "")
    monkeypatch.setenv("AGROSENSE_AUTO_MIGRATE", "")
    settings = Settings(_env_file=None)
    assert settings.cloud_database_url is None
    assert settings.auto_migrate is None


def test_las_pruebas_nunca_usan_la_base_de_la_nube(database_url):
    # tests/conftest.py la reemplaza por la local, venga de Compose o del .env.
    assert is_local(get_settings().database_url)
    assert is_local(database_url)
    assert database_url.database.endswith("_test")


def test_la_copia_de_la_nube_viaja_con_el_mismo_ssl(monkeypatch, tmp_path):
    monkeypatch.setattr(migrate.shutil, "which", lambda name: f"/usr/bin/{name}")
    url = cloud_settings(monkeypatch).database_url
    args, env = migrate._dump_command(url, tmp_path / "copia.dump")
    assert args[0] == "pg_dump"
    assert f"--host={HOST}" in args
    assert env["PGSSLMODE"] == "require"
    assert env["PGPASSWORD"] == "clave-de-ejemplo"


def test_sin_pg_dump_la_base_de_la_nube_no_se_copia_con_el_contenedor_local(monkeypatch, tmp_path):
    # El `pg_dump` del contenedor `db` solo alcanza la base local: copiaría la base equivocada.
    monkeypatch.setattr(migrate.shutil, "which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    url = cloud_settings(monkeypatch).database_url
    with pytest.raises(migrate.BackupError, match="imagen de la app"):
        migrate._dump_command(url, tmp_path / "copia.dump")


def test_al_arrancar_sin_migrar_solo_avisa_que_falta_una_migracion(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, "1.2")
    try:
        with capture_logs() as logs:
            migrate.on_startup(database_url, config, auto=False)
        assert migrate.current_revision(database_url) == "1.2"  # no la tocó
        pending = [entry for entry in logs if entry["event"] == "migration_pending"]
        assert len(pending) == 1
        assert (pending[0]["log_level"], pending[0]["current_migration"], pending[0]["expected_migration"]) == ("warning", "1.2", "1.3")
    finally:
        command.upgrade(config, "head")


def test_al_arrancar_sin_migrar_y_al_dia_lo_dice(engine, database_url):
    with capture_logs() as logs:
        migrate.on_startup(database_url, alembic_config(database_url), auto=False)
    assert [(entry["event"], entry["current_migration"]) for entry in logs] == [("migration_up_to_date", "1.3")]


# ---------- Una cadena mal escrita ----------

SECRET = "clave-que-no-debe-salir"


@pytest.mark.parametrize(
    "value",
    [
        f"AGROSENSE_DATABASE_URL=postgresql://usuario.ejemplo:{SECRET}@{HOST}:5432/postgres",  # con el nombre delante
        f'"postgresql://usuario.ejemplo:{SECRET}@{HOST}:5432/postgres"',  # entre comillas
        f"usuario.ejemplo:{SECRET}@{HOST}:5432/postgres",  # sin postgresql://
        f"https://usuario.ejemplo:{SECRET}@{HOST}:5432/postgres",  # otro esquema
        f"postgresql://usuario.ejemplo:{SECRET}@{HOST}:5432",  # sin la base
    ],
)
def test_una_cadena_mal_escrita_dice_que_corregir_sin_mostrar_la_clave(monkeypatch, value):
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", value)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    message = str(error.value)
    assert "AGROSENSE_DATABASE_URL no tiene la forma postgresql://usuario:clave@host:5432/base" in message
    assert SECRET not in message
    assert HOST not in message


def test_los_espacios_y_el_salto_de_linea_al_pegarla_no_estorban(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", f"  {CLOUD}\n")
    assert Settings(_env_file=None).database_url.host == HOST
    monkeypatch.setenv("AGROSENSE_DATABASE_URL", "   ")
    assert Settings(_env_file=None).cloud_database_url is None
