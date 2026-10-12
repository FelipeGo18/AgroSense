"""Aplica las migraciones, siempre con una copia de seguridad antes (backend/README.md, «Migraciones»).

    uv run python -m backend.db.migrate              # copia la base y aplica lo que falte
    uv run python -m backend.db.migrate --bajar 1.2  # copia la base y vuelve a como quedó tras la 1.2
    uv run python -m backend.db.migrate --bajar -1   # copia la base y deshace la última
    uv run python -m backend.db.migrate --al-arrancar  # como arranca la API: si algo falla lo registra y sigue

Regla del proyecto: **ninguna migración se aplica sin copia de seguridad**. Si la copia falla, no se migra.
Por eso las migraciones se aplican con este comando y no con `alembic upgrade` directo, que se niega a correr.
La única excepción es una base recién creada, que no tiene nada que copiar.
"""

import argparse
import os
import shutil
import subprocess  # noqa: S404 - se llama a pg_dump con argumentos fijos, sin pasar por un intérprete de órdenes
import sys
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, create_engine
from sqlalchemy.exc import OperationalError

from backend.config import logging
from backend.config.logging import get_logger
from backend.config.settings import get_settings

BACKUPS = Path("backups")
# Se conservan las copias más recientes; las demás se borran para no llenar el disco.
KEEP = 20


class BackupError(RuntimeError):
    pass


def current_revision(url: URL) -> str | None:
    """En qué migración está la base de datos; nulo si todavía no tiene ninguna."""
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def backup_name(database: str, current: str, target: str, now: datetime) -> str:
    """`agrosense_20261012-153000_de-1.3_a-1.4.dump`: qué base, cuándo y entre qué migraciones."""
    return f"{database}_{now:%Y%m%d-%H%M%S}_de-{current}_a-{target}.dump"


def _dump_command(url: URL, output: Path) -> tuple[list[str], dict[str, str]]:
    """Con `pg_dump` instalado (en la imagen de la app) se usa directo. Si no (un computador de desarrollo sin
    PostgreSQL instalado), se le pide al contenedor de la base de datos de Docker Compose, que lo trae."""
    if shutil.which("pg_dump"):
        args = ["pg_dump", "--format=custom", "--no-owner", f"--host={url.host}", f"--port={url.port}", f"--username={url.username}"]
        return [*args, f"--file={output}", str(url.database)], {**os.environ, "PGPASSWORD": url.password or ""}
    if shutil.which("docker"):
        inner = ["pg_dump", "--format=custom", "--no-owner", f"--username={url.username}", str(url.database)]
        return ["docker", "compose", "exec", "-T", "db", *inner], dict(os.environ)
    raise BackupError("No se encontró `pg_dump` ni Docker: no hay con qué hacer la copia de seguridad.")


def backup(url: URL, current: str, target: str, folder: Path = BACKUPS) -> Path:
    """Copia toda la base de datos a un archivo. Si algo falla, lanza `BackupError` y no deja un archivo a medias."""
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / backup_name(str(url.database), current, target, datetime.now(UTC))
    args, env = _dump_command(url, output)
    to_stdout = args[0] == "docker"
    try:
        with output.open("wb") if to_stdout else open(os.devnull, "wb") as sink:
            result = subprocess.run(args, env=env, stdout=sink, stderr=subprocess.PIPE, check=False, timeout=600)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired) as exc:
        output.unlink(missing_ok=True)
        raise BackupError(f"No se pudo hacer la copia de seguridad: {exc}") from exc
    # Un volcado en formato propio de PostgreSQL empieza por «PGDMP»: así se sabe que el archivo sirve.
    if result.returncode != 0 or not output.exists() or output.read_bytes()[:5] != b"PGDMP":
        output.unlink(missing_ok=True)
        detail = result.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["sin detalle"]
        raise BackupError(f"No se pudo hacer la copia de seguridad: {detail[0]}")
    return output


def prune(folder: Path = BACKUPS, keep: int = KEEP) -> list[Path]:
    """Borra las copias más viejas y deja las `keep` más recientes."""
    old = sorted(folder.glob("*.dump"), key=lambda file: file.stat().st_mtime, reverse=True)[keep:]
    for file in old:
        file.unlink()
    return old


