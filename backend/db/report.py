"""El comentario del PR con las migraciones nuevas y su SQL (HU-229). No se conecta a ninguna base: Alembic escribe el SQL
en modo offline.

    python -m backend.db.report backend/db/migrations/versions/1/1.4_algo.py [...]

Recibe los archivos que el PR agrega (los calcula el workflow con git) y escribe Markdown en la salida estándar.
"""

import io
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.db.renumber import Migration, RenumberError, chain, read

MAX_SQL = 60_000  # un comentario de GitHub admite 65 536 caracteres


def ordered(paths: list[Path]) -> list[Migration]:
    migrations = [read(path) for path in paths]
    starts = {m.down_revision for m in migrations} - {m.revision for m in migrations}
    if len(starts) != 1:
        raise RenumberError("Las migraciones nuevas no forman una sola cadena.")
    return chain(migrations, starts.pop())


def offline_sql(start: str | None, end: str) -> str:
    buffer = io.StringIO()
    config = Config("alembic.ini", output_buffer=buffer)
    config.attributes["configure_logger"] = False
    command.upgrade(config, f"{start}:{end}" if start else end, sql=True)
    return buffer.getvalue().strip()


def render(migrations: list[Migration], sql: str) -> str:
    lines = ["### Migraciones nuevas en este PR", ""]
    lines += [f"- **{m.revision}** (va después de {m.down_revision or 'ninguna'}): `{m.path.as_posix()}`" for m in migrations]
    lines += [
        "",
        "Al fusionar en `desarrollo`, GitHub Actions las aplica a la base de datos en la nube, con copia cifrada antes.",
        "Revise que sean compatibles con el código que todavía no se actualizó: agregar tablas o columnas sí; renombrar o",
        "borrar, en dos pasos (backend/README.md, «Migraciones con GitHub Actions»).",
        "",
        "<details><summary>SQL que se va a ejecutar</summary>",
        "",
        "```sql",
        sql if len(sql) <= MAX_SQL else sql[:MAX_SQL] + "\n-- (recortado: el SQL completo sale con alembic upgrade --sql)",
        "```",
        "",
        "</details>",
    ]
    return "\n".join(lines)


def main() -> None:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        return
    try:
        migrations = ordered(paths)
    except RenumberError as error:
        sys.exit(str(error))
    print(render(migrations, offline_sql(migrations[0].down_revision, migrations[-1].revision)))


if __name__ == "__main__":
    main()
