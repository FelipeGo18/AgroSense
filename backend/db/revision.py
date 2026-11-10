"""Crea la siguiente migración con el número que le toca (backend/README.md, «Migraciones»).

    uv run python -m backend.db.revision "lotes y temporadas"

Las migraciones se numeran con dos números: `1.1`, `1.2` … `1.9` y después `2.1`. El primer número es la carpeta:
`1/` guarda de la `1.1` a la `1.9` y `2/` empieza otra vez en `2.1`. Este comando calcula el número, compara los
modelos con la base de datos y deja el archivo en su carpeta. Nadie escribe el número a mano.
"""

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

# La numeración vive en `numbers.py`, sin dependencias, para que `renumber` corra sin el entorno del proyecto.
from backend.db.numbers import FILE, PER_FOLDER, VERSIONS, Number, after, existing, next_revision

__all__ = ["FILE", "PER_FOLDER", "VERSIONS", "Number", "after", "existing", "next_revision"]


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
