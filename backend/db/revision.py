"""Crea la siguiente migración con el número que le toca (backend/README.md, «Migraciones»).

    uv run python -m backend.db.revision "lotes y temporadas"

Las migraciones se numeran con dos números: `1.1`, `1.2` … `1.9` y después `2.1`. El primer número es la carpeta:
`1/` guarda de la `1.1` a la `1.9` y `2/` empieza otra vez en `2.1`. Este comando calcula el número, compara los
modelos con la base de datos y deja el archivo en su carpeta. Nadie escribe el número a mano.
"""

import argparse
import re
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

VERSIONS = Path(__file__).parent / "migrations" / "versions"
FILE = re.compile(r"^(\d+)\.([1-9])_.+\.py$")
# Cada carpeta guarda nueve migraciones: de la .1 a la .9.
PER_FOLDER = 9

Number = tuple[int, int]


def existing(versions_dir: Path = VERSIONS) -> list[Number]:
    """Las migraciones que hay, como (carpeta, número), en orden."""
    found = []
    for folder in versions_dir.iterdir() if versions_dir.exists() else []:
        if not (folder.is_dir() and folder.name.isdigit()):
            continue
        for file in folder.glob("*.py"):
            match = FILE.match(file.name)
            if match and match[1] == folder.name:
                found.append((int(match[1]), int(match[2])))
    return sorted(found)


def after(number: Number) -> Number:
    """La que sigue: de 1.1 a 1.9 sube el segundo número; después de 1.9 viene 2.1."""
    folder, position = number
    return (folder, position + 1) if position < PER_FOLDER else (folder + 1, 1)


def next_revision(found: list[Number]) -> tuple[str, str]:
    """La carpeta y el identificador de la migración que toca crear."""
    folder, position = after(found[-1]) if found else (1, 1)
    return str(folder), f"{folder}.{position}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea la siguiente migración de la base de datos.")
    parser.add_argument("mensaje", help="Qué cambia, en pocas palabras: «lotes y temporadas».")
    parser.add_argument("--vacia", action="store_true", help="Sin comparar los modelos: para una migración de datos escrita a mano.")
    args = parser.parse_args()

    folder, revision = next_revision(existing())
    script = command.revision(Config("alembic.ini"), message=args.mensaje, autogenerate=not args.vacia, rev_id=revision)
    if script is None:
        sys.exit("Alembic no creó ningún archivo.")
    # Alembic lo deja en `versions/`; aquí pasa a la carpeta de su número.
    created = Path(script.path)
    target = VERSIONS / folder
    target.mkdir(parents=True, exist_ok=True)
    created.rename(target / created.name)
    print(f"Migración {revision} creada en {(target / created.name).relative_to(Path.cwd())}")
    print("Léala antes de aplicarla: uv run alembic upgrade head")


if __name__ == "__main__":
    main()
