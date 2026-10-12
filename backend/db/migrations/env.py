"""Entorno de Alembic: a qué base de datos se conecta y contra qué modelos compara."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from backend.config.settings import get_settings
from backend.db.models import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Las tablas que deberían existir: todas las que reúne backend/db/models.py.
target_metadata = Base.metadata


def database_url():
    # Las pruebas pasan su propia base de datos; si no, la de las variables de entorno.
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: escribe el SQL sin conectarse, para revisarlo."""
    context.configure(
        url=database_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def require_backup() -> None:
    """Regla del proyecto: ninguna migración se aplica sin copia de seguridad antes.

    Quien la hace es `python -m backend.db.migrate`, que deja la marca `backup_checked`. Un `alembic upgrade` o
    `alembic downgrade` escrito a mano no pasó por la copia: se rechaza. Ver, comparar y crear migraciones
    (`current`, `history`, `check`, `revision`) no cambian la base de datos y siguen funcionando.
    """
    command = getattr(config.cmd_opts, "cmd", None)
    name = command[0].__name__ if command else ""
    if name in ("upgrade", "downgrade") and not config.attributes.get("backup_checked"):
        raise SystemExit(
            "Las migraciones se aplican con copia de seguridad antes:\n"
            "  uv run python -m backend.db.migrate              (en vez de alembic upgrade head)\n"
            "  uv run python -m backend.db.migrate --bajar -1   (en vez de alembic downgrade -1)"
        )


def run_migrations_online() -> None:
    require_backup()
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True)
        # Cada migración corre en una transacción: si falla a la mitad, PostgreSQL la deshace entera.
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
