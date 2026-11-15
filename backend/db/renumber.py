"""Pasa las migraciones de su rama al número que sigue a las de la rama de destino (HU-229).

    python -m backend.db.renumber                       # contra origin/desarrollo
    python -m backend.db.renumber --base origin/produccion

Solo usa la biblioteca estándar y git: corre con cualquier Python 3.12, sin Docker ni `uv`.

Para cuando dos personas crearon la misma migración (por ejemplo, las dos la `1.4`) y la otra ya se fusionó. Antes,
traiga la rama de destino a la suya (`git fetch` y `git merge origin/desarrollo`). El comando deja las de la rama de
destino como están y pasa las suyas detrás de la última: su `1.4` queda como `1.5`, con su archivo en su carpeta.

Solo arregla el número. Si las dos migraciones cambian la misma tabla, las pruebas lo dirán y la suya se rehace sobre la
rama de destino (backend/README.md, «Cuando dos personas crean una migración a la vez»).
"""

import argparse
import re
import subprocess  # noqa: S404 - git con argumentos fijos, sin pasar por un intérprete de órdenes
import sys
from dataclasses import dataclass
from pathlib import Path

# Solo la biblioteca estándar: corre con el Python de cualquier computador, sin Docker ni `uv`.
from backend.db.numbers import FILE, VERSIONS, after

REVISION = re.compile(r'^revision: str = "([^"]+)"$', re.MULTILINE)
DOWN = re.compile(r"^down_revision: str \| None = (None|\"[^\"]+\")$", re.MULTILINE)
HEADER = re.compile(r"^Migración \S+ · va después de .*$", re.MULTILINE)


class RenumberError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    path: Path
    revision: str
    down_revision: str | None


@dataclass(frozen=True)
class Move:
    migration: Migration
    revision: str
    down_revision: str


def read(path: Path) -> Migration:
    text = path.read_text(encoding="utf-8")
    revision, down = REVISION.search(text), DOWN.search(text)
    if not revision or not down:
        raise RenumberError(f"{path.name} no tiene `revision` y `down_revision` como las escribe el comando.")
    return Migration(path, revision[1], None if down[1] == "None" else down[1].strip('"'))


def number(revision: str) -> tuple[int, int]:
    folder, position = revision.split(".")
    return int(folder), int(position)


def chain(migrations: list[Migration], start: str | None) -> list[Migration]:
    """Las migraciones en orden, una detrás de otra, desde la que va después de `start`."""
    by_down = {m.down_revision: m for m in migrations}
    if len(by_down) != len(migrations):
        raise RenumberError("Dos migraciones van detrás de la misma: no forman una sola cadena. Arréglelo a mano antes de renumerar.")
    ordered, current = [], start
    while current in by_down:
        ordered.append(by_down[current])
        current = ordered[-1].revision
    if len(ordered) != len(migrations):
        raise RenumberError("Las migraciones no forman una sola cadena: arréglelo a mano antes de renumerar.")
    return ordered


def plan(theirs: list[Migration], mine: list[Migration]) -> list[Move]:
    """A qué número pasa cada migración propia. Vacío si ya están detrás de las de la rama de destino."""
    if not mine:
        return []
    last = chain(theirs, None)[-1].revision if theirs else None
    starts = {m.down_revision for m in mine} - {m.revision for m in mine}
    if len(starts) != 1:
        raise RenumberError("Las migraciones de su rama no forman una sola cadena: arréglelo a mano antes de renumerar.")
    ordered = chain(mine, starts.pop())
    moves, down = [], last
    following = after(number(last)) if last else (1, 1)
    for migration in ordered:
        revision = f"{following[0]}.{following[1]}"
        moves.append(Move(migration, revision, down))
        down, following = revision, after(following)
    if all(move.revision == move.migration.revision and move.down_revision == move.migration.down_revision for move in moves):
        return []
    return moves


def rewrite(text: str, move: Move) -> str:
    text = REVISION.sub(f'revision: str = "{move.revision}"', text, count=1)
    down = "None" if move.down_revision is None else f'"{move.down_revision}"'
    text = DOWN.sub(f"down_revision: str | None = {down}", text, count=1)
    return HEADER.sub(f"Migración {move.revision} · va después de {move.down_revision or 'ninguna'}", text, count=1)


def apply(moves: list[Move], versions_dir: Path = VERSIONS) -> list[Path]:
    """Reescribe y mueve cada archivo. Primero los reescribe todos y después los mueve, para no pisar ninguno."""
    contents = [(move, rewrite(move.migration.path.read_text(encoding="utf-8"), move)) for move in moves]
    created = []
    for move, text in contents:
        folder, _ = move.revision.split(".")
        name = re.sub(r"^\d+\.[1-9]_", f"{move.revision}_", move.migration.path.name)
        target = versions_dir / folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        move.migration.path.unlink()
        target.write_text(text, encoding="utf-8")
        created.append(target)
    return created


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if result.returncode != 0:
        raise RenumberError(f"git {' '.join(args)}: {result.stderr.strip() or 'falló'}")
    return result.stdout


def split(base: str, versions_dir: Path = VERSIONS) -> tuple[list[Migration], list[Migration]]:
    """Las migraciones de la rama de destino y las propias (las que la rama de destino no tiene)."""
    root = Path(_git("rev-parse", "--show-toplevel").strip())
    relative = versions_dir.resolve().relative_to(root.resolve()).as_posix()
    in_base = {Path(line).name for line in _git("ls-tree", "-r", "--name-only", base, "--", relative).splitlines()}
    here = [path for path in versions_dir.glob("*/*.py") if FILE.match(path.name)]
    missing = in_base - {path.name for path in here}
    if missing:
        raise RenumberError(f"Su rama no tiene migraciones de {base} ({', '.join(sorted(missing))}). Tráigala primero: git merge {base}")
    theirs = [read(path) for path in here if path.name in in_base]
    mine = [read(path) for path in here if path.name not in in_base]
    return theirs, mine


def main() -> None:
    parser = argparse.ArgumentParser(description="Pasa las migraciones de su rama detrás de las de la rama de destino.")
    parser.add_argument("--base", default="origin/desarrollo", help="La rama de destino (por defecto, origin/desarrollo).")
    args = parser.parse_args()
    # La terminal de Windows no siempre escribe en UTF-8: sin esto, «detrás» sale con símbolos raros.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        moves = plan(*split(args.base))
        if not moves:
            print(f"No hay nada que renumerar: sus migraciones ya van detrás de las de {args.base}.")
            return
        created = apply(moves)
    except RenumberError as error:
        sys.exit(str(error))
    for move, path in zip(moves, created, strict=True):
        print(f"{move.migration.revision} → {move.revision} (va después de {move.down_revision}): {path.as_posix()}")
    print("Si su base local ya tenía aplicada la del número viejo, rehágala: docker compose down -v, docker compose up -d db")
    print("y uv run python -m backend.db.migrate. Es la local: la de la nube no se toca.")
    print("Corra las pruebas. Si fallan porque las dos cambian la misma tabla, rehaga la suya sobre la rama de destino.")


if __name__ == "__main__":
    main()