def _label(scripts: ScriptDirectory, current: str, target: str) -> str:
    """A qué migración se llega al deshacer, para el nombre de la copia: «-1» desde la 1.3 es la 1.2; antes de la primera, «vacia»."""
    if not target.startswith("-"):
        return "vacia" if target == "base" else target
    revision: str | None = current
    for _ in range(int(target[1:])):
        script = scripts.get_revision(revision) if revision else None
        revision = script.down_revision if script else None  # type: ignore[assignment]
    return revision or "vacia"


def migrate(config: Config, url: URL, target: str = "head", down: bool = False, folder: Path = BACKUPS) -> Path | None:
    """Copia la base y aplica (o deshace) migraciones hasta `target`. Devuelve la copia, o nulo si no hizo falta."""
    scripts = ScriptDirectory.from_config(config)
    current = current_revision(url)
    goal = scripts.get_current_head() if target == "head" else target
    if not down and current == goal:
        return None  # ya está al día: no hay migración ni copia
    saved = None
    if current is not None:
        saved = backup(url, current, _label(scripts, current, target) if down else str(goal), folder)
        prune(folder)
    # Marca para `migrations/env.py`: esta corrida sí pasó por la copia de seguridad.
    config.attributes["backup_checked"] = True
    (command.downgrade if down else command.upgrade)(config, target)
    return saved


def on_startup(url: URL, config: Config) -> None:
    """Como arranca la API: intenta copiar y migrar, y pase lo que pase deja que la API suba.

    Si la base de datos no responde, o la copia o una migración fallan, lo escribe en el log y termina bien. La API
    arranca, lo que no usa la base de datos funciona, y las cuentas quedan apagadas hasta que el esquema esté al día
    (backend/db/state.py).
    """
    log = get_logger("agrosense.migrate")
    expected = ScriptDirectory.from_config(config).get_current_head()
    try:
        before = current_revision(url)
    except OperationalError:
        log.warning(
            "migration_skipped", reason="database_down", detail="La base de datos no responde: no se migró. Las cuentas quedan apagadas."
        )
        return
    try:
        saved = migrate(config, url)
    except Exception as error:  # noqa: BLE001 - cualquier fallo al migrar se registra y no tumba la API
        log.error(
            "migration_failed",
            current_migration=current_revision(url),
            expected_migration=expected,
            detail=f"La migración {expected} no se completó: {error}. Las cuentas quedan apagadas.",
            exc_info=not isinstance(error, BackupError),
        )
        return
    after = current_revision(url)
    if before == after:
        log.info(
            "migration_up_to_date",
            current_migration=after,
            detail=f"La base de datos ya está al día (migración {after}): no hubo nada que aplicar",
        )
    else:
        copy = f"con copia de seguridad en {saved}" if saved else "sin copia: la base estaba recién creada"
        log.info(
            "migration_applied",
            from_migration=before,
            current_migration=after,
            backup=str(saved) if saved else None,
            detail=f"Migraciones aplicadas: de {before or 'vacía'} a {after}, {copy}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica las migraciones, con copia de seguridad antes.")
    parser.add_argument("--bajar", metavar="MIGRACIÓN", help="Deshace migraciones hasta esa (por ejemplo 1.2), o «-1» para la última.")
    parser.add_argument(
        "--al-arrancar", action="store_true", help="Como arranca la API en Docker: si algo falla lo registra y termina bien."
    )
    args = parser.parse_args()
    settings = get_settings()
    url = settings.database_url
    if args.al_arrancar:
        logging.configure(settings.log_level, settings.log_format)
        on_startup(url, Config("alembic.ini"))
        return
    try:
        before = current_revision(url)
    except OperationalError:
        sys.exit("La base de datos no responde. ¿Está arriba? (docker compose up -d db)")
    try:
        saved = migrate(Config("alembic.ini"), url, target=args.bajar or "head", down=bool(args.bajar))
    except BackupError as error:
        sys.exit(f"{error}\nNo se aplicó ninguna migración.")
    after = current_revision(url)
    if before == after:
        print(f"La base de datos ya está al día ({after}).")
        return
    print(f"Copia de seguridad: {saved}" if saved else "Base recién creada: no había nada que copiar.")
    print(f"Migraciones aplicadas: de {before or 'vacía'} a {after or 'vacía'}.")


if __name__ == "__main__":
    main()
